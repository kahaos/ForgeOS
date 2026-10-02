# ForgeOS PATCH-011 — Execution Integration

Status: IMPLEMENTATION PACKAGE v2

Scope:
- Add a bounded execution state machine to PatchPlanStore.
- Execute only explicitly registered handlers.
- First handler: local-test.artifact.v1.
- Produce verification, evidence and a receipt.
- Do not execute arbitrary shell commands.
- Do not mutate the GovernanceStore lifecycle.
- Production remains disabled.

State path:
READY -> EXECUTING -> VERIFYING -> COMPLETED

Failure path:
EXECUTING/VERIFYING -> FAILED -> ROLLBACK_REQUIRED

The API integration is fail-closed and project/target bound.
