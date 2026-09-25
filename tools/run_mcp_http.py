"""Run the read-only video search MCP server over Streamable HTTP."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mcp_server import mcp  # noqa: E402
from starlette.middleware.base import BaseHTTPMiddleware  # noqa: E402
from starlette.responses import JSONResponse  # noqa: E402


class ApiKeyAuthMiddleware(BaseHTTPMiddleware):
    """Enforce API key authentication when MCP_API_KEY is configured."""

    async def dispatch(self, request, call_next):
        api_key = os.getenv("MCP_API_KEY", "").strip()
        # Health check endpoint does not require auth
        if request.url.path in {"/health", "/healthz"}:
            return JSONResponse({"status": "ok", "service": "video-retrieval-mcp-http"})

        if api_key:
            auth_header = request.headers.get("Authorization", "")
            x_api_key = request.headers.get("X-API-Key", "")
            token = ""
            if auth_header.startswith("Bearer "):
                token = auth_header[7:].strip()
            elif x_api_key:
                token = x_api_key.strip()

            if token != api_key:
                return JSONResponse(
                    {
                        "jsonrpc": "2.0",
                        "id": "unauthorized",
                        "error": {
                            "code": -32000,
                            "message": "Unauthorized: invalid or missing API key in Authorization or X-API-Key header",
                        },
                    },
                    status_code=401,
                )

        return await call_next(request)


def _csv_env(name: str, default: str) -> list[str]:
    return [value.strip() for value in os.getenv(name, default).split(",") if value.strip()]


def create_app():
    mcp.settings.stateless_http = True
    mcp.settings.json_response = True
    mcp.settings.streamable_http_path = "/mcp"
    mcp.settings.transport_security.allowed_hosts = _csv_env(
        "MCP_ALLOWED_HOSTS", "127.0.0.1:*,localhost:*,[::1]:*"
    )
    mcp.settings.transport_security.allowed_origins = _csv_env(
        "MCP_ALLOWED_ORIGINS", "http://127.0.0.1:*,http://localhost:*,http://[::1]:*"
    )
    app = mcp.streamable_http_app()
    app.add_middleware(ApiKeyAuthMiddleware)
    return app


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("MCP_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_PORT", "8001"))
    api_key_configured = bool(os.getenv("MCP_API_KEY", "").strip())

    print(f"Starting Video Retrieval MCP HTTP Server on {host}:{port}/mcp")
    print(f"Auth: {'API Key enabled' if api_key_configured else 'Disabled (Local only)'}")
    print("Mode: READ-ONLY (DRES submission is not exposed)")

    uvicorn.run(create_app(), host=host, port=port)
