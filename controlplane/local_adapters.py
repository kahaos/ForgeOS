"""Bounded local adapters for the disposable real-agent trial.

These adapters are intentionally narrower than a general-purpose executor. They
operate only on a trusted trial workspace/repository and never accept a shell
command from the agent.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from .models import ActionRequest


class _WorkspaceBound:
    def __init__(self, workspace: str | Path) -> None:
        self.workspace = Path(workspace).resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)

    def _path(self, relative: str) -> Path:
        if not isinstance(relative, str) or not relative:
            raise ValueError("workspace path is required")
        candidate = (self.workspace / relative).resolve()
        try:
            candidate.relative_to(self.workspace)
        except ValueError as exc:
            raise ValueError("path is outside workspace") from exc
        return candidate


class SafeWorkspaceAdapter(_WorkspaceBound):
    """Read/write only inside the pre-bound disposable workspace."""

    def read(self, relative: str) -> dict[str, Any]:
        path = self._path(relative)
        if not path.is_file():
            return {"status": "failed", "error": "file not found"}
        return {"status": "completed", "path": relative, "content": path.read_text(encoding="utf-8")}

    def write(self, relative: str, content: str) -> dict[str, Any]:
        path = self._path(relative)
        if not isinstance(content, str):
            raise ValueError("content must be text")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return {"status": "completed", "path": relative, "bytes": len(content.encode("utf-8"))}

    def __call__(self, request: ActionRequest) -> dict[str, Any]:
        if request.action == "read":
            return self.read(str(request.detail.get("path", "")))
        if request.action == "write":
            return self.write(str(request.detail.get("name", "")), str(request.detail.get("content", "")))
        raise ValueError(f"unsupported filesystem action: {request.action}")


class SafeTestAdapter(_WorkspaceBound):
    """Run only the fixed pytest invocation in the trial workspace."""

    def __init__(self, workspace: str | Path, timeout_seconds: int = 30) -> None:
        super().__init__(workspace)
        self.timeout_seconds = timeout_seconds

    def __call__(self, request: ActionRequest) -> dict[str, Any]:
        if request.target != str(self.workspace):
            raise ValueError("test target mismatch")
        command = ["python3", "-m", "pytest", "-q"]
        try:
            result = subprocess.run(
                command,
                cwd=self.workspace,
                check=False,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                env={},
            )
        except subprocess.TimeoutExpired:
            return {"status": "failed", "error": "test execution timed out"}
        return {
            "status": "completed" if result.returncode == 0 else "failed",
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }


class SafeGitAdapter:
    """Perform a fixed set of Git operations against one pre-bound repository."""

    def __init__(self, repository: str | Path, remote: str | Path) -> None:
        self.repository = Path(repository).resolve()
        self.remote = Path(remote).resolve()
        if not (self.repository / ".git").exists():
            raise ValueError("repository must be initialized")
        if not self.remote.exists():
            raise ValueError("trial remote does not exist")

    def _run(self, args: list[str]) -> dict[str, Any]:
        result = subprocess.run(
            args,
            cwd=self.repository,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
            env={},
        )
        return {
            "status": "completed" if result.returncode == 0 else "failed",
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

    def __call__(self, request: ActionRequest) -> dict[str, Any]:
        if request.target != str(self.repository):
            raise ValueError("repository target mismatch")
        detail = request.detail or {}
        requested_repository = str(detail.get("repository", request.target))
        if Path(requested_repository).resolve() != self.repository:
            raise ValueError("repository outside trial binding")

        if request.action == "status":
            return self._run(["git", "status", "--short", "--branch"])
        if request.action == "commit":
            message = str(detail.get("message", "")).strip()
            if not message:
                raise ValueError("commit message is required")
            staged = self._run(["git", "add", "--all"])
            if staged["status"] != "completed":
                return staged
            return self._run(["git", "commit", "-m", message])
        if request.action == "push":
            branch = str(detail.get("branch", ""))
            if not branch:
                raise ValueError("branch is required")
            return self._run(["git", "push", str(self.remote), f"HEAD:refs/heads/{branch}"])
        raise ValueError(f"unsupported git action: {request.action}")


class NoSecretAdapter:
    """Provider placeholder that can never return secret material."""

    def __call__(self, request: ActionRequest) -> dict[str, Any]:
        return {"status": "denied", "error": "trial secret material is not exposed by this executor"}


__all__ = [
    "NoSecretAdapter",
    "SafeGitAdapter",
    "SafeTestAdapter",
    "SafeWorkspaceAdapter",
]
