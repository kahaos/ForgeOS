from __future__ import annotations

from controlplane.api import ApprovalAPI
from controlplane.store import ControlPlane


def make_api(tmp_path):
    cp = ControlPlane(tmp_path / "controlplane")
    cp.register(
        "agent-1",
        owner="tester",
        capabilities=["FS_READ", "FS_WRITE", "GIT_PUSH"],
    )
    return ApprovalAPI(cp), cp


def call(api: ApprovalAPI, method: str, path: str, body=None):
    return api.handle(method, path, body)


def test_request_endpoint_delegates_allow_ask_and_deny_to_control_plane(tmp_path):
    api, _ = make_api(tmp_path)

    allowed_status, allowed = call(
        api,
        "POST",
        "/approvals/request",
        {
            "agent_id": "agent-1",
            "tool": "filesystem",
            "action": "read",
            "target": "hello.txt",
            "detail": {"name": "hello.txt"},
        },
    )
    assert allowed_status == 200
    assert allowed["verdict"] == "allow"

    ask_status, ask = call(
        api,
        "POST",
        "/approvals/request",
        {
            "agent_id": "agent-1",
            "tool": "git",
            "action": "push",
            "target": "test-repo",
            "detail": {"branch": "main"},
        },
    )
    assert ask_status == 202
    assert ask["verdict"] == "ask"
    assert ask["approval_id"]
    assert ask["request_digest"]

    deny_status, denied = call(
        api,
        "POST",
        "/approvals/request",
        {
            "agent_id": "agent-1",
            "tool": "policy",
            "action": "modify",
        },
    )
    assert deny_status == 403
    assert denied["verdict"] == "deny"


def test_pending_and_detail_endpoints_expose_exact_approval_binding(tmp_path):
    api, cp = make_api(tmp_path)
    _, pending = call(
        api,
        "POST",
        "/approvals/request",
        {
            "agent_id": "agent-1",
            "tool": "git",
            "action": "push",
            "target": "test-repo",
            "detail": {"branch": "main"},
        },
    )
    approval_id = pending["approval_id"]

    status, pending_list = call(api, "GET", "/approvals/pending")
    assert status == 200
    assert len(pending_list) == 1
    assert pending_list[0]["id"] == approval_id

    status, detail = call(api, "GET", f"/approvals/{approval_id}")
    assert status == 200
    assert detail["status"] == "pending"
    assert detail["request_digest"] == pending["request_digest"]
    assert detail["request"] == cp.approvals[approval_id]["request"]
    assert detail["agent_snapshot"] == cp.approvals[approval_id]["agent_snapshot"]
    assert detail["policy_version"] == cp.approvals[approval_id]["policy_version"]


def test_approve_authorizes_once_and_deny_never_authorizes(tmp_path):
    api, cp = make_api(tmp_path)
    _, pending = call(
        api,
        "POST",
        "/approvals/request",
        {
            "agent_id": "agent-1",
            "tool": "git",
            "action": "push",
            "target": "test-repo",
        },
    )
    approval_id = pending["approval_id"]

    status, approved = call(
        api,
        "POST",
        f"/approvals/{approval_id}/approve",
        {"actor": "human"},
    )
    assert status == 200
    assert approved["verdict"] == "allow"
    assert cp.approvals[approval_id]["status"] == "approved"

    replay_status, replay = call(
        api,
        "POST",
        f"/approvals/{approval_id}/approve",
        {"actor": "human"},
    )
    assert replay_status == 409
    assert replay["error"] == "no pending approval"

    _, pending2 = call(
        api,
        "POST",
        "/approvals/request",
        {
            "agent_id": "agent-1",
            "tool": "git",
            "action": "push",
            "target": "another-repo",
        },
    )
    approval_id2 = pending2["approval_id"]
    status, denied = call(
        api,
        "POST",
        f"/approvals/{approval_id2}/deny",
        {"actor": "human"},
    )
    assert status == 200
    assert denied["verdict"] == "deny"
    assert cp.approvals[approval_id2]["status"] == "denied"


def test_api_rejects_unknown_ids_and_malformed_requests_without_tracebacks(tmp_path):
    api, _ = make_api(tmp_path)

    status, body = call(api, "GET", "/approvals/apr_missing")
    assert status == 404
    assert body == {"error": "approval not found"}

    status, body = call(api, "POST", "/approvals/apr_missing/approve", {})
    assert status == 404
    assert body == {"error": "approval not found"}

    status, body = call(
        api,
        "POST",
        "/approvals/request",
        {"agent_id": "agent-1", "tool": "git"},
    )
    assert status == 400
    assert body["error"] == "invalid request"

    status, body = call(api, "PATCH", "/approvals/pending")
    assert status == 405
    assert body == {"error": "method not allowed"}


def test_api_cannot_replace_executor_or_bypass_control_plane_validation(tmp_path):
    api, cp = make_api(tmp_path)
    _, pending = call(
        api,
        "POST",
        "/approvals/request",
        {
            "agent_id": "agent-1",
            "tool": "git",
            "action": "push",
            "target": "test-repo",
        },
    )
    approval_id = pending["approval_id"]
    cp.approvals[approval_id]["request"]["target"] = "production-repo"

    status, body = call(
        api,
        "POST",
        f"/approvals/{approval_id}/approve",
        {"actor": "human"},
    )
    assert status == 409
    assert body["error"] == "approval binding rejected"
