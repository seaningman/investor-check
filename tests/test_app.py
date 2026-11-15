"""Tests for the JSON API in app.py and the cache in cala.py.

Cala is replaced by stand-ins throughout, so these never use the network or credits.
"""

import io
import json
import os
import tempfile
import time
import unittest
import urllib.error
from unittest import mock

import app
import cala


def rows(*results):
    return {"results": list(results), "entities": None}


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = app.app.test_client()
        server_key = mock.patch.dict(os.environ, {"CALA_API_KEY": "server-key"})
        server_key.start()
        self.addCleanup(server_key.stop)

    def test_page_loads(self):
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_missing_argument_is_a_400(self):
        for path in ("/api/entities", "/api/facts", "/api/investor", "/api/portfolio",
                     "/api/worth-a-call", "/api/search"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 400, path)
            self.assertIn("error", response.json)

    def test_entities(self):
        found = {"entities": [
            {"id": "1", "name": "Sequoia Capital", "entity_type": "Organization", "description": "A VC firm."},
            {"id": "2", "name": "", "entity_type": "Company", "description": "No name, so left out."},
        ]}
        with mock.patch.object(cala, "search_entities", return_value=found):
            response = self.client.get("/api/entities?name=Sequoia")
        self.assertEqual(response.json["entities"], [
            {"id": "1", "name": "Sequoia Capital", "type": "Organization", "description": "A VC firm."},
        ])

    def test_facts(self):
        entity = {"entity_type": "Organization", "properties": {
            "founding_date": {"value": "1972-01-01"},
            "registered_address": {"value": "2800 Sand Hill Rd"},
            "website": {"value": "sequoiacap.com"},
            "employee_count": {"value": 1904},
            "aliases": {"value": ["Sequoia"]},
        }}
        with mock.patch.object(cala, "retrieve_entity", return_value=entity):
            response = self.client.get("/api/facts?id=1")
        self.assertEqual(response.json, {"type": "Organization", "facts": [
            {"label": "Founded", "value": "1972"},
            {"label": "Registered address", "value": "2800 Sand Hill Rd"},
            {"label": "Website", "value": "sequoiacap.com", "url": "https://sequoiacap.com"},
            {"label": "Employees", "value": "1,904"},
        ]})

    def test_facts_prefers_headquarters_over_registered_address(self):
        entity = {"properties": {
            "headquarters_address": {"value": "Menlo Park"},
            "registered_address": {"value": "Delaware"},
        }}
        with mock.patch.object(cala, "retrieve_entity", return_value=entity):
            facts = self.client.get("/api/facts?id=1").json["facts"]
        self.assertEqual(facts, [{"label": "Headquarters", "value": "Menlo Park"}])

    def test_investor_briefing_and_sources(self):
        origin = {"source": {"name": "Publisher"}, "document": {"name": "Doc", "url": "https://example.com/a"}}
        unsafe = {"source": {"name": "Bad"}, "document": {"name": "Bad", "url": "javascript:alert(1)"}}
        answer = {"content": "**Hello**", "context": [
            {"origins": [origin, unsafe]},
            {"origins": [origin]},  # the same document again
        ]}
        with mock.patch.object(cala, "knowledge_search", return_value=answer):
            response = self.client.get("/api/investor?name=Sequoia")
        self.assertEqual(response.json, {
            "briefing": "**Hello**",
            "sources": [{"title": "Doc", "url": "https://example.com/a", "publisher": "Publisher"}],
        })

    def test_portfolio_and_search_keep_column_order(self):
        answer = rows({"name": "Seedcamp", "location": "London", "investor_type": "VC"})
        with mock.patch.object(cala, "knowledge_query", return_value=answer):
            for path in ("/api/portfolio?name=x", "/api/search?q=x"):
                response = self.client.get(path)
                self.assertEqual(list(response.json["rows"][0]), ["name", "location", "investor_type"], path)

    def test_rate_limit_message(self):
        error = cala.CalaError("Rate limit exceeded. Too many requests.", status=429)
        with mock.patch.object(cala, "knowledge_query", side_effect=error):
            response = self.client.get("/api/search?q=x")
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json["error"], "Cala's request limit was reached. Wait a minute and try again.")

    def test_other_cala_errors_pass_through(self):
        with mock.patch.object(cala, "knowledge_query", side_effect=cala.CalaError("Could not reach Cala")):
            response = self.client.get("/api/search?q=x")
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json["error"], "Could not reach Cala")

    def test_worth_a_call_looks_up_founders_and_falls_back(self):
        companies = ["Found", "Limited", "Empty", "Fourth", "Fifth"]

        def knowledge_query(question, **kwargs):
            if question.startswith("List companies"):
                return rows(*({"company": c, "founders": "from list"} for c in companies))
            if "Limited" in question:
                raise cala.CalaError("Rate limit exceeded.", status=429)
            if "Empty" in question:
                return rows()
            return rows({"name": "Ann Lee", "role": "CEO"}, {"name": "Bo Chan", "role": "CTO"})

        with mock.patch.object(cala, "knowledge_query", side_effect=knowledge_query) as query:
            response = self.client.get("/api/worth-a-call?name=Sequoia")

        founders = {row["company"]: row["founders"] for row in response.json["rows"]}
        self.assertEqual(founders, {
            "Found": "Ann Lee, Bo Chan",
            "Limited": "from list",   # its lookup was rate limited
            "Empty": "from list",     # its lookup found nobody
            "Fourth": "Ann Lee, Bo Chan",
            "Fifth": "from list",     # beyond MAX_FOUNDER_LOOKUPS
        })
        self.assertEqual(query.call_count, 1 + app.MAX_FOUNDER_LOOKUPS)


class KeyTests(unittest.TestCase):
    """Each visitor brings their own Cala API key in the X-Cala-Key header."""

    ROUTES = ("/api/entities?name=x", "/api/facts?id=1", "/api/investor?name=x",
              "/api/portfolio?name=x", "/api/worth-a-call?name=x", "/api/search?q=x")

    def setUp(self):
        self.client = app.app.test_client()
        self.set_server_key("")

    def set_server_key(self, value):
        patch = mock.patch.dict(os.environ, {"CALA_API_KEY": value})
        patch.start()
        self.addCleanup(patch.stop)

    def test_key_page_loads(self):
        self.assertEqual(self.client.get("/key").status_code, 200)

    def test_key_status(self):
        self.assertEqual(self.client.get("/api/key-status").json, {"server_key": False})
        self.set_server_key("server-key")
        self.assertEqual(self.client.get("/api/key-status").json, {"server_key": True})

    def test_no_key_anywhere_is_a_401(self):
        for path in self.ROUTES:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 401, path)
            self.assertEqual(response.json["error"], "Add your Cala API key to continue.")

    def test_visitor_key_reaches_every_cala_call(self):
        answer = {"results": [{"company": "A", "founders": "x"}], "entities": [], "content": "", "properties": {}}
        names = ("search_entities", "retrieve_entity", "knowledge_search", "knowledge_query")
        with mock.patch.multiple(cala, **{name: mock.Mock(return_value=answer) for name in names}):
            for path in self.ROUTES:
                self.assertEqual(self.client.get(path, headers={"X-Cala-Key": "visitor-key"}).status_code, 200, path)
            for name in names:
                calls = getattr(cala, name).call_args_list
                self.assertTrue(calls, name)
                for call in calls:  # includes the founder lookups, which run in threads
                    self.assertEqual(call.kwargs["api_key"], "visitor-key", name)

    def test_visitor_key_wins_over_server_key(self):
        self.set_server_key("server-key")
        with mock.patch.object(cala, "knowledge_query", return_value=rows()) as query:
            self.client.get("/api/search?q=x", headers={"X-Cala-Key": "visitor-key"})
            self.client.get("/api/search?q=x")
        self.assertEqual([call.kwargs["api_key"] for call in query.call_args_list], ["visitor-key", "server-key"])

    def test_rejected_key_is_a_401(self):
        with mock.patch.object(cala, "knowledge_query", side_effect=cala.CalaError("Invalid API key", status=401)):
            response = self.client.get("/api/search?q=x", headers={"X-Cala-Key": "bad"})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json["error"], "Cala didn't accept that API key.")

    def test_check_key(self):
        with mock.patch.object(cala, "search_entities", return_value={"entities": []}) as search:
            response = self.client.post("/api/check-key", headers={"X-Cala-Key": " good-key "})
        self.assertEqual(response.json, {"ok": True})
        self.assertEqual(search.call_args.kwargs["api_key"], "good-key")
        self.assertIs(search.call_args.kwargs["use_cache"], False)  # must really ask Cala

    def test_check_key_rejected_or_missing(self):
        with mock.patch.object(cala, "search_entities", side_effect=cala.CalaError("Invalid API key", status=401)):
            response = self.client.post("/api/check-key", headers={"X-Cala-Key": "bad"})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json["error"], "That key didn't work. Check you copied all of it.")
        self.assertEqual(self.client.post("/api/check-key").status_code, 400)


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class CacheTests(unittest.TestCase):
    def setUp(self):
        self.calls = 0
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.seed = tempfile.TemporaryDirectory()
        self.addCleanup(self.seed.cleanup)
        for patch in (
            mock.patch.object(cala, "CACHE_DIR", folder.name),
            mock.patch.object(cala, "SEED_DIR", self.seed.name),
            mock.patch.dict(os.environ, {"CALA_API_KEY": "stand-in"}),
            mock.patch("urllib.request.urlopen", side_effect=self.urlopen),
        ):
            patch.start()
            self.addCleanup(patch.stop)

    def urlopen(self, request, timeout=None):
        self.calls += 1
        if "fail" in request.full_url:
            body = io.BytesIO(b'{"error": "rate_limit_exceeded", "message": "Rate limit exceeded."}')
            raise urllib.error.HTTPError(request.full_url, 429, "Too Many Requests", {}, body)
        return FakeResponse(json.dumps({"entities": [], "call": self.calls}).encode())

    def test_same_question_is_asked_once(self):
        first = cala.search_entities("Sequoia")
        second = cala.search_entities("Sequoia")
        self.assertEqual(first, second)
        self.assertEqual(self.calls, 1)

    def test_seeded_answers_never_expire(self):
        cala.search_entities("Sequoia")
        long_ago = time.time() - cala.CACHE_SECONDS - 60
        for name in os.listdir(cala.CACHE_DIR):  # move the saved answer into the seed folder, aged
            os.replace(os.path.join(cala.CACHE_DIR, name), os.path.join(cala.SEED_DIR, name))
            os.utime(os.path.join(cala.SEED_DIR, name), (long_ago, long_ago))
        cala.search_entities("Sequoia")
        self.assertEqual(self.calls, 1)

    def test_use_cache_false_always_asks(self):
        cala.search_entities("Sequoia")
        cala.search_entities("Sequoia", use_cache=False)
        self.assertEqual(self.calls, 2)

    def test_given_key_is_sent_to_cala(self):
        with mock.patch("urllib.request.urlopen", side_effect=self.urlopen) as urlopen:
            cala.search_entities("Sequoia", api_key="visitor-key")
        self.assertEqual(urlopen.call_args.args[0].get_header("X-api-key"), "visitor-key")

    def test_different_questions_are_asked_separately(self):
        cala.search_entities("Sequoia")
        cala.search_entities("Index")
        self.assertEqual(self.calls, 2)

    def test_errors_are_not_saved(self):
        for _ in range(2):
            with self.assertRaises(cala.CalaError) as raised:
                cala.search_entities("fail")
            self.assertEqual(raised.exception.status, 429)
        self.assertEqual(self.calls, 2)

    def test_old_answers_are_asked_again(self):
        cala.search_entities("Sequoia")
        long_ago = time.time() - cala.CACHE_SECONDS - 60
        for name in os.listdir(cala.CACHE_DIR):
            os.utime(os.path.join(cala.CACHE_DIR, name), (long_ago, long_ago))
        cala.search_entities("Sequoia")
        self.assertEqual(self.calls, 2)


if __name__ == "__main__":
    unittest.main()
