# ForgeOS

## AI Agent Control Plane

**ForgeOS is the control plane for autonomous AI agents.**

It sits between an AI agent and the systems, tools, data, accounts, and real-world actions that agent is allowed to touch.

> **Let AI agents act autonomously without giving them unrestricted authority.**

ForgeOS is not the AI model and it is not the autonomous agent. It is the authoritative enforcement layer that decides whether an agent may request an operation, whether that operation needs human approval, and how an approved operation is allowed to reach an executor.

```text
AI Agent
   |
   v
ForgeOS Control Plane
   | identity
   | capability
   | risk
   | policy
   | evidence
   | verdict
   | human approval
   |
   v
Bound Execution Authorization
   |
   v
ForgeOS Execution Worker
   |
   v
ForgeOS Alpha governed execution
   |
   v
Real target
```

## What we are building

ForgeOS is intended to become a general-purpose authority layer for increasingly capable agents, including:

- coding agents;
- research agents;
- SEO and content agents;
- website and operations agents;
- business automation agents;
- infrastructure and deployment agents;
- multi-agent systems.

The agents can be highly autonomous. **The authority does not move with the agent.** Sensitive capabilities remain governed by ForgeOS.

The long-term architecture is one shared control plane rather than a different permission system for every agent.

```text
Coding Agent     Research Agent     SEO Agent
      \               |               /
       \              |              /
        +-------------v-------------+
        |          ForgeOS          |
        |     authoritative gates   |
        +-------------+-------------+
                      |
             governed execution
                      |
          Git / Cloud / Web / Data
```

## The ForgeOS 12-Gate Governed Execution Model

ForgeOS keeps the 12-gate model as a core architecture standard. The gates are layered rather than treated as one flat linear pipeline.

### Control Plane authorization gates

1. **Identity** — which agent is making the request?
2. **Capability** — what capabilities does that agent possess?
3. **Risk** — what risk level applies to the operation?
4. **Policy** — is the requested operation permitted, denied, or subject to approval?

### Governed execution gates

5. **Evidence** — has the operation and its context been recorded?
6. **Verdict** — what did ForgeOS decide?
7. **Human Approval** — when required, did an authorized human approve the exact request?
8. **Release** — is the approved operation released for execution?
9. **Preflight** — are execution prerequisites satisfied?
10. **Execute** — does the governed executor perform the operation?
11. **Verify** — did the result satisfy the required checks?
12. **Rollback** — if execution fails or verification fails, can the governed system recover safely?

The key distinction is:

> **The Control Plane decides whether an operation is authorized. Alpha governs the execution lifecycle.**

ForgeOS therefore does not replace ForgeOS Alpha. The Control Plane becomes the authority above the governed execution layer.

## Current v1 milestone

The current branch is `human-approval-v1`.

The current milestone has demonstrated a live Gemini agent calling tools through ForgeOS and receiving:

- `ALLOW` for permitted low-risk operations;
- `ASK` for sensitive operations requiring human approval;
- `DENY` for hard-restricted operations such as policy modification, unrestricted agent creation, and spending.

Human approval is bound to the exact request using a deterministic request digest, with agent and policy snapshots recorded in tamper-evident evidence.

The next boundary is the governed Execution Worker. It receives a short-lived, cryptographically bound execution authorization and independently rejects altered requests, expired/replayed authorizations, agent drift, policy drift, executor substitution, and target substitution.

### Current security status

This is still a **development milestone**, not a production security claim.

The current worker uses simulated/safe executors and an in-process control-plane store. The next security milestones include durable authorization state, isolated worker processes/containers, secret isolation, authenticated agent identities, network egress controls, rate/budget controls, real Git/GitHub/filesystem/shell integrations, and adversarial testing.

No real financial spending or real secret retrieval is enabled by this milestone.

## Repository structure

```text
controlplane/
  models.py              Agent and action models
  policy.py              Capability and policy evaluation
  approval.py            Exact-request digest/binding helpers
  store.py               Authoritative ControlPlane state/evidence
  evidence.py            Tamper-evident evidence chain
  api.py                 Approval API adapter
  api_server.py          Standard-library HTTP server
  execution_worker.py    Bound authorization + governed worker
  gemini_adapter.py      Gemini tool adapter
  gemini_test/           Live Gemini integration test

tests/
  test_controlplane_*.py Control Plane regression tests
  test_gemini_*.py       Gemini integration/approval tests
  test_execution_worker.py Worker boundary tests

docs/superpowers/
  specs/                 Approved architecture specifications
  plans/                 Implementation plans

ForgeOS Alpha/           Historical governed-execution material
```

## Approval API

The v1 API surface is intentionally small:

```text
POST /approvals/request
GET  /approvals/pending
GET  /approvals/{approval_id}
POST /approvals/{approval_id}/approve
POST /approvals/{approval_id}/deny
```

The API is a thin adapter over the existing `ControlPlane`. It does not create a second authorization system.

Approval is separated from execution at the worker boundary: the API grants authorization, then the Execution Worker consumes the exact authorization once.

## Development

Run the local demo:

```bash
python -m controlplane.demo
```

Run the approval API server locally:

```bash
python -m controlplane.api_server
```

Run the v1 regression suite:

```bash
PYTHONPATH=. pytest \
  tests/test_controlplane_execution.py \
  tests/test_controlplane_approval.py \
  tests/test_gemini_adapter.py \
  tests/test_gemini_approval.py \
  tests/test_controlplane_api.py \
  tests/test_execution_worker.py -q
```

## Roadmap

### v1 — Authority boundary

- Control Plane identity/capability/risk/policy;
- human approval;
- exact request binding;
- evidence;
- approval API;
- cryptographically bound execution authorization;
- safe Execution Worker.

### v1.1 — Harden the boundary

- durable execution authorizations;
- authenticated agent identities;
- isolated worker process/container;
- secret isolation;
- replay protection across restarts;
- network egress policy;
- rate and budget controls;
- stronger key management.

### v1.5 — Real integrations

- Git/GitHub execution;
- filesystem and shell sandboxes;
- cloud APIs;
- deployment providers;
- external tool adapters;
- richer evidence and verification.

### v2 — Multi-agent control plane

- multiple agent identities;
- delegated capabilities;
- agent-to-agent authorization;
- shared budgets;
- orchestration policies;
- policy-as-code;
- operator UI;
- organization/workspace controls.

### v3 — Enterprise/autonomous operations

- distributed execution workers;
- high-assurance audit infrastructure;
- policy simulation;
- approval workflows and roles;
- enterprise identity providers;
- large-scale multi-agent governance.

## Design principles

1. **ForgeOS is authoritative.** Agents cannot grant themselves authority.
2. **Approval binds the exact operation.** Changing the request invalidates the authorization.
3. **Deny is terminal.** A denied operation does not become allowed through agent-side escalation.
4. **Approval is single-use.** Replays are rejected.
5. **Evidence is first-class.** Governance decisions and execution results are recorded.
6. **Fail closed.** Missing or inconsistent authorization data blocks execution.
7. **Control and execution are separate.** The authority layer decides; the worker executes.
8. **Alpha remains the governed execution lifecycle.** The Control Plane does not replace it.
9. **Sensitive capabilities remain outside autonomous agent authority.**
10. **Security boundaries must be tested, not assumed.**

## Status

ForgeOS is under active development. The `human-approval-v1` branch is the current implementation track for the Control Plane authority boundary.
