from pathlib import Path
import tempfile
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from patch_plan import PatchPlanStore


def test_create_and_validate():
    with tempfile.TemporaryDirectory() as tmp:
        store = PatchPlanStore(tmp)

        result = store.create({
            "plan_id": "PLAN-000001",
            "project_id": "project-0001",
            "patches": [
                {
                    "patch_id": "PATCH-011-A",
                    "dependencies": [],
                },
                {
                    "patch_id": "PATCH-011-B",
                    "dependencies": ["PATCH-011-A"],
                },
            ],
        })

        assert result["plan"]["status"] == "PLANNED"
        assert result["plan"]["plan_digest"]

        result = store.validate()

        assert result["plan"]["status"] == "READY"
        assert result["plan"]["validation"]["ok"] is True


def test_missing_dependency_blocked():
    with tempfile.TemporaryDirectory() as tmp:
        store = PatchPlanStore(tmp)

        store.create({
            "plan_id": "PLAN-000002",
            "project_id": "project-0001",
            "patches": [
                {
                    "patch_id": "PATCH-011-B",
                    "dependencies": ["PATCH-011-A"],
                },
            ],
        })

        result = store.validate()

        assert result["plan"]["status"] == "BLOCKED"
        assert result["plan"]["validation"]["ok"] is False


def test_dependency_cycle_blocked():
    with tempfile.TemporaryDirectory() as tmp:
        store = PatchPlanStore(tmp)

        store.create({
            "plan_id": "PLAN-000003",
            "project_id": "project-0001",
            "patches": [
                {
                    "patch_id": "PATCH-A",
                    "dependencies": ["PATCH-B"],
                },
                {
                    "patch_id": "PATCH-B",
                    "dependencies": ["PATCH-A"],
                },
            ],
        })

        result = store.validate()

        assert result["plan"]["status"] == "BLOCKED"


def test_audit_is_written():
    with tempfile.TemporaryDirectory() as tmp:
        store = PatchPlanStore(tmp)

        store.create({
            "plan_id": "PLAN-000004",
            "project_id": "project-0001",
            "patches": [
                {
                    "patch_id": "PATCH-A",
                },
            ],
        })

        store.validate()

        events = store.audit()

        assert len(events) == 2
        assert events[0]["action"] == "PLAN_CREATED"
        assert events[1]["action"] == "PLAN_VALIDATED"
        assert events[0]["event_digest"]
        assert events[1]["event_digest"]


if __name__ == "__main__":
    print("PATCH-011 tests: PASS")
