from __future__ import annotations

import json
from pathlib import Path

from examples.run_gemini_forgeos_trial import build_gemini_settings, build_gemini_command


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
