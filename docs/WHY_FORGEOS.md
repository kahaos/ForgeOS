# Why ForgeOS for AI agents?

ForgeOS is an **AI agent control plane** for teams that want autonomous agents to work without giving those agents unrestricted authority.

As coding agents, research agents, operations agents, and multi-agent systems become more capable, the security problem is not only whether an agent can authenticate. The harder question is whether the agent is authorized to perform **this exact action, against this exact resource, for this exact task, at this moment**.

## The problem

Traditional credentials answer questions such as “who is this?” and “what can this account access?”. Autonomous agents also need runtime controls for:

- task-scoped permissions
- least-privilege capabilities
- resource and branch scope
- delegation between agents
- human approval for consequential actions
- short-lived execution authorization
- tamper-evident evidence
- replay and scope-escape protection

ForgeOS is designed to provide that cross-tool control layer without replacing provider-native authentication.

## What ForgeOS controls

```text
AI agent
   ↓
Identity → Capability → Task → Scope → Risk → Policy
   ↓
Allow / Ask / Deny
   ↓
Evidence + approval
   ↓
Bound execution authorization
   ↓
Governed executor
```

An agent can therefore be autonomous inside a defined boundary while sensitive authority remains controlled by ForgeOS.

## What ForgeOS does not claim

The current repository is a security-focused prototype. Some executors are simulated and production identity/provider integrations are future work. The project does not claim that a prototype test makes an arbitrary autonomous agent production-safe.

## Who should look at ForgeOS?

ForgeOS is intended for developers, security engineers, platform teams, AI infrastructure builders, and researchers working on AI agent authorization, agent identity, multi-agent systems, runtime governance, or secure autonomous execution.

## Next

- [AI agent authorization](AI_AGENT_AUTHORIZATION.md)
- [Multi-agent security](MULTI_AGENT_SECURITY.md)
- [Security model](SECURITY_MODEL.md)
- [Real agent quickstart](REAL_AGENT_QUICKSTART.md)
- [Evidence and current status](EVIDENCE.md)
