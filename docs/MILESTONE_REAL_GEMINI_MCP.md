# Milestone: Real Gemini Governed MCP Execution

**Date:** 2026-10-04  
**Status:** SUCCESS

## What this proves

ForgeOS has now been exercised by a real external Gemini agent through an MCP boundary, with ForgeOS remaining the authority over the resulting action.

The successful path was:

```text
Gemini 3.7 Flash
       |
       | MCP tool call
       v
Gemini MCP client
       |
       v
forgeos_write_file
       |
       v
ForgeOS MCP server
       |
       v
RuntimeGateway
       |
       +-- identity
       +-- task
       +-- capability
       +-- scope
       +-- policy
       |
       +-- ALLOW
       |
       v
signed execution authorization
       |
       v
ExecutionWorker
       |
       v
filesystem:write
       |
       v
bound disposable workspace
       |
       v
site/index.html
       |
       v
evidence ledger
```

The agent did not receive a generic shell. The workspace was bound by the ForgeOS runtime and the operation was evaluated against the task-scoped `FS_WRITE` authority.

## Trial identity

| Field | Value |
|---|---|
| External model | Gemini 3.7 Flash |
| Agent | `website-agent` |
| Task | `real-agent-website-build` |
| Capability | `FS_WRITE` |
| Policy | `controlplane-1.0` |
| MCP tool | `forgeos_write_file` |
| ForgeOS operation | `filesystem.write` |
| Executor | `filesystem:write` |
| Result | `completed` |

## Exact result

The agent created:

```text
site/index.html
```

with exactly:

```html
<html><body><h1>ForgeOS Gemini Trial</h1></body></html>
```

Execution result:

- bytes: `55`
- status: `completed`
- file SHA-256: `d30af4af6f7d9c91cd87c6386faecf5acf6dc3a30e34ee2b025853f2f17d0c36`

The recorded execution binding was:

`exec_d63b76b3bfc8`

The recorded request digest was:

`0885e2d0e3dbb3422bf48ac6db9114e59ce5760ae1ec0b3f4189132f2b37cd3f`

The resulting evidence digest was:

`dcf9bf9d06bad6a0159dde9c6bfcc1666e12c939308f58b9197d415d2f5622ac`

A committed evidence record is available at:

`evidence/gemini-write-success/2026-10-04-live-run.txt`

## How we got here

### 1. MCP boundary

ForgeOS introduced a narrow MCP-compatible bridge rather than exposing a generic host shell. The bridge maps model-facing tools onto explicit ForgeOS capabilities and existing execution adapters.

### 2. Workspace binding

The write operation originally depended on a workspace supplied in the request. That was tightened so the MCP server binds the workspace from the trusted trial runtime. The external agent supplies only the relative file name and content.

This prevents the agent from selecting an arbitrary workspace outside the authority already established for the task.

### 3. Gemini configuration debugging

Gemini initially connected to the MCP server but did not expose the expected tools to the model. Investigation showed that an empty Gemini `tools.core` configuration was suppressing the normal model tool surface. Removing that unrelated deny-all configuration restored MCP discovery.

A second issue was a name collision between Gemini CLI's built-in `write_file` capability and the ForgeOS MCP tool. The ForgeOS tool was renamed to:

`forgeos_write_file`

The underlying ForgeOS action did not change.

### 4. Direct MCP verification

Before retrying the external agent, the ForgeOS MCP server was tested directly. The renamed write tool successfully passed through the MCP protocol, RuntimeGateway, authority evaluation, approval/evidence recording, and filesystem executor.

This isolated the remaining problem to the Gemini-facing tool surface rather than the ForgeOS execution path.

### 5. Real Gemini verification

A fresh disposable trial was then prepared with the governed ForgeOS MCP server. Gemini was instructed to use only `forgeos_write_file` and not to use shell commands or other tools.

Gemini successfully invoked the ForgeOS tool and created the exact requested file.

## Evidence chain

The successful execution recorded both authorization and execution events. The authorization included the agent snapshot, capability, task scope, request details, policy version, grant, and approval identifier. The execution event recorded the executor, result, execution binding, and chained evidence digest.

Approval identifier:

`auto_82ff9989b314`

This is important because the success is not merely that a file appeared on disk. The execution passed through the same governed control plane that records why the action was allowed and which executor was released to perform it.

## Verification

The full ForgeOS regression suite was run after the implementation work:

**159 tests passed.**

The evidence milestone was then committed and pushed to the `real-agent-mcp-v1` branch.

## What changed in the codebase

The milestone included changes across the MCP server, Gemini trial harness, and regression tests:

- MCP write tool renamed from `write_file` to `forgeos_write_file`.
- Write schema reduced to `name` and `content` at the agent-facing boundary.
- Trusted runtime workspace binding added to the MCP server.
- Gemini trial configuration updated to use the renamed tool.
- Gemini regression tests updated to prevent the old tool name from returning.
- MCP stdio tests updated for the current seven-tool surface.
- Executor registration and RuntimeGateway paths retained as the central execution boundary.
- Successful live execution captured as committed evidence.

## Current seven-tool MCP surface

The real-agent MCP bridge currently exposes:

1. `read_file`
2. `forgeos_write_file`
3. `run_test`
4. `git_status`
5. `git_commit`
6. `git_push`
7. `request_action`

The presence of a tool does not itself grant authority. Each request still enters the ForgeOS control plane and is evaluated against the agent, task, capability, scope, policy, and execution binding.

## What this does not prove

This milestone is intentionally narrow.

It does **not** claim:

- unrestricted agent execution;
- unrestricted shell access;
- production GitHub access;
- production secret retrieval;
- production deployment;
- enterprise identity integration;
- production readiness;
- security certification.

The trial uses disposable resources and controlled local adapters.

## Next milestones

The next useful proofs are:

1. **Real Gemini test execution** — Gemini requests `run_test`; ForgeOS authorizes the fixed test executor and records the result.
2. **Real Gemini Git commit** — Gemini creates a controlled change and requests `git_commit` within the scoped repository.
3. **Real Gemini Git push** — a feature-branch push is allowed while a protected branch remains denied.
4. **Human approval** — a consequential request enters `ASK`, is explicitly approved, and only then reaches the execution worker.
5. **Adversarial runtime validation** — replay, scope escape, tampering, and state-drift attempts continue to be tested around the live-agent boundary.

## Bottom line

The central milestone is simple:

> **A real external AI agent has now crossed the ForgeOS MCP boundary and performed an actual filesystem action without receiving unrestricted authority.**

ForgeOS made the authorization decision, bound the execution to the disposable workspace, released the executor, and recorded the resulting evidence.
