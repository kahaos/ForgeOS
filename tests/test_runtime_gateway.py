from __future__ import annotations

from datetime import datetime, timedelta, timezone

from controlplane.execution_worker import ExecutionWorker
from controlplane.gateway import RuntimeGateway, SimulatedToolAdapter
from controlplane.store import ControlPlane


def setup_gateway(tmp_path):
    cp = ControlPlane(tmp_path / "controlplane")
    cp.register("builder", "human", ["GIT_PUSH"])
    cp.register("seo", "human", ["GIT_COMMIT"])
    expiry = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    cp.create_task("site", "human", "Build website", expiry)
    cp.issue_grant("site", "builder", "GIT_PUSH", {"tool": "git", "action": "push", "repository": "company/site", "branch": "feature/*"}, "human", expiry)
    worker = ExecutionWorker(cp, b"gateway-test-key")
    gateway = RuntimeGateway(cp, worker, b"gateway-test-key")
    adapter = SimulatedToolAdapter("git")
    gateway.register_adapter("git:push", "company/site", adapter)
    return cp, gateway, adapter


def test_scoped_allowed_action_gets_signed_authorization_and_executes(tmp_path):
    cp, gateway, adapter = setup_gateway(tmp_path)
    result = gateway.request("site", "builder", "git", "push", "company/site", {"branch": "feature/home"})
    assert result["verdict"] == "allow"
    assert result["result"]["simulated"] is True
    assert result["authorization"]["task_snapshot"]["task_id"] == "site"
    assert result["authorization"]["grant_snapshot"]["grant_id"].startswith("gr_")
    assert len(adapter.calls) == 1
    assert cp.approvals[next(k for k in cp.approvals if k.startswith("auto_"))]["status"] == "completed"


def test_scope_escape_never_reaches_adapter(tmp_path):
    _, gateway, adapter = setup_gateway(tmp_path)
    result = gateway.request("site", "builder", "git", "push", "company/site", {"branch": "main"})
    assert result["verdict"] == "deny"
    assert adapter.calls == []


def test_delegated_child_cannot_use_parent_repository_scope(tmp_path):
    cp, _, _ = setup_gateway(tmp_path)
    expiry = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    child = cp.delegate_grant(
        next(g.grant_id for g in cp.grants.values() if g.agent_id == "builder"),
        "seo",
        {"tool": "git", "action": "push", "repository": "company/site", "branch": "feature/seo"},
        expiry,
        "builder",
    )
    assert child.agent_id == "seo"
    result = cp.request_scoped("site", "seo", "git", "push", "company/site", {"branch": "feature/other"})
    assert result["verdict"] == "deny"


def test_tampered_scoped_authorization_is_bound_to_scope(tmp_path):
    cp, gateway, adapter = setup_gateway(tmp_path)
    result = gateway.request("site", "builder", "git", "push", "company/site", {"branch": "feature/home"})
    authorization = result["authorization"]
    assert authorization["scope_snapshot"]["branch"] == "feature/*"
    assert cp.snapshot()["evidence_ok"] is True
    assert len(adapter.calls) == 1


def test_production_branch_within_broad_scope_requires_human_approval(tmp_path):
    cp = ControlPlane(tmp_path / "controlplane")
    cp.register("builder", "human", ["GIT_PUSH"])
    expiry = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    cp.create_task("site", "human", "Build website", expiry)
    cp.issue_grant("site", "builder", "GIT_PUSH", {"tool": "git", "action": "push", "repository": "company/site", "branch": "*"}, "human", expiry)
    worker = ExecutionWorker(cp, b"gateway-test-key")
    gateway = RuntimeGateway(cp, worker, b"gateway-test-key")
    adapter = SimulatedToolAdapter("git")
    gateway.register_adapter("git:push", "company/site", adapter)

    result = gateway.request("site", "builder", "git", "push", "company/site", {"branch": "main"})
    assert result["verdict"] == "ask"
    assert result["approval_id"] in cp.approvals
    assert cp.approvals[result["approval_id"]]["status"] == "pending"
    assert adapter.calls == []
