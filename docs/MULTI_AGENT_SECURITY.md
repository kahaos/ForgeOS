# Multi-agent security with ForgeOS

A multi-agent system does not need every agent to share one permission set. ForgeOS models agents as separate principals operating inside a shared task-scoped control plane.

## Example

```text
Task: Build Website
├── Website Agent
│   └── GIT_PUSH → company/site / feature/*
├── SEO Agent
│   └── GIT_COMMIT → company/site / feature/*
└── Deployment Agent
    └── PRODUCTION_DEPLOY → production / approval required
```

The agents can cooperate while their authority remains separate.

## Why separate authority matters

A website agent should not automatically gain deployment authority because a deployment agent exists. An SEO agent should not inherit access to another repository merely because both agents participate in the same task.

ForgeOS therefore evaluates the requesting principal, task, capability, scope, risk, and policy together.

## Delegation

Delegation is explicit:

```text
Agent A
  ↓ parent grant
Agent B
  ↓ attenuated child grant
Agent C
```

A child grant cannot widen the parent grant's capability, resource scope, or expiry. Direct self-granting is rejected.

## Isolation is graduated

Not every agent needs the same level of sandboxing. Low-risk read-only work can use lighter controls. Shell execution, secrets, deployment, spending, or other consequential operations require stronger boundaries and can require human approval.

The goal is not to make autonomous agents unusable. The goal is to make authority explicit and proportional to the operation.

## Common escape cases ForgeOS should stop

- pushing to an unassigned repository
- pushing outside an assigned branch pattern
- using another agent's capability
- extending a grant beyond its task expiry
- replaying an already-consumed authorization
- executing after task or grant state has changed
- changing an approved request before execution
- bypassing the Runtime Gateway with a caller-supplied executor

## Current status

The repository contains scoped multi-agent authority and execution-boundary hardening tests. The first real-agent trial is deliberately disposable and uses simulated sensitive adapters. Production multi-agent deployment requires additional identity, persistence, provider, and operational hardening.

Continue with [AI agent authorization](AI_AGENT_AUTHORIZATION.md) and [the real-agent quickstart](REAL_AGENT_QUICKSTART.md).
