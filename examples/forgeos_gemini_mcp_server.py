"""Launch the disposable, ForgeOS-governed MCP runtime for Gemini CLI."""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# The MCP launcher is executed directly by Gemini CLI with cwd bound to the
# disposable workspace. Bootstrap the repository root explicitly so the
# controlplane package remains importable without relying on PYTHONPATH.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from controlplane.authority import Scope
from controlplane.execution_worker import ExecutionWorker
from controlplane.gateway import RuntimeGateway
from controlplane.local_adapters import NoSecretAdapter, SafeGitAdapter, SafeTestAdapter, SafeWorkspaceAdapter
from controlplane.mcp_server import ForgeOSMCPServer, MCPStdioServer
from controlplane.store import ControlPlane

TRIAL_TASK_ID = "real-agent-website-build"
TRIAL_AGENT_ID = "website-agent"
TRIAL_EXPIRY_HOURS = 1


def _run_git(args: list[str], cwd: Path) -> None:
    subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True, env={})


def _ensure_git_repo(workspace: Path, remote: Path) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    remote.parent.mkdir(parents=True, exist_ok=True)
    if not (workspace / ".git").exists():
        _run_git(["git", "init", "-b", "feature/site"], workspace)
        _run_git(["git", "config", "user.name", "ForgeOS Trial Agent"], workspace)
        _run_git(["git", "config", "user.email", "forgeos-trial@example.invalid"], workspace)
    if not remote.exists():
        _run_git(["git", "init", "--bare", str(remote)], remote.parent)
    remotes = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=workspace,
        check=False,
        capture_output=True,
        text=True,
        env={},
    )
    if remotes.returncode != 0:
        _run_git(["git", "remote", "add", "origin", str(remote)], workspace)


def _ensure_authority(cp: ControlPlane, workspace: Path, repository: Path) -> None:
    if TRIAL_AGENT_ID not in cp.agents:
        cp.register(
            TRIAL_AGENT_ID,
            owner="forgeos-trial",
            capabilities=["FS_READ", "FS_WRITE", "TEST_RUN", "GIT_READ", "GIT_COMMIT", "GIT_PUSH", "READ_SECRETS"],
            risk_level="low",
        )

    expires_at = (datetime.now(timezone.utc) + timedelta(hours=TRIAL_EXPIRY_HOURS)).isoformat()
    if TRIAL_TASK_ID not in cp.tasks:
        cp.create_task(
            TRIAL_TASK_ID,
            owner="forgeos-trial",
            purpose="Build a disposable static website under governed Gemini execution",
            expires_at=expires_at,
            human_context={"trial": "real-agent-mcp-v1", "environment": "disposable"},
        )

    existing = [grant.capability for grant in cp.effective_grants(TRIAL_TASK_ID, TRIAL_AGENT_ID)]
    grants = [
        ("FS_READ", {"workspace": str(workspace)}),
        ("FS_WRITE", {"workspace": str(workspace)}),
        ("TEST_RUN", {"workspace": str(workspace)}),
        ("GIT_READ", {"repository": str(repository)}),
        ("GIT_COMMIT", {"repository": str(repository)}),
        ("GIT_PUSH", {"repository": str(repository), "branch": "feature/*"}),
        ("READ_SECRETS", {"resource": "trial-secrets"}),
    ]
    for capability, scope in grants:
        if capability not in existing:
            cp.issue_grant(
                TRIAL_TASK_ID,
                TRIAL_AGENT_ID,
                capability,
                Scope(scope),
                issued_by="forgeos-operator",
                expires_at=expires_at,
            )


def build_trial_runtime(
    root: str | Path,
    *,
    workspace: str | Path | None = None,
    state_dir: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(root).resolve()
    workspace_path = Path(workspace).resolve() if workspace is not None else root / "workspace"
    state_path = Path(state_dir).resolve() if state_dir is not None else root / "state"
    remote_path = state_path / "remote.git"

    workspace_path.mkdir(parents=True, exist_ok=True)
    state_path.mkdir(parents=True, exist_ok=True)
    _ensure_git_repo(workspace_path, remote_path)

    cp = ControlPlane(state_path)
    _ensure_authority(cp, workspace_path, workspace_path)
    worker = ExecutionWorker(cp, b"forgeos-gemini-trial-execution-key")
    gateway = RuntimeGateway(cp, worker, b"forgeos-gemini-trial-execution-key")

    workspace_adapter = SafeWorkspaceAdapter(workspace_path)
    git_adapter = SafeGitAdapter(workspace_path, remote_path)
    test_adapter = SafeTestAdapter(workspace_path)

    gateway.register_adapter("filesystem:read", str(workspace_path), workspace_adapter)
    gateway.register_adapter("filesystem:write", str(workspace_path), workspace_adapter)
    gateway.register_adapter("test:run", str(workspace_path), test_adapter)
    gateway.register_adapter("git:status", str(workspace_path), git_adapter)
    gateway.register_adapter("git:commit", str(workspace_path), git_adapter)
    gateway.register_adapter("git:push", str(workspace_path), git_adapter)
    gateway.register_adapter("secrets:read", "trial-secrets", NoSecretAdapter())

    return {
        "controlplane": cp,
        "worker": worker,
        "gateway": gateway,
        "workspace": workspace_path,
        "repository": workspace_path,
        "remote": remote_path,
        "task_id": TRIAL_TASK_ID,
        "agent_id": TRIAL_AGENT_ID,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--state-dir", required=True)
    parser.add_argument("--task-id", default=TRIAL_TASK_ID)
    parser.add_argument("--agent-id", default=TRIAL_AGENT_ID)
    args = parser.parse_args()

    if args.task_id != TRIAL_TASK_ID or args.agent_id != TRIAL_AGENT_ID:
        raise SystemExit("only the fixed disposable trial task and agent are supported")

    runtime = build_trial_runtime(Path(args.workspace).parent, workspace=args.workspace, state_dir=args.state_dir)
    server = ForgeOSMCPServer(runtime["gateway"], runtime["task_id"], runtime["agent_id"], str(args.workspace))
    MCPStdioServer(server).serve()


if __name__ == "__main__":
    main()
