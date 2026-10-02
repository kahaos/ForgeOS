import json
import os
import re
import tempfile
from pathlib import Path
from .models import Project, GitHubRepository

class ProjectRegistry:
    """Persistent multi-project registry.

    Writes atomically and never stores GitHub credentials.
    """

    def __init__(self, root):
        self.root = Path(root)
        self.path = self.root / "projects.json"
        self.root.mkdir(parents=True, exist_ok=True)

    def _load(self):
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text())

    def _save(self, data):
        fd, tmp = tempfile.mkstemp(dir=self.root, prefix=".projects-", text=True)
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(data, f, indent=2, sort_keys=True)
                f.write("\n")
            os.replace(tmp, self.path)
        finally:
            if os.path.exists(tmp): os.unlink(tmp)

    def list(self):
        return list(self._load().values())

    def get(self, project_id):
        return self._load().get(project_id)

    def create(self, name, description="", workspace="", policy=None,
               github_owner=None, github_repo=None, default_branch="main",
               target="local-test", production_enabled=False):
        data = self._load()
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "project"
        i = 1
        project_id = f"proj-{slug}"
        while project_id in data:
            i += 1
            project_id = f"proj-{slug}-{i:02d}"
        gh = None
        if github_owner and github_repo:
            gh = GitHubRepository(owner=github_owner, name=github_repo,
                                  default_branch=default_branch,
                                  full_name=f"{github_owner}/{github_repo}")
        project = Project(
            project_id=project_id, name=name, description=description,
            workspace=workspace, policy=policy or {}, github=gh,
            production_enabled=production_enabled, target=target
        )
        record = project.__dict__.copy()
        if gh: record["github"] = gh.__dict__.copy()
        data[project_id] = record
        self._save(data)
        return record

    def bind_github(self, project_id, owner, repo, default_branch="main",
                    repo_id=None, html_url=""):
        data = self._load()
        if project_id not in data:
            raise KeyError(project_id)
        data[project_id]["github"] = {
            "owner": owner, "name": repo, "repo_id": repo_id,
            "default_branch": default_branch, "html_url": html_url,
            "full_name": f"{owner}/{repo}"
        }
        self._save(data)
        return data[project_id]

    def remove(self, project_id):
        data = self._load()
        if project_id not in data:
            raise KeyError(project_id)
        del data[project_id]
        self._save(data)
