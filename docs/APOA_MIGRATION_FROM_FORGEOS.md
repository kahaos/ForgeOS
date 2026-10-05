# Apoa Migration From ForgeOS

## Purpose

This document defines the non-destructive transition from the ForgeOS prototype/control plane to Apoa Core.

## Rule

**Do not delete ForgeOS. Do not rename the production branch during Core extraction.**

ForgeOS remains the historical prototype and source of validated behaviour. Apoa is the focused authorization product extracted from that work.

## Current branch

The first extraction work lives on:

```text
apoa-core-v1
```

The branch is intentionally isolated from `main`.

## What is being extracted

- canonical authorization request model
- ALLOW / DENY / REQUIRE_APPROVAL decisions
- capability checks
- resource scope checks
- parameter limits
- human approval binding
- short-lived execution authorization
- single-use nonce consumption
- evidence records
- provider-neutral interfaces

## What remains outside Core v1

- broad agent orchestration
- dashboard redesign
- multi-agent runtime management
- billing
- enterprise SSO
- large provider matrix
- cloud deployment automation

## Validation strategy

1. Prove Core primitives independently.
2. Run security regression tests.
3. Connect the existing MCP/Gemini path.
4. Compare behaviour against the existing ForgeOS evidence.
5. Add a provider-neutral integration.
6. Validate the developer experience with an external test user.

## Repository transition

When Core v1 is stable, create the standalone GitHub repository:

```text
kahaos/apoa
```

Display name:

```text
Apoa — Auth0 / Open Policy Agent for AI Tool Execution
```

Copy only the Apoa-specific implementation and documentation into that repository. Preserve ForgeOS history in its existing repository.

## Acceptance criterion

A developer must be able to place Apoa between an existing AI agent and its tools without adopting the ForgeOS runtime or dashboard.
