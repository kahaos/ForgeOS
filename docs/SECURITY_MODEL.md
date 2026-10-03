# ForgeOS security model

ForgeOS is designed as an authorization and governed-execution boundary for autonomous AI agents.

## Security principles

1. **ForgeOS is authoritative.** Sensitive operations enter through the ForgeOS authorization path.
2. **Least privilege is task-scoped.** Grants should be narrow in capability, resource, environment, and lifetime.
3. **Deny is terminal.** A denied operation must not reach an executor.
4. **Approval is exact.** Human approval is bound to the specific request and relevant state snapshots.
5. **Execution is bound.** Signed authorizations bind request, identity, policy, task/grant state, executor, expiry, and nonce.
6. **Evidence is first-class.** Meaningful authorization and execution transitions produce an append-only evidence chain.
7. **Fail closed.** Missing or changed authorization context prevents execution.
8. **Control and execution are separate.** The control plane decides; the governed worker executes.

## 12-gate governed execution model

1. Identity
2. Capability
3. Risk
4. Policy
5. Evidence
6. Verdict
7. Human Approval
8. Release
9. Preflight
10. Execute
11. Verify
12. Rollback

The first four gates form the authorization decision. The remaining gates govern the lifecycle after a request is authorized.

## Threats covered by the prototype

The current tests cover scope mismatch, capability mismatch, executor substitution, authorization tampering, state drift, expiry, replay, and restrictive Docker execution defaults.

## Threats still requiring production work

The current prototype does not by itself provide a complete enterprise identity system, transactional production database, cloud-provider enforcement, production secret management, network policy platform, or production incident-response system.

Human operator identity is currently represented by a server-bound operator principal in the prototype API. It should be replaced by a real authenticated principal model such as OIDC/JWT or another deployment-appropriate mechanism before production use.

## Safe trial boundary

The real-agent trial in this repository uses a disposable workspace and simulated Git/secrets adapters. It demonstrates the control path; it does not claim that the repository is ready to authorize arbitrary production agents.
