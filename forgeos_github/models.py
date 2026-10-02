from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

@dataclass
class GitHubRepository:
    owner: str
    name: str
    repo_id: Optional[int] = None
    default_branch: str = "main"
    html_url: str = ""
    full_name: str = ""

@dataclass
class Project:
    project_id: str
    name: str
    description: str = ""
    workspace: str = ""
    policy: Dict[str, Any] = field(default_factory=dict)
    github: Optional[GitHubRepository] = None
    production_enabled: bool = False
    target: str = "local-test"
    created_at: str = ""

@dataclass
class ExecutionContract:
    contract_id: str
    project_id: str
    run_id: str
    task: str
    github_owner: str
    github_repo: str
    base_branch: str
    base_commit: str
    allowed_paths: List[str]
    forbidden_paths: List[str]
    required_stages: List[str]
    production_enabled: bool = False

    def to_dict(self):
        return asdict(self)
