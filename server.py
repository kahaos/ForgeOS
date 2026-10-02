# PATCH-017-RELEASE-BINDING
import patch017_release_binding
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from governance import ALLOWED, GovernanceStore
from audit_merge import combined_audit
from approval_gate import ApprovalGate, ApprovalError
from patch_plan import PatchPlanStore, PatchPlanError
from governed_execution import GovernedExecutionStore
from ai_execution_api import get as ai_execution_get, post as ai_execution_post
from deployment_approval import DeploymentApprovalGate, DeploymentApprovalError
from ai_api import get as ai_get, post as ai_post
from ai_domain_api import get as ai_domain_get, post as ai_domain_post
from project_domain import ProjectDomainStore
from forgeos_github.api import build_integration as build_github_integration, get as github_get, post as github_post
from forgeos_agent.http_api import AgentHTTP
from public_trial import run_trial, PublicTrialError
from patch_011_execution import execute_patch_plan
from patch_023_multi_execution import execute_patch_plan_all

ROOT = Path(__file__).resolve().parent
store = GovernanceStore(ROOT)
approval = ApprovalGate(ROOT, store)
patch_plan = PatchPlanStore(ROOT)
deployment_approval = DeploymentApprovalGate(ROOT, store)
execution = GovernedExecutionStore(ROOT, store, approval, deployment_approval)
domain = ProjectDomainStore(ROOT)
github_integration = build_github_integration(ROOT)
agent_http = AgentHTTP(ROOT, github_integration)


class Handler(BaseHTTPRequestHandler):
    def send(self, status, body, content_type="application/json"):
        if isinstance(body, bytes):
            raw = body
        elif content_type.startswith("application/json"):
            raw = json.dumps(body, indent=2).encode()
        else:
            raw = str(body).encode()

        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _json_body(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        return json.loads(self.rfile.read(length))

    def do_GET(self):
        path = urlparse(self.path).path
        agent_result = agent_http.get(path)
        if agent_result is not None:
            status, payload = agent_result
            self.send(status, payload)
            return

        if path == "/api/projects" or path.startswith("/api/projects/"):
            result = github_get(path, github_integration)
            if result is not None:
                status, payload = result
                self.send(status, payload)
                return

        if path == "/api/deployment-approval":

            self.send(200, deployment_approval.status())

            return

        if path.startswith("/api/ai/v1/"):

            result = ai_execution_get(path, store, execution)

            if result is not None:

                status, payload = result

                self.send(status, payload)

                return

            result = ai_domain_get(path, store, domain)
            if result is not None:
                status, payload = result
                self.send(status, payload)
                return
            status, payload = ai_get(path, store)
            self.send(status, payload)
            return

        if path == "/":
            self.send(200, (ROOT / "index.html").read_bytes(), "text/html; charset=utf-8")
        elif path == "/api/health":
            self.send(200, store.health())
        elif path == "/api/state":
            self.send(200, store.state())
        elif path == "/api/status":
            state = store.state()
            health = store.health()
            self.send(200, {
                "schema": "forgeos.api_status.v1",
                "status": health["status"],
                "system": health,
                "project": {
                    "project_id": state["project_id"],
                    "name": state["name"],
                },
                "lifecycle": {
                    "state": state["state"],
                    "updated_at": state["updated_at"],
                    "allowed_next_states": sorted(ALLOWED.get(state["state"], set())),
                },
                "target": state.get("target"),
                "current_release": state.get("current_release", "REL-000002"),
                "governance": {
                    "authoritative": True,
                    "production_enabled": health["production_enabled"],
                },
            })
        elif path == "/api/lifecycle":
            state = store.state()
            self.send(200, {
                "schema": "forgeos.lifecycle_status.v1",
                "project_id": state["project_id"],
                "state": state["state"],
                "updated_at": state["updated_at"],
                "target": state.get("target"),
                "current_release": state.get("current_release", "REL-000002"),
                "allowed_next_states": sorted(ALLOWED.get(state["state"], set())),
                "terminal": not bool(ALLOWED.get(state["state"], set())),
            })
        elif path == "/api/approval":
            self.send(200, approval.status())
        elif path == "/api/patch-plan":
            self.send(200, patch_plan.status())
        elif path == "/api/patch-plan/audit":
            self.send(200, {
                "schema": "forgeos.patch_plan_audit.v1",
                "events": patch_plan.audit(),
            })
        elif path == "/api/audit":
            self.send(200, {"events": combined_audit(store)})
        else:
            self.send(404, {"error": "not_found"})

    def do_POST(self):
        path = urlparse(self.path).path

        if path == "/api/public/trial":
            try:
                body = self._json_body()
                result = run_trial(
                    agent_http,
                    body.get("task", ""),
                    body.get("mode", "normal"),
                    project_resolver=lambda pid: (
                        None
                        if github_integration.registry.get(pid) is None
                        else github_integration._project_model(
                            github_integration.registry.get(pid)
                        )
                    ),
                    client_id=self.client_address[0],
                )
                self.send(200, result)
            except PublicTrialError as exc:
                self.send(400, {"error": str(exc)})
            except Exception as exc:
                self.send(500, {"error": "public_trial_error", "detail": str(exc)})
            return


        if path == "/api/projects" or path.startswith("/api/projects/") or path == "/api/github/webhook" or path.startswith("/api/agent/"):
            try:
                body = self._json_body()
            except json.JSONDecodeError as exc:
                self.send(400, {"error": str(exc)})
                return
            agent_result = agent_http.post(path, body, lambda pid: (
                None
                if github_integration.registry.get(pid) is None
                else github_integration._project_model(
                    github_integration.registry.get(pid)
                )
            ))
            if agent_result is not None:
                status, payload = agent_result
                self.send(status, payload)
                return
            result = github_post(path, body, github_integration)
            if result is not None:
                status, payload = result
                self.send(status, payload)
                return

        if path == "/api/deployment-approval":

            try:

                body = self._json_body()

                record = deployment_approval.approve(

                    body["project_id"], body["release_id"], body["target"], body["approved_by"]

                )

                self.send(200, record)

                return

            except DeploymentApprovalError as exc:

                self.send(409, {"error": str(exc)})

                return

            except KeyError as exc:

                self.send(400, {"error": str(exc)})

                return

        if path.startswith("/api/ai/v1/"):
            try:
                body = self._json_body()
            except json.JSONDecodeError as exc:
                self.send(400, {"error": str(exc)})
                return

            result = ai_execution_post(path, body, store, execution, approval)
            if result is not None:
                status, payload = result
                self.send(status, payload)
                return

            result = ai_domain_post(path, body, store, domain)
            if result is not None:
                status, payload = result
                self.send(status, payload)
                return

            status, payload = ai_post(path, body, store)
            self.send(status, payload)
            return

        if path == "/api/transition":
            try:
                body = self._json_body()
                result = store.transition(body["state"], body.get("actor", "api"))
                self.send(200, result)
            except (KeyError, ValueError, json.JSONDecodeError) as exc:
                self.send(400, {"error": str(exc)})
            return

        if path == "/api/lifecycle/advance":
            try:
                body = self._json_body()
            except json.JSONDecodeError as exc:
                self.send(400, {"error": str(exc)})
                return
            state = store.state()
            next_states = sorted(ALLOWED.get(state["state"], set()))
            if not next_states:
                self.send(409, {"error":"no_legal_transition","state":state["state"]})
                return
            if state["state"] == "APPROVAL_PENDING" and "RELEASED" in next_states:
                try:
                    approval.require_valid()
                except ApprovalError as exc:
                    self.send(403, {"error":"approval_required","detail":str(exc),"approval":approval.status()})
                    return
            actor = body.get("actor", "ui") if isinstance(body, dict) else "ui"
            try:
                result = store.transition(next_states[0], actor)
                if result["event"]["to_state"] == "RELEASED":
                    approval.mark_consumed(actor)
                self.send(200, result)
            except ValueError as exc:
                self.send(409, {"error": str(exc)})
            return

        if path == "/api/patch-plan/create":
            try:
                body = self._json_body()
                current = store.state()

                if body.get("project_id") != current["project_id"]:
                    self.send(409, {
                        "error": "project_binding_mismatch",
                        "current_project_id": current["project_id"],
                    })
                    return

                result = patch_plan.create(body)
                self.send(201, result)

            except (
                PatchPlanError,
                KeyError,
                ValueError,
                TypeError,
                json.JSONDecodeError,
            ) as exc:
                self.send(400, {"error": str(exc)})
            return

        if path == "/api/patch-plan/validate":
            try:
                current = store.state()
                plan = patch_plan.status()

                if plan.get("status") == "EMPTY":
                    self.send(409, {"error": "no_patch_plan"})
                    return

                if plan.get("project_id") != current["project_id"]:
                    self.send(409, {
                        "error": "project_binding_mismatch",
                        "current_project_id": current["project_id"],
                    })
                    return

                body = self._json_body()
                actor = body.get("actor", "api")

                result = patch_plan.validate(actor=actor)
                self.send(200, result)

            except (
                PatchPlanError,
                KeyError,
                ValueError,
                TypeError,
                json.JSONDecodeError,
            ) as exc:
                self.send(400, {"error": str(exc)})
            return

        if path == "/api/patch-plan/execute-all":
            try:
                body = self._json_body()
                result = execute_patch_plan_all(
                    patch_plan,
                    body.get("project_id", ""),
                    body.get("target", "local-test"),
                    actor=body.get("actor", "human"),
                )
                self.send(200, result)
            except ValueError as exc:
                self.send(400, {"error": str(exc)})
            except Exception as exc:
                self.send(500, {"error": "multi_patch_execution_error", "detail": str(exc)})
            return


        if path == "/api/patch-plan/execute":
            try:
                body = self._json_body()
                current = store.state()
                plan = patch_plan.status()

                if plan.get("status") == "EMPTY":
                    self.send(409, {"error": "no_patch_plan"})
                    return

                project_id = body.get("project_id")
                target = body.get("target")
                patch_id = body.get("patch_id")
                actor = body.get("actor", "api")

                if not project_id:
                    self.send(400, {
                        "error": "project_id_required",
                    })
                    return

                if not target:
                    self.send(400, {
                        "error": "target_required",
                    })
                    return

                if not patch_id:
                    self.send(400, {
                        "error": "patch_id_required",
                    })
                    return

                if project_id != current["project_id"]:
                    self.send(409, {
                        "error": "project_binding_mismatch",
                        "current_project_id": current["project_id"],
                    })
                    return

                if target != "local-test":
                    self.send(409, {
                        "error": "target_not_allowed",
                    })
                    return

                result = execute_patch_plan(
                    patch_plan,
                    project_id,
                    target,
                    patch_id,
                    actor=actor,
                )

                self.send(200, result)

            except ValueError as exc:
                self.send(409, {"error": str(exc)})
            except (KeyError, TypeError, json.JSONDecodeError) as exc:
                self.send(400, {"error": str(exc)})
            return

        if path == "/api/approval":
            try:
                result = approval.approve(self._json_body())
                self.send(200, result)
            except (ApprovalError, KeyError, ValueError, TypeError, json.JSONDecodeError) as exc:
                self.send(400, {"error": str(exc)})
            return

        if path == "/api/approval/reject":
            try:
                result = approval.reject(self._json_body())
                self.send(200, result)
            except (ApprovalError, KeyError, ValueError, TypeError, json.JSONDecodeError) as exc:
                self.send(400, {"error": str(exc)})
            return

        self.send(404, {"error": "not_found"})

    def log_message(self, fmt, *args):
        print("[forgeos]", fmt % args)


if __name__ == "__main__":
    print("ForgeOS Alpha 0.7.1 UI/API listening on http://0.0.0.0:8510")
    ThreadingHTTPServer(("127.0.0.1", 8520), Handler).serve_forever()
