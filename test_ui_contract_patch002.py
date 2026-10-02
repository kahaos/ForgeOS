#!/usr/bin/env python3
from pathlib import Path
p=Path("index.html.patch002")
s=p.read_text()
required=[
"Lifecycle Command Centre",
"Current state",
"State history",
"Current release",
"Deployment target",
"Required human action",
"System health",
"Recent lifecycle events",
"/api/status",
"/api/lifecycle",
"/api/audit",
"DEPLOYMENT_APPROVED",
"Production disabled",
]
missing=[x for x in required if x not in s]
if missing:
    print("PATCH-002 UI contract: FAIL")
    print("\n".join(missing))
    raise SystemExit(1)
print("PATCH-002 UI contract: PASS")
