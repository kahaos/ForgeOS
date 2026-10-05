"""Protected execution boundary for Apoa-authorized tool calls."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .engine import ApoaEngine
from .models import Authorization, ExecutionRequest


class ProtectedExecutor:
    """Dispatch a tool only after Apoa validates the exact request authorization."""

    def __init__(self, engine: ApoaEngine, tool: Callable[[ExecutionRequest], Any]) -> None:
        self.engine = engine
        self.tool = tool

    def execute(self, request: ExecutionRequest, authorization: Authorization | None) -> Any:
        if authorization is None:
            return None
        if not self.engine.consume(request, authorization):
            return None
        return self.tool(request)
