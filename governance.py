from pathlib import Path
import hashlib
import json
from datetime import datetime, timezone

ALLOWED = {
    "REQUESTED": {"EXPERIMENTING"},
    "EXPERIMENTING": {"EVIDENCE_READY"},
    "EVIDENCE_READY": {"VERDICTED"},
    "VERDICTED": {"APPROVAL_PENDING"},
    "APPROVAL_PENDING": {"RELEASED"},
    "RELEASED": {"DEPLOYMENT_PRECHECKED"},
    "DEPLOYMENT_PRECHECKED": {"DEPLOYMENT_APPROVED"},
    "DEPLOYMENT_APPROVED": {"DEPLOYED"},
    "DEPLOYED": {"MONITORED", "ROLLING_BACK"},
    "MONITORED": {"ROLLING_BACK"},
    "ROLLING_BACK": {"ROLLED_BACK"},
    "ROLLED_BACK": set(),
}

def now():
    return datetime.now(timezone.utc).isoformat()

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()

def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()

class GovernanceStore:
    def __init__(self, root):
        self.root = Path(root)
        self.data = self.root / "data"
        self.data.mkdir(parents=True, exist_ok=True)
        self.state_file = self.data / "governance.json"
        self.audit_file = self.data / "audit.jsonl"
        if not self.state_file.exists():
            self._write({
                "schema": "forgeos.product_state.v1",
                "project_id": "project-0001",
                "name": "ForgeOS Alpha 0.7 Calculator",
                "target": "local-test",
                "state": "REQUESTED",
                "updated_at": now()
            })

    def _read(self):
        return json.loads(self.state_file.read_text())

    def _write(self, value):
        tmp = self.state_file.with_suffix(".tmp")
        tmp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
        tmp.replace(self.state_file)

    def state(self):
        return self._read()

    def audit(self):
        if not self.audit_file.exists():
            return []
        return [json.loads(x) for x in self.audit_file.read_text().splitlines() if x.strip()]

    def transition(self, new_state, actor="api"):
        current = self._read()
        old_state = current["state"]
        if new_state not in ALLOWED.get(old_state, set()):
            raise ValueError(f"illegal transition: {old_state} -> {new_state}")

        event = {
            "schema": "forgeos.lifecycle_event.v1",
            "timestamp": now(),
            "actor": actor,
            "project_id": current["project_id"],
            "from_state": old_state,
            "to_state": new_state
        }
        event["event_digest"] = digest(event)

        with self.audit_file.open("a") as f:
            f.write(json.dumps(event, sort_keys=True) + "\n")

        current["state"] = new_state
        current["updated_at"] = event["timestamp"]
        self._write(current)
        return {"state": current, "event": event}

    def health(self):
        return {
            "status": "HEALTHY",
            "governance_core": "READY",
            "api": "READY",
            "ui": "READY",
            "production_enabled": False
        }
