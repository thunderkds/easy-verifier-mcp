# TASK_REVIEW — T017: verification suite and release gate

## Status

**Host evidence passes; release remains blocked on container proof.** The suite is
independent of the per-task unit tests and does not modify `src/`.

## Evidence

| Check | Result | Evidence |
|---|---|---|
| Host integration suite | pass | `PYTHONPATH=src /home/hungnguyenhuu/workspace/training/phuongbui/ai-training/travel_chatbot/.venv/bin/python -m pytest tests/integration -q --tb=short` -> `17 passed, 3 skipped in 13.85s` with one pre-existing Pydantic warning. The skips are the two container proofs and the wrapper-only KPI test. |
| Full regression suite | pass | Compatible interpreter -> `586 passed, 4 skipped in 58.90s`; one upstream Pydantic warning. |
| Ruff and formatting | pass | `ruff check src tests` -> `All checks passed!`; `ruff format --check src tests` -> `58 files already formatted`. |
| Shell and diff checks | pass | `bash -n scripts/verify_release_gate.sh` and `git diff --check` both exit 0. |
| Release wrapper | **blocked / fail closed** | `bash scripts/verify_release_gate.sh` runs the host suite, then the required container tests fail with `permission denied while trying to connect to the Docker API at unix:///var/run/docker.sock`; exit 1. It does not convert unavailable Docker into a pass. |
| Security review | bounded substitution | The named `security-review` skill is unavailable in this Codex session. Direct review found no new production code, no network client, no secret fixture literals, and no writes outside temporary test targets/reports. |
| Code review | bounded substitution | The named `code-review` skill is unavailable in this Codex session. Manual P0-P3 review covered the integration helpers, adapter-boundary assertions, field-limited normalization, report scanner, and fail-closed wrapper. |
| MCP stdio process boundary | **NOT VERIFIED** | A direct stdio initialization probe under the provisioned Python 3.13/MCP environment produced no response before timeout, while in-process FastMCP calls passed. This remains an environment/runtime-boundary blocker; it is not converted to a pass. |

## Demonstration

The host run exercises kit-aware and standalone reports, all seven dimensions,
combined/score/discovery parity through CLI and in-process MCP, runtime-generated
secret shapes with exact expected fingerprints, findings rejection, and report
self-containment. The direct MCP stdio process boundary is **NOT VERIFIED** in
this environment. Container checks are
deliberately separate and require `T017_REQUIRE_DOCKER=1`, so a skipped Docker
probe cannot satisfy the release gate.

## Remaining gate

Run this exact command in a Docker-capable environment:

```bash
bash scripts/verify_release_gate.sh
```

T017 must not move to Done or be called release-ready until this command exits
0 with both container tests executed, `scripts/verify_container.sh` passing, and
the KPI summary reporting container parity as `PASS`.
