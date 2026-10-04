"""Reproducible low-risk trial of a real-agent-shaped workload through ForgeOS.

The harness deliberately uses only a disposable local workspace and simulated
Git/secrets adapters. It exercises the same task-scoped RuntimeGateway and
signed ExecutionWorker path used by the hardened control plane.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
from typing import Any

from controlplane.execution_worker import ExecutionWorker
from controlplane.gateway import RuntimeGateway, SimulatedToolAdapter
from controlplane.store import ControlPlane

KEY = b"forgeos-real-agent-trial-key"


def build_trial_controlplane(state_dir: str | Path) -> tuple[ControlPlane, RuntimeGateway]:
    cp = ControlPlane(Path(state_dir) / "controlplane")
    cp.register("website-agent", "human", ["FS_WRITE", "GIT_PUSH", "READ_SECRETS"])
    expires = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    cp.create_task("real-agent-website-build", "human", "Build a disposable website", expires)
    cp.issue_grant(
        "real-agent-website-build",
        "website-agent",
        "FS_WRITE",
        {"tool": "filesystem", "action": "write", "workspace": str(Path(state_dir).resolve())},
        "human",
        expires,
    )
    cp.issue_grant(
        "real-agent-website-build",
        "website-agent",
        "GIT_PUSH",
        {"tool": "git", "action": "push", "repository": "forgeos-agent-trial", "branch": "feature/*"},
        "human",
        expires,
    )
    cp.issue_grant(
        "real-agent-website-build",
        "website-agent",
        "READ_SECRETS",
        {"tool": "secrets", "action": "read", "resource": "trial-secrets"},
        "human",
        expires,
    )

    worker = ExecutionWorker(cp, KEY)
    gateway = RuntimeGateway(cp, worker, KEY)
    workspace = str(Path(state_dir).resolve())

    def write_file(request):
        name = str(request.detail.get("name", "forgeos-agent-trial.txt"))
        if Path(name).name != name or not name.endswith(".txt"):
            raise ValueError("trial file must be a local .txt filename")
        path = Path(workspace) / name
        path.write_text(str(request.detail.get("content", "ForgeOS real agent trial\n")), encoding="utf-8")
        return {"status": "completed", "path": name, "simulated": True}

    gateway.register_adapter("filesystem:write", workspace, write_file)
    gateway.register_adapter("git:push", "forgeos-agent-trial", SimulatedToolAdapter("git-push"))
    gateway.register_adapter("secrets:read", "trial-secrets", SimulatedToolAdapter("secret-access"))
    return cp, gateway


def run_trial(workspace: str | Path) -> dict[str, Any]:
    workspace_path = Path(workspace).resolve()
    workspace_path.mkdir(parents=True, exist_ok=True)
    cp, gateway = build_trial_controlplane(workspace_path)

    workspace_result = gateway.request(
        "real-agent-website-build",
        "website-agent",
        "filesystem",
        "write",
        str(workspace_path),
        {"workspace": str(workspace_path), "name": "forgeos-agent-trial.txt", "content": "ForgeOS governed agent trial\n"},
        executor_id="filesystem:write",
    )
    feature_push = gateway.request(
        "real-agent-website-build",
        "website-agent",
        "git",
        "push",
        "forgeos-agent-trial",
        {"repository": "forgeos-agent-trial", "branch": "feature/website"},
        executor_id="git:push",
    )
    main_push = gateway.request(
        "real-agent-website-build",
        "website-agent",
        "git",
        "push",
        "forgeos-agent-trial",
        {"repository": "forgeos-agent-trial", "branch": "main"},
        executor_id="git:push",
    )
    other_repo = gateway.request(
        "real-agent-website-build",
        "website-agent",
        "git",
        "push",
        "another-repository",
        {"repository": "another-repository", "branch": "feature/website"},
        executor_id="git:push",
    )
    sensitive = gateway.request(
        "real-agent-website-build",
        "website-agent",
        "secrets",
        "read",
        "trial-secrets",
        {"resource": "trial-secrets"},
        executor_id="secrets:read",
    )
    approval_id = sensitive["approval_id"]
    sensitive_execution = gateway.approve_and_execute(approval_id, actor="human-trial-operator")

    return {
        "task_id": "real-agent-website-build",
        "agent_id": "website-agent",
        "workspace_file": "forgeos-agent-trial.txt",
        "workspace_write": workspace_result,
        "feature_push": feature_push,
        "main_push": main_push,
        "other_repo": other_repo,
        "sensitive": sensitive,
        "approval_id": approval_id,
        "sensitive_execution": sensitive_execution,
        "external_services": [],
        "evidence_count": len(cp.evidence.all()),
        "evidence_ok": cp.evidence.verify(),
    }


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="forgeos-real-agent-trial-") as td:
        result = run_trial(td)
        print("FORGEOS REAL AGENT TRIAL")
        print("FEATURE PUSH:", result["feature_push"]["verdict"])
        print("MAIN PUSH:", result["main_push"]["verdict"])
        print("OTHER REPOSITORY:", result["other_repo"]["verdict"])
        print("SENSITIVE ACCESS:", result["sensitive"]["verdict"])
        print("SENSITIVE EXECUTION:", result["sensitive_execution"]["result"])
        print("EVIDENCE EVENTS:", result["evidence_count"])
        print("EVIDENCE OK:", result["evidence_ok"])
        print("EXTERNAL SERVICES:", result["external_services"])


if __name__ == "__main__":
    main()
