from __future__ import annotations

import json
import multiprocessing as mp
from dataclasses import asdict, replace
from pathlib import Path

import pytest

import controlplane.execution_worker as execution_worker_module
from controlplane.execution_worker import (
    ExecutionAuthorization,
    ExecutionAuthorizer,
    ExecutionWorker,
)
from controlplane.isolated_worker import DockerExecutorAdapter
from controlplane.store import ControlPlane


KEY = b"forgeos-adversarial-hardening-key"


def make_approved_request(tmp_path):
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
    approval_id = pending["approval_id"]
    approved = cp.decide(approval_id, approve=True, actor="human", execute=False)
    assert approved["verdict"] == "allow"
    return cp, approval_id


def make_worker(cp, calls):
    worker = ExecutionWorker(cp, KEY)
    worker.register_executor(
        "simulated-git-push",
        target="test-repo",
        executor=lambda request: calls.append(request.to_dict())
        or {"status": "completed", "simulated": True},
    )
    return worker


def make_docker_worker(cp, calls, tmp_path):
    workspace = tmp_path / "docker-workspace"
    workspace.mkdir()

    class FakeDockerWorker:
        def run(self, command, workspace):
            calls.append((list(command), workspace))
            return type("Result", (), {"returncode": 0, "stdout": "ok\n", "stderr": ""})()

    adapter = DockerExecutorAdapter(
        FakeDockerWorker(),
        command_builder=lambda request: ["git", "push", request.detail["branch"]],
        workspace=workspace,
    )
    worker = ExecutionWorker(cp, KEY)
    worker.register_docker_executor("simulated-git-push", "test-repo", adapter)
    return worker


def test_tampered_authorization_never_reaches_executor(tmp_path):
    cp, approval_id = make_approved_request(tmp_path)
    calls = []
    worker = make_worker(cp, calls)
    authorization = ExecutionAuthorizer(cp, KEY).issue(
        approval_id,
        executor_id="simulated-git-push",
    )

    with pytest.raises(ValueError, match="authorization signature mismatch"):
        worker.execute(replace(authorization, target="production-repo"))

    assert calls == []


def test_docker_tampered_authorization_never_reaches_executor(tmp_path):
    cp, approval_id = make_approved_request(tmp_path)
    calls = []
    worker = make_docker_worker(cp, calls, tmp_path)
    authorization = ExecutionAuthorizer(cp, KEY).issue(
        approval_id,
        executor_id="simulated-git-push",
    )

    with pytest.raises(ValueError, match="authorization signature mismatch"):
        worker.execute(replace(authorization, target="production-repo"))

    assert calls == []


def test_capability_drift_invalidates_issued_authorization(tmp_path):
    cp, approval_id = make_approved_request(tmp_path)
    calls = []
    worker = make_worker(cp, calls)
    authorization = ExecutionAuthorizer(cp, KEY).issue(
        approval_id,
        executor_id="simulated-git-push",
    )

    cp.agents["agent-1"].capabilities = []
    cp._save()
    restarted = ControlPlane(tmp_path / "controlplane")
    restarted_worker = make_worker(restarted, calls)

    with pytest.raises(ValueError, match="agent snapshot mismatch"):
        restarted_worker.execute(authorization)

    assert calls == []
    assert restarted.agents["agent-1"].capabilities == []


def test_docker_capability_drift_never_reaches_executor(tmp_path):
    cp, approval_id = make_approved_request(tmp_path)
    calls = []
    worker = make_docker_worker(cp, calls, tmp_path)
    authorization = ExecutionAuthorizer(cp, KEY).issue(
        approval_id,
        executor_id="simulated-git-push",
    )

    cp.agents["agent-1"].capabilities = []
    cp._save()
    restarted = ControlPlane(tmp_path / "controlplane")
    restarted_worker = make_docker_worker(restarted, calls, tmp_path)

    with pytest.raises(ValueError, match="agent snapshot mismatch"):
        restarted_worker.execute(authorization)

    assert calls == []


def test_policy_version_drift_invalidates_issued_authorization(tmp_path):
    cp, approval_id = make_approved_request(tmp_path)
    calls = []
    worker = make_worker(cp, calls)
    authorization = ExecutionAuthorizer(cp, KEY).issue(
        approval_id,
        executor_id="simulated-git-push",
    )

    original_policy = execution_worker_module.POLICY_VERSION
    execution_worker_module.POLICY_VERSION = original_policy + "-drift"
    try:
        with pytest.raises(ValueError, match="policy version mismatch"):
            worker.execute(authorization)
    finally:
        execution_worker_module.POLICY_VERSION = original_policy

    assert calls == []


def test_executor_substitution_cannot_redirect_authorization(tmp_path):
    cp, approval_id = make_approved_request(tmp_path)
    calls = []
    worker = make_worker(cp, calls)
    worker.register_executor(
        "simulated-other-target",
        target="other-repo",
        executor=lambda request: calls.append(request.to_dict())
        or {"status": "wrong"},
    )
    authorization = ExecutionAuthorizer(cp, KEY).issue(
        approval_id,
        executor_id="simulated-git-push",
    )

    with pytest.raises(ValueError, match="authorization signature mismatch"):
        worker.execute(replace(authorization, executor_id="simulated-other-target"))

    assert calls == []


def test_persisted_authorization_cannot_be_replayed_after_restart(tmp_path):
    cp, approval_id = make_approved_request(tmp_path)
    calls = []
    worker = make_worker(cp, calls)
    authorization = ExecutionAuthorizer(cp, KEY).issue(
        approval_id,
        executor_id="simulated-git-push",
    )

    worker.execute(authorization)

    restarted = ControlPlane(tmp_path / "controlplane")
    restarted_worker = make_worker(restarted, calls)

    with pytest.raises(ValueError, match="authorization already consumed"):
        restarted_worker.execute(authorization)

    assert len(calls) == 1


def test_docker_authorization_cannot_replay_after_restart(tmp_path):
    cp, approval_id = make_approved_request(tmp_path)
    calls = []
    worker = make_docker_worker(cp, calls, tmp_path)
    authorization = ExecutionAuthorizer(cp, KEY).issue(
        approval_id,
        executor_id="simulated-git-push",
    )

    worker.execute(authorization)

    restarted = ControlPlane(tmp_path / "controlplane")
    restarted_worker = make_docker_worker(restarted, calls, tmp_path)

    with pytest.raises(ValueError, match="authorization already consumed"):
        restarted_worker.execute(authorization)

    assert len(calls) == 1


def _concurrent_replay_attempt(args):
    root, auth_path, result_dir, worker_number = args
    data = json.loads(Path(auth_path).read_text(encoding="utf-8"))
    authorization = ExecutionAuthorization(**data)

    cp = ControlPlane(root)
    worker = ExecutionWorker(cp, KEY)

    def executor(request):
        marker = Path(result_dir) / f"EXECUTED-{worker_number}"
        marker.write_text(str(worker_number), encoding="utf-8")
        return {"status": "race-test-executed", "worker": worker_number}

    worker.register_executor(
        "simulated-git-push",
        target="test-repo",
        executor=executor,
    )

    try:
        result = worker.execute(authorization)
        return ("EXECUTED", worker_number, result)
    except Exception as exc:
        return ("REJECTED", worker_number, str(exc))


def test_concurrent_replay_allows_exactly_one_execution(tmp_path):
    cp, approval_id = make_approved_request(tmp_path)
    authorization = ExecutionAuthorizer(cp, KEY).issue(
        approval_id,
        executor_id="simulated-git-push",
    )

    auth_path = tmp_path / "authorization.json"
    result_dir = tmp_path / "results"
    result_dir.mkdir()
    auth_path.write_text(
        json.dumps(asdict(authorization)),
        encoding="utf-8",
    )

    root = str(tmp_path / "controlplane")
    args = [
        (root, str(auth_path), str(result_dir), worker_number)
        for worker_number in range(1, 9)
    ]

    context = mp.get_context("fork")
    with context.Pool(8) as pool:
        results = pool.map(_concurrent_replay_attempt, args)

    executed = [result for result in results if result[0] == "EXECUTED"]
    rejected = [result for result in results if result[0] == "REJECTED"]
    markers = list(result_dir.glob("EXECUTED-*"))

    assert len(executed) == 1
    assert len(rejected) == 7
    assert len(markers) == 1
    assert all("authorization already consumed" in result[2] for result in rejected)
