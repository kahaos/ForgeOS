from __future__ import annotations
import hashlib
import json
from datetime import datetime, timezone

from local_test_handler import HANDLERS

SCHEMA = "forgeos.patch_execution_receipt.v1"

def _now():
    return datetime.now(timezone.utc).isoformat()

def _digest(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()

def execute_patch_plan(store, project_id, target, patch_id, actor="human"):
    status = store.status()
    if status.get("status") == "EMPTY":
        raise ValueError("no_patch_plan")
    if status.get("project_id") != project_id:
        raise ValueError("project_binding_mismatch")
    if target != "local-test":
        raise ValueError("target_not_allowed")

    patch = next((p for p in status.get("patches", [])
                  if p.get("patch_id") == patch_id), None)
    if patch is None:
        raise ValueError("patch_not_found")
    if patch.get("status") != "READY":
        raise ValueError(f"patch_not_ready:{patch.get('status')}")

    handler_id = "local-test.artifact.v1"
    handler = HANDLERS.get(handler_id)
    if handler is None:
        raise ValueError("handler_not_registered")

    plan = store._read_plan()
    patch = next(p for p in plan["patches"] if p["patch_id"] == patch_id)
    patch["status"] = "EXECUTING"
    patch["execution"] = {
        "handler_id": handler_id,
        "target": target,
        "actor": actor,
        "started_at": _now(),
    }
    plan["updated_at"] = _now()
    store._write_plan(plan)
    store._audit("PATCH_EXECUTING", actor=actor, extra={
        "plan_id": plan["plan_id"],
        "patch_id": patch_id,
        "project_id": project_id,
        "target": target,
        "handler_id": handler_id,
    })

    try:
        result = handler["execute"](store.root)

        plan = store._read_plan()
        patch = next(p for p in plan["patches"] if p["patch_id"] == patch_id)
        patch["status"] = "VERIFYING"
        patch["execution"]["result"] = result
        plan["updated_at"] = _now()
        store._write_plan(plan)
        store._audit("PATCH_VERIFYING", actor=actor, extra={
            "plan_id": plan["plan_id"],
            "patch_id": patch_id,
            "result_digest": _digest(result),
        })

        verification = handler["verify"](store.root, result)
        if not verification.get("ok"):
            raise ValueError("verification_failed")

        plan = store._read_plan()
        patch = next(p for p in plan["patches"] if p["patch_id"] == patch_id)
        patch["status"] = "COMPLETED"
        patch["verification"] = verification
        patch["evidence"] = [{
            "type": "local-test-artifact",
            "digest": result.get("sha256"),
            "path": result.get("path"),
        }]
        receipt = {
            "schema": SCHEMA,
            "plan_id": plan["plan_id"],
            "patch_id": patch_id,
            "project_id": project_id,
            "target": target,
            "handler_id": handler_id,
            "status": "COMPLETED",
            "evidence": patch["evidence"],
            "completed_at": _now(),
        }
        plan["receipt"] = receipt
        plan["updated_at"] = _now()
        store._write_plan(plan)
        store._audit("PATCH_COMPLETED", actor=actor, extra={
            "plan_id": plan["plan_id"],
            "patch_id": patch_id,
            "receipt_digest": _digest(receipt),
        })
        return store.status()

    except Exception as exc:
        plan = store._read_plan()
        patch = next(p for p in plan["patches"] if p["patch_id"] == patch_id)
        patch["status"] = "FAILED"
        patch.setdefault("execution", {})["error"] = str(exc)
        plan["updated_at"] = _now()
        store._write_plan(plan)
        store._audit("PATCH_FAILED", actor=actor, extra={
            "plan_id": plan["plan_id"],
            "patch_id": patch_id,
            "error": str(exc),
        })
        raise
