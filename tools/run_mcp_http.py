"""Run the read-only video search MCP server over Streamable HTTP."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mcp_server import mcp  # noqa: E402


def _csv_env(name: str, default: str) -> list[str]:
    return [value.strip() for value in os.getenv(name, default).split(",") if value.strip()]


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("MCP_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_PORT", "8001"))
    mcp.settings.stateless_http = True
    mcp.settings.json_response = True
    mcp.settings.streamable_http_path = "/mcp"
    mcp.settings.transport_security.allowed_hosts = _csv_env(
        "MCP_ALLOWED_HOSTS", "127.0.0.1:*,localhost:*,[::1]:*"
    )
    mcp.settings.transport_security.allowed_origins = _csv_env(
        "MCP_ALLOWED_ORIGINS", "http://127.0.0.1:*,http://localhost:*,http://[::1]:*"
    )
    uvicorn.run(mcp.streamable_http_app(), host=host, port=port)
