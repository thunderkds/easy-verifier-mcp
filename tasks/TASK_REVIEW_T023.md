# TASK_REVIEW — T023: final v1 release verification

## Status

**In progress; release is not ready.** The host and static gates pass, but the
required Docker boundary is unavailable and the candidate is not clean or
confirmed published. The gate correctly fails closed.

## Candidate identity

| Check | Result |
|---|---|
| Local commit | `8a07c2af57fb85c12293147300140aebfb8a8352` |
| Branch | `develop` |
| Worktree | **dirty**; T017 hardening, T023 planning, Kanban, README, and review changes are present |
| `github/develop` confirmation | **NOT VERIFIED**; `git ls-remote github refs/heads/develop` failed with `Could not resolve hostname github.com` |

## Evidence

| Check | Result | Evidence |
|---|---|---|
| Release wrapper | **blocked / fail closed** | `bash scripts/verify_release_gate.sh` -> host integration `17 passed, 3 skipped in 8.42s`; required container selection then failed with two explicit Docker-unavailable failures: `permission denied while trying to connect to the Docker API at unix:///var/run/docker.sock`; exit `1` |
| Host integration | pass | Executed by the release wrapper; `17 passed, 3 skipped in 8.42s`. Skips are not release proof. |
| Docker integration | **NOT VERIFIED** | Required run failed before container tests could execute because the Docker socket is inaccessible. |
| MCP stdio boundary | **NOT VERIFIED** | This run did not reach the container/stdio stage; the prior independent T017 probe remains evidence of an unresolved stdio boundary, not a pass. |
| Full regression | pass | `PYTHONPATH=src /home/hungnguyenhuu/workspace/training/phuongbui/ai-training/travel_chatbot/.venv/bin/python -m pytest -q --tb=short` -> `586 passed, 4 skipped, 1 warning in 40.96s` |
| Ruff | pass | `ruff check src tests` -> `All checks passed!` |
| Formatting | pass | `ruff format --check src tests` -> `58 files already formatted` |
| Shell syntax | pass | `bash -n scripts/verify_release_gate.sh` -> exit `0` |
| Compose configuration | pass | `docker compose config --quiet` -> exit `0`; this does not prove daemon access |
| README/documentation tests | pass | `PYTHONPATH=src /home/hungnguyenhuu/workspace/training/phuongbui/ai-training/travel_chatbot/.venv/bin/python -m pytest tests/test_t018_readme.py -q` -> `6 passed, 1 skipped in 5.23s` |
| Diff check | pass | `git diff --check` -> exit `0` |

## Documentation truth pass

- `README.md` now names `bash scripts/verify_release_gate.sh` as the final gate and states that
  unavailable Docker/MCP stdio proof is `NOT VERIFIED` and non-zero.
- `docs/RELEASE_GUIDE.md` now defines prerequisites, the exact wrapper, supplemental checks,
  expected result, evidence requirements, and blocked-outcome semantics.
- Neither document claims that the current candidate is release-ready.

## Remaining gate

Re-run from a clean, published candidate in an environment with Docker socket access and a working
MCP stdio process boundary:

```bash
bash scripts/verify_release_gate.sh
```

T023 must remain open until that command exits `0`, all KPI rows report `PASS`, the candidate
identity is confirmed against `github/develop`, and the exact evidence is recorded here.
