"""Small, secret-safe HTTP client for the DRES v2 API."""

from __future__ import annotations

import os
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urlparse

import httpx


class DresApiError(RuntimeError):
    def __init__(self, message: str, *, status_code: Optional[int] = None, outcome_unknown: bool = False):
        super().__init__(message)
        self.status_code = status_code
        self.outcome_unknown = outcome_unknown


class DresClient:
    """DRES client; secrets are only carried in request bodies/query parameters."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        *,
        client_factory: Callable[..., Any] = httpx.AsyncClient,
        trust_env: Optional[bool] = None,
    ):
        url = (base_url or os.getenv("DRES_API_BASE_URL", "https://eventretrieval.one")).rstrip("/")
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
            raise ValueError("DRES_API_BASE_URL must be an HTTPS origin without embedded credentials")
        self.base_url = url
        self.client_factory = client_factory
        if trust_env is None:
            trust_env = os.getenv("DRES_TRUST_ENV", "true").strip().lower() not in {"0", "false", "no", "off"}
        self.trust_env = trust_env

    async def login(self, username: str, password: str) -> str:
        try:
            async with self.client_factory(timeout=10.0, follow_redirects=False, trust_env=self.trust_env) as client:
                response = await client.post(f"{self.base_url}/api/v2/login", json={"username": username, "password": password})
                if not response.is_success:
                    raise DresApiError("DRES login failed", status_code=response.status_code)
                try:
                    session_id = response.json().get("sessionId")
                except (ValueError, AttributeError):
                    session_id = None
                if not isinstance(session_id, str) or not session_id.strip():
                    # Some DRES v2 deployments return a session cookie on login;
                    # their documented user/session endpoint exposes its token.
                    session_response = await client.get(f"{self.base_url}/api/v2/user/session")
                    if session_response.is_success:
                        session_id = session_response.text.strip().strip('"')
        except httpx.HTTPError as exc:
            raise DresApiError("Could not reach DRES during login") from exc
        if not isinstance(session_id, str) or not session_id.strip():
            raise DresApiError("DRES login response did not include a sessionId")
        return session_id

    async def evaluations(self, session_id: str) -> List[Dict[str, Any]]:
        try:
            async with self.client_factory(timeout=10.0, follow_redirects=False, trust_env=self.trust_env) as client:
                response = await client.get(f"{self.base_url}/api/v2/client/evaluation/list", params={"session": session_id})
        except httpx.HTTPError as exc:
            raise DresApiError("Could not reach DRES while loading evaluations") from exc
        if not response.is_success:
            raise DresApiError("DRES could not load evaluations", status_code=response.status_code)
        try:
            data = response.json()
        except ValueError as exc:
            raise DresApiError("DRES returned an invalid evaluation list") from exc
        if isinstance(data, dict) and isinstance(data.get("evaluations"), list):
            data = data["evaluations"]
        if not isinstance(data, list):
            raise DresApiError("DRES returned an invalid evaluation list")
        return [
            row for row in data
            if isinstance(row, dict)
            and str(row.get("status", "")).upper() == "ACTIVE"
            and (row.get("evaluationId") is not None or row.get("id") is not None)
        ]

    async def submit(self, session_id: str, evaluation_id: str, payload: Dict[str, Any]) -> int:
        result = await self.submit_with_verdict(session_id, evaluation_id, payload)
        return result["http_status"]

    async def submit_with_verdict(self, session_id: str, evaluation_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}/api/v2/submit/{evaluation_id}"
        try:
            async with self.client_factory(timeout=12.0, follow_redirects=False, trust_env=self.trust_env) as client:
                response = await client.post(url, params={"session": session_id}, json=payload)
        except httpx.HTTPError as exc:
            raise DresApiError("DRES submit outcome is unknown; check the DRES evaluation before retrying", outcome_unknown=True) from exc
        if response.status_code >= 500 or response.status_code == 408:
            raise DresApiError("DRES submit outcome is unknown; check the DRES evaluation before retrying", status_code=response.status_code, outcome_unknown=True)
        if not response.is_success:
            raise DresApiError("DRES rejected the submission", status_code=response.status_code)
        try:
            body = response.json()
        except ValueError:
            body = {}
        if not isinstance(body, dict):
            body = {}
        verdict = body.get("submission")
        if not isinstance(verdict, str):
            verdict = None
        else:
            verdict = verdict.upper()
        return {
            "http_status": response.status_code,
            "verdict": verdict,
            "description": body.get("description") if isinstance(body.get("description"), str) else None,
        }
