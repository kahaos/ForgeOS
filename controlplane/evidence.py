"""Append-only evidence. Each event carries a digest of the previous event."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canon(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


class EvidenceLog:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("")

    def append(self, kind: str, payload: dict[str, Any]) -> dict[str, Any]:
        prev = self._last_digest()
        event = {"ts": _now(), "kind": kind, "payload": payload, "prev": prev}
        event["digest"] = hashlib.sha256(_canon({k: event[k] for k in ("ts", "kind", "payload", "prev")})).hexdigest()
        with self.path.open("a") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")
        return event

    def all(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        return [json.loads(line) for line in self.path.read_text().splitlines() if line.strip()]

    def verify(self) -> bool:
        prev = "GENESIS"
        for event in self.all():
            if event.get("prev") != prev:
                return False
            body = {k: event[k] for k in ("ts", "kind", "payload", "prev")}
            if hashlib.sha256(_canon(body)).hexdigest() != event.get("digest"):
                return False
            prev = event["digest"]
        return True

    def _last_digest(self) -> str:
        events = self.all()
        return events[-1]["digest"] if events else "GENESIS"
