# ForgeOS

> **The runtime authority layer for autonomous AI agents.**
>
> **Agent autonomy should not mean unrestricted authority.**

ForgeOS is a **proprietary source-available** AI agent control plane that sits between AI agents and the systems they can affect. It evaluates identity, capability, task scope, risk, policy, human approval, execution, and evidence before consequential actions are allowed to run.

**The model is not the authority. ForgeOS is.**

## Status

ForgeOS has a working governed execution path through MCP and a **real AI agent trial** using Gemini. The 2026-10-04 milestone demonstrated a Gemini agent crossing the ForgeOS boundary, receiving task-scoped `FS_WRITE` authority, writing to a disposable workspace, and producing committed evidence. The repository currently records **159 passing tests** after that milestone.

This is prototype validation, not production readiness or a security certification.

→ [Real Gemini MCP milestone](docs/MILESTONE_REAL_GEMINI_MCP.md)  
→ [Evidence](docs/EVIDENCE.md)  
→ [Architecture](docs/FORGEOS_ARCHITECTURE.md)  
→ [Security model](docs/SECURITY_MODEL.md)  
→ [Roadmap](docs/ROADMAP.md)

## AI agent security

ForgeOS treats **AI agent security** as an authorization and execution-boundary problem: an agent should be able to act autonomously inside a defined contract without receiving unrestricted authority over the surrounding environment.

Key controls include agent authorization, task-scoped permissions, least-privilege capabilities, resource and branch scope, multi-agent security boundaries, human approval for consequential actions, short-lived execution authorization, and committed security evidence.

→ [Why ForgeOS](docs/WHY_FORGEOS.md)  
→ [AI agent authorization](docs/AI_AGENT_AUTHORIZATION.md)  
→ [Multi-agent security](docs/MULTI_AGENT_SECURITY.md)  
→ [Real agent quickstart](docs/REAL_AGENT_QUICKSTART.md)  
→ [Security evidence](docs/EVIDENCE.md)  
→ [Security model](docs/SECURITY_MODEL.md)

## Core idea

```text
AI AGENT
   │
   ▼
ForgeOS Authority
   │
   ├── Identity
   ├── Capability
   ├── Task + Scope
   ├── Risk
   ├── Policy
   └── Human Approval
   │
   ├── ALLOW
   ├── ASK
   └── DENY
   │
   ▼
Governed Execution
   │
   ├── GitHub
   ├── Cloud
   └── Systems
   │
   ▼
Evidence / Task Ledger
```

ForgeOS is not another AI agent. It is designed as a provider-neutral authority boundary that can govern agents from Gemini, Claude, OpenAI, Grok, local models, and future providers without making the model itself the source of authority.

## Verified capabilities

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
- real external Gemini MCP execution
- committed authorization, execution and evidence records

## Roadmap

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

## Current limitations

ForgeOS is a developing proprietary source-available prototype. Production use requires additional work including authenticated human and agent principals, durable transactional state, production provider credential binding, secret isolation, network egress controls, production Git/GitHub and cloud adapters, deployment controls, and operational monitoring.

## Quick start

```bash
git clone https://github.com/kahaos/ForgeOS.git
cd ForgeOS
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip pytest
pytest -q
```

## Contributions

ForgeOS is **source-available, not open-source**. See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidance and the [LICENSE](LICENSE) for the rights and restrictions that apply to the repository.

## License

ForgeOS is proprietary source-available software and is **not licensed under an open-source license**. See [LICENSE](LICENSE) for the ForgeOS Source-Available License 1.0.

Commercial licensing and other permissions outside the source-available grant require a separate written agreement with the copyright holder.
