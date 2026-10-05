from apoa import Decision, ExecutionRequest, Policy, PolicyRule, ApoaEngine
from apoa.canonical import request_fingerprint
from apoa.executor import ProtectedExecutor


def engine() -> ApoaEngine:
    return ApoaEngine(Policy(name="demo-v1", version="1", rules=(
        PolicyRule(action="read_repo", required_capability="GIT_READ", allowed_targets=("repo/",)),
        PolicyRule(action="git_push", required_capability="GIT_PUSH", required_approval=True, allowed_targets=("repo/",)),
        PolicyRule(action="force_push", decision=Decision.DENY, required_capability="GIT_PUSH"),
        PolicyRule(action="refund", required_capability="PAYMENT", parameter_limits={"amount": 100}),
    )))


def push_request(**overrides) -> ExecutionRequest:
    values = dict(agent="agent-1", principal="principal-1", action="git_push", target="repo/project-a",
                  capabilities=frozenset({"GIT_PUSH"}), parameters={"branch": "main"}, task_id="task-1",
                  environment="production")
    values.update(overrides)
    return ExecutionRequest(**values)


def test_allow():
    assert engine().authorize(ExecutionRequest(agent="agent-1", action="read_repo", target="repo/project-a",
                                               capabilities=frozenset({"GIT_READ"}))).decision is Decision.ALLOW


def test_missing_capability_is_denied():
    assert engine().authorize(ExecutionRequest(agent="agent-1", action="read_repo", target="repo/project-a")).decision is Decision.DENY


def test_out_of_scope_target_is_denied():
    assert engine().authorize(ExecutionRequest(agent="agent-1", action="read_repo", target="production/secrets",
                                               capabilities=frozenset({"GIT_READ"}))).decision is Decision.DENY


def test_explicit_deny_wins():
    assert engine().authorize(ExecutionRequest(agent="agent-1", action="force_push", target="repo/project-a",
                                               capabilities=frozenset({"GIT_PUSH"}))).decision is Decision.DENY


def test_approval_required():
    assert engine().authorize(push_request()).decision is Decision.REQUIRE_APPROVAL


def test_parameter_limit_denies_excess():
    assert engine().authorize(ExecutionRequest(agent="agent-1", action="refund", target="payments",
                                               capabilities=frozenset({"PAYMENT"}), parameters={"amount": 101})).decision is Decision.DENY


def test_fingerprint_is_stable_when_mapping_order_changes():
    a = push_request(parameters={"amount": 20, "currency": "GBP"})
    b = push_request(parameters={"currency": "GBP", "amount": 20})
    assert request_fingerprint(a, "demo-v1", "1") == request_fingerprint(b, "demo-v1", "1")


def test_fingerprint_changes_for_security_relevant_fields():
    request = push_request()
    fp = request_fingerprint(request, "demo-v1", "1")
    for changed in (
        push_request(action="read_repo"), push_request(target="repo/other"),
        push_request(parameters={"branch": "develop"}), push_request(agent="agent-2"),
        push_request(principal="principal-2"), push_request(capabilities=frozenset({"GIT_READ", "GIT_PUSH"})),
        push_request(environment="staging"),
    ):
        assert request_fingerprint(changed, "demo-v1", "1") != fp
    assert request_fingerprint(request, "demo-v1", "2") != fp


def test_approved_execution_is_single_use():
    apoa, request = engine(), push_request()
    approval = apoa.approve(request, "human-1")
    authorization = apoa.issue_execution_authorization(request, approval)
    assert authorization.decision is Decision.ALLOW
    assert apoa.consume(request, authorization) is True
    assert apoa.consume(request, authorization) is False


def test_changed_target_cannot_reuse_authorization():
    apoa, request = engine(), push_request()
    authorization = apoa.issue_execution_authorization(request, apoa.approve(request, "human-1"))
    assert apoa.consume(push_request(target="repo/secrets"), authorization) is False


def test_changed_parameters_cannot_reuse_authorization():
    apoa, request = engine(), push_request()
    authorization = apoa.issue_execution_authorization(request, apoa.approve(request, "human-1"))
    assert apoa.consume(push_request(parameters={"branch": "production"}), authorization) is False


def test_changed_agent_cannot_reuse_authorization():
    apoa, request = engine(), push_request()
    authorization = apoa.issue_execution_authorization(request, apoa.approve(request, "human-1"))
    assert apoa.consume(push_request(agent="attacker"), authorization) is False


def test_changed_capability_cannot_reuse_authorization():
    apoa, request = engine(), push_request()
    authorization = apoa.issue_execution_authorization(request, apoa.approve(request, "human-1"))
    assert apoa.consume(push_request(capabilities=frozenset({"GIT_PUSH", "READ_SECRETS"})), authorization) is False


def test_approval_for_different_request_cannot_be_substituted():
    apoa = engine()
    a, b = push_request(target="repo/project-a"), push_request(target="repo/project-b")
    authorization = apoa.issue_execution_authorization(b, apoa.approve(a, "human-1"))
    assert authorization.decision is Decision.REQUIRE_APPROVAL


def test_policy_version_change_invalidates_old_authorization():
    apoa, request = engine(), push_request()
    authorization = apoa.issue_execution_authorization(request, apoa.approve(request, "human-1"))
    apoa.policy = Policy(name="demo-v1", version="2", rules=apoa.policy.rules)
    assert apoa.consume(request, authorization) is False


def test_expired_authorization_is_rejected():
    apoa = engine()
    request = ExecutionRequest(agent="agent-1", action="read_repo", target="repo/project-a", capabilities=frozenset({"GIT_READ"}))
    authorization = apoa.issue_execution_authorization(request, ttl=-1)
    assert authorization.decision is Decision.ALLOW
    assert apoa.consume(request, authorization) is False


def test_expired_approval_cannot_authorize_execution():
    apoa, request = engine(), push_request()
    authorization = apoa.issue_execution_authorization(request, apoa.approve(request, "human-1", ttl=-1))
    assert authorization.decision is Decision.REQUIRE_APPROVAL


def test_tampered_authorization_fingerprint_is_rejected():
    apoa, request = engine(), push_request()
    auth = apoa.issue_execution_authorization(request, apoa.approve(request, "human-1"))
    tampered = auth.__class__(authorization_id=auth.authorization_id, request_id=auth.request_id,
        request_fingerprint="tampered", decision=auth.decision, reason=auth.reason, policy=auth.policy,
        policy_version=auth.policy_version, issued_at=auth.issued_at, expires_at=auth.expires_at,
        nonce=auth.nonce, approval_id=auth.approval_id)
    assert apoa.consume(request, tampered) is False


def test_protected_executor_blocks_execution_without_valid_authorization():
    calls = []
    executor = ProtectedExecutor(engine(), lambda request: calls.append(request.target) or "ok")
    request = ExecutionRequest(agent="agent-1", action="read_repo", target="repo/project-a", capabilities=frozenset({"GIT_READ"}))
    assert executor.execute(request, None) is None
    assert calls == []


def test_protected_executor_executes_only_with_valid_authorization():
    apoa, calls = engine(), []
    executor = ProtectedExecutor(apoa, lambda request: calls.append(request.target) or "ok")
    request = ExecutionRequest(agent="agent-1", action="read_repo", target="repo/project-a", capabilities=frozenset({"GIT_READ"}))
    authorization = apoa.issue_execution_authorization(request)
    assert executor.execute(request, authorization) == "ok"
    assert calls == ["repo/project-a"]


def test_evidence_records_replay_attempt():
    apoa, request = engine(), ExecutionRequest(agent="agent-1", action="read_repo", target="repo/project-a", capabilities=frozenset({"GIT_READ"}))
    auth = apoa.issue_execution_authorization(request)
    assert apoa.consume(request, auth) is True
    assert apoa.consume(request, auth) is False
    assert any("replay" in event.reason.lower() for event in apoa.evidence())
