# ForgeOS — Getting Started

ForgeOS is an AI-agent control plane. It is designed to let agents act autonomously while keeping sensitive authority outside the agent itself.

## 1. Run the regression suite

Requirements:

- Python 3.11+;
- `git`;
- `pytest`.

```bash
git clone https://github.com/kahaos/ForgeOS.git
cd ForgeOS
git checkout hardening-v1

python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip pytest
pytest -q
```

The hardening branch is configured so plain `pytest -q` runs the intended `tests/` suite.

## 2. Run the safe control-plane demo

```bash
python -m controlplane.demo
```

This uses the simulated/safe execution path. It does not perform real financial spending, retrieve real secrets, or deploy production infrastructure.

## 3. Try the isolated worker

The isolated worker requires a working Docker installation.

Check Docker first:

```bash
docker version
docker info
```

Then run the harmless demo:

```bash
python examples/isolated_worker_demo.py
```

The demo starts a short-lived container with the ForgeOS hardened profile:

- network disabled;
- read-only container root filesystem;
- all Linux capabilities dropped;
- `no-new-privileges` enabled;
- memory, CPU and PID limits;
- only a temporary workspace is mounted;
- host environment variables are not forwarded;
- no shell string is accepted.

Docker documents these isolation controls, including `--network none`, read-only filesystems, capability dropping, `no-new-privileges`, and resource limits. See the Docker security documentation before using the worker with real workloads.

## 4. Exercise the boundary

The worker is intentionally offline by default. A useful local smoke test is:

```bash
python - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory

from controlplane.isolated_worker import DockerIsolatedWorker

with TemporaryDirectory() as td:
    worker = DockerIsolatedWorker(image="python:3.12-alpine")
    result = worker.run(
        ["python", "-c", "import os, socket; print('HOME=', os.environ.get('HOME')); print('NET=', socket.create_connection(('1.1.1.1', 80), 1))"],
        workspace=Path(td),
    )
    print('returncode:', result.returncode)
    print('stdout:', result.stdout)
    print('stderr:', result.stderr)
PY
```

The network operation should fail because the hardened profile uses Docker's `none` network driver. Do not interpret this demo as a formal host-escape proof; container security depends on the host kernel, Docker configuration, runtime, images, and mount configuration.

## 5. GitHub Codespaces

You can also open the repository in a GitHub Codespace and run the Python regression suite there. GitHub Codespaces creates a development container for the repository, so the normal Python tests are a convenient way to inspect the project without installing Python locally.

The Docker-backed isolated-worker demo is a separate runtime requirement: a Codespace's development container does not automatically mean that a usable Docker daemon is available to nested workloads. If Docker is unavailable, run the isolated-worker demo on a Linux machine or VPS with Docker configured.

## Security model

The isolated worker is **not** a second authorization system. ForgeOS authorization remains the source of truth. The worker is the constrained execution boundary reached only after a valid ForgeOS execution authorization has been issued.

The default security profile is deliberately restrictive. Future integrations should add explicit capability profiles rather than weakening the default profile globally. For example, a future Git integration may need narrowly scoped repository access and controlled network egress, but that should be represented as an explicit policy/capability rather than changing the offline baseline.

## Current limitations

This milestone is development software, not a production security guarantee.

- The default profile is offline and therefore cannot perform operations that require network access.
- Container images are currently specified by image reference; production deployments should pin trusted images by digest and manage image provenance.
- Docker itself is a privileged security boundary on many installations. Protect access to the Docker daemon and never expose an unauthenticated Docker API.
- Real Git/GitHub/cloud/secret integrations remain separate roadmap work.
