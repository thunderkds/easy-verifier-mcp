# TASK_REVIEW — T016: least-privilege container packaging

## Status

**Blocked at the live-container verification gate.** Implementation and static
verification are complete, but this Codex runner is denied access to
`/var/run/docker.sock`. T016 must not move to Ready for Review or Done until the
checked-in verifier passes against a real Docker daemon.

## Evidence

| Check | Result | Notes / output snippet |
|-------|--------|------------------------|
| New static acceptance tests | pass | `PYTHONPATH=src python -m pytest tests/test_t016_container_config.py -q` -> `4 passed` |
| README truth tests | pass | `PYTHONPATH=src python -m pytest tests/test_t018_readme.py -q` -> `7 passed` |
| Full regression suite | pass | `PYTHONPATH=src python -m pytest -q` -> `441 passed` |
| Compose expansion | pass | `docker compose config --quiet` exits 0 and static tests inspect its JSON form |
| Verifier shell syntax | pass | `bash -n scripts/verify_container.sh` exits 0 |
| Live container verification | **blocked** | `docker info` -> permission denied opening `unix:///var/run/docker.sock` |

## Demonstration

**BEFORE** (captured 2026-09-02T09:45:37Z):

```text
missing Dockerfile
missing compose.yaml
missing .dockerignore
missing scripts/verify_container.sh
bash: scripts/verify_container.sh: No such file or directory
exit=127
```

**CURRENT**:

```text
$ EASY_VERIFIER_ALLOW_DOCKER_SKIP=1 bash scripts/verify_container.sh
SKIP: Docker daemon is unavailable

$ PYTHONPATH=src python -m pytest tests/test_t016_container_config.py -q
....                                                                     [100%]
4 passed
```

When run without the explicit CI-only skip variable, the verifier fails closed
if Docker is unavailable. On a Docker-capable host the required command remains:

```text
docker compose build && bash scripts/verify_container.sh
```

That live gate checks the real MCP initialization, ten-tool listing, two tool
calls, non-root UID, read-only target root, writable reports overlay, readable
Git metadata, disabled network, dropped capabilities, absent ports, read-only
container root, and report path normalization.
