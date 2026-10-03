# Real-Agent MCP Boundary

ForgeOS can expose a deliberately narrow MCP-compatible tool surface to an autonomous coding agent. The agent is a requester; ForgeOS remains the authority that decides whether an action may execute.

## Boundary

```text
Autonomous agent
      |
      | MCP tool call
      v
ForgeOS MCP bridge
      |
      v
RuntimeGateway
      |
      +-- ALLOW -> signed authorization -> ExecutionWorker
      +-- ASK   -> pending human approval -> signed authorization -> ExecutionWorker
      +-- DENY  -> no executor invocation
```

The bridge must not expose a generic host shell. Tool calls must resolve to explicit ForgeOS capabilities and task-scoped grants.

## Initial tool surface

- `read_file`
- `write_file`
- `run_test`
- `git_status`
- `git_commit`
- `git_push`
- `request_action`

The first trial uses a disposable workspace and repository. The agent is not given production credentials, arbitrary secrets, Docker access, or unrestricted network access.

## Security invariants

1. Every tool call is bound to an agent and task.
2. Capability and scope are evaluated before executor invocation.
3. Scope mismatch is denied.
4. ASK never executes until an approval is explicitly recorded.
5. Approved execution uses the existing signed execution boundary.
6. Provider credentials stay in provider adapters rather than agent-visible tool arguments.
7. Unknown tools and malformed arguments fail closed.
8. Evidence records the authorization decision and execution outcome.

## First trial

The target task is a small website build in a disposable repository. The agent may modify the trial workspace, commit changes, and push a `feature/*` branch. Attempts to push `main`, access another repository, read ungranted secrets, or deploy production are expected to be denied or require approval according to the existing policy.

See [Real Agent Trial](REAL_AGENT_TRIAL.md) for the staged validation procedure and [AI Agent Authorization](AI_AGENT_AUTHORIZATION.md) for the broader authorization model.
