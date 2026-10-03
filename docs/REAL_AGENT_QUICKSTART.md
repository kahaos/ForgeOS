# Real AI agent quickstart

This guide explains the first ForgeOS agent trial. It is intentionally low-risk: the workspace is disposable, Git operations are simulated, and no production credentials are required.

## 1. Run the deterministic ForgeOS trial

From the repository root:

```bash
python examples/real_agent_trial.py
```

The deterministic trial entry point is `real-agent-trial.py` in the documented trial naming convention; the repository command above is the current runnable implementation.

The trial creates a task-scoped `website-agent` and exercises:

- workspace file write → **ALLOW**
- assigned feature branch push → **ALLOW**
- `main` push → **DENY**
- unrelated repository push → **DENY**
- simulated secret access → **ASK**
- human approval → governed execution

The final output also reports whether the evidence chain verifies.

## 2. What makes this an agent trial?

A real coding agent can be placed in front of the same control-plane model. The agent should be free to decide what work it needs to perform, while ForgeOS independently decides whether each requested operation is permitted.

The important test is not whether the agent follows a list of pre-written calls. The important test is whether the agent remains useful when ForgeOS is the authority and the agent encounters operations outside its grant.

## 3. First external-agent deployment

For the next stage, use a disposable GitHub repository and a feature branch. Give the agent only the credentials and tools required for that repository. Do not provide production credentials or unrestricted secrets.

The intended boundary is:

```text
Coding agent
   ↓
ForgeOS task + scoped grants
   ↓
Runtime Gateway
   ↓
Execution Worker
   ↓
Disposable repository/workspace
```

## 4. What to measure

Record:

- task completion
- autonomous operations requested
- allowed operations
- denied operations
- human approvals
- false denials or unnecessary friction
- execution latency
- evidence completeness
- replay attempts
- scope-escape attempts

## 5. Current limitation

The repository currently provides a prototype control plane and safe trial harness. Real provider adapters, authenticated human principals, production persistence, and production deployment controls are future milestones.

See [Why ForgeOS?](WHY_FORGEOS.md), [AI agent authorization](AI_AGENT_AUTHORIZATION.md), and [the security model](SECURITY_MODEL.md).
