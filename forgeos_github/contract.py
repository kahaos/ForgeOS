import fnmatch
import hashlib
import json
from pathlib import PurePosixPath
from .models import ExecutionContract

REQUIRED_STAGES = [
    "INSPECT", "PROPOSE", "SCOPE_CHECK", "CHANGE", "TEST",
    "EVIDENCE", "VERDICT", "RELEASE", "APPROVAL_REQUEST"
]

def _clean(path):
    return str(PurePosixPath(path)).lstrip("./")

def validate_path(path, allowed_paths, forbidden_paths):
    # PATCH-019.1 PATH_TRAVERSAL_GUARD
    if not isinstance(path, str) or not path:
        return False, "INVALID_PATH"

    candidate = path.replace("\\\\", "/")

    # Repository paths must be relative and must never contain
    # parent-directory components.
    if candidate.startswith("/"):
        return False, "PATH_TRAVERSAL"

    if ".." in candidate.split("/"):
        return False, "PATH_TRAVERSAL"

    p = _clean(path)
    if p.startswith("../") or "/../" in f"/{p}" or p == "..":
        return False, "PATH_TRAVERSAL"
    for rule in forbidden_paths:
        if fnmatch.fnmatch(p, _clean(rule)):
            return False, "FORBIDDEN_PATH"
    if not any(fnmatch.fnmatch(p, _clean(rule)) or
               fnmatch.fnmatch(p, _clean(rule).rstrip("/") + "/**")
               for rule in allowed_paths):
        return False, "OUT_OF_SCOPE"
    return True, "ALLOWED"

def build_execution_contract(project, run_id, task, base_commit):
    gh = project.github
    if gh is None:
        raise ValueError("GitHub repository must be bound before creating an execution contract")
    policy = project.policy or {}
    allowed = policy.get("allowed_paths", ["**"])
    forbidden = policy.get("forbidden_paths", [
        ".env", ".env.*", "secrets/**", ".git/**", ".github/workflows/**"
    ])
    payload = {
        "project_id": project.project_id, "run_id": run_id, "task": task,
        "github": f"{gh.owner}/{gh.name}", "base_commit": base_commit,
        "allowed_paths": allowed, "forbidden_paths": forbidden,
        "required_stages": REQUIRED_STAGES
    }
    cid = "contract-" + hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode()
    ).hexdigest()[:16]
    return ExecutionContract(
        contract_id=cid, project_id=project.project_id, run_id=run_id,
        task=task, github_owner=gh.owner, github_repo=gh.name,
        base_branch=gh.default_branch, base_commit=base_commit,
        allowed_paths=allowed, forbidden_paths=forbidden,
        required_stages=REQUIRED_STAGES.copy(),
        production_enabled=project.production_enabled
    )
