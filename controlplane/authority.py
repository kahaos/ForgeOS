"""Task-scoped authority primitives for ForgeOS.

The module is deliberately policy-light: it validates structured scope syntax and
provides deterministic matching/subset operations. The ControlPlane remains the
single authority for issuance and policy decisions.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from fnmatch import fnmatchcase
from pathlib import Path
from typing import Any, Mapping


SCOPE_DIMENSIONS = {
    "tool",
    "action",
    "resource",
    "repository",
    "branch",
    "workspace",
    "workspace_path",
    "environment",
    "api_host",
    "api_path",
}

TASK_STATUSES = {"active", "completed", "revoked", "expired"}


def _utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def resolve_workspace_path(workspace: str | Path, relative: str) -> Path:
    """Resolve a workspace-relative path and reject escapes from the workspace.

    This is shared by policy and the local executor so the authorization boundary
    and execution boundary apply exactly the same path-containment rule.
    """
    if not isinstance(relative, str) or not relative:
        raise ValueError("workspace path is required")
    root = Path(workspace).resolve()
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("path is outside workspace") from exc
    return candidate


def _request_value(request: Any, dimension: str) -> str:
    detail = request.detail or {}
    if dimension == "tool":
        return request.tool
    if dimension == "action":
        return request.action
    if dimension == "resource":
        return request.target
    if dimension == "repository":
        return str(detail.get("repository", request.target))
    if dimension == "branch":
        return str(detail.get("branch", ""))
    if dimension in {"workspace", "workspace_path"}:
        return str(detail.get("workspace", detail.get("path", "")))
    if dimension == "environment":
        return str(detail.get("environment", ""))
    if dimension == "api_host":
        return str(detail.get("api_host", ""))
    if dimension == "api_path":
        return str(detail.get("api_path", detail.get("path", "")))
    raise ValueError(f"unknown scope dimension: {dimension}")


@dataclass(frozen=True)
class Scope:
    values: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        unknown = set(self.values) - SCOPE_DIMENSIONS
        if unknown:
            raise ValueError(f"unknown scope dimension: {sorted(unknown)[0]}")
        if not self.values:
            raise ValueError("scope must contain at least one dimension")
        for key, value in self.values.items():
            if not isinstance(value, str) or not value:
                raise ValueError(f"scope value for {key} must be a non-empty string")
            if key != "branch" and ("*" in value or "?" in value):
                raise ValueError(f"wildcards are not supported for scope dimension {key}")

    @classmethod
    def from_dict(cls, values: Mapping[str, Any]) -> "Scope":
        return cls({str(k): str(v) for k, v in values.items()})

    def to_dict(self) -> dict[str, str]:
        return dict(self.values)

    def matches(self, request: Any) -> bool:
        for dimension, expected in self.values.items():
            actual = _request_value(request, dimension)
            if dimension == "branch":
                if not fnmatchcase(actual, expected):
                    return False
            elif actual != expected:
                return False
        return True

    def contains(self, child: "Scope") -> bool:
        """Return whether every child request is also inside this scope."""
        for dimension, parent_value in self.values.items():
            child_value = child.values.get(dimension)
            if child_value is None:
                return False
            if dimension == "branch":
                if not _branch_pattern_subset(parent_value, child_value):
                    return False
            elif child_value != parent_value:
                return False
        return True


def _branch_pattern_subset(parent: str, child: str) -> bool:
    if parent == child:
        return True
    if parent.endswith("/*") and not any(ch in child for ch in "*?"):
        return child.startswith(parent[:-1])
    return False


@dataclass(frozen=True)
class Task:
    task_id: str
    owner: str
    purpose: str
    status: str
    created_at: str
    expires_at: str
    parent_task_id: str | None = None
    human_context: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status not in TASK_STATUSES:
            raise ValueError(f"invalid task status: {self.status}")
        if _utc(self.expires_at) <= _utc(self.created_at):
            raise ValueError("task expiry must be after creation")

    def active(self, now: datetime | None = None) -> bool:
        current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        return self.status == "active" and current < _utc(self.expires_at)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CapabilityGrant:
    grant_id: str
    task_id: str
    agent_id: str
    capability: str
    scope: Scope
    issued_by: str
    issued_at: str
    expires_at: str
    policy_version: str
    parent_grant_id: str | None = None
    status: str = "active"

    def active(self, now: datetime | None = None) -> bool:
        current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
        return self.status == "active" and current < _utc(self.expires_at)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["scope"] = self.scope.to_dict()
        return data


@dataclass(frozen=True)
class AuthorityDecision:
    verdict: str
    reason: str
    request: Any
    grant_id: str | None = None
    task_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict,
            "reason": self.reason,
            "request": self.request.to_dict(),
            "grant_id": self.grant_id,
            "task_id": self.task_id,
        }
