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

Gemini is configured with only the ForgeOS MCP server, an explicit tool allowlist, isolated CLI state, no built-in Gemini tools, and no provider credentials in the prompt or MCP configuration. Gemini's MCP documentation supports `mcp.allowed`, per-server `includeTools`, and a `trust` setting; this trial keeps `trust: false` so the MCP server is not treated as inherently trusted by Gemini, while ForgeOS remains the authoritative policy and approval boundary for tool execution. urlGemini CLI MCP configurationhttps://geminicli.com/docs/tools/mcp-server/

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

The runner now performs the preparation step itself. From the ForgeOS repository root:

```bash
.venv/bin/python examples/run_gemini_forgeos_trial.py --prepare-only
```

By default this prepares:

```text
/opt/forgeos/gemini-controlplane-trial/
├── workspace/
│   └── .gemini/settings.json
├── state/
├── home/
└── gemini-home/
```

The generated project configuration binds the MCP server to the disposable workspace and state directory. It contains no provider API key, token, or secret. The runner also removes `GEMINI_API_KEY`, `GOOGLE_API_KEY`, and `GOOGLE_APPLICATION_CREDENTIALS` from the Gemini process environment unless the operator explicitly selects an authentication mode.

Use `--trial-root` to select another disposable location:

```bash
.venv/bin/python examples/run_gemini_forgeos_trial.py \
  --trial-root /opt/forgeos/gemini-controlplane-trial \
  --prepare-only
```

## Launch Gemini with an API key

The failed personal-Google login should not be worked around by weakening ForgeOS. Gemini CLI's current authentication documentation supports API-key authentication for headless operation, using `GEMINI_API_KEY`. urlGemini CLI authentication setuphttps://geminicli.com/docs/get-started/authentication/

Keep the API key outside the repository and outside the trial files. Export it only in the shell that launches the trial:

```bash
export GEMINI_API_KEY='YOUR_GEMINI_API_KEY'
```

Then explicitly select API-key authentication:

```bash
cd /opt/forgeos/hardening-v1-trial

/opt/forgeos/.venv/bin/python \
  examples/run_gemini_forgeos_trial.py \
  --trial-root /opt/forgeos/gemini-controlplane-trial \
  --provider-auth gemini-api-key
```

The runner passes `GEMINI_API_KEY` only to the Gemini subprocess. It does **not** put the key into `settings.json`, command-line arguments, ForgeOS MCP configuration, or evidence output. The generated Gemini settings explicitly select `gemini-api-key`, preventing the CLI from asking for Google OAuth during the trial.

If `GEMINI_API_KEY` is not present, the runner stops with an error rather than launching Gemini without a known authentication method.

## Launch Gemini without provider credentials

For preparation-only checks or environments where authentication is already cached inside the isolated Gemini home, omit `--provider-auth`. Credentials are stripped from the subprocess environment by default.

## Launch Gemini

First verify the CLI is the expected installation:

```bash
gemini --version
```

Do **not** use Gemini YOLO mode for this trial. The runner uses `--approval-mode default`, disables built-in Gemini tools, and exposes only the seven ForgeOS MCP tools. Gemini's CLI documentation identifies `default` as the approval mode that prompts for tool calls, while `yolo` automatically approves all tool calls. urlGemini CLI configurationhttps://geminicli.com/docs/reference/configuration/

The intended authority chain is:

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

The MCP server, stdio transport, session binding, real local adapters, executable Gemini trial harness, isolated runtime preparation, explicit API-key authentication path, and boundary tests are implemented. The remaining external validation is to run the API-key-authenticated harness on the VPS and capture the observed autonomous website build. The GitHub disposable-repository trial follows that validation.
