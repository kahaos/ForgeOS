# PATCH-013B — Project Domain

## Purpose
Add first governed domain operations beneath the AI interface without exposing generic lifecycle mutation.

## Enabled
- `GET /api/ai/v1/project` — inspect current project
- `POST /api/ai/v1/experiments` — create an experiment, only while lifecycle is `EXPERIMENTING`
- `GET /api/ai/v1/experiments/{experiment_id}` — inspect a project-bound experiment
- `GET /api/ai/v1/domain/audit` — inspect domain audit events

## Invariants
- AI does not become governance authority.
- Project ID supplied by the caller must equal the authoritative current project.
- Experiment creation is denied outside `EXPERIMENTING`.
- Duplicate experiment IDs are rejected.
- Generic `/api/transition` remains outside the AI domain API.
- Approval, release, deployment, monitoring and rollback remain unavailable.
- Production remains disabled.
- Domain writes have an append-only audit event and object digest.
- Authentication/authorization for external users remains a prerequisite before exposing mutating AI operations beyond the trusted local baseline.

## Security basis
Object/function authorization should be explicit at every object/function boundary; OWASP identifies object-level and function-level authorization as distinct API risks.
