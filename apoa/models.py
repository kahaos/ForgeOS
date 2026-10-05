"""Canonical, provider-neutral Apoa data structures."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping
import time
import uuid


class Decision(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"


@dataclass(frozen=True)
class ExecutionRequest:
    agent: str
    action: str
    target: str
    capabilities: frozenset[str] = frozenset()
    parameters: Mapping[str, Any] = field(default_factory=dict)
    task_id: str | None = None
    environment: str | None = None
    principal: str | None = None
    request_id: str = field(default_factory=lambda: f"req_{uuid.uuid4().hex}")


@dataclass(frozen=True)
class PolicyRule:
    action: str
    decision: Decision = Decision.ALLOW
    required_capability: str | None = None
    allowed_targets: tuple[str, ...] = ()
    required_approval: bool = False
    parameter_limits: Mapping[str, float] = field(default_factory=dict)
    allowed_environments: tuple[str, ...] = ()


@dataclass(frozen=True)
class Policy:
    name: str
    version: str
    rules: tuple[PolicyRule, ...]


@dataclass(frozen=True)
class Approval:
    approval_id: str
    request_id: str
    request_fingerprint: str
    approver: str
    approved: bool
    expires_at: float
    created_at: float = field(default_factory=time.time)


@dataclass(frozen=True)
class Authorization:
    authorization_id: str
    request_id: str
    request_fingerprint: str | None
    decision: Decision
    reason: str
    policy: str
    policy_version: str
    issued_at: float = field(default_factory=time.time)
    expires_at: float | None = None
    nonce: str | None = None
    approval_id: str | None = None

    @property
    def allowed(self) -> bool:
        return self.decision is Decision.ALLOW

    @property
    def requires_approval(self) -> bool:
        return self.decision is Decision.REQUIRE_APPROVAL
