"""Deterministic request binding helpers for Human Approval v1."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .models import ActionRequest


def canonical_request(request: ActionRequest) -> bytes:
    """Return canonical UTF-8 JSON for the governed request."""
    return json.dumps(
        request.to_dict(),
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def request_digest(request: ActionRequest) -> str:
    """Return the SHA-256 digest of the exact governed request."""
    return hashlib.sha256(canonical_request(request)).hexdigest()


def agent_snapshot(agent: Any) -> dict[str, Any]:
    """Capture immutable approval-relevant agent state."""
    return {
        "agent_id": agent.agent_id,
        "owner": agent.owner,
        "capabilities": sorted(set(agent.capabilities)),
        "risk_level": agent.risk_level,
    }
