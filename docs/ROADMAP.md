# ForgeOS roadmap

ForgeOS is being developed as an AI agent control plane: a shared authorization and governed-execution layer for autonomous agents and the tools they use.

## Current: hardened scoped-authority prototype

Verified in the current development track:

- task-scoped capability grants
- resource and branch scoping
- multi-agent authority separation
- attenuating delegation
- ALLOW / ASK / DENY decisions
- exact-request human approval
- signed execution authorizations
- single-use execution nonces
- replay/tamper/state-drift protections
- Docker-backed isolated worker tests
- provider-neutral Runtime Gateway
- reproducible real-agent-shaped trial harness using safe simulated adapters

## Next: real agent integration

The next validation stage is a real coding agent operating against a disposable repository/workspace through ForgeOS. The purpose is to measure usefulness and friction while keeping production systems outside the trust boundary.

## v1.2 security foundation

Planned work includes:

- authenticated human and agent principals
- OIDC/JWT or deployment-appropriate identity integration
- race-safe authorization and approval transactions
- durable transactional state
- stronger policy version lifecycle
- provider-specific credential binding
- controlled Git/GitHub adapters
- network egress policy
- secret isolation

## Platform stage

Longer-term work can add:

- production GitHub/cloud adapters
- deployment environments with explicit release gates
- live control console
- evidence search and audit workflows
- budgets and rate limits
- multi-agent orchestration
- policy administration with protected change control
- integrations with agent runtimes and tool protocols

Roadmap items are targets, not claims that those capabilities are already production-ready.
