from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from controlplane.execution_worker import ExecutionAuthorizer, ExecutionWorker
from controlplane.store import ControlPlane


def make_approved_request(tmp_path):
    cp = ControlPlane(tmp_path / "controlplane")
    cp.register("agent-1", owner="tester", capabilities=["GIT_PUSH"])
    pending = cp.request(
        "agent-1",
        "git",
        "push",
        target="test-repo",
        detail={"branch": "main"},
        executor_id="simulated-git-push",
    )
    assert pending["verdict"] == "ask"
    approval_id = pending["approval_id"]
    approved = cp.decide(approval_id, approve=True, actor="human", execute=False)
    assert approved["verdict"] == "allow"
    assert cp.approvals[approval_id]["status"] == "approved"
    return cp, approval_id


def make_worker(cp, key=b"forgeos-test-execution-key"):
    calls: list[dict] = []
    worker = ExecutionWorker(cp, key)
    worker.register_executor(
        "simulated-git-push",
        target="test-repo",
        executor=lambda request: calls.append(request.to_dict()) or {"status": "completed", "simulated": True},
    )
    return worker, calls


def test_valid_approval_authorization_executes_once(tmp_path):
    cp, approval_id = make_approved_request(tmp_path)
    worker, calls = make_worker(cp)
    authorizer = ExecutionAuthorizer(cp, b"forgeos-test-execution-key")

    authorization = authorizer.issue(approval_id, executor_id="simulated-git-push")
    result = worker.execute(authorization)

    assert result == {"status": "completed", "simulated": True}
    assert len(calls) == 1
    assert cp.approvals[approval_id]["status"] == "completed"
    with pytest.raises(ValueError, match="authorization already consumed"):
        worker.execute(authorization)
    assert len(calls) == 1


def test_request_tampering_is_rejected_before_executor(tmp_path):
    cp, approval_id = make_approved_request(tmp_path)
    worker, calls = make_worker(cp)
    authorizer = ExecutionAuthorizer(cp, b"forgeos-test-execution-key")
    authorization = authorizer.issue(approval_id, executor_id="simulated-git-push")

    tampered = replace(authorization, target="production-repo")
    with pytest.raises(ValueError, match="authorization signature mismatch"):
        worker.execute(tampered)
    assert calls == []


def test_agent_capability_drift_is_rejected_before_executor(tmp_path):
    cp, approval_id = make_approved_request(tmp_path)
    worker, calls = make_worker(cp)
    authorizer = ExecutionAuthorizer(cp, b"forgeos-test-execution-key")
    authorization = authorizer.issue(approval_id, executor_id="simulated-git-push")

    cp.agents["agent-1"].capabilities.append("SPEND_FUNDS")
    with pytest.raises(ValueError, match="agent snapshot mismatch"):
        worker.execute(authorization)
    assert calls == []


def test_signature_mismatch_is_rejected_before_executor(tmp_path):
    cp, approval_id = make_approved_request(tmp_path)
    worker, calls = make_worker(cp)
    authorizer = ExecutionAuthorizer(cp, b"forgeos-test-execution-key")
    authorization = authorizer.issue(approval_id, executor_id="simulated-git-push")

    tampered = replace(authorization, nonce="different-nonce")
    with pytest.raises(ValueError, match="authorization signature mismatch"):
        worker.execute(tampered)
    assert calls == []


def test_expired_authorization_is_rejected_before_executor(tmp_path):
    cp, approval_id = make_approved_request(tmp_path)
    worker, calls = make_worker(cp)
    authorizer = ExecutionAuthorizer(
        cp,
        b"forgeos-test-execution-key",
        ttl_seconds=-1,
    )
    authorization = authorizer.issue(approval_id, executor_id="simulated-git-push")

    with pytest.raises(ValueError, match="authorization expired"):
        worker.execute(authorization)
    assert calls == []


def test_executor_and_target_substitution_are_rejected(tmp_path):
    cp, approval_id = make_approved_request(tmp_path)
    worker, calls = make_worker(cp)
    worker.register_executor(
        "simulated-other-target",
        target="other-repo",
        executor=lambda request: calls.append(request.to_dict()) or {"status": "wrong"},
    )
    authorizer = ExecutionAuthorizer(cp, b"forgeos-test-execution-key")
    authorization = authorizer.issue(approval_id, executor_id="simulated-git-push")

    with pytest.raises(ValueError, match="authorization signature mismatch"):
        worker.execute(replace(authorization, executor_id="simulated-other-target"))
    assert calls == []


def test_missing_persisted_executor_binding_fails_closed(tmp_path):
    cp, approval_id = make_approved_request(tmp_path)
    authorizer = ExecutionAuthorizer(cp, b"forgeos-test-execution-key")
    authorization = authorizer.issue(approval_id, executor_id="simulated-git-push")

    restarted_cp = ControlPlane(tmp_path / "controlplane")
    restarted_worker = ExecutionWorker(restarted_cp, b"forgeos-test-execution-key")
    with pytest.raises(ValueError, match="executor binding unavailable"):
        ExecutionAuthorizer(restarted_cp, b"forgeos-test-execution-key").issue(
            approval_id,
            executor_id=authorization.executor_id,
        )

    with pytest.raises(ValueError, match="unknown executor"):
        restarted_worker.execute(authorization)


def test_authorization_expiry_is_utc_bound(tmp_path):
    cp, approval_id = make_approved_request(tmp_path)
    authorizer = ExecutionAuthorizer(cp, b"forgeos-test-execution-key", ttl_seconds=60)
    authorization = authorizer.issue(approval_id, executor_id="simulated-git-push")

    issued = datetime.fromisoformat(authorization.issued_at)
    expires = datetime.fromisoformat(authorization.expires_at)
    assert issued.tzinfo == timezone.utc
    assert expires - issued == timedelta(seconds=60)
