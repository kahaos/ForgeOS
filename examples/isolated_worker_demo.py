"""Run a harmless command inside the ForgeOS hardened worker boundary."""

from pathlib import Path
from tempfile import TemporaryDirectory

from controlplane.isolated_worker import DockerIsolatedWorker


with TemporaryDirectory(prefix="forgeos-sandbox-") as tmp:
    workspace = Path(tmp)
    worker = DockerIsolatedWorker(image="python:3.12-alpine")
    result = worker.run(
        [
            "python",
            "-c",
            "from pathlib import Path; print('ForgeOS sandbox OK'); print(Path.cwd())",
        ],
        workspace=workspace,
    )
    print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="")
    raise SystemExit(result.returncode)
