"""Small standard-library HTTP server for the ForgeOS approval API."""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .api import ApprovalAPI
from .store import ControlPlane


class ApprovalHTTPServer(ThreadingHTTPServer):
    """Threaded development server carrying one authoritative ApprovalAPI."""

    def __init__(self, server_address: tuple[str, int], api: ApprovalAPI) -> None:
        self.api = api
        super().__init__(server_address, _make_handler(api))


def _make_handler(api: ApprovalAPI) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: int, payload: dict[str, Any] | list[dict[str, Any]]) -> None:
            encoded = json.dumps(payload, sort_keys=True).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def _body(self) -> dict[str, Any] | None:
            length = self.headers.get("Content-Length")
            if length is None:
                return {}
            try:
                raw = self.rfile.read(int(length))
                value = json.loads(raw.decode("utf-8"))
            except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
                return None
            return value if isinstance(value, dict) else None

        def _handle(self, method: str) -> None:
            body = self._body() if method == "POST" else None
            if method == "POST" and body is None:
                self._send(400, {"error": "invalid request"})
                return
            status, payload = api.handle(method, self.path, body)
            self._send(status, payload)

        def do_GET(self) -> None:  # noqa: N802
            self._handle("GET")

        def do_POST(self) -> None:  # noqa: N802
            self._handle("POST")

        def do_PATCH(self) -> None:  # noqa: N802
            self._handle("PATCH")

        def log_message(self, format: str, *args: Any) -> None:
            return

    return Handler


def serve(root: str, host: str = "127.0.0.1", port: int = 8520, operator_id: str | None = None) -> None:
    """Run the local development approval API with a server-bound operator principal."""
    controlplane = ControlPlane(root)
    resolved_operator = operator_id or os.environ.get("FORGEOS_OPERATOR_ID")
    server = ApprovalHTTPServer((host, port), ApprovalAPI(controlplane, operator_id=resolved_operator))
    try:
        server.serve_forever()
    finally:
        server.server_close()


if __name__ == "__main__":
    serve("data/controlplane")