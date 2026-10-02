from pathlib import Path

class IsolationError(Exception): pass

def safe_id(value: str, label: str):
    if not isinstance(value, str) or not value or any(c in value for c in '/\\') or '..' in value or '\x00' in value:
        raise IsolationError(f'invalid {label}')
    return value

def project_root(root: Path, project_id: str) -> Path:
    return Path(root) / 'projects' / safe_id(project_id, 'project id')

def run_root(root: Path, project_id: str, run_id: str) -> Path:
    return project_root(root, project_id) / 'runs' / safe_id(run_id, 'run id')

def assert_within(path: Path, root: Path) -> Path:
    p, r = Path(path).resolve(), Path(root).resolve()
    try: p.relative_to(r)
    except ValueError: raise IsolationError('PATH_ESCAPES_WORKSPACE')
    return p
