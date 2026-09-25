"""Integration test for MCP Streamable HTTP endpoint and authentication."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from starlette.testclient import TestClient  # noqa: E402
from tools.run_mcp_http import create_app  # noqa: E402


def test_mcp_http():
    # Configure test API key
    test_key = "test-secret-key-456"
    os.environ["MCP_API_KEY"] = test_key

    app = create_app()

    with TestClient(app, base_url="http://127.0.0.1:8001") as client:
        # 1. Health check (no auth needed)
        res_health = client.get("/health")
        assert res_health.status_code == 200, f"Health check failed: {res_health.status_code}"
        assert res_health.json().get("status") == "ok"
        print("PASS: Health check (/health)")

        # 2. Unauthorized request (missing token)
        res_no_auth = client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "initialize"},
            headers={"Accept": "application/json"},
        )
        assert res_no_auth.status_code == 401, f"Expected 401, got {res_no_auth.status_code}"
        print("PASS: Auth check (missing token rejected with 401)")

        # 3. Unauthorized request (wrong token)
        res_bad_auth = client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "initialize"},
            headers={"Accept": "application/json", "Authorization": "Bearer wrong-key"},
        )
        assert res_bad_auth.status_code == 401, f"Expected 401, got {res_bad_auth.status_code}"
        print("PASS: Auth check (wrong token rejected with 401)")

        # 4. Valid initialize with Bearer auth
        auth_headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {test_key}",
            "Host": "127.0.0.1:8001",
        }
        init_req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0.0"},
            },
        }
        res_init = client.post("/mcp", json=init_req, headers=auth_headers)
        assert res_init.status_code == 200, f"Initialize failed: {res_init.text}"
        print("PASS: MCP initialize (200 OK)")

        # 5. tools/list
        tools_req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        res_tools = client.post("/mcp", json=tools_req, headers=auth_headers)
        assert res_tools.status_code == 200, f"tools/list failed: {res_tools.text}"
        tools = res_tools.json().get("result", {}).get("tools", [])
        assert len(tools) == 10, f"Expected 10 tools, got {len(tools)}"
        tool_names = {t["name"] for t in tools}
        assert "inspect_vision_probe" in tool_names
        assert "search_traffic_camera" in tool_names
        assert "inspect_candidate_grid" in tool_names
        print(f"PASS: tools/list (found all {len(tools)} tools)")

        # 6. tools/call inspect_vision_probe
        call_req = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "inspect_vision_probe", "arguments": {"variant": "probe_a"}},
        }
        res_call = client.post("/mcp", json=call_req, headers=auth_headers)
        assert res_call.status_code == 200, f"tools/call failed: {res_call.text}"
        content = res_call.json().get("result", {}).get("content", [])
        assert len(content) > 0 and content[0].get("type") == "image"
        print(f"PASS: tools/call inspect_vision_probe (returned {content[0]['mimeType']} image)")

    print("\nAll MCP HTTP test assertions passed successfully!")


if __name__ == "__main__":
    test_mcp_http()
