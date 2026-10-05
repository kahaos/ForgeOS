from apoa_core import ApoaEngine, Decision, ExecutionRequest, Policy, PolicyRule


def engine() -> ApoaEngine:
    return ApoaEngine(
        Policy(
            name="demo-v1",
            version="1",
            rules=(
                PolicyRule(
                    action="read_repo",
                    required_capability="GIT_READ",
                    allowed_targets=("repo/",),
                ),
                PolicyRule(
                    action="git_push",
                    required_capability="GIT_PUSH",
                    required_approval=True,
                    allowed_targets=("repo/",),
                ),
                PolicyRule(
                    action="force_push",
                    decision=Decision.DENY,
                    required_capability="GIT_PUSH",
                ),
                PolicyRule(
                    action="refund",
                    required_capability="PAYMENT",
                    parameter_limits={"amount": 100},
                ),
            ),
        )
    )


def test_allow():
    decision = engine().authorize(
        ExecutionRequest(
            agent="agent-1",
            action="read_repo",
            target="repo/project-a",
            capabilities=frozenset({"GIT_READ"}),
        )
    )
    assert decision.decision is Decision.ALLOW


def test_missing_capability_is_denied():
    decision = engine().authorize(
        ExecutionRequest(agent="agent-1", action="read_repo", target="repo/project-a")
    )
    assert decision.decision is Decision.DENY


def test_out_of_scope_target_is_denied():
    decision = engine().authorize(
        ExecutionRequest(
            agent="agent-1",
            action="read_repo",
            target="production/secrets",
            capabilities=frozenset({"GIT_READ"}),
        )
    )
    assert decision.decision is Decision.DENY


def test_explicit_deny_wins():
    decision = engine().authorize(
        ExecutionRequest(
            agent="agent-1",
            action="force_push",
            target="repo/project-a",
            capabilities=frozenset({"GIT_PUSH"}),
        )
    )
    assert decision.decision is Decision.DENY


def test_approval_required():
    decision = engine().authorize(
        ExecutionRequest(
            agent="agent-1",
            action="git_push",
            target="repo/project-a",
            capabilities=frozenset({"GIT_PUSH"}),
        )
    )
    assert decision.decision is Decision.REQUIRE_APPROVAL


def test_parameter_limit_denies_excess():
    decision = engine().authorize(
        ExecutionRequest(
            agent="agent-1",
            action="refund",
            target="payments",
            capabilities=frozenset({"PAYMENT"}),
            parameters={"amount": 101},
        )
    )
    assert decision.decision is Decision.DENY


def test_approved_execution_is_single_use():
    apoa = engine()
    request = ExecutionRequest(
        agent="agent-1",
        action="git_push",
        target="repo/project-a",
        capabilities=frozenset({"GIT_PUSH"}),
    )
    approval = apoa.approve(request, "human-1")
    authorization = apoa.issue_execution_authorization(request, approval)

    assert authorization.decision is Decision.ALLOW
    assert apoa.consume(authorization) is True
    assert apoa.consume(authorization) is False


def test_evidence_is_created_for_decisions():
    apoa = engine()
    request = ExecutionRequest(agent="agent-1", action="missing", target="x")
    decision = apoa.authorize(request)

    assert decision.decision is Decision.DENY
    assert len(apoa.evidence()) == 1
    assert apoa.evidence()[0].request_id == request.request_id
