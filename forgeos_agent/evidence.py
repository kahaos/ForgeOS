import hashlib,json,time
from pathlib import Path

def record(root, run_id, kind, payload, summary):
    raw=payload if isinstance(payload,bytes) else json.dumps(payload,sort_keys=True,default=str).encode()
    digest=hashlib.sha256(raw).hexdigest()
    eid=f'EV-{int(time.time()*1000)}-{digest[:12]}'
    d=Path(root)/'evidence'/run_id; d.mkdir(parents=True,exist_ok=True)
    (d/f'{eid}.json').write_bytes(raw)
    meta={'evidence_id':eid,'run_id':run_id,'kind':kind,'payload_sha256':digest,'summary':summary}
    (d/f'{eid}.meta.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
    return meta
