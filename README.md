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
      \\               |               /
       \\              |              /
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

`human-approval-v1` is the frozen authority-boundary milestone. `hardening-v1` is the active security-hardening track built on top of it.

The v1 milestone demonstrated a live Gemini agent calling tools through ForgeOS and receiving:

- `ALLOW` for permitted low-risk operations;
- `ASK` for sensitive operations requiring human approval;
- `DENY` for hard-restricted operations such as policy modification, unrestricted agent creation, and spending.

Human approval is bound to the exact request using a deterministic request digest, with agent and policy snapshots recorded in tamper-evident evidence.

The hardened boundary now has additional protections: restart-safe executor metadata, durable single-use execution nonces, request-bound authenticated-agent identity using short-lived HMAC assertions, adversarial replay/tamper/state-drift tests, and a Docker-backed isolated execution boundary with restrictive defaults.

### Current security status

This is still a **development milestone**, not a production security claim.

The default isolated worker profile is intentionally offline and restrictive. It uses a read-only container root filesystem, drops Linux capabilities, enables `no-new-privileges`, limits memory/CPU/PIDs, mounts only a dedicated workspace, and does not forward the host environment. Docker's `none` network driver is used for the baseline worker profile.

The isolated worker is an execution boundary, **not a second authorization system**. ForgeOS authorization remains authoritative; the worker only executes after a valid authorization reaches it.

No real financial spending or real secret retrieval is enabled by this milestone.

## Try ForgeOS

The quickest way to explore the repository is the [Getting Started guide](docs/GETTING_STARTED.md).

For a normal local checkout:

```bash
git clone https://github.com/kahaos/ForgeOS.git
cd ForgeOS
git checkout hardening-v1
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip pytest
pytest -q
```

Run the safe control-plane demo:

```bash
python -m controlplane.demo
```

To try the isolated worker itself, install Docker and run:

```bash
python examples/isolated_worker_demo.py
```

For the real-Docker isolation regression suite, explicitly opt in on a host with a usable Docker daemon:

```bash
FORGEOS_DOCKER_TESTS=1 pytest tests/test_isolated_worker_docker.py -q
```

GitHub Codespaces can be used for the normal Python test suite; the Docker-backed worker additionally requires a usable Docker daemon, which is not automatically provided merely because the development environment is a Codespace.

## Licensing

ForgeOS is licensed under the **Apache License 2.0 (Apache-2.0)**. The repository includes the full `LICENSE` text and `NOTICE` file. Apache 2.0 is a permissive open-source license and includes an express patent license for qualifying contributor patent claims.

## Repository structure

```text
controlplane/
  models.py              Agent and action models
  policy.py              Capability and policy evaluation
  approval.py            Exact-request digest/binding helpers
  agent_identity.py      Request-bound agent authentication prototype
  store.py               Authoritative ControlPlane state/evidence
  evidence.py            Tamper-evident evidence chain
  api.py                 Approval API adapter
  api_server.py          Standard-library HTTP server
  execution_worker.py    Bound authorization + governed worker
  isolated_worker.py     Hardened Docker execution boundary + adapter
  gemini_adapter.py      Gemini tool adapter
  gemini_test/           Live Gemini integration test

tests/
  test_controlplane_*.py Control Plane regression tests
  test_gemini_*.py       Gemini integration/approval tests
  test_execution_worker.py Worker boundary tests
  test_hardening_persistence.py Restart/replay hardening tests
  test_agent_identity.py Agent authentication tests
  test_adversarial_hardening.py Adversarial tamper/replay/state tests
  test_isolated_worker.py Isolated worker security contract tests
  test_isolated_worker_docker.py Opt-in real-Docker isolation tests

examples/
  isolated_worker_demo.py Safe Docker worker demonstration

docs/
  GETTING_STARTED.md     Local, Codespaces and isolated-worker setup

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

Run the complete hardening regression suite:

```bash
pytest -q
```

The portable regression suite is run by GitHub Actions and includes the authorization, adversarial, and isolated-worker contract tests. Real-Docker isolation tests are opt-in and skip cleanly when Docker is unavailable.

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

- **completed:** durable executor metadata across Control Plane restart;
- **completed:** durable single-use execution nonce consumption;
- **completed:** request-bound authenticated agent identity prototype;
- **completed:** adversarial tamper/replay/state-drift regression suite;
- **completed:** hardened Docker-backed isolated worker baseline;
- gateway/API identity enforcement;
- dedicated credential and key management;
- secret isolation;
- network egress policy for explicitly authorized integrations;
- rate and budget controls;
- stronger asymmetric key management;
- transactional multi-worker persistence;
- pinned trusted executor images and image provenance.

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
11. **Secure defaults should not become permanent limitations.** Additional capabilities must be explicit, scoped, and policy-controlled rather than weakening the baseline.

## Status

ForgeOS is under active development. The `human-approval-v1` branch is the frozen authority milestone; `hardening-v1` is the active implementation track for the next security boundaries.
