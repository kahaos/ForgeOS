"""
ForgeOS PATCH-013B — Project Domain
Governed project/experiment domain operations for the AI API.

This layer deliberately does not expose generic lifecycle transitions.
"""
import hashlib, json
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "forgeos.ai.project_domain.v1"
AUDIT_SCHEMA = "forgeos.ai.project_domain_event.v1"

def now():
    return datetime.now(timezone.utc).isoformat()

def digest(obj):
    raw=json.dumps(obj,sort_keys=True,separators=(",",":")).encode()
    return hashlib.sha256(raw).hexdigest()

class DomainError(ValueError):
    pass

class ProjectDomainStore:
    def __init__(self, root):
        self.root=Path(root)
        self.data=self.root/"data"/"ai_project_domain.json"
        self.audit_file=self.root/"data"/"ai_project_domain_audit.jsonl"
        self.data.parent.mkdir(parents=True,exist_ok=True)

    def _load(self):
        if not self.data.exists():
            return {"schema":SCHEMA,"projects":{},"experiments":{}}
        return json.loads(self.data.read_text())

    def _save(self, data):
        data["updated_at"]=now()
        data["digest"]=digest(data)
        tmp=self.data.with_suffix(".tmp")
        tmp.write_text(json.dumps(data,indent=2,sort_keys=True))
        tmp.replace(self.data)

    def _audit(self, action, actor, payload):
        event={
            "schema":AUDIT_SCHEMA,
            "action":action,
            "actor":actor,
            "timestamp":now(),
            "payload":payload,
        }
        event["event_digest"]=digest(event)
        with self.audit_file.open("a") as f:
            f.write(json.dumps(event,sort_keys=True)+"\n")
        return event

    def inspect_project(self, store):
        state=store.state()
        project_id=state["project_id"]
        data=self._load()
        record=data["projects"].get(project_id)
        return {
            "schema":"forgeos.ai.project.v1",
            "project_id":project_id,
            "name":state["name"],
            "target":state.get("target"),
            "lifecycle":state["state"],
            "current_release":state.get("current_release"),
            "experiment_count":sum(1 for e in data["experiments"].values() if e["project_id"]==project_id),
            "record":record,
        }

    def create_experiment(self, store, body, actor="ai"):
        state=store.state()
        if state["state"] != "EXPERIMENTING":
            raise DomainError(f"experiment_create_requires_EXPERIMENTING:{state['state']}")

        project_id=body.get("project_id")
        if project_id != state["project_id"]:
            raise DomainError("project_binding_mismatch")

        experiment_id=body.get("experiment_id")
        name=body.get("name")
        if not isinstance(experiment_id,str) or not experiment_id.strip():
            raise DomainError("experiment_id_required")
        if not isinstance(name,str) or not name.strip():
            raise DomainError("experiment_name_required")

        data=self._load()
        if experiment_id in data["experiments"]:
            raise DomainError("experiment_exists")

        record={
            "schema":"forgeos.ai.experiment.v1",
            "experiment_id":experiment_id,
            "project_id":project_id,
            "name":name.strip(),
            "description":body.get("description",""),
            "status":"CREATED",
            "created_by":actor,
            "created_at":now(),
        }
        record["digest"]=digest(record)
        data["experiments"][experiment_id]=record
        self._save(data)
        event=self._audit("EXPERIMENT_CREATED",actor,{
            "project_id":project_id,
            "experiment_id":experiment_id,
            "experiment_digest":record["digest"],
        })
        return {"experiment":record,"event":event}

    def inspect_experiment(self, store, experiment_id):
        data=self._load()
        record=data["experiments"].get(experiment_id)
        if record is None:
            raise DomainError("experiment_not_found")
        if record["project_id"] != store.state()["project_id"]:
            raise DomainError("project_binding_mismatch")
        return record

    def audit(self):
        if not self.audit_file.exists():
            return []
        return [json.loads(x) for x in self.audit_file.read_text().splitlines() if x.strip()]
