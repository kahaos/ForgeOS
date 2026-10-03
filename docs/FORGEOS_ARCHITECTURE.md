# ForgeOS Scoped Authority Architecture v1

ForgeOS is a runtime authority and evidence layer for autonomous AI agents. It does not replace GitHub, AWS, Entra, OAuth, MCP, or provider-native permissions. Those controls remain defense in depth; ForgeOS evaluates whether an agent may request an operation and binds permitted execution to a task, scope, policy and evidence trail.

## Runtime model

```text
Human / Company
      |
     Task
      |
  Agent identity
      |
Scoped capability grant
      |
Resource / branch / workspace scope
      |
Policy + risk
      |
  allow / ask / deny
      |
Signed short-lived authorization
      |
Provider / tool adapter
      |
Isolated execution
      |
Evidence
```

## Why task scope exists

An enterprise permission such as “can push to GitHub” is too broad for autonomous agents. ForgeOS can instead express “this agent may push repository `company/site` on `feature/*` while task `website-build` is active.” The same agent can participate in another task with different authority.

NIST's September 2026 summary of public feedback identifies task-scoped and contextual authorization, continuous runtime evaluation, ephemeral access, and scope attenuation in delegation chains as important capabilities for agentic systems. citeturn1search1turn1search6

OWASP's September 2026 Agent Control Standard describes runtime enforcement hooks and portable controls across agent frameworks, which is consistent with ForgeOS's provider-neutral gateway direction. citeturn2search0

## Multi-agent authority

Agents are independent principals. A website task can contain:

```text
Task: Build Website
├── Website Agent
│   └── Git push: company/site / feature/*
├── SEO Agent
│   └── Git commit: company/site / feature/*
└── Deployment Agent
    └── production deployment: approval required
```

An agent does not inherit another agent's authority simply because both belong to the same task. Delegation uses `parent_grant_id` and can only narrow capability, scope and expiry.

## Risk model

Low- and medium-risk scoped operations can execute autonomously when policy permits. Consequential operations such as production deployment, secret access, financial operations and authority-management changes require the existing human-approval path or are hard-denied by policy. A production branch push is also treated as consequential while feature-branch pushes can remain autonomous.

This avoids turning ForgeOS into a confirmation dialog for every tool call. The goal is autonomous work inside explicit boundaries, with human attention reserved for consequential transitions.

## Provider integration

Provider adapters are boundaries, not replacement IAM systems. A GitHub adapter can use GitHub-native OAuth/app credentials; an AWS adapter can use AWS-native role/session mechanisms; an MCP adapter can mediate tool calls. Agents should not receive provider secrets directly when a provider adapter can hold and use them.

The runtime gateway contains no second policy engine. It delegates authorization to the Control Plane and execution to registered adapters.

## Security properties

The existing ForgeOS security boundary remains in force:

- signed execution authorization
- exact request and target binding
- agent snapshot validation
- task/grant/scope snapshot validation for scoped authorizations
- policy-version binding
- persisted single-use nonce protection
- executor binding
- isolated Docker execution
- network disabled by default
- dropped Linux capabilities
- no-new-privileges
- resource limits and timeouts

## Current v1 non-goals

ForgeOS v1 does not replace enterprise IAM, become a universal SSO product, enable arbitrary outbound networking, manage production credentials, self-modify policy, or provide provider integrations for every SaaS platform.
