#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
cp patch_plan.py "patch_plan.py.bak_patch011_acceptance_${STAMP}"
cp server.py "server.py.bak_patch011_acceptance_${STAMP}"
cp "$(dirname "$0")/patch_011_execution_acceptance.py" ./patch_011_execution_acceptance.py
cp "$(dirname "$0")/test_patch_011_execution_acceptance.py" ./test_patch_011_execution_acceptance.py
echo "PATCH-011 controlled execution acceptance package installed."
echo "Backups created:"
echo "  patch_plan.py.bak_patch011_acceptance_${STAMP}"
echo "  server.py.bak_patch011_acceptance_${STAMP}"
echo "IMPORTANT: this package installs the execution engine and tests only."
echo "The HTTP execution route must be added and tested before live execution is enabled."
echo "Production remains disabled."
