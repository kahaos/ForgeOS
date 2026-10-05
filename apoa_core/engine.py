"""Deterministic Apoa authorization engine.

This module intentionally contains no model-provider or tool-execution code.
It evaluates canonical requests and returns an authorization decision.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Iterable

from .models import Approval, Authorization, Decision, ExecutionRequest, Policy, PolicyRule


@dataclass(frozen=True)
class Evidence:
    request_id: str
    authorization_id: str
    decision: Decision
    reason: str
    timestamp: float
    agent: str
    action: str
    target: str
    policy: str
    policy_version: str


class ApoaEngine:
    """Small, provider-neutral policy enforcement core."""

    def __init__(self, policy: Policy, *, authorization_ttl: float = 60.0) -> None:
        self.policy = policy
        self.authorization_ttl = authorization_ttl
        self._used_nonces: set[str] = set()
        self._approvals: dict[str, Approval] = {}
        self._evidence: list[Evidence] = []

    def authorize(self, request: ExecutionRequest) -> Authorization:
        rule = self._find_rule(request.action)
        if rule is None:
            return self._record(request, Decision.DENY, "No policy rule permits this action")

        if rule.required_capability and rule.required_capability not in request.capabilities:
            return self._record(
                request,
                Decision.DENY,
                f"Missing capability: {rule.required_capability}",
            )

        if rule.allowed_targets and not self._matches(request.target, rule.allowed_targets):
            return self._record(request, Decision.DENY, "Target is outside policy scope")

        if rule.allowed_environments and request.environment not in rule.allowed_environments:
            return self._record(request, Decision.DENY, "Environment is outside policy scope")

        for name, maximum in rule.parameter_limits.items():
            value = request.parameters.get(name)
            if value is None:
                continue
            if not isinstance(value, (int, float)) or value > maximum:
                return self._record(
                    request,
                    Decision.DENY,
                    f"Parameter exceeds policy limit: {name} <= {maximum}",
                )

        if rule.decision is Decision.DENY:
            return self._record(request, Decision.DENY, "Action is explicitly denied by policy")

        if rule.required_approval or rule.decision is Decision.REQUIRE_APPROVAL:
            return self._record(request, Decision.REQUIRE_APPROVAL, "Human approval is required")

        return self._record(request, Decision.ALLOW, "Action satisfies policy")

    def approve(
        self,
        request: ExecutionRequest,
        approver: str,
        *,
        ttl: float = 300.0,
    ) -> Approval:
        approval = Approval(
            approval_id=f"apr_{uuid.uuid4().hex}",
            request_id=request.request_id,
            approver=approver,
            approved=True,
            expires_at=time.time() + ttl,
        )
        self._approvals[approval.approval_id] = approval
        return approval

    def issue_execution_authorization(
        self,
        request: ExecutionRequest,
        approval: Approval | None = None,
        *,
        ttl: float | None = None,
    ) -> Authorization:
        decision = self.authorize(request)

        if decision.decision is Decision.DENY:
            return decision

        if decision.requires_approval:
            if approval is None or not self._valid_approval(request, approval):
                return self._record(request, Decision.REQUIRE_APPROVAL, "Valid human approval required")

        nonce = f"nonce_{uuid.uuid4().hex}"
        expiry = time.time() + (self.authorization_ttl if ttl is None else ttl)
        authorization = Authorization(
            authorization_id=f"auth_{uuid.uuid4().hex}",
            request_id=request.request_id,
            decision=Decision.ALLOW,
            reason="Execution authorized",
            policy=self.policy.name,
            policy_version=self.policy.version,
            expires_at=expiry,
            nonce=nonce,
            approval_id=approval.approval_id if approval else None,
        )
        self._record_authorization(request, authorization)
        return authorization

    def consume(self, authorization: Authorization) -> bool:
        """Consume a short-lived execution authorization exactly once."""
        if not authorization.allowed or not authorization.nonce or authorization.expires_at is None:
            return False
        if time.time() >= authorization.expires_at:
            return False
        if authorization.nonce in self._used_nonces:
            return False
        self._used_nonces.add(authorization.nonce)
        return True

    def evidence(self) -> tuple[Evidence, ...]:
        return tuple(self._evidence)

    def _find_rule(self, action: str) -> PolicyRule | None:
        return next((rule for rule in self.policy.rules if rule.action == action), None)

    @staticmethod
    def _matches(target: str, allowed: Iterable[str]) -> bool:
        return any(target == pattern or target.startswith(pattern.rstrip("*") ) for pattern in allowed)

    @staticmethod
    def _valid_approval(request: ExecutionRequest, approval: Approval) -> bool:
        return (
            approval.approved
            and approval.request_id == request.request_id
            and approval.expires_at > time.time()
        )

    def _record(self, request: ExecutionRequest, decision: Decision, reason: str) -> Authorization:
        authorization = Authorization(
            authorization_id=f"auth_{uuid.uuid4().hex}",
            request_id=request.request_id,
            decision=decision,
            reason=reason,
            policy=self.policy.name,
            policy_version=self.policy.version,
        )
        self._record_authorization(request, authorization)
        return authorization

    def _record_authorization(self, request: ExecutionRequest, authorization: Authorization) -> None:
        self._evidence.append(
            Evidence(
                request_id=request.request_id,
                authorization_id=authorization.authorization_id,
                decision=authorization.decision,
                reason=authorization.reason,
                timestamp=time.time(),
                agent=request.agent,
                action=request.action,
                target=request.target,
                policy=self.policy.name,
                policy_version=self.policy.version,
            )
        )
