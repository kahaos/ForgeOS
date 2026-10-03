# ForgeOS real-agent trial harness

The real-agent trial harness is the bridge between the current scoped-authority prototype and an external autonomous coding-agent integration.

## What it proves

The MCP trial places Gemini CLI behind a real ForgeOS MCP stdio server. Every exposed operation is routed through the existing `RuntimeGateway` and signed `ExecutionWorker` path.

The trial exercises:

- task-scoped filesystem authority
- bounded workspace reads and writes
- governed test execution without an agent-supplied shell command
- Git status and commit authority
- feature-branch Git push authority
- repository and branch escape denial
- human approval for a separately scoped secret request
- signed governed execution
- append-only evidence

Gemini is configured with only the ForgeOS MCP server, an explicit tool allowlist, isolated CLI state, no built-in Gemini tools, and no provider credentials in the prompt or MCP configuration. Gemini's MCP documentation supports `mcp.allowed`, per-server `includeTools`, and a `trust` setting; this trial uses `trust: true` specifically so ForgeOS is the sole tool-execution gate rather than stacking a second confirmation dialog on top of ForgeOS. urlGemini CLI MCP configurationhttps://geminicli.com/docs/tools/mcp-server/

## What it deliberately does not do

The first real-agent harness does not contact GitHub, cloud providers, production systems, real secret stores, financial services, or deployment environments. Git uses a local bare remote and secret access is represented by an executor that never returns secret material.

This is intentional. The next stage is the disposable GitHub repository trial with a narrow repository credential.

## Run the MCP boundary tests

```bash
.venv/bin/python -m pytest \
  tests/test_mcp_server.py \
  tests/test_mcp_stdio.py \
  tests/test_agent_session.py \
  tests/test_real_agent_boundary.py \
  tests/test_gemini_trial_runner.py \
  tests/test_gemini_real_runtime.py \
  tests/test_gemini_mcp_runtime.py \
  tests/test_execution_path_hardening.py \
  tests/test_real_agent_trial.py \
  -q
```

## Prepare the disposable Gemini trial

From the ForgeOS repository root:

```bash
TRIAL=/opt/forgeos/gemini-controlplane-trial
rm -rf "$TRIAL"
mkdir -p "$TRIAL"

.venv/bin/python - <<'PY'
from pathlib import Path
from examples.run_gemini_forgeos_trial import build_mcp_server_command, write_gemini_settings

root = Path("/opt/forgeos/gemini-controlplane-trial")
server = Path.cwd() / "examples" / "forgeos_gemini_mcp_server.py"
write_gemini_settings(root, str(server))
print("settings:", root / "workspace/.gemini/settings.json")
print("server:", build_mcp_server_command(
    workspace=root / "workspace",
    state_dir=root / "state",
    task_id="real-agent-website-build",
    agent_id="website-agent",
))
PY
```

The generated project configuration binds the MCP server to the disposable workspace and state directory. It contains no provider API key, token, or secret.

## Launch Gemini

First verify the CLI is the expected installation:

```bash
gemini --version
```

Then launch only after the MCP boundary suite is green:

```bash
cd /opt/forgeos

TRIAL=/opt/forgeos/gemini-controlplane-trial

HOME="$TRIAL/home" \
GEMINI_CLI_HOME="$TRIAL/gemini-home" \
GEMINI_CLI_TRUST_WORKSPACE=true \
  gemini \
    --approval-mode default \
    --extensions none \
    --output-format text \
    --include-directories "$TRIAL/workspace" \
    "$(.venv/bin/python - <<'PY'
from examples.run_gemini_forgeos_trial import build_trial_prompt
print(build_trial_prompt('/opt/forgeos/gemini-controlplane-trial/workspace'))
PY
)"
```

Do **not** use Gemini YOLO mode for this trial. The intended authority chain is:

```text
Gemini
  -> ForgeOS MCP
  -> RuntimeGateway
  -> signed ExecutionAuthorization
  -> ExecutionWorker
  -> disposable workspace / local Git remote
```

## Expected evidence

At minimum, capture:

- tool discovery contains exactly the seven ForgeOS tools
- website files are created only inside the trial workspace
- tests execute through the fixed test adapter
- Git commit succeeds in the disposable repository
- `feature/*` push succeeds
- `main` / `master` push is denied before executor invocation
- unrelated repository access is denied
- secret request produces `ASK` and remains pending until explicit approval
- no provider credential appears in Gemini configuration, prompt, or tool result
- evidence contains the authorization and execution lifecycle

## Current status

The MCP server, stdio transport, session binding, real local adapters, Gemini launch configuration, and boundary tests are implemented. The remaining external validation is to run Gemini itself on the VPS and capture the observed autonomous website build. The GitHub disposable-repository trial follows that validation.
