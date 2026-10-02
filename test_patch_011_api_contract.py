import json
import threading
import urllib.request
from pathlib import Path
from tempfile import TemporaryDirectory

import server


def request_json(base, method, path, body=None):
    data = None
    headers = {"Cache-Control": "no-cache"}

    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        base + path,
        data=data,
        headers=headers,
        method=method,
    )

    with urllib.request.urlopen(request, timeout=5) as response:
        return response.status, json.loads(response.read().decode())


def test_patch_plan_api_contract():
    with TemporaryDirectory() as tmp:
        root = Path(tmp)

        # Create an isolated ForgeOS state for this HTTP contract test.
        isolated_store = server.GovernanceStore(root)
        isolated_patch_plan = server.PatchPlanStore(root)

        old_store = server.store
        old_patch_plan = server.patch_plan

        httpd = None

        try:
            server.store = isolated_store
            server.patch_plan = isolated_patch_plan

            httpd = server.ThreadingHTTPServer(
                ("127.0.0.1", 0),
                server.Handler,
            )

            thread = threading.Thread(
                target=httpd.serve_forever,
                daemon=True,
            )
            thread.start()

            port = httpd.server_address[1]
            base = f"http://127.0.0.1:{port}"

            # Clean isolated instance starts empty.
            status, body = request_json(
                base,
                "GET",
                "/api/patch-plan",
            )

            assert status == 200
            assert body["status"] == "EMPTY"

            # Create the plan through the real HTTP API.
            status, body = request_json(
                base,
                "POST",
                "/api/patch-plan/create",
                {
                    "plan_id": "PLAN-API-TEST-001",
                    "project_id": "project-0001",
                    "patches": [
                        {
                            "patch_id": "PATCH-API-TEST-A",
                            "dependencies": [],
                        }
                    ],
                },
            )

            assert status == 201
            assert body["plan"]["schema"] == "forgeos.patch_plan.v1"
            assert body["plan"]["status"] == "PLANNED"
            assert body["plan"]["plan_id"] == "PLAN-API-TEST-001"
            assert body["plan"]["project_id"] == "project-0001"

            # Validate through the real HTTP API.
            status, body = request_json(
                base,
                "POST",
                "/api/patch-plan/validate",
                {
                    "actor": "api-test",
                },
            )

            assert status == 200
            assert body["plan"]["schema"] == "forgeos.patch_plan.v1"
            assert body["plan"]["status"] == "READY"
            assert body["plan"]["plan_id"] == "PLAN-API-TEST-001"
            assert body["plan"]["project_id"] == "project-0001"
            assert body["plan"]["validation"]["ok"] is True

            # GET must expose the authoritative validated state.
            status, body = request_json(
                base,
                "GET",
                "/api/patch-plan",
            )

            assert status == 200
            assert body["schema"] == "forgeos.patch_plan.v1"
            assert body["status"] == "READY"
            assert body["plan_id"] == "PLAN-API-TEST-001"
            assert body["project_id"] == "project-0001"

            # Audit must contain the complete API lifecycle.
            status, body = request_json(
                base,
                "GET",
                "/api/patch-plan/audit",
            )

            assert status == 200
            assert body["schema"] == "forgeos.patch_plan_audit.v1"

            actions = [event["action"] for event in body["events"]]

            assert "PLAN_CREATED" in actions
            assert "PLAN_VALIDATED" in actions

            validation_events = [
                event
                for event in body["events"]
                if event["action"] == "PLAN_VALIDATED"
            ]

            assert validation_events
            assert validation_events[-1]["ok"] is True
            assert validation_events[-1]["plan_id"] == "PLAN-API-TEST-001"

        finally:
            if httpd is not None:
                httpd.shutdown()
                httpd.server_close()

            server.store = old_store
            server.patch_plan = old_patch_plan
