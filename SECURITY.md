# Security Policy

## Scope

ForgeOS is an evolving AI agent authorization and governed-execution prototype. Security reports about authorization bypasses, scope escapes, replay, tampering, identity confusion, execution-boundary bypasses, or secret exposure are especially valuable.

## Reporting a vulnerability

Please do not disclose an unpatched security vulnerability publicly in an issue. Use GitHub's private security reporting mechanism for this repository when available.

Include:

- affected commit or version
- concise reproduction steps
- expected versus actual authorization behaviour
- whether an executor was reached
- relevant logs or evidence identifiers with secrets removed

Never include API keys, passwords, private tokens, or other credentials in reports.

## Current security limitations

The current project is not a production security certification. Human authentication, durable transactional state, provider credential binding, secret management, network policy, and production operational controls remain roadmap work.
