# AI agent authorization with task-scoped permissions

ForgeOS uses task-scoped authorization to decide whether an AI agent may perform an operation. The central idea is to grant authority for a defined task rather than treating an agent identity as a blanket permission set.

## Authorization model

```text
Principal
  ↓
Task
  ↓
Capability grant
  ↓
Resource scope
  ↓
Risk + policy
  ↓
ALLOW / ASK / DENY
```

A grant can constrain capability, repository, branch, workspace, environment, API host, or other supported dimensions.

Example:

```text
Agent: website-agent
Task: website-build
Capability: GIT_PUSH
Repository: company/site
Branch: feature/*
Expiry: task expiry
```

A push to `company/site` on `feature/home` can be allowed while a push to `main` or another repository falls outside the grant.

## Delegation and attenuation

Agents can be separate principals inside one task. Delegation uses an explicit parent grant. A delegated grant cannot widen the parent's capability, scope, or expiry.

This provides a way to build multi-agent systems without merging all agents into one authority domain.

## ALLOW, ASK, DENY

**ALLOW** means the request matches active authority and policy and can proceed through the governed execution path.

**ASK** means the request is potentially permitted but requires an authorized human decision before execution.

**DENY** means ForgeOS has no applicable authority or policy prohibits the operation. A denied request must not reach the executor.

## Execution binding

An approved scoped operation is bound to the request, agent snapshot, task/grant state, policy version, executor, expiry, and single-use execution nonce. The Runtime Gateway routes the operation through the Execution Authorizer and Execution Worker.

The purpose is to prevent an agent or caller from changing the target after approval or replaying an authorization for another operation.

## Provider-native authorization still matters

ForgeOS is not intended to replace GitHub, cloud IAM, OAuth, MCP authorization, or provider credentials. Those controls remain important. ForgeOS adds a cross-provider runtime authority layer that can evaluate task context and preserve evidence consistently across tools.

## Prototype status

The current implementation is a prototype. Authentication of the human operator, durable transactional state, production provider adapters, and production identity federation remain roadmap work.

See [the security model](SECURITY_MODEL.md) and [the real-agent quickstart](REAL_AGENT_QUICKSTART.md).
