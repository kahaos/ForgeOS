"""Provider-neutral runtime gateway for task-scoped agent actions."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Protocol

from .approval import agent_snapshot, request_digest
from .execution_worker import ExecutionAuthorizer, ExecutionWorker
from .models import ActionRequest
from .policy import POLICY_VERSION, evaluate_scoped
from .store import ControlPlane, Executor


class ToolAdapter(Protocol):
    def __call__(self, request: ActionRequest) -> dict[str, Any]: ...


class RuntimeGateway:
    """Route agent actions through the Control Plane and signed execution boundary."""

    def __init__(self, controlplane: ControlPlane, worker: ExecutionWorker, key: bytes) -> None:
        self.controlplane = controlplane
        self.worker = worker
        self.authorizer = ExecutionAuthorizer(controlplane, key)
        self.adapters: dict[str, tuple[str, ToolAdapter]] = {}

    def register_adapter(self, executor_id: str, target: str, adapter: ToolAdapter) -> None:
        self.worker.register_executor(executor_id, target, adapter)
        self.adapters[executor_id] = (target, adapter)

    def request(self, task_id: str, agent_id: str, tool: str, action: str, target: str, detail: dict[str, Any] | None = None, executor_id: str | None = None) -> dict[str, Any]:
        request = ActionRequest(agent_id, tool, action, target, detail or {})
        agent = self.controlplane.agents.get(agent_id)
        task = self.controlplane.tasks.get(task_id)
        grants = self.controlplane.effective_grants(task_id, agent_id) if task else []
        if agent is None:
            return {"verdict": "deny", "reason": "unknown agent", "task_id": task_id}
        decision = evaluate_scoped(agent, task, grants, request)
        if decision.verdict == "deny":
            return self.controlplane._scoped_denial(request, decision.reason, task_id)

        resolved_executor_id = executor_id or f"{tool}:{action}"
        adapter_entry = self.adapters.get(resolved_executor_id)
        if adapter_entry is None:
            return {"verdict": "deny", "reason": "unknown executor", "task_id": task_id, "grant_id": decision.grant_id}
        target_binding, _adapter = adapter_entry
        if target_binding != target:
            return {"verdict": "deny", "reason": "executor target mismatch", "task_id": task_id, "grant_id": decision.grant_id}

        if decision.verdict == "ask":
            return self.controlplane.request_scoped(
                task_id,
                agent_id,
                tool,
                action,
                target,
                detail,
                executor_id=resolved_executor_id,
            )

        grant = self.controlplane.grants[decision.grant_id]
        approval_id = "auto_" + uuid.uuid4().hex[:12]
        timestamp = datetime.now(timezone.utc).isoformat()
        record = {
            "id": approval_id,
            "status": "approved",
            "request": request.to_dict(),
            "request_digest": request_digest(request),
            "agent_snapshot": agent_snapshot(agent),
            "policy_version": POLICY_VERSION,
            "task_id": task_id,
            "grant_id": grant.grant_id,
            "grant_snapshot": grant.to_dict(),
            "created_at": timestamp,
            "reason": decision.reason,
            "actor": "policy",
            "decided_at": timestamp,
            "execution_binding_id": "exec_" + uuid.uuid4().hex[:12],
            "executor_id": resolved_executor_id,
        }
        self.controlplane.approvals[approval_id] = record
        self.controlplane._save()
        self.controlplane.evidence.append("scoped.approval.auto_granted", self.controlplane._evidence_payload(record))

        authorization = self.authorizer.issue(approval_id, resolved_executor_id)
        result = self.worker.execute(authorization)
        return {"verdict": "allow", "reason": decision.reason, "task_id": task_id, "grant_id": grant.grant_id, "authorization": authorization.to_dict(), "result": result}

    def approve_and_execute(self, approval_id: str, actor: str) -> dict[str, Any]:
        """Approve a scoped request, then execute only through signed authorization."""
        record = self.controlplane.approvals.get(approval_id)
        if record is None or record.get("status") != "pending":
            raise KeyError(f"no pending approval {approval_id}")
        if record.get("task_id") is None:
            raise ValueError("approve_and_execute only supports scoped approvals")

        self.controlplane.decide(approval_id, approve=True, actor=actor, execute=False)
        executor_id = record.get("executor_id")
        if not isinstance(executor_id, str) or not executor_id:
            raise ValueError("scoped executor binding unavailable")
        if executor_id not in self.adapters:
            raise ValueError("unknown executor")

        authorization = self.authorizer.issue(approval_id, executor_id)
        result = self.worker.execute(authorization)
        return {
            "verdict": "allow",
            "reason": "human approved",
            "approval_id": approval_id,
            "authorization": authorization.to_dict(),
            "result": result,
        }


class SimulatedToolAdapter:
    """Safe adapter useful for demos and tests."""

    def __init__(self, label: str = "simulated") -> None:
        self.label = label
        self.calls: list[dict[str, Any]] = []

    def __call__(self, request: ActionRequest) -> dict[str, Any]:
        self.calls.append(request.to_dict())
        return {"status": "completed", "simulated": True, "adapter": self.label, "target": request.target}


class GitHubAdapterBoundary:
    """Provider boundary; credentials stay in the provider adapter, not agent code."""

    def __init__(self, handler: Executor) -> None:
        self.handler = handler

    def __call__(self, request: ActionRequest) -> dict[str, Any]:
        return self.handler(request)


class HttpToolAdapterBoundary:
    """Generic HTTP/tool boundary for future provider-specific credential handling."""

    def __init__(self, handler: Executor) -> None:
        self.handler = handler

    def __call__(self, request: ActionRequest) -> dict[str, Any]:
        return self.handler(request)


class MCPToolAdapterBoundary:
    """MCP-oriented tool boundary; policy remains in the ForgeOS Control Plane."""

    def __init__(self, handler: Executor) -> None:
        self.handler = handler

    def __call__(self, request: ActionRequest) -> dict[str, Any]:
        return self.handler(request)