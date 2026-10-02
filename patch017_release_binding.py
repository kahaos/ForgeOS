"""PATCH-017: release/approval identity binding hardening.

This module is imported before ForgeOS constructs its GovernedExecutionStore.
It monkey-patches only the release-creation boundary and GovernanceStore with
small, reversible helpers. The goal is to make the authoritative lifecycle's
current_release follow the newly-created governed release, so approval checks
cannot accidentally validate a stale release ID.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from governed_execution import GovernedExecutionStore
from governance import GovernanceStore


def _bind_release(self: GovernanceStore, release_id: str) -> dict[str, Any]:
    if not isinstance(release_id, str) or not release_id.strip():
        raise ValueError("release_id_required")
    state = dict(self.state())
    current = state.get("current_release")
    if current == release_id:
        return state
    state["current_release"] = release_id
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    self._write(state)
    return state


if not getattr(GovernanceStore, "_patch017_release_binding", False):
    GovernanceStore.bind_release = _bind_release
    GovernanceStore._patch017_release_binding = True


_original_create_release = getattr(GovernedExecutionStore, "create_release")

if not getattr(_original_create_release, "_patch017_release_binding", False):
    def _patched_create_release(self, project_id, release_id, verdict_id, target, actor="ai", *args, **kwargs):
        result = _original_create_release(
            self, project_id, release_id, verdict_id, target, actor, *args, **kwargs
        )
        # The release call succeeded. Bind the exact release ID supplied to
        # create_release into the authoritative lifecycle state.
        self.governance.bind_release(release_id)
        return result

    _patched_create_release._patch017_release_binding = True
    _patched_create_release._patch017_original = _original_create_release
    GovernedExecutionStore.create_release = _patched_create_release
