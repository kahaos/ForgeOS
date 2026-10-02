#!/usr/bin/env python3
import json, urllib.request, sys

BASE = "http://127.0.0.1:8510"

def get(path):
    req = urllib.request.Request(BASE + path, headers={"Cache-Control":"no-cache"})
    with urllib.request.urlopen(req, timeout=5) as r:
        return r.status, r.read().decode()

def fail(msg):
    print("PATCH-009 E2E UI ACCEPTANCE: FAIL")
    print(msg)
    raise SystemExit(1)

try:
    status_code, html = get("/")
    if status_code != 200: fail(f"root HTTP {status_code}")

    sc, status_raw = get("/api/status")
    if sc != 200: fail(f"/api/status HTTP {sc}")
    status = json.loads(status_raw)

    lc, lifecycle_raw = get("/api/lifecycle")
    if lc != 200: fail(f"/api/lifecycle HTTP {lc}")
    lifecycle = json.loads(lifecycle_raw)

    ac, audit_raw = get("/api/audit")
    if ac != 200: fail(f"/api/audit HTTP {ac}")
    audit = json.loads(audit_raw)

    checks = {
        "healthy": status.get("status") == "HEALTHY",
        "governance_ready": status.get("system", {}).get("governance_core") == "READY",
        "api_ready": status.get("system", {}).get("api") == "READY",
        "ui_ready": status.get("system", {}).get("ui") == "READY",
        "production_disabled": status.get("system", {}).get("production_enabled") is False,
        "authoritative": status.get("governance", {}).get("authoritative") is True,
        "project": status.get("project", {}).get("project_id") == "project-0001",
        "release": status.get("current_release") == "REL-000002",
        "target": status.get("target") == "local-test",
        "state": lifecycle.get("state") == "DEPLOYMENT_PRECHECKED",
        "next_gate": "DEPLOYMENT_APPROVED" in lifecycle.get("allowed_next_states", []),
        "audit_events": isinstance(audit.get("events"), list) and len(audit["events"]) > 0,
        "nav_projects": "Projects" in html,
        "nav_runs": "Runs" in html,
        "nav_releases": "Releases" in html,
        "nav_deployments": "Deployments" in html,
        "nav_evidence": "Evidence" in html,
        "nav_audit": "Audit" in html,
        "nav_policies": "Policies" in html,
        "nav_system": "System" in html,
        "responsive_850": "@media (max-width: 850px)" in html,
        "responsive_520": "@media (max-width:520px)" in html,
        "backend_authority_text": "backend remains the authoritative security boundary" in html.lower(),
    }
    bad = [k for k,v in checks.items() if not v]
    if bad: fail("failed checks: " + ", ".join(bad))

    print("PATCH-009 E2E UI ACCEPTANCE: PASS")
    print("HTTP/API health: PASS")
    print("Lifecycle binding: DEPLOYMENT_PRECHECKED -> DEPLOYMENT_APPROVED")
    print("Production: DISABLED")
    print("Target: local-test")
    print("UI navigation: PASS")
    print("Responsive mobile contract: PASS")
    print("Audit feed: PASS")
    print("No lifecycle mutation performed by this test.")
except Exception as e:
    fail(str(e))
