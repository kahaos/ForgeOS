from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from controlplane.execution_worker import ExecutionAuthorizer, ExecutionWorker
from controlplane.gateway import SimulatedToolAdapter
from controlplane.store import ControlPlane


def make_approved_scoped(tmp_path):
    cp = ControlPlane(tmp_path / "controlplane")
    cp.register("builder", "human", ["GIT_PUSH"])
    expiry = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
    cp.create_task("site", "human", "Deploy website", expiry)
    grant = cp.issue_grant("site", "builder", "GIT_PUSH", {"tool": "git", "action": "push", "repository": "company/site", "branch": "*"}, "human", expiry)
    pending = cp.request_scoped("site", "builder", "git", "push", "company/site", {"branch": "main"}, executor_id="git:push")
    assert pending["verdict"] == "ask"
    cp.decide(pending["approval_id"], approve=True, actor="human", execute=False)
    return cp, pending["approval_id"], grant


def test_signed_authorization_binds_task_and_grant_snapshots(tmp_path):
    cp, approval_id, grant = make_approved_scoped(tmp_path)
    worker = ExecutionWorker(cp, b"scoped-binding-key")
    adapter = SimulatedToolAdapter("git")
    worker.register_executor("git:push", "company/site", adapter)
    authorization = ExecutionAuthorizer(cp, b"scoped-binding-key").issue(approval_id, "git:push")
    assert authorization.task_snapshot["task_id"] == "site"
    assert authorization.grant_snapshot["grant_id"] == grant.grant_id
    assert authorization.scope_snapshot["branch"] == "*"

    cp.grants[grant.grant_id] = replace(grant, scope=grant.scope.from_dict({"tool": "git", "action": "push", "repository": "company/site", "branch": "feature/*"}))
    with pytest.raises(ValueError, match="grant snapshot mismatch"):
        worker.execute(authorization)
    assert adapter.calls == []


def test_task_revocation_invalidates_signed_scoped_authorization(tmp_path):
    cp, approval_id, _ = make_approved_scoped(tmp_path)
    worker = ExecutionWorker(cp, b"scoped-binding-key")
    adapter = SimulatedToolAdapter("git")
    worker.register_executor("git:push", "company/site", adapter)
    authorization = ExecutionAuthorizer(cp, b"scoped-binding-key").issue(approval_id, "git:push")
    cp.revoke_task("site", "human")
    with pytest.raises(ValueError, match="scoped authority is no longer active"):
        worker.execute(authorization)
    assert adapter.calls == []


def test_scope_tampering_invalidates_signature(tmp_path):
    cp, approval_id, _ = make_approved_scoped(tmp_path)
    worker = ExecutionWorker(cp, b"scoped-binding-key")
    adapter = SimulatedToolAdapter("git")
    worker.register_executor("git:push", "company/site", adapter)
    authorization = ExecutionAuthorizer(cp, b"scoped-binding-key").issue(approval_id, "git:push")
    tampered = replace(authorization, scope_snapshot={"branch": "main"})
    with pytest.raises(ValueError, match="authorization signature mismatch"):
        worker.execute(tampered)
    assert adapter.calls == []
