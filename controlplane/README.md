# ForgeOS Control Plane

The `controlplane` package is the authoritative authorization layer for ForgeOS.

It sits between an agent and the systems the agent may touch:

```text
agent
  -> identity
  -> capability
  -> risk
  -> policy
  -> evidence
  -> verdict
  -> human approval (when required)
  -> bound execution authorization
  -> Execution Worker
```

The package is deliberately **not** an AI model and is not the autonomous agent. Its job is to govern agent authority.

## 12 gates

The Control Plane owns the first authorization gates of the ForgeOS 12-Gate Governed Execution Model:

1. Identity
2. Capability
3. Risk
4. Policy

The downstream governed execution layer owns:

5. Evidence
6. Verdict
7. Human Approval
8. Release
9. Preflight
10. Execute
11. Verify
12. Rollback

The split is architectural: the Control Plane answers **"may this agent request this operation?"** while ForgeOS Alpha remains responsible for the governed execution lifecycle.

## Core modules

### `models.py`

Defines `Agent`, `ActionRequest`, and `Decision`.

### `policy.py`

Evaluates capabilities and hard-deny rules. Policy version is explicit and becomes part of approval binding.

### `approval.py`

Provides deterministic request hashing and agent snapshot binding. The request digest covers the complete governed request, including agent, tool, action, target, and detail.

### `store.py`

`ControlPlane` is the authoritative state machine for registration, action requests, approvals, evidence, and execution completion.

Important lifecycle behaviour:

```text
request
  -> allow
  -> deny
  -> ask / pending
       |
       +-> human deny -> denied
       |
       +-> human approve -> approved
                                |
                                v
                         Execution Worker
                                |
                         successful execution
                                |
                                v
                            completed
```

The existing `decide(..., execute=True)` behaviour remains for compatibility with the original in-process approval tests. The API path uses `execute=False` so approval authorizes the operation without executing it; the separate Execution Worker then consumes the authorization.

Executor identity/target bindings are now persisted in `executors.json`, allowing an approved authorization to be issued after a Control Plane restart. The executable callable is intentionally still registered by the live worker process, so a restart cannot silently recreate executable authority.

Execution nonces are persisted in `execution_nonces.json` and consumed under a Unix file lock. This makes the single-use authorization decision survive worker restarts. A failed executor does not release its consumed nonce; retry requires a new authorization.

### `agent_identity.py`

Provides the first authenticated-agent identity prototype. An agent proves possession of a provisioned secret by producing an HMAC assertion bound to:

- agent identity;
- ForgeOS audience;
- exact request digest;
- issue/expiry timestamps;
- single-use nonce.

The verifier uses constant-time MAC comparison and rejects wrong secrets, request/audience substitution, expiry, signature tampering, and replay. Secrets remain process-local in this prototype; production key management will move the trust anchor into a dedicated credential system and should prefer sender-constrained/asymmetric credentials.

### `evidence.py`

Maintains the tamper-evident evidence chain. Approval requests, decisions, grants, executions, and failures are recorded as evidence events.

### `api.py`

Thin adapter exposing:

```text
POST /approvals/request
GET  /approvals/pending
GET  /approvals/{approval_id}
POST /approvals/{approval_id}/approve
POST /approvals/{approval_id}/deny
```

The API contains no independent policy engine. It delegates to the existing `ControlPlane`.

### `api_server.py`

A small Python standard-library HTTP server around `ApprovalAPI`, intended for local development and integration testing.

### `execution_worker.py`

Implements the next security boundary between authorization and execution.

`ExecutionAuthorizer` creates a short-lived `ExecutionAuthorization` containing:

- approval ID;
- exact request;
- request digest;
- agent snapshot and snapshot digest;
- policy version;
- exact executor identity;
- exact target;
- issue and expiry timestamps;
- single-use nonce;
- HMAC-SHA-256 signature.

`ExecutionWorker` validates the authorization before invoking an executor. It rejects:

- altered authorization payloads;
- expired authorizations;
- replayed authorizations;
- missing approvals;
- request digest mismatches;
- agent capability/identity drift;
- policy drift;
- executor substitution;
- target substitution;
- unknown executors.

After successful execution, the worker records completion through the Control Plane so the approval lifecycle and evidence chain remain authoritative.

## Security model

The v1 worker uses HMAC-SHA-256 for the authorization prototype and constant-time signature comparison. Python's `hmac.compare_digest()` is specifically intended for secure comparison of externally supplied MACs. citeturn1search0

Nonces are generated with Python's `secrets` module, which provides cryptographically strong randomness suitable for security tokens. citeturn2search3

Authorization state is written with atomic file replacement, and nonce consumption uses an exclusive Unix file lock. These mechanisms are appropriate for the current development worker boundary, but they are **not** the final production state store or key-management architecture. Python documents `os.replace()` as atomic when the replacement occurs successfully on the same filesystem, and `fcntl.flock()` provides exclusive file locking on Unix. citeturn4search0turn2search0

The authenticated-agent prototype follows the same principle of request-bound, short-lived, replay-resistant assertions. NIST's current agent-identity work emphasizes first-class agent identities, tightly scoped short-lived credentials, request binding, and proof-of-possession rather than relying on long-lived bearer credentials. citeturn7search0turn7search1

The production roadmap still requires durable agent credential storage/rotation, stronger asymmetric key management, isolated workers, secret isolation, network controls, durable multi-process state, and adversarial security testing.

## Current limitations

This v1 milestone intentionally does not enable:

- real secret retrieval;
- real financial spending;
- unrestricted shell;
- production deployment;
- unrestricted agent creation;
- agent-controlled policy modification.

Executor metadata and replay state are now durable, but executor function bindings remain process-local by design. A restarted worker must explicitly re-register the executor callable before it can execute anything. This prevents persistence from becoming an implicit permission to execute.

Agent authentication secrets are process-local and are not persisted, rotated, or exposed through the HTTP API yet. The next identity step is to bind `AgentAuthenticator` into the gateway/API and then replace shared-secret provisioning with a dedicated credential/key-management layer.

The JSON store is still a development persistence layer rather than a production database. The next persistence hardening step is a transactional multi-worker store with stronger concurrency guarantees.

## Run

Demo:

```bash
python -m controlplane.demo
```

Local approval API:

```bash
python -m controlplane.api_server
```

The default development server listens on `127.0.0.1:8520` and stores Control Plane state under `data/controlplane` when launched as a module.

## Tests

The v1 CI suite covers:

- Control Plane execution;
- exact approval binding;
- approval tamper detection;
- capability/policy drift;
- executor substitution;
- hard denies;
- approval evidence;
- API routing and malformed input;
- real HTTP approval API routing;
- authorization signing;
- expiry;
- replay protection;
- executor/target binding;
- worker fail-closed behaviour;
- restart-safe executor binding;
- durable nonce consumption;
- no-retry-after-failed-execution replay protection;
- authenticated agent request binding;
- agent secret, audience, signature, expiry, and replay failures.

The latest verified hardening regression run completed with **45 tests passing**.
