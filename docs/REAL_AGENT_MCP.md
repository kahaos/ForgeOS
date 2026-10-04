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

The bridge must not expose a generic host shell. Tool calls resolve to explicit ForgeOS capabilities and task-scoped grants.

## Current tool surface

The real-agent MCP bridge currently exposes seven governed tools:

- `read_file`
- `forgeos_write_file`
- `run_test`
- `git_status`
- `git_commit`
- `git_push`
- `request_action`

The write operation deliberately uses the `forgeos_write_file` name rather than the generic `write_file` name. During Gemini integration testing, the generic name collided with Gemini CLI's built-in tooling. Renaming the MCP-facing tool made the ForgeOS operation unambiguous without changing the underlying ForgeOS action.

The Gemini CLI trial is configured with only the ForgeOS MCP server and an explicit per-server tool allowlist. The MCP bridge therefore remains narrow before a model can invoke an operation.

The first trial uses a disposable workspace and local bare Git repository. The agent is not given production credentials, arbitrary secrets, Docker access, or unrestricted shell access.

## Successful Gemini milestone

On 2026-10-04, Gemini 3.7 Flash successfully invoked `forgeos_write_file` through this boundary and created `site/index.html` inside the ForgeOS-bound disposable workspace.

The successful execution path was:

```text
Gemini
  -> forgeos_write_file
  -> MCP server
  -> RuntimeGateway
  -> scoped authority
  -> ExecutionWorker
  -> filesystem:write
  -> bound workspace
  -> evidence
```

The operation was authorized under agent `website-agent`, task `real-agent-website-build`, with `FS_WRITE` capability and policy `controlplane-1.0`.

See [Real Gemini MCP Milestone](MILESTONE_REAL_GEMINI_MCP.md) and the committed evidence record at `evidence/gemini-write-success/2026-10-04-live-run.txt`.

## Security invariants

1. Every tool call is bound to an agent and task.
2. Capability and scope are evaluated before executor invocation.
3. Scope mismatch is denied.
4. ASK never executes until an approval is explicitly recorded.
5. Approved execution uses the existing signed execution boundary.
6. Provider credentials stay in provider adapters rather than agent-visible tool arguments.
7. Unknown tools and malformed arguments fail closed.
8. Evidence records the authorization decision and execution outcome.
9. The local test executor accepts no agent-supplied shell command; it invokes one fixed test command with an argument vector.
10. File operations are resolved against the pre-bound workspace and reject traversal outside that workspace.

## Workspace binding

For the governed write operation, the MCP server binds the workspace from the trusted trial runtime. The external agent supplies a relative file name and content rather than choosing the execution workspace itself.

This keeps resource selection inside the authority already established for the task and prevents an agent from redirecting the executor to an unrelated workspace.

## Executor boundary

The MCP bridge is not itself the final executor. It routes requests through the RuntimeGateway and ExecutionWorker. Executor identifiers such as `filesystem:write`, `filesystem:read`, `test:run`, `git:status`, `git:commit`, and `git:push` are bound by the runtime.

Executable adapter callables are process-local. Persisted executor metadata records the identity and target binding so restart behaviour cannot silently recreate an executable authority that was never explicitly registered by the current process.

## Trial scope

The target task is a small website build in a disposable repository. The agent may modify the trial workspace, commit changes, and push a `feature/*` branch when its scoped authority permits those operations. Attempts to push a protected branch, access another repository, read ungranted sensitive material, or perform an unrelated operation are expected to be denied or routed to approval according to the active grants and policy.

The local adapters deliberately use argument vectors rather than shell command strings for subprocess execution. The local test executor also uses a fixed test command rather than accepting arbitrary commands from the agent.

## What the current milestone does not prove

The successful Gemini write is a controlled low-risk milestone. It does not claim unrestricted shell execution, production GitHub access, production secret retrieval, production deployment, enterprise identity integration, or production readiness.

The next validation targets are real-agent test execution, Git commit/push, human approval, and additional adversarial runtime tests.

See [Real Agent Trial](REAL_AGENT_TRIAL.md) for the staged validation procedure, [Real Gemini MCP Milestone](MILESTONE_REAL_GEMINI_MCP.md) for the detailed evidence, and [AI Agent Authorization](AI_AGENT_AUTHORIZATION.md) for the broader authorization model.
