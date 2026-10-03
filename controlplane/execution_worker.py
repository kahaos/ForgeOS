"""Cryptographically bound approval authorization and safe execution worker."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from .approval import agent_snapshot, request_digest
from .models import ActionRequest
from .policy import POLICY_VERSION
from .store import ControlPlane


Executor = Callable[[ActionRequest], dict[str, Any]]


def _canonical(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256(value: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class ExecutionAuthorization:
    approval_id: str
    request: dict[str, Any]
    request_digest: str
    agent_snapshot: dict[str, Any]
    agent_snapshot_digest: str
    policy_version: str
    executor_id: str
    target: str
    issued_at: str
    expires_at: str
    nonce: str
    signature: str

    def unsigned_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("signature", None)
        return data

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ExecutionAuthorizer:
    """Issue short-lived execution authorizations from approved requests."""

    def __init__(
        self,
        controlplane: ControlPlane,
        key: bytes,
        ttl_seconds: int = 60,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if not key:
            raise ValueError("execution authorization key is required")
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        self.controlplane = controlplane
        self.key = bytes(key)
        self.ttl_seconds = ttl_seconds
        self.clock = clock or _now

    def issue(self, approval_id: str, executor_id: str) -> ExecutionAuthorization:
        record = self.controlplane.approvals.get(approval_id)
        if not record or record.get("status") != "approved":
            raise ValueError("approval is not approved")

        try:
            self.controlplane._validate_binding(record)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc

        binding = self.controlplane.executors.get(executor_id)
        if binding is None:
            raise ValueError("executor binding unavailable")
        if record.get("executor_id") != executor_id:
            raise ValueError("executor binding mismatch")
        request = ActionRequest(**record["request"])
        if binding.get("target") != request.target:
            raise ValueError("executor target mismatch")

        snapshot = record["agent_snapshot"]
        issued = self.clock().astimezone(timezone.utc)
        expires = issued + timedelta(seconds=self.ttl_seconds)
        authorization = ExecutionAuthorization(
            approval_id=approval_id,
            request=request.to_dict(),
            request_digest=request_digest(request),
            agent_snapshot=snapshot,
            agent_snapshot_digest=_sha256(snapshot),
            policy_version=POLICY_VERSION,
            executor_id=executor_id,
            target=request.target,
            issued_at=issued.isoformat(),
            expires_at=expires.isoformat(),
            nonce=secrets.token_hex(32),
            signature="",
        )
        signature = hmac.new(
            self.key,
            _canonical(authorization.unsigned_dict()),
            hashlib.sha256,
        ).hexdigest()
        return ExecutionAuthorization(**{**authorization.to_dict(), "signature": signature})


class ExecutionWorker:
    """Validate an execution authorization before invoking a registered executor."""

    def __init__(
        self,
        controlplane: ControlPlane,
        key: bytes,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if not key:
            raise ValueError("execution authorization key is required")
        self.controlplane = controlplane
        self.key = bytes(key)
        self.clock = clock or _now
        self.executors: dict[str, tuple[str, Executor]] = {}

    def register_executor(self, executor_id: str, target: str, executor: Executor) -> None:
        if not executor_id or not target:
            raise ValueError("executor_id and target are required")
        self.controlplane.register_executor(executor_id, target)
        self.executors[executor_id] = (target, executor)

    def execute(self, authorization: ExecutionAuthorization) -> dict[str, Any]:
        self._verify_signature(authorization)
        self._verify_time(authorization)

        record = self.controlplane.approvals.get(authorization.approval_id)
        if not record or record.get("status") != "approved":
            raise ValueError("approval is not executable")

        request = ActionRequest(**authorization.request)
        if request_digest(request) != authorization.request_digest:
            raise ValueError("request digest mismatch")
        if record.get("request_digest") != authorization.request_digest:
            raise ValueError("approval request digest mismatch")

        agent = self.controlplane.agents.get(request.agent_id)
        if agent is None or agent_snapshot(agent) != authorization.agent_snapshot:
            raise ValueError("agent snapshot mismatch")
        if record.get("agent_snapshot") != authorization.agent_snapshot:
            raise ValueError("approval agent snapshot mismatch")
        if authorization.agent_snapshot_digest != _sha256(authorization.agent_snapshot):
            raise ValueError("agent snapshot digest mismatch")
        if authorization.policy_version != POLICY_VERSION or record.get("policy_version") != POLICY_VERSION:
            raise ValueError("policy version mismatch")
        if record.get("executor_id") != authorization.executor_id:
            raise ValueError("executor binding mismatch")
        if request.target != authorization.target:
            raise ValueError("target binding mismatch")

        registered = self.executors.get(authorization.executor_id)
        if registered is None:
            raise ValueError("unknown executor")
        registered_target, executor = registered
        if registered_target != authorization.target:
            raise ValueError("executor target mismatch")

        if not self.controlplane.consume_execution_nonce(authorization.nonce):
            raise ValueError("authorization already consumed")

        result = executor(request)
        self.controlplane.complete_approved_execution(authorization.approval_id, result)
        return result

    def _verify_signature(self, authorization: ExecutionAuthorization) -> None:
        expected = hmac.new(
            self.key,
            _canonical(authorization.unsigned_dict()),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, authorization.signature):
            raise ValueError("authorization signature mismatch")

    def _verify_time(self, authorization: ExecutionAuthorization) -> None:
        try:
            expires = datetime.fromisoformat(authorization.expires_at).astimezone(timezone.utc)
        except ValueError as exc:
            raise ValueError("invalid authorization expiry") from exc
        if self.clock().astimezone(timezone.utc) >= expires:
            raise ValueError("authorization expired")
