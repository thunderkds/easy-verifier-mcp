# TASK_GUIDE — T103: Make the shared scoring container the primary documented path (docs + spec after T101)
**Date**: 2026-10-15
**Complexity Level**: C1
**Risk Level**: Medium (amends security/safety requirements NFR-007, NFR-013 and the transport requirement FR-019a)
**Priority**: P1
**Assigned agent**: backend-developer
**Agent guide**: `.claude/agents/backend.md`
**Depends on**: T101 (merged, `1d5c2fc`)

## Context (Supervisor)

T101 / DDR-0013 (`docs/ddr/0013-one-shared-http-container.md`, local-only) added one shared, long-running
scoring container: `easy-verifier-mcp --transport streamable-http` serving `/mcp` on
`127.0.0.1:$EASY_VERIFIER_PORT` (default `8766`), compose service `scorer`, `network_mode: host`, the
workspace mounted read-only at the identical host path, and reports written to
`$EASY_VERIFIER_REPORTS_DIR/<repo directory name>/` (compose default `~/.easy-verifier-reports`).
`README.md` and `docs/DOCKER_MCP_GUIDE.md` were updated by T101 and already lead with it.

**User decision 2026-10-15 ("2")**: the shared container is now the **primary** path; per-session stdio
(`docker run -i`, no network) stays fully supported as the alternative. The code default of the bare
`easy-verifier-mcp` command stays **stdio** — this task changes no code and no default.

A docs audit on 2026-10-15 found these documents still describe the pre-T101 world.

## Acceptance Criteria

| # | Criterion (testable) |
|---|----------------------|
| 1 | `PRD.md` FR-019a no longer says stdio is "required": it states the shared streamable-HTTP container (FR-019b, DDR-0013) is the primary deployment and stdio is the supported alternative and the bare-command default. Add an "**Amended 2026-10-15 (T103)**" marker. FR-019b's loopback-only rule is unchanged |
| 2 | `PRD.md` FR-017, NFR-007 and NFR-013 each name the one exception: when `EASY_VERIFIER_REPORTS_DIR` is set, reports go to `<that dir>/<repo name>/` outside the target repo, and in the shared container the target repo is mounted fully read-only (no writable `reports/`). Same amended marker. NFR-006 matches AC1. "Never execute code from the target repository" stays word-for-word |
| 3 | `PROJECT_SPEC.md`: Deployment target (Project Identity) names the shared container as primary with stdio as the alternative; constraint 5 adds the `EASY_VERIFIER_REPORTS_DIR` exception; constraint 6 matches AC1 and keeps "bind `127.0.0.1` only — never `0.0.0.0`"; one Memory/Insights row dated 2026-10-15 for T103 |
| 4 | `docs/LOCAL_MCP_GUIDE.md`: the HTTP section documents `--transport streamable-http` (`/mcp`, `EASY_VERIFIER_PORT`, default 8766, loopback only, no authentication — any local process can reach it) **before** the legacy `--http`; the reports line says `<repo>/reports/` by default, or `$EASY_VERIFIER_REPORTS_DIR/<repo name>/` when set; points to `DOCKER_MCP_GUIDE.md` for the shared container |
| 5 | `.claude/skills/verify/SKILL.md` gains a "Shared container (HTTP)" surface: `EASY_VERIFIER_WORKSPACE=<abs parent> docker compose up -d scorer`, register/probe `http://127.0.0.1:8766/mcp`, a tool call with an absolute `repo`, report lands under the reports dir, `docker compose down scorer`. Commands must be copied from `README.md`/`DOCKER_MCP_GUIDE.md`/`compose.yaml`, never invented |
| 6 | `docs/RELEASE_GUIDE.md` says plainly that `scripts/verify_release_gate.sh` covers the stdio boundary only, and adds the shared-container checks to "Supplemental checks" (`python -m pytest tests/test_t101_shared_container.py -q`, plus a pointer to the verify skill's HTTP surface). Do **not** change the script |
| 7 | New test `tests/test_t103_docs_shared_container.py` pins AC1–AC6 by content (pattern of `tests/test_t025_image_publish.py` / `tests/test_t018_readme.py`): red on the pre-change docs, green after. Also asserts no doc in scope still calls stdio "required" |
| 8 | Full suite passes (apart from known Docker-dependent tests if Docker is unavailable — name them) and `ruff check src tests` is clean |

## Approach

Text edits only. Match each document's existing voice and length; amend in place, never rewrite whole
sections. Keep historical rows (PRD issue #13, the 2026-08-14 spec insight) as history — do not edit them.

## Files Must NOT Touch

`src/`, `scripts/`, `compose.yaml`, `Dockerfile`, `README.md`, `docs/DOCKER_MCP_GUIDE.md` (already current),
any other task guide or review, and T025's branch.

## Out of scope (recorded as follow-ups, not done here)

- The HTML report advisory still says "inside the evaluated repository" when `EASY_VERIFIER_REPORTS_DIR`
  is set (T101 review follow-up; touches `src/`).
- `scripts/verify_release_gate.sh` has no shared-container check (script work).

## Verification Command

`.venv` is broken (system Python is 3.14; see `memory/learnings.md`, 2026-10-15). Use:

```bash
M=<absolute path of the main checkout>
PYTHONPATH=src:$M/.venv/lib/python3.12/site-packages /usr/bin/python3.12 -m pytest -q tests/test_t103_docs_shared_container.py
PYTHONPATH=src:$M/.venv/lib/python3.12/site-packages /usr/bin/python3.12 -m pytest -q
PYTHONPATH=src:$M/.venv/lib/python3.12/site-packages /usr/bin/python3.12 -m ruff check src tests
```

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T103.md`.

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T103.md`. BEFORE = verbatim prior text of FR-019a and constraint 6.

## UI / Design Acceptance Criteria

> N/A — no UI. All three UI Evidence rows are ☐ N/A.
