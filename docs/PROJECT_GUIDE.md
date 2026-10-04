# ForgeOS Project Guide

## What is ForgeOS?

ForgeOS is the runtime authority layer for autonomous AI agents. It sits between an agent and the systems the agent can affect, evaluating identity, capability, task scope, risk, policy, human approval, execution, and evidence.

The core idea is simple: **agent autonomy should not mean unrestricted authority.**

## The authority boundary

```text
AI Agent
   ↓
ForgeOS Control Plane
   ↓
ALLOW / ASK / DENY
   ↓
Human approval when required
   ↓
Bound execution authorization
   ↓
Execution worker
   ↓
Tool / application / system
   ↓
Evidence
```

ForgeOS is not another model and does not replace provider-native authorization, application permissions, cloud IAM, OAuth, or MCP security. It provides a common runtime authority layer across them.

## Who is it for?

- AI-agent developers who need useful autonomy without unrestricted access
- Security teams working on agent identity, least privilege, authorization, and governance
- Platform teams building shared agent infrastructure
- Researchers exploring secure autonomous execution and multi-agent systems
- Developers building provider and application integrations

## ALLOW / ASK / DENY

**ALLOW** means the exact request matches active authority and policy and can enter governed execution.

**ASK** means the operation may be permitted but requires an authorized human decision.

**DENY** means no applicable authority exists or policy prohibits the operation; the request must not reach an executor.

## 12-gate model

1. Identity
2. Capability
3. Risk
4. Policy
5. Evidence
6. Verdict
7. Human Approval
8. Release
9. Preflight
10. Execute
11. Verify
12. Rollback

The goal is to keep authorization and execution distinct while making the entire lifecycle observable and auditable.

## Current verified milestone

On 2026-10-04, a real Gemini 3.7 Flash agent crossed the ForgeOS MCP boundary and completed a governed filesystem write in a disposable workspace. The repository records the execution and evidence, and the full regression suite reported 159 passing tests after the implementation work.

Read the [real Gemini milestone](MILESTONE_REAL_GEMINI_MCP.md) and [committed evidence](../evidence/gemini-write-success/2026-10-04-live-run.txt).

This is controlled prototype evidence, not production certification.

## Where ForgeOS is going

The next major direction is a common authority layer across multiple AI providers and applications:

```text
Gemini / Claude / OpenAI / Grok / Local models
                    ↓
          Common ForgeOS runtime
                    ↓
       Authority + policy + approval
                    ↓
       GitHub / Cloud / CI / Systems
```

Priority application work begins with GitHub because coding agents routinely need repository, branch, commit, pull-request, CI, merge, and deployment capabilities.

The roadmap also includes a Task Ledger, human-readable task reports, and notifications so users can understand exactly what an agent did without reading raw execution logs.

See [ROADMAP.md](ROADMAP.md).

## Where to read next

- [Architecture](FORGEOS_ARCHITECTURE.md)
- [Security model](SECURITY_MODEL.md)
- [AI agent authorization](AI_AGENT_AUTHORIZATION.md)
- [Multi-agent security](MULTI_AGENT_SECURITY.md)
- [Real-agent MCP boundary](REAL_AGENT_MCP.md)
- [Evidence and current status](EVIDENCE.md)
- [Roadmap](ROADMAP.md)
- [Contributing](../CONTRIBUTING.md)
- [Security policy](../SECURITY.md)
