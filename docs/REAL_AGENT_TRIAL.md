# ForgeOS real-agent trial harness

The real-agent trial harness is a safe bridge between the current scoped-authority prototype and a future external coding-agent integration.

## What it proves

`examples/real_agent_trial.py` runs a disposable task through the real ForgeOS `RuntimeGateway` and `ExecutionWorker` path. It exercises:

- task-scoped filesystem authority
- feature-branch Git push authority
- repository and branch escape denial
- human approval for simulated secret access
- signed governed execution after approval
- append-only evidence verification

## What it deliberately does not do

The harness does not contact GitHub, cloud providers, production systems, real secret stores, financial services, or deployment environments. Git and secret adapters are simulated.

This is intentional. The next step is to place a real coding agent in front of the control plane while retaining a disposable target and narrowly scoped credentials.

## Run it

```bash
python examples/real_agent_trial.py
```

For automated verification:

```bash
pytest tests/test_real_agent_trial.py -q
```

## Next stage

A real coding agent should receive a task, inspect its workspace, decide which changes are needed, and request tool operations. ForgeOS should independently authorize each operation. The agent should not be trusted to enforce its own permission boundary.
