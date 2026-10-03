"""ForgeOS policy: legacy flat capabilities plus task-scoped authority."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence

from .authority import CapabilityGrant, Task
from .models import ActionRequest, Agent, Decision

POLICY_VERSION = "controlplane-1.0"
SCOPED_POLICY_VERSION = "controlplane-scoped-authority-1.0"

REQUIRED = {
    ("filesystem", "read"): "FS_READ",
    ("filesystem", "write"): "FS_WRITE",
    ("git", "commit"): "GIT_COMMIT",
    ("git", "push"): "GIT_PUSH",
    ("github", "read"): "GITHUB_READ",
    ("github", "write"): "GITHUB_WRITE",
    ("shell", "exec"): "SHELL",
    ("network", "request"): "NETWORK",
    ("deploy", "production"): "PRODUCTION_DEPLOY",
    ("agent", "create"): "CREATE_AGENT",
    ("funds", "spend"): "SPEND_FUNDS",
    ("policy", "modify"): "MODIFY_POLICY",
    ("secrets", "read"): "READ_SECRETS",
}

ASK = {
    ("git", "push"),
    ("deploy", "production"),
    ("agent", "create"),
    ("funds", "spend"),
    ("policy", "modify"),
    ("secrets", "read"),
}

HARD_DENY = {
    ("policy", "modify"),
    ("agent", "create"),
    ("funds", "spend"),
}


def evaluate(agent: Agent, request: ActionRequest) -> Decision:
    key = (request.tool, request.action)
    needed = REQUIRED.get(key)
    if needed is None:
        return Decision("deny", f"unknown action {request.tool}.{request.action}", request)
    if key in HARD_DENY:
        return Decision("deny", f"agent does not possess {needed}; this action cannot be self-granted", request)
    if needed not in agent.capabilities:
        return Decision("deny", f"missing capability {needed}", request)
    if key in ASK or agent.risk_level in ("high", "critical") and request.tool in ("git", "deploy", "shell"):
        return Decision("ask", f"{needed} present; human approval required", request)
    return Decision("allow", f"{needed} present", request)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def evaluate_scoped(agent: Agent, task: Task | None, grants: Sequence[CapabilityGrant], request: ActionRequest) -> object:
    from .authority import AuthorityDecision

    if task is None:
        return AuthorityDecision("deny", "unknown task", request)
    if agent.status != "registered":
        return AuthorityDecision("deny", "agent is not active", request, task_id=task.task_id)
    if not task.active(_now()):
        return AuthorityDecision("deny", "task is expired or revoked", request, task_id=task.task_id)

    needed = REQUIRED.get((request.tool, request.action))
    if needed is None:
        return AuthorityDecision("deny", f"unknown action {request.tool}.{request.action}", request, task_id=task.task_id)
    if (request.tool, request.action) in HARD_DENY:
        return AuthorityDecision("deny", f"{needed} is hard-denied by policy", request, task_id=task.task_id)

    matching = [g for g in grants if g.capability == needed and g.policy_version == POLICY_VERSION and g.active(_now()) and g.scope.matches(request)]
    if not matching:
        return AuthorityDecision("deny", f"no scoped authority for {needed}", request, task_id=task.task_id)

    grant = sorted(matching, key=lambda item: item.grant_id)[0]
    key = (request.tool, request.action)
    branch = str(request.detail.get("branch", ""))
    production_branch = branch in {"main", "master", "production"}
    consequential = key in {("deploy", "production"), ("secrets", "read"), ("policy", "modify"), ("agent", "create"), ("funds", "spend")}
    if consequential or (key == ("git", "push") and production_branch):
        return AuthorityDecision("ask", f"{needed} present within scope; human approval required", request, grant.grant_id, task.task_id)
    if agent.risk_level in ("high", "critical") and request.tool in ("git", "deploy", "shell"):
        return AuthorityDecision("ask", f"{needed} present within scope; agent risk requires approval", request, grant.grant_id, task.task_id)
    return AuthorityDecision("allow", f"{needed} present within task scope", request, grant.grant_id, task.task_id)
