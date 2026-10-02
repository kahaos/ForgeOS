from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone
from typing import Any

SCHEMA_MANIFEST = "forgeos.ai.manifest.v1"
SCHEMA_CONTEXT = "forgeos.ai.context.v1"
SCHEMA_ERROR = "forgeos.ai.error.v1"

LIFECYCLE = [
    "REQUESTED",
    "EXPERIMENTING",
    "EVIDENCE_READY",
    "VERDICTED",
    "APPROVAL_PENDING",
    "RELEASED",
    "DEPLOYMENT_PRECHECKED",
    "DEPLOYMENT_APPROVED",
    "DEPLOYED",
    "MONITORED",
    "ROLLING_BACK",
    "ROLLED_BACK",
]

CAPABILITIES = [
    {
        "name": "system.status",
        "method": "GET",
        "path": "/api/ai/v1/context",
        "mutating": False,
    },
    {
        "name": "system.manifest",
        "method": "GET",
        "path": "/api/ai/v1/manifest",
        "mutating": False,
    },
    {
        "name": "system.capabilities",
        "method": "GET",
        "path": "/api/ai/v1/capabilities",
        "mutating": False,
    },
    {
        "name": "system.audit",
        "method": "GET",
        "path": "/api/ai/v1/audit",
        "mutating": False,
    },
]

READ_ONLY_REASON = (
    "PATCH-013A is discovery-only. Project, experiment, evidence, verdict, "
    "approval, release and deployment mutations are not exposed until their "
    "governance-backed domain operations exist."
)

def now():
    return datetime.now(timezone.utc).isoformat()

def canonical(value: Any):
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":")
    ).encode()

def digest(value: Any):
    return hashlib.sha256(canonical(value)).hexdigest()

def _production_enabled(store):
    try:
        return bool(store.health().get("production_enabled", False))
    except Exception:
        return False

def _state(store):
    s = store.state()

    return {
        "project_id": s.get("project_id"),
        "name": s.get("name"),
        "target": s.get("target"),
        "state": s.get("state"),
        "updated_at": s.get("updated_at"),
        "current_release": s.get("current_release"),
        "production_enabled": _production_enabled(store),
    }

def _next_state(current):
    return {
        "REQUESTED": "EXPERIMENTING",
        "EXPERIMENTING": "EVIDENCE_READY",
        "EVIDENCE_READY": "VERDICTED",
        "VERDICTED": "APPROVAL_PENDING",
        "APPROVAL_PENDING": "RELEASED",
        "RELEASED": "DEPLOYMENT_PRECHECKED",
        "DEPLOYMENT_PRECHECKED": "DEPLOYMENT_APPROVED",
        "DEPLOYMENT_APPROVED": "DEPLOYED",
        "DEPLOYED": "MONITORED",
        "MONITORED": "ROLLING_BACK",
        "ROLLING_BACK": "ROLLED_BACK",
    }.get(current)

def _allowed_actions(current):
    return {
        "REQUESTED": [
            "project.inspect",
            "experiment.create",
        ],
        "EXPERIMENTING": [
            "project.inspect",
            "experiment.inspect",
            "evidence.submit",
        ],
        "EVIDENCE_READY": [
            "project.inspect",
            "evidence.inspect",
            "verdict.create",
        ],
        "VERDICTED": [
            "project.inspect",
            "verdict.inspect",
            "approval.request",
        ],
        "APPROVAL_PENDING": [
            "project.inspect",
            "approval.inspect",
        ],
        "RELEASED": [
            "project.inspect",
            "release.inspect",
            "deployment.precheck",
        ],
        "DEPLOYMENT_PRECHECKED": [
            "project.inspect",
            "deployment.inspect",
        ],
        "DEPLOYMENT_APPROVED": [
            "project.inspect",
            "deployment.inspect",
            "deployment.execute",
        ],
        "DEPLOYED": [
            "project.inspect",
            "deployment.inspect",
            "monitor.inspect",
            "rollback.request",
        ],
        "MONITORED": [
            "project.inspect",
            "monitor.inspect",
            "rollback.request",
        ],
        "ROLLING_BACK": [
            "project.inspect",
            "rollback.inspect",
        ],
        "ROLLED_BACK": [
            "project.inspect",
            "rollback.inspect",
        ],
    }.get(current, [])

def _blocked_actions(current):
    names = [
        "evidence.submit",
        "verdict.create",
        "approval.request",
        "release.create",
        "deployment.execute",
    ]

    return [
        {
            "name": name,
            "reason": (
                f"not available in PATCH-013A; "
                f"current lifecycle state is {current}"
            ),
        }
        for name in names
        if name not in _allowed_actions(current)
    ]

def manifest(store):
    return {
        "schema": SCHEMA_MANIFEST,
        "api_version": "1.0",
        "patch": "PATCH-013A",
        "system": "ForgeOS",
        "governance_authoritative": True,
        "production_enabled": _production_enabled(store),
        "read_only": True,
        "lifecycle": LIFECYCLE,
        "capabilities": CAPABILITIES,
        "rules": [
            "The AI is an operator, not the governance authority.",
            "The backend governance core is authoritative.",
            "The AI must inspect current context before consequential actions.",
            "The AI must not bypass lifecycle gates.",
            "The AI must not fabricate evidence, approval, release or deployment state.",
            "Production is disabled in this baseline.",
            "PATCH-013A exposes discovery only; no lifecycle mutation is exposed through the AI API.",
        ],
        "planned_capability_families": [
            "project",
            "experiment",
            "evidence",
            "verdict",
            "approval",
            "release",
            "deployment",
            "monitor",
            "rollback",
            "patch-plan",
            "red-team",
        ],
        "timestamp": now(),
    }

def context(store):
    state = _state(store)
    current = state["state"]
    allowed = _allowed_actions(current)

    return {
        "schema": SCHEMA_CONTEXT,
        "patch": "PATCH-013A",
        "system": {
            "governance_authoritative": True,
            "production_enabled": state["production_enabled"],
            "health": store.health(),
        },
        "project": state,
        "lifecycle": {
            "current_state": current,
            "next_state": _next_state(current),
        },
        "allowed_actions": allowed,
        "blocked_actions": _blocked_actions(current),
        "next_action": {
            "name": allowed[0] if allowed else None,
            "reason": (
                "PATCH-013A discovery contract; "
                "domain actions are reported, not executed."
            ),
        },
        "read_only": True,
        "timestamp": now(),
    }

def capabilities(store):
    return {
        "schema": "forgeos.ai.capabilities.v1",
        "patch": "PATCH-013A",
        "read_only": True,
        "capabilities": CAPABILITIES,
        "planned": [
            "project.create",
            "experiment.create",
            "experiment.run",
            "evidence.submit",
            "verdict.create",
            "approval.request",
            "release.create",
            "deployment.precheck",
            "deployment.execute",
            "deployment.verify",
            "monitor.inspect",
            "rollback.request",
            "rollback.execute",
            "patch-plan.*",
            "red-team.*",
        ],
        "timestamp": now(),
    }

def audit(store):
    events = store.audit()

    return {
        "schema": "forgeos.ai.audit.v1",
        "patch": "PATCH-013A",
        "events": events,
        "count": len(events),
        "timestamp": now(),
    }

def error(code, detail, status=400, **extra):
    payload = {
        "schema": SCHEMA_ERROR,
        "error": code,
        "detail": detail,
        "status": status,
        "timestamp": now(),
    }

    payload.update(extra)

    return status, payload

def get(path, store):
    if path == "/api/ai/v1/manifest":
        return 200, manifest(store)

    if path == "/api/ai/v1/context":
        return 200, context(store)

    if path == "/api/ai/v1/capabilities":
        return 200, capabilities(store)

    if path == "/api/ai/v1/audit":
        return 200, audit(store)

    return error(
        "ai_route_not_found",
        f"Unknown AI API route: {path}",
        404,
    )

def post(path, body, store):
    return error(
        "ai_capability_not_enabled",
        READ_ONLY_REASON,
        403,
        path=path,
        allowed_mutations=[],
    )

def verify_patch_013a(store):
    manifest_result = manifest(store)
    context_result = context(store)
    capabilities_result = capabilities(store)

    assert manifest_result["governance_authoritative"] is True
    assert manifest_result["production_enabled"] is False
    assert manifest_result["read_only"] is True
    assert context_result["read_only"] is True

    assert all(
        item["mutating"] is False
        for item in capabilities_result["capabilities"]
    )

    return {
        "schema": "forgeos.ai.acceptance.v1",
        "patch": "PATCH-013A",
        "status": "PASS",
        "checks": [
            "manifest",
            "context",
            "capabilities",
            "production_disabled",
            "governance_authoritative",
            "read_only_mutation_boundary",
        ],
        "timestamp": now(),
        "digest": digest({
            "manifest": manifest_result,
            "context": context_result,
            "capabilities": capabilities_result,
        }),
    }
