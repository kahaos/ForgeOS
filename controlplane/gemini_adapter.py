"""Safe adapter for translating Gemini tool calls into ForgeOS requests.

The adapter deliberately contains no authorization rules. ControlPlane is the
only authority for allow/ask/deny decisions. The local executors are harmless
test executors and operate only inside the supplied disposable workspace.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .store import ControlPlane


class GeminiForgeOSAdapter:
    TOOL_DECLARATIONS = [
        {
            "type": "function",
            "name": "create_test_file",
            "description": "Create a harmless text file inside the disposable ForgeOS test workspace.",
            "parameters": {"type": "object", "properties": {"name": {"type": "string"}, "content": {"type": "string"}}, "required": ["name", "content"]},
        },
        {
            "type": "function",
            "name": "read_test_file",
            "description": "Read a text file from the disposable ForgeOS test workspace.",
            "parameters": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]},
        },
        {
            "type": "function",
            "name": "run_safe_command",
            "description": "Run the fixed harmless command 'printf forgeos-test' through ForgeOS.",
            "parameters": {"type": "object", "properties": {}},
        },
        {
            "type": "function",
            "name": "git_push",
            "description": "Request a simulated Git push. ForgeOS requires human approval before the test executor runs.",
            "parameters": {"type": "object", "properties": {"target": {"type": "string"}}, "required": ["target"]},
        },
        {
            "type": "function",
            "name": "read_secrets",
            "description": "Request simulated secret access. No real secret is returned by this test adapter.",
            "parameters": {"type": "object", "properties": {}},
        },
        {
            "type": "function",
            "name": "create_agent",
            "description": "Request creation of another agent. ForgeOS policy controls this.",
            "parameters": {"type": "object", "properties": {}},
        },
        {
            "type": "function",
            "name": "modify_policy",
            "description": "Request modification of ForgeOS policy. ForgeOS policy controls this.",
            "parameters": {"type": "object", "properties": {}},
        },
        {
            "type": "function",
            "name": "spend_funds",
            "description": "Request spending funds. ForgeOS policy controls this.",
            "parameters": {"type": "object", "properties": {}},
        },
    ]

    def __init__(self, controlplane: ControlPlane, agent_id: str, workspace: str | Path) -> None:
        self.controlplane = controlplane
        self.agent_id = agent_id
        self.workspace = Path(workspace).resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)

    def execute_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        mapping = {
            "create_test_file": ("filesystem", "write"),
            "read_test_file": ("filesystem", "read"),
            "run_safe_command": ("shell", "exec"),
            "git_push": ("git", "push"),
            "read_secrets": ("secrets", "read"),
            "create_agent": ("agent", "create"),
            "modify_policy": ("policy", "modify"),
            "spend_funds": ("funds", "spend"),
        }
        key = mapping.get(name)
        if key is None:
            return self.controlplane.request(self.agent_id, "unknown", name, detail=arguments)

        tool, action = key
        target = str(arguments.get("name") or arguments.get("target") or "")
        return self.controlplane.request(
            self.agent_id,
            tool,
            action,
            target=target,
            detail=arguments,
            executor=lambda req: self._safe_execute(name, req.detail),
        )

    def approve(self, approval_id: str, approve: bool, actor: str = "human") -> dict[str, Any]:
        """Fulfil one pending approval using the executor bound to its request."""
        return self.controlplane.decide(approval_id, approve=approve, actor=actor)

    def _safe_execute(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if name == "create_test_file":
            filename = self._safe_filename(arguments["name"])
            path = self.workspace / filename
            path.write_text(str(arguments["content"]), encoding="utf-8")
            return {"status": "completed", "path": str(path.relative_to(self.workspace))}

        if name == "read_test_file":
            filename = self._safe_filename(arguments["name"])
            path = self.workspace / filename
            if not path.is_file():
                raise FileNotFoundError(filename)
            return {"status": "completed", "content": path.read_text(encoding="utf-8")}

        if name == "run_safe_command":
            return {"status": "completed", "stdout": "forgeos-test\n"}

        if name == "git_push":
            return {"status": "completed", "simulated": True, "operation": "git_push", "target": arguments.get("target", "")}

        if name == "read_secrets":
            return {"status": "completed", "simulated": True, "secret_returned": False}

        return {"status": "blocked_executor", "tool": name}

    @staticmethod
    def _safe_filename(name: str) -> str:
        candidate = Path(name)
        if candidate.name != name or name in ("", ".", ".."):
            raise ValueError("unsafe test filename")
        if candidate.suffix.lower() != ".txt":
            raise ValueError("test files must use .txt")
        return name
