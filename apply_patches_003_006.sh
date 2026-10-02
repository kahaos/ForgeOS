#!/usr/bin/env bash
set -euo pipefail
BASE="/opt/forgeos/alpha/forgeos_alpha_0_7/forgeos_product"
cd "$BASE"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
cp -a index.html "index.html.bak_ui2_patches003_006_${STAMP}"
cp index.html.patches003_006 index.html
echo "PATCH-003 through PATCH-006 applied as a sequential UI bundle."
echo "Backup: $BASE/index.html.bak_ui2_patches003_006_${STAMP}"
echo "Backend governance, API routes, lifecycle state and production settings were not modified."
