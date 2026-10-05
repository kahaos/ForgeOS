# Apoa Security Specification v1

**Status:** Proposed for implementation
**Product:** Apoa — Auth0 / Open Policy Agent for AI Tool Execution
**Branch:** `apoa-core-v1`

## 1. Purpose

Apoa is an AI-agnostic authorization and enforcement layer between AI agents and the tools, APIs, data, and systems they can control.

> **AI agents request. Apoa authorizes. Tools execute.**

The model is not the authority. A protected tool execution must not occur unless Apoa has produced a valid authorization for the exact execution request.

This specification defines the security contract for Apoa Core v1. It is intentionally narrower than the eventual enterprise product. Dashboard, billing, SSO, orchestration, marketplace, and other product surfaces are outside this specification unless they affect the security boundary.

## 2. Security Invariants

The following invariants are normative requirements.

### S1 — No authorization, no protected execution

A protected executor MUST reject execution when no valid Apoa execution authorization is supplied.

### S2 — Authorization is bound to the exact request

An authorization MUST be bound to a canonical fingerprint of the complete security-relevant execution request. A valid authorization for Request A MUST NOT authorize Request B.

At minimum the fingerprint MUST cover:

- agent identity
- principal identity
- action
- target
- parameters
- capabilities
- environment
- task identity when present
- policy identity/version

### S3 — Deterministic canonicalization

Semantically identical security-relevant requests MUST produce the same canonical representation and fingerprint. Non-semantic serialization differences such as mapping key order MUST NOT change the fingerprint.

Security-relevant differences MUST change the fingerprint.

### S4 — Authorization is time-bounded

Every execution authorization MUST have an explicit expiry. Expired authorizations MUST be rejected.

### S5 — Authorization is single-use

An execution authorization MUST NOT be consumable more than once. A replay attempt MUST be rejected and recorded as evidence.

### S6 — Approval is request-bound

A human approval MUST be bound to the same request fingerprint as the execution authorization. Approval for one request MUST NOT be transferable to another request.

### S7 — Policy version is bound

An authorization MUST record the policy identity and version used to make the decision. An authorization MUST NOT silently become valid under an incompatible policy version.

### S8 — Capabilities are authoritative

An agent's declared capabilities MUST NOT grant authority by themselves. Capabilities are effective only when permitted by Apoa policy.

### S9 — Scope is authoritative

Targets MUST be normalized and checked against policy scope before execution. Equivalent representations MUST NOT permit scope escape.

### S10 — Parameter policy is authoritative

Parameters MUST be validated against policy before authorization. Changing a security-relevant parameter after authorization MUST invalidate the authorization.

### S11 — Fail closed

If Apoa cannot safely determine whether an operation is authorized, the protected operation MUST fail closed rather than execute.

### S12 — Provider neutrality

Apoa Core MUST NOT rely on a specific AI provider. Provider-specific adapters MUST translate provider requests into the canonical execution request model.

### S13 — Evidence

Authorization decisions, approvals, authorization issuance, rejected authorization attempts, execution outcomes, and replay attempts MUST be representable as auditable evidence events.

### S14 — Sensitive-data minimization

Evidence MUST NOT require storing secrets or unnecessary sensitive parameter values in plaintext. Redaction/minimization MUST be part of the evidence design.

## 3. Canonical Execution Request

The canonical request is the security boundary's input.

Conceptual structure:

```text
ExecutionRequest
  request_id
  agent
  principal
  action
  target
  parameters
  capabilities
  task_id
  environment
```

Provider-specific metadata MAY exist outside the security-critical canonical representation.

### Required semantics

- `action` identifies the operation being requested.
- `target` identifies the protected resource.
- `parameters` contain security-relevant execution inputs.
- `capabilities` identify requested authority, but do not grant authority.
- `agent` identifies the AI/software actor.
- `principal` identifies the human/service identity on whose authority the request operates.
- `environment` identifies the execution context such as development, staging, or production.
- `task_id` links related requests without replacing request identity.

## 4. Canonicalization and Fingerprinting

Apoa MUST normalize the security-relevant request before hashing.

Conceptually:

```text
request_fingerprint = SHA-256(canonical_request)
```

The implementation MAY choose a different cryptographic construction if it preserves the required properties.

### Fingerprint tests MUST prove

1. Same request with reordered object keys → same fingerprint.
2. Changed action → different fingerprint.
3. Changed target → different fingerprint.
4. Changed parameter → different fingerprint.
5. Changed agent → different fingerprint.
6. Changed principal → different fingerprint.
7. Changed capability set → different fingerprint.
8. Changed environment → different fingerprint.
9. Changed policy version → different fingerprint when policy version is part of the authorization context.

## 5. Decision Model

Apoa Core v1 has exactly three primary decisions:

```text
ALLOW
DENY
REQUIRE_APPROVAL
```

Reasons MUST be represented separately from the primary decision.

Suggested reason codes include:

```text
IDENTITY_MISSING
IDENTITY_UNKNOWN
IDENTITY_NOT_AUTHORIZED
CAPABILITY_MISSING
CAPABILITY_NOT_ALLOWED
TARGET_MISSING
TARGET_OUT_OF_SCOPE
TARGET_DENIED
PARAMETER_INVALID
PARAMETER_OUT_OF_RANGE
PARAMETER_NOT_ALLOWED
NO_MATCHING_RULE
EXPLICIT_DENY
POLICY_INVALID
POLICY_VERSION_MISMATCH
APPROVAL_REQUIRED
APPROVAL_MISSING
APPROVAL_DENIED
APPROVAL_EXPIRED
APPROVAL_MISMATCH
AUTHORIZATION_EXPIRED
AUTHORIZATION_INVALID
AUTHORIZATION_MISMATCH
AUTHORIZATION_REPLAYED
AUTHORIZATION_REVOKED
```

## 6. Policy Evaluation Order

Policy evaluation MUST be deterministic.

The baseline evaluation sequence is:

1. Validate request structure.
2. Resolve/validate identity.
3. Resolve applicable policy.
4. Apply explicit deny rules.
5. Validate required capability.
6. Validate target and scope.
7. Validate environment.
8. Validate parameters.
9. Evaluate configured risk conditions.
10. Produce `DENY`, `REQUIRE_APPROVAL`, or `ALLOW`.
11. Record the decision as evidence.

An explicit deny MUST NOT be overridden by a generic allow rule.

## 7. Authorization Object

An execution authorization MUST contain, directly or through an equivalent immutable structure:

```text
authorization_id
request_id
request_fingerprint
decision
policy_id
policy_version
issued_at
expires_at
nonce
approval_id (when applicable)
```

The authorization is valid only when:

- decision is `ALLOW`;
- current time is before expiry;
- request fingerprint matches exactly;
- policy binding is valid;
- nonce has not previously been consumed;
- required approval is present and valid;
- authorization has not been revoked, if revocation is enabled.

## 8. Approval Model

An approval MUST contain:

```text
approval_id
request_id
request_fingerprint
approver_id
decision
created_at
expires_at
```

Approval validation MUST verify:

- approval is for the exact request fingerprint;
- approval has not expired;
- approval was granted;
- approval is not revoked;
- the approval is valid for the authorization being issued.

An approval MUST NOT be reusable for a materially different request.

## 9. Execution Enforcement

Apoa MUST provide a protected execution boundary that can verify an authorization against the request immediately before tool execution.

Conceptual flow:

```text
AI Agent
  ↓
Adapter
  ↓
ExecutionRequest
  ↓
Apoa authorization
  ↓
Optional human approval
  ↓
Execution authorization
  ↓
Protected executor verifies request + authorization
  ↓
Tool executes
```

The executor MUST NOT trust an AI-generated statement such as "this operation was approved". It MUST verify the Apoa authorization itself.

## 10. Replay Protection

An authorization nonce MUST be unique for the authorization's validity scope and MUST become unusable after successful consumption.

Tests MUST cover:

- immediate replay;
- replay after the original execution succeeds;
- replay after process restart where persistence is claimed;
- concurrent consumption attempts.

The implementation MUST define whether a failed execution consumes an authorization. For Core v1, the preferred rule is that authorization is consumed when the protected executor accepts the execution for dispatch, preventing ambiguous repeated side effects.

## 11. Expiry and Revocation

Authorization and approval expiry MUST be enforced at validation time, not only at issuance time.

Future enterprise implementations MAY support explicit revocation. If revocation is implemented, a revoked authorization MUST fail closed.

## 12. Policy Versioning

Policy versions are immutable identifiers for a policy state used during authorization.

When policy changes:

- new requests MUST use the current applicable policy;
- existing authorizations MUST retain their original policy binding;
- a stale/incompatible authorization MUST NOT silently acquire new authority.

The initial implementation MAY reject an authorization when its policy version is no longer accepted.

## 13. Identity and Principal Separation

An AI agent and the human/service principal it acts for are distinct identities.

Example:

```text
principal: company-user-123
agent: gemini-agent-01
```

Apoa MUST NOT infer that an agent has all authority possessed by its principal.

## 14. Capability Security

Capabilities are explicit authority categories such as:

```text
FS_READ
FS_WRITE
GIT_READ
GIT_COMMIT
GIT_PUSH
DB_READ
DB_WRITE
HTTP_REQUEST
READ_SECRETS
CLOUD_READ
CLOUD_WRITE
PAYMENT
```

Capabilities MUST be granted by policy. An agent MUST NOT elevate itself by adding a capability to its own request.

## 15. Target and Scope Security

Target matching MUST occur after appropriate normalization for the target type.

The implementation MUST test:

- exact target matches;
- permitted prefixes/scopes;
- sibling/out-of-scope targets;
- traversal forms such as `../` where path targets apply;
- equivalent encoded representations where relevant;
- case sensitivity rules where relevant;
- empty or malformed targets.

Target semantics SHOULD remain target-type-specific rather than pretending every resource is a filesystem path.

## 16. Parameter Security

Core v1 MUST support deterministic parameter constraints sufficient for the initial demonstrations, including numeric bounds.

The architecture MUST leave room for:

- minimum/maximum;
- enumerated values;
- string patterns;
- nested values;
- collection constraints.

Parameter changes after authorization MUST invalidate the authorization fingerprint.

## 17. Risk

Risk is metadata/input to policy, not a replacement for policy.

Initial levels:

```text
LOW
MEDIUM
HIGH
CRITICAL
```

Example policy behaviour:

```text
LOW       → ALLOW
HIGH      → REQUIRE_APPROVAL
CRITICAL  → DENY
```

This is illustrative; policy remains authoritative.

## 18. Evidence

The minimum evidence lifecycle is:

```text
REQUEST_RECEIVED
POLICY_EVALUATED
DECISION_MADE
APPROVAL_REQUESTED
APPROVAL_GRANTED
APPROVAL_DENIED
AUTHORIZATION_ISSUED
AUTHORIZATION_REJECTED
EXECUTION_STARTED
EXECUTION_COMPLETED
EXECUTION_FAILED
AUTHORIZATION_CONSUMED
AUTHORIZATION_REPLAY_BLOCKED
```

Evidence SHOULD include:

- request ID;
- authorization ID when present;
- agent/principal identifiers;
- action;
- target or redacted target;
- decision;
- reason;
- policy/version;
- timestamps;
- execution result metadata.

Secrets MUST be redacted.

A later tamper-evident ledger MAY hash-link evidence events. That is not required to prove the Core v1 authorization invariant, but the data model MUST not prevent it.

## 19. Fail-Closed Behaviour

Protected execution MUST fail closed on:

- malformed authorization;
- missing authorization;
- request mismatch;
- fingerprint mismatch;
- expired authorization;
- replayed authorization;
- invalid approval;
- policy mismatch;
- unavailable required security state;
- ambiguous policy evaluation.

The implementation MUST NOT silently fall back to direct execution.

## 20. Threat Model

Apoa Core v1 assumes an untrusted AI agent may attempt to:

- modify its own request after authorization;
- claim capabilities it does not possess;
- change target resources;
- change parameters after approval;
- reuse an authorization;
- reuse another request's approval;
- impersonate another agent/principal within the adapter boundary;
- bypass an adapter and call a protected tool directly;
- exploit target normalization;
- exploit policy version changes;
- race two execution attempts;
- provide malformed or adversarial serialization.

Apoa Core v1 does not assume the underlying operating system, cloud account, network, or tool itself is malicious. Those become separate deployment/security concerns.

## 21. Mandatory Adversarial Test Matrix

The implementation is not considered Core v1 complete until tests exist for at least:

| Attack | Expected result |
|---|---|
| Change target after authorization | DENY |
| Change action after authorization | DENY |
| Change parameters after authorization | DENY |
| Change agent after authorization | DENY |
| Change principal after authorization | DENY |
| Add capability after authorization | DENY |
| Change environment after authorization | DENY |
| Reuse authorization | DENY |
| Expired authorization | DENY |
| Expired approval | DENY |
| Approval for different request | DENY |
| Explicit policy deny | DENY |
| Out-of-scope target | DENY |
| Missing capability | DENY |
| Policy-version mismatch | DENY or mandatory reauthorization |
| Direct protected-tool execution without Apoa authorization | BLOCK |
| Concurrent authorization consumption | At most one successful dispatch |
| Malformed authorization | DENY |
| Tampered fingerprint | DENY |

## 22. Core v1 Completion Gate

Apoa Core v1 is complete only when all of the following are true:

1. Canonical request representation exists.
2. Security-relevant request fingerprinting exists.
3. Authorization contains the fingerprint.
4. Approval contains the fingerprint.
5. Authorization validation compares the supplied request with the authorized request.
6. Replay protection is enforced.
7. Expiry is enforced.
8. Policy-version binding is enforced.
9. Capability, scope, environment, and parameter checks are deterministic.
10. A protected executor enforces the authorization immediately before tool execution.
11. Adversarial tests cover the mandatory matrix.
12. Evidence records the security lifecycle without requiring plaintext secrets.
13. The core remains AI-provider agnostic.
14. The public API remains small enough to integrate into an existing agent/tool stack.

## 23. Non-Goals for Core v1

Do not block Core v1 on:

- dashboard;
- billing;
- SSO;
- marketplace;
- multi-agent orchestration;
- cloud provisioning;
- large workflow engine;
- provider-specific business logic;
- enterprise UI polish.

These belong to later product milestones after the security primitive is proven.

## 24. Definition of Success

The strongest Core v1 demonstration is:

```text
AI requests git.push
        ↓
Apoa evaluates policy
        ↓
REQUIRE_APPROVAL
        ↓
Human approves exact request
        ↓
Apoa issues short-lived execution authorization
        ↓
Protected executor verifies exact request + authorization
        ↓
Git executes
        ↓
Evidence records outcome
```

Then mutate the request:

```text
same authorization + different target
        ↓
DENY
```

Then replay it:

```text
same authorization + same request
        ↓
DENY (already consumed)
```

If those properties hold, Apoa has demonstrated its central security primitive rather than merely wrapping an AI API.
