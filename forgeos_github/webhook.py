import hashlib
import hmac
import json

def verify_signature(body: bytes, signature_header: str, secret: str) -> bool:
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)

def parse_event(body: bytes, event_name: str):
    data = json.loads(body.decode("utf-8"))
    return {
        "event": event_name,
        "delivery_id": data.get("installation", {}).get("id") or data.get("delivery_id"),
        "action": data.get("action"),
        "repository": (data.get("repository") or {}).get("full_name"),
        "ref": data.get("ref"),
        "sha": ((data.get("after") or "") if event_name == "push" else
                ((data.get("pull_request") or {}).get("head") or {}).get("sha")),
        "raw": data,
    }
