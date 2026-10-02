from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json


SCHEMA = "forgeos.patch_plan.v1"

PLAN_STATES = {
    "PLANNED": {"VALIDATING"},
    "VALIDATING": {"READY", "BLOCKED"},
    "READY": {"EXECUTING", "BLOCKED"},
    "EXECUTING": {"VERIFYING", "FAILED"},
    "VERIFYING": {"COMPLETED", "FAILED"},
    "FAILED": {"ROLLBACK_REQUIRED"},
    "ROLLBACK_REQUIRED": {"ROLLED_BACK", "ROLLBACK_FAILED"},
    "ROLLED_BACK": set(),
    "ROLLBACK_FAILED": set(),
    "COMPLETED": set(),
    "BLOCKED": set(),
}


def now():
    return datetime.now(timezone.utc).isoformat()


def canonical(value):
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":")
    ).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


class PatchPlanError(Exception):
    pass


class PatchPlanStore:
    """
    PATCH-011 orchestration layer.

    This component does NOT own ForgeOS lifecycle state.
    GovernanceStore remains authoritative for lifecycle transitions.
    """

    def __init__(self, root):
        self.root = Path(root)
        self.data = self.root / "data"
        self.data.mkdir(parents=True, exist_ok=True)

        self.plan_file = self.data / "patch_plan.json"
        self.audit_file = self.data / "patch_plan_audit.jsonl"

    def _read_plan(self):
        if not self.plan_file.exists():
            return None
        return json.loads(self.plan_file.read_text())

    def _write_plan(self, value):
        tmp = self.plan_file.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(value, indent=2, sort_keys=True) + "\n"
        )
        tmp.replace(self.plan_file)

    def _audit(self, action, actor="system", extra=None):
        event = {
            "schema": "forgeos.patch_plan_event.v1",
            "timestamp": now(),
            "action": action,
            "actor": actor,
        }

        if extra:
            event.update(extra)

        event["event_digest"] = digest(event)

        with self.audit_file.open("a") as f:
            f.write(json.dumps(event, sort_keys=True) + "\n")

        return event

    def audit(self):
        if not self.audit_file.exists():
            return []

        return [
            json.loads(x)
            for x in self.audit_file.read_text().splitlines()
            if x.strip()
        ]

    def status(self):
        plan = self._read_plan()

        if not plan:
            return {
                "schema": SCHEMA,
                "status": "EMPTY",
                "plan": None,
            }

        return {
            "schema": SCHEMA,
            "status": plan["status"],
            "plan_id": plan["plan_id"],
            "project_id": plan["project_id"],
            "patches": plan["patches"],
            "receipt": plan.get("receipt"),
        }

    def create(self, body):
        if not isinstance(body, dict):
            raise PatchPlanError("plan body must be an object")

        plan_id = str(body.get("plan_id", "")).strip()
        project_id = str(body.get("project_id", "")).strip()
        patches = body.get("patches")

        if not plan_id:
            raise PatchPlanError("plan_id is required")

        if not project_id:
            raise PatchPlanError("project_id is required")

        if not isinstance(patches, list) or not patches:
            raise PatchPlanError("patches must be a non-empty list")

        existing = self._read_plan()
        if existing and existing.get("status") not in {
            "COMPLETED",
            "BLOCKED",
            "ROLLED_BACK",
            "ROLLBACK_FAILED",
        }:
            raise PatchPlanError(
                "a patch plan already exists; create a new plan only after "
                "the existing plan reaches a terminal state"
            )

        seen = set()

        for patch in patches:
            if not isinstance(patch, dict):
                raise PatchPlanError("each patch must be an object")

            patch_id = str(patch.get("patch_id", "")).strip()

            if not patch_id:
                raise PatchPlanError("patch_id is required")

            if patch_id in seen:
                raise PatchPlanError(
                    f"duplicate patch_id: {patch_id}"
                )

            seen.add(patch_id)

            if "dependencies" not in patch:
                patch["dependencies"] = []

            if not isinstance(patch["dependencies"], list):
                raise PatchPlanError(
                    f"dependencies must be a list: {patch_id}"
                )

            patch.setdefault("status", "PENDING")
            patch.setdefault("verification", {})
            patch.setdefault("rollback", {})
            patch.setdefault("evidence", [])

        plan = {
            "schema": SCHEMA,
            "plan_id": plan_id,
            "project_id": project_id,
            "created_at": now(),
            "updated_at": now(),
            "status": "PLANNED",
            "patches": patches,
        }

        plan["plan_digest"] = digest(plan)

        self._write_plan(plan)

        event = self._audit(
            "PLAN_CREATED",
            extra={
                "plan_id": plan_id,
                "project_id": project_id,
                "plan_digest": plan["plan_digest"],
            },
        )

        return {
            "plan": plan,
            "event": event,
        }

    def validate(self, actor="system"):
        plan = self._read_plan()

        if not plan:
            raise PatchPlanError("no patch plan exists")

        if plan["status"] not in {"PLANNED", "BLOCKED"}:
            raise PatchPlanError(
                f"plan cannot be validated from {plan['status']}"
            )

        plan["status"] = "VALIDATING"
        plan["updated_at"] = now()

        patch_ids = {
            patch["patch_id"]
            for patch in plan["patches"]
        }

        completed_dependencies = set()

        problems = []

        for patch in plan["patches"]:
            dependencies = patch.get("dependencies", [])

            for dependency in dependencies:
                if dependency not in patch_ids:
                    problems.append(
                        f"{patch['patch_id']}: missing dependency "
                        f"{dependency}"
                    )

                if dependency == patch["patch_id"]:
                    problems.append(
                        f"{patch['patch_id']}: self dependency"
                    )

            patch["status"] = "READY"

        # Detect simple dependency cycles using DFS.
        graph = {
            patch["patch_id"]: set(patch.get("dependencies", []))
            for patch in plan["patches"]
        }

        visiting = set()
        visited = set()

        def visit(node):
            if node in visiting:
                return True

            if node in visited:
                return False

            visiting.add(node)

            for dep in graph.get(node, set()):
                if dep in graph and visit(dep):
                    return True

            visiting.remove(node)
            visited.add(node)

            return False

        for node in graph:
            if visit(node):
                problems.append("dependency cycle detected")
                break

        if problems:
            plan["status"] = "BLOCKED"
            plan["validation"] = {
                "ok": False,
                "problems": problems,
                "validated_at": now(),
            }
        else:
            plan["status"] = "READY"
            plan["validation"] = {
                "ok": True,
                "problems": [],
                "validated_at": now(),
            }

        plan["updated_at"] = now()

        unsigned = dict(plan)
        unsigned.pop("plan_digest", None)
        plan["plan_digest"] = digest(unsigned)

        self._write_plan(plan)

        event = self._audit(
            "PLAN_VALIDATED",
            actor=actor,
            extra={
                "plan_id": plan["plan_id"],
                "ok": plan["validation"]["ok"],
                "plan_digest": plan["plan_digest"],
            },
        )

        return {
            "plan": plan,
            "event": event,
        }

    def receipt(self):
        plan = self._read_plan()

        if not plan:
            raise PatchPlanError("no patch plan exists")

        receipt = plan.get("receipt")

        if not receipt:
            return None

        return receipt
