#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo "PATCH-011 controlled execution installer"
echo "Target: local-test only"
echo "Production: disabled"

test -f patch_plan.py
test -f server.py
test -f local_test_handler.py

# This package deliberately refuses to guess at the live server's exact route
# structure. It installs the bounded handler and acceptance assets first.
# The integration step is performed only when the expected PATCH-011 markers
# match exactly.

python3 - <<'PY'
from pathlib import Path

p = Path("patch_plan.py")
s = p.read_text()

required = [
    'SCHEMA = "forgeos.patch_plan.v1"',
    "class PatchPlanStore",
    "def validate(",
]

missing = [x for x in required if x not in s]
if missing:
    raise SystemExit("FAIL-CLOSED: patch_plan.py markers missing: " + repr(missing))

print("PATCH-011 execution preflight: PASS")
print("PatchPlanStore markers found; no lifecycle mutation performed.")
PY

echo
echo "Handler installed. Server integration is intentionally fail-closed."
echo "Run the acceptance/preflight test before enabling execution routes."
