import json
from pathlib import Path

from patch_plan import PatchPlanStore
from patch_011_execution_acceptance import execute_patch_plan

def test_controlled_local_execution(tmp_path, monkeypatch):
    store = PatchPlanStore(tmp_path)
    store.create({
        "plan_id": "PLAN-EXEC-TEST",
        "project_id": "project-0001",
        "patches": [{"patch_id": "PATCH-A"}],
    })
    store.validate(actor="human")

    monkeypatch.chdir(tmp_path)
    result = execute_patch_plan(
        store, "project-0001", "local-test", "PATCH-A", actor="human"
    )

    assert result["patches"][0]["status"] == "COMPLETED"
    assert result["receipt"]["status"] == "COMPLETED"
    assert result["patches"][0]["evidence"][0]["sha256" if False else "digest"]

def test_replay_rejected(tmp_path, monkeypatch):
    store = PatchPlanStore(tmp_path)
    store.create({
        "plan_id": "PLAN-REPLAY",
        "project_id": "project-0001",
        "patches": [{"patch_id": "PATCH-A"}],
    })
    store.validate(actor="human")
    monkeypatch.chdir(tmp_path)
    execute_patch_plan(store, "project-0001", "local-test", "PATCH-A")
    try:
        execute_patch_plan(store, "project-0001", "local-test", "PATCH-A")
    except ValueError as e:
        assert str(e).startswith("patch_not_ready:COMPLETED")
    else:
        raise AssertionError("replay was accepted")

def test_production_rejected(tmp_path):
    store = PatchPlanStore(tmp_path)
    store.create({
        "plan_id": "PLAN-PROD",
        "project_id": "project-0001",
        "patches": [{"patch_id": "PATCH-A"}],
    })
    store.validate(actor="human")
    try:
        execute_patch_plan(store, "project-0001", "production", "PATCH-A")
    except ValueError as e:
        assert str(e) == "target_not_allowed"
    else:
        raise AssertionError("production execution was accepted")
