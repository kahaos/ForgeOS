from examples.run_gemini_forgeos_trial import NATIVE_BYPASS_TOOLS

EXPECTED_NATIVE_BYPASS_TOOLS = (
    "run_shell_command",
    "write_file",
    "replace",
    "read_file",
    "list_directory",
    "glob",
)


def test_native_bypass_regression_matrix_covers_all_canonical_tools():
    assert NATIVE_BYPASS_TOOLS == EXPECTED_NATIVE_BYPASS_TOOLS

def test_trial_policy_denies_every_native_bypass_tool(tmp_path):
    from examples.run_gemini_forgeos_trial import build_gemini_settings

    workspace = tmp_path / "workspace"
    workspace.mkdir()

    build_gemini_settings(workspace, tmp_path / "server.py")

    policy = (tmp_path / "forgeos-trial.toml").read_text(encoding="utf-8")

    for tool_name in NATIVE_BYPASS_TOOLS:
        assert f'toolName = "{tool_name}"' in policy
        assert 'decision = "deny"' in policy
