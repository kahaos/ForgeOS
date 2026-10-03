from __future__ import annotations

from pathlib import Path

from examples.real_agent_trial import run_trial


def test_real_agent_trial_enforces_scoped_authority(tmp_path: Path):
    result = run_trial(tmp_path)

    assert result["task_id"] == "real-agent-website-build"
    assert result["agent_id"] == "website-agent"
    assert result["feature_push"]["verdict"] == "allow"
    assert result["main_push"]["verdict"] == "deny"
    assert result["other_repo"]["verdict"] == "deny"
    assert result["sensitive"]["verdict"] == "ask"
    assert result["approval_id"]
    assert result["evidence_count"] >= 1
    assert result["workspace_file"] == "forgeos-agent-trial.txt"


def test_real_agent_trial_never_contacts_external_services(tmp_path: Path):
    result = run_trial(tmp_path)

    assert result["external_services"] == []
    assert result["sensitive_execution"]["result"]["simulated"] is True
