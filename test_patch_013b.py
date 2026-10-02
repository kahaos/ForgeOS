import json
from pathlib import Path
from project_domain import ProjectDomainStore, DomainError

class FakeStore:
    def __init__(self, root, state="EXPERIMENTING"):
        self.root=Path(root)
        self._state={
            "project_id":"project-0001",
            "name":"Test Project",
            "target":"local-test",
            "state":state,
            "current_release":None,
        }
    def state(self): return dict(self._state)

def test_project_inspect(tmp_path):
    from ai_domain_api import get
    s=FakeStore(tmp_path); d=ProjectDomainStore(tmp_path)
    status, body=get("/api/ai/v1/project",s,d)
    assert status==200
    assert body["project_id"]=="project-0001"

def test_experiment_create_is_project_bound(tmp_path):
    s=FakeStore(tmp_path); d=ProjectDomainStore(tmp_path)
    status, body=__import__("ai_domain_api").post(
        "/api/ai/v1/experiments",
        {"project_id":"project-0001","experiment_id":"EXP-001","name":"Calculator test"},
        s,d)
    assert status==201
    assert body["experiment"]["project_id"]=="project-0001"

def test_experiment_wrong_project_rejected(tmp_path):
    s=FakeStore(tmp_path); d=ProjectDomainStore(tmp_path)
    status, body=__import__("ai_domain_api").post(
        "/api/ai/v1/experiments",
        {"project_id":"project-9999","experiment_id":"EXP-001","name":"Bad"},
        s,d)
    assert status==409
    assert body["error"]=="project_binding_mismatch"

def test_experiment_create_wrong_lifecycle_rejected(tmp_path):
    s=FakeStore(tmp_path,state="DEPLOYMENT_PRECHECKED"); d=ProjectDomainStore(tmp_path)
    status, body=__import__("ai_domain_api").post(
        "/api/ai/v1/experiments",
        {"project_id":"project-0001","experiment_id":"EXP-001","name":"Bad"},
        s,d)
    assert status==409
    assert body["error"].startswith("experiment_create_requires_EXPERIMENTING:")

def test_experiment_duplicate_rejected(tmp_path):
    s=FakeStore(tmp_path); d=ProjectDomainStore(tmp_path)
    api=__import__("ai_domain_api")
    payload={"project_id":"project-0001","experiment_id":"EXP-001","name":"Test"}
    assert api.post("/api/ai/v1/experiments",payload,s,d)[0]==201
    assert api.post("/api/ai/v1/experiments",payload,s,d)[0]==409
