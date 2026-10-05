# ForgeOS evidence and current status

This page separates demonstrated repository behaviour from future product goals.

## Current verified status — 2026-10-05

The latest ForgeOS regression verification completed with:

```text
179 passed, 7 skipped in 1.22s
```

The latest autonomous OpenRouter trial also passed its independent completion and authority checks:

```text
MODEL_REQUESTS: 5
FILES_CREATED: 3
CURRENT_RUN_FILES: ['index.html', 'script.js', 'style.css']
ALLOWED_WRITES: 3
DENIED_ACTIONS: 0
OUT_OF_SCOPE_DENIED: True
COMPLETION_VALIDATION: {'complete': True, 'missing_files': [], 'errors': []}
EVIDENCE_EVENTS: 44
EVIDENCE_OK: True
EXTERNAL_SERVICES: []
FORGEOS_OPENROUTER_AUTONOMOUS_TEST: PASS
```

During that run, the upstream OpenRouter provider returned a `502 provider_unavailable` response on turn 2. ForgeOS explicitly rejected the provider error as completion and requested another autonomous turn. The agent then created `style.css` and `script.js` and later returned a normal `stop` response. ForgeOS independently validated the resulting workspace before accepting completion.

See `docs/MILESTONE_AUTONOMOUS_PROVIDER_RESILIENCE.md` and `docs/evidence/2026-10-05-provider-authority-validation.md` for the preserved milestone and detailed evidence.

## Verified hardening evidence

The `hardening-v1` development track has been exercised with:

- full Python regression suite: 115 passed, 7 skipped
- opt-in Docker isolation suite: 7 passed
- scoped multi-agent demo: feature branch push allowed, main push denied, unrelated repository denied
- focused execution-boundary regression suite: 5 passed

These figures are historical baseline evidence for the earlier hardening track; the current repository verification is recorded above.

The Docker tests require an explicit opt-in because they need a usable Docker daemon.

## What the evidence demonstrates

The evidence demonstrates prototype behaviour around scoped authority, execution-boundary enforcement, replay protection, state binding, restrictive worker isolation, provider-neutral tool execution, autonomous task execution, provider-failure recovery, and independent completion validation.

The latest milestone demonstrates that an upstream provider failure does not automatically become a successful agent completion. ForgeOS remains responsible for deciding whether the task is complete.

## What it does not demonstrate

It does not establish production readiness for arbitrary autonomous agents. In particular, the current repository still needs production identity federation, durable transactional persistence, provider credential binding, operational controls, and production-grade deployment integrations.

## Live evidence artifacts

The repository contains dated evidence artifacts for the human-approval, governed-execution, provider-neutral, and autonomous-agent work. Those artifacts should be read as test evidence with their stated limitations, not as independent security certification.

## Real-agent trial evidence

The `examples/real_agent_trial.py` harness is deliberately safe: it uses a disposable local workspace and simulated Git/secrets adapters. Its purpose is to prove the control path before introducing real external credentials.

Run it with:

```bash
python examples/real_agent_trial.py
```

The output reports ALLOW/DENY/ASK behaviour, approval execution, evidence count, and evidence-chain verification.

## Autonomous provider-resilience evidence

The 2026-10-05 autonomous website trial is preserved as a specific failure-recovery and completion-authority milestone.

Observed sequence:

```text
AI agent receives high-level objective
        ↓
ForgeOS grants scoped FS_WRITE
        ↓
Agent creates index.html
        ↓
Upstream provider returns 502/provider_unavailable
        ↓
ForgeOS rejects provider error as completion
        ↓
Agent receives another autonomous turn
        ↓
Agent creates style.css and script.js
        ↓
Provider returns normal stop
        ↓
ForgeOS validates required files and workspace
        ↓
Out-of-scope action is denied
        ↓
Evidence chain verifies
```

The provider was therefore able to fail without taking control of ForgeOS task state.
