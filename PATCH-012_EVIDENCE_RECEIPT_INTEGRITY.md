# PATCH-012 — Evidence & Receipt Integrity

## Objective
Correct the evidence-path binding defect discovered during PATCH-011 live acceptance and establish a fresh, non-mutating acceptance record.

## Safety
- Historical PLAN-000004 / PATCH-A is not modified.
- Fresh acceptance uses PLAN-000005 / PATCH-B.
- Execution target is `local-test`.
- Production remains disabled.
- Replay of a completed patch must return HTTP 409.
- Freeze operation performs no lifecycle transition.

## Acceptance criteria
1. Evidence path equals the handler artifact path.
2. Receipt evidence path equals the artifact path.
3. Execution, verification and evidence SHA-256 values agree.
4. Receipt status is COMPLETED.
5. Replay is rejected.
6. A new Alpha 0.8 freeze record and changelog are generated.
