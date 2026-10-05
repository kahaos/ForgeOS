"""Provider adapter for OpenRouter's OpenAI-compatible chat API.

This module is deliberately *not* an authority boundary. It only translates
ForgeOS runtime messages/tool declarations to and from OpenRouter. Tool calls
must be handed back to ForgeOS (for example RuntimeGateway) before any action
is executed.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Mapping, Sequence


class OpenRouterAdapter:
    """Thin OpenRouter model adapter with no direct tool execution authority."""

    DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
    DEFAULT_MODEL = "openai/gpt-oss-20b"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        timeout: float = 60.0,
        app_name: str | None = None,
        app_url: str | None = None,
    ) -> None:
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is required")
        self.model = model or os.getenv("OPENROUTER_MODEL", self.DEFAULT_MODEL)
        self.base_url = (base_url or os.getenv("OPENROUTER_BASE_URL", self.DEFAULT_BASE_URL)).rstrip("/")
        self.timeout = timeout
        self.app_name = app_name or os.getenv("OPENROUTER_APP_NAME", "ForgeOS")
        self.app_url = app_url or os.getenv("OPENROUTER_APP_URL")

    def complete(
        self,
        messages: Sequence[Mapping[str, Any]],
        tools: Sequence[Mapping[str, Any]] | None = None,
        *,
        model: str | None = None,
        temperature: float | None = None,
    ) -> dict[str, Any]:
        """Generate one model turn and normalize tool calls for ForgeOS.

        The adapter never executes a returned tool call. Callers are expected
        to submit each normalized call to the ForgeOS authority boundary.
        """
        payload: dict[str, Any] = {
            "model": model or self.model,
            "messages": [dict(message) for message in messages],
        }
        if tools:
            payload["tools"] = [dict(tool) for tool in tools]
        if temperature is not None:
            payload["temperature"] = temperature

        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if self.app_name:
            headers["X-Title"] = self.app_name
        if self.app_url:
            headers["HTTP-Referer"] = self.app_url

        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=body,
            headers=headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenRouter request failed ({exc.code}): {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"OpenRouter connection failed: {exc.reason}") from exc

        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError("OpenRouter returned invalid JSON") from exc

        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            raise RuntimeError("OpenRouter response contained no choices")
        message = choices[0].get("message")
        if not isinstance(message, dict):
            raise RuntimeError("OpenRouter response contained no assistant message")

        normalized_calls = []
        for call in message.get("tool_calls") or []:
            if not isinstance(call, dict):
                continue
            function = call.get("function") or {}
            arguments = function.get("arguments", {})
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments) if arguments else {}
                except json.JSONDecodeError as exc:
                    raise RuntimeError("OpenRouter returned invalid tool-call arguments") from exc
            if not isinstance(arguments, dict):
                raise RuntimeError("OpenRouter tool-call arguments must be an object")
            normalized_calls.append(
                {
                    "id": call.get("id"),
                    "name": function.get("name"),
                    "arguments": arguments,
                }
            )

        return {
            "provider": "openrouter",
            "model": data.get("model", payload["model"]),
            "response_id": data.get("id"),
            "text": message.get("content") or "",
            "tool_calls": normalized_calls,
            "finish_reason": choices[0].get("finish_reason"),
            "raw": data,
        }
