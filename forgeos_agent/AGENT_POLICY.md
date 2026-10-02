# PATCH-020 Agent Boundary

ForgeOS is the authority. Agents receive only registered run-scoped tools.

- A run is bound to one project and one exact Git commit.
- File access is relative to that run's isolated workspace.
- Paths are checked against the run's allowed/forbidden policy before filesystem access.
- Commands are allow-listed and shell chaining/redirection is rejected.
- Agent tools cannot approve releases or deploy production.
- Human approval is a separate API operation.
- GitHub credentials are read from `FORGEOS_GITHUB_TOKEN` and are never persisted in project/run JSON.
- GitHub PR state is repository evidence, not ForgeOS approval.
