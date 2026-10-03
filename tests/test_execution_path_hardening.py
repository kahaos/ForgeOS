from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from controlplane.api import ApprovalAPI
from controlplane.execution_worker import ExecutionWorker
from controlplane.gateway import RuntimeGateway, SimulatedToolAdapter
from controlplane.store import ControlPlane


def setup_scoped(tmp_path):
    cp = ControlPlane(tmp_path / "controlplane")
    cp.register("builder", "human", ["GIT_PUSH"])
    expiry = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    cp.create_task("site", "human", "Build website", expiry)
    cp.issue_grant(
        "site",
        "builder",
        "GIT_PUSH",
        {"tool": "git", "action": "push", "repository": "company/site", "branch": "*"},
        "human",
        expiry,
    )
    return cp


def test_scoped_request_never_invokes_caller_executor(tmp_path):
    cp = setup_scoped(tmp_path)
    calls = []

    def attacker(request):
        calls.append(request.to_dict())
        return {"status": "attacker-executed"}

    with pytest.raises(ValueError, match="scoped execution must use RuntimeGateway"):
        cp.request_scoped(
            "site",
            "builder",
            "git",
            "push",
            "company/site",
            {"branch": "feature/home"},
            executor=attacker,
            executor_id="git:push",
        )
    assert calls == []


def test_scoped_approval_cannot_execute_directly_from_controlplane(tmp_path):
    cp = setup_scoped(tmp_path)
    adapter = SimulatedToolAdapter("git")
    pending = cp.request_scoped(
        "site",
        "builder",
        "git",
        "push",
        "company/site",
        {"branch": "main"},
        executor=adapter,
        executor_id="git:push",
    )
    assert pending["verdict"] == "ask"
    with pytest.raises(ValueError, match="scoped approval must execute through RuntimeGateway"):
        cp.decide(pending["approval_id"], approve=True, actor="human", execute=True)
    assert adapter.calls == []


def test_scoped_ask_then_approve_converges_on_signed_worker(tmp_path):
    cp = setup_scoped(tmp_path)
    worker = ExecutionWorker(cp, b"boundary-test-key")
    gateway = RuntimeGateway(cp, worker, b"boundary-test-key")
    adapter = SimulatedToolAdapter("git")
    gateway.register_adapter("git:push", "company/site", adapter)

    pending = gateway.request(
        "site",
        "builder",
        "git",
        "push",
        "company/site",
        {"branch": "main"},
    )
    assert pending["verdict"] == "ask"
    assert adapter.calls == []

    approved = gateway.approve_and_execute(pending["approval_id"], actor="human")
    assert approved["verdict"] == "allow"
    assert approved["result"]["simulated"] is True
    assert approved["authorization"]["task_snapshot"]["task_id"] == "site"
    assert approved["authorization"]["grant_snapshot"]["grant_id"].startswith("gr_")
    assert adapter.calls and adapter.calls[0]["detail"]["branch"] == "main"
    assert cp.approvals[pending["approval_id"]]["status"] == "completed"


def test_api_uses_authenticated_operator_not_client_issued_by(tmp_path):
    cp = ControlPlane(tmp_path / "controlplane")
    cp.register("builder", "human", ["GIT_PUSH"])
    api = ApprovalAPI(cp, operator_id="operator-1")
    expiry = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    status, _ = api.handle(
        "POST",
        "/tasks",
        {"task_id": "site", "owner": "human", "purpose": "Build site", "expires_at": expiry},
    )
    assert status == 201

    status, body = api.handle(
        "POST",
        "/tasks/site/grants",
        {
            "agent_id": "builder",
            "capability": "GIT_PUSH",
            "scope": {"tool": "git", "action": "push", "repository": "company/site", "branch": "feature/*"},
            "issued_by": "attacker",
            "expires_at": expiry,
        },
    )
    assert status == 409
    assert body["error"] == "grant issuer mismatch"
    assert cp.grants == {}


def test_api_grant_uses_authenticated_operator_when_issuer_omitted(tmp_path):
    cp = ControlPlane(tmp_path / "controlplane")
    cp.register("builder", "human", ["GIT_PUSH"])
    api = ApprovalAPI(cp, operator_id="operator-1")
    expiry = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    api.handle(
        "POST",
        "/tasks",
        {"task_id": "site", "owner": "human", "purpose": "Build site", "expires_at": expiry},
    )

    status, grant = api.handle(
        "POST",
        "/tasks/site/grants",
        {
            "agent_id": "builder",
            "capability": "GIT_PUSH",
            "scope": {"tool": "git", "action": "push", "repository": "company/site", "branch": "feature/*"},
            "expires_at": expiry,
        },
    )
    assert status == 201
    assert grant["issued_by"] == "operator-1"
