from __future__ import annotations

from controlplane.execution_worker import ExecutionAuthorizer, ExecutionWorker
from controlplane.store import ControlPlane


KEY = b"forgeos-hardening-test-key"


def make_pending(tmp_path):
    cp = ControlPlane(tmp_path / "controlplane")
    cp.register("agent-1", owner="tester", capabilities=["GIT_PUSH"])
    cp.register_executor("simulated-git-push", target="test-repo")
    pending = cp.request(
        "agent-1",
        "git",
        "push",
        target="test-repo",
        detail={"branch": "main"},
        executor_id="simulated-git-push",
    )
    assert pending["verdict"] == "ask"
    return cp, pending["approval_id"]


def test_executor_binding_survives_controlplane_restart(tmp_path):
    cp, approval_id = make_pending(tmp_path)
    cp.decide(approval_id, approve=True, actor="human", execute=False)

    restarted = ControlPlane(tmp_path / "controlplane")
    authorization = ExecutionAuthorizer(restarted, KEY).issue(
        approval_id,
        executor_id="simulated-git-push",
    )

    assert authorization.executor_id == "simulated-git-push"
    assert authorization.target == "test-repo"


def test_execution_nonce_is_persisted_and_consumed_once(tmp_path):
    cp, approval_id = make_pending(tmp_path)
    cp.decide(approval_id, approve=True, actor="human", execute=False)
    authorization = ExecutionAuthorizer(cp, KEY).issue(approval_id, "simulated-git-push")

    assert cp.consume_execution_nonce(authorization.nonce) is True
    assert cp.consume_execution_nonce(authorization.nonce) is False

    restarted = ControlPlane(tmp_path / "controlplane")
    assert restarted.consume_execution_nonce(authorization.nonce) is False


def test_failed_execution_cannot_replay_authorization(tmp_path):
    cp, approval_id = make_pending(tmp_path)
    cp.decide(approval_id, approve=True, actor="human", execute=False)
    authorization = ExecutionAuthorizer(cp, KEY).issue(approval_id, "simulated-git-push")

    worker = ExecutionWorker(cp, KEY)
    worker.register_executor(
        "simulated-git-push",
        target="test-repo",
        executor=lambda request: (_ for _ in ()).throw(RuntimeError("executor failed")),
    )

    try:
        worker.execute(authorization)
    except RuntimeError:
        pass
    else:
        raise AssertionError("expected executor failure")

    restarted = ControlPlane(tmp_path / "controlplane")
    restarted_worker = ExecutionWorker(restarted, KEY)
    restarted_worker.register_executor(
        "simulated-git-push",
        target="test-repo",
        executor=lambda request: {"status": "must-not-run"},
    )

    try:
        restarted_worker.execute(authorization)
    except ValueError as exc:
        assert "authorization already consumed" in str(exc)
    else:
        raise AssertionError("authorization replay unexpectedly succeeded")
