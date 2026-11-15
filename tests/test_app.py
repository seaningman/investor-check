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
        for patch in (
            mock.patch.object(cala, "CACHE_DIR", folder.name),
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
