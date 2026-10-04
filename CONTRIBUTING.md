# Contributing to ForgeOS

ForgeOS is an open-source project exploring secure authorization and governed execution for autonomous AI agents.

The project is especially interested in contributions around **agent security, least privilege, runtime authorization, policy, human approval, MCP, provider adapters, evidence, and secure integrations**.

## Before opening a change

Please explain:

1. the problem being solved
2. the proposed behaviour
3. the security or authority boundary involved
4. how the change is tested

For authorization or execution changes, include tests for both the intended path and the relevant denial, bypass, or scope-escape case.

## Development

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip pytest
pytest -q
```

Docker isolation tests are opt-in because they require a usable Docker daemon.

## Where contributions belong

- `controlplane/` — core authorization, policy, gateway, evidence, and execution primitives
- `examples/` — safe demonstrations and reproducible trials
- `tests/` — regression, adversarial, and integration coverage
- `docs/` — architecture, security, guides, milestones, and roadmap
- provider adapters — keep provider-specific code thin; shared authority semantics belong in ForgeOS
- application integrations — add explicit scopes and governed actions rather than broad unrestricted access

## Security-sensitive changes

Changes involving identity, capability grants, policy, approvals, execution authorization, worker boundaries, secrets, provider credentials, or MCP integrations should include adversarial tests where practical.

Do not commit credentials or production configuration.

## Documentation and product claims

Write for the person trying to solve a concrete AI-agent security or authorization problem. Keep product claims proportional to the evidence in the repository. Clearly distinguish **verified**, **experimental**, and **planned** capabilities.

For security vulnerabilities, follow [SECURITY.md](SECURITY.md) rather than opening a public issue with sensitive details.