from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from controlplane.authority import CapabilityGrant, Scope, Task
from controlplane.models import ActionRequest
from controlplane.store import ControlPlane


NOW = datetime(2026, 10, 3, 12, 0, tzinfo=timezone.utc)
FUTURE = (NOW + timedelta(hours=4)).isoformat()


def make_cp(tmp_path):
    cp = ControlPlane(tmp_path / "controlplane")
    cp.register("builder", owner="human", capabilities=["GIT_PUSH", "GIT_COMMIT"])
    cp.register("seo", owner="human", capabilities=["GIT_COMMIT"])
    return cp


def grant_builder(cp):
    task = cp.create_task("task-site", owner="human", purpose="Build website", expires_at=FUTURE)
    grant = cp.issue_grant(
        task_id=task.task_id,
        agent_id="builder",
        capability="GIT_PUSH",
        scope={"tool": "git", "action": "push", "repository": "company/site", "branch": "feature/*"},
        issued_by="human",
        expires_at=FUTURE,
    )
    return task, grant


def test_scope_matches_repository_and_branch():
    scope = Scope.from_dict({"tool": "git", "action": "push", "repository": "company/site", "branch": "feature/*"})
    assert scope.matches(ActionRequest("builder", "git", "push", "company/site", {"branch": "feature/home"}))
    assert not scope.matches(ActionRequest("builder", "git", "push", "company/other", {"branch": "feature/home"}))
    assert not scope.matches(ActionRequest("builder", "git", "push", "company/site", {"branch": "main"}))


def test_unknown_scope_dimension_fails_closed():
    with pytest.raises(ValueError, match="unknown scope dimension"):
        Scope.from_dict({"tool": "git", "account": "all"})


def test_scoped_request_allows_in_scope_without_human_approval(tmp_path):
    cp = make_cp(tmp_path)
    task, grant = grant_builder(cp)
    result = cp.request_scoped(task.task_id, "builder", "git", "push", "company/site", {"branch": "feature/home"})
    assert result["verdict"] == "allow"
    assert result["grant_id"] == grant.grant_id


def test_wrong_repository_and_branch_are_denied(tmp_path):
    cp = make_cp(tmp_path)
    task, _ = grant_builder(cp)
    wrong_repo = cp.request_scoped(task.task_id, "builder", "git", "push", "company/other", {"branch": "feature/home"})
    wrong_branch = cp.request_scoped(task.task_id, "builder", "git", "push", "company/site", {"branch": "main"})
    assert wrong_repo["verdict"] == "deny"
    assert wrong_branch["verdict"] == "deny"


def test_expired_and_revoked_authority_denies(tmp_path):
    cp = make_cp(tmp_path)
    task = cp.create_task("expired", "human", "expired", expires_at=(NOW - timedelta(minutes=1)).isoformat())
    cp.issue_grant("expired", "builder", "GIT_PUSH", {"tool": "git", "action": "push", "repository": "company/site"}, "human", expires_at=FUTURE)
    result = cp.request_scoped("expired", "builder", "git", "push", "company/site", {})
    assert result["verdict"] == "deny"

    task, grant = grant_builder(cp)
    cp.revoke_grant(grant.grant_id, actor="human")
    revoked = cp.request_scoped(task.task_id, "builder", "git", "push", "company/site", {"branch": "feature/x"})
    assert revoked["verdict"] == "deny"


def test_delegation_can_only_attenuate_scope_and_expiry(tmp_path):
    cp = make_cp(tmp_path)
    task, parent = grant_builder(cp)
    child = cp.delegate_grant(
        parent.grant_id,
        child_agent_id="seo",
        scope={"tool": "git", "action": "push", "repository": "company/site", "branch": "feature/seo"},
        expires_at=(NOW + timedelta(hours=1)).isoformat(),
        issued_by="builder",
    )
    assert child.parent_grant_id == parent.grant_id
    allowed = cp.request_scoped(task.task_id, "seo", "git", "push", "company/site", {"branch": "feature/seo"})
    denied = cp.request_scoped(task.task_id, "seo", "git", "push", "company/site", {"branch": "feature/other"})
    assert allowed["verdict"] == "allow"
    assert denied["verdict"] == "deny"


def test_delegation_widening_is_rejected(tmp_path):
    cp = make_cp(tmp_path)
    task, parent = grant_builder(cp)
    with pytest.raises(ValueError, match="outside parent grant scope"):
        cp.delegate_grant(
            parent.grant_id,
            child_agent_id="seo",
            scope={"tool": "git", "action": "push", "repository": "company/site", "branch": "main"},
            expires_at=FUTURE,
            issued_by="builder",
        )


def test_self_grant_is_rejected(tmp_path):
    cp = make_cp(tmp_path)
    task = cp.create_task("self", "human", "self grant", expires_at=FUTURE)
    with pytest.raises(ValueError, match="cannot self-grant"):
        cp.issue_grant("self", "builder", "GIT_PUSH", {"tool": "git", "action": "push", "repository": "company/site"}, "builder", expires_at=FUTURE)


def test_task_and_grant_persist_across_restart(tmp_path):
    cp = make_cp(tmp_path)
    task, grant = grant_builder(cp)
    restarted = ControlPlane(tmp_path / "controlplane")
    assert restarted.tasks[task.task_id].purpose == "Build website"
    assert restarted.grants[grant.grant_id].agent_id == "builder"
    result = restarted.request_scoped(task.task_id, "builder", "git", "push", "company/site", {"branch": "feature/restart"})
    assert result["verdict"] == "allow"
