"""In-memory + JSON file control plane. Tools are simulated; the gate is real."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from .evidence import EvidenceLog
from .models import ActionRequest, Agent
from .policy import evaluate


class ControlPlane:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.agents_path = self.root / "agents.json"
        self.approvals_path = self.root / "approvals.json"
        self.evidence = EvidenceLog(self.root / "evidence.jsonl")
        self.agents: dict[str, Agent] = {}
        self.approvals: dict[str, dict[str, Any]] = {}
        self._load()

    def register(self, agent_id: str, owner: str, capabilities: list[str], risk_level: str = "medium") -> Agent:
        agent = Agent(agent_id, owner, capabilities, risk_level)
        self.agents[agent_id] = agent
        self._save()
        self.evidence.append("agent.registered", agent.to_dict())
        return agent

    def request(self, agent_id: str, tool: str, action: str, target: str = "", detail: dict | None = None) -> dict[str, Any]:
        if agent_id not in self.agents:
            event = self.evidence.append("action.denied", {"agent_id": agent_id, "reason": "unknown agent"})
            return {"verdict": "deny", "reason": "unknown agent", "evidence": event["digest"]}
        agent = self.agents[agent_id]
        req = ActionRequest(agent_id, tool, action, target, detail or {})
        decision = evaluate(agent, req)
        if decision.verdict == "allow":
            result = self._execute(req)
            event = self.evidence.append("action.allowed", {"request": req.to_dict(), "result": result, "reason": decision.reason})
            return {"verdict": "allow", "reason": decision.reason, "result": result, "evidence": event["digest"]}
        if decision.verdict == "deny":
            event = self.evidence.append("action.denied", {"request": req.to_dict(), "reason": decision.reason})
            return {"verdict": "deny", "reason": decision.reason, "evidence": event["digest"]}
        approval_id = "apr_" + uuid.uuid4().hex[:8]
        record = {"id": approval_id, "status": "pending", "request": req.to_dict(), "reason": decision.reason}
        self.approvals[approval_id] = record
        self._save()
        event = self.evidence.append("approval.requested", record)
        return {"verdict": "ask", "reason": decision.reason, "approval_id": approval_id, "evidence": event["digest"]}

    def decide(self, approval_id: str, approve: bool, actor: str = "human") -> dict[str, Any]:
        record = self.approvals.get(approval_id)
        if not record or record["status"] != "pending":
            raise KeyError(f"no pending approval {approval_id}")
        record["status"] = "approved" if approve else "denied"
        record["actor"] = actor
        self._save()
        if not approve:
            event = self.evidence.append("approval.denied", record)
            return {"verdict": "deny", "reason": "human denied", "evidence": event["digest"]}
        req = ActionRequest(**record["request"])
        result = self._execute(req)
        event = self.evidence.append("approval.granted", {"approval": record, "result": result})
        return {"verdict": "allow", "reason": "human approved", "result": result, "evidence": event["digest"]}

    def pending(self) -> list[dict[str, Any]]:
        return [a for a in self.approvals.values() if a["status"] == "pending"]

    def snapshot(self) -> dict[str, Any]:
        events = self.evidence.all()
        return {"agents": [a.to_dict() for a in self.agents.values()], "pending": self.pending(), "evidence_ok": self.evidence.verify(), "events": len(events), "recent": events[-8:]}

    def _execute(self, req: ActionRequest) -> dict[str, Any]:
        return {"tool": req.tool, "action": req.action, "target": req.target, "status": "completed"}

    def _load(self) -> None:
        if self.agents_path.exists():
            raw = json.loads(self.agents_path.read_text())
            self.agents = {k: Agent(**v) for k, v in raw.items()}
        if self.approvals_path.exists():
            self.approvals = json.loads(self.approvals_path.read_text())

    def _save(self) -> None:
        self.agents_path.write_text(json.dumps({k: v.to_dict() for k, v in self.agents.items()}, indent=2) + "\n")
        self.approvals_path.write_text(json.dumps(self.approvals, indent=2) + "\n")
