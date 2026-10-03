"""Thin JSON API adapter for the ForgeOS Control Plane."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit

from .store import ControlPlane


class ApprovalAPI:
    """Translate API requests into the single ControlPlane authority lifecycle."""

    def __init__(self, controlplane: ControlPlane) -> None:
        self.controlplane = controlplane

    def handle(self, method: str, path: str, body: dict[str, Any] | None = None) -> tuple[int, dict[str, Any] | list[dict[str, Any]]]:
        method = method.upper()
        route = urlsplit(path).path.rstrip("/") or "/"
        payload = body if body is not None else {}

        if route == "/approvals/request":
            return self._method(method, "POST", lambda: self._request(payload))
        if route == "/scoped/request":
            return self._method(method, "POST", lambda: self._scoped_request(payload))
        if route == "/approvals/pending":
            return self._method(method, "GET", lambda: (200, self.controlplane.pending()))
        if route == "/tasks":
            return self._method(method, "POST", lambda: self._create_task(payload))
        if route == "/tasks/pending":
            return self._method(method, "GET", lambda: (200, [t.to_dict() for t in self.controlplane.tasks.values() if t.active()]))
        if route == "/authority/graph":
            return self._method(method, "GET", lambda: (200, self.controlplane.authority_graph()))
        if route.startswith("/tasks/"):
            return self._task_route(method, route[len("/tasks/"):], payload)
        if route.startswith("/agents/") and route.endswith("/authority"):
            return self._method(method, "GET", lambda: self._agent_authority(route[len("/agents/"):-len("/authority")].strip("/")))
        if route.startswith("/approvals/"):
            remainder = route[len("/approvals/"):]
            parts = remainder.split("/")
            if len(parts) == 1 and parts[0]:
                return self._method(method, "GET", lambda: self._detail(parts[0]))
            if len(parts) == 2 and parts[0] and parts[1] in {"approve", "deny"}:
                return self._method(method, "POST", lambda: self._decide(parts[0], parts[1], payload))
        return 404, {"error": "not found"}

    @staticmethod
    def _method(actual: str, expected: str, handler):
        if actual != expected:
            return 405, {"error": "method not allowed"}
        return handler()

    def _request(self, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        if not isinstance(payload, dict):
            return 400, {"error": "invalid request"}
        required = ("agent_id", "tool", "action")
        if any(not isinstance(payload.get(key), str) or not payload[key] for key in required):
            return 400, {"error": "invalid request"}
        target = payload.get("target", "")
        detail = payload.get("detail", {})
        if not isinstance(target, str) or not isinstance(detail, dict):
            return 400, {"error": "invalid request"}
        result = self.controlplane.request(payload["agent_id"], payload["tool"], payload["action"], target=target, detail=detail)
        return self._decision_status(result)

    def _scoped_request(self, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        if not isinstance(payload, dict):
            return 400, {"error": "invalid request"}
        required = ("task_id", "agent_id", "tool", "action", "target")
        if any(not isinstance(payload.get(key), str) or not payload[key] for key in required):
            return 400, {"error": "invalid request"}
        detail = payload.get("detail", {})
        if not isinstance(detail, dict):
            return 400, {"error": "invalid request"}
        result = self.controlplane.request_scoped(payload["task_id"], payload["agent_id"], payload["tool"], payload["action"], payload["target"], detail, executor_id=payload.get("executor_id"))
        return self._decision_status(result)

    def _create_task(self, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        required = ("task_id", "owner", "purpose", "expires_at")
        if not isinstance(payload, dict) or any(not isinstance(payload.get(k), str) or not payload[k] for k in required):
            return 400, {"error": "invalid request"}
        try:
            task = self.controlplane.create_task(payload["task_id"], payload["owner"], payload["purpose"], payload["expires_at"], payload.get("parent_task_id"), payload.get("human_context"))
        except (KeyError, ValueError):
            return 409, {"error": "task rejected"}
        return 201, task.to_dict()

    def _task_route(self, method: str, remainder: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any] | list[dict[str, Any]]]:
        parts = [p for p in remainder.split("/") if p]
        if len(parts) == 1 and method == "GET":
            task = self.controlplane.tasks.get(parts[0])
            return (200, task.to_dict()) if task else (404, {"error": "task not found"})
        if len(parts) == 2 and parts[1] == "revoke" and method == "POST":
            try:
                return 200, self.controlplane.revoke_task(parts[0], payload.get("actor", "human")).to_dict()
            except KeyError:
                return 404, {"error": "task not found"}
        if len(parts) == 2 and parts[1] == "grants" and method == "GET":
            return 200, [g.to_dict() for g in self.controlplane.grants.values() if g.task_id == parts[0]]
        if len(parts) == 2 and parts[1] == "grants" and method == "POST":
            required = ("agent_id", "capability", "scope", "issued_by", "expires_at")
            if not isinstance(payload, dict) or any(k not in payload for k in required):
                return 400, {"error": "invalid request"}
            try:
                grant = self.controlplane.issue_grant(parts[0], payload["agent_id"], payload["capability"], payload["scope"], payload["issued_by"], payload["expires_at"], payload.get("parent_grant_id"))
            except (KeyError, ValueError):
                return 409, {"error": "grant rejected"}
            return 201, grant.to_dict()
        return 404, {"error": "not found"}

    def _agent_authority(self, agent_id: str) -> tuple[int, dict[str, Any]]:
        if agent_id not in self.controlplane.agents:
            return 404, {"error": "agent not found"}
        grants = [g.to_dict() for g in self.controlplane.grants.values() if g.agent_id == agent_id]
        relationships = [r for r in self.controlplane.agent_relationships if r["child_agent_id"] == agent_id or r["parent_agent_id"] == agent_id]
        return 200, {"agent": self.controlplane.agents[agent_id].to_dict(), "grants": grants, "relationships": relationships}

    @staticmethod
    def _decision_status(result: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        verdict = result.get("verdict")
        if verdict == "ask":
            return 202, result
        if verdict == "deny":
            return 403, result
        return 200, result

    def _detail(self, approval_id: str) -> tuple[int, dict[str, Any]]:
        record = self.controlplane.approvals.get(approval_id)
        return (200, dict(record)) if record else (404, {"error": "approval not found"})

    def _decide(self, approval_id: str, decision: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        if not isinstance(payload, dict):
            return 400, {"error": "invalid request"}
        actor = payload.get("actor", "human")
        if not isinstance(actor, str) or not actor:
            return 400, {"error": "invalid request"}
        record = self.controlplane.approvals.get(approval_id)
        if record is None:
            return 404, {"error": "approval not found"}
        if record.get("status") != "pending":
            return 409, {"error": "no pending approval"}
        try:
            result = self.controlplane.decide(approval_id, approve=decision == "approve", actor=actor, execute=False)
        except (KeyError, ValueError):
            return 409, {"error": "approval binding rejected"}
        return 200, result
