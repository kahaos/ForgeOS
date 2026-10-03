# ForgeOS

## AI Agent Control Plane

**ForgeOS is the control plane for autonomous AI agents.**

It sits between an AI agent and the systems, tools, data, accounts, and real-world actions that agent is allowed to touch.

> **Let AI agents act autonomously without giving them unrestricted authority.**

ForgeOS is not the AI model and it is not the autonomous agent. It is the authoritative enforcement layer that decides whether an agent may request an operation, whether that operation needs human approval, and how an approved operation is allowed to reach an executor.

```text
1. Product definition
ForgeOS is an AI agent control plane: an enforcement and evidence layer between autonomous AI agents and the tools, systems, data, accounts, and real-world actions they are allowed to touch.

The product is intended to let organizations run increasingly capable AI agents without giving those agents unrestricted authority. ForgeOS should make agent actions explicit, policy-controlled, approval-aware, attributable, and auditable.

Core model:

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
   | capabilities
   | risk
   | policy
   | approval
   | evidence
   |
   v
Execution Gateway
   |
   v
Governed Executor / ForgeOS Alpha
   |
   v
Real target
ForgeOS is not an AI model and is not itself the autonomous agent. It governs what an agent is permitted to request and controls the path by which an approved operation can reach an executor.

2. Product objective
The long-term objective is a general-purpose control plane for AI workers, including coding agents, research agents, SEO agents, operations agents, business agents, and future multi-agent systems.

A ForgeOS-controlled agent should be able to work autonomously inside clearly defined boundaries while ForgeOS remains authoritative over sensitive actions.

The central product promise is:

Let AI agents act autonomously without giving them unrestricted authority.

3. Non-goals for this milestone
No production deployment integration.
No real secret retrieval.
No unrestricted shell access.
No real financial spending.
No agent-controlled policy modification.
No unrestricted agent creation.
No replacement of the existing ForgeOS Alpha governed execution lifecycle.
No second, parallel authorization system.
4. Architectural principles
4.1 ForgeOS is authoritative
Executors must not implement their own independent permission model. Sensitive operations enter through the ForgeOS authorization path.

4.2 Approval binds to the exact operation
A human approval is not a generic permission. It is bound to the exact request, agent snapshot, policy version, and execution binding.

4.3 Deny is terminal
A denied request must not reach an executor.

4.4 Approval is single-use
An approval must not be reusable for a second execution.

4.5 Evidence is first-class
Every meaningful authorization and execution transition should produce tamper-evident evidence and remain traceable to the originating request.

4.6 Fail closed
If an approval binding cannot be verified, if the executor binding is unavailable, or if policy/identity data has changed, ForgeOS must refuse execution rather than guess.

4.7 Separate control from execution
The control plane decides whether an operation may proceed. The execution boundary performs the operation. This separation becomes a security boundary as the system matures.

5. v1 approval API
Introduce a small HTTP API around the Control Plane:

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
The API must expose the exact request being approved, its digest, agent identity/snapshot, policy version, target, status, timestamps, and evidence identifiers.

The approval API must call the existing ControlPlane.request() and ControlPlane.decide() paths rather than duplicating authorization logic.

The first implementation may use a local development server and JSON responses. Authentication and production transport hardening are later milestones, but the API shape should not require a second authorization model.

6. Live evidence artifact
Create a committed evidence record for the successful 2026-10-03 live Gemini Human Approval run.

It should document:

branch and commit under test
date/time
Gemini model
test agent identity
capabilities
each ALLOW / ASK / DENY operation
both human approval IDs
request digests
approval evidence digests
execution evidence digests
final event count
final evidence_ok state
the fact that Git push and secret access were simulated in this test
limitations of the current in-process boundary
The artifact is evidence of the prototype behaviour, not a claim of production security.

7. Execution boundary
Create a governed execution service/worker abstraction so the Gemini process is not itself the final trust boundary.

Initial design:

Gemini / other agent
        |
        | action request
        v
ForgeOS Gateway
        |
        +--> identity + capability + risk
        +--> policy
        +--> approval
        +--> evidence
        |
        | signed/bound execution authorization
        v
Execution Worker
        |
        +--> executor adapter
        v
     target system
The first worker should continue using safe/simulated executors. Real GitHub, secret, shell, network, and deployment adapters are separate follow-on work.

The worker must receive an execution authorization that is cryptographically or otherwise strongly bound to the original request and approval. It must reject altered requests, expired/replayed authorizations, mismatched agents, and mismatched targets.

8. Relationship with ForgeOS Alpha
The existing Alpha governed execution system remains part of ForgeOS.

Control Plane answers:

Is this agent allowed to request this operation, and does it require human approval?

Alpha answers:

Has this specific operation completed ForgeOS's governed lifecycle?

The intended lifecycle becomes:

agent
 -> request
 -> control-plane decision
 -> approval if required
 -> execution authorization
 -> Alpha verdict/release
 -> preflight
 -> execution
 -> verification
 -> rollback if required
 -> correlated evidence
9. Product documentation refresh
Update the repository documentation so it consistently describes ForgeOS as the AI agent control plane rather than as a historical Alpha patch package.

Documentation should include:

what ForgeOS is
why it exists
the control-plane architecture
agent identity and capabilities
ALLOW / ASK / DENY
human approval
evidence and auditability
relationship between Control Plane and Alpha
current status and demonstrated capabilities
known limitations
roadmap toward a secure multi-agent execution platform
clear distinction between prototype/simulated executors and future real integrations
The root README becomes the product-facing entry point. controlplane/README.md becomes the technical control-plane guide. Existing historical Alpha material should remain discoverable but clearly labelled as historical implementation/laboratory material.

10. Test strategy
Before merging implementation changes:

Unit-test request/API serialization and approval lifecycle.
Test API ALLOW / ASK / DENY behaviour through the real Control Plane.
Test approval tampering, capability drift, policy drift, executor substitution, replay, and single-use behaviour.
Test execution-worker rejection of invalid authorization bindings.
Run the existing Human Approval v1 regression suite.
Run the live Gemini test only with simulated sensitive executors.
Record a new evidence artifact after a successful live run.
Historical legacy UI test failures caused by missing unrelated patch artifacts remain separate from this milestone and must not be fabricated away.

11. Security hardening roadmap
After the v1 API and execution boundary:

authenticated agent identities
signed execution authorizations
durable approval/executor bindings across process restarts
secret isolation
sandbox/container isolation
network egress controls
replay protection with expiry/nonces
rate and budget controls
real Git/GitHub adapters
controlled filesystem and shell adapters
deployment environments with explicit gates
security/adversarial testing
policy version lifecycle and controlled policy administration
UI for live requests, approvals, executions, and evidence
multi-agent orchestration under the same control plane
12. Definition of success
This milestone succeeds when an AI agent can request a sensitive operation, ForgeOS can deterministically return ALLOW/ASK/DENY, a human can approve the exact request, only the exact approved operation can reach the execution worker, and the complete lifecycle can be reconstructed from tamper-evident evidence.

The system should then be capable of becoming the common enforcement layer for many agents and many tools without creating a separate permission model for each executor.
