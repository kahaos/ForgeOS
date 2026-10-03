# ForgeOS — AI Agent Control Plane

**Let AI agents act autonomously without giving them unrestricted authority.**

ForgeOS is an open-source **AI agent control plane** for authorization, human approval, governed execution, and evidence. It sits between autonomous AI agents and the tools, systems, data, accounts, and real-world actions they are allowed to touch.

> **Agent autonomy should not mean unrestricted authority.**

[Try the real-agent trial](docs/REAL_AGENT_QUICKSTART.md) · [Read the security model](docs/SECURITY_MODEL.md) · [Explore the architecture](docs/FORGEOS_ARCHITECTURE.md) · [See the roadmap](docs/ROADMAP.md)

## Why ForgeOS?

AI agents are increasingly capable of coding, researching, operating systems, managing content, calling APIs, and coordinating with other agents. Authentication alone does not answer the runtime question:

> **Is this agent allowed to perform this exact action, against this exact resource, for this task, right now?**

ForgeOS is designed to answer that question with explicit, task-scoped authority.

It is aimed at developers, security engineers, platform teams, AI infrastructure builders, and researchers working on **AI agent security, agent authorization, agent identity, least privilege, multi-agent security, runtime governance, and secure autonomous execution**.

## The core model

```text
AI Agent
   │
   ▼
ForgeOS Control Plane
   ├─ Identity
   ├─ Capability
   ├─ Task
   ├─ Scope
   ├─ Risk
   └─ Policy
   │
   ▼
ALLOW / ASK / DENY
   │
   ├── Evidence
   ├── Human approval when required
   └── Short-lived execution authorization
               │
               ▼
       ForgeOS Execution Worker
               │
               ▼
        Provider / Executor
```

The control plane remains authoritative. The execution worker does not create a second permission system.

## Task-scoped AI agent authorization

A ForgeOS grant can be narrow enough to describe one task and one resource boundary:

```text
Agent:       website-agent
Task:        website-build
Capability:  GIT_PUSH
Repository:  company/site
Branch:      feature/*
Expiry:      task expiry
```

That means an agent can work autonomously on its assigned feature branch while a different repository or production branch falls outside its authority.

### Multi-agent security

Agents remain separate principals even when they cooperate on one task:

```text
Build Website
├── Website Agent
│   └── Git push → company/site / feature/*
├── SEO Agent
│   └── Git commit → company/site / feature/*
└── Deployment Agent
    └── Production deploy → human approval
```

Delegation is explicit and attenuating: a child grant cannot widen the parent's capability, resource scope, or expiry.

Read more: [AI agent authorization](docs/AI_AGENT_AUTHORIZATION.md) · [Multi-agent security](docs/MULTI_AGENT_SECURITY.md)

## ALLOW, ASK, DENY

**ALLOW** — the operation matches active task-scoped authority and policy and can enter the governed execution path.

**ASK** — the operation is potentially permitted but requires an authorized human decision before execution.

**DENY** — no applicable authority exists or policy prohibits the operation. A denied request must not reach an executor.

## The 12-Gate Governed Execution Model

ForgeOS separates authorization from execution lifecycle governance.

| Gate | Purpose |
|---|---|
| 1. Identity | Identify the requesting principal |
| 2. Capability | Determine the requested capability |
| 3. Risk | Evaluate operation risk |
| 4. Policy | Decide allow, ask, or deny |
| 5. Evidence | Record the operation and context |
| 6. Verdict | Record the authorization decision |
| 7. Human Approval | Approve consequential requests when required |
| 8. Release | Release the exact approved operation |
| 9. Preflight | Validate execution prerequisites |
| 10. Execute | Run through the governed worker |
| 11. Verify | Check the execution result |
| 12. Rollback | Recover when required |

## Real AI agent trial

The repository now contains a reproducible low-risk trial harness:

```bash
python examples/real_agent_trial.py
```

It demonstrates:

- workspace write → **ALLOW**
- assigned feature branch → **ALLOW**
- `main` branch escape → **DENY**
- unrelated repository → **DENY**
- sensitive access → **ASK**
- human approval → governed execution
- append-only evidence verification

The trial uses a disposable local workspace and simulated Git/secrets adapters. **It does not use production credentials or claim production readiness.**

Next step: put a real coding agent in front of this control plane using a disposable repository and measure task completion, denied actions, approval friction, scope-escape attempts, latency, and evidence completeness.

Read: [Real AI agent quickstart](docs/REAL_AGENT_QUICKSTART.md)

## Security evidence

The current hardened development track has been exercised with:

- **115 passed, 7 skipped** in the Python regression suite
- **7 passed** in the opt-in Docker isolation suite
- scoped multi-agent tests showing feature-branch allow, main-branch denial, and repository escape denial
- focused execution-boundary regression tests covering direct executor bypass and scoped approval routing

See [Evidence and current status](docs/EVIDENCE.md).

These are prototype test results, not a security certification or claim of production readiness.

## Provider-neutral by design

ForgeOS does not aim to replace provider-native authorization. GitHub, cloud IAM, OAuth, MCP, and provider credentials remain important controls.

ForgeOS adds a common runtime authority layer that can evaluate task context, scope, risk, approval, and evidence across different agents and tools.

## Quick start

```bash
git clone https://github.com/kahaos/ForgeOS.git
cd ForgeOS
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip pytest
pytest -q
```

Run the scoped multi-agent demo:

```bash
python examples/scoped_multi_agent_demo.py
```

Run the real-agent trial:

```bash
python examples/real_agent_trial.py
```

Run the Docker isolation demo when Docker is intentionally available:

```bash
python examples/isolated_worker_demo.py
```

## Architecture

The core separation is:

```text
Agent
  ↓
ForgeOS Control Plane
  ↓
Runtime Gateway
  ↓
Bound Execution Authorization
  ↓
Execution Worker
  ↓
Provider / Executor
  ↓
Evidence
```

See [ForgeOS architecture](docs/FORGEOS_ARCHITECTURE.md) for the detailed model.

## Current limitations

ForgeOS is a developing open-source prototype. Production use requires additional work, including:

- authenticated human and agent principals
- durable transactional state
- production provider credential binding
- secret isolation
- network egress controls
- production Git/GitHub and cloud adapters
- deployment controls and operational monitoring

The current API uses a server-bound operator principal rather than a complete enterprise identity provider integration.

## Roadmap

See [the ForgeOS roadmap](docs/ROADMAP.md).

## Repository guide

- `controlplane/` — authorization, policy, evidence, gateway, and execution primitives
- `tests/` — regression and adversarial tests
- `examples/` — safe demonstrations and the real-agent trial harness
- `docs/` — product, security, architecture, quickstarts, evidence, and roadmap
- `docs/superpowers/` — approved specifications and implementation plans

## Contributing and security

- [Contributing](CONTRIBUTING.md)
- [Security policy](SECURITY.md)
- [Code of Conduct](CODE_OF_CONDUCT.md)

## License

ForgeOS is licensed under the **Apache License 2.0**. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
