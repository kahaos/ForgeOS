"""Build a deliberately constrained Gemini CLI trial for ForgeOS.

This module only constructs the launch configuration. The agent receives a
single ForgeOS MCP server and an explicit MCP tool allowlist; no provider
credentials are embedded in Gemini settings.
"""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any


FORGEOS_TOOLS = [
    "read_file",
    "write_file",
    "run_test",
    "git_status",
    "git_commit",
    "git_push",
    "request_action",
]


def build_gemini_settings(workspace: str | Path, server_script: str) -> dict[str, Any]:
    """Return the minimal Gemini settings needed for a ForgeOS-only trial."""
    workspace = str(Path(workspace).resolve())
    return {
        "mcp": {
            "allowed": ["forgeos"],
        },
        "mcpServers": {
            "forgeos": {
                "command": sys.executable,
                "args": [server_script],
                "cwd": workspace,
                "trust": False,
                "includeTools": list(FORGEOS_TOOLS),
            }
        },
        "tools": {
            # An empty core allowlist disables Gemini's built-in tools. The
            # only model-visible tools are therefore the ForgeOS MCP tools.
            "core": [],
        },
        "security": {
            "disableYoloMode": True,
            "disableAlwaysAllow": True,
        },
        "general": {
            "defaultApprovalMode": "default",
        },
        "privacy": {
            "usageStatisticsEnabled": False,
        },
    }


def build_gemini_command(workspace: str | Path, prompt: str) -> list[str]:
    """Build a non-YOLO Gemini CLI invocation for the disposable workspace."""
    workspace = str(Path(workspace).resolve())
    return [
        "gemini",
        "--approval-mode",
        "default",
        "--extensions",
        "none",
        "--output-format",
        "text",
        "--include-directories",
        workspace,
        prompt,
    ]


__all__ = ["FORGEOS_TOOLS", "build_gemini_command", "build_gemini_settings"]
