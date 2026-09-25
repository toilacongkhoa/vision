"""DRES v2 API routes, isolated from the retrieval application for testing."""

from __future__ import annotations

import asyncio
import ipaddress
import os
from typing import Any, Dict, List, Literal, Optional
from urllib.parse import urlsplit

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from .dres_client import DresApiError, DresClient
from .dres_submission import SubmissionError, validate_payload


class DRESLoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=256)
    password: str = Field(..., min_length=1, max_length=1024)


class DRESEvaluationsRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=2048)


class DRESSubmitRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=2048)
    evaluation_id: str = Field(..., min_length=1, max_length=256, pattern=r"^[A-Za-z0-9_-]+$")
    query_id: str = Field(..., min_length=1, max_length=256)
    query_type: Literal["KIS", "QA", "TRAKE"]
    payload: Dict[str, Any]


def create_dres_router(
    client: Optional[DresClient] = None,
) -> APIRouter:
    """Build routes around an injectable DRES client."""
    dres_client = client or DresClient()
    submission_lock = asyncio.Lock()
    router = APIRouter()

    @router.post("/api/v1/dres/login")
    async def dres_login(request: DRESLoginRequest):
        try:
            session_id = await dres_client.login(request.username, request.password)
            return {"session_id": session_id}
        except DresApiError as exc:
            raise HTTPException(status_code=exc.status_code or 502, detail=str(exc)) from exc

    @router.post("/api/v1/dres/login/configured")
    async def dres_login_configured(request: Request):
        origin = request.headers.get("origin", "")
        parsed_origin = urlsplit(origin)
        request_host = request.headers.get("host", "").lower()
        hostname = (request.url.hostname or "").lower()
        client_host = request.client.host if request.client else ""
        try:
            is_loopback_client = ipaddress.ip_address(client_host).is_loopback
        except ValueError:
            is_loopback_client = False
        same_local_origin = (
            parsed_origin.scheme == request.url.scheme
            and parsed_origin.netloc.lower() == request_host
            and hostname in {"localhost", "127.0.0.1", "::1"}
            and is_loopback_client
        )
        if not same_local_origin:
            raise HTTPException(status_code=403, detail="Configured DRES login is only available to the local same-origin app.")
        username = os.getenv("DRES_USERNAME", "")
        password = os.getenv("DRES_PASSWORD", "")
        if not username or not password:
            raise HTTPException(status_code=503, detail="DRES_USERNAME and DRES_PASSWORD are not configured on the server.")
        try:
            session_id = await dres_client.login(username, password)
            return {"session_id": session_id}
        except DresApiError as exc:
            raise HTTPException(status_code=exc.status_code or 502, detail=str(exc)) from exc

    @router.post("/api/v1/dres/evaluations")
    async def dres_evaluations(request: DRESEvaluationsRequest):
        try:
            return {"evaluations": await dres_client.evaluations(request.session_id)}
        except DresApiError as exc:
            raise HTTPException(status_code=exc.status_code or 502, detail=str(exc)) from exc

    @router.post("/api/v1/dres/submit")
    async def dres_submit(request: DRESSubmitRequest):
        if not request.query_id.strip():
            raise HTTPException(status_code=422, detail="query_id must be non-empty")
        try:
            validate_payload(request.payload, request.query_type)
        except SubmissionError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        async with submission_lock:
            try:
                result = await dres_client.submit_with_verdict(request.session_id, request.evaluation_id, request.payload)
            except DresApiError as exc:
                if exc.outcome_unknown:
                    raise HTTPException(status_code=504, detail=str(exc)) from exc
                if exc.status_code == 412:
                    raise HTTPException(status_code=412, detail=str(exc)) from exc
                raise HTTPException(status_code=exc.status_code or 502, detail=str(exc)) from exc
        verdict = result.get("verdict")
        accepted = True if verdict == "CORRECT" else False if verdict == "WRONG" else None
        response = {"status": "sent", "http_status": result["http_status"], "accepted": accepted}
        if verdict:
            response["verdict"] = verdict
        if result.get("description"):
            response["description"] = result["description"]
        return response

    return router
