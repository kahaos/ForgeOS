"""Bounded local-test PATCH-011 handler."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from datetime import datetime, timezone

HANDLER_ID = "local-test.artifact.v1"
TARGET = "local-test"
ARTIFACT_RELATIVE_PATH = "data/local_test_execution_artifact.txt"
ARTIFACT_CONTENT = "ForgeOS PATCH-011 local-test execution\n"


class LocalTestExecutionError(RuntimeError):
    pass


def execute(root: str | Path) -> dict:
    root = Path(root).resolve()
    artifact = root / ARTIFACT_RELATIVE_PATH
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(ARTIFACT_CONTENT, encoding="utf-8")
    digest = sha256(artifact.read_bytes()).hexdigest()
    return {
        "handler_id": HANDLER_ID,
        "target": TARGET,
        "artifact": str(artifact.relative_to(root)),
        "sha256": digest,
        "executed_at": datetime.now(timezone.utc).isoformat(),
    }


def verify(root: str | Path, result: dict) -> dict:
    root = Path(root).resolve()
    artifact = root / result["artifact"]
    if not artifact.is_file():
        raise LocalTestExecutionError("local-test artifact missing")
    digest = sha256(artifact.read_bytes()).hexdigest()
    if digest != result["sha256"]:
        raise LocalTestExecutionError("local-test artifact digest mismatch")
    return {
        "ok": True,
        "handler_id": result["handler_id"],
        "artifact": result["artifact"],
        "sha256": digest,
    }


HANDLERS = {
    HANDLER_ID: {
        "target": TARGET,
        "execute": execute,
        "verify": verify,
    }
}
