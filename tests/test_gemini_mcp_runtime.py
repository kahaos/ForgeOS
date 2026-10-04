from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from controlplane.local_adapters import SafeWorkspaceAdapter
from examples.forgeos_gemini_mcp_server import build_trial_runtime


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SERVER_SCRIPT = PROJECT_ROOT / "examples" / "forgeos_gemini_mcp_server.py"


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


def _start_server(tmp_path: Path) -> tuple[subprocess.Popen[str], Path]:
    workspace = tmp_path / "workspace"
    state_dir = tmp_path / "state"
    process = subprocess.Popen(
        [
            sys.executable,
            str(SERVER_SCRIPT),
            "--workspace",
            str(workspace),
            "--state-dir",
            str(state_dir),
            "--task-id",
            "real-agent-website-build",
            "--agent-id",
            "website-agent",
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert process.stdin is not None
    assert process.stdout is not None
    return process, workspace


def _rpc(process: subprocess.Popen[str], message: dict[str, object]) -> dict[str, object]:
    assert process.stdin is not None
    assert process.stdout is not None
    process.stdin.write(json.dumps(message) + "\n")
    process.stdin.flush()
    return json.loads(process.stdout.readline())


def test_real_mcp_launcher_exposes_only_fixed_tools_and_executes_governed_write(tmp_path: Path) -> None:
    process, workspace = _start_server(tmp_path)
    try:
        initialize = _rpc(process, {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        assert initialize["result"]["serverInfo"]["name"] == "forgeos-control-plane"

        tools = _rpc(process, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        names = {tool["name"] for tool in tools["result"]["tools"]}
        assert names == {
            "read_file",
            "forgeos_write_file",
            "run_test",
            "git_status",
            "git_commit",
            "git_push",
            "request_action",
        }
        assert "shell" not in names

        write_schema = next(
            tool for tool in tools["result"]["tools"]
            if tool["name"] == "forgeos_write_file"
        )
        assert write_schema["inputSchema"]["required"] == ["name", "content"]
        assert "workspace" not in write_schema["inputSchema"]["properties"]

        write = _rpc(
            process,
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "forgeos_write_file",
                    "arguments": {
                        "name": "index.html",
                        "content": "<h1>ForgeOS</h1>\n",
                    },
                },
            },
        )
        assert write["result"]["isError"] is False
        assert (workspace / "index.html").read_text(encoding="utf-8") == "<h1>ForgeOS</h1>\n"
    finally:
        if process.stdin is not None:
            process.stdin.close()
        process.terminate()
        process.wait(timeout=5)
