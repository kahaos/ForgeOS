from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json

class ApprovalError(Exception):
    pass

def now():
    return datetime.now(timezone.utc).isoformat()

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()

def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()

class ApprovalGate:
    SCHEMA = "forgeos.approval.v1"
    def __init__(self, root, store):
        self.root = Path(root)
        self.store = store
        self.file = self.root / "data" / "approval.json"
        self.audit_file = self.root / "data" / "approval_audit.jsonl"
    def _read(self):
        if not self.file.exists(): return None
        return json.loads(self.file.read_text())
    def _write(self, value):
        self.file.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.file.with_suffix(".tmp")
        tmp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
        tmp.replace(self.file)
    def _record(self, action, actor, extra=None):
        event = {"schema":"forgeos.approval_event.v1","timestamp":now(),"action":action,"actor":actor,"project_id":self.store.state()["project_id"]}
        if extra: event.update(extra)
        event["event_digest"] = digest(event)
        with self.audit_file.open("a") as f: f.write(json.dumps(event, sort_keys=True) + "\n")
        return event
    def status(self):
        state = self.store.state(); record = self._read()
        release_id = state.get("current_release", "REL-000002")
        return {"schema":self.SCHEMA,"status":(record or {}).get("status","PENDING"),"required_state":"APPROVAL_PENDING","project_id":state["project_id"],"release_id":release_id,"target":state.get("target"),"approved":bool(record and record.get("status")=="APPROVED"),"approval":record}
    def approve(self, body):
        state = self.store.state()
        if state["state"] != "APPROVAL_PENDING": raise ApprovalError(f"approval only allowed at APPROVAL_PENDING, current state is {state['state']}")
        release_id = body.get("release_id", state.get("current_release", "REL-000002")); target = body.get("target", state.get("target")); actor = body.get("approved_by") or body.get("actor")
        if not actor: raise ApprovalError("approved_by is required")
        if release_id != state.get("current_release", "REL-000002"): raise ApprovalError("release_id does not match current release")
        if target != state.get("target"): raise ApprovalError("target does not match current target")
        payload = {"schema":self.SCHEMA,"status":"APPROVED","project_id":state["project_id"],"release_id":release_id,"target":target,"state":"APPROVAL_PENDING","approved_by":actor,"approved_at":now()}
        unsigned = dict(payload); payload["approval_digest"] = digest(unsigned); self._write(payload)
        event = self._record("APPROVED", actor, {"release_id":release_id,"target":target,"approval_digest":payload["approval_digest"]})
        return {"status":"APPROVED","approval":payload,"event":event}
    def reject(self, body):
        state = self.store.state()
        if state["state"] != "APPROVAL_PENDING": raise ApprovalError(f"rejection only allowed at APPROVAL_PENDING, current state is {state['state']}")
        actor = body.get("rejected_by") or body.get("actor"); reason = str(body.get("reason","")).strip()
        if not actor: raise ApprovalError("rejected_by is required")
        if not reason: raise ApprovalError("reason is required")
        event = self._record("REJECTED", actor, {"reason":reason})
        record = {"schema":self.SCHEMA,"status":"REJECTED","project_id":state["project_id"],"release_id":state.get("current_release","REL-000002"),"target":state.get("target"),"rejected_by":actor,"rejected_at":event["timestamp"],"reason":reason}
        record["approval_digest"] = digest(record); self._write(record)
        return {"status":"REJECTED","approval":record,"event":event}
    def require_valid(self):
        state = self.store.state(); record = self._read()
        if not record: raise ApprovalError("no approval record exists")
        if record.get("status") != "APPROVED": raise ApprovalError("approval record is not APPROVED")
        if record.get("project_id") != state["project_id"]: raise ApprovalError("approval project binding mismatch")
        if record.get("release_id") != state.get("current_release","REL-000002"): raise ApprovalError("approval release binding mismatch")
        if record.get("target") != state.get("target"): raise ApprovalError("approval target binding mismatch")
        if record.get("state") != "APPROVAL_PENDING": raise ApprovalError("approval state binding mismatch")
        stored = record.get("approval_digest")
        if not stored: raise ApprovalError("approval digest missing")
        unsigned = dict(record); unsigned.pop("approval_digest",None)
        if digest(unsigned) != stored: raise ApprovalError("approval integrity check failed")
        return True
    def mark_consumed(self, actor):
        record = self._read()
        if not record: return
        record["status"]="CONSUMED"; record["consumed_at"]=now(); record["consumed_by"]=actor
        unsigned=dict(record); unsigned.pop("approval_digest",None); record["approval_digest"]=digest(unsigned); self._write(record)
        self._record("CONSUMED", actor, {"release_id":record.get("release_id"),"target":record.get("target")})
