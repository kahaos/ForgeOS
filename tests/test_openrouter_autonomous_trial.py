from pathlib import Path

from examples.run_openrouter_autonomous_trial import build_controlplane


def test_openrouter_autonomous_trial_has_execution_worker(tmp_path: Path):
    cp, gateway = build_controlplane(tmp_path)

    assert gateway.controlplane is cp
    assert gateway.worker is not None
    assert gateway.adapters
    assert "filesystem:write" in gateway.adapters


def test_openrouter_autonomous_trial_uses_canonical_filesystem_write_name(
    tmp_path: Path,
):
    cp, gateway = build_controlplane(tmp_path)
    task_id = next(iter(cp.tasks))

    result = gateway.request(
        task_id,
        "openrouter-website-agent",
        "filesystem",
        "write",
        str(tmp_path),
        {
            "workspace": str(tmp_path),
            "name": "index.html",
            "content": "<h1>ForgeOS</h1>\n",
        },
        executor_id="filesystem:write",
    )

    assert result["verdict"] == "allow"
    assert (tmp_path / "index.html").read_text(encoding="utf-8") == "<h1>ForgeOS</h1>\n"

def test_openrouter_autonomous_trial_rebuilds_provider_tool_call_shape():
    from examples.run_openrouter_autonomous_trial import _provider_assistant_message

    result = {
        "content": "",
        "tool_calls": [
            {
                "id": "call-test-1",
                "name": "forgeos_write_file",
                "arguments": {
                    "path": "index.html",
                    "content": "<h1>ForgeOS</h1>",
                },
            }
        ],
    }

    message = _provider_assistant_message(result)

    assert message["role"] == "assistant"
    assert message["content"] == ""
    assert message["tool_calls"] == [
        {
            "id": "call-test-1",
            "type": "function",
            "function": {
                "name": "forgeos_write_file",
                "arguments": '{"path":"index.html","content":"<h1>ForgeOS</h1>"}',
            },
        }
    ]

def test_completion_feedback_requires_agent_to_continue_when_assets_are_missing():
    from examples.run_openrouter_autonomous_trial import completion_feedback

    result = {
        "complete": False,
        "missing_files": ["style.css", "script.js"],
        "errors": [],
    }

    feedback = completion_feedback(result)

    assert feedback is not None
    assert "style.css" in feedback
    assert "script.js" in feedback
    assert "continue" in feedback.lower()


def test_validate_website_completion_detects_missing_local_assets(tmp_path):
    from examples.run_openrouter_autonomous_trial import validate_website_completion

    (tmp_path / "index.html").write_text(
        '<html><head>'
        '<link rel="stylesheet" href="style.css">'
        '</head><body>'
        '<script src="script.js"></script>'
        '</body></html>',
        encoding="utf-8",
    )

    result = validate_website_completion(tmp_path)

    assert result["complete"] is False
    assert "style.css" in result["missing_files"]
    assert "script.js" in result["missing_files"]


def test_validate_website_completion_accepts_complete_site(tmp_path):
    from examples.run_openrouter_autonomous_trial import validate_website_completion

    (tmp_path / "index.html").write_text(
        '<html><head>'
        '<link rel="stylesheet" href="style.css">'
        '</head><body>'
        '<script src="script.js"></script>'
        '</body></html>',
        encoding="utf-8",
    )

    (tmp_path / "style.css").write_text(
        "body { margin: 0; }",
        encoding="utf-8",
    )

    (tmp_path / "script.js").write_text(
        "console.log('ForgeOS');",
        encoding="utf-8",
    )

    result = validate_website_completion(tmp_path)

    assert result["complete"] is True
    assert result["missing_files"] == []


def test_autonomous_trial_success_requires_completed_website(tmp_path):
    from examples.run_openrouter_autonomous_trial import validate_website_completion

    (tmp_path / "index.html").write_text(
        '<link rel="stylesheet" href="style.css">'
        '<script src="script.js"></script>',
        encoding="utf-8",
    )

    result = validate_website_completion(tmp_path)

    assert result["complete"] is False


def test_validate_website_completion_accepts_completed_website(tmp_path):
    from examples.run_openrouter_autonomous_trial import validate_website_completion

    (tmp_path / "index.html").write_text(
        '<link rel="stylesheet" href="style.css">'
        '<script src="script.js"></script>',
        encoding="utf-8",
    )
    (tmp_path / "style.css").write_text(
        "body { margin: 0; }",
        encoding="utf-8",
    )
    (tmp_path / "script.js").write_text(
        "console.log('ForgeOS');",
        encoding="utf-8",
    )

    result = validate_website_completion(tmp_path)

    assert result["complete"] is True

def test_autonomous_trial_success_requires_completion_validation():
    from examples.run_openrouter_autonomous_trial import autonomous_trial_success

    assert autonomous_trial_success(
        tool_calls=3,
        allowed=3,
        files=["index.html", "style.css"],
        created_files={"index.html", "style.css"},
        completion={"complete": False},
        outside_denied=True,
        evidence_ok=True,
    ) is False


def test_autonomous_trial_success_accepts_completed_website():
    from examples.run_openrouter_autonomous_trial import autonomous_trial_success

    assert autonomous_trial_success(
        tool_calls=3,
        allowed=3,
        files=["index.html", "style.css", "script.js"],
        created_files={"index.html", "style.css", "script.js"},
        completion={"complete": True},
        outside_denied=True,
        evidence_ok=True,
    ) is True

def test_autonomous_trial_task_ids_are_unique():
    from examples.run_openrouter_autonomous_trial import autonomous_trial_task_id

    first = autonomous_trial_task_id()
    second = autonomous_trial_task_id()

    assert first.startswith("openrouter-autonomous-website-")
    assert second.startswith("openrouter-autonomous-website-")
    assert first != second

def test_build_controlplane_uses_unique_task_id(tmp_path):
    from examples.run_openrouter_autonomous_trial import build_controlplane

    cp1, _ = build_controlplane(tmp_path / "run1")
    cp2, _ = build_controlplane(tmp_path / "run2")

    task_ids_1 = list(cp1.tasks)
    task_ids_2 = list(cp2.tasks)

    assert len(task_ids_1) == 1
    assert len(task_ids_2) == 1

    assert task_ids_1[0].startswith("openrouter-autonomous-website-")
    assert task_ids_2[0].startswith("openrouter-autonomous-website-")
    assert task_ids_1[0] != task_ids_2[0]

def test_autonomous_trial_provider_error_is_not_completion():
    from examples.run_openrouter_autonomous_trial import should_accept_agent_completion

    assert should_accept_agent_completion(
        finish_reason="error",
        created_files={"index.html", "style.css", "script.js"},
        completion={"complete": True},
    ) is False


def test_autonomous_trial_completion_requires_current_run_files():
    from examples.run_openrouter_autonomous_trial import should_accept_agent_completion

    assert should_accept_agent_completion(
        finish_reason="stop",
        created_files=set(),
        completion={"complete": True},
    ) is False


def test_autonomous_trial_completion_accepts_successful_current_run():
    from examples.run_openrouter_autonomous_trial import should_accept_agent_completion

    assert should_accept_agent_completion(
        finish_reason="stop",
        created_files={"index.html", "style.css", "script.js"},
        completion={"complete": True},
    ) is True


def test_autonomous_trial_success_requires_current_run_files():
    from examples.run_openrouter_autonomous_trial import autonomous_trial_success

    assert autonomous_trial_success(
        tool_calls=1,
        allowed=1,
        files=["index.html", "style.css", "script.js"],
        created_files=set(),
        completion={"complete": True},
        outside_denied=True,
        evidence_ok=True,
    ) is False


def test_autonomous_trial_success_accepts_completed_current_run():
    from examples.run_openrouter_autonomous_trial import autonomous_trial_success

    assert autonomous_trial_success(
        tool_calls=3,
        allowed=3,
        files=["index.html", "style.css", "script.js"],
        created_files={"index.html", "style.css", "script.js"},
        completion={"complete": True},
        outside_denied=True,
        evidence_ok=True,
    ) is True


def test_autonomous_trial_task_ids_are_unique():
    from examples.run_openrouter_autonomous_trial import autonomous_trial_task_id

    first = autonomous_trial_task_id()
    second = autonomous_trial_task_id()

    assert first.startswith("openrouter-autonomous-website-")
    assert second.startswith("openrouter-autonomous-website-")
    assert first != second

def test_build_controlplane_uses_unique_task_id(tmp_path):
    from examples.run_openrouter_autonomous_trial import build_controlplane

    cp1, _ = build_controlplane(tmp_path / "run1")
    cp2, _ = build_controlplane(tmp_path / "run2")

    task_ids_1 = list(cp1.tasks)
    task_ids_2 = list(cp2.tasks)

    assert len(task_ids_1) == 1
    assert len(task_ids_2) == 1

    assert task_ids_1[0].startswith("openrouter-autonomous-website-")
    assert task_ids_2[0].startswith("openrouter-autonomous-website-")
    assert task_ids_1[0] != task_ids_2[0]

def test_autonomous_trial_provider_error_is_not_completion():
    from examples.run_openrouter_autonomous_trial import should_accept_agent_completion

    assert should_accept_agent_completion(
        finish_reason="error",
        tool_calls=[],
        validation={"complete": True},
    ) is False


def test_autonomous_trial_completion_requires_current_run_files():
    from examples.run_openrouter_autonomous_trial import autonomous_trial_success

    assert autonomous_trial_success(
        tool_calls=1,
        allowed=1,
        files=["index.html", "style.css", "script.js"],
        created_files={"index.html"},
        completion={"complete": True},
        outside_denied=True,
        evidence_ok=True,
    ) is False

