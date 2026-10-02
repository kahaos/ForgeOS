#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/forgeos/alpha/forgeos_alpha_0_7/forgeos_product"
PY="/opt/forgeos/.venv/bin/python"
cd "$ROOT"

TS="$(date -u +%Y%m%dT%H%M%SZ)"
echo "=== ForgeOS PATCH-012 / freeze preparation ==="
echo "ROOT=$ROOT"

# Backup live execution module before the evidence-path fix.
sudo cp patch_011_execution.py "patch_011_execution.py.bak_patch012_${TS}"

# Fix evidence path: the handler returns 'artifact', not 'path'.
sudo "$PY" - <<'PY'
from pathlib import Path
p = Path("patch_011_execution.py")
s = p.read_text()
old = '"path": result.get("path"),'
new = '"path": result.get("artifact"),'
if old not in s:
    raise SystemExit("Expected evidence path line not found; refusing to mutate.")
p.write_text(s.replace(old, new, 1))
print("Evidence path fix applied.")
PY

"$PY" -m py_compile patch_011_execution.py

# Create a fresh acceptance plan; do not mutate historical PLAN-000004.
"$PY" - <<'PY'
import json, urllib.request

base = "http://127.0.0.1:8510"
payload = {
    "plan_id": "PLAN-000005",
    "project_id": "project-0001",
    "patches": [{"patch_id": "PATCH-B", "dependencies": []}]
}
def post(path, obj):
    req = urllib.request.Request(
        base + path,
        data=json.dumps(obj).encode(),
        headers={"Content-Type":"application/json"},
        method="POST")
    with urllib.request.urlopen(req, timeout=10) as r:
        print(path, r.status, r.read().decode())

post("/api/patch-plan/create", payload)
post("/api/patch-plan/validate", {"actor":"human"})
PY

# Execute fresh patch and capture response.
curl -fsS -X POST http://127.0.0.1:8510/api/patch-plan/execute \
  -H 'Content-Type: application/json' \
  -d '{"project_id":"project-0001","target":"local-test","patch_id":"PATCH-B","actor":"human"}' \
  | tee /tmp/forgeos_patch012_execute.json

# Verify evidence path is populated and receipt is complete.
"$PY" - <<'PY'
import json, urllib.request, hashlib
with urllib.request.urlopen("http://127.0.0.1:8510/api/patch-plan", timeout=10) as r:
    data=json.load(r)
plan=data["plan"]
patch=next(x for x in plan["patches"] if x["patch_id"]=="PATCH-B")
assert patch["status"]=="COMPLETED", patch
assert patch["evidence"], patch
assert patch["evidence"][0]["path"] == patch["execution"]["result"]["artifact"], patch
assert patch["receipt"]["evidence"][0]["path"] == patch["execution"]["result"]["artifact"], patch
artifact=patch["execution"]["result"]["artifact"]
digest=hashlib.sha256(open(artifact,"rb").read()).hexdigest()
assert digest == patch["execution"]["result"]["sha256"]
assert digest == patch["verification"]["sha256"]
print("PATCH-012 acceptance: PASS")
print("Evidence path:", patch["evidence"][0]["path"])
print("Receipt status:", patch["receipt"]["status"])
print("Artifact SHA256:", digest)
PY

# Replay must remain blocked.
HTTP="$(curl -s -o /tmp/forgeos_patch012_replay.json -w '%{http_code}' \
  -X POST http://127.0.0.1:8510/api/patch-plan/execute \
  -H 'Content-Type: application/json' \
  -d '{"project_id":"project-0001","target":"local-test","patch_id":"PATCH-B","actor":"human"}')"
test "$HTTP" = "409"
echo "Replay protection: PASS (HTTP $HTTP)"

# Create a fresh freeze record from the accepted live UI and governance state.
mkdir -p "ui_freeze_0_8"
cp index.html "ui_freeze_0_8/index.html"
UI_SHA="$(sha256sum ui_freeze_0_8/index.html | awk '{print $1}')"

"$PY" - <<PY
import json, urllib.request
status=json.load(urllib.request.urlopen("http://127.0.0.1:8510/api/status"))
life=json.load(urllib.request.urlopen("http://127.0.0.1:8510/api/lifecycle"))
plan=json.load(urllib.request.urlopen("http://127.0.0.1:8510/api/patch-plan"))
p=next(x for x in plan["plan"]["patches"] if x["patch_id"]=="PATCH-B")
open("ui_freeze_0_8/PATCH-012_ACCEPTANCE.md","w").write(f"""# PATCH-012 Evidence & Receipt Integrity — Acceptance

Status: ACCEPTED
Plan: PLAN-000005
Patch: PATCH-B
Project: project-0001
Target: local-test
Patch status: {p["status"]}
Evidence path: {p["evidence"][0]["path"]}
Receipt status: {p["receipt"]["status"]}
Artifact SHA256: {p["execution"]["result"]["sha256"]}
Replay protection: PASS (HTTP 409)
Production: {status["production_enabled"]}
Lifecycle: {life["current_state"]}
Next governed state: {life["next_state"]}
""")
open("ui_freeze_0_8/PATCH-011_012_CHANGELOG.md","w").write("""# ForgeOS Alpha 0.8 — Changelog

## PATCH-011 — Patch Plan Engine
- Added persistent governed patch-plan storage.
- Added dependency validation and cycle detection.
- Added plan digests and append-only plan audit.
- Added controlled registered-handler execution for `local-test`.
- Added independent verification, execution receipts and replay protection.
- Added project/target binding and production fail-closed behavior.
- Historical acceptance plan: PLAN-000004 / PATCH-A.

## PATCH-012 — Evidence & Receipt Integrity
- Corrected evidence and receipt evidence path binding to the handler's `artifact` field.
- Created fresh acceptance plan PLAN-000005 / PATCH-B without modifying historical PLAN-000004.
- Executed and independently verified PATCH-B against `local-test`.
- Verified artifact SHA-256 consistency across execution result, verification and evidence.
- Verified replay protection remains enforced after completion.
- Prepared a new UI/governance freeze record.
""")
open("ui_freeze_0_8/FORGEOS_ALPHA_0_8_FREEZE.md","w").write(f"""# ForgeOS Alpha 0.8 — Freeze Record

Status: FROZEN
UI baseline SHA256: {UI_SHA}
Lifecycle: {life["current_state"]}
Next governed state: {life["next_state"]}
Current release: {life["current_release"]}
Deployment target: {life["deployment_target"]}
Production: DISABLED
Governance: BACKEND AUTHORITATIVE
PATCH-009: E2E ACCEPTED
PATCH-010: UI 2.0 FREEZE
PATCH-011: EXECUTION FOUNDATION ACCEPTED
PATCH-012: EVIDENCE & RECEIPT INTEGRITY ACCEPTED
Fresh acceptance plan: PLAN-000005 / PATCH-B

This freeze records the accepted Alpha 0.8 baseline.
No lifecycle transition is performed by the freeze operation.
""")
print("Freeze records written.")
PY

cp "ui_freeze_0_8/FORGEOS_ALPHA_0_8_FREEZE.md" "FORGEOS_ALPHA_0_8_FREEZE.md"
cp "ui_freeze_0_8/PATCH-011_012_CHANGELOG.md" "FORGEOS_ALPHA_0_8_CHANGELOG.md"

zip -qr "forgeos_alpha_0_8_freeze_archive.zip" \
  ui_freeze_0_8/FORGEOS_ALPHA_0_8_FREEZE.md \
  ui_freeze_0_8/PATCH-012_ACCEPTANCE.md \
  ui_freeze_0_8/PATCH-011_012_CHANGELOG.md \
  ui_freeze_0_8/PATCH-010_UI_2_0_FREEZE.md \
  ui_freeze_0_8/index.html \
  FORGEOS_ALPHA_0_8_FREEZE.md \
  FORGEOS_ALPHA_0_8_CHANGELOG.md

echo
echo "=== FREEZE HASHES ==="
sha256sum ui_freeze_0_8/index.html FORGEOS_ALPHA_0_8_FREEZE.md FORGEOS_ALPHA_0_8_CHANGELOG.md forgeos_alpha_0_8_freeze_archive.zip
echo
echo "Archive created: $ROOT/forgeos_alpha_0_8_freeze_archive.zip"
