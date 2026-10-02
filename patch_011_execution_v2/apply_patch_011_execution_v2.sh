#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/forgeos/alpha/forgeos_alpha_0_7/forgeos_product"
cd "$ROOT"

echo "PATCH-011 execution integration installer"
echo "Target: local-test only"
echo "Production: disabled"

test -f patch_plan.py
test -f server.py
test -f patch_011_execution/local_test_handler.py

# Backups are created before any integration mutation.
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
sudo cp patch_plan.py "patch_plan.py.bak_patch011_exec_${STAMP}"
sudo cp server.py "server.py.bak_patch011_exec_${STAMP}"

echo "Backups created:"
echo "  patch_plan.py.bak_patch011_exec_${STAMP}"
echo "  server.py.bak_patch011_exec_${STAMP}"

# This installer only installs the handler and documentation. It intentionally
# does NOT mutate server.py or patch_plan.py automatically.
echo "Handler package verified."
echo "FAIL-CLOSED: live execution integration requires the acceptance patch."
echo "No lifecycle transition performed."
