"""Narrow MCP-compatible tool bridge for real autonomous agents.

The bridge deliberately contains no generic shell or direct provider access. It
binds every tool call to one ForgeOS task and agent, then delegates authorization
and execution to the existing RuntimeGateway.
"""

from __future__ import annotations

import json
import sys
from typing import Any, TextIO

from .gateway import RuntimeGateway


class ForgeOSMCPServer:
    """Expose only explicitly governed ForgeOS operations to an agent."""

    TOOL_NAMES = frozenset(
        {
            "read_file",
            "forgeos_write_file",
            "run_test",
            "git_status",
            "git_commit",
            "git_push",
            "request_action",
        }
    )

    TOOL_SCHEMAS: dict[str, dict[str, Any]] = {
        "read_file": {
            "description": "Read a file through ForgeOS policy.",
            "inputSchema": {"type": "object", "properties": {"workspace": {"type": "string"}, "path": {"type": "string"}}, "required": ["workspace", "path"]},
        },
        "forgeos_write_file": {
            "description": "Write a file through ForgeOS policy.",
            "inputSchema": {"type": "object", "properties": {"name": {"type": "string"}, "content": {"type": "string"}}, "required": ["name", "content"]},
        },
        "run_test": {
            "description": "Run a governed test operation in a workspace.",
            "inputSchema": {"type": "object", "properties": {"workspace": {"type": "string"}, "command": {"type": "string"}}, "required": ["workspace"]},
        },
        "git_status": {
            "description": "Inspect Git status through ForgeOS policy.",
            "inputSchema": {"type": "object", "properties": {"repository": {"type": "string"}}, "required": ["repository"]},
        },
        "git_commit": {
            "description": "Create a Git commit through ForgeOS policy.",
            "inputSchema": {"type": "object", "properties": {"repository": {"type": "string"}, "message": {"type": "string"}}, "required": ["repository", "message"]},
        },
        "git_push": {
            "description": "Push a Git branch through ForgeOS policy.",
            "inputSchema": {"type": "object", "properties": {"repository": {"type": "string"}, "branch": {"type": "string"}}, "required": ["repository", "branch"]},
        },
        "request_action": {
            "description": "Request another explicitly registered ForgeOS action; policy decides allow, ask, or deny.",
            "inputSchema": {"type": "object", "properties": {"tool": {"type": "string"}, "action": {"type": "string"}, "target": {"type": "string"}, "detail": {"type": "object"}}, "required": ["tool", "action", "target"]},
        },
    }

    def __init__(self, gateway: RuntimeGateway, task_id: str, agent_id: str, workspace: str | None = None) -> None:
        if not task_id or not agent_id:
            raise ValueError("task_id and agent_id are required")
        self.gateway = gateway
        self.task_id = task_id
        self.agent_id = agent_id
        self.workspace = workspace

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
        return self._request(arguments, tool="filesystem", action="read", target_key="workspace", executor_id="filesystem:read", required=("workspace", "path"))

    def _tool_forgeos_write_file(self, arguments: dict[str, Any]) -> dict[str, Any]:
        bound = dict(arguments)
        if self.workspace:
            bound["workspace"] = self.workspace
        elif "workspace" not in bound:
            raise ValueError("workspace is required for forgeos_write_file")
        return self._request(
            bound,
            tool="filesystem",
            action="write",
            target_key="workspace",
            executor_id="filesystem:write",
            required=("workspace", "name", "content"),
        )

    def _tool_run_test(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return self._request(arguments, tool="test", action="run", target_key="workspace", executor_id="test:run", required=("workspace",))

    def _tool_git_status(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return self._request(arguments, tool="git", action="status", target_key="repository", executor_id="git:status", required=("repository",))

    def _tool_git_commit(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return self._request(arguments, tool="git", action="commit", target_key="repository", executor_id="git:commit", required=("repository", "message"))

    def _tool_git_push(self, arguments: dict[str, Any]) -> dict[str, Any]:
        return self._request(arguments, tool="git", action="push", target_key="repository", executor_id="git:push", required=("repository", "branch"))

    def _tool_request_action(self, arguments: dict[str, Any]) -> dict[str, Any]:
        self._require(arguments, "tool", "action", "target")
        detail = dict(arguments.get("detail") or {})
        for key, value in arguments.items():
            if key not in {"tool", "action", "target", "detail"}:
                detail.setdefault(key, value)
        return self.gateway.request(self.task_id, self.agent_id, str(arguments["tool"]), str(arguments["action"]), str(arguments["target"]), detail, executor_id=f"{arguments['tool']}:{arguments['action']}")


class MCPStdioServer:
    """Minimal JSON-RPC stdio transport for MCP hosts such as Gemini CLI."""

    PROTOCOL_VERSION = "2025-06-18"

    def __init__(self, server: ForgeOSMCPServer) -> None:
        self.server = server

    def handle(self, message: dict[str, Any]) -> dict[str, Any] | None:
        """Handle one JSON-RPC request or notification without executing protocol errors."""
        request_id = message.get("id")
        method = message.get("method")
        params = message.get("params") or {}

        if message.get("jsonrpc") != "2.0" or not isinstance(method, str):
            return self._error(request_id, -32600, "invalid request")

        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": self.PROTOCOL_VERSION,
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "forgeos-control-plane", "version": "0.1.0"},
                },
            }

        if method == "notifications/initialized":
            # JSON-RPC notifications must not receive a response.
            return None

        if method == "ping":
            return {"jsonrpc": "2.0", "id": request_id, "result": {}}

        if method == "tools/list":
            tools = [
                {"name": name, **self.server.TOOL_SCHEMAS[name]}
                for name in sorted(self.server.TOOL_NAMES)
            ]
            return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": tools}}

        if method == "tools/call":
            if not isinstance(params, dict):
                return self._tool_error(request_id, "invalid tools/call parameters")
            name = params.get("name")
            arguments = params.get("arguments", {})
            if not isinstance(name, str) or not isinstance(arguments, dict):
                return self._tool_error(request_id, "invalid tools/call parameters")
            try:
                result = self.server.call_tool(name, arguments)
            except (KeyError, TypeError, ValueError) as exc:
                return self._tool_error(request_id, str(exc))
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"content": [{"type": "text", "text": json.dumps(result, sort_keys=True)}], "isError": False},
            }

        return self._error(request_id, -32601, f"method not found: {method}")

    @staticmethod
    def _error(request_id: Any, code: int, message: str) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}

    @staticmethod
    def _tool_error(request_id: Any, message: str) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "result": {"content": [{"type": "text", "text": message}], "isError": True}}

    def serve(self, stdin: TextIO | None = None, stdout: TextIO | None = None) -> None:
        """Serve newline-delimited JSON-RPC messages; diagnostics never go to stdout."""
        stdin = stdin or sys.stdin
        stdout = stdout or sys.stdout
        for line in stdin:
            if not line.strip():
                continue
            try:
                message = json.loads(line)
                response = self.handle(message)
            except (json.JSONDecodeError, TypeError):
                response = self._error(None, -32700, "parse error")
            if response is not None:
                stdout.write(json.dumps(response, separators=(",", ":")) + "\n")
                stdout.flush()


__all__ = ["ForgeOSMCPServer", "MCPStdioServer"]
