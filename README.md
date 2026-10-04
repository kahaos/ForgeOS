# ForgeOS — AI Agent Control Plane

**Let AI agents act autonomously without giving them unrestricted authority.**

ForgeOS is an open-source **AI agent control plane** for authorization, human approval, governed execution, and evidence. It sits between autonomous AI agents and the tools, systems, data, accounts, and real-world actions they are allowed to touch.

> **Agent autonomy should not mean unrestricted authority.**

[Why ForgeOS?](docs/WHY_FORGEOS.md) · [Try the real-agent trial](docs/REAL_AGENT_QUICKSTART.md) · [Read the security model](docs/SECURITY_MODEL.md) · [Explore the architecture](docs/FORGEOS_ARCHITECTURE.md) · [Read the Gemini milestone](docs/MILESTONE_REAL_GEMINI_MCP.md) · [See the roadmap](docs/ROADMAP.md)

## 🚀 Real Gemini MCP milestone — SUCCESS

On **2026-10-04**, ForgeOS successfully executed a real external **Gemini 3.7 Flash** agent action through the ForgeOS MCP boundary.

The demonstrated path was:

```text
Gemini 3.7 Flash
      ↓
Gemini MCP client
      ↓
forgeos_write_file
      ↓
ForgeOS MCP bridge
      ↓
RuntimeGateway
      ↓
ALLOW + task-scoped authority
      ↓
signed execution authorization
      ↓
ExecutionWorker
      ↓
filesystem:write
      ↓
bound disposable workspace
      ↓
site/index.html
      ↓
evidence ledger
```

The agent was `website-agent`, operating under task `real-agent-website-build` with `FS_WRITE` authority. It created the requested `site/index.html` with exactly 55 bytes. The resulting file hash, request digest, execution binding, and evidence digest were recorded in the committed evidence record.

**159 tests passed** in the full ForgeOS regression suite after the implementation work.

Read the full technical report: [Real Gemini MCP milestone](docs/MILESTONE_REAL_GEMINI_MCP.md)  
Read the committed run record: [Gemini write evidence](evidence/gemini-write-success/2026-10-04-live-run.txt)  
See the project history: [CHANGELOG](CHANGELOG.md)

> This is a controlled, low-risk disposable trial. It is evidence of a working governed execution path, not a claim of production readiness or security certification.

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

The repository contains a reproducible low-risk real-agent trial harness:

```bash
python examples/run_gemini_forgeos_trial.py --prepare-only
```

The current MCP bridge exposes seven deliberately narrow tools:

- `read_file`
- `forgeos_write_file`
- `run_test`
- `git_status`
- `git_commit`
- `git_push`
- `request_action`

The demonstrated Gemini milestone proves the write path. Additional real-agent proofs for test execution, Git commit/push, and human approval are the next validation targets.

The trial uses a disposable local workspace and controlled local adapters. **It does not use production credentials or claim production readiness.**

Read: [Real-Agent MCP boundary](docs/REAL_AGENT_MCP.md) · [Real Gemini MCP milestone](docs/MILESTONE_REAL_GEMINI_MCP.md)

## Security evidence

The current development track has been exercised with:

- **159 passed** in the full Python regression suite following the real Gemini MCP implementation work
- scoped multi-agent tests showing feature-branch allow, main-branch denial, and repository escape denial
- focused execution-boundary tests covering executor binding and scoped approval routing
- a real external Gemini execution that crossed the MCP boundary and completed a governed filesystem write
- committed evidence containing authorization, execution, request digest, execution binding, result, and evidence-chain digest

See [Evidence and current status](docs/EVIDENCE.md) and [Real Gemini MCP milestone](docs/MILESTONE_REAL_GEMINI_MCP.md).

These are prototype test and trial results, not a security certification or claim of production readiness.

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

Prepare the real Gemini MCP trial:

```bash
python examples/run_gemini_forgeos_trial.py --prepare-only
```

Run the original control-plane trial:

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
- `docs/` — product, security, architecture, quickstarts, evidence, milestones, and roadmap
- `evidence/` — selected committed proof records from validated milestones
- `docs/superpowers/` — approved specifications and implementation plans

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for milestone history and [the real Gemini milestone](docs/MILESTONE_REAL_GEMINI_MCP.md) for the current detailed validation record.

## Contributing and security

- [Contributing](CONTRIBUTING.md)
- [Security policy](SECURITY.md)
- [Code of Conduct](CODE_OF_CONDUCT.md)

## License

ForgeOS is licensed under the **Apache License 2.0**. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
