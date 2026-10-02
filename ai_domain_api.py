from project_domain import ProjectDomainStore, DomainError

def get(path, store, domain):
    if path == "/api/ai/v1/project":
        return 200, domain.inspect_project(store)
    if path.startswith("/api/ai/v1/experiments/"):
        experiment_id=path.rsplit("/",1)[-1]
        try:
            return 200, {
                "schema":"forgeos.ai.experiment.inspect.v1",
                "experiment":domain.inspect_experiment(store,experiment_id),
            }
        except DomainError as exc:
            return 404, {"schema":"forgeos.ai.error.v1","error":str(exc),"status":404}
    if path == "/api/ai/v1/domain/audit":
        return 200, {"schema":"forgeos.ai.project_domain_audit.v1","events":domain.audit()}
    return None

def post(path, body, store, domain):
    if path == "/api/ai/v1/experiments":
        try:
            return 201, domain.create_experiment(store,body)
        except DomainError as exc:
            return 409, {"schema":"forgeos.ai.error.v1","error":str(exc),"status":409}
    return None
