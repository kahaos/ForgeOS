"""Narrow MCP-compatible tool bridge for real autonomous agents.

The bridge deliberately contains no generic shell or direct provider access. It
binds every tool call to one ForgeOS task and agent, then delegates authorization
and execution to the existing RuntimeGateway.
"""

from __future__ import annotations

from typing import Any, Callable

from .gateway import RuntimeGateway


class ForgeOSMCPServer:
    """Expose only explicitly governed ForgeOS operations to an agent."""

    TOOL_NAMES = frozenset(
        {
            "read_file",
            "write_file",
            "run_test",
            "git_status",
            "git_commit",
            "git_push",
            "request_action",
        }
    )

    def __init__(self, gateway: RuntimeGateway, task_id: str, agent_id: str) -> None:
        if not task_id or not agent_id:
            raise ValueError("task_id and agent_id are required")
        self.gateway = gateway
        self.task_id = task_id
        self.agent_id = agent_id

    def list_tools(self) -> set[str]:
        """Return the fixed, intentionally narrow agent-facing tool surface."""
        return set(self.TOOL_NAMES)

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Translate one MCP-style call into a governed RuntimeGateway request."""
        if name not in self.TOOL_NAMES:
            raise ValueError(f"unknown MCP tool: {name}")
        if not isinstance(arguments, dict):
            raise ValueError("MCP tool arguments must be an object")

        handler = getattr(self, f"_tool_{name}")
        return handler(arguments)

    def _request(
        self,
        arguments: dict[str, Any],
        *,
        tool: str,
        action: str,
        target_key: str,
        executor_id: str | None = None,
        required: tuple[str, ...] = (),
    ) -> dict[str, Any]:
        self._require(arguments, *required)
        target = str(arguments[target_key])
        return self.gateway.request(
            self.task_id,
            self.agent_id,
            tool,
            action,
            target,
            dict(arguments),
            executor_id=executor_id,
        )

    @staticmethod
    def _require(arguments: dict[str, Any], *keys: str) -> None:
        missing = [key for key in keys if key not in arguments]
        if missing:
            raise ValueError(f"missing MCP arguments: {', '.join(missing)}")

    def _tool_read_file(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return self._request(
            arguments,
            tool="filesystem",
            action="read",
            target_key="workspace",
            executor_id="filesystem:read",
            required=("workspace", "path"),
        )

    def _tool_write_file(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return self._request(
            arguments,
            tool="filesystem",
            action="write",
            target_key="workspace",
            executor_id="filesystem:write",
            required=("workspace", "name", "content"),
        )

    def _tool_run_test(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return self._request(
            arguments,
            tool="test",
            action="run",
            target_key="workspace",
            executor_id="test:run",
            required=("workspace",),
        )

    def _tool_git_status(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return self._request(
            arguments,
            tool="git",
            action="status",
            target_key="repository",
            executor_id="git:status",
            required=("repository",),
        )

    def _tool_git_commit(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return self._request(
            arguments,
            tool="git",
            action="commit",
            target_key="repository",
            executor_id="git:commit",
            required=("repository", "message"),
        )

    def _tool_git_push(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return self._request(
            arguments,
            tool="git",
            action="push",
            target_key="repository",
            executor_id="git:push",
            required=("repository", "branch"),
        )

    def _tool_request_action(self, arguments: dict[str, Any]) -> dict[str, Any]:
        self._require(arguments, "tool", "action", "target")
        detail = dict(arguments.get("detail") or {})
        for key, value in arguments.items():
            if key not in {"tool", "action", "target", "detail"}:
                detail.setdefault(key, value)
        return self.gateway.request(
            self.task_id,
            self.agent_id,
            str(arguments["tool"]),
            str(arguments["action"]),
            str(arguments["target"]),
            detail,
            executor_id=f"{arguments['tool']}:{arguments['action']}",
        )


__all__ = ["ForgeOSMCPServer"]
