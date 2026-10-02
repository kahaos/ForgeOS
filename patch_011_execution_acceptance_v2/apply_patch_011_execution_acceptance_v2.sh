#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
cp patch_plan.py "patch_plan.py.bak_patch011_acceptance_v2_${STAMP}"
cp server.py "server.py.bak_patch011_acceptance_v2_${STAMP}"
cp "$(dirname "$0")/patch_011_execution_acceptance_v2.py" ./patch_011_execution_acceptance_v2.py
cp "$(dirname "$0")/test_patch_011_execution_acceptance_v2.py" ./test_patch_011_execution_acceptance_v2.py
echo "PATCH-011 controlled execution acceptance v2 installed."
echo "Backups created:"
echo "  patch_plan.py.bak_patch011_acceptance_v2_${STAMP}"
echo "  server.py.bak_patch011_acceptance_v2_${STAMP}"
echo "Production remains disabled."
