from __future__ import annotations

import pytest

from controlplane.approval import request_digest
from controlplane.models import ActionRequest
from controlplane.policy import POLICY_VERSION
from controlplane.store import ControlPlane


def test_request_digest_is_deterministic_for_identical_requests() -> None:
    a = ActionRequest("agent-1", "git", "push", "repo", {"z": 2, "a": 1})
    b = ActionRequest("agent-1", "git", "push", "repo", {"a": 1, "z": 2})
    assert request_digest(a) == request_digest(b)


def test_request_digest_changes_when_any_governed_field_changes() -> None:
    base = ActionRequest("agent-1", "git", "push", "repo", {"branch": "main"})
    variants = [
        ActionRequest("agent-2", "git", "push", "repo", {"branch": "main"}),
        ActionRequest("agent-1", "github", "push", "repo", {"branch": "main"}),
        ActionRequest("agent-1", "git", "commit", "repo", {"branch": "main"}),
        ActionRequest("agent-1", "git", "push", "other-repo", {"branch": "main"}),
        ActionRequest("agent-1", "git", "push", "repo", {"branch": "other"}),
    ]
    assert all(request_digest(base) != request_digest(item) for item in variants)


def test_ask_record_contains_exact_binding_metadata(tmp_path) -> None:
    cp = ControlPlane(tmp_path)
    cp.register("agent-1", "tester", ["GIT_PUSH", "FS_READ"], risk_level="medium")

    result = cp.request("agent-1", "git", "push", target="test-repo", detail={"branch": "main"})

    assert result["verdict"] == "ask"
    record = cp.approvals[result["approval_id"]]
    assert record["request"] == {
        "agent_id": "agent-1",
        "tool": "git",
        "action": "push",
        "target": "test-repo",
        "detail": {"branch": "main"},
    }
    assert record["request_digest"] == request_digest(ActionRequest(**record["request"]))
    assert record["agent_snapshot"] == {
        "agent_id": "agent-1",
        "owner": "tester",
        "capabilities": ["FS_READ", "GIT_PUSH"],
        "risk_level": "medium",
    }
    assert record["policy_version"] == POLICY_VERSION
    assert record["status"] == "pending"


def test_approved_request_executes_once_and_cannot_be_replayed(tmp_path) -> None:
    cp = ControlPlane(tmp_path)
    cp.register("agent-1", "tester", ["GIT_PUSH"])
    calls: list[dict] = []

    pending = cp.request(
        "agent-1",
        "git",
        "push",
        target="test-repo",
        detail={"branch": "main"},
        executor=lambda req: calls.append(req.to_dict()) or {"status": "completed"},
    )
    approval_id = pending["approval_id"]

    result = cp.decide(approval_id, approve=True, actor="human")

    assert result["verdict"] == "allow"
    assert len(calls) == 1
    assert cp.approvals[approval_id]["status"] == "completed"
    with pytest.raises(KeyError):
        cp.decide(approval_id, approve=True, actor="human")
    assert len(calls) == 1


def test_rejected_request_never_executes(tmp_path) -> None:
    cp = ControlPlane(tmp_path)
    cp.register("agent-1", "tester", ["GIT_PUSH"])
    calls: list[dict] = []

    pending = cp.request(
        "agent-1",
        "git",
        "push",
        target="test-repo",
        executor=lambda req: calls.append(req.to_dict()) or {"status": "completed"},
    )

    result = cp.decide(pending["approval_id"], approve=False, actor="human")

    assert result["verdict"] == "deny"
    assert calls == []
    assert cp.approvals[pending["approval_id"]]["status"] == "denied"


def test_tampered_request_digest_fails_closed_before_execution(tmp_path) -> None:
    cp = ControlPlane(tmp_path)
    cp.register("agent-1", "tester", ["GIT_PUSH"])
    calls: list[dict] = []
    pending = cp.request(
        "agent-1",
        "git",
        "push",
        target="test-repo",
        detail={"branch": "main"},
        executor=lambda req: calls.append(req.to_dict()) or {"status": "completed"},
    )
    approval_id = pending["approval_id"]
    cp.approvals[approval_id]["request"]["target"] = "production-repo"

    with pytest.raises(ValueError, match="approval request digest mismatch"):
        cp.decide(approval_id, approve=True, actor="human")
    assert calls == []


def test_agent_capability_drift_fails_closed(tmp_path) -> None:
    cp = ControlPlane(tmp_path)
    cp.register("agent-1", "tester", ["GIT_PUSH"])
    pending = cp.request("agent-1", "git", "push", target="test-repo")
    approval_id = pending["approval_id"]
    cp.agents["agent-1"].capabilities.append("SPEND_FUNDS")

    with pytest.raises(ValueError, match="approval agent snapshot mismatch"):
        cp.decide(approval_id, approve=True, actor="human")


def test_policy_version_drift_fails_closed(tmp_path) -> None:
    cp = ControlPlane(tmp_path)
    cp.register("agent-1", "tester", ["GIT_PUSH"])
    pending = cp.request("agent-1", "git", "push", target="test-repo")
    approval_id = pending["approval_id"]
    cp.approvals[approval_id]["policy_version"] = "controlplane-999"

    with pytest.raises(ValueError, match="approval policy version mismatch"):
        cp.decide(approval_id, approve=True, actor="human")


def test_executor_cannot_be_substituted_at_decision_time(tmp_path) -> None:
    cp = ControlPlane(tmp_path)
    cp.register("agent-1", "tester", ["GIT_PUSH"])
    calls: list[str] = []
    pending = cp.request(
        "agent-1",
        "git",
        "push",
        target="test-repo",
        executor=lambda req: calls.append("A") or {"status": "completed"},
    )

    with pytest.raises(ValueError, match="executor binding mismatch"):
        cp.decide(
            pending["approval_id"],
            approve=True,
            actor="human",
            executor=lambda req: calls.append("B") or {"status": "completed"},
        )
    assert calls == []


def test_hard_denies_remain_denied_with_nominal_capabilities(tmp_path) -> None:
    cp = ControlPlane(tmp_path)
    cp.register(
        "privileged-test-agent",
        "tester",
        ["CREATE_AGENT", "MODIFY_POLICY", "SPEND_FUNDS"],
    )
    for tool, action in (("agent", "create"), ("policy", "modify"), ("funds", "spend")):
        result = cp.request("privileged-test-agent", tool, action)
        assert result["verdict"] == "deny"
        assert not cp.pending()


def test_approval_evidence_contains_digest_and_lifecycle(tmp_path) -> None:
    cp = ControlPlane(tmp_path)
    cp.register("agent-1", "tester", ["GIT_PUSH"])
    pending = cp.request("agent-1", "git", "push", target="test-repo")
    approval_id = pending["approval_id"]
    digest = cp.approvals[approval_id]["request_digest"]

    cp.decide(approval_id, approve=True, actor="human")

    events = cp.evidence.all()
    kinds = [event["kind"] for event in events]
    assert "approval.requested" in kinds
    assert "approval.granted" in kinds
    assert "approval.executed" in kinds
    lifecycle = [e for e in events if e["kind"].startswith("approval.")]
    assert all(e["data"]["approval_id"] == approval_id for e in lifecycle)
    assert all(e["data"]["request_digest"] == digest for e in lifecycle)
    assert cp.evidence.verify() is True
