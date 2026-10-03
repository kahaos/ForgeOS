"""Safe ForgeOS scoped-authority multi-agent demonstration.

All execution is simulated; provider-native credentials and production systems are
intentionally absent from this example.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile

from controlplane.execution_worker import ExecutionWorker
from controlplane.gateway import RuntimeGateway, SimulatedToolAdapter
from controlplane.store import ControlPlane


KEY = b"forgeos-demo-key"


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="forgeos-scoped-demo-") as td:
        cp = ControlPlane(Path(td) / "controlplane")
        cp.register("website-agent", "human", ["GIT_PUSH", "GIT_COMMIT"])
        cp.register("seo-agent", "human", ["GIT_COMMIT"])
        cp.register("deployment-agent", "human", ["PRODUCTION_DEPLOY"])

        expires = (datetime.now(timezone.utc) + timedelta(hours=4)).isoformat()
        cp.create_task("website-build", "human", "Build company website", expires)
        cp.issue_grant(
            "website-build", "website-agent", "GIT_PUSH",
            {"tool": "git", "action": "push", "repository": "company/site", "branch": "feature/*"},
            "human", expires,
        )
        cp.issue_grant(
            "website-build", "seo-agent", "GIT_COMMIT",
            {"tool": "git", "action": "commit", "repository": "company/site", "branch": "feature/*"},
            "human", expires,
        )
        cp.issue_grant(
            "website-build", "deployment-agent", "PRODUCTION_DEPLOY",
            {"tool": "deploy", "action": "production", "environment": "production", "resource": "company/site"},
            "human", expires,
        )

        worker = ExecutionWorker(cp, KEY)
        gateway = RuntimeGateway(cp, worker, KEY)
        gateway.register_adapter("git:push", "company/site", SimulatedToolAdapter("git-push"))
        gateway.register_adapter("git:commit", "company/site", SimulatedToolAdapter("git-commit"))
        gateway.register_adapter("deploy:production", "company/site", SimulatedToolAdapter("production-deploy"))

        print("FEATURE PUSH:", gateway.request("website-build", "website-agent", "git", "push", "company/site", {"branch": "feature/home"})["verdict"])
        print("MAIN PUSH:", gateway.request("website-build", "website-agent", "git", "push", "company/site", {"branch": "main"})["verdict"])
        print("SEO REPO ESCAPE:", gateway.request("website-build", "seo-agent", "git", "commit", "company/other", {"branch": "feature/seo"})["verdict"])
        print("AUTHORITY GRAPH:", cp.authority_graph("website-build"))


if __name__ == "__main__":
    main()
