# TASK_GUIDE — T090: Report each route's request path (unweighted)
**Date**: 2026-10-12
**Complexity Level**: C2
**Risk Level**: Low
**Priority**: P2
**Assigned agent**: backend-developer
**Agent guide**: `.claude/agents/backend.md`

---

## Mandatory Startup (Do Not Skip)

Before writing any code:
1. Read `PROJECT_SPEC.md`
2. Read `memory/MEMORY.md`
3. Read this file completely
4. Read `.claude/agents/backend.md`
5. Note the **Complexity Level** above and apply the matching process from the Complexity matrix in `.claude/agents/general-agent-template.md`
6. Read `docs/ddr/0012-recognize-by-behaviour-and-content-not-names.md` (§2) and `tasks/TASK_GUIDE_T088.md`

---

## Requirement (Pillar 1 — Adapt the requirement)

User (2026-10-12): architecture *"relate to the code structure, the life cycle of request"*; and
*"database is not relate to the repos scoring, cause it belong to another service, we just check
what we have"*.

**Restated intent**:
> For each recognised route, the output shows the in-repo path its request takes: route handler →
> in-repo modules → the first boundary call (DB/ORM, from T088's data evidence). Each hop is cited by
> `file:line`. It is **reported, never scored**: no weight, no pass or fail, and no effect on any
> rating or the overall.

**Out of scope**:
- Any weight or rule (user Q2: the boundary belongs to another service)
- Runtime tracing; call-graph precision beyond imports
- Non-DB boundaries (HTTP clients, queues), which are a possible follow-up

**Requirement Refs**:
- FR-077 (added 2026-10-12)

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [x] Restated intent confirmed (user Q2, "go" 2026-10-12)
- [x] Domain terms align with `PROJECT_SPEC.md` (metric, layer, boundary)
- [x] Every Acceptance Criterion traces to the Requirement
- [x] FR-077 exists in `PRD.md`

---

## Dependencies & Reachability

**Depends on**: T088 (behaviour layers: api and data evidence, import graph)

**Entry point**: `request_paths` metric in `src/easy_verifier/core/metrics.py` (architecture dimension, unrated)

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | An unrated architecture metric `request_paths` lists, per route (method + path + `file:line`), the shortest in-repo import path to a data file, each hop cited, plus the boundary call line | request lifecycle |
| 2 | Summary counts: routes found; routes reaching a boundary directly (handler file is data); via ≥ 1 in-repo module; reaching none. Purely descriptive wording, no "violation" or "bad" | reported, not judged |
| 3 | The metric is in the payload's metric list and in the HTML report's architecture card as a folded list, capped (e.g. first 20 routes, with the cap disclosed) | readable output |
| 4 | **No rating, overall, improvement-plan item or area count changes** because of this metric. Test: the rating payload is equal with the metric on and off | not scored |
| 5 | **Real repos (paste)**: bryony and kitchd summary counts plus 3 hand-checked paths each | real-repo verified |

---

## Evaluation & Acceptance (How we know the agent worked correctly)

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | T088 Express fixture | `GET /api/x: server/r.js:3 → lib/svc.js → lib/store.js:7 (User.find)` | automated test |
| 2 | route with no data reach | listed under "reaching none" | automated test |
| 3 | ratings on/off | identical | automated test |

### Verification Command (exact, runnable)

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q
.venv/bin/python -m ruff check src tests
```

### Evidence

> Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T090.md`.

---

## UI / Design Acceptance Criteria

> N/A: the HTML report reuses existing folded-list markup. All three UI Evidence rows are ☐ N/A.

---

## Approach

**Pattern reference**: unrated metrics such as `requirements_docs_count` (computed, shown, never
weighted, T077); the report's folded lists in `core/report.py`.

BFS over T088's import graph from each api file. Never build a new graph.

---

## Edge Case Checklist

- [ ] Several routes in one file share the file's path; cite each route line
- [ ] Cycles in the import graph do not loop the BFS
- [ ] Payload size: cap, and disclose the cap (citation bloat is a known issue, see the T068 follow-up)

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/core/metrics.py` | `request_paths` unrated metric |
| `src/easy_verifier/core/report.py` | folded list in the architecture card |
| `docs/SCORING_RULES.md` | unrated-metric note |
| `tests/test_t085_request_paths.py` | new |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| `RATING_RULES` in `core/judge.py` | never scored |

---

## Test Plan

Unit fixtures SC 1–3. Real-repo pass on bryony and kitchd.

---

## Completion Checklist

- [ ] Implementation done
- [ ] Self-review: `Skill({ skill: "code-review" })` run
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T090.md`
- [ ] Real-repo run pasted (AC 5)
- [ ] Supervisor notified: task ready for Stage 4 review
