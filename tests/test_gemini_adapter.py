from pathlib import Path

from controlplane.store import ControlPlane
from controlplane.gemini_adapter import GeminiForgeOSAdapter


def make_adapter(tmp_path: Path) -> GeminiForgeOSAdapter:
    cp = ControlPlane(tmp_path / "controlplane")
    cp.register("gemini-test-agent-01", owner="gemini", capabilities=["FS_READ", "FS_WRITE", "SHELL"])
    return GeminiForgeOSAdapter(cp, "gemini-test-agent-01", tmp_path / "workspace")


def test_allowed_gemini_tool_call_reaches_only_safe_executor(tmp_path):
    adapter = make_adapter(tmp_path)

    result = adapter.execute_tool("create_test_file", {"name": "hello.txt", "content": "forgeos-test"})

    assert result["verdict"] == "allow"
    assert (tmp_path / "workspace" / "hello.txt").read_text() == "forgeos-test"


def test_git_push_is_gated_and_does_not_execute(tmp_path):
    adapter = make_adapter(tmp_path)

    result = adapter.execute_tool("git_push", {"target": "test-repo"})

    assert result["verdict"] == "ask"
    assert result["approval_id"]
    assert not (tmp_path / "workspace" / "PUSHED").exists()


def test_hard_denied_requests_never_reach_executor(tmp_path):
    adapter = make_adapter(tmp_path)

    for tool_name in ("create_agent", "modify_policy", "spend_funds"):
        result = adapter.execute_tool(tool_name, {})
        assert result["verdict"] == "deny"

    assert not (tmp_path / "workspace" / "BYPASS").exists()


def test_unknown_tool_is_denied(tmp_path):
    adapter = make_adapter(tmp_path)

    result = adapter.execute_tool("delete_production", {"target": "prod"})

    assert result["verdict"] == "deny"
    assert "unknown action" in result["reason"]


def test_direct_executor_path_is_not_exposed_by_adapter(tmp_path):
    adapter = make_adapter(tmp_path)

    assert not hasattr(adapter, "executor")
    assert not hasattr(adapter, "execute_direct")
