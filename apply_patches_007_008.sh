#!/usr/bin/env bash
set -euo pipefail
BASE="/opt/forgeos/alpha/forgeos_alpha_0_7/forgeos_product"
cd "$BASE"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
cp -a index.html "index.html.bak_ui2_patches007_008_${STAMP}"
cp index.html.patches007_008 index.html
echo "PATCH-007 and PATCH-008 applied: System Health + Responsive Mobile."
echo "Backup: $BASE/index.html.bak_ui2_patches007_008_${STAMP}"
echo "Backend governance, API routes, lifecycle state and production settings were not modified."
