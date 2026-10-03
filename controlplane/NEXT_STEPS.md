# ForgeOS Control Plane — Frozen Checkpoint

## Status

This branch is a deliberate frozen checkpoint for the ForgeOS control-plane work:

- Branch: `controlplane-1.0-frozen`
- Snapshot commit before this note: `0f6720051b35b8fafc02ad688a714078bb5bac3c`
- The control plane is considered a foundation/prototype, not a finished 1.0 architecture.

Do not treat this branch as the place for active development. Use a new development branch for future changes so this checkpoint remains easy to return to.

## What is already here

The control plane currently provides the core concepts needed for ForgeOS:

- agent identity
- capabilities
- risk levels
- allow / deny / approval decisions
- persistent control-plane state
- evidence recording
- executor gating for the integrated filesystem and shell paths
- tests proving allowed execution and missing-capability denial

The existing ForgeOS Alpha system also contains the governed execution lifecycle for evidence, verdicts, approvals, releases, preflight, deployment, verification and rollback.

## Architectural decision

Keep the control-plane concept.

Do **not** replace the existing Alpha execution/governance system. The intended architecture is to make the two layers complementary:

```text
AI Agent
   |
   v
ForgeOS Control Plane
   |  identity
   |  capabilities
   |  policy
   |  risk
   |  approval
   |  evidence
   |
   v
Action / Execution Gateway
   |
   v
ForgeOS Alpha governed execution
   |  evidence
   |  verdict
   |  approval
   |  release
   |  preflight
   |  execute
   |  verify
   |  rollback
   |
   v
Real target
```

The control plane answers:

> Is this agent allowed to request this operation?

Alpha answers:

> Has this particular operation satisfied ForgeOS's required governed lifecycle?

Both layers must succeed before sensitive execution proceeds.

## Immediate next step

Create a new development branch from this frozen checkpoint and implement the smallest useful integration:

> Route AI execution requests through the Control Plane before they reach Alpha governed execution.

Start with one real execution path. Do not attempt to integrate every executor at once.

### Required first integration

1. Accept an AI execution request.
2. Identify the requesting agent.
3. Evaluate its capability and risk through the Control Plane.
4. Return `ALLOW`, `ASK`, or `DENY`.
5. Only an allowed request proceeds into Alpha.
6. An approval-gated request must obtain human approval before proceeding.
7. A denied request must never reach the Alpha executor.
8. Record enough evidence to correlate the Control Plane decision with the Alpha lifecycle.

## Important hardening work

Before calling the integration production-ready, approval records should be bound to the exact operation being approved. An approval should include, at minimum:

- request ID
- request digest
- agent identity
- capability snapshot
- target
- relevant parameters/digest
- policy version
- approver identity
- approval timestamp

This prevents an approval for one request being reused for a different request.

## Evidence direction

The Control Plane and Alpha currently have separate evidence mechanisms. The next architecture should allow a single operation to be traced across both layers using a common request/execution identifier and cryptographic bindings where appropriate.

The desired audit trail is conceptually:

```text
agent
  -> request
  -> policy decision
  -> approval (if required)
  -> verdict
  -> release
  -> preflight
  -> execution
  -> verification
  -> rollback (if required)
```

## Development order after integration

### Phase 1 — Foundation

- Control Plane -> Alpha integration
- request IDs and request hashes
- approval binding
- unified/correlated evidence
- integration tests

### Phase 2 — Executors

Gradually connect controlled executors such as:

- filesystem
- shell
- Git
- GitHub
- network/web
- deployment

Each executor should be gated by the same authorization path rather than implementing its own independent permission model.

### Phase 3 — UI

Expose the control-plane state in the ForgeOS UI:

- agents
- capabilities
- risk
- pending approvals
- live requests
- decisions
- executions
- evidence
- policy state

### Phase 4 — Multi-agent operation

Support multiple specialized agents while keeping ForgeOS authoritative over what they can do:

- agent registration
- capability assignment
- agent-to-agent requests
- controlled agent creation
- spending/budget controls
- secret access controls

### Phase 5 — Security hardening

- strong authentication
- policy versioning
- tamper-evident evidence chains
- secrets isolation
- rate limits
- replay protection
- rollback/recovery
- adversarial/security testing

## What not to do next

- Do not delete the control plane.
- Do not replace Alpha with the control plane.
- Do not build a second independent governance system.
- Do not connect production deployment yet.
- Do not make broad live-VPS changes before isolated integration tests pass.
- Do not manufacture missing legacy UI patch artifacts merely to make the entire historical test suite green.

## Verification baseline

The control-plane-specific tests were verified successfully in the VPS worktree. The broader historical test suite has unrelated legacy UI tests referencing missing patch artifacts; those failures should remain separate from evaluation of the new control-plane work.

## Definition of the next milestone

The next milestone is **not** "more features." It is:

> One AI execution request can pass through the Control Plane, satisfy the appropriate authorization/approval rules, enter Alpha governed execution, produce correlated evidence, and be rejected before execution when authorization fails.

Once that works reliably, expand the same gateway pattern to additional executors.
