"""In-memory + JSON file control plane. Tools are simulated; the gate is real."""

from __future__ import annotations

import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .approval import agent_snapshot, request_digest
from .evidence import EvidenceLog
from .models import ActionRequest, Agent
from .policy import POLICY_VERSION, evaluate


Executor = Callable[[ActionRequest], dict[str, Any]]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ControlPlane:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.agents_path = self.root / "agents.json"
        self.approvals_path = self.root / "approvals.json"
        self.executors_path = self.root / "executors.json"
        self.execution_nonces_path = self.root / "execution_nonces.json"
        self.execution_nonces_lock_path = self.root / "execution_nonces.lock"
        self.evidence = EvidenceLog(self.root / "evidence.jsonl")
        self.agents: dict[str, Agent] = {}
        self.approvals: dict[str, dict[str, Any]] = {}
        self.executors: dict[str, dict[str, str]] = {}
        self._execution_nonces: set[str] = set()
        self._approval_executors: dict[str, Executor] = {}
        self._load()

    def register(self, agent_id: str, owner: str, capabilities: list[str], risk_level: str = "medium") -> Agent:
        agent = Agent(agent_id, owner, capabilities, risk_level)
        self.agents[agent_id] = agent
        self._save()
        self.evidence.append("agent.registered", agent.to_dict())
        return agent

    def register_executor(self, executor_id: str, target: str) -> dict[str, str]:
        if not executor_id or not target:
            raise ValueError("executor_id and target are required")
        existing = self.executors.get(executor_id)
        if existing is not None and existing["target"] != target:
            raise ValueError("executor binding target mismatch")
        binding = {"executor_id": executor_id, "target": target}
        self.executors[executor_id] = binding
        self._save()
        return binding

    def request(
        self,
        agent_id: str,
        tool: str,
        action: str,
        target: str = "",
        detail: dict | None = None,
        executor: Executor | None = None,
        executor_id: str | None = None,
    ) -> dict[str, Any]:
        if agent_id not in self.agents:
            event = self.evidence.append("action.denied", {"agent_id": agent_id, "reason": "unknown agent"})
            return {"verdict": "deny", "reason": "unknown agent", "evidence": event["digest"]}

        agent = self.agents[agent_id]
        req = ActionRequest(agent_id, tool, action, target, detail or {})
        decision = evaluate(agent, req)

        if decision.verdict == "allow":
            result = executor(req) if executor is not None else self._execute(req)
            event = self.evidence.append("action.allowed", {"request": req.to_dict(), "result": result, "reason": decision.reason})
            return {"verdict": "allow", "reason": decision.reason, "result": result, "evidence": event["digest"]}

        if decision.verdict == "deny":
            event = self.evidence.append("action.denied", {"request": req.to_dict(), "reason": decision.reason})
            return {"verdict": "deny", "reason": decision.reason, "evidence": event["digest"]}

        approval_id = "apr_" + uuid.uuid4().hex[:8]
        binding_id = "exec_" + uuid.uuid4().hex[:12]
        bound_executor = executor or self._execute
        resolved_executor_id = executor_id or f"{tool}:{action}"
        if executor_id is not None:
            self.register_executor(executor_id, target)
        record = {
            "id": approval_id,
            "status": "pending",
            "request": req.to_dict(),
            "request_digest": request_digest(req),
            "agent_snapshot": agent_snapshot(agent),
            "policy_version": POLICY_VERSION,
            "created_at": _now(),
            "reason": decision.reason,
            "execution_binding_id": binding_id,
            "executor_id": resolved_executor_id,
        }
        self.approvals[approval_id] = record
        self._approval_executors[approval_id] = bound_executor
        self._save()
        event = self.evidence.append("approval.requested", self._evidence_payload(record))
        return {"verdict": "ask", "reason": decision.reason, "approval_id": approval_id, "request_digest": record["request_digest"], "evidence": event["digest"]}

    def decide(
        self,
        approval_id: str,
        approve: bool,
        actor: str = "human",
        executor: Executor | None = None,
        execute: bool = True,
    ) -> dict[str, Any]:
        record = self.approvals.get(approval_id)
        if not record or record["status"] != "pending":
            raise KeyError(f"no pending approval {approval_id}")

        self._validate_binding(record)
        bound_executor = self._approval_executors.get(approval_id)
        if executor is not None and bound_executor is not executor:
            raise ValueError("executor binding mismatch")
        if approve and execute and bound_executor is None:
            raise ValueError("executor binding unavailable")

        record["actor"] = actor
        record["decided_at"] = _now()

        if not approve:
            record["status"] = "denied"
            self._save()
            event = self.evidence.append("approval.denied", self._evidence_payload(record))
            return {"verdict": "deny", "reason": "human denied", "evidence": event["digest"]}

        record["status"] = "approved"
        self._save()
        approved_payload = self._evidence_payload(record)
        approved_event = self.evidence.append("approval.approved", approved_payload)
        self.evidence.append("approval.granted", approved_payload)

        if not execute:
            return {
                "verdict": "allow",
                "reason": "human approved",
                "approval_id": approval_id,
                "request_digest": record["request_digest"],
                "approval_evidence": approved_event["digest"],
            }

        req = ActionRequest(**record["request"])
        try:
            result = bound_executor(req)
        except Exception as exc:
            record["status"] = "failed"
            record["error"] = str(exc)
            self._save()
            self.evidence.append("approval.execution_failed", {**self._evidence_payload(record), "error": str(exc)})
            raise

        return self.complete_approved_execution(approval_id, result)

    def complete_approved_execution(self, approval_id: str, result: dict[str, Any]) -> dict[str, Any]:
        record = self.approvals.get(approval_id)
        if not record or record["status"] != "approved":
            raise KeyError(f"no approved execution {approval_id}")
        record["status"] = "completed"
        self._save()
        executed_event = self.evidence.append(
            "approval.executed",
            {**self._evidence_payload(record), "result": result},
        )
        return {
            "verdict": "allow",
            "reason": "human approved",
            "result": result,
            "approval_id": approval_id,
            "request_digest": record["request_digest"],
            "evidence": executed_event["digest"],
        }

    def consume_execution_nonce(self, nonce: str) -> bool:
        if not nonce:
            raise ValueError("execution nonce is required")
        try:
            import fcntl
        except ImportError:  # pragma: no cover - Windows fallback
            fcntl = None

        self.execution_nonces_lock_path.touch(exist_ok=True)
        with self.execution_nonces_lock_path.open("r+") as lock:
            if fcntl is not None:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                current = set(json.loads(self.execution_nonces_path.read_text())) if self.execution_nonces_path.exists() else set()
                if nonce in current:
                    self._execution_nonces = current
                    return False
                current.add(nonce)
                self._atomic_write_json(self.execution_nonces_path, sorted(current))
                self._execution_nonces = current
                return True
            finally:
                if fcntl is not None:
                    fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    def pending(self) -> list[dict[str, Any]]:
        return [a for a in self.approvals.values() if a["status"] == "pending"]

    def snapshot(self) -> dict[str, Any]:
        events = self.evidence.all()
        return {"agents": [a.to_dict() for a in self.agents.values()], "pending": self.pending(), "evidence_ok": self.evidence.verify(), "events": len(events), "recent": events[-8:]}

    def _validate_binding(self, record: dict[str, Any]) -> None:
        request = ActionRequest(**record["request"])
        if request_digest(request) != record["request_digest"]:
            raise ValueError("approval request digest mismatch")
        agent = self.agents.get(request.agent_id)
        if agent is None or agent_snapshot(agent) != record["agent_snapshot"]:
            raise ValueError("approval agent snapshot mismatch")
        if record["policy_version"] != POLICY_VERSION:
            raise ValueError("approval policy version mismatch")
        if not str(record.get("execution_binding_id", "")).startswith("exec_"):
            raise ValueError("approval execution binding mismatch")

    @staticmethod
    def _evidence_payload(record: dict[str, Any]) -> dict[str, Any]:
        return {"approval_id": record["id"], "request_digest": record["request_digest"], "request": record["request"], "agent_snapshot": record["agent_snapshot"], "policy_version": record["policy_version"], "status": record["status"], "actor": record.get("actor"), "created_at": record["created_at"], "decided_at": record.get("decided_at")}

    def _execute(self, req: ActionRequest) -> dict[str, Any]:
        return {"tool": req.tool, "action": req.action, "target": req.target, "status": "completed"}

    def _load(self) -> None:
        if self.agents_path.exists():
            raw = json.loads(self.agents_path.read_text())
            self.agents = {k: Agent(**v) for k, v in raw.items()}
        if self.approvals_path.exists():
            self.approvals = json.loads(self.approvals_path.read_text())
        if self.executors_path.exists():
            self.executors = json.loads(self.executors_path.read_text())
        if self.execution_nonces_path.exists():
            self._execution_nonces = set(json.loads(self.execution_nonces_path.read_text()))

    def _save(self) -> None:
        self._atomic_write_json(self.agents_path, {k: v.to_dict() for k, v in self.agents.items()})
        self._atomic_write_json(self.approvals_path, self.approvals)
        self._atomic_write_json(self.executors_path, self.executors)

    @staticmethod
    def _atomic_write_json(path: Path, value: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp_path = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        try:
            with os.fdopen(fd, "w") as handle:
                handle.write(json.dumps(value, indent=2) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, path)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
