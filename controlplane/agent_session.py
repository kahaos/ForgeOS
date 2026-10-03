"""Task- and agent-bound session facade for governed agent tool calls."""

from __future__ import annotations

from typing import Any

from .gateway import RuntimeGateway
from .mcp_server import ForgeOSMCPServer


class AgentSession:
    """Bind an autonomous agent session to one authoritative task and agent."""

    def __init__(self, gateway: RuntimeGateway, task_id: str, agent_id: str) -> None:
        if not task_id or not agent_id:
            raise ValueError("task_id and agent_id are required")
        self.gateway = gateway
        self.task_id = task_id
        self.agent_id = agent_id
        self.mcp = ForgeOSMCPServer(gateway, task_id, agent_id)

    def call(
        self,
        tool_name: str,
        target: str,
        secondary: str = "",
        *,
        task_id: str | None = None,
        agent_id: str | None = None,
        **arguments: Any,
    ) -> dict[str, Any]:
        """Call one governed agent tool without allowing identity rebinding."""
        if task_id is not None and task_id != self.task_id:
            raise ValueError("session task binding cannot be overridden")
        if agent_id is not None and agent_id != self.agent_id:
            raise ValueError("session agent binding cannot be overridden")

        if tool_name == "shell":
            raise ValueError("unknown agent tool: shell")

        if tool_name == "git_push":
            payload = {"repository": target, "branch": secondary, **arguments}
        elif tool_name == "request_action":
            payload = {
                "tool": arguments.pop("tool", ""),
                "action": secondary,
                "target": target,
                **arguments,
            }
        elif tool_name in {"read_file", "write_file", "run_test"}:
            payload = {"workspace": target, **arguments}
            if tool_name == "read_file" and secondary:
                payload.setdefault("path", secondary)
            elif tool_name == "write_file" and secondary:
                payload.setdefault("name", secondary)
        elif tool_name in {"git_status", "git_commit"}:
            payload = {"repository": target, **arguments}
            if tool_name == "git_commit" and secondary:
                payload.setdefault("message", secondary)
        else:
            raise ValueError(f"unknown agent tool: {tool_name}")

        return self.mcp.call_tool(tool_name, payload)


__all__ = ["AgentSession"]
