import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

from dotenv import load_dotenv

load_dotenv()  # picks up CALA_API_KEY from the .env file

BASE_URL = "https://api.cala.ai"
TIMEOUT = 120  # seconds; the knowledge endpoints can take over a minute

# Answers are saved here and reused, so a repeated question is instant and
# costs no credits. Delete the folder to clear it.
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache")
CACHE_SECONDS = 24 * 60 * 60


class CalaError(Exception):
    """Any failure talking to Cala. `status` is the HTTP status, or None if no response."""

    def __init__(self, message, status=None):
        super().__init__(message)
        self.message = message
        self.status = status


def _error_message(payload, fallback):
    """Pull a readable message out of Cala's different error shapes."""
    if not isinstance(payload, dict):
        return fallback
    error = payload.get("error")
    if isinstance(error, dict) and error.get("message"):  # {"error": {"error_type", "message"}}
        return error["message"]
    if payload.get("message"):  # {"error": "rate_limit_exceeded", "message": ...}
        return payload["message"]
    if payload.get("detail"):  # {"detail": "API Key not present"}
        detail = payload["detail"]
        return detail if isinstance(detail, str) else json.dumps(detail)
    return fallback


def _cache_path(method, path, params, body):
    """The file a request's answer is saved in."""
    key = json.dumps([method, path, params, body], sort_keys=True)
    return os.path.join(CACHE_DIR, hashlib.sha256(key.encode("utf-8")).hexdigest() + ".json")


def _cache_read(cache_path):
    """A saved answer that is still fresh, or None."""
    try:
        if time.time() - os.path.getmtime(cache_path) > CACHE_SECONDS:
            return None
        with open(cache_path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _cache_write(cache_path, answer):
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        temporary = "%s.%d.tmp" % (cache_path, os.getpid())
        with open(temporary, "w", encoding="utf-8") as f:
            json.dump(answer, f)
        os.replace(temporary, cache_path)  # so a half-written file is never read
    except OSError:
        pass  # the cache is a convenience; never fail a request over it


def _request(method, path, params=None, body=None):
    """Send one request to Cala and return the parsed JSON response."""
    cache_path = _cache_path(method, path, params, body)
    cached = _cache_read(cache_path)
    if cached is not None:
        return cached

    api_key = os.environ.get("CALA_API_KEY")
    if not api_key:
        raise CalaError("CALA_API_KEY is not set. Add it to .env (get a key at https://console.cala.ai).")

    url = BASE_URL + path
    if params:
        url += "?" + urllib.parse.urlencode(params, doseq=True)

    headers = {"X-API-KEY": api_key, "Accept": "application/json"}
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            raw = response.read()
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            payload = json.loads(raw)
        except ValueError:
            payload = None
        fallback = "Cala returned HTTP %d" % e.code
        raise CalaError(_error_message(payload, fallback), status=e.code) from e
    except OSError as e:  # URLError, timeouts, connection problems
        raise CalaError("Could not reach Cala: %s" % (getattr(e, "reason", None) or e)) from e

    try:
        answer = json.loads(raw)
    except ValueError as e:
        raise CalaError("Cala returned a response that is not JSON") from e
    _cache_write(cache_path, answer)
    return answer


# --- Knowledge ----------------------------------------------------------------


def knowledge_search(question, explainability=True, return_entities=True):
    """Ask a natural-language question; get a markdown answer with sources.

    Returns {"content", "explainability", "context", "entities"}.
    """
    return _request("POST", "/v1/knowledge/search", body={
        "input": question,
        "explainability": explainability,
        "return_entities": return_entities,
    })


def knowledge_query(question, return_entities=True):
    """Ask a question; get structured rows whose columns depend on the question.

    Returns {"results": [...], "entities": [...]}.
    """
    return _request("POST", "/v1/knowledge/query", body={
        "input": question,
        "return_entities": return_entities,
    })


# --- Entities -----------------------------------------------------------------


def search_entities(name, entity_types=None, limit=20):
    """Find entities by (fuzzy) name, most relevant first.

    entity_types optionally filters, e.g. ["Company", "Person"].
    Returns {"entities": [{"id", "name", "entity_type", "description"}, ...]}.
    """
    params = {"name": name, "limit": limit}
    if entity_types:
        params["entity_types"] = entity_types
    return _request("GET", "/v1/entities", params=params)


def lookup_entity(scheme, value):
    """Resolve one entity by an external identifier, e.g. lookup_entity("lei", "9598...").

    Supported schemes: cik, companies_house_uk_company_number, lei, rssd_id, siren.
    """
    return _request("POST", "/v1/entities/lookup", body={"id": {scheme: str(value)}})


def introspect_entity(entity_id):
    """List the properties, relationships and numerical observations an entity has."""
    return _request("GET", "/v1/entities/%s/introspection" % urllib.parse.quote(str(entity_id), safe=""))


def retrieve_entity(entity_id, properties=None, relationships=None, numerical_observations=None):
    """Get an entity's details by its UUID.

    With no optional arguments Cala returns its default properties. Otherwise:
      properties: list of property names, e.g. ["name", "aliases"]
      relationships: {"outgoing": {TYPE: {"limit", "offset"}}, "incoming": {...}}
      numerical_observations: {"FinancialMetric": [observation UUIDs]}
    Use introspect_entity() to see what is available for an entity.
    """
    body = {}
    if properties:
        body["properties"] = properties
    if relationships:
        body["relationships"] = relationships
    if numerical_observations:
        body["numerical_observations"] = numerical_observations
    return _request("POST", "/v1/entities/%s" % urllib.parse.quote(str(entity_id), safe=""), body=body)
