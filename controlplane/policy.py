"""Capability policy. Deny wins. Missing capability is deny. High-risk tools ask."""

from __future__ import annotations

from .models import ActionRequest, Agent, Decision

POLICY_VERSION = "controlplane-1.0"

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
