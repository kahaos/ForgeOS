from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass(frozen=True)
class AgentRun:
    run_id: str
    project_id: str
    task: str
    base_commit: str
    workspace: str
    owner: str
    repo: str
    branch: str
    allowed_paths: List[str] = field(default_factory=list)
    forbidden_paths: List[str] = field(default_factory=list)
    required_stages: List[str] = field(default_factory=list)
    state: str = "READY"
    verdict: Optional[str] = None
    approval: Optional[str] = None
    changed_files: List[str] = field(default_factory=list)
    evidence_ids: List[str] = field(default_factory=list)
