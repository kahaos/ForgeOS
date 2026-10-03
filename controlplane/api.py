"""Thin JSON API adapter for the ForgeOS Control Plane.

This module deliberately contains no authorization policy. It translates HTTP-like
requests into the existing ControlPlane request/decision lifecycle.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit

from .store import ControlPlane


class ApprovalAPI:
    """Expose the ControlPlane approval lifecycle as deterministic JSON responses."""

    def __init__(self, controlplane: ControlPlane) -> None:
        self.controlplane = controlplane

    def handle(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
    ) -> tuple[int, dict[str, Any] | list[dict[str, Any]]]:
        method = method.upper()
        route = urlsplit(path).path.rstrip("/") or "/"
        payload = body if body is not None else {}

        if route == "/approvals/request":
            if method != "POST":
                return 405, {"error": "method not allowed"}
            return self._request(payload)

        if route == "/approvals/pending":
            if method != "GET":
                return 405, {"error": "method not allowed"}
            return 200, self.controlplane.pending()

        if route.startswith("/approvals/"):
            remainder = route[len("/approvals/") :]
            parts = remainder.split("/")
            if len(parts) == 1 and parts[0]:
                if method != "GET":
                    return 405, {"error": "method not allowed"}
                return self._detail(parts[0])
            if len(parts) == 2 and parts[0] and parts[1] in {"approve", "deny"}:
                if method != "POST":
                    return 405, {"error": "method not allowed"}
                return self._decide(parts[0], parts[1], payload)

        return 404, {"error": "not found"}

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

        result = self.controlplane.request(
            payload["agent_id"],
            payload["tool"],
            payload["action"],
            target=target,
            detail=detail,
        )
        verdict = result.get("verdict")
        if verdict == "ask":
            return 202, result
        if verdict == "deny":
            return 403, result
        return 200, result

    def _detail(self, approval_id: str) -> tuple[int, dict[str, Any]]:
        record = self.controlplane.approvals.get(approval_id)
        if record is None:
            return 404, {"error": "approval not found"}
        return 200, dict(record)

    def _decide(
        self,
        approval_id: str,
        decision: str,
        payload: dict[str, Any],
    ) -> tuple[int, dict[str, Any]]:
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
            result = self.controlplane.decide(
                approval_id,
                approve=decision == "approve",
                actor=actor,
                execute=False,
            )
        except KeyError:
            return 409, {"error": "no pending approval"}
        except ValueError:
            return 409, {"error": "approval binding rejected"}
        return 200, result
