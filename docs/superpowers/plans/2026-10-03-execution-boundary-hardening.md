# Scoped Authority v1.1 Execution Boundary Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure every scoped execution, including autonomous ALLOW and human-approved ASK, reaches a real `ExecutionAuthorizer -> ExecutionWorker -> Executor` boundary, and prevent client-supplied issuer identity from being treated as authenticated authority.

**Architecture:** The ControlPlane remains the decision and evidence authority but no longer invokes caller-supplied scoped executors. RuntimeGateway owns the execution path: it creates/binds scoped approvals, asks for human approval when required, then issues a short-lived signed authorization and routes it through ExecutionWorker. API grant issuance uses a server-bound authenticated operator principal rather than trusting `issued_by` from request JSON.

**Tech Stack:** Python 3, pytest, existing ForgeOS JSON persistence, HMAC execution authorization, GitHub Actions, existing RuntimeGateway/ExecutionWorker.

**Spec:** Approved bounded design from the ForgeOS execution-boundary review: remove direct scoped executor execution; converge ALLOW and ASK->APPROVE on the signed worker; bind task/grant/scope snapshots; add regression tests; replace client-supplied issuer identity with authenticated operator identity.

## Global Constraints

- Preserve the existing legacy ControlPlane request/approval behavior unless the record is explicitly scoped.
- Scoped execution must never invoke a caller-supplied executor directly.
- Every scoped executor invocation must pass `ExecutionAuthorizer` signature, expiry, nonce, request, agent, task, grant, scope and executor binding checks.
- Human approval remains single-use and exact-request bound.
- No broad Docker socket access or production deployment changes are part of this patch.
- Provider-native credentials and controls remain outside ForgeOS policy code.

## Review Focus

- Caller-supplied scoped executor: must never be invoked directly; test with a recording executor.
- Scoped ASK approval: approval must not execute before the worker path is invoked; test pending state and adapter call count.
- Scoped approval after human approval: execution must require signed authorization and worker validation.
- Task/grant/scope drift: any mutation or tampering must prevent executor invocation.
- Issuer spoofing: request JSON cannot select the authority issuer; API must use its authenticated operator principal.

### Task 1: Lock down direct scoped execution

**Files:**
- Modify: `controlplane/store.py`
- Test: `tests/test_execution_path_hardening.py`

- [ ] Write failing tests proving `request_scoped(..., executor=...)` cannot invoke the supplied executor and scoped `decide(..., execute=True)` cannot directly invoke its bound executor.
- [ ] Run the focused tests and verify they fail for the current implementation.
- [ ] Change scoped approval/execution handling so direct executor invocation is rejected; preserve legacy unscoped behavior.
- [ ] Run the focused tests and verify they pass.
- [ ] Commit `security: block direct scoped executor bypass`.

### Task 2: Converge RuntimeGateway approval execution on ExecutionWorker

**Files:**
- Modify: `controlplane/gateway.py`
- Modify: `controlplane/store.py`
- Test: `tests/test_execution_path_hardening.py`

- [ ] Add a failing test for a scoped ASK request followed by RuntimeGateway approval that proves the adapter is invoked only after `ExecutionAuthorizer.issue()` and `ExecutionWorker.execute()`.
- [ ] Run the focused test and verify it fails.
- [ ] Add a RuntimeGateway approval/execution method that performs `decide(..., execute=False)`, issues signed authorization, and executes through the worker.
- [ ] Ensure scoped approvals contain task/grant snapshots and executor binding.
- [ ] Run focused gateway and worker tests.
- [ ] Commit `security: route scoped approvals through execution worker`.

### Task 3: Bind API grant issuance to authenticated operator identity

**Files:**
- Modify: `controlplane/api.py`
- Test: `tests/test_execution_path_hardening.py`

- [ ] Add a failing test showing `issued_by` supplied in request JSON cannot impersonate another issuer.
- [ ] Run the focused test and verify it fails.
- [ ] Add a server-supplied operator principal to `ApprovalAPI`; scoped grant issuance must use that principal and reject conflicting client-supplied issuer data.
- [ ] Keep agent delegation semantics unchanged: only the parent grant holder may delegate.
- [ ] Run API regression tests.
- [ ] Commit `security: bind scoped grant issuance to operator identity`.

### Task 4: Full verification and VPS handoff

**Files:**
- Modify: `docs/superpowers/plans/2026-10-03-execution-boundary-hardening.md`

- [ ] Run the complete Python suite.
- [ ] Run the opt-in Docker suite on the VPS using the existing privileged execution path.
- [ ] Run the scoped multi-agent demo.
- [ ] Add the final verification results to this plan.
- [ ] Create a PR from `scoped-authority-v1-1-execution-boundary` into `hardening-v1`.
