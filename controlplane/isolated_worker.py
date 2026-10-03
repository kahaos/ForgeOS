"""Hardened Docker-backed execution boundary for ForgeOS workers."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

from .models import ActionRequest


@dataclass(frozen=True)
class IsolationProfile:
    """Fail-closed defaults for untrusted executor commands.

    The initial profile intentionally supports only offline execution. Future
    profiles can add narrowly-scoped network and capability grants, but this
    baseline cannot be relaxed accidentally through constructor arguments.
    """

    network: str = "none"
    read_only: bool = True
    cap_drop: tuple[str, ...] = ("ALL",)
    no_new_privileges: bool = True
    memory: str = "256m"
    cpus: str = "1.0"
    pids_limit: int = 64
    tmpfs: str = "/tmp:rw,nosuid,nodev,noexec,size=64m"

    def __post_init__(self) -> None:
        if self.network != "none":
            raise ValueError("network must be 'none' for the hardened profile")
        if not self.read_only:
            raise ValueError("read_only must be enabled for the hardened profile")
        if self.cap_drop != ("ALL",):
            raise ValueError("ALL capabilities must be dropped for the hardened profile")
        if not self.no_new_privileges:
            raise ValueError("no_new_privileges must be enabled for the hardened profile")
        if self.pids_limit <= 0:
            raise ValueError("pids_limit must be positive")


class DockerIsolatedWorker:
    """Run an already-authorized command in a constrained Docker container.

    ForgeOS remains responsible for authorization. This class is only the
    execution boundary: it never accepts a shell command string and never
    forwards the host environment into the container.
    """

    def __init__(
        self,
        image: str,
        profile: IsolationProfile | None = None,
        timeout_seconds: int = 30,
        docker_binary: str = "docker",
    ) -> None:
        if not image:
            raise ValueError("image is required")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self.image = image
        self.profile = profile or IsolationProfile()
        self.timeout_seconds = timeout_seconds
        self.docker_binary = docker_binary

    def build_command(self, command: Sequence[str], workspace: Path) -> list[str]:
        if isinstance(command, (str, bytes)):
            raise TypeError("command must be a sequence of arguments, not a shell string")
        argv = [str(item) for item in command]
        if not argv or any("\x00" in item for item in argv):
            raise ValueError("command must contain non-empty arguments without NUL bytes")

        workspace = Path(workspace).resolve()
        if not workspace.is_dir():
            raise ValueError("workspace must be an existing directory")

        mount = f"type=bind,src={workspace},dst=/workspace"
        return [
            self.docker_binary,
            "run",
            "--rm",
            "--network",
            self.profile.network,
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges=true",
            "--memory",
            self.profile.memory,
            "--cpus",
            self.profile.cpus,
            "--pids-limit",
            str(self.profile.pids_limit),
            "--tmpfs",
            self.profile.tmpfs,
            "--mount",
            mount,
            "--workdir",
            "/workspace",
            self.image,
            *argv,
        ]

    def run(self, command: Sequence[str], workspace: Path) -> subprocess.CompletedProcess[str]:
        argv = self.build_command(command, workspace)
        try:
            return subprocess.run(
                argv,
                check=False,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                env={},
            )
        except FileNotFoundError as exc:
            raise RuntimeError("docker runtime is unavailable") from exc
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("isolated execution timed out") from exc


CommandBuilder = Callable[[ActionRequest], Sequence[str]]


class DockerExecutorAdapter:
    """Adapt an already-authorized ForgeOS request to isolated Docker execution.

    The command builder and workspace are supplied by the trusted executor
    registration layer. The agent request is input to the builder, but this
    adapter performs no authorization or policy evaluation of its own.
    """

    def __init__(
        self,
        worker: DockerIsolatedWorker,
        command_builder: CommandBuilder,
        workspace: Path,
    ) -> None:
        if not callable(command_builder):
            raise TypeError("command_builder must be callable")
        self.worker = worker
        self.command_builder = command_builder
        self.workspace = Path(workspace).resolve()
        if not self.workspace.is_dir():
            raise ValueError("workspace must be an existing directory")

    def __call__(self, request: ActionRequest) -> dict[str, object]:
        try:
            result = self.worker.run(self.command_builder(request), self.workspace)
        except (RuntimeError, TypeError, ValueError) as exc:
            return {"status": "failed", "error": str(exc)}

        return {
            "status": "completed" if result.returncode == 0 else "failed",
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
