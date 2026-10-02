import os, shlex, shutil
from pathlib import Path

SAFE_ENV = {
    "PATH", "LANG", "LC_ALL", "LC_CTYPE", "LC_MESSAGES",
    "TZ", "TERM", "PYTHONUNBUFFERED", "PYTHONDONTWRITEBYTECODE",
}
SENSITIVE_MARKERS = ("TOKEN", "SECRET", "PASSWORD", "PRIVATE_KEY", "API_KEY", "CREDENTIAL")

class SandboxError(Exception):
    pass

def _sanitised_env(workspace):
    env = {}
    for k, v in os.environ.items():
        ku = k.upper()
        if any(marker in ku for marker in SENSITIVE_MARKERS):
            continue
        if k in SAFE_ENV or k.startswith("LC_"):
            env[k] = v
    ws = str(Path(workspace).resolve())
    home = Path(ws) / ".agent-home"
    tmp = Path(ws) / ".agent-tmp"
    home.mkdir(parents=True, exist_ok=True)
    tmp.mkdir(parents=True, exist_ok=True)
    env["HOME"] = str(home)
    env["TMPDIR"] = str(tmp)
    env["TEMP"] = str(tmp)
    env["TMP"] = str(tmp)
    return env

def build_execution(command, workspace, forge_root):
    if not isinstance(command, str) or not command.strip():
        raise SandboxError("EMPTY_COMMAND")
    argv = shlex.split(command)
    if not argv:
        raise SandboxError("EMPTY_COMMAND")
    env = _sanitised_env(workspace)

    mode = os.getenv("FORGEOS_AGENT_SANDBOX", "auto").lower()
    bwrap = shutil.which("bwrap")
    if mode == "required" and not bwrap:
        raise SandboxError("OS_SANDBOX_UNAVAILABLE")
    if mode in ("off", "disabled") or not bwrap:
        return argv, env

    ws = str(Path(workspace).resolve())
    venv = Path("/opt/forgeos/.venv")
    wrapped = [
        bwrap,
        "--die-with-parent",
        "--new-session",
        "--unshare-pid",
        "--unshare-ipc",
        "--unshare-uts",
        "--unshare-net",
        "--ro-bind", "/usr", "/usr",
        "--ro-bind", "/bin", "/bin",
        "--ro-bind", "/lib", "/lib",
        "--ro-bind", "/lib64", "/lib64",
        "--tmpfs", "/etc",
        "--ro-bind", "/etc/localtime", "/etc/localtime",
        "--ro-bind", "/etc/ssl", "/etc/ssl",
        "--proc", "/proc",
        "--dev", "/dev",
        "--tmpfs", "/tmp",
        "--bind", ws, "/workspace",
        "--chdir", "/workspace",
    ]
    if venv.exists():
        wrapped += ["--ro-bind", str(venv), str(venv)]
    wrapped += ["--"] + argv
    return wrapped, env
