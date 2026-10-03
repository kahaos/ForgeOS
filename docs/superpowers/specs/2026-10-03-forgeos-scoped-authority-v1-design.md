# ForgeOS Scoped Authority v1

## Status

Design approved in conversation; implementation branch: `scoped-authority-v1`.

## Goal

Extend ForgeOS from flat agent capabilities into a runtime authority layer where every consequential agent action is evaluated against the agent, task, capability, resource scope, policy context, delegation chain, and expiry, while preserving the existing governed execution and isolated-worker security model.

## Product principle

ForgeOS is not a replacement for GitHub, AWS, Entra, OAuth, MCP, or provider-native permissions. It is the runtime authority and evidence layer above those systems. Existing provider controls remain defense in depth; ForgeOS determines whether an agent may request an operation and binds approved authority to a specific execution.

## Core authority model

```text
Agent
  -> Task
  -> Capability Grant
  -> Resource Scope
  -> Risk / Policy
  -> Approval when required
  -> Short-lived signed Authorization
  -> Provider / Executor
  -> Evidence
```

The authoritative primitive is a task-scoped, time-bounded capability grant. Convenience profiles may be added later but must expand to explicit grants and never bypass policy.

## Backwards compatibility

The existing `Agent`, `ActionRequest`, flat capabilities, policy decisions, approval records, signed `ExecutionAuthorization`, executor binding, replay protection, Docker isolation, and governed execution lifecycle remain supported. Existing callers may continue to submit flat capability requests during migration. New task-scoped requests use the richer authority path.

## Domain model

### Task

A task represents the bounded purpose for which one or more agents receive authority.

Required fields:
- `task_id`
- `owner`
- `purpose`
- `status`
- `created_at`
- `expires_at`

Optional fields include parent task/delegation metadata and human context.

Task status is one of `active`, `completed`, `revoked`, `expired`.

### CapabilityGrant

A grant authorizes one capability within a task and scope.

Required fields:
- `grant_id`
- `task_id`
- `agent_id`
- `capability`
- `scope`
- `issued_by`
- `issued_at`
- `expires_at`
- `policy_version`

A grant may optionally reference `parent_grant_id` when delegated.

### Scope

Scopes are structured, not free-form authorization strings. The first implementation supports:
- tool
- operation/action
- resource
- repository
- branch patterns
- workspace path
- environment
- API host/path

Unknown scope dimensions fail closed. Scope matching must be explicit and deterministic. Wildcards are only supported where a scope type defines safe pattern semantics (for example `feature/*` for a repository branch).

### Delegation

An agent may delegate only authority it currently possesses. Child authority must be the intersection of the parent's effective authority and the requested child grant. Delegation cannot broaden capability, resource scope, environment, or expiry.

Self-granting, parent substitution, scope widening, and capability escalation are denied.

## Policy evaluation

Policy v2 evaluates:

`agent + task + grant + requested action + target + runtime context`

The result remains `allow`, `ask`, or `deny`.

Evaluation order:
1. Validate agent identity/status.
2. Validate task exists, belongs to the request, and is active/unexpired.
3. Resolve effective grants for the agent and task.
4. Match capability.
5. Match every applicable resource scope.
6. Apply hard-deny rules.
7. Apply risk policy.
8. Return allow/ask/deny with a stable reason.

Deny wins. Missing authority denies. High-risk operations can require approval without requiring approval for every low-risk operation.

## Risk model

Default behavior:
- Low-risk, narrowly scoped reads/writes: automatic when authorized.
- Medium-risk changes: automatic when policy permits and scope is exact.
- High-risk external/public changes: human approval.
- Critical production, financial, authority-management, secret access, and policy changes: approval or explicit denial according to policy.

Human approval is an exception for consequential operations, not a general-purpose interaction loop.

## Signed execution authorization

The existing authorization mechanism is extended so its signed payload binds:
- agent identity snapshot
- task snapshot
- effective capability grant snapshot
- scope snapshot
- policy version
- request digest
- executor ID
- target
- issuance/expiry timestamps
- nonce

Any mutation of task, grant, scope, agent authority, policy version, target, executor, or request invalidates the authorization.

Authorization remains single-use and replay protected.

## Runtime gateway

Add a provider-neutral gateway interface through which agents request governed actions. The gateway delegates authorization to the Control Plane and execution to registered executors/adapters.

The gateway must not contain an independent policy engine. There is one source of authorization truth.

Initial adapters:
- existing Docker isolated executor
- generic simulated executor for tests
- GitHub-oriented adapter boundary
- generic HTTP/tool adapter boundary
- MCP-oriented tool gateway boundary

Provider adapters must retain provider-native credentials and controls; ForgeOS must not require provider secrets to be stored in agent processes.

## Multi-agent model

Agents become first-class principals with optional parent/child relationships and task membership. An agent can participate in multiple tasks, but authority is always evaluated in task context.

Example:

```text
Company
  -> Task: Build Website
      -> Website Agent
          -> GitHub: company/website, feature/*
          -> CI: test environment
      -> SEO Agent
          -> Website content
          -> approved web APIs
      -> Deployment Agent
          -> production deployment (approval required)
```

The SEO agent cannot inherit GitHub deployment authority merely because another agent has it.

## Authority graph

Persist enough relationship metadata to answer:
- Who authorized this agent?
- Which task created this authority?
- Which grants are currently effective?
- Which grants were delegated?
- What authority existed when an action occurred?
- Which executor performed it?
- What was the result?

The first implementation may expose a graph-shaped API/data model without requiring a sophisticated visualization frontend.

## Evidence and audit

Every governed action records task, agent, grant/authority identity, policy version, target, executor, decision, approval actor when applicable, execution result, and timestamps. Existing evidence semantics remain intact.

Audit records must not become an authorization bypass. Evidence is downstream of authorization and execution.

## Security requirements

The implementation must preserve existing security properties:
- no unrestricted executor bypass
- signed authorization
- authorization/request binding
- executor binding
- target binding
- agent snapshot validation
- policy-version validation
- persisted replay nonce protection
- concurrency-safe single execution
- Docker root filesystem isolation
- no outbound network by default
- no host environment leakage
- dropped Linux capabilities
- no-new-privileges
- resource limits
- execution timeout

Network access remains disabled by default in v1. Explicit network authority is a later bounded project.

## API direction

Introduce task/grant/agent relationship endpoints alongside existing approval endpoints. Exact endpoint names should follow current `controlplane/api.py` conventions. The API must expose creation, inspection, revocation, and effective-authority evaluation without allowing clients to self-grant authority.

A minimal developer-facing request should conceptually look like:

```json
{
  "task_id": "task-1837",
  "tool": "git",
  "action": "push",
  "target": "company/website",
  "detail": {"branch": "feature/homepage"}
}
```

The server derives effective authority rather than trusting a client-supplied capability grant.

## Required adversarial coverage

Permanent tests must cover:
- authorized scope succeeds
- wrong repository denied
- wrong branch denied
- wrong workspace denied
- expired task denied
- expired grant denied
- wrong task denied
- revoked grant denied
- revoked task denied
- agent substitution denied
- capability escalation denied
- scope widening denied
- child delegation narrowed correctly
- child delegation widening denied
- policy drift invalidates old authorization
- authority mutation invalidates old authorization
- target tampering rejected
- executor substitution rejected
- replay rejected
- concurrent replay executes at most once
- approval required only where policy says so
- existing flat capability compatibility remains intact

## Acceptance criteria

The v1 implementation is accepted only when:

1. The full existing regression suite passes.
2. All new scoped-authority tests pass.
3. The end-to-end governed execution test passes using task-scoped authority.
4. A scoped agent can autonomously complete an allowed action without unnecessary human approval.
5. The same agent is denied when it leaves its resource scope.
6. A high-risk scoped action reaches the existing human-approval path.
7. A delegated agent cannot exceed the delegator's authority.
8. Signed authorization binds the effective authority snapshot.
9. Existing Docker isolation guarantees remain verified.
10. Documentation demonstrates a company connecting multiple agents without replacing provider-native security.

## Explicit non-goals for v1

- Replacing enterprise IAM.
- Replacing provider-native permissions.
- Production deployment control.
- Arbitrary outbound network access.
- Autonomous policy self-modification.
- Secret-management replacement.
- A full enterprise SSO product.
- A large visual graph editor.
- Provider-specific integrations for every SaaS platform.

## Migration strategy

Implement the richer authority model alongside the existing flat model. Existing flat capability registrations remain valid. New task-scoped grants are preferred for new integrations. Once compatibility is demonstrated, documentation should direct new agent integrations toward task-scoped authority.
