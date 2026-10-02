#!/usr/bin/env python3
from pathlib import Path
s=Path("index.html.patches007_008").read_text().lower()
required=[
"system health",
"production safety",
"@media (max-width: 850px)",
"@media (max-width:520px)",
"overflow-x:auto",
"grid-template-columns:1fr!important",
"/api/status",
"/api/lifecycle",
"/api/audit",
"production_enabled",
"authoritative"
]
missing=[x for x in required if x not in s]
if missing:
    print("PATCHES-007-008 UI contract: FAIL")
    print("\n".join(missing))
    raise SystemExit(1)
print("PATCHES-007-008 UI contract: PASS")
