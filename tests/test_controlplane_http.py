from __future__ import annotations

import http.client
import json
import threading

from controlplane.api import ApprovalAPI
from controlplane.api_server import ApprovalHTTPServer
from controlplane.store import ControlPlane


def test_http_server_routes_real_json_requests(tmp_path):
    cp = ControlPlane(tmp_path / "controlplane")
    cp.register("agent-1", owner="tester", capabilities=["GIT_PUSH"])
    server = ApprovalHTTPServer(("127.0.0.1", 0), ApprovalAPI(cp))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        body = json.dumps(
            {
                "agent_id": "agent-1",
                "tool": "git",
                "action": "push",
                "target": "test-repo",
            }
        )
        conn.request(
            "POST",
            "/approvals/request",
            body=body,
            headers={"Content-Type": "application/json"},
        )
        response = conn.getresponse()
        pending = json.loads(response.read())
        assert response.status == 202
        approval_id = pending["approval_id"]

        conn.request("GET", "/approvals/pending")
        response = conn.getresponse()
        pending_list = json.loads(response.read())
        assert response.status == 200
        assert pending_list[0]["id"] == approval_id

        conn.request(
            "POST",
            f"/approvals/{approval_id}/approve",
            body=json.dumps({"actor": "human"}),
            headers={"Content-Type": "application/json"},
        )
        response = conn.getresponse()
        approved = json.loads(response.read())
        assert response.status == 200
        assert approved["verdict"] == "allow"
        assert cp.approvals[approval_id]["status"] == "approved"
        conn.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
