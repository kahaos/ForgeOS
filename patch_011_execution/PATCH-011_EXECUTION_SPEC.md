# ForgeOS PATCH-011 — Controlled Execution Extension

Status: IMPLEMENTATION PACKAGE

Purpose:
Extend the PATCH-011 Patch Plan Engine with a bounded local-test execution path.

Safety boundary:
- Only the `local-test` target is supported.
- No arbitrary shell command execution.
- No production deployment.
- Execution is through an explicitly registered handler.
- The handler writes only a ForgeOS-owned test artifact.
- Verification is SHA-256 based.
- Evidence and a receipt are recorded.
- Existing GovernanceStore lifecycle remains authoritative and is not mutated by this patch.

Execution lifecycle:
READY -> EXECUTING -> VERIFYING -> COMPLETED

Failure:
EXECUTING/VERIFYING -> FAILED -> ROLLBACK_REQUIRED

The installer is fail-closed: it refuses to modify files if expected PATCH-011 markers are not found.
