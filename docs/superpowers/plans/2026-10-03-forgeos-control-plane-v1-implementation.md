# ForgeOS Control Plane v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the approved ForgeOS Control Plane v1 design into a tested API, governed execution-worker boundary, live evidence artifact, and consistent product documentation while preserving the 12-gate model and existing Alpha lifecycle.

**Architecture:** The existing `ControlPlane` remains the single authorization authority. A thin HTTP API exposes its request/pending/approve/deny operations without duplicating policy logic. A separate worker abstraction accepts only a cryptographically bound execution authorization produced after approval, validates the exact request/agent/target and single-use state, and then invokes safe/simulated executors. Alpha remains the downstream governed execution layer and is not replaced.

**Tech Stack:** Python 3.x standard library for the v1 API/worker boundary, existing `controlplane` package, pytest, JSON persistence already used by the control plane, HMAC/SHA-256 for execution-authorization binding.

**Spec:** `docs/superpowers/specs/2026-10-03-forgeos-control-plane-v1-design.md`

## Global Constraints

- ForgeOS remains authoritative over agent permissions and sensitive execution requests.
- Approval binds the exact operation; altered requests must fail closed.
- Approval is single-use and replay attempts must fail closed.
- Evidence is first-class and tamper-evident.
- Deny is terminal for the governed request.
- The control plane and execution worker remain separate components.
- Initial worker executors remain safe/simulated; no real secrets, financial spending, or production deployment.
- Do not replace ForgeOS Alpha or create a second parallel governance system.
- Do not introduce unrestricted shell, unrestricted agent creation, policy self-modification, or real deployment in this milestone.
- Preserve the ForgeOS 12-Gate Governed Execution Model: Identity, Capability, Risk, Policy, Evidence, Verdict, Human Approval, Release, Preflight, Execute, Verify, Rollback.
- Existing Gemini Human Approval behavior and targeted regression tests must remain passing.

## Review Focus

- Exact request tampering: an approved authorization must never execute a changed target, action, tool, or detail.
- Agent/capability drift: changing the registered agent after approval must invalidate execution.
- Authorization replay: a completed authorization must never execute twice.
- Executor substitution: an authorization must not be redirected to an unbound executor or target.
- Restart/persistence boundaries: v1 must fail closed when an execution binding cannot be reconstructed rather than silently falling back to an executor.

---

### Task 1: Capture the live Gemini Human Approval evidence artifact

**Files:**
- Create: `EVIDENCE_HUMAN_APPROVAL_LIVE_2026-10-03.md`

**Interfaces:**
- Consumes: the verified live-run record from the 2026-10-03 Gemini Human Approval test.
- Produces: a committed, human-readable evidence artifact containing the exact run metadata, ALLOW/ASK/DENY outcomes, approval IDs/digests, evidence digests, event count, verification status, simulated-executor limitation, and security-boundary limitation.

- [ ] **Step 1: Write the evidence artifact**
  Include branch/commit, UTC run date, Gemini model, test agent identity/capabilities, all eight operations, the two approval IDs, request digests, approval/execution evidence digests, final snapshot (`events=15`, `evidence_ok=true`, `pending=0`), and an explicit statement that Git push and secret access were simulated and the adapter/worker boundary is still in-process.
- [ ] **Step 2: Review the artifact for accuracy**
  Ensure no API keys or real secrets are included and that every digest is copied exactly from the verified run record.
- [ ] **Step 3: Commit**
  `git add EVIDENCE_HUMAN_APPROVAL_LIVE_2026-10-03.md && git commit -m "docs: record live human approval evidence"`

---

### Task 2: Add failing tests for the Approval API

**Files:**
- Create: `tests/test_controlplane_api.py`
- Reference: `controlplane/store.py`, `controlplane/models.py`, `controlplane/policy.py`

**Interfaces:**
- Consumes: existing `ControlPlane.request`, `ControlPlane.pending`, `ControlPlane.decide`.
- Produces: HTTP-facing handlers for `POST /approvals/request`, `GET /approvals/pending`, `GET /approvals/{approval_id}`, `POST /approvals/{approval_id}/approve`, and `POST /approvals/{approval_id}/deny`.

- [ ] **Step 1: Write request endpoint tests**
  Test valid requests return `allow`, `deny`, or `ask` using the existing policy engine, and ASK responses contain the approval ID and request digest.
- [ ] **Step 2: Write pending/detail endpoint tests**
  Verify pending approvals are returned and individual approval details expose status and exact binding metadata without executing anything.
- [ ] **Step 3: Write approve/deny endpoint tests**
  Verify approval executes exactly once, denial never executes, and malformed/unknown IDs produce deterministic 4xx responses.
- [ ] **Step 4: Write security regression tests**
  Verify the API cannot bypass the existing ControlPlane validation by changing the request after approval or by injecting a replacement executor.
- [ ] **Step 5: Run the new test file**
  Run `pytest tests/test_controlplane_api.py -q`.
  Expected: FAIL because the API module/handlers do not yet exist.

---

### Task 3: Implement the thin Approval API

**Files:**
- Create: `controlplane/api.py`
- Create: `controlplane/api_server.py` if a process entrypoint is needed
- Modify: `controlplane/__init__.py` only if public exports are useful
- Test: `tests/test_controlplane_api.py`

**Interfaces:**
- `ApprovalAPI` owns an existing `ControlPlane` instance and translates JSON HTTP requests into calls to it; it does not evaluate policy independently.
- `POST /approvals/request` accepts `{agent_id, tool, action, target, detail}` and returns the existing ControlPlane decision payload.
- `GET /approvals/pending` returns current pending approval records.
- `GET /approvals/{approval_id}` returns one approval record or 404.
- `POST /approvals/{approval_id}/approve` accepts an optional actor and calls `decide(..., approve=True)`.
- `POST /approvals/{approval_id}/deny` accepts an optional actor and calls `decide(..., approve=False)`.

- [ ] **Step 1: Implement the smallest adapter around ControlPlane**
  Use the Python standard library only; do not add a web framework dependency for this milestone.
- [ ] **Step 2: Keep request parsing and HTTP errors deterministic**
  Return JSON, appropriate 2xx/4xx status codes, and never expose tracebacks or filesystem paths through the API.
- [ ] **Step 3: Re-run API tests**
  Run `pytest tests/test_controlplane_api.py -q`.
  Expected: PASS.
- [ ] **Step 4: Commit**
  `git add controlplane/api.py controlplane/api_server.py controlplane/__init__.py tests/test_controlplane_api.py && git commit -m "feat: add control plane approval API"`

---

### Task 4: Add failing tests for the governed execution authorization boundary

**Files:**
- Create: `tests/test_execution_worker.py`
- Reference: `controlplane/approval.py`, `controlplane/store.py`

**Interfaces:**
- `ExecutionAuthorization` carries approval ID, request digest, agent snapshot digest/binding, target, policy version, issued timestamp/expiry, nonce, and an HMAC signature.
- `ExecutionAuthorizer` creates an authorization only from a successfully approved request.
- `ExecutionWorker.execute(authorization)` validates the authorization and invokes a pre-registered safe executor.

- [ ] **Step 1: Test valid authorization executes once**
  A valid approval-bound authorization reaches the worker and executes the intended simulated operation.
- [ ] **Step 2: Test request tampering**
  Change tool/action/target/detail after signing; worker rejects before execution.
- [ ] **Step 3: Test agent mismatch**
  Change the agent identity or snapshot; worker rejects before execution.
- [ ] **Step 4: Test signature mismatch**
  Modify the signed authorization; worker rejects before execution.
- [ ] **Step 5: Test expiry and replay**
  Expired or already-consumed authorizations fail closed and never execute.
- [ ] **Step 6: Test executor/target substitution**
  An authorization for one registered executor/target cannot be redirected to another.
- [ ] **Step 7: Test missing persisted binding**
  If the worker cannot validate the required binding, it fails closed rather than falling back to the generic `_execute` path.
- [ ] **Step 8: Run the worker test file**
  Run `pytest tests/test_execution_worker.py -q`.
  Expected: FAIL until the worker implementation exists.

---

### Task 5: Implement the governed execution worker boundary

**Files:**
- Create: `controlplane/execution_worker.py`
- Modify: `controlplane/store.py` only where needed to issue a bound authorization after approval
- Test: `tests/test_execution_worker.py`

**Interfaces:**
- `ExecutionAuthorization` is immutable once signed.
- `ExecutionAuthorizer.issue(approval_id) -> ExecutionAuthorization` requires a completed/approved control-plane lifecycle state and uses a configured HMAC key.
- `ExecutionWorker.register_executor(executor_id, target, executor)` registers only known safe/simulated executors.
- `ExecutionWorker.execute(authorization) -> dict` validates signature, expiry, approval ID, request digest, agent snapshot, policy version, executor ID, target, and replay state before executing.

- [ ] **Step 1: Implement canonical authorization serialization**
  Reuse the existing deterministic request serialization approach; never sign non-canonical JSON.
- [ ] **Step 2: Implement HMAC signing and verification**
  Use SHA-256 HMAC with a key supplied by the caller/environment; do not hard-code keys.
- [ ] **Step 3: Implement worker validation**
  Every validation must occur before the executor is called; failures are terminal and fail closed.
- [ ] **Step 4: Implement single-use replay protection**
  Record consumed authorization IDs/nonces in the worker process and reject repeats.
- [ ] **Step 5: Keep executors simulated**
  Provide only safe test executors for this milestone; no real Git push, secret retrieval, spending, or deployment.
- [ ] **Step 6: Run worker tests**
  Run `pytest tests/test_execution_worker.py -q`.
  Expected: PASS.
- [ ] **Step 7: Run existing approval tests**
  Run `pytest tests/test_controlplane_approval.py tests/test_controlplane_execution.py -q`.
  Expected: PASS.
- [ ] **Step 8: Commit**
  `git add controlplane/execution_worker.py controlplane/store.py tests/test_execution_worker.py && git commit -m "feat: add governed execution worker boundary"`

---

### Task 6: Integrate the API/worker path without replacing Alpha

**Files:**
- Modify: `controlplane/demo.py` or add a focused integration test module
- Create: `tests/test_controlplane_integration.py`

**Interfaces:**
- Consumes: Approval API + ControlPlane + ExecutionAuthorizer + ExecutionWorker.
- Produces: a tested path `agent -> API -> ControlPlane -> approval -> authorization -> worker -> simulated executor`.

- [ ] **Step 1: Write end-to-end integration tests**
  Cover an auto-allowed operation, a human-approved operation, and a hard-denied operation.
- [ ] **Step 2: Verify evidence lifecycle**
  Confirm request, approval, authorization, execution, and denial events remain on the same tamper-evident chain.
- [ ] **Step 3: Verify Alpha separation**
  Assert the integration path does not import, replace, or bypass Alpha's governed execution lifecycle.
- [ ] **Step 4: Run integration tests**
  Run `pytest tests/test_controlplane_integration.py -q`.
  Expected: PASS.
- [ ] **Step 5: Commit**
  `git add tests/test_controlplane_integration.py controlplane/demo.py && git commit -m "test: verify governed control plane execution path"`

---

### Task 7: Refresh ForgeOS product and technical documentation

**Files:**
- Modify: `README.md`
- Modify: `controlplane/README.md`
- Create: `docs/FORGEOS_ARCHITECTURE.md`

**Interfaces:**
- Consumes: approved design/spec, 12-gate model, live evidence artifact, API/worker interfaces.
- Produces: consistent product language describing ForgeOS, its purpose, architecture, current scope, and roadmap.

- [ ] **Step 1: Rewrite the root README as product-facing documentation**
  Define ForgeOS as the AI Agent Control Plane and explain the central promise, users/agents, 12 gates, control-plane/execution split, and current maturity.
- [ ] **Step 2: Refresh `controlplane/README.md`**
  Document the technical API, approval binding, evidence model, worker boundary, and safe/simulated execution status.
- [ ] **Step 3: Add architecture reference**
  Document the full architecture and explicitly mark Alpha material as the existing governed execution subsystem rather than obsolete product code.
- [ ] **Step 4: Add external standards context**
  Reference NIST AI RMF only as external context: NIST describes governance as cross-cutting and calls for clear human-AI oversight roles; ForgeOS implements its own product architecture independently. citeturn0search12turn0search14
- [ ] **Step 5: Review terminology**
  Ensure all docs consistently use: AI Agent Control Plane, 12-Gate Governed Execution Model, Control Plane, Execution Gateway/Worker, Alpha governed execution, evidence, approval, fail closed.
- [ ] **Step 6: Commit**
  `git add README.md controlplane/README.md docs/FORGEOS_ARCHITECTURE.md && git commit -m "docs: define ForgeOS product architecture"`

---

### Task 8: Full verification and release checkpoint

**Files:**
- No product files expected unless verification exposes a defect.

**Interfaces:**
- Consumes: all implementation and documentation tasks above.
- Produces: verified branch state suitable for the next ForgeOS hardening phase.

- [ ] **Step 1: Run the complete targeted regression suite**
  `pytest -q tests/test_controlplane_execution.py tests/test_controlplane_approval.py tests/test_gemini_adapter.py tests/test_gemini_approval.py tests/test_controlplane_api.py tests/test_execution_worker.py tests/test_controlplane_integration.py`
- [ ] **Step 2: Run the broader repository test suite**
  `pytest -q`
- [ ] **Step 3: Re-run the live Gemini test with only simulated sensitive executors**
  Confirm ALLOW/ASK/DENY behavior and evidence verification remain intact.
- [ ] **Step 4: Inspect git state and commits**
  Confirm no secrets, temporary workspaces, or generated credentials are tracked.
- [ ] **Step 5: Record the verification result**
  Add a short verification note to the evidence/architecture docs if needed, including exact test commands and outcomes.
- [ ] **Step 6: Commit the final verification documentation**
  Use a focused `docs:` commit if documentation changed.

## Execution Order

1. Task 1 — live evidence artifact
2. Task 2 — failing API tests
3. Task 3 — API implementation
4. Task 4 — failing worker-boundary tests
5. Task 5 — worker implementation
6. Task 6 — integration path
7. Task 7 — documentation refresh
8. Task 8 — full verification

No production deployment, real secret retrieval, real spending, unrestricted shell, or real Git/GitHub execution is introduced by this plan.