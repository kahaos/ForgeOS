from __future__ import annotations
from pathlib import Path
from urllib.parse import urlparse
from .github_provider import GitHubAPIError, GitHubProvider
from .orchestrator import GovernanceOrchestrator
from .project_registry import ProjectRegistry
from .models import Project, GitHubRepository

PREFIX="/api/projects"
WEBHOOK_PATH="/api/github/webhook"

class GitHubIntegration:
    def __init__(self, root, provider=None):
        self.root=Path(root)
        self.registry=ProjectRegistry(self.root/"data"/"github_projects")
        self.provider=provider if provider is not None else GitHubProvider()
        self.orchestrator=GovernanceOrchestrator(self.provider)

    def _project_model(self, data):
        if isinstance(data, Project):
            return data

        d = dict(data)
        gh = d.get("github")

        github = None
        if gh:
            if isinstance(gh, GitHubRepository):
                github = gh
            else:
                github = GitHubRepository(
                    owner=str(gh.get("owner", "")),
                    name=str(gh.get("name", "")),
                    repo_id=gh.get("repo_id"),
                    default_branch=str(gh.get("default_branch", "main")),
                    html_url=str(gh.get("html_url", "")),
                    full_name=str(gh.get("full_name", "")),
                )

        return Project(
            project_id=str(d.get("project_id", "")),
            name=str(d.get("name", "")),
            description=str(d.get("description", "")),
            workspace=str(d.get("workspace", "")),
            policy=d.get("policy") or {},
            github=github,
            production_enabled=bool(d.get("production_enabled", False)),
            target=str(d.get("target", "local-test")),
            created_at=str(d.get("created_at", "")),
        )

    def _project_dict(self,p):
        if isinstance(p, dict):
            d=dict(p)
        else:
            d=dict(p.__dict__)

        if d.get("github") is not None:
            github=d["github"]
            if isinstance(github, dict):
                d["github"]=dict(github)
            else:
                d["github"]=dict(github.__dict__)

        return d

    def get(self,path):
        if path==PREFIX:
            return 200,{"schema":"forgeos.projects.v1","projects":[self._project_dict(p) for p in self.registry.list()]}
        if not path.startswith(PREFIX+"/"):
            return None
        parts=[x for x in path[len(PREFIX)+1:].split("/") if x]
        if not parts: return None
        p=self.registry.get(parts[0])
        if p is None: return 404,{"error":"project_not_found","project_id":parts[0]}
        project_model=self._project_model(p)
        if len(parts)==1:
            return 200,{"schema":"forgeos.project.v1","project":self._project_dict(p)}
        if parts[1]!="github": return 404,{"error":"not_found"}
        if len(parts)==3 and parts[2]=="repository":
            if not project_model.github: return 409,{"error":"github_not_bound"}
            return 200,{"schema":"forgeos.github.repository.v1","repository":dict(project_model.github.__dict__)}
        if not project_model.github: return 409,{"error":"github_not_bound"}
        if len(parts)==3 and parts[2]=="branches":
            return 200,{"schema":"forgeos.github.branches.v1","branches":self.provider.list_branches(project_model.github.owner,project_model.github.name)}
        if len(parts)==3 and parts[2]=="commits":
            return 200,{"schema":"forgeos.github.commits.v1","commits":self.provider.list_commits(project_model.github.owner,project_model.github.name)}
        if len(parts)==3 and parts[2]=="pulls":
            return 200,{"schema":"forgeos.github.pulls.v1","pulls":self.provider.list_pull_requests(project_model.github.owner,project_model.github.name)}
        if len(parts)==4 and parts[2]=="checks":
            return 200,{"schema":"forgeos.github.checks.v1","checks":self.provider.list_checks(project_model.github.owner,project_model.github.name,parts[3])}
        return 404,{"error":"not_found"}

    def post(self,path,body):
        body=body if isinstance(body,dict) else {}
        if path==PREFIX:
            name=str(body.get("name","")).strip()
            if not name: return 400,{"error":"name_required"}
            p=self.registry.create(
            name,
            description=str(body.get("description","")),
            workspace=str(body.get("workspace","")),
            policy=body.get("policy") or {},
            target=str(body.get("target","local-test")),
            production_enabled=False,
        )
            return 201,{"schema":"forgeos.project.v1","project":self._project_dict(p)}
        if path==WEBHOOK_PATH:
            return 202,{"schema":"forgeos.github.webhook.v1","status":"RECEIVED"}
        if not path.startswith(PREFIX+"/"): return None
        parts=[x for x in path[len(PREFIX)+1:].split("/") if x]
        p=self.registry.get(parts[0])
        if p is None: return 404,{"error":"project_not_found","project_id":parts[0]}
        project_model=self._project_model(p)
        if len(parts)==3 and parts[1]=="github" and parts[2]=="bind":
            owner=str(body.get("owner","")).strip(); repo=str(body.get("repo","")).strip()
            if not owner or not repo: return 400,{"error":"owner_and_repo_required"}
            remote=self.provider.get_repository(owner,repo)
            bound=self.registry.bind_github(parts[0],owner=owner,repo=repo,
                repo_id=remote.get("id"),default_branch=remote.get("default_branch","main"),
                html_url=remote.get("html_url",""))
            return 200,{"schema":"forgeos.project.v1","project":self._project_dict(bound)}
        if len(parts)==2 and parts[1]=="runs":
            run_id=str(body.get("run_id","")).strip(); task=str(body.get("task","")).strip()
            if not run_id or not task: return 400,{"error":"run_id_and_task_required"}
            if not project_model.github: return 409,{"error":"github_not_bound"}
            contract=self.orchestrator.create_contract(project_model,run_id,task)
            return 201,{"schema":"forgeos.execution_contract.v1","contract":contract.__dict__}
        if len(parts)==3 and parts[1]=="github" and parts[2]=="pulls":
            if not project_model.github: return 409,{"error":"github_not_bound"}
            result=self.provider.create_pull_request(
                project_model.github.owner,
                project_model.github.name,
                body.get("title",""),
                body.get("head",""),
                body.get("base",project_model.github.default_branch),
                body.get("body","")
            )
            return 201,{"schema":"forgeos.github.pull.v1","pull":result}
        return None

def build_integration(root): return GitHubIntegration(root)

def get(path,integration):
    try: return integration.get(urlparse(path).path)
    except GitHubAPIError as exc: return 502,{"error":"github_api_error","detail":str(exc)}
    except Exception as exc: return 500,{"error":"github_integration_error","detail":str(exc)}

def post(path,body,integration):
    try: return integration.post(urlparse(path).path,body)
    except GitHubAPIError as exc: return 502,{"error":"github_api_error","detail":str(exc)}
    except Exception as exc: return 500,{"error":"github_integration_error","detail":str(exc)}
