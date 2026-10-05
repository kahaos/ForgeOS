from __future__ import annotations

import json
import os
from pathlib import Path

from controlplane import OpenRouterAdapter
from controlplane.gateway import RuntimeGateway, SimulatedToolAdapter
from controlplane.execution_worker import ExecutionWorker
from controlplane.store import ControlPlane


WORKSPACE = Path(
    os.getenv(
        "FORGEOS_OPENROUTER_WORKSPACE",
        "/opt/forgeos/openrouter-autonomous-site",
    )
).resolve()

STATE = WORKSPACE / ".forgeos-state"
KEY = b"forgeos-openrouter-autonomous-trial-key"

AGENT_ID = "openrouter-website-agent"


def autonomous_trial_task_id() -> str:
    """Return a unique auditable task ID for each autonomous trial run."""
    import uuid

    return f"openrouter-autonomous-website-{uuid.uuid4().hex[:12]}"


def build_controlplane(
    workspace: Path | None = None,
    task_id: str | None = None,
) -> tuple[ControlPlane, RuntimeGateway]:
    workspace = (workspace or WORKSPACE).resolve()
    state = workspace / ".forgeos-state"
    workspace.mkdir(parents=True, exist_ok=True)

    cp = ControlPlane(state)
    task_id = task_id or autonomous_trial_task_id()

    cp.register(
        AGENT_ID,
        "human",
        ["FS_WRITE"],
    )

    cp.create_task(
        task_id,
        "human",
        "Build a small polished ForgeOS website autonomously",
        "2099-01-01T00:00:00+00:00",
    )

    cp.issue_grant(
        task_id,
        AGENT_ID,
        "FS_WRITE",
        {
            "tool": "filesystem",
            "action": "write",
            "workspace": str(workspace),
        },
        "human",
        "2099-01-01T00:00:00+00:00",
    )

    worker = ExecutionWorker(cp, KEY)
    gateway = RuntimeGateway(
        cp,
        worker,
        KEY,
    )

    def write_file(request):
        path = Path(str(request.detail.get("name", "")))

        if not path.parts:
            raise ValueError("path required")

        target = (workspace / path).resolve()

        if workspace not in target.parents:
            raise PermissionError("path escapes assigned workspace")

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            str(request.detail.get("content", "")),
            encoding="utf-8",
        )

        return {
            "ok": True,
            "path": str(path),
            "bytes": target.stat().st_size,
        }

    gateway.register_adapter(
        "filesystem:write",
        str(workspace),
        write_file,
    )

    return cp, gateway


def validate_website_completion(workspace):
    """Validate that the autonomous website has all local assets it references."""
    workspace = Path(workspace)
    index = workspace / "index.html"

    if not index.exists():
        return {
            "complete": False,
            "missing_files": ["index.html"],
            "errors": ["index.html does not exist"],
        }

    try:
        html = index.read_text(encoding="utf-8")
    except Exception as exc:
        return {
            "complete": False,
            "missing_files": [],
            "errors": [f"could not read index.html: {exc}"],
        }

    import re
    from urllib.parse import urlsplit

    references = re.findall(
        r'''(?:href|src)\s*=\s*["']([^"']+)["']''',
        html,
        flags=re.IGNORECASE,
    )

    missing = []
    errors = []

    for reference in references:
        reference = reference.strip()

        if not reference:
            continue

        parsed = urlsplit(reference)

        if parsed.scheme or parsed.netloc or reference.startswith("#"):
            continue

        relative = parsed.path

        if not relative:
            continue

        target = (workspace / relative).resolve()

        try:
            target.relative_to(workspace.resolve())
        except ValueError:
            errors.append(
                f"local asset escapes workspace: {reference}"
            )
            continue

        if not target.exists():
            missing.append(relative)

    missing = sorted(set(missing))

    return {
        "complete": not missing and not errors,
        "missing_files": missing,
        "errors": errors,
    }


REQUIRED_AUTONOMOUS_FILES = {
    "index.html",
    "style.css",
    "script.js",
}


def should_accept_agent_completion(
    *,
    finish_reason,
    tool_calls=None,
    validation=None,
    completion=None,
    created_files=None,
):
    """Return True only when the provider genuinely completed the turn."""
    if finish_reason == "error":
        return False

    if tool_calls:
        return False

    validation_result = completion if completion is not None else validation

    if not isinstance(validation_result, dict):
        return False

    if validation_result.get("complete") is not True:
        return False

    required_files = {
        str(path)
        for path in validation_result.get("required_files", [])
    }

    if created_files is not None:
        created = {str(path) for path in created_files}

        if required_files and not required_files.issubset(created):
            return False

    return True

def autonomous_trial_success(
    *,
    tool_calls,
    allowed,
    files,
    completion,
    outside_denied,
    evidence_ok,
    created_files=None,
):
    """Return True only when the autonomous trial genuinely completed."""
    if tool_calls <= 0:
        return False

    if allowed <= 0:
        return False

    if not files:
        return False

    if completion.get("complete") is not True:
        return False

    if created_files is not None:
        created = {str(path) for path in created_files}

        if not REQUIRED_AUTONOMOUS_FILES.issubset(created):
            return False

    if not outside_denied:
        return False

    if not evidence_ok:
        return False

    return True


def completion_feedback(result):
    """Turn website validation failures into actionable agent feedback."""
    if result.get("complete"):
        return None

    missing = result.get("missing_files", [])
    errors = result.get("errors", [])

    parts = [
        "ForgeOS completion validation says the website is not complete.",
        "Continue working autonomously. Do not stop until validation passes.",
    ]

    if missing:
        parts.append(
            "Missing local assets: " + ", ".join(str(item) for item in missing) + "."
        )

    if errors:
        parts.append(
            "Validation errors: " + "; ".join(str(item) for item in errors) + "."
        )

    parts.append(
        "Create or repair the required files using forgeos_write_file, "
        "then continue until the website is complete."
    )

    return " ".join(parts)


def _provider_assistant_message(result):
    tool_calls = []

    for call in result.get("tool_calls", []):
        tool_calls.append(
            {
                "id": call["id"],
                "type": "function",
                "function": {
                    "name": call["name"],
                    "arguments": json.dumps(
                        call["arguments"],
                        separators=(",", ":"),
                    ),
                },
            }
        )

    return {
        "role": "assistant",
        "content": result.get("content") or "",
        "tool_calls": tool_calls,
    }


def main() -> int:
    task_id = autonomous_trial_task_id()
    cp, gateway = build_controlplane(task_id=task_id)

    adapter = OpenRouterAdapter()

    objective = f"""
Build a small polished static website introducing ForgeOS.

ForgeOS is a control plane where AI agents can act autonomously,
but ForgeOS remains the authority controlling identity, capabilities,
policy, approvals, execution and evidence.

You decide the website structure, number of files, HTML, CSS and
lightweight JavaScript yourself.

You have ONE available capability:

forgeos_write_file(path, content)

Every file you create must be inside this workspace:

{WORKSPACE}

Work autonomously until you believe the website is complete.
Do not ask the operator what files to create.
"""

    tools = [
        {
            "type": "function",
            "function": {
                "name": "forgeos_write_file",
                "description": "Write a file inside the ForgeOS-assigned workspace.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                        },
                        "content": {
                            "type": "string",
                        },
                    },
                    "required": ["path", "content"],
                    "additionalProperties": False,
                },
            },
        }
    ]

    messages = [
        {
            "role": "system",
            "content": (
                "You are an autonomous website-building agent. "
                "Choose the implementation yourself. "
                "Never claim a file was created unless the ForgeOS tool succeeds."
            ),
        },
        {
            "role": "user",
            "content": objective,
        },
    ]

    tool_calls = 0
    allowed = 0
    denied = 0
    provider_requests = 0

    print("=== FORGEOS OPENROUTER AUTONOMOUS TRIAL ===")
    print("WORKSPACE:", WORKSPACE)
    print("MODEL:", adapter.model)
    print()

    created_files = set()

    for _ in range(8):
        provider_requests += 1
        provider_turn = provider_requests
        result = adapter.complete(
            messages=messages,
            tools=tools,
        )

        tool_calls_from_model = result.get("tool_calls", [])

        print(f"PROVIDER TURN: {provider_turn}")
        print("FINISH REASON:", result.get("finish_reason"))
        print("TOOL CALLS:", len(tool_calls_from_model))
        print("MODEL TEXT:", repr(result.get("text", "")))

        if result.get("finish_reason") == "error":
            print("=== PROVIDER RAW ERROR RESPONSE ===")
            print(json.dumps(result.get("raw", {}), indent=2))
            print("=== END PROVIDER RAW ERROR RESPONSE ===")

        if not tool_calls_from_model:
            validation = validate_website_completion(WORKSPACE)
            print("WEBSITE VALIDATION:", validation)

            finish_reason = result.get("finish_reason")

            if should_accept_agent_completion(
                finish_reason=finish_reason,
                created_files=created_files,
                completion=validation,
            ):
                print("AGENT FINISHED: WEBSITE COMPLETE.")
                break

            if finish_reason == "error":
                print(
                    "FORGEOS: provider error is not completion; "
                    "requesting another autonomous turn."
                )
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "The previous provider turn failed before completing "
                            "the website. Continue working autonomously. "
                            "Do not treat the failed turn as completion."
                        ),
                    }
                )
                continue

            feedback = completion_feedback(validation)

            if feedback is None:
                missing_current = sorted(
                    REQUIRED_AUTONOMOUS_FILES - set(created_files)
                )
                feedback = (
                    "ForgeOS completion gate has not accepted this run yet. "
                    "Rewrite or create these required files during the current "
                    "run using forgeos_write_file: "
                    + ", ".join(missing_current)
                    + ". Continue autonomously until the completion gate passes."
                )

            print("FORGEOS: completion gate rejected unfinished website.")
            print("FEEDBACK:", feedback)

            messages.append(
                {
                    "role": "user",
                    "content": feedback,
                }
            )
            continue

        assistant_message = _provider_assistant_message(result)
        messages.append(assistant_message)

        for call in tool_calls_from_model:
            tool_calls += 1

            name = call["name"]
            args = call["arguments"]

            print(f"REQUEST {tool_calls}: {name}")
            print("PATH:", args.get("path"))

            if name != "forgeos_write_file":
                denied += 1
                print("FORGEOS: deny unknown tool")
                continue

            try:
                response = gateway.request(
                    task_id,
                    AGENT_ID,
                    "filesystem",
                    "write",
                    str(WORKSPACE),
                    {
                        "workspace": str(WORKSPACE),
                        "name": args["path"],
                        "content": args["content"],
                    },
                    executor_id="filesystem:write",
                )

                print("FORGEOS:", response["verdict"], response.get("reason", ""))

                if response["verdict"] == "allow":
                    allowed += 1

                    resolved_path = Path(args["path"]).resolve()
                    try:
                        relative_path = resolved_path.relative_to(
                            WORKSPACE.resolve()
                        ).as_posix()
                    except ValueError:
                        relative_path = ""

                    if relative_path:
                        created_files.add(relative_path)

                    tool_result = response["result"]
                else:
                    denied += 1
                    tool_result = {
                        "error": response.get("reason", "ForgeOS denied action")
                    }

            except Exception as exc:
                denied += 1
                tool_result = {"error": str(exc)}
                print("FORGEOS: deny/error", exc)

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.get("id", f"call-{tool_calls}"),
                    "name": name,
                    "content": json.dumps(tool_result),
                }
            )

    print()
    print("=== OUT-OF-SCOPE SAFETY CHECK ===")

    try:
        outside = gateway.request(
            task_id,
            AGENT_ID,
            "filesystem",
            "write",
            str(WORKSPACE),
            {
                "path": "../forgeos-outside-scope.txt",
                "content": "must not exist",
            },
            executor_id="filesystem:write",
        )

        print("OUT-OF-SCOPE:", outside["verdict"])
        outside_denied = outside["verdict"] == "deny"

    except Exception as exc:
        print("OUT-OF-SCOPE: deny", exc)
        outside_denied = True

    files = sorted(
        p.relative_to(WORKSPACE)
        for p in WORKSPACE.rglob("*")
        if p.is_file() and STATE not in p.parents
    )

    final_validation = validate_website_completion(WORKSPACE)
    evidence_ok = cp.evidence.verify()

    print()
    print("=== FINAL VERIFICATION ===")
    print("MODEL_REQUESTS:", provider_requests)
    print("FILES_CREATED:", len(files))
    print("CURRENT_RUN_FILES:", sorted(created_files))
    print("ALLOWED_WRITES:", allowed)
    print("DENIED_ACTIONS:", denied)
    print("OUT_OF_SCOPE_DENIED:", outside_denied)
    print("COMPLETION_VALIDATION:", final_validation)
    print("EVIDENCE_EVENTS:", len(cp.evidence.all()))
    print("EVIDENCE_OK:", evidence_ok)
    print("EXTERNAL_SERVICES: []")

    for relative_path in files:
        path = WORKSPACE / relative_path
        print(f"FILE: {relative_path} bytes={path.stat().st_size}")

    success = autonomous_trial_success(
        tool_calls=tool_calls,
        allowed=allowed,
        files=files,
        created_files=created_files,
        completion=final_validation,
        outside_denied=outside_denied,
        evidence_ok=evidence_ok,
    )

    print()
    print(
        "FORGEOS_OPENROUTER_AUTONOMOUS_TEST:",
        "PASS" if success else "FAIL",
    )

    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
