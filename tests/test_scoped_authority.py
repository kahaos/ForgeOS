from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from controlplane.authority import Scope
from controlplane.models import ActionRequest
from controlplane.store import ControlPlane


NOW = datetime(2026, 10, 3, 12, 0, tzinfo=timezone.utc)
FUTURE = (NOW + timedelta(hours=4)).isoformat()


def make_cp(tmp_path):
    cp = ControlPlane(tmp_path / "controlplane")
    cp.register("builder", owner="human", capabilities=["GIT_PUSH", "GIT_COMMIT"])
    cp.register("seo", owner="human", capabilities=["GIT_COMMIT", "GIT_PUSH"])
    return cp


def grant_builder(cp):
    task = cp.create_task("task-site", owner="human", purpose="Build website", expires_at=FUTURE)
    grant = cp.issue_grant(task.task_id, "builder", "GIT_PUSH", {"tool": "git", "action": "push", "repository": "company/site", "branch": "feature/*"}, "human", FUTURE)
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
    assert cp.request_scoped(task.task_id, "builder", "git", "push", "company/other", {"branch": "feature/home"})["verdict"] == "deny"
    assert cp.request_scoped(task.task_id, "builder", "git", "push", "company/site", {"branch": "main"})["verdict"] == "deny"


def test_expired_and_revoked_authority_denies(tmp_path):
    cp = make_cp(tmp_path)
    task = cp.create_task("expired", "human", "expired", expires_at=(datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat())
    cp.tasks["expired"] = replace(task, status="expired")
    cp.issue_grant("expired", "builder", "GIT_PUSH", {"tool": "git", "action": "push", "repository": "company/site"}, "human", expires_at=(datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat())
    assert cp.request_scoped("expired", "builder", "git", "push", "company/site", {})["verdict"] == "deny"

    task, grant = grant_builder(cp)
    cp.revoke_grant(grant.grant_id, actor="human")
    assert cp.request_scoped(task.task_id, "builder", "git", "push", "company/site", {"branch": "feature/x"})["verdict"] == "deny"


def test_delegation_can_only_attenuate_scope_and_expiry(tmp_path):
    cp = make_cp(tmp_path)
    task, parent = grant_builder(cp)
    child = cp.delegate_grant(parent.grant_id, "seo", {"tool": "git", "action": "push", "repository": "company/site", "branch": "feature/seo"}, expires_at=(datetime.now(timezone.utc) + timedelta(minutes=20)).isoformat(), issued_by="builder")
    assert child.parent_grant_id == parent.grant_id
    assert cp.request_scoped(task.task_id, "seo", "git", "push", "company/site", {"branch": "feature/seo"})["verdict"] == "allow"
    assert cp.request_scoped(task.task_id, "seo", "git", "push", "company/site", {"branch": "feature/other"})["verdict"] == "deny"


def test_delegation_widening_is_rejected(tmp_path):
    cp = make_cp(tmp_path)
    _, parent = grant_builder(cp)
    with pytest.raises(ValueError, match="outside parent grant scope"):
        cp.delegate_grant(parent.grant_id, "seo", {"tool": "git", "action": "push", "repository": "company/site", "branch": "main"}, FUTURE, "builder")


def test_self_grant_and_direct_agent_grant_are_rejected(tmp_path):
    cp = make_cp(tmp_path)
    cp.create_task("self", "human", "self grant", expires_at=FUTURE)
    with pytest.raises(ValueError, match="cannot self-grant"):
        cp.issue_grant("self", "builder", "GIT_PUSH", {"tool": "git", "action": "push", "repository": "company/site"}, "builder", FUTURE)
    with pytest.raises(ValueError, match="cannot issue grants directly"):
        cp.issue_grant("self", "seo", "GIT_PUSH", {"tool": "git", "action": "push", "repository": "company/site"}, "builder", FUTURE)


def test_task_and_grant_persist_across_restart(tmp_path):
    cp = make_cp(tmp_path)
    task, grant = grant_builder(cp)
    restarted = ControlPlane(tmp_path / "controlplane")
    assert restarted.tasks[task.task_id].purpose == "Build website"
    assert restarted.grants[grant.grant_id].agent_id == "builder"
    assert restarted.request_scoped(task.task_id, "builder", "git", "push", "company/site", {"branch": "feature/restart"})["verdict"] == "allow"
