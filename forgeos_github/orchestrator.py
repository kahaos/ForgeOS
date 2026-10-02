from .contract import build_execution_contract, validate_path

class GovernanceOrchestrator:
    """Backend-side gatekeeper for Git-backed agent execution.

    This class intentionally contains no human approval operation.
    """

    def __init__(self, github_provider):
        self.github = github_provider

    def snapshot_base(self, project):
        gh = project.github
        if gh is None:
            raise ValueError("project has no GitHub binding")
        branch = self.github.get_branch(gh.owner, gh.name, gh.default_branch)
        return branch["commit"]["sha"]

    def create_contract(self, project, run_id, task):
        return build_execution_contract(project, run_id, task, self.snapshot_base(project))

    def authorize_change(self, contract, path):
        return validate_path(path, contract.allowed_paths, contract.forbidden_paths)

    def repository_state(self, contract):
        return self.github.get_commit(
            contract.github_owner, contract.github_repo, contract.base_commit
        )

    def checks(self, contract, ref):
        return self.github.list_checks(contract.github_owner, contract.github_repo, ref)
