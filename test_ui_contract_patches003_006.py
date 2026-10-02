#!/usr/bin/env python3
from pathlib import Path
s=Path("index.html.patches003_006").read_text().lower()
required=[
"project workspace",
"run & evidence workspace",
"release & deployment workspace",
"audit timeline",
"/api/status",
"/api/lifecycle",
"/api/audit",
"deployment_approved",
"remains authoritative",
"append-only audit timeline",
]
missing=[x for x in required if x not in s]
if missing:
    print("PATCHES-003-006 UI contract: FAIL")
    print("\n".join(missing))
    raise SystemExit(1)
print("PATCHES-003-006 UI contract: PASS")
