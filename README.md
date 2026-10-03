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
   | task
   | scope
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

ForgeOS is intended to become a general-purpose authority layer for increasingly capable agents, including coding, research, SEO/content, website/operations, infrastructure, business automation and multi-agent systems.

The agents can be highly autonomous. **The authority does not move with the agent.** Sensitive capabilities remain governed by ForgeOS.

The long-term architecture is one shared control plane rather than a different permission system for every agent.

## Scoped Authority v1

The active `scoped-authority-v1` implementation extends the original flat capability model with task-scoped authority:

```text
Agent
  -> Task
  -> Capability Grant
  -> Resource Scope
  -> Risk / Policy
  -> Allow / Ask / Deny
  -> Short-lived signed authorization
  -> Provider / Executor
  -> Evidence
```

A grant can be as narrow as:

```text
Agent: website-agent
Task: website-build
Capability: GIT_PUSH
Repository: company/site
Branch: feature/*
Expiry: task expiry
```

The same agent can therefore push its assigned feature branch autonomously while a push to `main` can require human approval. An unrelated repository is denied regardless of the agent's other capabilities.

### Multi-agent authority

Agents are independent principals. A single task can contain several agents without merging their permissions:

```text
Task: Build Website
├── Website Agent
│   └── Git push: company/site / feature/*
├── SEO Agent
│   └── Website content / feature/*
└── Deployment Agent
    └── production deployment / approval required
```

Delegation uses explicit parent grants and can only attenuate authority. A child cannot widen the repository, capability, environment or expiry inherited from its parent.

### Runtime gateway

The provider-neutral runtime gateway is deliberately above provider-native controls. It does not replace GitHub, AWS, Entra, OAuth or MCP authorization. Provider adapters retain their own credentials and controls while ForgeOS supplies the task-scoped runtime authority decision and evidence boundary.

NIST's current agent identity and authorization work is examining task-scoped/contextual authorization, ephemeral access, proof of authority, delegation, auditing and non-repudiation for agentic systems. NIST's September 2026 comment summary specifically describes strong support for task-scoped authorization and attenuation through delegation chains. OWASP's September 2026 Agent Control Standard similarly focuses on portable runtime enforcement hooks for agent platforms.

See `docs/FORGEOS_ARCHITECTURE.md` for the detailed model.

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

> **The Control Plane decides whether an operation is authorized. Alpha governs the execution lifecycle.**

## Current v1 milestone

`human-approval-v1` is the frozen authority-boundary milestone. `hardening-v1` is the active security-hardening track. `scoped-authority-v1` is the next feature branch extending that hardened boundary into task-scoped multi-agent authority.

The hardened boundary includes restart-safe executor metadata, durable single-use execution nonces, request-bound authenticated-agent identity using short-lived HMAC assertions, adversarial replay/tamper/state-drift tests, and a Docker-backed isolated execution boundary with restrictive defaults.

The isolated worker is an execution boundary, **not a second authorization system**. ForgeOS authorization remains authoritative; the worker only executes after a valid authorization reaches it.

No real financial spending or real secret retrieval is enabled by this milestone.

## Try ForgeOS

The quickest way to explore the repository is the `docs/GETTING_STARTED.md` guide.

For a normal local checkout:

```bash
git clone https://github.com/kahaos/ForgeOS.git
cd ForgeOS
git checkout scoped-authority-v1
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip pytest
pytest -q
```

Run the safe multi-agent scoped-authority demo:

```bash
python examples/scoped_multi_agent_demo.py
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

## Licensing

ForgeOS is licensed under the **Apache License 2.0 (Apache-2.0)**. The repository includes the full `LICENSE` text and `NOTICE` file.

## Repository structure

```text
controlplane/
  models.py              Agent and action models
  authority.py           Task, scope and capability-grant primitives
  policy.py              Legacy and scoped policy evaluation
  approval.py            Exact-request digest/binding helpers
  agent_identity.py      Request-bound agent authentication prototype
  store.py               Authoritative ControlPlane state/evidence
  evidence.py            Tamper-evident evidence chain
  api.py                 Approval + scoped authority API adapter
  api_server.py          Standard-library HTTP server
  gateway.py             Provider-neutral runtime gateway/adapters
  execution_worker.py    Signed authorization + governed worker
  isolated_worker.py     Hardened Docker execution boundary + adapter
  gemini_adapter.py      Gemini tool adapter

tests/
  test_scoped_authority.py       Scope/task/grant/delegation tests
  test_scoped_authority_api.py   Scoped API tests
  test_runtime_gateway.py         Multi-agent runtime tests
  test_scoped_execution_binding.py Signed scope-binding tests
  test_execution_worker.py        Worker boundary regression tests
  test_adversarial_hardening.py   Adversarial tamper/replay/state tests
  test_isolated_worker_docker.py  Opt-in real-Docker isolation tests

examples/
  scoped_multi_agent_demo.py     Safe multi-agent authority demonstration
  isolated_worker_demo.py        Safe Docker worker demonstration

docs/
  FORGEOS_ARCHITECTURE.md        Scoped multi-agent architecture
  GETTING_STARTED.md              Local/Codespaces/worker setup

docs/superpowers/
  specs/                           Approved architecture specifications
  plans/                           Implementation plans
```

## API surface

Existing approval endpoints remain supported:

```text
POST /approvals/request
GET  /approvals/pending
GET  /approvals/{approval_id}
POST /approvals/{approval_id}/approve
POST /approvals/{approval_id}/deny
```

Scoped authority adds:

```text
POST /tasks
GET  /tasks/{task_id}
POST /tasks/{task_id}/revoke
GET  /tasks/{task_id}/grants
POST /tasks/{task_id}/grants
POST /scoped/request
GET  /agents/{agent_id}/authority
GET  /authority/graph
```

The API never accepts a client-supplied grant as proof of authority. The Control Plane resolves effective authority from persisted task/grant state.

## Development

Run the full local suite:

```bash
pytest -q
```

The Docker-backed tests are opt-in because they require a usable Docker daemon. Do not grant broad Docker socket access merely to run the normal Python suite.
