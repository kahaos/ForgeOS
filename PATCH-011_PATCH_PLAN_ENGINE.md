# ForgeOS Alpha 0.8 — PATCH-011
# Patch Plan Engine

Status: IMPLEMENTATION

## Purpose

Introduce a governed orchestration layer for ordered ForgeOS patch plans.

The Patch Plan Engine does not replace or bypass GovernanceStore.

GovernanceStore remains authoritative for:

- lifecycle state
- legal lifecycle transitions
- lifecycle audit
- approval enforcement

## Plan lifecycle

PLANNED
→ VALIDATING
→ READY
→ EXECUTING
→ VERIFYING
→ COMPLETED

Failure path:

EXECUTING
→ FAILED
→ ROLLBACK_REQUIRED
→ ROLLED_BACK

Validation failure:

VALIDATING
→ BLOCKED

## Patch record

Each patch contains:

- patch_id
- dependencies
- status
- verification
- rollback
- evidence

## Security boundary

PATCH-011 must never provide an HTTP endpoint that executes arbitrary shell commands.

Patch execution must occur through explicitly registered patch handlers.

The API is therefore an orchestration/control surface rather than a remote command executor.

## Current implementation

PATCH-011 v1 implements:

- persistent plan storage
- plan identity
- project binding
- ordered patch definitions
- dependency validation
- dependency-cycle detection
- plan digest
- append-only patch-plan audit
- machine-readable status
- receipt foundation

## Deliberately deferred

- arbitrary command execution
- production deployment
- automatic lifecycle mutation
- automatic approval
- SilverForge integration

Those require separate governed increments.
