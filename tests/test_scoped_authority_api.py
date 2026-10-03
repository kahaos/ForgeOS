from __future__ import annotations

from datetime import datetime, timedelta, timezone

from controlplane.api import ApprovalAPI
from controlplane.store import ControlPlane


def test_task_grant_and_graph_endpoints(tmp_path):
    cp = ControlPlane(tmp_path / "controlplane")
    cp.register("builder", "human", ["GIT_PUSH"])
    api = ApprovalAPI(cp, operator_id="human")
    expiry = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()

    status, task = api.handle("POST", "/tasks", {"task_id": "site", "owner": "human", "purpose": "Build site", "expires_at": expiry})
    assert status == 201
    assert task["task_id"] == "site"

    status, grant = api.handle("POST", "/tasks/site/grants", {"agent_id": "builder", "capability": "GIT_PUSH", "scope": {"tool": "git", "action": "push", "repository": "company/site", "branch": "feature/*"}, "issued_by": "human", "expires_at": expiry})
    assert status == 201
    assert grant["agent_id"] == "builder"

    status, graph = api.handle("GET", "/authority/graph")
    assert status == 200
    assert graph["tasks"][0]["task_id"] == "site"
    assert graph["grants"][0]["agent_id"] == "builder"


def test_scoped_request_endpoint_enforces_scope(tmp_path):
    cp = ControlPlane(tmp_path / "controlplane")
    cp.register("builder", "human", ["GIT_PUSH"])
    api = ApprovalAPI(cp, operator_id="human")
    expiry = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    api.handle("POST", "/tasks", {"task_id": "site", "owner": "human", "purpose": "Build site", "expires_at": expiry})
    api.handle("POST", "/tasks/site/grants", {"agent_id": "builder", "capability": "GIT_PUSH", "scope": {"tool": "git", "action": "push", "repository": "company/site", "branch": "feature/*"}, "issued_by": "human", "expires_at": expiry})

    status, allowed = api.handle("POST", "/scoped/request", {"task_id": "site", "agent_id": "builder", "tool": "git", "action": "push", "target": "company/site", "detail": {"branch": "feature/home"}})
    assert status == 200
    assert allowed["verdict"] == "allow"

    status, denied = api.handle("POST", "/scoped/request", {"task_id": "site", "agent_id": "builder", "tool": "git", "action": "push", "target": "company/site", "detail": {"branch": "main"}})
    assert status == 403
    assert denied["verdict"] == "deny"


def test_clients_cannot_self_grant(tmp_path):
    cp = ControlPlane(tmp_path / "controlplane")
    cp.register("builder", "human", ["GIT_PUSH"])
    api = ApprovalAPI(cp, operator_id="human")
    expiry = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    api.handle("POST", "/tasks", {"task_id": "site", "owner": "human", "purpose": "Build site", "expires_at": expiry})
    status, body = api.handle("POST", "/tasks/site/grants", {"agent_id": "builder", "capability": "GIT_PUSH", "scope": {"tool": "git", "action": "push", "repository": "company/site"}, "issued_by": "builder", "expires_at": expiry})
    assert status == 409
    assert body["error"] == "grant issuer mismatch"