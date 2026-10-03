from __future__ import annotations

import json
from pathlib import Path

from examples.run_gemini_forgeos_trial import (
    FORGEOS_TOOLS,
    build_gemini_settings,
    build_gemini_command,
    build_trial_environment,
    prepare_trial,
)


def test_gemini_settings_allow_only_forgeos_mcp(tmp_path: Path) -> None:
    settings = build_gemini_settings(tmp_path, "forgeos-server.py")

    assert settings["mcp"]["allowed"] == ["forgeos"]
    assert settings["mcpServers"]["forgeos"]["trust"] is False
    assert settings["mcpServers"]["forgeos"]["includeTools"] == [
        "read_file",
        "write_file",
        "run_test",
        "git_status",
        "git_commit",
        "git_push",
        "request_action",
    ]
    assert settings["tools"]["core"] == []
    assert settings["security"]["disableYoloMode"] is True


def test_gemini_settings_do_not_contain_credentials(tmp_path: Path) -> None:
    settings = build_gemini_settings(tmp_path, "forgeos-server.py")
    serialized = json.dumps(settings).lower()

    assert "api_key" not in serialized
    assert "token" not in serialized
    assert "secret" not in serialized


def test_gemini_command_uses_isolated_home_and_no_yolo(tmp_path: Path) -> None:
    command = build_gemini_command(tmp_path, "Build the trial website")

    assert command[0] == "gemini"
    assert "--yolo" not in command
    assert "--approval-mode" in command
    assert "default" in command


def test_prepare_trial_creates_complete_isolated_runtime(tmp_path: Path) -> None:
    paths = prepare_trial(tmp_path, "forgeos-server.py")

    assert paths.root == tmp_path.resolve()
    assert paths.workspace == (tmp_path / "workspace").resolve()
    assert paths.state == (tmp_path / "state").resolve()
    assert paths.home == (tmp_path / "home").resolve()
    assert paths.gemini_home == (tmp_path / "gemini-home").resolve()
    assert paths.settings == (tmp_path / "workspace/.gemini/settings.json").resolve()

    assert paths.workspace.is_dir()
    assert paths.state.is_dir()
    assert paths.home.is_dir()
    assert paths.gemini_home.is_dir()
    assert paths.settings.is_file()

    settings = json.loads(paths.settings.read_text(encoding="utf-8"))
    assert settings["mcpServers"]["forgeos"]["includeTools"] == FORGEOS_TOOLS
    assert settings["mcpServers"]["forgeos"]["cwd"] == str(paths.workspace)


def test_trial_environment_strips_provider_credentials(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "redacted-test-value")
    monkeypatch.setenv("GOOGLE_API_KEY", "redacted-test-value")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/tmp/test-creds.json")

    environment = build_trial_environment(tmp_path)

    assert "GEMINI_API_KEY" not in environment
    assert "GOOGLE_API_KEY" not in environment
    assert "GOOGLE_APPLICATION_CREDENTIALS" not in environment
    assert environment["HOME"] == str(tmp_path.resolve() / "home")
    assert environment["GEMINI_CLI_HOME"] == str(tmp_path.resolve() / "gemini-home")
