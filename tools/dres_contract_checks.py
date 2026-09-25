"""Offline contract checks for the DRES v2 HTTP client (no organizer calls)."""

import asyncio
import unittest
from unittest.mock import patch

import httpx
from fastapi import FastAPI

from src.dres_api import create_dres_router
from src.dres_client import DresApiError, DresClient
from src.dres_submission import SubmissionDeduper, SubmissionError


class DresContractTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.requests = []
        self.responses = []

        def handler(request):
            self.requests.append(request)
            return self.responses.pop(0)

        transport = httpx.MockTransport(handler)
        self.factory = lambda **kwargs: httpx.AsyncClient(transport=transport, **kwargs)
        self.client = DresClient("https://dres.test", client_factory=self.factory)

    async def test_login_and_active_evaluations(self):
        self.responses.extend([
            httpx.Response(200, json={"sessionId": "test-session"}),
            httpx.Response(200, json=[
                {"evaluationId": "active-1", "name": "Final", "status": "ACTIVE"},
                {"evaluationId": "done-1", "name": "Old", "status": "FINISHED"},
            ]),
        ])
        session = await self.client.login("demo-user", "demo-secret")
        active = await self.client.evaluations(session)
        self.assertEqual(session, "test-session")
        self.assertEqual([row["evaluationId"] for row in active], ["active-1"])
        self.assertEqual(self.requests[0].url.path, "/api/v2/login")
        self.assertEqual(self.requests[0].read(), b'{"username":"demo-user","password":"demo-secret"}')
        self.assertEqual(self.requests[1].url.path, "/api/v2/client/evaluation/list")
        self.assertEqual(self.requests[1].url.params["session"], session)

    async def test_login_cookie_session_fallback(self):
        self.responses.extend([
            httpx.Response(200, json={"userId": "demo-user"}, headers={"set-cookie": "DRESSESSION=cookie-session; Path=/; Secure; HttpOnly"}),
            httpx.Response(200, text="cookie-session"),
        ])
        session = await self.client.login("demo-user", "demo-secret")
        self.assertEqual(session, "cookie-session")
        self.assertEqual(self.requests[1].url.path, "/api/v2/user/session")
        self.assertIn("DRESSESSION=cookie-session", self.requests[1].headers["cookie"])

    async def test_submit_path_query_and_payload(self):
        payload = {"answerSets": [{"answers": [{"mediaItemName": "L26_V123", "start": "1200", "end": "1200"}]}]}
        self.responses.append(httpx.Response(200, json={"status": "ok"}))
        status = await self.client.submit("secret-session", "eval-42", payload)
        request = self.requests[0]
        self.assertEqual(status, 200)
        self.assertEqual(request.method, "POST")
        self.assertEqual(request.url.path, "/api/v2/submit/eval-42")
        self.assertEqual(request.url.params["session"], "secret-session")
        self.assertEqual(request.read(), b'{"answerSets":[{"answers":[{"mediaItemName":"L26_V123","start":"1200","end":"1200"}]}]}')

    async def test_server_error_is_unknown_outcome(self):
        self.responses.append(httpx.Response(503, json={"detail": "temporary"}))
        with self.assertRaises(DresApiError) as raised:
            await self.client.submit("session", "eval-42", {"answerSets": []})
        self.assertTrue(raised.exception.outcome_unknown)
        self.assertEqual(raised.exception.status_code, 503)

    async def test_wrapped_evaluation_list_filters_invalid_rows(self):
        self.responses.append(httpx.Response(200, json={"evaluations": [
            {"id": "active-1", "status": "ACTIVE"},
            {"name": "missing-id", "status": "ACTIVE"},
            {"id": "inactive-1", "status": "FINISHED"},
        ]}))
        active = await self.client.evaluations("session")
        self.assertEqual(active, [{"id": "active-1", "status": "ACTIVE"}])

    async def test_deduper_records_same_query_payload_without_blocking_retry(self):
        guard = SubmissionDeduper()
        first = {"answerSets": [{"answers": [{"text": "QA-spoon-L26_V1-200"}]}]}
        corrected = {"answerSets": [{"answers": [{"text": "QA-ladle-L26_V1-200"}]}]}
        guard.record("query-1", first)
        self.assertTrue(guard.contains("query-1", first))
        self.assertFalse(guard.contains("query-1", corrected))
        guard.record("query-1", first)
        guard.record("query-1", corrected)

    async def test_credentials_require_https(self):
        for base_url in ("http://dres.test", "https://user:password@dres.test"):
            with self.assertRaises(ValueError):
                DresClient(base_url)

    async def test_api_routes_login_list_submit_and_allow_duplicate(self):
        payload = {"answerSets": [{"answers": [{"text": "TR-L26_V1-10,20"}]}]}
        self.responses.extend([
            httpx.Response(200, json={"sessionId": "route-session"}),
            httpx.Response(200, json=[{"id": "eval-1", "name": "Final", "status": "ACTIVE"}]),
            httpx.Response(202, json={"status": "pending"}),
            httpx.Response(202, json={"status": "pending"}),
        ])
        app = FastAPI()
        app.include_router(create_dres_router(self.client))
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as api:
            login = await api.post("/api/v1/dres/login", json={"username": "demo", "password": "secret"})
            self.assertEqual(login.status_code, 200)
            session = login.json()["session_id"]
            evaluations = await api.post("/api/v1/dres/evaluations", json={"session_id": session})
            self.assertEqual(evaluations.json()["evaluations"][0]["id"], "eval-1")
            body = {"session_id": session, "evaluation_id": "eval-1", "query_id": "query-1", "query_type": "TRAKE", "payload": payload}
            submitted = await api.post("/api/v1/dres/submit", json=body)
            repeated = await api.post("/api/v1/dres/submit", json=body)
            self.assertEqual(submitted.status_code, 200)
            self.assertEqual(submitted.json(), {"status": "sent", "http_status": 202, "accepted": None})
            self.assertEqual(repeated.status_code, 200)
        self.assertEqual(len([request for request in self.requests if "/api/v2/submit/" in request.url.path]), 2)

    async def test_configured_login_uses_server_env_for_local_same_origin(self):
        self.responses.append(httpx.Response(200, json={"sessionId": "configured-session"}))
        app = FastAPI()
        app.include_router(create_dres_router(self.client))
        transport = httpx.ASGITransport(app=app)
        with patch.dict("os.environ", {"DRES_USERNAME": "team-demo", "DRES_PASSWORD": "secret-demo"}):
            async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as api:
                response = await api.post("/api/v1/dres/login/configured", headers={"Origin": "http://localhost"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"session_id": "configured-session"})
        self.assertEqual(self.requests[0].read(), b'{"username":"team-demo","password":"secret-demo"}')

    async def test_configured_login_rejects_cross_origin(self):
        app = FastAPI()
        app.include_router(create_dres_router(self.client))
        transport = httpx.ASGITransport(app=app)
        with patch.dict("os.environ", {"DRES_USERNAME": "team-demo", "DRES_PASSWORD": "secret-demo"}):
            async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as api:
                response = await api.post("/api/v1/dres/login/configured", headers={"Origin": "https://attacker.example"})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.requests, [])

    async def test_configured_login_requires_env_credentials(self):
        app = FastAPI()
        app.include_router(create_dres_router(self.client))
        transport = httpx.ASGITransport(app=app)
        with patch.dict("os.environ", {"DRES_USERNAME": "", "DRES_PASSWORD": ""}):
            async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as api:
                response = await api.post("/api/v1/dres/login/configured", headers={"Origin": "http://localhost"})
        self.assertEqual(response.status_code, 503)
        self.assertEqual(self.requests, [])

    async def test_api_routes_validate_before_submit_and_allow_unknown_retry(self):
        app = FastAPI()
        app.include_router(create_dres_router(self.client))
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as api:
            invalid = await api.post("/api/v1/dres/submit", json={
                "session_id": "session", "evaluation_id": "eval-1", "query_id": "query-1",
                "query_type": "TRAKE", "payload": {"answerSets": []},
            })
            self.assertEqual(invalid.status_code, 422)
            blank_query = await api.post("/api/v1/dres/submit", json={
                "session_id": "session", "evaluation_id": "eval-1", "query_id": "   ",
                "query_type": "KIS", "payload": {"answerSets": [{"answers": [{"mediaItemName": "L26_V1", "start": "20", "end": "20"}]}]},
            })
            self.assertEqual(blank_query.status_code, 422)
            self.assertEqual(self.requests, [])

            payload = {"answerSets": [{"answers": [{"mediaItemName": "L26_V1", "start": "20", "end": "20"}]}]}
            self.responses.extend([
                httpx.Response(503, json={"detail": "temporary"}),
                httpx.Response(202, json={"status": "pending"}),
                httpx.Response(202, json={"status": "pending"}),
            ])
            body = {"session_id": "session", "evaluation_id": "eval-1", "query_id": "query-2", "query_type": "KIS", "payload": payload}
            unknown = await api.post("/api/v1/dres/submit", json=body)
            retry = await api.post("/api/v1/dres/submit", json=body)
            body["payload"] = {"answerSets": [{"answers": [{"mediaItemName": "L26_V1", "start": "21", "end": "21"}]}]}
            corrected = await api.post("/api/v1/dres/submit", json=body)
            self.assertEqual(unknown.status_code, 504)
            self.assertEqual(retry.status_code, 200)
            self.assertEqual(corrected.status_code, 200)
        self.assertEqual(len(self.requests), 3)

    async def test_api_route_allows_retry_of_rejected_payload_and_correction(self):
        app = FastAPI()
        app.include_router(create_dres_router(self.client))
        original = {"answerSets": [{"answers": [{"text": "TR-L26_V1-10,20"}]}]}
        corrected = {"answerSets": [{"answers": [{"text": "TR-L26_V1-10,21"}]}]}
        self.responses.extend([
            httpx.Response(412, json={"detail": "rejected"}),
            httpx.Response(200, json={"status": "ok"}),
            httpx.Response(200, json={"status": "ok"}),
        ])
        body = {"session_id": "session", "evaluation_id": "eval-1", "query_id": "query-3", "query_type": "TRAKE", "payload": original}
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as api:
            rejected = await api.post("/api/v1/dres/submit", json=body)
            retry = await api.post("/api/v1/dres/submit", json=body)
            body["payload"] = corrected
            corrected_response = await api.post("/api/v1/dres/submit", json=body)
        self.assertEqual(rejected.status_code, 412)
        self.assertEqual(retry.status_code, 200)
        self.assertEqual(corrected_response.status_code, 200)
        self.assertEqual(len(self.requests), 3)

    async def test_api_route_preserves_dres_auth_and_evaluation_errors(self):
        app = FastAPI()
        app.include_router(create_dres_router(self.client))
        self.responses.extend([
            httpx.Response(401, json={"detail": "unauthorized"}),
            httpx.Response(404, json={"detail": "evaluation not found"}),
        ])
        body = {
            "session_id": "session", "evaluation_id": "eval-1", "query_id": "query-5",
            "query_type": "KIS",
            "payload": {"answerSets": [{"answers": [{"mediaItemName": "L26_V1", "start": "20", "end": "20"}]}]},
        }
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as api:
            unauthorized = await api.post("/api/v1/dres/submit", json=body)
            missing_evaluation = await api.post("/api/v1/dres/submit", json=body)
        self.assertEqual(unauthorized.status_code, 401)
        self.assertEqual(missing_evaluation.status_code, 404)
        self.assertEqual(len(self.requests), 2)

    async def test_api_route_forwards_concurrent_duplicate_retries(self):
        app = FastAPI()
        app.include_router(create_dres_router(self.client))
        self.responses.extend([
            httpx.Response(200, json={"status": "ok"}),
            httpx.Response(200, json={"status": "ok"}),
        ])
        payload = {"answerSets": [{"answers": [{"mediaItemName": "L26_V1", "start": "20", "end": "20"}]}]}
        body = {"session_id": "session", "evaluation_id": "eval-1", "query_id": "query-4", "query_type": "KIS", "payload": payload}
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as api:
            first, second = await asyncio.gather(
                api.post("/api/v1/dres/submit", json=body),
                api.post("/api/v1/dres/submit", json=body),
            )
        self.assertEqual(sorted([first.status_code, second.status_code]), [200, 200])
        self.assertEqual(len(self.requests), 2)


if __name__ == "__main__":
    unittest.main()
