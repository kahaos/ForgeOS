from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


RISK_LEVELS = ("low", "medium", "high", "critical")


@dataclass
class Agent:
    agent_id: str
    owner: str
    capabilities: list[str]
    risk_level: str = "medium"
    status: str = "registered"

    def __post_init__(self) -> None:
        if self.risk_level not in RISK_LEVELS:
            raise ValueError(f"risk_level must be one of {RISK_LEVELS}")
        self.capabilities = sorted(set(self.capabilities))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ActionRequest:
    agent_id: str
    tool: str
    action: str
    target: str = ""
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Decision:
    verdict: str  # allow | deny | ask
    reason: str
    request: ActionRequest
    approval_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
