# ForgeOS PATCH-011 — Controlled Execution Acceptance Patch

Purpose: integrate the registered `local-test` handler with the Patch Plan Engine without granting arbitrary shell execution.

Required governed execution path:
READY -> EXECUTING -> VERIFYING -> COMPLETED

Failure path:
EXECUTING/VERIFYING -> FAILED -> ROLLBACK_REQUIRED

Security requirements:
- Only explicitly registered handlers may execute.
- Only `local-test` is accepted.
- Project binding must match the authoritative ForgeOS project.
- Patch must be READY.
- A completed patch cannot be replayed.
- No arbitrary shell/subprocess execution.
- No production execution.
- GovernanceStore remains authoritative for lifecycle state.
- Every execution produces evidence and a receipt.
- Execution actions are audited with digests.

The acceptance patch is deliberately narrow and intended only for local-test validation.
