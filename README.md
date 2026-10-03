1. Product definition
ForgeOS is an AI agent control plane: an enforcement and evidence layer between autonomous AI agents and the tools, systems, data, accounts, and real-world actions they are allowed to touch.

The product is intended to let organizations run increasingly capable AI agents without giving those agents unrestricted authority. ForgeOS should make agent actions explicit, policy-controlled, approval-aware, attributable, and auditable.

Core model:

AI Agent
   |
   v
ForgeOS Control Plane
   | identity
   | capabilities
   | risk
   | policy
   | approval
   | evidence
   |
   v
Execution Gateway
   |
   v
Governed Executor / ForgeOS Alpha
   |
   v
Real target
ForgeOS is not an AI model and is not itself the autonomous agent. It governs what an agent is permitted to request and controls the path by which an approved operation can reach an executor.

2. Product objective
The long-term objective is a general-purpose control plane for AI workers, including coding agents, research agents, SEO agents, operations agents, business agents, and future multi-agent systems.

A ForgeOS-controlled agent should be able to work autonomously inside clearly defined boundaries while ForgeOS remains authoritative over sensitive actions.

The central product promise is:

Let AI agents act autonomously without giving them unrestricted authority.

3. Non-goals for this milestone
No production deployment integration.
No real secret retrieval.
No unrestricted shell access.
No real financial spending.
No agent-controlled policy modification.
No unrestricted agent creation.
No replacement of the existing ForgeOS Alpha governed execution lifecycle.
No second, parallel authorization system.
4. Architectural principles
4.1 ForgeOS is authoritative
Executors must not implement their own independent permission model. Sensitive operations enter through the ForgeOS authorization path.

4.2 Approval binds to the exact operation
A human approval is not a generic permission. It is bound to the exact request, agent snapshot, policy version, and execution binding.

4.3 Deny is terminal
A denied request must not reach an executor.

4.4 Approval is single-use
An approval must not be reusable for a second execution.

4.5 Evidence is first-class
Every meaningful authorization and execution transition should produce tamper-evident evidence and remain traceable to the originating request.

4.6 Fail closed
If an approval binding cannot be verified, if the executor binding is unavailable, or if policy/identity data has changed, ForgeOS must refuse execution rather than guess.

4.7 Separate control from execution
The control plane decides whether an operation may proceed. The execution boundary performs the operation. This separation becomes a security boundary as the system matures.

5. v1 approval API
Introduce a small HTTP API around the Control Plane:

POST /approvals/request
GET  /approvals/pending
GET  /approvals/{approval_id}
POST /approvals/{approval_id}/approve
POST /approvals/{approval_id}/deny
The API must expose the exact request being approved, its digest, agent identity/snapshot, policy version, target, status, timestamps, and evidence identifiers.

The approval API must call the existing ControlPlane.request() and ControlPlane.decide() paths rather than duplicating authorization logic.

The first implementation may use a local development server and JSON responses. Authentication and production transport hardening are later milestones, but the API shape should not require a second authorization model.

6. Live evidence artifact
Create a committed evidence record for the successful 2026-10-03 live Gemini Human Approval run.

It should document:

branch and commit under test
date/time
Gemini model
test agent identity
capabilities
each ALLOW / ASK / DENY operation
both human approval IDs
request digests
approval evidence digests
execution evidence digests
final event count
final evidence_ok state
the fact that Git push and secret access were simulated in this test
limitations of the current in-process boundary
The artifact is evidence of the prototype behaviour, not a claim of production security.

7. Execution boundary
Create a governed execution service/worker abstraction so the Gemini process is not itself the final trust boundary.

Initial design:

Gemini / other agent
        |
        | action request
        v
ForgeOS Gateway
        |
        +--> identity + capability + risk
        +--> policy
        +--> approval
        +--> evidence
        |
        | signed/bound execution authorization
        v
Execution Worker
        |
        +--> executor adapter
        v
     target system
The first worker should continue using safe/simulated executors. Real GitHub, secret, shell, network, and deployment adapters are separate follow-on work.

The worker must receive an execution authorization that is cryptographically or otherwise strongly bound to the original request and approval. It must reject altered requests, expired/replayed authorizations, mismatched agents, and mismatched targets.

8. Relationship with ForgeOS Alpha
The existing Alpha governed execution system remains part of ForgeOS.

Control Plane answers:

Is this agent allowed to request this operation, and does it require human approval?

Alpha answers:

Has this specific operation completed ForgeOS's governed lifecycle?

The intended lifecycle becomes:

agent
 -> request
 -> control-plane decision
 -> approval if required
 -> execution authorization
 -> Alpha verdict/release
 -> preflight
 -> execution
 -> verification
 -> rollback if required
 -> correlated evidence
9. Product documentation refresh
Update the repository documentation so it consistently describes ForgeOS as the AI agent control plane rather than as a historical Alpha patch package.

Documentation should include:

what ForgeOS is
why it exists
the control-plane architecture
agent identity and capabilities
ALLOW / ASK / DENY
human approval
evidence and auditability
relationship between Control Plane and Alpha
current status and demonstrated capabilities
known limitations
roadmap toward a secure multi-agent execution platform
clear distinction between prototype/simulated executors and future real integrations
The root README becomes the product-facing entry point. controlplane/README.md becomes the technical control-plane guide. Existing historical Alpha material should remain discoverable but clearly labelled as historical implementation/laboratory material.

10. Test strategy
Before merging implementation changes:

Unit-test request/API serialization and approval lifecycle.
Test API ALLOW / ASK / DENY behaviour through the real Control Plane.
Test approval tampering, capability drift, policy drift, executor substitution, replay, and single-use behaviour.
Test execution-worker rejection of invalid authorization bindings.
Run the existing Human Approval v1 regression suite.
Run the live Gemini test only with simulated sensitive executors.
Record a new evidence artifact after a successful live run.
Historical legacy UI test failures caused by missing unrelated patch artifacts remain separate from this milestone and must not be fabricated away.

11. Security hardening roadmap
After the v1 API and execution boundary:

authenticated agent identities
signed execution authorizations
durable approval/executor bindings across process restarts
secret isolation
sandbox/container isolation
network egress controls
replay protection with expiry/nonces
rate and budget controls
real Git/GitHub adapters
controlled filesystem and shell adapters
deployment environments with explicit gates
security/adversarial testing
policy version lifecycle and controlled policy administration
UI for live requests, approvals, executions, and evidence
multi-agent orchestration under the same control plane
12. Definition of success
This milestone succeeds when an AI agent can request a sensitive operation, ForgeOS can deterministically return ALLOW/ASK/DENY, a human can approve the exact request, only the exact approved operation can reach the execution worker, and the complete lifecycle can be reconstructed from tamper-evident evidence.

The system should then be capable of becoming the common enforcement layer for many agents and many tools without creating a separate permission model for each executor.
