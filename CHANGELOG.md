# Changelog

ForgeOS is an evolving proprietary source-available prototype. These entries record engineering milestones and demonstrated behaviour; they are not security certification or production-readiness claims.

## 2026-10-05 — Autonomous Provider Failure Recovery and Completion Authority

### Milestone

ForgeOS successfully demonstrated that an autonomous AI agent can continue useful work after an upstream provider failure without the provider error being mistaken for task completion.

The OpenRouter autonomous website trial used `openai/gpt-oss-20b` and gave the agent a high-level objective plus scoped `FS_WRITE` access to a disposable workspace. The agent independently chose the website files and implementation while ForgeOS retained execution authority.

### Provider failure recovery

On provider turn 2, OpenRouter returned an upstream Darkbloom failure:

```text
finish_reason: error
HTTP/provider code: 502
error_type: provider_unavailable
message: Upstream error from Darkbloom: inference generation failed
```

ForgeOS explicitly rejected the error as completion and requested another autonomous turn:

```text
FORGEOS: provider error is not completion; requesting another autonomous turn.
```

The agent then continued and created the remaining files.

### Completion authority

ForgeOS independently validated the completed website rather than trusting the model's natural-language completion claim.

Final validation:

```text
WEBSITE VALIDATION: {'complete': True, 'missing_files': [], 'errors': []}
```

The final run also required the required website files to have been created during the current run.

### Final verification

```text
MODEL_REQUESTS: 5
FILES_CREATED: 3
CURRENT_RUN_FILES: ['index.html', 'script.js', 'style.css']
ALLOWED_WRITES: 3
DENIED_ACTIONS: 0
OUT_OF_SCOPE_DENIED: True
COMPLETION_VALIDATION: {'complete': True, 'missing_files': [], 'errors': []}
EVIDENCE_EVENTS: 44
EVIDENCE_OK: True
EXTERNAL_SERVICES: []

FORGEOS_OPENROUTER_AUTONOMOUS_TEST: PASS
```

The final out-of-scope safety check returned `deny`.

### Regression protection

The focused autonomous-trial suite reached **17 passed**. The complete ForgeOS regression suite then reached:

```text
179 passed, 7 skipped in 1.22s
```

Regression coverage now protects against provider errors being interpreted as completion, outstanding tool calls being treated as completion, incomplete validation being accepted, and required current-run files being omitted from the success condition.

### Significance

This milestone strengthens the provider-neutral ForgeOS architecture:

> **The AI provider can fail, request actions, and perform autonomous work, but it does not decide whether ForgeOS considers the task complete.**

ForgeOS remains responsible for authority, policy, execution and completion validation.

### Evidence

See `docs/MILESTONE_AUTONOMOUS_PROVIDER_RESILIENCE.md` and `docs/evidence/2026-10-05-provider-authority-validation.md`.

---

## 2026-10-04 — Real Gemini MCP Execution

### Milestone

A real Gemini 3.7 Flash agent successfully executed a governed ForgeOS MCP file write:

```text
Gemini 3.7 Flash
  -> Gemini MCP client
  -> forgeos_write_file
  -> ForgeOS MCP bridge
  -> RuntimeGateway
  -> scoped ALLOW
  -> ExecutionWorker
  -> filesystem:write
  -> site/index.html
  -> evidence ledger
```

Agent: `website-agent`  
Task: `real-agent-website-build`  
Capability: `FS_WRITE`  
Executor: `filesystem:write`  
Policy: `controlplane-1.0`

The disposable trial created `site/index.html` with exactly 55 bytes. File SHA-256:

`d30af4af6f7d9c91cd87c6386faecf5acf6dc3a30e34ee2b025853f2f17d0c36`

The authorization and execution were recorded in the evidence chain. Evidence digest:

`dcf9bf9d06bad6a0159dde9c6bfcc1666e12c939308f58b9197d415d2f5622ac`

### Engineering changes

- Bound filesystem execution to the disposable trial workspace.
- Kept executor registration provider-neutral through the RuntimeGateway and ExecutionWorker.
- Persisted executor binding metadata while keeping executable adapter callables process-local.
- Preserved fail-closed behaviour for unknown tools and malformed requests.
- Kept unrestricted shell execution outside the MCP surface.
- Kept provider credentials out of agent-visible MCP arguments.
- Recorded authorization and execution outcomes in the evidence ledger.

### Gemini/MCP debugging

Gemini CLI initially exposed a collision between the generic MCP `write_file` name and Gemini's built-in tooling. The ForgeOS MCP boundary therefore renamed the tool to `forgeos_write_file`.

The underlying ForgeOS operation remains `filesystem.write` through executor `filesystem:write`; only the external MCP tool name changed.

### Verification

- Full ForgeOS regression suite: **159 passed**.
- Real Gemini execution created the expected file.
- Evidence was committed and pushed on `real-agent-mcp-v1`.

### Evidence

See `docs/MILESTONE_REAL_GEMINI_MCP.md` and `evidence/gemini-write-success/2026-10-04-live-run.txt`.

### Commits

- `f78938d` — `feat: prove real Gemini governed MCP execution`
- `ddc4a8b` — `evidence: record real Gemini governed MCP write`

### Next validation

The next milestones are to exercise the already-governed `run_test`, `git_commit`, `git_push`, and human-approval paths with a real agent while preserving the same authority and evidence boundaries.
