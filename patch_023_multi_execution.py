from datetime import datetime, timezone

from patch_011_execution import execute_patch_plan


def _now():
    return datetime.now(timezone.utc).isoformat()


def _dependents(patches, completed_or_failed):
    result = set()

    changed = True
    while changed:
        changed = False

        for patch in patches:
            patch_id = patch["patch_id"]

            if patch_id in result:
                continue

            dependencies = set(patch.get("dependencies", []))

            if dependencies & completed_or_failed:
                result.add(patch_id)
                changed = True

        completed_or_failed = set(completed_or_failed) | result

    return result


def _write_failure_state(store, failed_patch_id, error, actor):
    plan = store._read_plan()

    patches = plan["patches"]

    failed = next(
        p for p in patches
        if p["patch_id"] == failed_patch_id
    )

    failed["status"] = "FAILED"
    failed.setdefault("execution", {})
    failed["execution"]["error"] = str(error)
    failed["execution"]["failed_at"] = _now()

    blocked_ids = _dependents(
        patches,
        {failed_patch_id},
    )

    for patch in patches:
        if patch["patch_id"] in blocked_ids:
            if patch["status"] not in {"COMPLETED", "FAILED"}:
                patch["status"] = "BLOCKED"
                patch.setdefault("execution", {})
                patch["execution"]["blocked_by"] = failed_patch_id
                patch["execution"]["blocked_at"] = _now()

    plan["status"] = "FAILED"
    plan["updated_at"] = _now()

    store._write_plan(plan)

    store._audit(
        "MULTI_PATCH_FAILED",
        actor=actor,
        extra={
            "plan_id": plan["plan_id"],
            "failed_patch_id": failed_patch_id,
            "blocked_patch_ids": sorted(blocked_ids),
            "error": str(error),
        },
    )


def _write_completed_receipt(store, project_id, target, actor):
    plan = store._read_plan()

    completed = [
        p["patch_id"]
        for p in plan["patches"]
        if p.get("status") == "COMPLETED"
    ]

    failed = [
        p["patch_id"]
        for p in plan["patches"]
        if p.get("status") == "FAILED"
    ]

    blocked = [
        p["patch_id"]
        for p in plan["patches"]
        if p.get("status") == "BLOCKED"
    ]

    receipt = {
        "schema": "forgeos.multi_patch_execution_receipt.v1",
        "plan_id": plan["plan_id"],
        "project_id": project_id,
        "target": target,
        "actor": actor,
        "status": plan["status"],
        "completed_patch_ids": completed,
        "failed_patch_ids": failed,
        "blocked_patch_ids": blocked,
        "completed_at": _now(),
    }

    plan["receipt"] = receipt
    plan["updated_at"] = _now()

    store._write_plan(plan)

    return receipt


def execute_patch_plan_all(
    store,
    project_id,
    target,
    actor="human",
):
    status = store.status()

    if status.get("status") == "EMPTY":
        raise ValueError("no_patch_plan")

    if status.get("project_id") != project_id:
        raise ValueError("project_binding_mismatch")

    if target != "local-test":
        raise ValueError("target_not_allowed")

    if status.get("status") == "COMPLETED":
        raise ValueError("plan_already_completed")

    if status.get("status") != "READY":
        raise ValueError(
            f"plan_not_ready:{status.get('status')}"
        )

    store._audit(
        "MULTI_PATCH_EXECUTING",
        actor=actor,
        extra={
            "plan_id": status["plan_id"],
            "project_id": project_id,
            "target": target,
        },
    )

    while True:
        plan = store._read_plan()

        patches = plan["patches"]

        if all(
            patch.get("status") == "COMPLETED"
            for patch in patches
        ):
            plan["status"] = "COMPLETED"
            plan["updated_at"] = _now()
            store._write_plan(plan)

            _write_completed_receipt(
                store,
                project_id,
                target,
                actor,
            )

            store._audit(
                "MULTI_PATCH_COMPLETED",
                actor=actor,
                extra={
                    "plan_id": plan["plan_id"],
                    "project_id": project_id,
                    "completed_patch_ids": [
                        p["patch_id"]
                        for p in patches
                    ],
                },
            )

            return store.status()

        completed_ids = {
            patch["patch_id"]
            for patch in patches
            if patch.get("status") == "COMPLETED"
        }

        candidate = None

        for patch in patches:
            if patch.get("status") != "READY":
                continue

            dependencies = set(
                patch.get("dependencies", [])
            )

            if dependencies.issubset(completed_ids):
                candidate = patch
                break

        if candidate is None:
            unresolved = [
                p["patch_id"]
                for p in patches
                if p.get("status") == "READY"
            ]

            for patch in patches:
                if patch["patch_id"] in unresolved:
                    patch["status"] = "BLOCKED"
                    patch.setdefault("execution", {})
                    patch["execution"]["blocked_at"] = _now()
                    patch["execution"]["blocked_reason"] = (
                        "dependencies_not_satisfied"
                    )

            plan["status"] = "BLOCKED"
            plan["updated_at"] = _now()
            store._write_plan(plan)

            store._audit(
                "MULTI_PATCH_BLOCKED",
                actor=actor,
                extra={
                    "plan_id": plan["plan_id"],
                    "blocked_patch_ids": unresolved,
                },
            )

            return store.status()

        patch_id = candidate["patch_id"]

        try:
            execute_patch_plan(
                store,
                project_id,
                target,
                patch_id,
                actor=actor,
            )
        except Exception as exc:
            _write_failure_state(
                store,
                patch_id,
                exc,
                actor,
            )

            return store.status()
