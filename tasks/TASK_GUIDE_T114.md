# TASK_GUIDE — T114: Blast-radius rated at project scope from the repository import graph
**Date**: 2026-10-17
**Complexity Level**: C2
**Risk Level**: Medium (new rated rules; blast-radius starts contributing to `overall`)
**Priority**: P1
**Assigned agent**: backend-developer
**Agent guide**: `.claude/agents/backend.md`

---

## Mandatory Startup (Do Not Skip)

1. Read `PROJECT_SPEC.md`, `memory/MEMORY.md`, this file, `.claude/agents/backend.md`
2. Apply the C2 process
3. Read `PRD.md` FR-086 (added with this guide); T113's index (`tasks/TASK_GUIDE_T113.md`)
4. Read `dimensions/blast_radius.py` (references, co-change, churn hotspots), `core/structure.py`
   (import resolution used by `top_level_import_cycles` / `layer_direction_violations` /
   `max_fan_in_changed`), `core/judge.py` blast-radius rules

---

## Requirement (Pillar 1)

User, 2026-10-17: *"the point for the blast radius is not good at all"* → proposal "blast-radius at
project scope: repo-wide import graph → most-imported files, churn × reach hotspots, untested
high-reach files", user: *"looks good, let spawn"*.

**Restated intent**:
> At project scope blast-radius reads one file and abstains (node-api: "all declared rating metrics
> abstained"). Using T113's index, build the **repository import graph** (the same import resolution
> architecture uses) and rate it with two project-scope rules (project defaults, pre-registered):
> - `high_reach_files_without_test_share` ≤ **0.20** — of the **high-reach files** (source files in the
>   top 10 % by in-repo fan-in, minimum fan-in 3, at least 1 file), the share with no covering test
>   (test-strategy's correspondence over the index, plus T112's symbol reference to any of the file's
>   declared public symbols);
> - `high_reach_churn_hotspot_share` ≤ **0.30** — of the high-reach files, the share that are also in
>   the top 10 % by git churn (last 400 non-merge commits; abstain below `MIN_CHURN_COMMITS`).
> Both list the files they count, with fan-in and churn, as cited evidence. Narrow scopes keep today's
> blast-radius behaviour unchanged.

**Out of scope**: new import resolvers per language, runtime call graphs, changes to architecture rules.

**Requirement Refs**: FR-086 (new), US-006.

### Requirement Fidelity Gate
- [x] Restated intent confirmed (user 2026-10-17)
- [x] Domain terms align with `PROJECT_SPEC.md` (adds **High-reach file** to the glossary)
- [x] Every AC traces to the Requirement
- [x] Requirement Refs exist in `PRD.md`

---

## Dependencies & Reachability

**Depends on**: T113
**Entry point**: `score_repository` at `project` scope, dimension `blast-radius`

---

## Acceptance Criteria

| # | Criterion (testable) |
|---|----------------------|
| 1 | Fan-in per source file computed over the whole index (in-repo imports only, third-party excluded); a synthetic repo with a known graph gives the exact fan-in table |
| 2 | High-reach set = top 10 % by fan-in, fan-in ≥ 3, ties included, at least 1 file; fewer than 1 qualifying file → both rules abstain with a stated reason |
| 3 | `high_reach_files_without_test_share` counts a file covered by name correspondence or by a test referencing one of its public symbols; cites the uncovered files with their fan-in |
| 4 | `high_reach_churn_hotspot_share` uses the existing churn ranking; abstains below `MIN_CHURN_COMMITS` or on a shallow clone with the existing warning text |
| 5 | Rules added to `judge.py` with project-default citation and an evaluation area; `areas_measured` updates; report renders the high-reach table |
| 6 | `changes`/`worktree`/`task` blast-radius payloads byte-equal to develop on this repo (sha256 pasted) |
| 7 | **Real repos, pre-registered**: node-api, node-monorepo, fullstack-ts, nest-api, python-ml — blast-radius now rates (or abstains with a stated reason); paste the high-reach list (top 5) and both rule values; overall old → new |
| 8 | `tests/test_t114_project_blast_radius.py` covers AC1–AC6 |

---

## Evaluation & Acceptance

```bash
PYTHONPATH=src:<main>/.venv/lib/python3.12/site-packages /usr/bin/python3.12 -m pytest -q tests/test_t114_project_blast_radius.py
# full suite in background; ruff check src tests
```

### Evidence
> **Moved.** `tasks/TASK_REVIEW_T114.md`.

## Demonstration
> **Moved.** `tasks/TASK_REVIEW_T114.md`. BEFORE = node-api project blast-radius "all declared rating
> metrics abstained" (pack read 1 file).

## UI / Design Acceptance Criteria
> N/A — one table row group in the existing blast-radius report block. UI Evidence rows ☐ N/A.

---

## Approach

Reuse the import resolution behind `max_fan_in_changed` / `top_level_import_cycles`; do not write a new
resolver. 1. BEFORE. 2. Fan-in over the index (AC1). 3. High-reach set (AC2). 4. Two rules (AC3–5).
5. Narrow-scope equality (AC6). 6. Real repos (AC7).

## Edge Case Checklist
- [ ] Barrel / index files (`index.ts` re-exports) — count them, but say so in the derivation
- [ ] Tiny repo (< 10 source files) → high-reach set may be 1 file; never 0/0
- [ ] Monorepo: imports across packages via workspace names count as in-repo when resolved

## Files to Change (Predicted)
| File | Change |
|------|--------|
| `dimensions/blast_radius.py` | project-scope graph metrics |
| `core/judge.py`, `core/metrics.py`, `core/metric_tables.py`, `core/report.py` | 2 rules + rendering |
| `tests/test_t114_project_blast_radius.py` | new |

## Files Must NOT Touch
| File | Reason |
|------|--------|
| narrow-scope blast-radius behaviour | AC6 |
| other dimensions' rules | out of scope |

## Completion Checklist
- [ ] Committed on `feat/T114-project-blast-radius` (commit WIP early)
- [ ] AC7 expectations written before the runs
- [ ] T100 guard green
- [ ] Supervisor notified
