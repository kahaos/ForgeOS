"""AI-native governed execution HTTP adapter for PATCH-013C."""
from governed_execution import GovernedExecutionError

PREFIX="/api/ai/v1/"

def _json_error(code, detail, status=409):
    return status, {"schema":"forgeos.ai.error.v1","error":code,"detail":detail}

def get(path, store, execution):
    if path == PREFIX+"execution":
        project = store.state()
        execution_state = execution._state()
        project_execution = execution_state.get("projects", {}).get(
            project.get("project_id"), {}
        )
        return 200, {"schema":"forgeos.ai.execution_context.v1",
                      "project_id":project.get("project_id"),
                      "lifecycle":project.get("state"),
                      "target":project.get("target"),
                      "production_enabled":False,
                      "governance_authoritative":True,
                      "release":project_execution.get("release"),
                      "approval_request":project_execution.get("approval_request"),
                      "preflight":project_execution.get("preflight"),
                      "capabilities":["evidence.submit","verdict.create","approval.request","approval.approve",
                                      "release.create","deployment.preflight",
                                      "deployment.execute","deployment.verify","rollback.request"]}
    if path == PREFIX+"execution/audit":
        return 200, {"schema":"forgeos.ai.execution_audit.v1","events":execution.audit()}
    return None

def post(path, body, store, execution, approval):
    try:
        if path==PREFIX+"evidence":
            return 201, execution.submit_evidence(body["project_id"],body["experiment_id"],body["content"],body.get("actor","ai"))
        if path==PREFIX+"verdict":
            return 201, execution.create_verdict(body["project_id"],body["evidence_id"],body["verdict"],body.get("rationale",""),body.get("actor","ai"))
        if path==PREFIX+"approval/request":
            return 201, execution.request_approval(body["project_id"],body["release_id"],body["target"],body["verdict_id"],body.get("actor","ai"))
        if path==PREFIX+"approval/approve":
            return 200, execution.approve_release(
                body["project_id"],
                body["release_id"],
                body["target"],
                body["verdict_id"],
                body.get("approved_by") or body.get("actor"),
            )
        if path==PREFIX+"release":
            return 201, execution.create_release(body["project_id"],body["release_id"],body["verdict_id"],body["target"],body.get("actor","ai"))
        if path==PREFIX+"deployment/preflight":
            return 200, execution.mark_preflight(body["project_id"],body["release_id"],body["target"],body.get("actor","system"))
        if path==PREFIX+"deployment/execute":
            # Execution requires a prior backend-approved lifecycle state and preflight.
            rec=execution.deploy_local_test(body["project_id"],body["release_id"],body["target"],body.get("actor","system"))
            return 200, rec
        if path==PREFIX+"deployment/verify":
            return 200, execution.verify(body["project_id"],body["receipt"],body.get("actor","system"))
        if path==PREFIX+"rollback":
            return 200, execution.rollback(body["project_id"],body["release_id"],body.get("reason","unspecified"),body.get("actor","human"))
        return None
    except KeyError as exc:
        return _json_error("required_field_missing",str(exc),400)
    except GovernedExecutionError as exc:
        return _json_error("governed_execution_blocked",str(exc),409)
