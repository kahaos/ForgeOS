# ForgeOS roadmap

ForgeOS is being developed as an AI agent control plane: a shared authorization and governed-execution layer for autonomous agents and the tools they use.

## Current: hardened scoped-authority prototype

Verified in the current development track:

- task-scoped capability grants
- resource and branch scoping
- multi-agent authority separation
- attenuating delegation
- ALLOW / ASK / DENY decisions
- exact-request human approval
- signed execution authorizations
- single-use execution nonces
- replay/tamper/state-drift protections
- Docker-backed isolated worker tests
- provider-neutral Runtime Gateway
- reproducible real-agent-shaped trial harness using safe simulated adapters
- real Gemini MCP execution through the governed ForgeOS boundary

## Next: multi-provider agent support

ForgeOS should evolve from a Gemini proof into a provider-neutral authority layer that can govern agents regardless of the underlying model/provider.

Priority provider integrations:

- Gemini — current real-agent integration
- Anthropic / Claude
- OpenAI / ChatGPT
- xAI / Grok
- additional major providers and OpenAI-compatible/local models where practical

The architecture should use a common agent-adapter/runtime interface so provider-specific integrations remain thin while identity, task scope, policy, approval, execution authority, and evidence remain ForgeOS responsibilities.

## Next: first serious application integration — GitHub

GitHub is a priority application/tool integration because coding agents routinely need repository access and consequential operations.

Planned governed capabilities include:

- repository read access
- branch creation and changes
- commits
- pull requests
- code review operations
- Git push
- GitHub Actions / CI interaction
- merge operations
- release/deployment actions where supported

High-impact operations should be capable of triggering ForgeOS ALLOW / ASK / DENY policy decisions and exact human approval. The goal is to demonstrate that different AI agents can use the same external systems while ForgeOS remains the authority boundary.

## New product capability: ForgeOS Task Reports & Notifications

Every meaningful governed agent task should eventually produce a human-readable task report that translates machine activity into an understandable record of what the AI actually did.

### Task identity

Each task should receive a persistent ForgeOS task identifier, for example:

`FOS-2026-10-04-8A42C1`

The task record should connect the full lifecycle:

- original user request
- agent/provider identity
- task start and completion time
- duration
- actions requested and executed
- ALLOW / ASK / DENY decisions
- human approvals and denials
- policies applied and policy version
- tools and external applications used
- files/resources changed
- Git commits and SHA identifiers
- tests and verification results
- errors and failures
- execution/result data
- evidence and integrity metadata

### Human-readable completion report

For non-technical users, ForgeOS should turn the underlying evidence into a clear summary such as:

> Gemini completed your website task in 25 minutes. 20 files were changed, 4 commits were created, automated tests passed, and a pull request was opened.

The report should provide both:

- **Simple view** — plain-English explanation of what happened
- **Detailed/technical view** — files, commits, SHAs, policies, approvals, evidence and execution details

### Notifications

Initial notification target:

- email on task completion
- email when human approval is required
- email when a consequential operation is denied
- links back to the ForgeOS task record and relevant GitHub resources

The notification system should be provider/channel-neutral so it can later support:

- email
- dashboard notifications
- Slack / Teams
- webhooks
- API consumers
- mobile notifications

The underlying **Task Ledger** should remain the source of truth; notifications are a presentation/delivery layer over that record.

### Example completion record

```text
ForgeOS Task: FOS-2026-10-04-8A42C1
Agent:         Gemini
Task:          Build business website
Started:       18:42
Completed:     19:07
Duration:      25 minutes
Status:        COMPLETED

Changes:
  20 files changed
  +1,842 lines
  -127 lines
  4 commits

Verification:
  Tests: PASSED
  Pull request: CREATED

Evidence:
  Policy: controlplane-1.0
  Approvals: 2 requested / 2 approved
  Git SHA: a81f3c7...

ForgeOS task ID provides the permanent audit reference.
```

## v1.2 security foundation

Planned work includes:

- authenticated human and agent principals
- OIDC/JWT or deployment-appropriate identity integration
- race-safe authorization and approval transactions
- durable transactional state
- stronger policy version lifecycle
- provider-specific credential binding
- controlled Git/GitHub adapters
- network egress policy
- secret isolation

## Platform stage

Longer-term work can add:

- production GitHub/cloud adapters
- deployment environments with explicit release gates
- live control console
- evidence search and audit workflows
- task history and Task Ledger UI
- human-readable task reports
- email and other notification channels
- budgets and rate limits
- multi-agent orchestration
- policy administration with protected change control
- integrations with agent runtimes and tool protocols
- additional high-value application integrations such as Slack, Jira, Notion, Google Drive, cloud infrastructure, CI/CD and databases

## Product direction

The long-term product goal is not to make ForgeOS another AI agent. It is to make ForgeOS the **runtime authority layer for autonomous AI agents**.

The model/provider should be replaceable. The tools and applications should be extensible. ForgeOS should remain responsible for identity, authority, policy, risk, approval, governed execution, evidence, and the human-readable record of what an agent did.

Roadmap items are targets, not claims that those capabilities are already production-ready.
