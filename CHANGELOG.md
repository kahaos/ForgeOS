# Changelog

ForgeOS is an evolving open-source prototype. These entries record engineering milestones and demonstrated behaviour; they are not security certification or production-readiness claims.

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
