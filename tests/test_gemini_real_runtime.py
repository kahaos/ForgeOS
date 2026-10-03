from __future__ import annotations

import json
from pathlib import Path

from examples.run_gemini_forgeos_trial import (
    build_gemini_environment,
    build_mcp_server_command,
    build_trial_prompt,
    write_gemini_settings,
)


def test_gemini_environment_isolated_from_host_home(tmp_path: Path) -> None:
    env = build_gemini_environment(tmp_path)

    assert env["HOME"] == str(tmp_path / "home")
    assert env["GEMINI_CLI_HOME"] == str(tmp_path / "gemini-home")
    assert env["HOME"] != str(Path.home())


def test_write_gemini_settings_creates_only_forgeos_mcp(tmp_path: Path) -> None:
    server_script = tmp_path / "forgeos_mcp_server.py"
    settings_path = write_gemini_settings(tmp_path, str(server_script))

    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    server = settings["mcpServers"]["forgeos"]
    assert settings["mcp"]["allowed"] == ["forgeos"]
    assert server["includeTools"] == [
        "read_file",
        "write_file",
        "run_test",
        "git_status",
        "git_commit",
        "git_push",
        "request_action",
    ]
    # Keep the MCP server untrusted at the Gemini layer so ForgeOS remains the
    # authoritative policy/approval boundary for every tool action.
    assert server["trust"] is False
    assert server["args"] == [
        str(server_script.resolve()),
        "--workspace",
        str((tmp_path / "workspace").resolve()),
        "--state-dir",
        str((tmp_path / "state").resolve()),
        "--task-id",
        "real-agent-website-build",
        "--agent-id",
        "website-agent",
    ]
    assert settings["tools"]["core"] == []
    assert settings["security"]["disableYoloMode"] is True
    assert settings["security"]["disableAlwaysAllow"] is True


def test_gemini_mcp_server_command_has_no_shell_or_credentials(tmp_path: Path) -> None:
    command = build_mcp_server_command(
        workspace=tmp_path / "workspace",
        state_dir=tmp_path / "state",
        task_id="real-agent-website-build",
        agent_id="website-agent",
    )

    assert command[0].endswith("python") or command[0].endswith("python3")
    assert any(item.endswith("forgeos_gemini_mcp_server.py") for item in command)
    assert "real-agent-website-build" in command
    assert "website-agent" in command
    serialized = json.dumps(command).lower()
    assert "api_key" not in serialized
    assert "token" not in serialized
    assert "secret" not in serialized
    assert "shell" not in serialized


def test_trial_prompt_requires_governed_website_workflow(tmp_path: Path) -> None:
    prompt = build_trial_prompt(tmp_path / "workspace")
    lowered = prompt.lower()

    assert "website" in lowered
    assert "forgeos" in lowered
    assert "write_file" in lowered
    assert "git_commit" in lowered
    assert "git_push" in lowered
    assert "feature" in lowered
    assert "production" in lowered
