#!/usr/bin/env bash
set -euo pipefail
BASE="/opt/forgeos/alpha/forgeos_alpha_0_7/forgeos_product"
cd "$BASE"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
cp -a index.html "index.html.bak_ui2_patch002_${STAMP}"
cp index.html.patch002 "$BASE/index.html"
echo "PATCH-002 applied: Lifecycle Command Centre."
echo "Backup: $BASE/index.html.bak_ui2_patch002_${STAMP}"
echo "Backend governance, API routes, lifecycle state and production settings were not modified."
