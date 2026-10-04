from __future__ import annotations

from pathlib import Path

import pytest

from controlplane.mcp_server import ForgeOSMCPServer
from examples.real_agent_trial import build_trial_controlplane


def test_mcp_exposes_only_governed_tools(tmp_path: Path) -> None:
    _cp, gateway = build_trial_controlplane(tmp_path)
    server = ForgeOSMCPServer(gateway, "real-agent-website-build", "website-agent")

    assert server.list_tools() == {
        "read_file",
        "forgeos_write_file",
        "run_test",
        "git_status",
        "git_commit",
        "git_push",
        "request_action",
    }
    assert "shell" not in server.list_tools()
    assert "exec" not in server.list_tools()


def test_mcp_write_is_governed_by_task_scope(tmp_path: Path) -> None:
    _cp, gateway = build_trial_controlplane(tmp_path)
    server = ForgeOSMCPServer(gateway, "real-agent-website-build", "website-agent")

    result = server.call_tool(
        "forgeos_write_file",
        {"workspace": str(tmp_path), "name": "site.txt", "content": "hello"},
    )

    assert result["verdict"] == "allow"
    assert (tmp_path / "site.txt").read_text() == "hello"


def test_mcp_git_push_scope_escape_is_denied(tmp_path: Path) -> None:
    _cp, gateway = build_trial_controlplane(tmp_path)
    server = ForgeOSMCPServer(gateway, "real-agent-website-build", "website-agent")

    result = server.call_tool(
        "git_push",
        {"repository": "forgeos-agent-trial", "branch": "main"},
    )

    assert result["verdict"] == "deny"


def test_mcp_sensitive_action_requires_approval_and_does_not_execute(tmp_path: Path) -> None:
    _cp, gateway = build_trial_controlplane(tmp_path)
    server = ForgeOSMCPServer(gateway, "real-agent-website-build", "website-agent")

    result = server.call_tool("request_action", {"tool": "secrets", "action": "read", "target": "trial-secrets"})

    assert result["verdict"] == "ask"
    assert result["approval_id"]


def test_mcp_unknown_tool_fails_closed(tmp_path: Path) -> None:
    _cp, gateway = build_trial_controlplane(tmp_path)
    server = ForgeOSMCPServer(gateway, "real-agent-website-build", "website-agent")

    with pytest.raises(ValueError, match="unknown MCP tool"):
        server.call_tool("shell", {"command": "id"})
