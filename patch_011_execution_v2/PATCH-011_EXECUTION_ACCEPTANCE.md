# PATCH-011 Execution Acceptance

Acceptance conditions for the live integration:

1. Only registered handlers may execute.
2. The only registered handler is `local-test.artifact.v1`.
3. Target must be `local-test`.
4. Project must match the active GovernanceStore project.
5. Plan must be `READY`.
6. Successful execution records execution data.
7. Verification independently checks the artifact SHA-256.
8. Evidence is persisted.
9. A receipt is persisted and bound to the plan.
10. Repeat execution of a completed patch is rejected.
11. Handler exceptions move execution to failure state.
12. No arbitrary command/subprocess API exists.
13. GovernanceStore lifecycle remains unchanged.
14. Production remains disabled.
