# ForgeOS

> **The runtime authority layer for autonomous AI agents.**
>
> **Agent autonomy should not mean unrestricted authority.**

ForgeOS is an open-source control plane that sits between AI agents and the systems they can affect. It evaluates **identity, capability, task scope, risk, policy, human approval, execution, and evidence** before consequential actions are allowed to run.

**The model is not the authority. ForgeOS is.**

[Why ForgeOS](docs/WHY_FORGEOS.md) · [Project Guide](docs/PROJECT_GUIDE.md) · [Architecture](docs/FORGEOS_ARCHITECTURE.md) · [Security](docs/SECURITY_MODEL.md) · [Roadmap](docs/ROADMAP.md)

---

## Why ForgeOS?

AI agents can now write code, modify files, call APIs, operate infrastructure, and coordinate with other agents. Authentication tells you **who** an agent is. Credentials tell you **what access** it has.

ForgeOS is designed to answer the runtime question:

> **Is this agent allowed to perform this exact action, against this exact resource, for this exact task, right now?**

Instead of giving an agent broad standing authority, ForgeOS can issue narrow, task-scoped authority and route every governed request through an explicit decision:

```text
                     AI AGENT
                         │
                         ▼
              ┌─────────────────────┐
              │       ForgeOS       │
              │                     │
              │ Identity            │
              │ Capability          │
              │ Task + Scope        │
              │ Risk                │
              │ Policy              │
              └──────────┬──────────┘
                         │
                  ALLOW / ASK / DENY
                         │
              ┌──────────┴──────────┐
              │                     │
       Human approval          Evidence
              │                     │
              └──────────┬──────────┘
                         ▼
              Governed Execution
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
      GitHub           Cloud           Systems
```

ForgeOS is **not another AI agent** and does not replace provider-native authorization, GitHub permissions, cloud IAM, OAuth, MCP security, or application credentials. It provides a common runtime authority boundary across them.

---

## 🚀 Verified: real Gemini agent execution

**2026-10-04 — real Gemini 3.7 Flash successfully crossed the ForgeOS MCP boundary and completed a governed filesystem write.**

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

The agent `website-agent` operated under task `real-agent-website-build` with `FS_WRITE` authority and created `site/index.html` with exactly **55 bytes**. The file hash, request digest, execution binding, and evidence digest were recorded in the committed evidence record.

**159 tests passed** in the full ForgeOS regression suite after the implementation work.

**Important:** this is a controlled, low-risk disposable trial. It is evidence of a working governed execution path, **not** a claim of production readiness or security certification.

→ [Read the full Gemini milestone](docs/MILESTONE_REAL_GEMINI_MCP.md)  
→ [Inspect the committed evidence](evidence/gemini-write-success/2026-10-04-live-run.txt)  
→ [See the engineering changelog](CHANGELOG.md)

---

## The ForgeOS security model

A ForgeOS authority grant can be narrower than a conventional credential:

```text
Agent:       website-agent
Task:        website-build
Capability:  GIT_PUSH
Repository:  company/site
Branch:      feature/*
Expiry:      task expiry
```

The agent can autonomously work inside that boundary while a different repository, production branch, capability, or expired task falls outside its authority.

### ALLOW / ASK / DENY

| Decision | Meaning |
|---|---|
| **ALLOW** | The exact request matches active authority and policy and may enter governed execution. |
| **ASK** | The operation may be permitted, but an authorized human decision is required first. |
| **DENY** | No applicable authority exists or policy prohibits the operation. The request must not reach an executor. |

### 12-gate governed execution

1. **Identity** — identify the requesting principal
2. **Capability** — determine what operation is requested
3. **Risk** — evaluate operation risk
4. **Policy** — decide ALLOW, ASK, or DENY
5. **Evidence** — record request and context
6. **Verdict** — record authorization decision
7. **Human Approval** — approve consequential requests when required
8. **Release** — release the exact approved operation
9. **Preflight** — validate execution prerequisites
10. **Execute** — run through the governed worker
11. **Verify** — check the result
12. **Rollback** — recover when required

See [the security model](docs/SECURITY_MODEL.md) and [AI agent authorization](docs/AI_AGENT_AUTHORIZATION.md).

---

## Multi-agent authority

ForgeOS treats agents as separate principals even when they cooperate:

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

→ [Multi-agent security](docs/MULTI_AGENT_SECURITY.md)

---

## Provider-neutral by design

ForgeOS is being designed so the underlying model/provider can change without changing the authority model.

| Agent/provider | Current status |
|---|---|
| **Gemini** | ✅ Real MCP execution verified |
| **Anthropic / Claude** | 🟡 Planned |
| **OpenAI / ChatGPT** | 🟡 Planned |
| **xAI / Grok** | 🟡 Planned |
| **OpenAI-compatible / local models** | 🟡 Planned |

The target architecture is:

```text
Gemini ───────┐
Claude ───────┤
OpenAI ───────┤
Grok ─────────┤──→ Common ForgeOS runtime interface
Local models ─┘                 │
                                ▼
                        ForgeOS Authority
                                │
                ┌───────────────┼───────────────┐
                ▼               ▼               ▼
             GitHub           Cloud          Systems
```

Provider adapters should remain thin. ForgeOS owns task context, scope, policy, approval, execution authority, and evidence.

→ [Provider roadmap](docs/ROADMAP.md)

---

## Application integrations

The next major validation target is **GitHub**, because coding agents need to perform exactly the kinds of operations where runtime authority matters.

| Integration | Status | Planned governed actions |
|---|---|---|
| Filesystem | ✅ Verified | Read/write through governed worker |
| MCP boundary | ✅ Verified | Tool requests through ForgeOS |
| GitHub | 🟡 Next | Repos, branches, commits, PRs, push, CI, merge, release |
| Cloud | 🟡 Planned | Infrastructure and deployment actions |
| Secrets | 🟡 Planned | Scoped secret access |
| Slack / Teams | 🟡 Planned | Governed communication/actions |
| CI/CD | 🟡 Planned | Build, release and deployment gates |

High-impact operations should be able to trigger **ALLOW / ASK / DENY** and exact human approval while producing evidence of the decision and result.

→ [See the full roadmap](docs/ROADMAP.md)

---

## Task Ledger & human-readable reports

A major product direction is to make machine activity understandable to humans.

Every meaningful governed task should eventually receive a persistent ForgeOS task ID such as:

```text
FOS-2026-10-04-8A42C1
```

A task record will connect the request, agent/provider, actions, policy decisions, approvals, tools, files, Git commits, tests, errors, results, and evidence.

A non-technical user should be able to receive a report like:

```text
ForgeOS Task: FOS-2026-10-04-8A42C1
Agent:         Gemini
Task:          Build business website
Started:       18:42
Completed:     19:07
Duration:      25 minutes
Status:        COMPLETED

Changes:
  20 files changed
  4 commits

Verification:
  Tests: PASSED
  Pull request: CREATED

Evidence:
  Approvals: 2 requested / 2 approved
  Git SHA: a81f3c7...
```

The **Task Ledger** remains the source of truth; email, dashboard, Slack, webhooks and other notification channels can become delivery layers over it.

→ [Task Reports & Notifications roadmap](docs/ROADMAP.md)

---

## What is actually verified today?

The current development track has evidence for:

- task-scoped capability grants
- resource and branch scoping
- multi-agent authority separation
- attenuating delegation
- ALLOW / ASK / DENY decisions
- exact-request human approval
- signed execution authorizations
- single-use execution nonces
- replay/tamper/state-drift protections
- Docker-backed isolated worker tests
- provider-neutral Runtime Gateway
- a real external Gemini MCP execution through the governed ForgeOS boundary
- committed authorization, execution and evidence records
- **159 passing tests** after the Gemini milestone

These are prototype validation results, not a security certification.

→ [Evidence and current status](docs/EVIDENCE.md)  
→ [Real-agent MCP boundary](docs/REAL_AGENT_MCP.md)

---

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

For a guided tour, start with [Project Guide](docs/PROJECT_GUIDE.md).

---

## Repository map

```text
ForgeOS/
├── controlplane/   Core authorization, policy, evidence, gateway and execution primitives
├── examples/       Safe demos and real-agent trial harnesses
├── tests/          Regression and adversarial tests
├── docs/           Architecture, security, guides, milestones and roadmap
├── evidence/       Selected committed proof records
├── .github/        CI and community issue templates
└── README.md       Project entry point
```

The repository also contains historical patch plans and earlier engineering artifacts. They are intentionally preserved while the project evolves; this presentation pass does not remove historical material.

---

## Current limitations

ForgeOS is a developing open-source prototype. Production use requires additional work, including:

- authenticated human and agent principals
- durable transactional state
- production provider credential binding
- secret isolation
- network egress controls
- production Git/GitHub and cloud adapters
- deployment controls and operational monitoring

The current API uses a server-bound operator principal rather than a complete enterprise identity-provider integration.

**Do not treat the current trial as a production deployment or security certification.**

---

## Roadmap

### Foundation — current

- [x] Scoped authority
- [x] Policy and ALLOW / ASK / DENY
- [x] Human approval path
- [x] Governed execution worker
- [x] Evidence ledger
- [x] Real Gemini MCP execution

### Next

- [ ] Claude / Anthropic adapter
- [ ] OpenAI adapter
- [ ] Grok adapter
- [ ] GitHub governed integration
- [ ] Task Ledger
- [ ] Human-readable task reports
- [ ] Completion / approval / denial notifications

### Platform

- [ ] Cloud integrations
- [ ] Secret isolation and controlled access
- [ ] CI/CD and deployment gates
- [ ] Slack / Teams / Jira / Notion integrations
- [ ] Live control console
- [ ] Evidence search and audit workflows
- [ ] Multi-agent orchestration
- [ ] Policy administration and protected policy changes

→ [Full roadmap](docs/ROADMAP.md)

---

## For contributors

ForgeOS welcomes people interested in:

- AI agent security
- agent authorization and identity
- least privilege
- MCP security
- policy engines
- secure autonomous execution
- AI governance
- provider adapters
- enterprise integrations

See [CONTRIBUTING.md](CONTRIBUTING.md) and the [Project Guide](docs/PROJECT_GUIDE.md).

For security issues, see [SECURITY.md](SECURITY.md).

---

## License

ForgeOS is licensed under the **Apache License 2.0**. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
