# ForgeOS Scoped Authority v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Extend ForgeOS into a task-scoped runtime authority layer for autonomous and multi-agent execution while preserving the existing governed execution and isolation guarantees.

**Architecture:** Add a structured authority domain beside the legacy flat capability path. The Control Plane remains the single policy authority; a runtime gateway binds allowed or approved requests to short-lived signed authority snapshots and registered executors. Delegation attenuates authority and provider adapters remain thin boundaries over provider-native credentials.

**Tech Stack:** Python 3.11+, standard library, pytest, JSON persistence, HMAC-SHA256, existing Docker isolated worker.

**Spec:** `docs/superpowers/specs/2026-10-03-forgeos-scoped-authority-v1-design.md`

## Global Constraints
- Preserve legacy flat capability requests and existing regression behavior.
- Scoped authority is task-bound, time-bounded, explicit, and fail-closed.
- There is exactly one authorization policy authority: `ControlPlane`/policy.
- Human approval is reserved for policy-defined consequential operations.
- Delegation may only attenuate authority.
- Signed authorization binds task, grant, scope, agent, policy, request, executor, target, expiry, and nonce.
- Existing Docker isolation defaults remain unchanged.
- No production deployment, arbitrary network access, secret-management replacement, or policy self-modification in v1.

## Tasks

### Task 1 — Domain models and scope engine
**Files:** `controlplane/authority.py`, `tests/test_scoped_authority.py`
- [ ] Write failing tests for Task, Scope, CapabilityGrant, expiry, revocation, deterministic scope matching, safe branch wildcards, and fail-closed unknown dimensions.
- [ ] Implement immutable-friendly dataclasses and persistence-ready dictionaries.
- [ ] Implement exact scope matching and safe `feature/*` branch semantics.
- [ ] Run the focused tests; expected RED before implementation and GREEN after.

### Task 2 — Control Plane persistence and scoped policy
**Files:** `controlplane/store.py`, `controlplane/policy.py`, `tests/test_scoped_authority.py`
- [ ] Add task/grant persistence without altering legacy files.
- [ ] Add task creation/revocation, grant issuance/revocation, effective-grant lookup, and scoped request evaluation.
- [ ] Ensure clients cannot self-grant and delegation requires a parent grant.
- [ ] Implement risk-aware allow/ask/deny for scoped requests.
- [ ] Verify wrong repo, branch, workspace, task, expiry and revoked authority all deny.

### Task 3 — Delegation and multi-agent relationships
**Files:** `controlplane/authority.py`, `controlplane/store.py`, tests
- [ ] Add parent/child agent relationship metadata.
- [ ] Add delegated grants with parent_grant_id.
- [ ] Enforce capability/resource/environment/expiry attenuation.
- [ ] Test escalation, parent substitution, self-grant and widening denial.

### Task 4 — Signed scoped runtime authorization
**Files:** `controlplane/execution_worker.py`, `controlplane/authority.py`, tests
- [ ] Extend signed authorization to include task/grant/scope snapshots.
- [ ] Reject task, grant, scope, agent, policy, target, executor and request drift.
- [ ] Preserve persisted nonce replay protection and concurrency safety.
- [ ] Add task-scoped end-to-end governed execution regression.

### Task 5 — Runtime gateway and adapter boundaries
**Files:** `controlplane/gateway.py`, tests
- [ ] Add provider-neutral gateway with no duplicate policy engine.
- [ ] Register simulated, Docker, GitHub-boundary, generic HTTP/tool, and MCP-boundary adapters.
- [ ] Ensure provider secrets stay outside agent processes.
- [ ] Test automatic scoped execution and approval-required execution.

### Task 6 — API and authority graph
**Files:** `controlplane/api.py`, `tests/test_scoped_authority_api.py`
- [ ] Add task/grant/agent relationship endpoints following existing API conventions.
- [ ] Expose effective authority and graph-shaped relationship data.
- [ ] Expose revocation/inspection/evaluation without self-grant bypass.
- [ ] Test deterministic 2xx/4xx behavior.

### Task 7 — Documentation and multi-agent demo
**Files:** `README.md`, `controlplane/README.md`, `docs/FORGEOS_ARCHITECTURE.md`, `examples/scoped_multi_agent_demo.py`
- [ ] Document provider-native security integration and runtime authority.
- [ ] Document task-scoped grants and delegation attenuation.
- [ ] Add a multi-agent website example with coder, SEO and deployment agents.
- [ ] Demonstrate autonomous low/medium-risk work, approval for consequential work, and denied scope escape.

### Task 8 — Full verification
- [ ] Run focused scoped-authority tests.
- [ ] Run the complete `pytest -q` suite.
- [ ] Run Docker integration tests.
- [ ] Inspect GitHub Actions for the exact implementation head.
- [ ] Verify no secrets or generated credentials were introduced.
- [ ] Record exact verification evidence before claiming completion.

## Delivery

The implementation is delivered as one coherent `scoped-authority-v1` branch/release feature. Individual commits may separate TDD stages, but no task is considered complete without its focused test evidence. The branch is not merged into `hardening-v1` until the full verification gate is green.