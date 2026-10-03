from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from controlplane.local_adapters import SafeWorkspaceAdapter
from examples.forgeos_gemini_mcp_server import build_trial_runtime


def test_workspace_adapter_rejects_path_escape(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    adapter = SafeWorkspaceAdapter(workspace)

    with pytest.raises(ValueError, match="outside workspace"):
        adapter.write("../escape.txt", "blocked")


def test_workspace_adapter_reads_and_writes_only_inside_workspace(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    adapter = SafeWorkspaceAdapter(workspace)

    result = adapter.write("site/index.html", "<h1>ForgeOS</h1>")

    assert result["status"] == "completed"
    assert (workspace / "site/index.html").read_text(encoding="utf-8") == "<h1>ForgeOS</h1>"
    assert adapter.read("site/index.html")["content"] == "<h1>ForgeOS</h1>"


def test_trial_runtime_registers_only_governed_executors(tmp_path: Path) -> None:
    runtime = build_trial_runtime(tmp_path)

    assert set(runtime["gateway"].adapters) == {
        "filesystem:read",
        "filesystem:write",
        "test:run",
        "git:status",
        "git:commit",
        "git:push",
        "secrets:read",
    }
    assert "shell:exec" not in runtime["gateway"].adapters


def test_git_status_is_allowed_inside_repository_scope(tmp_path: Path) -> None:
    runtime = build_trial_runtime(tmp_path)
    result = runtime["gateway"].request(
        runtime["task_id"],
        runtime["agent_id"],
        "git",
        "status",
        str(runtime["repository"]),
        {"repository": str(runtime["repository"])},
        executor_id="git:status",
    )

    assert result["verdict"] == "allow"
    assert result["result"]["status"] == "completed"


def test_feature_push_executes_but_main_push_is_denied(tmp_path: Path) -> None:
    runtime = build_trial_runtime(tmp_path)
    gateway = runtime["gateway"]
    task_id = runtime["task_id"]
    agent_id = runtime["agent_id"]
    repo = runtime["repository"]

    (repo / "index.html").write_text("<h1>ForgeOS</h1>\n", encoding="utf-8")
    subprocess.run(["git", "add", "index.html"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "trial"], cwd=repo, check=True, capture_output=True, text=True)

    feature = gateway.request(
        task_id,
        agent_id,
        "git",
        "push",
        str(repo),
        {"repository": str(repo), "branch": "feature/site"},
        executor_id="git:push",
    )
    assert feature["verdict"] == "allow"

    main = gateway.request(
        task_id,
        agent_id,
        "git",
        "push",
        str(repo),
        {"repository": str(repo), "branch": "main"},
        executor_id="git:push",
    )
    assert main["verdict"] == "deny"
    assert "result" not in main


def test_secret_request_creates_approval_without_exposing_secret(tmp_path: Path) -> None:
    runtime = build_trial_runtime(tmp_path)
    result = runtime["gateway"].request(
        runtime["task_id"],
        runtime["agent_id"],
        "secrets",
        "read",
        "trial-secrets",
        {"resource": "trial-secrets"},
        executor_id="secrets:read",
    )

    assert result["verdict"] == "ask"
    approval = runtime["controlplane"].approvals[result["approval_id"]]
    assert "secret material" not in str(approval).lower()
    assert approval["status"] == "pending"
