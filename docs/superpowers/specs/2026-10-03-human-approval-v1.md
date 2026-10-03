# Human Approval v1 Specification

**Goal:** Make every `ASK` decision a human approval of one immutable, exact action request rather than a general permission.

## Scope

Human Approval v1 applies to the existing ForgeOS Control Plane and Gemini integration on the `human-approval-v1` branch. It does not replace the policy engine, Alpha release lifecycle, or evidence system.

## Approval record

Every approval request MUST capture:

- `approval_id`
- exact `ActionRequest`
- deterministic `request_digest` using SHA-256 over canonical JSON
- agent identity
- agent capability snapshot
- agent risk level
- policy version
- creation timestamp
- status
- approver when decided
- decision timestamp when decided

## Lifecycle

```text
PENDING
   ├── APPROVED -> verify binding -> execute exact request -> COMPLETED
   └── DENIED   -> DENIED
```

An approval MUST be single-use. A second decision or execution attempt MUST fail without executing the request.

## Exact-request binding

Before an approved request executes, ForgeOS MUST recompute the request digest and verify it equals the digest stored with the approval. The approval MUST also remain bound to the original agent identity, capability snapshot, risk level, and policy version.

Changing the target, action, tool, or any detail parameter MUST invalidate the approval rather than executing the modified request.

## Policy binding

Introduce a Control Plane policy version constant, initially `controlplane-1.0`. Approval records MUST store the version that produced the decision.

## Executor binding

The executor used for approval fulfilment MUST be associated with the original governed request rather than being freely substituted when the approval is decided. This version may use an in-process registry/binding because the current Gemini adapter is not yet a hardened process boundary. The later security-boundary milestone will move execution behind a separate process/container/service.

## Hard-deny validation

A disposable test agent MUST be granted `CREATE_AGENT`, `MODIFY_POLICY`, and `SPEND_FUNDS`, and all three actions MUST still return `DENY`. These policy actions remain hard-deny operations and cannot be self-granted.

## Evidence

The evidence trail MUST record the approval lifecycle with the approval ID and request digest:

```text
approval.requested
        -> approval.approved OR approval.denied
        -> approval.executed (approved path only)
```

The existing append-only hash-chain verification MUST remain valid.

## Gemini integration

The integration test MUST demonstrate:

```text
Gemini function call
        -> ForgeOS ASK
        -> human approval
        -> ForgeOS exact-request verification
        -> execution
        -> function result
        -> Gemini continuation
```

Gemini function calling remains application-executed: the model emits a structured function call, the application executes it, and the result is returned to the model. The Gemini Interactions API supports continuing the interaction using `previous_interaction_id` and a `function_result` step.

## Non-goals

- production deployment
- real financial transactions
- real secret retrieval
- autonomous policy modification
- multi-process/container security isolation
- finished approval web UI

## Success criterion

The Control Plane tests and a real Gemini integration test demonstrate that a human approves one exact governed operation, the exact approved request executes once, tampering is rejected, and the evidence chain records the lifecycle.
