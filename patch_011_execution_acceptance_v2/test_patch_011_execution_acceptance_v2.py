from patch_plan import PatchPlanStore
from patch_011_execution_acceptance_v2 import execute_patch_plan

def make_store(tmp_path, plan_id):
    store = PatchPlanStore(tmp_path)
    store.create({
        "plan_id": plan_id,
        "project_id": "project-0001",
        "patches": [{"patch_id": "PATCH-A"}],
    })
    store.validate(actor="human")
    return store

def test_controlled_local_execution(tmp_path, monkeypatch):
    store = make_store(tmp_path, "PLAN-EXEC-TEST")
    monkeypatch.chdir(tmp_path)
    result = execute_patch_plan(
        store, "project-0001", "local-test", "PATCH-A", actor="human"
    )
    patch = result["patches"][0]
    assert patch["status"] == "COMPLETED"
    assert result["receipt"]["status"] == "COMPLETED"
    assert patch["evidence"]
    actions = [e["action"] for e in store.audit()]
    assert "PATCH_EXECUTING" in actions
    assert "PATCH_VERIFYING" in actions
    assert "PATCH_COMPLETED" in actions

def test_replay_rejected(tmp_path, monkeypatch):
    store = make_store(tmp_path, "PLAN-REPLAY")
    monkeypatch.chdir(tmp_path)
    execute_patch_plan(store, "project-0001", "local-test", "PATCH-A")
    try:
        execute_patch_plan(store, "project-0001", "local-test", "PATCH-A")
    except ValueError as exc:
        assert str(exc) == "patch_not_ready:COMPLETED"
    else:
        raise AssertionError("replay was accepted")

def test_production_rejected(tmp_path):
    store = make_store(tmp_path, "PLAN-PROD")
    try:
        execute_patch_plan(store, "project-0001", "production", "PATCH-A")
    except ValueError as exc:
        assert str(exc) == "target_not_allowed"
    else:
        raise AssertionError("production execution was accepted")

def test_project_binding_rejected(tmp_path):
    store = make_store(tmp_path, "PLAN-BIND")
    try:
        execute_patch_plan(store, "wrong-project", "local-test", "PATCH-A")
    except ValueError as exc:
        assert str(exc) == "project_binding_mismatch"
    else:
        raise AssertionError("wrong project was accepted")
