import subprocess
from pathlib import Path

import pytest

from controlplane.isolated_worker import DockerExecutorAdapter, DockerIsolatedWorker, IsolationProfile
from controlplane.models import ActionRequest


def test_hardened_profile_defaults_to_no_network_and_read_only():
    profile = IsolationProfile()

    assert profile.network == "none"
    assert profile.read_only is True
    assert profile.cap_drop == ("ALL",)
    assert profile.no_new_privileges is True
    assert profile.memory == "256m"
    assert profile.cpus == "1.0"
    assert profile.pids_limit == 64


def test_hardened_profile_rejects_network_and_privilege_relaxation():
    with pytest.raises(ValueError, match="network must be 'none'"):
        IsolationProfile(network="bridge")

    with pytest.raises(ValueError, match="read_only must be enabled"):
        IsolationProfile(read_only=False)

    with pytest.raises(ValueError, match="ALL capabilities must be dropped"):
        IsolationProfile(cap_drop=())

    with pytest.raises(ValueError, match="no_new_privileges must be enabled"):
        IsolationProfile(no_new_privileges=False)


def test_build_command_contains_isolation_controls(tmp_path: Path):
    worker = DockerIsolatedWorker(image="python:3.12-alpine")
    argv = worker.build_command(
        ["python", "-c", "print('ok')"],
        workspace=tmp_path,
    )

    assert argv[:3] == ["docker", "run", "--rm"]
    assert "--network" in argv and argv[argv.index("--network") + 1] == "none"
    assert "--read-only" in argv
    assert "--cap-drop" in argv and argv[argv.index("--cap-drop") + 1] == "ALL"
    assert "--security-opt" in argv
    assert "no-new-privileges=true" in argv
    assert "--memory" in argv and argv[argv.index("--memory") + 1] == "256m"
    assert "--cpus" in argv and argv[argv.index("--cpus") + 1] == "1.0"
    assert "--pids-limit" in argv and argv[argv.index("--pids-limit") + 1] == "64"
    assert "--mount" in argv
    assert "type=bind" in argv[argv.index("--mount") + 1]
    assert "readonly" not in argv[argv.index("--mount") + 1]
    assert argv[-3:] == ["python", "-c", "print('ok')"]


def test_build_command_rejects_shell_string(tmp_path: Path):
    worker = DockerIsolatedWorker(image="python:3.12-alpine")

    with pytest.raises(TypeError, match="command must be a sequence"):
        worker.build_command("python -c 'print(1)'", workspace=tmp_path)


def test_run_uses_no_host_environment_and_timeout(tmp_path: Path, monkeypatch):
    worker = DockerIsolatedWorker(image="python:3.12-alpine", timeout_seconds=7)
    captured = {}

    def fake_run(argv, **kwargs):
        captured["argv"] = argv
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(argv, 0, stdout="ok\n", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = worker.run(["python", "-c", "print('ok')"], workspace=tmp_path)

    assert result.returncode == 0
    assert captured["kwargs"]["timeout"] == 7
    assert captured["kwargs"]["check"] is False
    assert captured["kwargs"]["env"] == {}
    assert "DOCKER_HOST" not in captured["kwargs"]["env"]


def test_run_fails_closed_when_docker_is_unavailable(tmp_path: Path, monkeypatch):
    worker = DockerIsolatedWorker(image="python:3.12-alpine")

    def fake_run(*args, **kwargs):
        raise FileNotFoundError("docker")

    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(RuntimeError, match="docker runtime is unavailable"):
        worker.run(["python", "-c", "print('ok')"], workspace=tmp_path)


def test_docker_executor_adapter_returns_structured_success(tmp_path: Path):
    class FakeWorker:
        def run(self, command, workspace):
            assert command == ["python", "-c", "print('ok')"]
            assert workspace == tmp_path
            return subprocess.CompletedProcess(command, 0, stdout="ok\n", stderr="")

    request = ActionRequest("agent-1", "test", "run", target="test-target")
    adapter = DockerExecutorAdapter(
        FakeWorker(),
        command_builder=lambda _: ["python", "-c", "print('ok')"],
        workspace=tmp_path,
    )

    assert adapter(request) == {
        "status": "completed",
        "returncode": 0,
        "stdout": "ok\n",
        "stderr": "",
    }


def test_docker_executor_adapter_represents_nonzero_exit_as_failure(tmp_path: Path):
    class FakeWorker:
        def run(self, command, workspace):
            return subprocess.CompletedProcess(command, 7, stdout="", stderr="boom\n")

    request = ActionRequest("agent-1", "test", "run", target="test-target")
    adapter = DockerExecutorAdapter(
        FakeWorker(),
        command_builder=lambda _: ["python", "-c", "raise SystemExit(7)"],
        workspace=tmp_path,
    )

    assert adapter(request) == {
        "status": "failed",
        "returncode": 7,
        "stdout": "",
        "stderr": "boom\n",
    }


def test_docker_executor_adapter_represents_runtime_failure_as_failure(tmp_path: Path):
    class FakeWorker:
        def run(self, command, workspace):
            raise RuntimeError("isolated execution timed out")

    request = ActionRequest("agent-1", "test", "run", target="test-target")
    adapter = DockerExecutorAdapter(
        FakeWorker(),
        command_builder=lambda _: ["python", "-c", "while True: pass"],
        workspace=tmp_path,
    )

    assert adapter(request) == {
        "status": "failed",
        "error": "isolated execution timed out",
    }


def test_docker_executor_adapter_represents_invalid_execution_as_failure(tmp_path: Path):
    class FakeWorker:
        def run(self, command, workspace):
            raise ValueError("command must be a sequence of arguments, not a shell string")

    request = ActionRequest("agent-1", "test", "run", target="test-target")
    adapter = DockerExecutorAdapter(
        FakeWorker(),
        command_builder=lambda _: "python -c 'print(1)'",
        workspace=tmp_path,
    )

    assert adapter(request) == {
        "status": "failed",
        "error": "command must be a sequence of arguments, not a shell string",
    }
