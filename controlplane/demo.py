"""Milestone 1 demo: register, allow, deny, ask, approve, verify evidence."""

from pathlib import Path
import tempfile

from controlplane import ControlPlane


def run(root: Path | None = None) -> dict:
    root = root or Path(tempfile.mkdtemp(prefix="forgeos-cp-"))
    cp = ControlPlane(root)
    cp.register(
        "codex-builder",
        owner="kahaos",
        capabilities=["FS_READ", "FS_WRITE", "GIT_COMMIT", "GIT_PUSH", "GITHUB_READ", "GITHUB_WRITE", "SHELL"],
        risk_level="medium",
    )

    allowed = cp.request("codex-builder", "filesystem", "write", target="/workspace/app.py")
    denied_spawn = cp.request("codex-builder", "agent", "create", target="seo-agent")
    denied_spend = cp.request("codex-builder", "funds", "spend", target="gbp:500")
    denied_secret = cp.request("codex-builder", "secrets", "read", target="prod.env")
    asked = cp.request("codex-builder", "git", "push", target="forgeos-community@main")
    approved = cp.decide(asked["approval_id"], approve=True, actor="kahaos")

    snap = cp.snapshot()
    assert allowed["verdict"] == "allow", allowed
    assert denied_spawn["verdict"] == "deny", denied_spawn
    assert denied_spend["verdict"] == "deny", denied_spend
    assert denied_secret["verdict"] == "deny", denied_secret
    assert asked["verdict"] == "ask", asked
    assert approved["verdict"] == "allow", approved
    assert snap["evidence_ok"] is True
    assert snap["pending"] == []
    return {"root": str(root), "allow": allowed, "deny_spawn": denied_spawn, "deny_spend": denied_spend, "deny_secret": denied_secret, "ask": asked, "approved": approved, "evidence_ok": snap["evidence_ok"], "events": snap["events"]}


if __name__ == "__main__":
    import json
    print(json.dumps(run(Path("/tmp/forgeos-cp-demo")), indent=2))
