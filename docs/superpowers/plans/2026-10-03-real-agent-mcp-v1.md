# Real-Agent MCP v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connect a real autonomous coding agent to ForgeOS through a narrow MCP tool bridge so ForgeOS remains the authoritative authorization and execution boundary.

**Architecture:** The agent receives only ForgeOS-governed MCP tools. Each tool call becomes an `ActionRequest` evaluated by the existing scoped `RuntimeGateway`, then either executes through signed `ExecutionAuthorization` + `ExecutionWorker`, waits for human approval, or is denied. No generic host shell, provider credential, Docker socket, or production credential is exposed to the agent.

**Tech Stack:** Python, existing ForgeOS Control Plane, RuntimeGateway, ExecutionAuthorizer, ExecutionWorker, MCP-compatible server interface, pytest, Gemini CLI for external validation.

**Spec:** `docs/REAL_AGENT_MCP.md`

## Global Constraints

- ForgeOS remains the authoritative policy and execution boundary.
- MCP tools MUST NOT expose unrestricted host shell access.
- The first real-agent trial MUST use a disposable workspace and repository.
- The first real-agent grant MUST be task-scoped and branch-scoped.
- Production deployment, secrets, spending, and unrelated repositories remain unavailable.
- Provider credentials remain outside agent prompts/tool results and are owned by provider adapters.
- Existing hardened execution tests must remain green.
- Real-agent integration is experimental until the external VPS trial passes.

## Review Focus

- Tool calls that attempt to escape the task scope must be denied before executor invocation.
- Unknown or malformed MCP tools/arguments must fail closed.
- ASK operations must create a pending approval and must not execute before approval.
- Approved operations must use signed execution authorization and replay protection.
- The agent must not receive a generic shell or direct provider credential path.

### Task 1: MCP contract and governed server

**Files:**
- Create: `docs/REAL_AGENT_MCP.md`
- Create: `controlplane/mcp_server.py`
- Test: `tests/test_mcp_server.py`

- [ ] Write failing tests for tool discovery, scoped allow/deny, ASK behavior, and absence of unrestricted shell.
- [ ] Run the focused tests and verify the failure is caused by the missing MCP implementation.
- [ ] Implement the minimal MCP server/bridge over `RuntimeGateway`.
- [ ] Run the focused tests and verify they pass.
- [ ] Commit the contract and implementation.

### Task 2: Agent session and trial runner

**Files:**
- Create: `controlplane/agent_session.py`
- Create: `examples/run_gemini_forgeos_trial.py`
- Test: `tests/test_agent_session.py`
- Test: `tests/test_real_agent_boundary.py`

- [ ] Write failing tests for task/session binding and rejection of cross-task or unbound requests.
- [ ] Run the focused tests and verify the failure.
- [ ] Implement the minimal session binding layer.
- [ ] Add a safe trial runner that launches the agent only with ForgeOS MCP tools.
- [ ] Run focused tests and verify they pass.
- [ ] Commit the session/trial layer.

### Task 3: External Gemini validation

**Files:**
- Modify: `docs/REAL_AGENT_MCP.md`
- Modify: `docs/REAL_AGENT_TRIAL.md`

- [ ] Run the full Python suite on the VPS.
- [ ] Run the Docker isolation suite.
- [ ] Run the MCP bridge tests.
- [ ] Launch Gemini against the disposable workspace with no direct host shell/provider credentials.
- [ ] Record ALLOW, DENY, ASK, approval, execution, and evidence outcomes.
- [ ] Verify the agent can complete the useful website task without bypassing ForgeOS.
- [ ] Document the observed limitations and any v1.2 changes required.

### Task 4: GitHub disposable-repository trial

- [ ] Create/use a disposable GitHub repository dedicated to the trial.
- [ ] Configure the narrowest available repository credential.
- [ ] Grant only `GIT_READ`, `GIT_COMMIT`, and `GIT_PUSH` to `feature/*` for the trial task.
- [ ] Verify feature push succeeds.
- [ ] Verify main/master push is denied.
- [ ] Verify unrelated repository access is denied.
- [ ] Capture the complete evidence trail.

### Task 5: Final verification

- [ ] Run the full test suite.
- [ ] Run isolated Docker tests.
- [ ] Run the real-agent trial twice to confirm repeatability and clean state.
- [ ] Review the diff and evidence.
- [ ] Request code review before merge.
