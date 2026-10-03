from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from controlplane.isolated_worker import DockerIsolatedWorker


def _docker_available() -> bool:
    if os.environ.get("FORGEOS_DOCKER_TESTS") != "1":
        return False
    if shutil.which("docker") is None:
        return False
    try:
        result = subprocess.run(
            ["docker", "info"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0


pytestmark = pytest.mark.skipif(
    not _docker_available(),
    reason="set FORGEOS_DOCKER_TESTS=1 on a host with a usable Docker daemon",
)


def make_worker(timeout_seconds: int = 10) -> DockerIsolatedWorker:
    return DockerIsolatedWorker(
        image="python:3.12-alpine",
        timeout_seconds=timeout_seconds,
    )


def run_python(worker: DockerIsolatedWorker, workspace: Path, code: str):
    return worker.run(["python", "-c", code], workspace)


def test_network_is_disabled(tmp_path: Path):
    result = run_python(
        make_worker(),
        tmp_path,
        "import socket; "
        "\ntry: "
        " socket.create_connection(('1.1.1.1', 443), timeout=2)"
        "\nexcept OSError as exc: "
        " print(f'ERRNO={exc.errno}')",
    )

    assert result.returncode == 0
    assert "ERRNO=101" in result.stdout


def test_root_filesystem_is_read_only(tmp_path: Path):
    result = run_python(
        make_worker(),
        tmp_path,
        "from pathlib import Path; Path('/forgeos-root-write-test').write_text('blocked')",
    )

    assert result.returncode != 0
    assert "Read-only file system" in result.stderr


def test_workspace_is_writable(tmp_path: Path):
    result = run_python(
        make_worker(),
        tmp_path,
        "from pathlib import Path; Path('/workspace/forgeos-write-test').write_text('ok')",
    )

    assert result.returncode == 0
    assert (tmp_path / "forgeos-write-test").read_text() == "ok"


def test_host_environment_is_not_forwarded(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("FORGEOS_HOST_SECRET", "must-not-enter-container")
    result = run_python(
        make_worker(),
        tmp_path,
        "import os; print(os.environ.get('FORGEOS_HOST_SECRET', 'ABSENT'))",
    )

    assert result.returncode == 0
    assert result.stdout.strip() == "ABSENT"


def test_no_new_privileges_is_enabled(tmp_path: Path):
    result = run_python(
        make_worker(),
        tmp_path,
        "print(next(line for line in open('/proc/self/status') if line.startswith('NoNewPrivs:')))",
    )

    assert result.returncode == 0
    assert "NoNewPrivs:\t1" in result.stdout


def test_effective_capabilities_are_zero(tmp_path: Path):
    result = run_python(
        make_worker(),
        tmp_path,
        "print(next(line for line in open('/proc/self/status') if line.startswith('CapEff:')))",
    )

    assert result.returncode == 0
    assert "CapEff:\t0000000000000000" in result.stdout


def test_timeout_is_enforced(tmp_path: Path):
    worker = make_worker(timeout_seconds=1)

    with pytest.raises(RuntimeError, match="isolated execution timed out"):
        run_python(worker, tmp_path, "while True: pass")
