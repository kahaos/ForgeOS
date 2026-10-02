"""ForgeOS PATCH-013C governed execution domain.

Local-test only. No arbitrary command execution is exposed.
The GovernanceStore remains the authority for lifecycle state.
"""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import hashlib, json, secrets

SCHEMA = "forgeos.governed_execution.v1"
RECEIPT_SCHEMA = "forgeos.governed_execution_receipt.v1"
EVIDENCE_SCHEMA = "forgeos.evidence.v1"
VERDICT_SCHEMA = "forgeos.verdict.v1"
RELEASE_SCHEMA = "forgeos.release.v1"
PREFLIGHT_SCHEMA = "forgeos.preflight.v1"


class GovernedExecutionError(ValueError):
    pass


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(obj):
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()


def _read(path, default):
    try:
        return json.loads(Path(path).read_text())
    except FileNotFoundError:
        return default


def _write(path, obj):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True))
    tmp.replace(p)


class GovernedExecutionStore:
    """Domain records for evidence/verdict/release/deployment.

    The store deliberately has no shell/exec interface. Deployment is a
    deterministic local-test artifact operation.
    """

    def __init__(self, root, governance, approval, deployment_approval=None):
        self.root = Path(root)
        self.governance = governance
        self.approval = approval
        self.deployment_approval = deployment_approval
        self.data = self.root / "data" / "governed_execution"
        self.data.mkdir(parents=True, exist_ok=True)
        self.evidence_file = self.data / "evidence.json"
        self.verdict_file = self.data / "verdicts.json"
        self.release_file = self.data / "releases.json"
        self.approval_file = self.data / "approvals.json"
        self.state_file = self.data / "execution_state.json"
        self.receipt_file = self.data / "receipts.json"
        self.audit_file = self.data / "audit.jsonl"

    def _state(self):
        return _read(self.state_file, {"schema": SCHEMA, "projects": {}})

    def _save(self, state):
        _write(self.state_file, state)

    def _audit(self, action, project_id, record=None, actor="system"):
        event = {
            "schema": "forgeos.governed_execution_event.v1",
            "action": action,
            "project_id": project_id,
            "actor": actor,
            "timestamp": now(),
        }
        if record is not None:
            event["record_digest"] = digest(record)
        event["event_digest"] = digest(event)
        with self.audit_file.open("a") as f:
            f.write(json.dumps(event, sort_keys=True) + "\n")
        return event

    def _current(self):
        return self.governance.state()

    def _require_project(self, project_id):
        cur = self._current()
        if cur.get("project_id") != project_id:
            raise GovernedExecutionError("project_binding_mismatch")
        return cur

    def _transition(self, new_state, actor):
        # GovernanceStore is the only lifecycle authority. Domain code may request
        # the consequence of a validated domain operation; it never writes state directly.
        try:
            return self.governance.transition(new_state, actor=actor)
        except TypeError:
            return self.governance.transition(new_state, actor)
        except Exception as exc:
            raise GovernedExecutionError(f"lifecycle_transition_failed:{exc}") from exc

    def _require_state(self, expected):
        cur = self._current()
        if cur.get("state") != expected:
            raise GovernedExecutionError(f"requires_{expected}:{cur.get('state')}")
        return cur

    @staticmethod
    def _verify_integrity(record, field="integrity_digest", error="record_integrity_failed"):
        supplied = record.get(field)
        unsigned = {k: v for k, v in record.items() if k != field}
        if not supplied or digest(unsigned) != supplied:
            raise GovernedExecutionError(error)

    def _get_evidence(self, project_id, evidence_id):
        evs = _read(self.evidence_file, {"items": []})["items"]
        ev = next((x for x in evs if x.get("evidence_id") == evidence_id), None)
        if not ev or ev.get("project_id") != project_id:
            raise GovernedExecutionError("evidence_binding_mismatch")
        self._verify_integrity(ev, error="evidence_integrity_failed")
        return ev

    def _get_verdict(self, project_id, verdict_id):
        vs = _read(self.verdict_file, {"items": []})["items"]
        verdict = next((x for x in vs if x.get("verdict_id") == verdict_id), None)
        if not verdict or verdict.get("project_id") != project_id:
            raise GovernedExecutionError("verdict_binding_mismatch")
        self._verify_integrity(verdict, error="verdict_integrity_failed")
        self._get_evidence(project_id, verdict.get("evidence_id"))
        return verdict

    def _get_release(self, project_id, release_id, target="local-test"):
        rs = _read(self.release_file, {"items": []})["items"]
        rel = next((x for x in rs if x.get("release_id") == release_id), None)
        if not rel or rel.get("project_id") != project_id or rel.get("target") != target:
            raise GovernedExecutionError("release_binding_mismatch")
        if rel.get("target") != "local-test":
            raise GovernedExecutionError("target_not_allowed")
        self._verify_integrity(rel, error="release_integrity_failed")
        self._get_verdict(project_id, rel.get("verdict_id"))
        return rel

    def submit_evidence(self, project_id, experiment_id, content, actor="ai"):
        self._require_project(project_id)
        self._require_state("EXPERIMENTING")
        if not experiment_id or not content:
            raise GovernedExecutionError("experiment_id_and_content_required")
        ev = _read(self.evidence_file, {"schema": EVIDENCE_SCHEMA, "items": []})
        if any(x["project_id"] == project_id and x["experiment_id"] == experiment_id for x in ev["items"]):
            raise GovernedExecutionError("evidence_already_exists")
        rec = {
            "schema": EVIDENCE_SCHEMA,
            "evidence_id": "EVD-" + secrets.token_hex(6).upper(),
            "project_id": project_id,
            "experiment_id": experiment_id,
            "content": content,
            "created_at": now(),
            "actor": actor,
        }
        rec["integrity_digest"] = digest(rec)
        ev["items"].append(rec)
        _write(self.evidence_file, ev)
        self._audit("EVIDENCE_SUBMITTED", project_id, rec, actor)
        self._transition("EVIDENCE_READY", actor)
        return rec

    def create_verdict(self, project_id, evidence_id, verdict, rationale="", actor="ai"):
        self._require_project(project_id)
        self._require_state("EVIDENCE_READY")
        self._get_evidence(project_id, evidence_id)
        vs = _read(self.verdict_file, {"schema": VERDICT_SCHEMA, "items": []})
        rec = {
            "schema": VERDICT_SCHEMA,
            "verdict_id": "VER-" + secrets.token_hex(6).upper(),
            "project_id": project_id,
            "evidence_id": evidence_id,
            "verdict": verdict,
            "rationale": rationale,
            "created_at": now(),
            "actor": actor,
        }
        rec["integrity_digest"] = digest(rec)
        vs["items"].append(rec)
        _write(self.verdict_file, vs)
        self._audit("VERDICT_CREATED", project_id, rec, actor)
        self._transition("VERDICTED", actor)
        return rec

    def create_release(self, project_id, release_id, verdict_id, target, actor="ai"):
        self._require_project(project_id)
        self._require_state("VERDICTED")
        if target != "local-test":
            raise GovernedExecutionError("target_not_allowed")
        self._get_verdict(project_id, verdict_id)
        rs = _read(self.release_file, {"schema": RELEASE_SCHEMA, "items": []})
        if any(x["release_id"] == release_id for x in rs["items"]):
            raise GovernedExecutionError("release_exists")
        rec = {
            "schema": RELEASE_SCHEMA,
            "release_id": release_id,
            "project_id": project_id,
            "verdict_id": verdict_id,
            "target": target,
            "created_at": now(),
            "actor": actor,
        }
        rec["integrity_digest"] = digest(rec)
        rs["items"].append(rec)
        _write(self.release_file, rs)

        # Persist the active governed release context separately from the
        # legacy GovernanceStore. GovernanceStore remains the sole lifecycle
        # authority; this is only the 013C execution-domain binding.
        st = self._state()
        project_state = st["projects"].setdefault(project_id, {})
        project_state["release"] = {
            "release_id": release_id,
            "verdict_id": verdict_id,
            "target": target,
            "release_digest": rec["integrity_digest"],
            "created_at": rec["created_at"],
        }
        self._save(st)

        self._audit("RELEASE_CREATED", project_id, rec, actor)
        return rec

    def request_approval(self, project_id, release_id, target, verdict_id, actor="ai"):
        self._require_project(project_id)
        self._require_state("VERDICTED")
        if target != "local-test":
            raise GovernedExecutionError("target_not_allowed")
        rel = self._get_release(project_id, release_id, target)
        if rel.get("verdict_id") != verdict_id:
            raise GovernedExecutionError("release_binding_mismatch")
        st = self._state()
        p = st["projects"].setdefault(project_id, {})
        p["approval_request"] = {
            "release_id": release_id,
            "target": target,
            "verdict_id": verdict_id,
            "requested_at": now(),
            "requested_by": actor,
        }
        self._save(st)
        self._audit("APPROVAL_REQUESTED", project_id, p["approval_request"], actor)
        self._transition("APPROVAL_PENDING", actor)
        return p["approval_request"]

    def require_valid_release_approval(
        self,
        project_id,
        release_id,
        target,
        verdict_id,
    ):
        """Verify a persisted 013C release approval record.

        This is a read-only governed integrity check. It verifies:
        - exact project/release/target/verdict binding
        - approval status
        - release integrity
        - approval-request binding
        - approval digest integrity
        - persisted approval-record equality
        """
        self._require_project(project_id)

        if target != "local-test":
            raise GovernedExecutionError("only local-test approval is enabled")

        approvals = _read(
            self.approval_file,
            {"schema": "forgeos.release_approvals.v1", "items": []},
        )

        record = next(
            (
                item
                for item in approvals.get("items", [])
                if item.get("project_id") == project_id
                and item.get("release_id") == release_id
                and item.get("target") == target
            ),
            None,
        )

        if record is None:
            raise GovernedExecutionError("release_approval_not_found")

        if record.get("status") != "APPROVED":
            raise GovernedExecutionError(
                f"release_approval_not_approved:{record.get('status')}"
            )

        if record.get("verdict_id") != verdict_id:
            raise GovernedExecutionError(
                "release_approval_verdict_binding_mismatch"
            )

        rel = self._get_release(project_id, release_id, target)

        if record.get("release_digest") != rel.get("integrity_digest"):
            raise GovernedExecutionError(
                "release_approval_release_mismatch"
            )

        approval_digest = record.get("approval_digest")
        if not approval_digest:
            raise GovernedExecutionError(
                "release_approval_digest_missing"
            )

        unsigned = dict(record)
        unsigned.pop("approval_digest", None)

        if digest(unsigned) != approval_digest:
            raise GovernedExecutionError(
                "release_approval_integrity_failed"
            )

        stored = next(
            (
                item
                for item in approvals.get("items", [])
                if item.get("approval_digest") == approval_digest
            ),
            None,
        )

        if stored is None:
            raise GovernedExecutionError(
                "release_approval_not_recorded"
            )

        if stored != record:
            raise GovernedExecutionError(
                "release_approval_record_mismatch"
            )

        st = self._state()
        project_state = st.get("projects", {}).get(project_id, {})
        request = project_state.get("approval_request")

        if not request:
            raise GovernedExecutionError(
                "no approval request exists"
            )

        if request.get("project_id", project_id) != project_id:
            raise GovernedExecutionError(
                "approval_request_project_binding_mismatch"
            )

        if request.get("release_id") != release_id:
            raise GovernedExecutionError(
                "approval_request_release_binding_mismatch"
            )

        if request.get("target") != target:
            raise GovernedExecutionError(
                "approval_request_target_binding_mismatch"
            )

        if request.get("verdict_id") != verdict_id:
            raise GovernedExecutionError(
                "approval_request_verdict_binding_mismatch"
            )

        return record

    def approve_release(
        self,
        project_id,
        release_id,
        target,
        verdict_id,
        approved_by,
    ):
        """Consume a 013C release approval request.

        This is the human release-approval gate for the governed execution
        domain. It intentionally does not use the legacy ApprovalGate.
        GovernanceStore remains authoritative for lifecycle state.
        """
        self._require_project(project_id)
        self._require_state("APPROVAL_PENDING")

        if target != "local-test":
            raise GovernedExecutionError(
                "only local-test approval is enabled"
            )

        if not approved_by:
            raise GovernedExecutionError(
                "approved_by is required"
            )

        # Exact release binding and release integrity.
        rel = self._get_release(
            project_id,
            release_id,
            target,
        )

        if rel.get("verdict_id") != verdict_id:
            raise GovernedExecutionError(
                "approval verdict binding mismatch"
            )

        stored_release_digest = rel.get("integrity_digest")
        if not stored_release_digest:
            raise GovernedExecutionError(
                "release integrity digest missing"
            )

        unsigned_release = dict(rel)
        unsigned_release.pop("integrity_digest", None)

        if digest(unsigned_release) != stored_release_digest:
            raise GovernedExecutionError(
                "release integrity check failed"
            )

        # Verify the verdict exists and is bound to the release.
        verdict = self._get_verdict(
            project_id,
            verdict_id,
        )

        if verdict.get("project_id") != project_id:
            raise GovernedExecutionError(
                "verdict project binding mismatch"
            )

        if verdict.get("evidence_id") is None:
            raise GovernedExecutionError(
                "verdict evidence binding missing"
            )

        # Verify the stored approval request is exact.
        st = self._state()
        project_state = st.get("projects", {}).get(project_id, {})
        request = project_state.get("approval_request")

        if not request:
            raise GovernedExecutionError(
                "no approval request exists"
            )

        if request.get("project_id", project_id) != project_id:
            raise GovernedExecutionError(
                "approval request project binding mismatch"
            )

        if request.get("release_id") != release_id:
            raise GovernedExecutionError(
                "approval request release binding mismatch"
            )

        if request.get("target") != target:
            raise GovernedExecutionError(
                "approval request target binding mismatch"
            )

        if request.get("verdict_id") != verdict_id:
            raise GovernedExecutionError(
                "approval request verdict binding mismatch"
            )

        approvals = _read(
            self.approval_file,
            {"schema": "forgeos.release_approvals.v1", "items": []},
        )

        # Replay protection.
        for existing in approvals.get("items", []):
            if (
                existing.get("project_id") == project_id
                and existing.get("release_id") == release_id
                and existing.get("target") == target
            ):
                if existing.get("status") == "APPROVED":
                    raise GovernedExecutionError(
                        "release approval already consumed"
                    )

        record = {
            "schema": "forgeos.release_approval.v1",
            "status": "APPROVED",
            "project_id": project_id,
            "release_id": release_id,
            "target": target,
            "verdict_id": verdict_id,
            "release_digest": stored_release_digest,
            "approved_by": approved_by,
            "approved_at": now(),
        }

        record["approval_digest"] = digest(record)

        approvals.setdefault("items", []).append(record)
        _write(self.approval_file, approvals)

        # Persist the approval as the current governed execution context.
        project_state["approval"] = {
            "status": "APPROVED",
            "project_id": project_id,
            "release_id": release_id,
            "target": target,
            "verdict_id": verdict_id,
            "release_digest": stored_release_digest,
            "approval_digest": record["approval_digest"],
            "approved_by": approved_by,
            "approved_at": record["approved_at"],
        }
        self._save(st)

        self._audit(
            "RELEASE_APPROVED",
            project_id,
            record,
            approved_by,
        )

        # GovernanceStore is the sole lifecycle authority.
        try:
            self.governance.transition(
                "RELEASED",
                actor=approved_by,
            )
        except TypeError:
            self.governance.transition(
                "RELEASED",
                approved_by,
            )

        return record

    def preflight(self, project_id, release_id, target, actor="system"):
        self._require_project(project_id)
        self._require_state("RELEASED")
        if target != "local-test":
            raise GovernedExecutionError("target_not_allowed")
        rel = self._get_release(project_id, release_id, target)
        result = {
            "schema": PREFLIGHT_SCHEMA,
            "project_id": project_id,
            "release_id": release_id,
            "target": target,
            "release_digest": rel["integrity_digest"],
            "passed": True,
            "checks": ["project", "release", "target", "integrity", "verdict_chain", "production_disabled"],
            "production_enabled": False,
            "timestamp": now(),
        }
        result["integrity_digest"] = digest(result)
        self._audit("PREFLIGHT_PASSED", project_id, result, actor)
        self._transition("DEPLOYMENT_PRECHECKED", actor)
        return result

    def mark_preflight(self, project_id, release_id, target, actor="system"):
        result = self.preflight(project_id, release_id, target, actor)
        st = self._state()
        p = st["projects"].setdefault(project_id, {})
        p["preflight"] = result
        p["preflight_passed"] = True
        self._save(st)
        return result

    def _require_preflight(self, project_id, release_id, target):
        p = self._state().get("projects", {}).get(project_id, {})
        preflight = p.get("preflight")
        if not p.get("preflight_passed") or not isinstance(preflight, dict):
            raise GovernedExecutionError("preflight_required")
        if (preflight.get("project_id"), preflight.get("release_id"), preflight.get("target")) != (project_id, release_id, target):
            raise GovernedExecutionError("preflight_binding_mismatch")
        self._verify_integrity(preflight, error="preflight_integrity_failed")
        if not preflight.get("passed"):
            raise GovernedExecutionError("preflight_failed")
        rel = self._get_release(project_id, release_id, target)
        if preflight.get("release_digest") != rel.get("integrity_digest"):
            raise GovernedExecutionError("preflight_release_mismatch")
        return preflight

    def deploy_local_test(self, project_id, release_id, target, actor="system"):
        self._require_project(project_id)
        self._require_state("DEPLOYMENT_APPROVED")
        if target != "local-test":
            raise GovernedExecutionError("target_not_allowed")
        if self.deployment_approval is None:
            raise GovernedExecutionError("deployment_approval_gate_not_configured")
        self._get_release(project_id, release_id, target)
        self._require_preflight(project_id, release_id, target)
        try:
            self.deployment_approval.require_valid(project_id, release_id, target)
        except Exception as exc:
            raise GovernedExecutionError(str(exc)) from exc

        artifact = self.data / f"{release_id}.local_test_artifact.txt"
        content = f"ForgeOS local-test deployment\nrelease={release_id}\n"
        artifact.write_text(content)
        sha = hashlib.sha256(artifact.read_bytes()).hexdigest()
        rec = {
            "schema": RECEIPT_SCHEMA,
            "project_id": project_id,
            "release_id": release_id,
            "target": target,
            "status": "EXECUTED",
            "artifact": str(artifact),
            "artifact_sha256": sha,
            "timestamp": now(),
            "actor": actor,
        }
        rec["receipt_digest"] = digest(rec)
        receipts = _read(self.receipt_file, {"schema": RECEIPT_SCHEMA, "items": []})
        receipts["items"].append(rec)
        _write(self.receipt_file, receipts)
        self._audit("DEPLOYMENT_EXECUTED", project_id, rec, actor)
        self.deployment_approval.consume(project_id, release_id, target)
        self._transition("DEPLOYED", actor)
        return rec

    def verify(self, project_id, receipt, actor="system"):
        self._require_project(project_id)
        self._require_state("DEPLOYED")
        if receipt.get("schema") != RECEIPT_SCHEMA or receipt.get("status") != "EXECUTED":
            raise GovernedExecutionError("invalid_receipt")
        if receipt.get("project_id") != project_id or receipt.get("target") != "local-test":
            raise GovernedExecutionError("receipt_binding_mismatch")
        self._verify_integrity(receipt, field="receipt_digest", error="receipt_integrity_failed")
        rel = self._get_release(project_id, receipt.get("release_id"), "local-test")
        receipts = _read(self.receipt_file, {"items": []})["items"]
        stored = next((x for x in receipts if x.get("receipt_digest") == receipt.get("receipt_digest")), None)
        if stored is None:
            raise GovernedExecutionError("receipt_not_recorded")
        if stored != receipt:
            raise GovernedExecutionError("receipt_record_mismatch")
        artifact_path = Path(receipt.get("artifact", ""))
        try:
            artifact_path.relative_to(self.data)
        except ValueError as exc:
            raise GovernedExecutionError("artifact_path_not_allowed") from exc
        ok = artifact_path.exists() and hashlib.sha256(artifact_path.read_bytes()).hexdigest() == receipt.get("artifact_sha256")
        if not ok:
            result = {
                "schema": "forgeos.verification.v1",
                "project_id": project_id,
                "release_id": rel["release_id"],
                "target": "local-test",
                "ok": False,
                "timestamp": now(),
            }
            self._audit("DEPLOYMENT_VERIFICATION_FAILED", project_id, result, actor)
            return result
        result = {
            "schema": "forgeos.verification.v1",
            "project_id": project_id,
            "release_id": rel["release_id"],
            "target": "local-test",
            "ok": True,
            "timestamp": now(),
        }
        self._audit("DEPLOYMENT_VERIFIED", project_id, result, actor)
        self._transition("MONITORED", actor)
        return result

    def rollback(self, project_id, release_id, reason, actor="human"):
        self._require_project(project_id)
        cur = self._current()
        if cur.get("state") not in {"DEPLOYED", "MONITORED"}:
            raise GovernedExecutionError(f"requires_DEPLOYED_OR_MONITORED:{cur.get('state')}")
        self._get_release(project_id, release_id, "local-test")
        rec = {
            "schema": "forgeos.rollback.v1",
            "project_id": project_id,
            "release_id": release_id,
            "target": "local-test",
            "reason": reason,
            "status": "ROLLING_BACK",
            "timestamp": now(),
            "actor": actor,
        }
        self._audit("ROLLBACK_STARTED", project_id, rec, actor)
        self._transition("ROLLING_BACK", actor)
        rec["status"] = "ROLLED_BACK"
        rec["completed_at"] = now()
        self._audit("ROLLBACK_COMPLETED", project_id, rec, actor)
        self._transition("ROLLED_BACK", actor)
        return rec

    def audit(self, project_id=None):
        out = []
        if self.audit_file.exists():
            for line in self.audit_file.read_text().splitlines():
                if not line:
                    continue
                x = json.loads(line)
                if project_id is None or x.get("project_id") == project_id:
                    out.append(x)
        return out
