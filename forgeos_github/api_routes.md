# PATCH-019 API integration contract

These routes are intentionally documented separately from the frozen PATCH-018 handlers.
Wire them into the existing server only after the PATCH-019 tests pass.

## Projects

POST `/api/projects`

```json
{
  "name": "Calculator",
  "description": "Demo project",
  "workspace": "/opt/forgeos/workspaces/calculator",
  "github": {
    "owner": "OWNER",
    "repo": "calculator",
    "default_branch": "main"
  },
  "policy": {
    "allowed_paths": ["src/**", "tests/**"],
    "forbidden_paths": [".env", ".github/workflows/**", ".git/**"]
  }
}
```

GET `/api/projects`

GET `/api/projects/{project_id}`

POST `/api/projects/{project_id}/github/bind`

POST `/api/projects/{project_id}/runs`

## GitHub

GET `/api/projects/{project_id}/github/repository`

GET `/api/projects/{project_id}/github/branches`

GET `/api/projects/{project_id}/github/commits`

GET `/api/projects/{project_id}/github/pulls`

POST `/api/projects/{project_id}/github/pulls`

GET `/api/projects/{project_id}/github/checks/{ref}`

POST `/api/projects/{project_id}/github/webhook`

POST `/api/github/webhook`

## Governance invariants

1. No GitHub credential is stored in project JSON.
2. Every run captures the exact base commit.
3. Every agent change is checked against the execution contract.
4. Forbidden/out-of-scope paths are backend-blocked.
5. Human approval remains outside the agent capability set.
6. A GitHub PR/merge is evidence about repository state; it is not itself ForgeOS approval.
7. Production remains disabled unless explicitly enabled by a future production patch.
