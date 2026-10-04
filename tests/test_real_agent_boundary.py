from __future__ import annotations

from pathlib import Path

import pytest

from controlplane.agent_session import AgentSession
from examples.real_agent_trial import build_trial_controlplane


def test_real_agent_session_has_no_generic_shell_path(tmp_path: Path) -> None:
    _cp, gateway = build_trial_controlplane(tmp_path)
    session = AgentSession(gateway, "real-agent-website-build", "website-agent")

    with pytest.raises(ValueError, match="unknown agent tool"):
        session.call("shell", "", "")


def test_real_agent_session_keeps_sensitive_request_pending(tmp_path: Path) -> None:
    _cp, gateway = build_trial_controlplane(tmp_path)
    session = AgentSession(gateway, "real-agent-website-build", "website-agent")

    result = session.call(
        "request_action",
        "trial-secrets",
        "read",
        tool="secrets",
    )

    assert result["verdict"] == "ask"
    assert result["approval_id"]
    assert result["approval_id"] in gateway.controlplane.approvals
    assert gateway.controlplane.approvals[result["approval_id"]]["status"] == "pending"
