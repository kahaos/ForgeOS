# ForgeOS evidence and current status

This page separates demonstrated repository behaviour from future product goals.

## Verified hardening evidence

The `hardening-v1` development track has been exercised with:

- full Python regression suite: 115 passed, 7 skipped
- opt-in Docker isolation suite: 7 passed
- scoped multi-agent demo: feature branch push allowed, main push denied, unrelated repository denied
- focused execution-boundary regression suite: 5 passed

The Docker tests require an explicit opt-in because they need a usable Docker daemon.

## What the evidence demonstrates

The evidence demonstrates prototype behaviour around scoped authority, execution-boundary enforcement, replay protection, state binding, and restrictive worker isolation.

## What it does not demonstrate

It does not establish production readiness for arbitrary autonomous agents. In particular, the current repository still needs production identity federation, durable transactional persistence, provider credential binding, operational controls, and production-grade deployment integrations.

## Live evidence artifacts

The repository contains dated evidence artifacts for the human-approval and governed-execution work. Those artifacts should be read as test evidence with their stated limitations, not as independent security certification.

## Real-agent trial evidence

The `examples/real_agent_trial.py` harness is deliberately safe: it uses a disposable local workspace and simulated Git/secrets adapters. Its purpose is to prove the control path before introducing real external credentials.

Run it with:

```bash
python examples/real_agent_trial.py
```

The output reports ALLOW/DENY/ASK behaviour, approval execution, evidence count, and evidence-chain verification.
