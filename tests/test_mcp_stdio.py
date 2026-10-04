from __future__ import annotations

import json
from pathlib import Path

from controlplane.mcp_server import ForgeOSMCPServer, MCPStdioServer
from examples.real_agent_trial import build_trial_controlplane


def test_stdio_lists_only_governed_tools(tmp_path: Path) -> None:
    _cp, gateway = build_trial_controlplane(tmp_path)
    server = MCPStdioServer(ForgeOSMCPServer(gateway, "real-agent-website-build", "website-agent"))

    response = server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})

    names = {tool["name"] for tool in response["result"]["tools"]}
    assert names == {
        "read_file",
        "forgeos_write_file",
        "run_test",
        "git_status",
        "git_commit",
        "git_push",
        "request_action",
    }
    assert "shell" not in names


def test_stdio_initialized_notification_has_no_response(tmp_path: Path) -> None:
    _cp, gateway = build_trial_controlplane(tmp_path)
    server = MCPStdioServer(
        ForgeOSMCPServer(gateway, "real-agent-website-build", "website-agent")
    )

    response = server.handle(
        {
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {},
        }
    )

    assert response is None


def test_stdio_tool_call_uses_bound_session(tmp_path: Path) -> None:
    _cp, gateway = build_trial_controlplane(tmp_path)
    server = MCPStdioServer(ForgeOSMCPServer(gateway, "real-agent-website-build", "website-agent"))

    response = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "git_push",
                "arguments": {"repository": "forgeos-agent-trial", "branch": "feature/home"},
            },
        }
    )

    payload = json.loads(response["result"]["content"][0]["text"])
    assert payload["verdict"] == "allow"
    assert payload["task_id"] == "real-agent-website-build"


def test_stdio_malformed_tool_call_fails_closed(tmp_path: Path) -> None:
    _cp, gateway = build_trial_controlplane(tmp_path)
    server = MCPStdioServer(ForgeOSMCPServer(gateway, "real-agent-website-build", "website-agent"))

    response = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {"name": "shell", "arguments": {}},
        }
    )

    assert response["result"]["isError"] is True
    assert "unknown MCP tool" in response["result"]["content"][0]["text"]
