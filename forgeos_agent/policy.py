import fnmatch, shlex
from pathlib import PurePosixPath

class PolicyError(Exception): pass

def normalise_path(path):
    if not isinstance(path,str) or not path or path.startswith('/') or '\x00' in path:
        raise PolicyError('PATH_TRAVERSAL')
    p=path.replace('\\','/')
    if '..' in PurePosixPath(p).parts: raise PolicyError('PATH_TRAVERSAL')
    return str(PurePosixPath(p))

def check_path(path, allowed, forbidden):
    try: p=normalise_path(path)
    except PolicyError as e: return False,str(e)
    for rule in forbidden:
        if fnmatch.fnmatch(p, rule) or fnmatch.fnmatch(p, rule.rstrip('/')+'/**'): return False,'FORBIDDEN_PATH'
    if any(fnmatch.fnmatch(p,r) or fnmatch.fnmatch(p,r.rstrip('/')+'/**') for r in allowed): return True,'ALLOWED'
    return False,'OUT_OF_SCOPE'

def check_command(command, allowed):
    if not isinstance(command,str) or not command.strip(): return False,'EMPTY_COMMAND'
    try: argv=shlex.split(command)
    except ValueError: return False,'INVALID_COMMAND'
    if not argv or argv[0] not in set(allowed): return False,'COMMAND_NOT_ALLOWED'
    # Explicitly deny shell chaining/redirection so the allow-list cannot be bypassed.
    if any(x in command for x in ['&&','||',';','>','<','`','$(']): return False,'COMMAND_SYNTAX_NOT_ALLOWED'
    return True,'ALLOWED'
