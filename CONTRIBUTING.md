# Contributing to ForgeOS

ForgeOS is an open-source project exploring secure authorization and governed execution for autonomous AI agents.

## Before opening a change

Please explain the problem, the proposed behaviour, and the security boundary involved. For authorization or execution changes, include tests that demonstrate both the intended path and the relevant denial or bypass case.

## Development

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip pytest
pytest -q
```

Docker isolation tests are opt-in because they require a usable Docker daemon.

## Security-sensitive changes

Changes involving identity, capability grants, policy, approvals, execution authorization, worker boundaries, secrets, or provider credentials should include adversarial tests where practical.

Do not commit credentials or production configuration.

## Documentation

Use clear, descriptive page titles and write for the person trying to solve a concrete AI-agent security or authorization problem. Keep product claims proportional to the evidence in the repository.
