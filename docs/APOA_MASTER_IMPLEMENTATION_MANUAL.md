# Apoa — Auth0 / Open Policy Agent for AI Tool Execution

## Master Implementation Manual

**Status:** Core v1 implementation branch  
**Repository lineage:** ForgeOS → Apoa  
**Principle:** AI agents request. Apoa authorizes. Tools execute.

---

## 1. Purpose

Apoa is an AI-agnostic execution authorization engine that sits between an AI agent and the tools, APIs, systems, and data that agent can affect.

> **The AI model is not the authority. Apoa is the authority.**

Apoa is not intended to replace an AI model, MCP, LangChain, CrewAI, AutoGen, IAM, or an existing agent framework. It is an authorization and policy enforcement layer that can be integrated beneath them.

The positioning reference is **“Auth0 / Open Policy Agent for AI Tool Execution.”** Apoa is independent and is not affiliated with Auth0 or Open Policy Agent.

---

## 2. Product Definition

### One sentence

> Apoa is an AI-agnostic policy authorization engine that controls what AI agents are allowed to do before their tools execute.

### Product rule

**AI agents request. Apoa authorizes. Tools execute.**

### Core decisions

- `ALLOW`
- `DENY`
- `REQUIRE_APPROVAL`

No consequential tool execution should occur without a valid authorization decision.

---

## 3. Why Apoa Exists

ForgeOS demonstrated that a governed execution path can intercept real AI tool activity, enforce capabilities and scope, require human approval, issue constrained authorization, prevent replay, and produce evidence.

The next step is not to make ForgeOS larger. It is to extract the smallest reusable security primitive and make it independently integrable.

ForgeOS therefore remains the prototype/reference lineage while Apoa becomes the focused product direction.

Do not delete or overwrite the existing ForgeOS history during this transition.

---

## 4. Architecture

```text
                    AI AGENT
                       |
             tool/action request
                       |
                       v
             +-------------------+
             |       APOA        |
             |                   |
             | Identity          |
             | Capability        |
             | Scope             |
             | Policy            |
             | Parameters        |
             | Risk              |
             | Approval          |
             | Authorization     |
             | Evidence          |
             +---------+---------+
                       |
                ALLOW / DENY /
              REQUIRE_APPROVAL
                       |
                       v
              +----------------+
              | Tool / API / OS |
              +----------------+
                       |
                       v
                  REAL WORLD
```

The security boundary is only useful if the agent cannot bypass it and directly acquire the authority Apoa is supposed to enforce.

---

## 5. Canonical Execution Request

Every adapter must translate provider-specific requests into one canonical request model.

Conceptually:

```json
{
  "request_id": "req_123",
  "principal": {
    "type": "agent",
    "id": "support-agent"
  },
  "action": {
    "type": "refund_customer"
  },
  "target": {
    "system": "payments",
    "resource": "customer_123"
  },
  "parameters": {
    "amount": 250
  },
  "task": {
    "id": "task_456"
  },
  "context": {
    "environment": "production"
  }
}
```

The Core must not depend on Gemini, Claude, OpenAI, MCP, or any other provider-specific representation.

---

## 6. Core Authorization Flow

```text
REQUEST
  ↓
AUTHENTICATE
  ↓
IDENTIFY
  ↓
CAPABILITY CHECK
  ↓
RESOURCE/SCOPE CHECK
  ↓
PARAMETER POLICY
  ↓
RISK POLICY
  ↓
APPROVAL POLICY
  ↓
EXECUTION AUTHORIZATION
  ↓
EXECUTE
  ↓
EVIDENCE
```

The exact implementation order may evolve, but the security invariant must remain:

> **No tool execution may occur unless Apoa has produced a valid authorization for that exact execution.**

---

## 7. Initial Gates

### Gate 1 — Identity

Determine who is requesting the action. Unknown or invalid principals are denied.

### Gate 2 — Capability

Determine whether the principal possesses the capability required by the action.

Examples:

- `FS_READ`
- `FS_WRITE`
- `GIT_READ`
- `GIT_COMMIT`
- `GIT_PUSH`
- `DATABASE_READ`
- `DATABASE_WRITE`
- `SECRET_READ`
- `NETWORK_REQUEST`
- `PAYMENT`

### Gate 3 — Resource / Scope

Verify that the requested target falls within the principal's authorized resource, environment, branch, path, tenant, or task scope.

### Gate 4 — Parameter Policy

Evaluate exact request parameters against policy limits.

Examples:

- maximum payment
- maximum refund
- maximum records affected
- allowed branches
- allowed filesystem paths
- allowed API operations

### Gate 5 — Risk

Classify the requested action and apply policy-specific risk controls.

### Gate 6 — Human Approval

Require explicit human authorization for consequential actions where policy requires it.

### Gate 7 — Authorization Integrity

Bind approval/authorization to the exact request, principal, target, action, relevant parameters, and policy version.

### Gate 8 — Replay Protection

Use short-lived, unique execution authorization and prevent unauthorized reuse.

### Gate 9 — State / Policy Consistency

Prevent execution using stale authorization when relevant policy or authorization state has changed.

### Gate 10 — Evidence

Record the request, decision, approval, authorization and execution outcome.

The original ForgeOS “12 gates” should be treated as the source of proven security ideas, not as a requirement that Apoa expose exactly twelve gates forever.

---

## 8. Policy Model

Policies must be external to the AI model.

Conceptual policy:

```yaml
agent:
  name: customer-support-agent

permissions:
  - CUSTOMER_READ
  - EMAIL_SEND

restrictions:
  database_write: false
  secret_access: false

limits:
  email_per_hour: 100
  refund_without_approval: 100

approval_required:
  refunds_above: 100
  production_changes: true
```

The AI must not be able to modify its own policy without passing through a separately protected policy-management authorization path.

---

## 9. Enterprise AI Execution Contracts

Apoa should eventually allow an organization to define an explicit contract for each AI agent.

The contract describes:

- identity
- capabilities
- allowed resources
- denied resources
- parameter limits
- environments
- approval requirements
- expiry
- evidence requirements

This is intended to make an AI's authority understandable to both developers and non-technical governance/security users.

---

## 10. Authorization Response

Conceptual response:

```json
{
  "decision": "REQUIRE_APPROVAL",
  "reason": "Refund exceeds autonomous execution limit",
  "policy": "customer-support-agent-v1",
  "request_id": "req_123",
  "authorization_id": "auth_456",
  "approval_required": true
}
```

The response must be structured and machine-readable. Human-readable explanations are supplementary and must never replace the authoritative decision.

---

## 11. Execution Authorization

An `ALLOW` decision should eventually produce a short-lived execution authorization containing enough information to bind execution to the decision.

Conceptual fields:

```text
authorization_id
request_id
principal
agent
action
target
policy_version
issued_at
expires_at
nonce
```

Downstream execution components validate this authorization before running the tool.

---

## 12. Human Approval

Approval is an authorization event, not merely a UI button.

An approval should identify:

- approver
- request
- action
- target
- relevant parameters
- policy version
- timestamp
- approval state

Approval must not silently expand the scope of the original request.

---

## 13. Evidence Ledger

Every consequential action should produce an auditable evidence trail.

Example lifecycle:

```text
REQUESTED
    ↓
EVALUATED
    ↓
APPROVAL_REQUIRED
    ↓
HUMAN_APPROVED
    ↓
AUTHORIZED
    ↓
EXECUTED
    ↓
VERIFIED
```

Or:

```text
REQUESTED
    ↓
EVALUATED
    ↓
DENIED
```

Evidence should include, as appropriate:

- request ID
- timestamp
- principal
- agent
- action
- target
- parameters or safe parameter representation
- policy
- policy version
- decision
- reason
- approval event
- authorization ID
- execution result

Sensitive data must not be unnecessarily copied into evidence records.

---

## 14. AI Provider Agnosticism

The Core must remain provider-neutral.

```text
Gemini Adapter ──┐
Claude Adapter ──┤
OpenAI Adapter ──┤
MCP Adapter ─────┤──→ APOA CORE
Custom Adapter ──┘
```

Adapters translate provider-specific tool calls into the canonical execution request.

The authorization result must not depend on which model generated the request unless policy explicitly includes provider/model identity as a condition.

---

## 15. MCP Integration

MCP is an integration mechanism, not the security model.

```text
AI
 ↓
MCP
 ↓
Apoa Adapter
 ↓
Apoa Core
 ↓
Decision
 ↓
Tool
```

The existing ForgeOS MCP work should be used as the first reference integration.

---

## 16. Developer API

The intended developer experience should be small.

Conceptually:

```python
from apoa import authorize

decision = authorize(
    agent="my-agent",
    action="git_push",
    target="production"
)

if decision.allowed:
    execute()
elif decision.requires_approval:
    request_approval()
else:
    deny()
```

The exact API should be finalized against the existing ForgeOS implementation before productionizing the SDK.

---

## 17. CLI Direction

Planned commands include:

```bash
apoa check
apoa authorize
apoa policy validate
apoa policy test
apoa approval list
apoa evidence show
```

The CLI is for inspectability and developer experience. It is not a replacement for the enforcement boundary.

---

## 18. Target Repository Architecture

```text
apoa/
├── src/
│   └── apoa/
│       ├── core/
│       │   ├── authorization.py
│       │   ├── decisions.py
│       │   ├── requests.py
│       │   ├── policy.py
│       │   ├── capabilities.py
│       │   ├── approvals.py
│       │   ├── evidence.py
│       │   └── execution.py
│       ├── adapters/
│       │   ├── mcp/
│       │   ├── gemini/
│       │   ├── openai/
│       │   └── anthropic/
│       ├── policy/
│       │   ├── parser.py
│       │   └── evaluator.py
│       └── cli/
├── tests/
│   ├── core/
│   ├── policy/
│   ├── approvals/
│   ├── evidence/
│   └── adapters/
├── examples/
├── docs/
├── pyproject.toml
├── README.md
├── SECURITY.md
├── LICENSE
└── CHANGELOG.md
```

This is a target structure. Do not create unnecessary modules merely to match the diagram.

---

## 19. Migration Strategy From ForgeOS

Do not perform a destructive rewrite.

Use this progression:

```text
FORGEOS
  ↓
Identify proven authorization/security primitives
  ↓
Define Apoa canonical interfaces
  ↓
Extract/refactor reusable logic
  ↓
Add independent Core tests
  ↓
Connect existing MCP/Gemini paths
  ↓
Verify behavioural parity
  ↓
Add new provider-neutral integrations
```

Potentially reusable components include:

- authorization primitives
- capabilities
- policy evaluation
- approval machinery
- signed authorization
- nonce/replay protection
- evidence records
- scope enforcement
- MCP integration concepts
- security regression tests

Do not migrate unrelated orchestration or UI merely because it already exists.

---

## 20. Testing Strategy

Every Core capability requires positive and negative tests.

Examples:

```text
legitimate request          → ALLOW
unauthorized request        → DENY
dangerous but approvable    → REQUIRE_APPROVAL
```

Security tests must cover:

### Identity

- unknown agent
- forged identity
- missing identity
- identity mismatch

### Capabilities

- undeclared capability
- escalation
- delegation escalation

### Scope

- path traversal
- resource substitution
- environment substitution
- branch substitution

### Parameters

- excessive amount
- excessive records
- dangerous command parameters
- malformed parameters

### Approval

- wrong approver
- expired approval
- approval for another request
- approval reuse
- parameter modification after approval

### Replay

- reused nonce
- expired authorization
- duplicate execution

### Policy

- unauthorized policy modification
- stale policy
- policy bypass
- conflicting policies

---

## 21. First Demonstration

Give an AI agent access to Git.

Policy:

```text
read repository     → ALLOW
create branch       → ALLOW
commit              → ALLOW
push                → REQUIRE_APPROVAL
force push          → DENY
delete repository   → DENY
```

The demonstration should visibly show that the model can request actions but cannot decide its own authority.

This should be the first major Apoa product demonstration.

---

## 22. Second Demonstration

Financial tool example:

```text
read balance        → ALLOW
£20 payment         → ALLOW
£500 payment        → REQUIRE_APPROVAL
£5,000 payment      → DENY
secret API key      → DENY
```

This demonstrates that Apoa is an execution authorization engine rather than a Git-specific security layer.

---

## 23. Third Demonstration

Production infrastructure:

```text
read logs           → ALLOW
restart staging     → ALLOW
restart production  → REQUIRE_APPROVAL
delete production DB → DENY
modify policy       → REQUIRE_APPROVAL
```

This demonstrates enterprise applicability.

---

## 24. Development Sequence

Implementation order:

1. Repository and documentation
2. Canonical request model
3. Decision model
4. Policy engine
5. Capability enforcement
6. Scope enforcement
7. Parameter enforcement
8. Approval system
9. Execution authorization
10. Replay/state protection
11. Evidence
12. Python SDK
13. CLI
14. MCP adapter
15. Gemini integration
16. Security regression suite
17. Developer quickstart
18. External developer validation

Do not build the complete platform before validating the Core.

---

## 25. Explicitly Out of Scope for Core v1

Do not make these prerequisites for Core v1:

- large dashboard
- multi-agent orchestration
- ten provider integrations
- billing
- marketplace
- enterprise SSO
- cloud deployment automation
- broad workflow engine
- replacement agent runtime

These can become future layers after the Core has evidence of demand.

---

## 26. Success Criteria

Apoa Core v1 is successful when an external developer can understand:

1. What Apoa is.
2. Why it is useful.
3. Where it sits in their architecture.
4. How to integrate it.
5. How to write a policy.
6. How decisions work.
7. How approvals work.
8. How evidence is produced.

The Core should be useful without adopting the rest of the platform.

---

## 27. Definition of Done

- [ ] Provider-independent canonical request model
- [ ] ALLOW implemented
- [ ] DENY implemented
- [ ] REQUIRE_APPROVAL implemented
- [ ] Identity model implemented
- [ ] Capability model implemented
- [ ] Resource/scope enforcement implemented
- [ ] Parameter limits implemented
- [ ] Approval bound to exact request
- [ ] Authorization expiry implemented
- [ ] Replay protection implemented
- [ ] Policy version recorded
- [ ] Evidence generated
- [ ] Python integration implemented
- [ ] CLI implemented
- [ ] MCP integration demonstrated
- [ ] Gemini integration demonstrated
- [ ] Security invariants covered by automated tests
- [ ] Migration/reference documentation completed

---

## 28. Product Positioning

Primary:

> **Auth0 / Open Policy Agent for AI Tool Execution.**

Expanded:

> Apoa gives organizations a deterministic authorization layer between AI agents and the tools they can control.

Core message:

> **Agents can be autonomous without being unrestricted.**

Differentiator:

> **The model is not the authority.**

---

## 29. Long-Term Architecture

```text
                  ANY AI AGENT
                       │
          ┌────────────┼────────────┐
          │            │            │
        Gemini       Claude       OpenAI
          │            │            │
          └────────────┼────────────┘
                       │
                       ▼
              +----------------+
              |      APOA      |
              |                |
              | Identity       |
              | Policy         |
              | Capability     |
              | Scope          |
              | Risk           |
              | Approval       |
              | Authorization  |
              | Evidence       |
              +-------+--------+
                      │
              ALLOW / DENY / ASK
                      │
          ┌───────────┼───────────┐
          ▼           ▼           ▼
       GitHub       Cloud       Database
                      │
                      ▼
                 REAL WORLD
```

The model can be autonomous.

The model does not become the authority.

**That is Apoa.**
