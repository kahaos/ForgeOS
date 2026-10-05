"""Canonicalization and fingerprinting for Apoa security decisions."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .models import ExecutionRequest


def _normalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _normalize(value[key]) for key in sorted(value, key=lambda item: str(item))}
    if isinstance(value, (list, tuple)):
        return [_normalize(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted((_normalize(item) for item in value), key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":")))
    if isinstance(value, float) and value != value:
        raise ValueError("NaN is not valid in a security-sensitive request")
    if isinstance(value, float) and value in (float("inf"), float("-inf")):
        raise ValueError("Infinity is not valid in a security-sensitive request")
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"Unsupported security-sensitive value: {type(value).__name__}")


def canonical_request(request: ExecutionRequest, policy: str, policy_version: str) -> str:
    """Return deterministic JSON for the security-relevant request context."""
    payload = {
        "agent": request.agent,
        "principal": request.principal,
        "action": request.action,
        "target": request.target,
        "parameters": request.parameters,
        "capabilities": request.capabilities,
        "environment": request.environment,
        "task_id": request.task_id,
        "policy": policy,
        "policy_version": policy_version,
    }
    return json.dumps(_normalize(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def request_fingerprint(request: ExecutionRequest, policy: str, policy_version: str) -> str:
    canonical = canonical_request(request, policy, policy_version).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()
