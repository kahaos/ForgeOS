# PATCH-009 — E2E UI Acceptance

Purpose:
Validate the running ForgeOS UI against the authoritative backend without mutating lifecycle state.

Checks:
- Root UI HTTP 200
- /api/status, /api/lifecycle, /api/audit HTTP 200
- HEALTHY / READY service state
- governance authoritative
- production disabled
- project/release/target binding
- DEPLOYMENT_PRECHECKED with next gate DEPLOYMENT_APPROVED
- audit feed present
- required UI navigation
- responsive mobile contract
- backend-authority wording

This acceptance test deliberately performs no lifecycle advance and no deployment.
