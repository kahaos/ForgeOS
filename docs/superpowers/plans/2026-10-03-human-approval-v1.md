# Human Approval v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make ForgeOS `ASK` decisions single-use human approvals cryptographically bound to the exact governed request, then prove the lifecycle through a real Gemini continuation.

**Architecture:** Keep the existing Control Plane policy engine as the authorization kernel. Add deterministic request binding and approval metadata in the Control Plane, bind approval fulfilment to the original governed executor, and preserve the existing append-only evidence chain. Extend the Gemini test adapter only after local approval semantics are proven, using the Interactions API's function-result continuation pattern.

**Tech Stack:** Python 3, pytest, dataclasses, JSON persistence, SHA-256, existing ForgeOS evidence log, `google-genai`.

**Spec:** `docs/superpowers/specs/2026-10-03-human-approval-v1.md`

## Global Constraints

- Work only on `human-approval-v1` until implementation and verification are complete.
- Do not modify production deployment services or connect real production targets.
- Do not expose or commit Gemini API keys or other secrets.
- Preserve the existing ALLOW / ASK / DENY policy semantics.
- Preserve the append-only hash-chained evidence verification.
- No production security-boundary claim: the current Gemini adapter remains in-process.
- Follow TDD: each production behavior change begins with a failing test.
- Existing unrelated legacy UI test failures must not be fabricated away.

## Review Focus

- Request tampering after approval must be rejected before execution — covered by digest mismatch tests.
- Capability/policy context drift must invalidate an approval — covered by snapshot/version tests.
- Approval replay must never execute twice — covered by single-use tests.
- Hard-deny operations must remain denied even when the agent owns the nominal capability — covered by explicit hard-deny escalation tests.
- Gemini must resume with the result of the approved function call without bypassing ForgeOS — covered by the live integration test and evidence record.

---

### Task 1: Add deterministic request and approval binding primitives

**Files:**
- Modify: `controlplane/models.py`
- Create: `controlplane/approval.py`
- Test: `tests/test_controlplane_approval.py`

**Interfaces:**
- `approval.py` produces deterministic canonical serialization and SHA-256 request digests.
- `models.py` gains only the minimum approval model fields required by the spec; existing `ActionRequest` compatibility must be preserved.

- [ ] **Step 1: Write failing tests for canonical request hashing**

Test that identical `ActionRequest` values produce identical digests, dictionary key ordering does not change the digest, and changing any governed field changes the digest.

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `pytest tests/test_controlplane_approval.py -q`

Expected: failures because the digest/binding helpers do not yet exist.

- [ ] **Step 3: Implement minimal digest helpers**

Implement canonical JSON using sorted keys and compact separators, then SHA-256 the UTF-8 representation. Keep the helper deterministic and side-effect free.

- [ ] **Step 4: Run the focused tests and verify GREEN**

Run: `pytest tests/test_controlplane_approval.py -q`

Expected: all Task 1 tests pass.

- [ ] **Step 5: Commit**

```bash
git add controlplane/models.py controlplane/approval.py tests/test_controlplane_approval.py
git commit -m "feat: add approval request binding primitives"
```

---

### Task 2: Bind approvals to agent and policy snapshots

**Files:**
- Modify: `controlplane/policy.py`
- Modify: `controlplane/store.py`
- Modify: `controlplane/models.py` if needed by Task 1
- Test: `tests/test_controlplane_approval.py`

**Interfaces:**
- Add `POLICY_VERSION = "controlplane-1.0"`.
- Approval records expose `request_digest`, `agent_snapshot`, `policy_version`, `status`, `actor`, and decision metadata.
- `ControlPlane.request(...)` creates these fields for `ASK` decisions.

- [ ] **Step 1: Write failing tests for approval record contents**

Create a request that produces `ASK` and assert that the pending approval contains the exact request, deterministic digest, agent snapshot, and policy version.

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `pytest tests/test_controlplane_approval.py -q`

Expected: failure because the current approval record lacks the binding fields.

- [ ] **Step 3: Implement approval record construction**

Snapshot the agent identity, sorted capabilities, risk level, and current policy version at request time. Never store a mutable reference to the live `Agent` object.

- [ ] **Step 4: Run tests and verify GREEN**

Run: `pytest tests/test_controlplane_approval.py -q`

Expected: all approval metadata tests pass.

- [ ] **Step 5: Commit**

```bash
git add controlplane/policy.py controlplane/store.py controlplane/models.py tests/test_controlplane_approval.py
git commit -m "feat: bind approvals to policy and agent snapshots"
```

---

### Task 3: Enforce exact-request approval and single-use execution

**Files:**
- Modify: `controlplane/store.py`
- Modify: `controlplane/approval.py`
- Test: `tests/test_controlplane_approval.py`

**Interfaces:**
- `ControlPlane.decide(...)` must validate the stored approval binding before execution.
- Approval decisions are terminal: pending -> approved/denied only once.
- Approval fulfilment must execute the request represented by the original approval record, not a caller-substituted request.

- [ ] **Step 1: Write failing tamper and replay tests**

Cover:
- target changed after approval;
- detail parameter changed after approval;
- agent capabilities changed after approval;
- policy version changed after approval;
- second decision attempt;
- approved request executes exactly once;
- rejected request never executes.

- [ ] **Step 2: Run focused tests and verify RED**

Run: `pytest tests/test_controlplane_approval.py -q`

Expected: failures showing the current `decide()` path does not enforce these bindings.

- [ ] **Step 3: Implement exact binding validation**

Recompute the request digest from the persisted request. Compare it to the stored digest. Validate the approval's agent/policy snapshot against the approval contract. Reject before executor invocation on any mismatch.

- [ ] **Step 4: Implement single-use state transitions**

Ensure only `pending` approvals can be decided. Mark the decision state before execution so a repeated decision cannot execute the same approval twice. Record the execution outcome separately.

- [ ] **Step 5: Run focused tests and verify GREEN**

Run: `pytest tests/test_controlplane_approval.py -q`

Expected: all binding, tamper, replay, approval, and rejection tests pass.

- [ ] **Step 6: Commit**

```bash
git add controlplane/store.py controlplane/approval.py tests/test_controlplane_approval.py
git commit -m "feat: enforce exact single-use approvals"
```

---

### Task 4: Bind the executor to the governed approval

**Files:**
- Modify: `controlplane/store.py`
- Modify: `controlplane/gemini_adapter.py`
- Test: `tests/test_controlplane_approval.py`
- Test: `tests/test_gemini_adapter.py`

**Interfaces:**
- The approval must retain an execution binding/token sufficient to prevent an arbitrary executor from being supplied when an approval is fulfilled.
- The binding must remain compatible with the current in-process Gemini adapter.

- [ ] **Step 1: Write a failing executor-substitution test**

Create an approval using executor A, then attempt to fulfil it through executor B. Assert B is never called and the approval fails closed.

- [ ] **Step 2: Run the focused test and verify RED**

Run: `pytest tests/test_controlplane_approval.py::test_approval_cannot_swap_executor -q`

Expected: failure because the current `decide()` accepts an executor supplied at decision time.

- [ ] **Step 3: Implement minimal executor binding**

Use an explicit in-process execution registry/token associated with the approval. The approval fulfilment path must resolve the originally bound executor and reject mismatches. Do not expose the raw executor through persisted JSON.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run: `pytest tests/test_controlplane_approval.py -q`

Expected: executor substitution is blocked and existing approval tests remain green.

- [ ] **Step 5: Commit**

```bash
git add controlplane/store.py controlplane/gemini_adapter.py tests/test_controlplane_approval.py tests/test_gemini_adapter.py
git commit -m "feat: bind approval execution to original executor"
```

---

### Task 5: Add explicit hard-deny escalation coverage

**Files:**
- Modify: `tests/test_controlplane_approval.py`
- Modify: `tests/test_controlplane_execution.py` only if shared fixtures require it

**Interfaces:**
- No production policy change is expected unless tests expose a regression.

- [ ] **Step 1: Write failing tests for a fully privileged disposable agent**

Register an agent containing `CREATE_AGENT`, `MODIFY_POLICY`, and `SPEND_FUNDS`. Request each corresponding operation and assert `deny`, no approval record, and no executor call.

- [ ] **Step 2: Run tests and verify the expected result**

Run: `pytest tests/test_controlplane_approval.py -q`

If the current policy already passes these tests, record that the tests were added as regression coverage and continue.

- [ ] **Step 3: Run the control-plane test suite**

Run: `pytest tests/test_controlplane_execution.py tests/test_controlplane_approval.py -q`

Expected: all control-plane tests pass.

- [ ] **Step 4: Commit**

```bash
git add tests/test_controlplane_approval.py tests/test_controlplane_execution.py
git commit -m "test: lock down hard-deny escalation behavior"
```

---

### Task 6: Record the complete approval lifecycle in evidence

**Files:**
- Modify: `controlplane/store.py`
- Modify: `controlplane/evidence.py` only if the existing interface cannot represent the required fields
- Test: `tests/test_controlplane_approval.py`

**Interfaces:**
- Evidence events must include approval ID and request digest.
- Required lifecycle events: `approval.requested`, `approval.approved` or `approval.denied`, and `approval.executed` for successful execution.

- [ ] **Step 1: Write failing evidence assertions**

Assert the event sequence and verify every relevant approval event contains the approval ID and request digest.

- [ ] **Step 2: Run focused tests and verify RED**

Run: `pytest tests/test_controlplane_approval.py -q`

Expected: missing lifecycle fields/events cause failures.

- [ ] **Step 3: Implement lifecycle evidence**

Append evidence at each state transition and after successful governed execution. Preserve the existing hash-chain behavior.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run: `pytest tests/test_controlplane_approval.py -q`

Expected: lifecycle and hash-chain assertions pass.

- [ ] **Step 5: Commit**

```bash
git add controlplane/store.py controlplane/evidence.py tests/test_controlplane_approval.py
git commit -m "feat: record approval lifecycle evidence"
```

---

### Task 7: Integrate approval/resume with Gemini

**Files:**
- Modify: `controlplane/gemini_adapter.py`
- Modify: `controlplane/gemini_test/run_gemini.py`
- Modify: `controlplane/gemini_test/README.md`
- Test: `tests/test_gemini_adapter.py`
- Create: `controlplane/gemini_test/EVIDENCE_HUMAN_APPROVAL_V1_2026-10-03.md` after the live run

**Interfaces:**
- Gemini `ASK` results must surface `approval_id` and request digest without executing the governed function.
- After human approval, the adapter must produce the exact function result for the approved call.
- The Gemini continuation must use the original interaction ID and the corresponding function call ID when returning the result.

- [ ] **Step 1: Write failing adapter tests**

Test that an approval-required Gemini tool call pauses execution, that approval execution returns the exact result, and that the adapter can construct the correct continuation payload.

- [ ] **Step 2: Run tests and verify RED**

Run: `pytest tests/test_gemini_adapter.py -q`

Expected: failures for the new approval/resume behavior.

- [ ] **Step 3: Implement the adapter approval pause/resume path**

Keep the model's function-call ID and interaction ID associated with the pending approval. Do not execute the function while the approval is pending.

- [ ] **Step 4: Run adapter tests and verify GREEN**

Run: `pytest tests/test_gemini_adapter.py -q`

Expected: all Gemini adapter tests pass.

- [ ] **Step 5: Run the combined local suite**

Run: `pytest tests/test_controlplane_execution.py tests/test_controlplane_approval.py tests/test_gemini_adapter.py -q`

Expected: all relevant tests pass.

- [ ] **Step 6: Commit**

```bash
git add controlplane/gemini_adapter.py controlplane/gemini_test/run_gemini.py controlplane/gemini_test/README.md tests/test_gemini_adapter.py
git commit -m "feat: integrate Gemini with human approval resume"
```

---

### Task 8: Execute and document the live Gemini approval proof

**Files:**
- Create: `controlplane/gemini_test/EVIDENCE_HUMAN_APPROVAL_V1_2026-10-03.md`

**Interfaces:**
- No production behavior changes; this task produces evidence only.

- [ ] **Step 1: Run the real Gemini integration on the VPS/test environment**

Use the existing environment variables and test model configuration. Do not print the API key. Force or reliably elicit an approval-required function call.

- [ ] **Step 2: Approve the exact pending request**

Capture the approval ID and request digest, approve it as the human actor, and continue the Gemini interaction with the exact function result.

- [ ] **Step 3: Verify tamper resistance in the live harness**

Attempt a modified request using the same approval ID/digest context and verify ForgeOS rejects it without invoking the executor.

- [ ] **Step 4: Verify evidence integrity**

Confirm the evidence log reports `evidence_ok: true` and contains the complete approval lifecycle.

- [ ] **Step 5: Write the evidence record**

Record date, branch, agent, model, request, approval ID, digest, decision, execution result, evidence verification, and explicit limitations. Never record secrets.

- [ ] **Step 6: Commit the evidence**

```bash
git add controlplane/gemini_test/EVIDENCE_HUMAN_APPROVAL_V1_2026-10-03.md
git commit -m "docs: record Human Approval v1 live evidence"
```

---

### Task 9: Final verification and branch review

**Files:**
- No planned source changes.

- [ ] **Step 1: Run the complete relevant test set**

Run: `pytest tests/test_controlplane_execution.py tests/test_controlplane_approval.py tests/test_gemini_adapter.py -q`

Expected: zero failures.

- [ ] **Step 2: Inspect the branch diff against `gemini-controlplane-test`**

Run: `git diff --stat gemini-controlplane-test...HEAD` and inspect all changed files.

Expected: only Human Approval v1 implementation, tests, documentation, and evidence are present.

- [ ] **Step 3: Verify no secrets were added**

Run an appropriate repository search for API-key-like values and inspect the diff manually.

Expected: no Gemini API key, credential, token, or private secret is committed.

- [ ] **Step 4: Verify evidence before claiming completion**

Re-run the live/local verification required by the completion claim and record the actual output. Do not infer success from prior runs.

- [ ] **Step 5: Prepare the branch for review**

Create a PR from `human-approval-v1` into `gemini-controlplane-test` only after fresh verification. Do not merge automatically.
