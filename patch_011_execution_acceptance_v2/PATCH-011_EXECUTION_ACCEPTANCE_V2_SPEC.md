# ForgeOS PATCH-011 — Controlled Execution Acceptance v2

This version is aligned with the actual PatchPlanStore contract:
_read_plan(), _write_plan(), _audit(action, actor="system", extra=None).

It does not modify patch_plan.py.

Execution is restricted to the registered local-test handler and target local-test.
Production is rejected. Replay is rejected. Evidence, receipt and audit events are persisted.
GovernanceStore remains authoritative for ForgeOS lifecycle state.
