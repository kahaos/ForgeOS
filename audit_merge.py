from pathlib import Path
import json

def combined_audit(store):
    events = list(store.audit())
    approval_file = Path(store.root) / "data" / "approval_audit.jsonl"
    if approval_file.exists():
        for line in approval_file.read_text().splitlines():
            if line.strip():
                events.append(json.loads(line))
    events.sort(key=lambda event: event.get("timestamp", ""))
    return events
