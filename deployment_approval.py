from __future__ import annotations
from pathlib import Path
import hashlib, json, secrets
from datetime import datetime, timezone

SCHEMA = "forgeos.deployment_approval.v1"

class DeploymentApprovalError(ValueError):
    pass

def now():
    return datetime.now(timezone.utc).isoformat()

def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()

class DeploymentApprovalGate:
    def __init__(self, root, governance):
        self.root = Path(root)
        self.governance = governance
        self.file = self.root / "data" / "deployment_approval.json"
        self.audit_file = self.root / "data" / "deployment_approval_audit.jsonl"
        self.release_file = self.root / "data" / "governed_execution" / "releases.json"
        self.verdict_file = self.root / "data" / "governed_execution" / "verdicts.json"
        self.execution_state_file = self.root / "data" / "governed_execution" / "execution_state.json"

    def _read(self):
        try:
            return json.loads(self.file.read_text())
        except FileNotFoundError:
            return {}

    def _read_json(self, path, default):
        try:
            return json.loads(path.read_text())
        except FileNotFoundError:
            return default

    @staticmethod
    def _verify_integrity(record, field, error):
        supplied = record.get(field)
        unsigned = {k: v for k, v in record.items() if k != field}
        if not supplied or digest(unsigned) != supplied:
            raise DeploymentApprovalError(error)

    def _get_release(self, project_id, release_id, target):
        records = self._read_json(self.release_file, {"items": []}).get("items", [])
        rel = next((x for x in records if x.get("release_id") == release_id), None)
        if not rel or (rel.get("project_id"), rel.get("target")) != (project_id, target):
            raise DeploymentApprovalError("release_binding_mismatch")
        if target != "local-test":
            raise DeploymentApprovalError("target_not_allowed")
        self._verify_integrity(rel, "integrity_digest", "release_integrity_failed")
        verdicts = self._read_json(self.verdict_file, {"items": []}).get("items", [])
        verdict = next((x for x in verdicts if x.get("verdict_id") == rel.get("verdict_id")), None)
        if not verdict or verdict.get("project_id") != project_id:
            raise DeploymentApprovalError("verdict_binding_mismatch")
        self._verify_integrity(verdict, "integrity_digest", "verdict_integrity_failed")
        return rel

    def _require_preflight(self, project_id, release_id, target):
        st = self._read_json(self.execution_state_file, {"projects": {}})
        p = st.get("projects", {}).get(project_id, {})
        preflight = p.get("preflight")
        if not p.get("preflight_passed") or not isinstance(preflight, dict):
            raise DeploymentApprovalError("preflight_required")
        if (preflight.get("project_id"), preflight.get("release_id"), preflight.get("target")) != (project_id, release_id, target):
            raise DeploymentApprovalError("preflight_binding_mismatch")
        self._verify_integrity(preflight, "integrity_digest", "preflight_integrity_failed")
        if not preflight.get("passed"):
            raise DeploymentApprovalError("preflight_failed")
        rel = self._get_release(project_id, release_id, target)
        if preflight.get("release_digest") != rel.get("integrity_digest"):
            raise DeploymentApprovalError("preflight_release_mismatch")
        return preflight

    def status(self):
        r = self._read()
        return {"schema": SCHEMA, "approved": r.get("status") == "APPROVED",
                "status": r.get("status", "NONE"), "project_id": r.get("project_id"),
                "release_id": r.get("release_id"), "target": r.get("target")}

    def approve(self, project_id, release_id, target, approved_by):
        state = self.governance.state()
        if state.get("project_id") != project_id:
            raise DeploymentApprovalError("project_binding_mismatch")
        if state.get("state") != "DEPLOYMENT_PRECHECKED":
            raise DeploymentApprovalError(f"requires_DEPLOYMENT_PRECHECKED:{state.get('state')}")
        if target != "local-test":
            raise DeploymentApprovalError("target_not_allowed")
        if not approved_by:
            raise DeploymentApprovalError("approved_by_required")
        existing = self._read()
        if existing.get("status") == "APPROVED":
            raise DeploymentApprovalError("deployment_approval_already_pending")
        release = self._get_release(project_id, release_id, target)
        self._require_preflight(project_id, release_id, target)
        record = {"schema": SCHEMA, "approval_id": "DAPP-" + secrets.token_hex(6).upper(),
                  "status": "APPROVED", "project_id": project_id, "release_id": release_id,
                  "release_digest": release["integrity_digest"], "target": target,
                  "approved_by": approved_by, "approved_at": now()}
        record["approval_digest"] = digest(record)
        self.file.parent.mkdir(parents=True, exist_ok=True)
        self.file.write_text(json.dumps(record, indent=2, sort_keys=True))
        event = {"schema": "forgeos.deployment_approval_event.v1", "action": "DEPLOYMENT_APPROVED",
                 "project_id": project_id, "release_id": release_id, "target": target,
                 "approved_by": approved_by, "timestamp": now(),
                 "approval_digest": record["approval_digest"]}
        event["event_digest"] = digest(event)
        with self.audit_file.open("a") as fh:
            fh.write(json.dumps(event, sort_keys=True) + "\n")

        # GovernanceStore remains the sole lifecycle authority.
        # Deployment approval is the explicit human authorization that
        # advances the governed project from prechecked to approved.
        try:
            self.governance.transition("DEPLOYMENT_APPROVED", actor=approved_by)
        except TypeError:
            self.governance.transition("DEPLOYMENT_APPROVED", approved_by)

        return record

    def require_valid(self, project_id, release_id, target):
        record = self._read()
        if record.get("status") != "APPROVED":
            raise DeploymentApprovalError("deployment_approval_required")
        if (record.get("project_id"), record.get("release_id"), record.get("target")) != (project_id, release_id, target):
            raise DeploymentApprovalError("deployment_approval_binding_mismatch")
        unsigned = dict(record)
        supplied = unsigned.pop("approval_digest", None)
        if digest(unsigned) != supplied:
            raise DeploymentApprovalError("deployment_approval_integrity_failed")
        release = self._get_release(project_id, release_id, target)
        if record.get("release_digest") != release.get("integrity_digest"):
            raise DeploymentApprovalError("deployment_approval_release_mismatch")
        self._require_preflight(project_id, release_id, target)
        return record

    def consume(self, project_id, release_id, target):
        record = self.require_valid(project_id, release_id, target)
        record["status"] = "CONSUMED"
        record["consumed_at"] = now()
        record["approval_digest"] = digest(record)
        self.file.write_text(json.dumps(record, indent=2, sort_keys=True))
        event = {"schema": "forgeos.deployment_approval_event.v1", "action": "DEPLOYMENT_APPROVAL_CONSUMED",
                 "project_id": project_id, "release_id": release_id, "target": target,
                 "timestamp": now(), "approval_digest": record["approval_digest"]}
        event["event_digest"] = digest(event)
        with self.audit_file.open("a") as fh:
            fh.write(json.dumps(event, sort_keys=True) + "\n")
        return record
