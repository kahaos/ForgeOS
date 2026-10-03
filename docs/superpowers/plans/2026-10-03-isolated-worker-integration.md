# Isolated Worker Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the hardened Docker worker a governed execution adapter behind ForgeOS `ExecutionAuthorization`, while preserving the existing control-plane authorization semantics and adding permanent isolation regression coverage.

**Architecture:** `ExecutionAuthorizer` remains the authority that issues a short-lived, signed, executor-bound authorization. `ExecutionWorker` continues to validate signature, expiry, nonce, approval state, request/agent/policy snapshots, executor binding, and target before dispatching; the new Docker adapter becomes the execution mechanism for an already-authorized command and never makes policy decisions. Docker provides the constrained runtime with no network, read-only root, scoped writable workspace, dropped capabilities, no-new-privileges, and resource limits.

**Tech Stack:** Python 3.11+, pytest, Docker Engine, standard-library `subprocess`, dataclasses, existing ForgeOS control-plane persistence and authorization model.

**Spec:** `docs/superpowers/specs/2026-10-03-forgeos-control-plane-v1-design.md` plus the approved isolated-worker design in conversation.

## Global Constraints

- ForgeOS Control Plane remains authoritative for authorization; the Docker worker is not a second policy engine.
- Existing `ExecutionAuthorization` fields and cryptographic binding semantics remain intact unless a test-driven integration requires a minimal interface addition.
- Default isolated execution is offline: Docker network must remain `none`.
- Container root filesystem remains read-only; only the explicitly assigned `/workspace` bind mount is writable.
- All Linux capabilities are dropped and `no-new-privileges` remains enabled.
- Host environment variables must not be forwarded to the container.
- Execution commands are argv sequences, never shell command strings.
- Docker daemon access is a host security boundary; the implementation must not mount `/var/run/docker.sock` into the worker container and must not use `--privileged`.
- Existing Alpha services, production services, and port 8520 must not be modified.
- Docker integration tests must be optional/skip cleanly when Docker is unavailable so the normal portable pytest suite remains runnable.
- Production image references should eventually be digest-pinned; this plan does not introduce mutable-image trust as a final production guarantee.

## Review Focus

- A tampered authorization must fail before the Docker executor is invoked; add/retain an integration test proving the executor invocation count remains zero.
- A replayed authorization must be rejected by the durable nonce mechanism even when the Docker adapter is recreated; test the adapter path rather than only the in-process worker.
- Agent capability or policy drift after authorization must invalidate execution before container creation; add tests that prove no Docker invocation occurs.
- A caller attempting to substitute the executor or target must fail closed; test both executor ID and target binding.
- Docker-unavailable, timeout, non-zero exit, and malformed argv failures must surface as controlled execution errors without bypassing ForgeOS completion/evidence state.

---

### Task 1: Add the isolated execution adapter contract

**Files:**
- Modify: `controlplane/isolated_worker.py`
- Test: `tests/test_isolated_worker.py`

**Interfaces:**
- Consumes: `DockerIsolatedWorker`, `IsolationProfile`, an existing authorized `ActionRequest`, and a workspace path.
- Produces: a small adapter callable/class interface that can execute an already-authorized argv sequence and return a structured result without introducing policy evaluation.

- [ ] **Step 1: Write failing unit tests for the adapter contract**
  - Prove the adapter accepts only argv sequences and an existing workspace.
  - Prove a non-zero container exit is represented in the returned result rather than silently treated as success.
  - Prove timeout/runtime failures are explicit and do not become successful execution results.

- [ ] **Step 2: Run the focused tests and verify they fail for the intended missing interface.**
  - Run: `pytest tests/test_isolated_worker.py -q`
  - Expected: new adapter tests fail while the existing worker tests remain green.

- [ ] **Step 3: Implement the minimum adapter interface.**
  - Keep Docker command construction in `DockerIsolatedWorker`.
  - Do not add authorization checks to the Docker layer.
  - Preserve the existing hard-coded fail-closed profile invariants.

- [ ] **Step 4: Run the focused tests and verify they pass.**
  - Run: `pytest tests/test_isolated_worker.py -q`
  - Expected: PASS.

- [ ] **Step 5: Commit.**
  - Commit message: `feat: define isolated execution adapter`

### Task 2: Add an authorized Docker executor to the existing execution worker

**Files:**
- Modify: `controlplane/execution_worker.py`
- Modify: `controlplane/isolated_worker.py` if the adapter interface requires it
- Test: `tests/test_execution_worker.py`
- Test: `tests/test_adversarial_hardening.py`

**Interfaces:**
- Consumes: `ExecutionAuthorization`, existing `ExecutionWorker.execute()`, executor ID/target binding, and the isolated adapter from Task 1.
- Produces: a registered executor path that performs Docker execution only after the existing `ExecutionWorker` authorization checks succeed.

- [ ] **Step 1: Write failing tests for the authorized Docker path.**
  - Register a Docker-backed executor with an executor ID and target.
  - Issue an approved `ExecutionAuthorization` for that exact executor.
  - Verify the executor receives only the authorized argv/workspace information.
  - Verify the result is recorded through the existing `complete_approved_execution()` lifecycle.

- [ ] **Step 2: Write failing adversarial tests for the Docker-backed path.**
  - Tampered signature/request/target/executor ID: Docker executor invocation count remains zero.
  - Capability drift: zero Docker invocations.
  - Policy drift: zero Docker invocations.
  - Replayed nonce: zero second Docker invocations.

- [ ] **Step 3: Run the focused tests and verify they fail for the missing integration.**
  - Run: `pytest tests/test_execution_worker.py tests/test_adversarial_hardening.py -q`
  - Expected: new Docker-path tests fail without weakening the existing authorization tests.

- [ ] **Step 4: Implement the adapter registration path.**
  - Keep `ExecutionWorker.execute()` as the gatekeeper.
  - Do not move signature, nonce, snapshot, policy, or executor-binding validation into Docker code.
  - The Docker executor receives a fully validated request and runs only the prevalidated argv/workspace supplied by the registration layer.
  - Preserve exact executor ID and target binding.

- [ ] **Step 5: Run the focused tests and verify they pass.**
  - Run: `pytest tests/test_execution_worker.py tests/test_adversarial_hardening.py -q`
  - Expected: PASS.

- [ ] **Step 6: Commit.**
  - Commit message: `feat: govern docker execution with authorization`

### Task 3: Add optional real-Docker isolation regression tests

**Files:**
- Create: `tests/test_isolated_worker_docker.py`
- Modify: `docs/GETTING_STARTED.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: `DockerIsolatedWorker` and the real `python:3.12-alpine` test image.
- Produces: opt-in/skip-cleanly Docker tests that prove the runtime properties already demonstrated on the trial VPS.

- [ ] **Step 1: Write Docker integration tests.**
  - Skip unless `FORGEOS_DOCKER_TESTS=1` and Docker is usable.
  - Test network access fails with `Network is unreachable` or equivalent non-success.
  - Test root filesystem write fails.
  - Test `/workspace` write succeeds and persists to the host workspace.
  - Test host environment variables are absent.
  - Test `NoNewPrivs: 1`.
  - Test effective capabilities are zero.
  - Test timeout raises `RuntimeError("isolated execution timed out")`.

- [ ] **Step 2: Run without Docker integration enabled.**
  - Run: `pytest -q`
  - Expected: all normal tests pass; Docker tests skip cleanly.

- [ ] **Step 3: Run with Docker integration enabled on a Docker host.**
  - Run: `FORGEOS_DOCKER_TESTS=1 pytest tests/test_isolated_worker_docker.py -q`
  - Expected: all Docker isolation tests pass.

- [ ] **Step 4: Update getting-started documentation.**
  - Document the opt-in command and explain that Docker-backed tests require a Docker daemon.
  - Keep the security notes about never mounting the Docker socket into an untrusted worker and never using `--privileged`.

- [ ] **Step 5: Commit.**
  - Commit message: `test: add docker isolation regression suite`

### Task 4: Verify the complete governed execution path

**Files:**
- Modify: `tests/test_adversarial_hardening.py` only if a final end-to-end regression is needed
- No production Alpha files

**Interfaces:**
- Consumes: Tasks 1–3.
- Produces: verified evidence that an approved ForgeOS authorization reaches the isolated Docker worker exactly once and that invalid authorization never reaches it.

- [ ] **Step 1: Run the full portable suite.**
  - Run: `pytest -q`
  - Expected: all tests pass with Docker tests skipped when not explicitly enabled.

- [ ] **Step 2: Run the Docker suite on the hardening VPS.**
  - Run: `FORGEOS_DOCKER_TESTS=1 pytest tests/test_isolated_worker_docker.py -q`
  - Expected: all Docker isolation tests pass.

- [ ] **Step 3: Run the authorized execution demonstration.**
  - Exercise one harmless approved operation through `ExecutionAuthorization` → `ExecutionWorker` → Docker worker.
  - Expected: exactly one execution, evidence/completion recorded, replay rejected.

- [ ] **Step 4: Run the adversarial suite.**
  - Run: `pytest tests/test_adversarial_hardening.py -q`
  - Expected: tamper, drift, substitution, replay, and concurrency protections remain green.

- [ ] **Step 5: Inspect the git diff and verify no Alpha/production files changed.**
  - Run: `git status --short` and `git diff --check`.
  - Expected: only hardening-v1 integration/test/docs changes are present.

- [ ] **Step 6: Commit the verification/documentation changes.**
  - Commit message: `test: verify governed isolated execution path`

### Task 5: CI and release evidence

**Files:**
- Modify: `.github/workflows/human-approval-v1.yml`
- Modify: `docs/GETTING_STARTED.md` if CI invocation needs documenting

**Interfaces:**
- Consumes: the completed test suite.
- Produces: a CI job that always runs the portable suite and does not require privileged Docker access on GitHub-hosted runners.

- [ ] **Step 1: Ensure CI runs the full portable pytest suite on `hardening-v1`.**
  - Keep Docker integration opt-in so CI does not grant the test job broad Docker-daemon authority by default.

- [ ] **Step 2: Run/inspect GitHub Actions for the resulting commit.**
  - Expected: workflow succeeds with the portable suite green.

- [ ] **Step 3: Record the verified VPS Docker results in a dated evidence document only after the VPS run succeeds.**
  - Include test commands, pass counts, and isolation observations; do not record secrets.

- [ ] **Step 4: Final verification before claiming completion.**
  - Confirm portable tests, Docker integration tests, adversarial tests, and CI evidence are all green.
  - Confirm no production/Alpha service was modified.
