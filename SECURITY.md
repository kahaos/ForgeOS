# Security Policy

ForgeOS is an AI-agent authorization and governed-execution prototype. Security review is a first-class part of the project.

## Security-sensitive reports

Reports involving the following are especially valuable:

- authorization bypasses
- task or resource scope escapes
- capability escalation
- replay, tampering, or state-drift attacks
- identity or principal confusion
- human-approval bypasses
- execution-boundary bypasses
- unsafe executor or tool registration
- secret exposure
- provider or MCP boundary failures

## Reporting a vulnerability

Please do not disclose an unpatched vulnerability publicly in a GitHub issue. Use GitHub's private security reporting mechanism for this repository when available.

Include:

- affected commit or version
- concise reproduction steps
- expected versus actual authorization behaviour
- whether an executor was reached
- relevant logs or evidence identifiers with sensitive values removed
- security impact and known preconditions

Never include API keys, passwords, private tokens, credentials, or other sensitive material in a report.

## Security claims and limitations

**ForgeOS is not currently a production security certification, and the repository should not be treated as one.**

The project contains prototype validation and committed evidence, including governed execution and human-approval paths. Important production controls remain roadmap work, including authenticated principals, durable transactional state, provider credential binding, secret isolation, network egress controls, production Git/GitHub and cloud adapters, deployment controls, and operational monitoring.

The real Gemini MCP milestone is a controlled, low-risk disposable trial. It demonstrates a working governed execution path; it does not establish production readiness.

## Security contributions

Security improvements are welcome. Changes involving identity, capabilities, policy, approvals, execution authorization, worker boundaries, secrets, provider credentials, or MCP integrations should include adversarial or negative-path tests where practical.

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidance.