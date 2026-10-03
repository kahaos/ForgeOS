from pathlib import Path

import pytest

from controlplane.gemini_adapter import GeminiForgeOSAdapter
from controlplane.store import ControlPlane


def make_adapter(tmp_path: Path) -> GeminiForgeOSAdapter:
    cp = ControlPlane(tmp_path / "controlplane")
    cp.register(
        "gemini-test-agent-01",
        owner="gemini",
        capabilities=["FS_READ", "FS_WRITE", "SHELL", "GIT_PUSH", "READ_SECRETS"],
    )
    return GeminiForgeOSAdapter(cp, "gemini-test-agent-01", tmp_path / "workspace")


def test_gemini_approval_pauses_then_executes_exact_request(tmp_path):
    adapter = make_adapter(tmp_path)

    pending = adapter.execute_tool("git_push", {"target": "test-repo"})

    assert pending["verdict"] == "ask"
    assert pending["approval_id"]
    assert pending["request_digest"]

    approved = adapter.approve(pending["approval_id"], True)

    assert approved["verdict"] == "allow"
    assert approved["result"] == {
        "status": "completed",
        "simulated": True,
        "operation": "git_push",
        "target": "test-repo",
    }
    assert adapter.controlplane.approvals[pending["approval_id"]]["status"] == "completed"


def test_gemini_approval_rejects_tampering(tmp_path):
    adapter = make_adapter(tmp_path)
    pending = adapter.execute_tool("git_push", {"target": "test-repo"})
    approval_id = pending["approval_id"]
    adapter.controlplane.approvals[approval_id]["request"]["target"] = "production-repo"

    with pytest.raises(ValueError, match="approval request digest mismatch"):
        adapter.approve(approval_id, True)


def test_gemini_approval_is_single_use(tmp_path):
    adapter = make_adapter(tmp_path)
    pending = adapter.execute_tool("git_push", {"target": "test-repo"})

    adapter.approve(pending["approval_id"], True)

    with pytest.raises(KeyError):
        adapter.approve(pending["approval_id"], True)
