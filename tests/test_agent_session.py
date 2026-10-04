from __future__ import annotations

from pathlib import Path

import pytest

from controlplane.agent_session import AgentSession
from examples.real_agent_trial import build_trial_controlplane


def test_session_binds_agent_and_task_to_every_tool_call(tmp_path: Path) -> None:
    _cp, gateway = build_trial_controlplane(tmp_path)
    session = AgentSession(gateway, "real-agent-website-build", "website-agent")

    result = session.call(
        "git_push",
        "forgeos-agent-trial",
        "feature/home",
    )

    assert result["verdict"] == "allow"
    assert result["task_id"] == "real-agent-website-build"


def test_session_rejects_cross_task_override(tmp_path: Path) -> None:
    _cp, gateway = build_trial_controlplane(tmp_path)
    session = AgentSession(gateway, "real-agent-website-build", "website-agent")

    with pytest.raises(ValueError, match="session task binding"):
        session.call(
            "git_push",
            "forgeos-agent-trial",
            "feature/home",
            task_id="different-task",
        )


def test_session_rejects_cross_agent_override(tmp_path: Path) -> None:
    _cp, gateway = build_trial_controlplane(tmp_path)
    session = AgentSession(gateway, "real-agent-website-build", "website-agent")

    with pytest.raises(ValueError, match="session agent binding"):
        session.call(
            "git_push",
            "forgeos-agent-trial",
            "feature/home",
            agent_id="different-agent",
        )


def test_session_cannot_be_created_without_authoritative_bindings(tmp_path: Path) -> None:
    _cp, gateway = build_trial_controlplane(tmp_path)

    with pytest.raises(ValueError, match="task_id and agent_id"):
        AgentSession(gateway, "", "")
