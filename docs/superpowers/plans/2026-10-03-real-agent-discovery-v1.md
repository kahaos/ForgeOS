# Real Agent and Public Discovery v1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make ForgeOS ready for a reproducible real coding-agent trial while turning the public GitHub repository into a clear discovery and conversion funnel for AI-agent security, authorization, governance, and control-plane users.

**Architecture:** The real-agent trial will use the existing ForgeOS control plane and execution boundary rather than introducing a parallel permission system. The agent-facing harness will be explicit about disposable workspaces and simulated/highly scoped targets, while the public documentation will expose the problem, architecture, reproducible evidence, limitations, and roadmap in focused pages.

**Tech Stack:** Python 3, pytest, existing ForgeOS ControlPlane/RuntimeGateway/ExecutionWorker, Markdown, GitHub repository metadata.

**Spec:** Approved design from the 2026-10-03 ForgeOS real-agent and public-discovery discussion.

## Global Constraints

- ForgeOS remains the authoritative authorization layer for governed operations.
- The first real-agent trial must not use production credentials, real financial spending, unrestricted secrets, or production deployment.
- The trial must use a disposable workspace/repository and task-scoped authority.
- Sensitive operations must continue through the existing governed execution path.
- Documentation must distinguish demonstrated prototype behaviour from future production integrations.
- SEO copy must target real search intent without keyword stuffing, fabricated claims, or unsupported rankings.
- Existing legacy/unscoped behaviour must remain compatible unless a test explicitly covers a scoped path.

## Review Focus

- Agent bypass: a real agent must not be able to invoke a sensitive executor outside ForgeOS.
- Scope escape: repository, branch, workspace, and capability boundaries must reject out-of-scope requests.
- Approval execution: ASK operations remain pending until the governed approval/worker path executes them.
- Public claims: README and docs must never imply production readiness where only simulated or isolated evidence exists.
- Discoverability quality: pages must have one clear audience/problem, descriptive titles, useful cross-links, and natural target terminology.

---

### Task 1: Build the reproducible real-agent trial harness

**Files:**
- Create: `examples/real_agent_trial.py`
- Create: `tests/test_real_agent_trial.py`
- Create: `docs/REAL_AGENT_TRIAL.md`

**Interfaces:**
- `build_trial_controlplane(state_dir: str | Path) -> ControlPlane`
- `run_trial(workspace: str | Path) -> dict[str, Any]`
- Trial result must expose deterministic `allow`, `deny`, and `ask` outcomes plus evidence identifiers.

- [ ] **Step 1: Write failing tests** proving the harness creates one disposable task, grants only feature-branch Git push plus workspace file operations, denies another repository/main branch, and requires approval for the simulated sensitive operation.
- [ ] **Step 2: Run `pytest tests/test_real_agent_trial.py -q` and verify failure.**
- [ ] **Step 3: Implement the harness using existing `ControlPlane`, `RuntimeGateway`, scoped tasks/grants, and the existing safe/simulated adapters. Do not add a second policy engine.
- [ ] **Step 4: Run the focused test and verify pass.**
- [ ] **Step 5: Run `python examples/real_agent_trial.py` and verify it prints the trial summary and evidence identifiers without contacting production services.**
- [ ] **Step 6: Commit `feat: add reproducible real agent trial harness`.**

### Task 2: Create public-facing security and architecture documentation

**Files:**
- Create: `docs/WHY_FORGEOS.md`
- Create: `docs/AI_AGENT_AUTHORIZATION.md`
- Create: `docs/MULTI_AGENT_SECURITY.md`
- Create: `docs/REAL_AGENT_QUICKSTART.md`
- Create: `docs/SECURITY_MODEL.md`

**Interfaces:**
- Each page has one discrete search/user intent and links to the relevant next page.
- `REAL_AGENT_QUICKSTART.md` links to the reproducible trial and clearly labels its safety limitations.

- [ ] **Step 1: Write documentation acceptance tests as a lightweight Python test that checks required titles, target phrases, relative links, and prototype/simulation limitation language.**
- [ ] **Step 2: Run the documentation test and verify it fails because the pages do not exist.**
- [ ] **Step 3: Create the five pages with descriptive titles and concise introductions aimed at developers/security/platform teams. Cover AI agent permissions, least privilege, task-scoped authorization, multi-agent delegation, human approval, evidence, execution boundaries, and current limitations.**
- [ ] **Step 4: Run the documentation test and verify pass.**
- [ ] **Step 5: Commit `docs: add AI agent security discovery guides`.**

### Task 3: Rewrite the root README as the product-facing discovery funnel

**Files:**
- Modify: `README.md`
- Create: `docs/ROADMAP.md`
- Create: `docs/EVIDENCE.md`

- [ ] **Step 1: Write a failing README structure/content test for the product description, audience terminology, real-agent trial link, security links, evidence link, quickstart, and explicit prototype limitations.**
- [ ] **Step 2: Run the focused documentation test and verify failure.**
- [ ] **Step 3: Rewrite README so the first screen explains ForgeOS as an AI agent control plane, the problem it solves, a concrete agent workflow, the 12-gate model, demonstrated evidence, quickstart, architecture, security model, roadmap, and contribution path. Remove duplicated internal specification material from the product-facing README while keeping technical details discoverable through docs.**
- [ ] **Step 4: Add `docs/ROADMAP.md` and `docs/EVIDENCE.md` with dated status and explicit separation between verified prototype capabilities and future integrations.**
- [ ] **Step 5: Run the documentation tests and full Python suite.**
- [ ] **Step 6: Commit `docs: reposition ForgeOS for AI agent security discovery`.**

### Task 4: Add repository discovery and contribution metadata

**Files:**
- Create: `.github/ISSUE_TEMPLATE/feature_request.md`
- Create: `.github/ISSUE_TEMPLATE/security_report.md`
- Create: `SECURITY.md`
- Create: `CONTRIBUTING.md`
- Create: `CITATION.cff`

- [ ] **Step 1: Write metadata/content tests for required headings, safe disclosure guidance, contribution instructions, and citation metadata.**
- [ ] **Step 2: Run tests and verify failure.**
- [ ] **Step 3: Add the metadata and contribution files with concise, public-project language.**
- [ ] **Step 4: Run tests and full suite.**
- [ ] **Step 5: Commit `docs: add public project contribution and security metadata`.**

### Task 5: Final verification and GitHub discovery configuration

**Files:**
- Modify: repository description/topics through GitHub repository metadata after code/docs are verified.

- [ ] **Step 1: Run the complete Python suite.**
- [ ] **Step 2: Run the real-agent trial harness locally and record its deterministic output.**
- [ ] **Step 3: Review changed documentation for broken relative links and unsupported claims.**
- [ ] **Step 4: Set a concise repository description and up to 20 relevant lowercase GitHub topics focused on AI-agent security, authorization, governance, runtime control, and multi-agent systems.**
- [ ] **Step 5: Create a pull request from `real-agent-discovery-v1` into `hardening-v1` for review.**
