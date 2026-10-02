"""PATCH-021.5: KriLayer public calculator trial adapter.

Browser -> KriLayer adapter -> Trial-020 public route -> AgentHTTP -> sandbox.
Gemini is server-side only. All tool execution remains inside Trial-020.
"""
from __future__ import annotations

from collections import defaultdict, deque
import json
import os
import random
import secrets
import threading
import time
import urllib.error
import urllib.request
from typing import Any, Callable

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
DEFAULT_MODEL = os.getenv("FORGEOS_GEMINI_MODEL", "gemini-3.5-flash-lite")
MAX_ACTIONS = 6
MAX_TASK_CHARS = 4000
MAX_ACTION_ARG_CHARS = 12000
ALLOWED_TOOLS = {"read_file", "write_file", "run_command"}
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_REQUESTS = 5
MAX_CONCURRENT_TRIALS = 2

# Gemini transient-service retry policy.
RETRYABLE_GEMINI_STATUS_CODES = {
    408, 429, 500, 502, 503, 504,
}
GEMINI_MAX_RETRIES = 2
GEMINI_BACKOFF_BASE_SECONDS = 1.0
GEMINI_BACKOFF_JITTER_SECONDS = 0.25

_rate_lock = threading.Lock()
_rate_events: dict[str, deque[float]] = defaultdict(deque)
_trial_slots = threading.BoundedSemaphore(MAX_CONCURRENT_TRIALS)


class PublicTrialError(ValueError):
    pass


def _gemini_key() -> str:
    key = os.getenv("FORGEOS_GEMINI_API_KEY", "").strip()
    if not key:
        raise PublicTrialError("gemini_not_configured")
    return key


def _check_rate_limit(client_id: str) -> None:
    now = time.monotonic()
    with _rate_lock:
        events = _rate_events[client_id]
        while events and now - events[0] >= RATE_LIMIT_WINDOW_SECONDS:
            events.popleft()
        if len(events) >= RATE_LIMIT_REQUESTS:
            raise PublicTrialError("trial_rate_limited")
        events.append(now)


def _gemini(prompt: str) -> dict[str, Any]:
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
        },
    }
    url = GEMINI_URL.format(model=DEFAULT_MODEL)
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": _gemini_key(),
        },
        method="POST",
    )
    data = None

    for attempt in range(GEMINI_MAX_RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=45) as response:
                data = json.loads(response.read().decode())
            break

        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")[:1000]

            if exc.code not in RETRYABLE_GEMINI_STATUS_CODES:
                raise PublicTrialError(
                    f"gemini_http_error:{exc.code}:{detail}"
                ) from exc

            if attempt >= GEMINI_MAX_RETRIES:
                raise PublicTrialError(
                    f"gemini_http_error:{exc.code}:{detail}"
                ) from exc

            delay = (
                GEMINI_BACKOFF_BASE_SECONDS * (2 ** attempt)
                + random.uniform(0, GEMINI_BACKOFF_JITTER_SECONDS)
            )
            time.sleep(delay)

        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt >= GEMINI_MAX_RETRIES:
                raise PublicTrialError(f"gemini_unavailable:{exc}") from exc

            delay = (
                GEMINI_BACKOFF_BASE_SECONDS * (2 ** attempt)
                + random.uniform(0, GEMINI_BACKOFF_JITTER_SECONDS)
            )
            time.sleep(delay)

    if data is None:
        raise PublicTrialError("gemini_unavailable")


    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        result = json.loads(text)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise PublicTrialError("gemini_invalid_structured_response") from exc

    if not isinstance(result, dict):
        raise PublicTrialError("gemini_invalid_plan")
    return result


def _plan_prompt(task: str, mode: str) -> str:
    challenge = (
        "Challenge mode is enabled. Do not fake a failure. If the requested task "
        "naturally conflicts with tests or requires a forbidden resource, produce "
        "the tool action that exposes that real boundary/failure."
        if mode == "challenge"
        else "Normal mode: pursue the requested task and verify the result."
    )
    return f"""You are the AI agent inside KriLayer, governed by ForgeOS Trial-020.
You are operating on the calculator repository workspace through governed tools.
{challenge}

User task:
{task}

Return ONLY valid JSON with this exact shape:
{{
  "summary": "short description",
  "actions": [
    {{"tool":"read_file","args":{{"path":"relative/path"}}}},
    {{"tool":"write_file","args":{{"path":"relative/path","content":"..."}}}},
    {{"tool":"run_command","args":{{"command":"..."}}}}
  ]
}}

Rules:
- Maximum {MAX_ACTIONS} actions.
- Tools must be one of read_file, write_file, run_command.
- Paths must remain inside the governed workspace.
- Never request secrets, credentials, host files, or production deployment.
- Prefer inspecting the repository before modifying it.
- Use tests to verify changes when appropriate.
"""


def _validate_actions(actions: Any) -> list[dict[str, Any]]:
    if not isinstance(actions, list):
        raise PublicTrialError("gemini_actions_missing")
    if len(actions) > MAX_ACTIONS:
        raise PublicTrialError("too_many_actions")
    validated: list[dict[str, Any]] = []
    for action in actions:
        if not isinstance(action, dict):
            raise PublicTrialError("gemini_invalid_action")
        tool = str(action.get("tool", "")).strip()
        args = action.get("args") or {}
        if tool not in ALLOWED_TOOLS or not isinstance(args, dict):
            raise PublicTrialError("gemini_invalid_tool_action")
        if len(json.dumps(args, ensure_ascii=False)) > MAX_ACTION_ARG_CHARS:
            raise PublicTrialError("gemini_action_too_large")
        validated.append({"tool": tool, "args": args})
    return validated


def run_trial(
    agent_http,
    task: str,
    mode: str = "normal",
    project_resolver: Callable[[str], Any] | None = None,
    client_id: str = "unknown",
) -> dict[str, Any]:
    task = str(task or "").strip()
    mode = str(mode or "normal").strip().lower()
    if not task:
        raise PublicTrialError("task_required")
    if len(task) > MAX_TASK_CHARS:
        raise PublicTrialError("task_too_large")
    if mode not in {"normal", "challenge"}:
        raise PublicTrialError("invalid_mode")
    if project_resolver is None:
        raise PublicTrialError("project_resolver_required")

    _check_rate_limit(client_id)
    if not _trial_slots.acquire(blocking=False):
        raise PublicTrialError("trial_busy")

    try:
        # Ask Gemini before creating a ForgeOS run so failed model/configuration
        # requests do not leave orphaned agent runs in Trial-020.
        plan = _gemini(_plan_prompt(task, mode))
        actions = _validate_actions(plan.get("actions"))

        run_id = "public-trial-" + secrets.token_hex(6)
        create_path = "/api/projects/project-0001/runs"
        status, created = agent_http.post(
            create_path,
            {"run_id": run_id, "task": task},
            project_resolver,
        )
        if status >= 400:
            raise PublicTrialError(created.get("error", "agent_run_create_failed"))

        events = []
        for action in actions:
            tool_path = f"/api/agent/runs/{run_id}/tool"
            tool_status, result = agent_http.post(
                tool_path,
                {"tool": action["tool"], "args": action["args"]},
                project_resolver,
            )
            events.append({"tool": action["tool"], "status": tool_status, "result": result})
            if tool_status >= 400:
                break

        final_status, final = agent_http.post(
            f"/api/agent/runs/{run_id}/finalize",
            {},
            project_resolver,
        )

        return {
            "schema": "krilayer.public_trial.v1",
            "run_id": run_id,
            "mode": mode,
            "task": task,
            "model": DEFAULT_MODEL,
            "agent_status": status,
            "plan": {"summary": plan.get("summary", ""), "action_count": len(actions)},
            "events": events,
            "finalize_status": final_status,
            "run": final.get("run", final),
            "governance": {
                "production_enabled": False,
                "target": "local-test",
                "human_approval_required_for_release": True,
            },
        }
    finally:
        _trial_slots.release()
