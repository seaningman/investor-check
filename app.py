from concurrent.futures import ThreadPoolExecutor

from flask import Flask, abort, jsonify, make_response, render_template, request

import cala
import prompts

app = Flask(__name__)
app.json.sort_keys = False  # keep Cala's column order in the tables

# Each founder lookup is one more Cala request. Four keeps a whole investor
# check (9 requests) under Cala's free-tier limit of 10 requests per minute.
MAX_FOUNDER_LOOKUPS = 4

# Properties of a Cala entity record shown as quick facts: (property, label).
# A registered address is only shown when there is no headquarters address.
FACTS = [
    ("founding_date", "Founded"),
    ("headquarters_address", "Headquarters"),
    ("registered_address", "Registered address"),
    ("website", "Website"),
    ("employee_count", "Employees"),
]


def _required(arg):
    """Return a query-string argument, or stop with a 400 if it is missing."""
    value = request.args.get(arg, "").strip()
    if not value:
        abort(make_response(jsonify(error="Missing '%s'." % arg), 400))
    return value


def _sources(answer):
    """The documents behind a knowledge_search answer, without duplicates."""
    sources, seen = [], set()
    for fact in answer.get("context") or []:
        for origin in fact.get("origins") or []:
            document = origin.get("document") or {}
            url = document.get("url")
            if url and url.startswith(("http://", "https://")) and url not in seen:
                seen.add(url)
                sources.append({
                    "title": document.get("name") or url,
                    "url": url,
                    "publisher": (origin.get("source") or {}).get("name"),
                })
    return sources


def _column(row, *words):
    """The name of the first column in a row whose name contains one of `words`."""
    for key in row:
        if any(word in key.lower() for word in words):
            return key
    return None


def _founders(company):
    """The names of a company's founders, or None if Cala can't say."""
    if not company:
        return None
    try:
        answer = cala.knowledge_query(prompts.company_founders(company), return_entities=False)
    except cala.CalaError:
        return None  # e.g. rate limited; the caller keeps the founders it already has
    names = []
    for row in answer.get("results") or []:
        name = row.get(_column(row, "name", "founder"))
        if name:
            names.append(str(name))
    return ", ".join(names) or None


@app.errorhandler(cala.CalaError)
def cala_error(e):
    if e.status == 429:
        return jsonify(error="Cala's request limit was reached. Wait a minute and try again."), 429
    return jsonify(error=e.message), e.status or 502


# --- Page -------------------------------------------------------------------


@app.route("/")
def home():
    return render_template("index.html")


# --- JSON API ---------------------------------------------------------------


@app.route("/api/entities")
def api_entities():
    """The investors a typed name could mean, so the founder can pick the right one."""
    name = _required("name")[:100]  # Cala's limit for entity names
    found = cala.search_entities(name, entity_types=["Company", "Organization", "Person"], limit=8)
    return jsonify(entities=[
        {
            "id": entity.get("id") or "",
            "name": entity.get("name") or "",
            "type": entity.get("entity_type") or "",
            "description": entity.get("description") or "",
        }
        for entity in found.get("entities") or []
        if entity.get("name")
    ])


@app.route("/api/facts")
def api_facts():
    """Quick facts from an investor's Cala entity record. Fast, unlike the briefing."""
    entity = cala.retrieve_entity(_required("id"))
    properties = entity.get("properties") or {}

    facts = []
    for key, label in FACTS:
        value = (properties.get(key) or {}).get("value")
        if not isinstance(value, (str, int)) or value == "":
            continue
        if key == "registered_address" and any(fact["label"] == "Headquarters" for fact in facts):
            continue
        fact = {"label": label, "value": str(value)}
        if key == "founding_date":
            fact["value"] = fact["value"][:4]  # the year; the day is often a placeholder
        elif key == "website":
            url = fact["value"] if "://" in fact["value"] else "https://" + fact["value"]
            if url.startswith(("http://", "https://")):
                fact["url"] = url
        elif key == "employee_count" and isinstance(value, int):
            fact["value"] = "{:,}".format(value)
        facts.append(fact)

    return jsonify(type=entity.get("entity_type") or "", facts=facts)


def _investor():
    """The investor a request is about: its name and, if one was picked, its description."""
    return _required("name"), request.args.get("about", "").strip()[:300]


@app.route("/api/investor")
def api_investor():
    """A written briefing on one investor, with its sources."""
    name, about = _investor()
    answer = cala.knowledge_search(
        prompts.investor_profile(name, about), explainability=False, return_entities=False)
    return jsonify(briefing=answer.get("content") or "", sources=_sources(answer))


@app.route("/api/portfolio")
def api_portfolio():
    """One investor's investments as table rows."""
    name, about = _investor()
    answer = cala.knowledge_query(prompts.investor_portfolio(name, about), return_entities=False)
    return jsonify(rows=answer.get("results") or [])


@app.route("/api/worth-a-call")
def api_worth_a_call():
    """One investor's failed or struggling companies and their founders, as table rows."""
    name, about = _investor()
    answer = cala.knowledge_query(prompts.worth_a_call(name, about), return_entities=False)
    rows = answer.get("results") or []

    # Ask Cala for each company's founders, all at the same time. A row keeps
    # the founders from the list above if its own lookup finds nothing.
    lookups = rows[:MAX_FOUNDER_LOOKUPS]
    companies = [row.get(_column(row, "company", "name")) for row in lookups]
    with ThreadPoolExecutor(max_workers=MAX_FOUNDER_LOOKUPS) as pool:
        founders = list(pool.map(_founders, companies))
    for row, names in zip(lookups, founders):
        if names:
            row[_column(row, "founder") or "founders"] = names

    return jsonify(rows=rows)


@app.route("/api/search")
def api_search():
    """Investors matching a founder's description, as table rows."""
    query = _required("q")
    answer = cala.knowledge_query(prompts.find_investors(query), return_entities=False)
    return jsonify(rows=answer.get("results") or [])


if __name__ == "__main__":
    # Port 5000 is taken by AirPlay Receiver on macOS.
    app.run(debug=True, port=5001)
