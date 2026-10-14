# TASK_GUIDE — T082: The score names the evaluation areas it does not measure
**Date**: 2026-10-06
**Complexity Level**: C2
**Risk Level**: Medium
**Priority**: P1
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
6. Read `memory/codebase-map.md`
7. Read `docs/AREA_COVERAGE.md` (the 32 areas → rules map) and `docs/EVALUATION_GUIDE.md`

---

## Requirement (Pillar 1 — Adapt the requirement)

User (2026-10-06): "I saw some rules to evaluate comes from the business domain is not evaluate as
implement yet, let check and investigate" → after the Supervisor's findings: "start the list of
tasks with automatic".

Supervisor finding (develop `6bf651e`): 21 of the 32 areas (`judge.AREAS`) have no rating rule and
no documentation rule, including the business-domain areas #3 financial integrity, #6
transactions/idempotency, #9 PHI, #28 BAA/residency and #32 business continuity. The score payload
and the HTML report never say this. `OverallRating.disclosure` names abstained *dimensions*, and
the report lists *unmeasured metrics* of rated dimensions, but nothing names the *areas* a score
does not speak for. Example: nest-api scored 65 from code-quality + security, covering
areas 8, 10, 17, 18, 20 and 31 — the reader cannot learn that from the output. This gap is visible
only in `docs/AREA_COVERAGE.md`.

**Restated intent**:
> Every score (CLI JSON, MCP payload, HTML report) states how many of the 32 evaluation areas this
> run actually measured, and lists by name the areas no declared rule covers. A reader can see
> what a number does not speak for without opening the docs.

**Out of scope**:
- New rules for any area (T041–T049)
- Changing any rating value, weight, floor or abstention
- Per-area sub-scores

**Requirement Refs**:
- FR-051: area rule groups (areas labelled on every rule)
- FR-038: overall disclosure counts each kind
- FR-073 (new, added by this task to `PRD.md`): the score discloses the evaluation areas it measured and the areas no declared rule covers

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [x] Restated intent confirmed to match the user's request (Supervisor, 2026-10-06 — user approved "start the list of tasks with automatic")
- [x] Domain terms align with `PROJECT_SPEC.md` glossary (area, rule, dimension, abstention, disclosure)
- [x] Every Acceptance Criterion below traces to a line in the Requirement
- [x] FR-051 / FR-038 exist in `PRD.md`; FR-073 is added by this task

---

## Dependencies & Reachability

**Depends on**: None (T039 area labels and T072 area doc are Done)

**Entry point**: `judge.OverallRating` (payload) and `report._render_score_panel` (HTML)

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | The score payload carries `areas_measured` (areas with at least one *measured* rule input in a contributing dimension, or a documentation result) and `areas_without_rule` (areas of `judge.AREAS` named by no rule in `RATING_RULES` and no `DOCUMENTATION_RULES` entry), both in `AREAS` order | names the gap |
| 2 | `areas_without_rule` is derived from the live rule tables, never a hand list: adding a rule for an area removes it from the list (test adds a rule via monkeypatch or checks against the tables) | stays true as T041–T049 land |
| 3 | The overall disclosure sentence states "measured N of 32 evaluation areas" | visible in every surface |
| 4 | The HTML report score panel shows the count and a folded list "Areas no rule covers yet (K)" with each area name; escaped like all other report text | visible in report |
| 5 | When the overall is withheld (`OverallAbstention`), the area lists still appear in the payload and the report | nothing hidden on abstention |
| 6 | No rating value changes: existing rating/replay tests pass unchanged except tests that pin the exact disclosure text or payload key set, which are updated | out of scope guard |
| 7 | `docs/EVALUATION_GUIDE.md` and `docs/AREA_COVERAGE.md` mention the new fields in one line each; `PRD.md` gains FR-073 | docs truth |
| 8 | **Real repo**: `score` on nest-api or node-monorepo shows the measured count and the uncovered list in JSON and in the written report (paste both) | done means real-repo verified |

---

## Evaluation & Acceptance (How we know the agent worked correctly)

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | today's rule tables | `areas_without_rule` has exactly the 21 "Not yet" rows of `AREA_COVERAGE.md` | automated test against the doc's table |
| 2 | fixture repo rated by code-quality only | `areas_measured` lists only code-quality areas that were measured | automated test |
| 3 | overall withheld | lists still present | automated test |
| 4 | real repo | count + list in JSON and HTML | pasted output |

### Verification Command (exact, runnable)

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q
.venv/bin/python -m ruff check src tests
```

### Evidence

> Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T082.md`.

---

## UI / Design Acceptance Criteria

> N/A — the HTML report is a generated static document, not an interactive UI; it reuses existing
> report markup/classes. All three UI Evidence rows are ☐ N/A.

---

## Approach

**Pattern reference**: `OverallRating.disclosure` / `to_dict` in `core/judge.py`; `_render_unmeasured`
in `core/report.py` for a folded list.

Compute both lists where the overall is built (the rule tables and per-dimension rating inputs are
already in hand there). Keep the derivation a small pure function over `AREAS`, `RATING_RULES`,
`DOCUMENTATION_RULES` so T041–T049 update it for free. If adding fields to `OverallRating` breaks
byte-equal replay, add them in a backward-compatible way and say how in the review notes.

---

## Edge Case Checklist

- [ ] A rule whose metric abstained does not count its area as measured
- [ ] An abstained dimension's areas are not measured
- [ ] Documentation-only areas count as measured when the documentation result exists
- [ ] Changes scope: only blast-radius-measured areas count

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/core/judge.py` | area derivation + payload fields + disclosure |
| `src/easy_verifier/core/report.py` | count + folded list in score panel |
| `PRD.md` | FR-073 |
| `docs/EVALUATION_GUIDE.md`, `docs/AREA_COVERAGE.md` | one line each |
| `tests/test_t082_uncovered_areas.py` | new |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| `src/easy_verifier/dimensions/*` | no rule changes |

---

## Completion Checklist

- [ ] Implementation done
- [ ] Self-review: `Skill({ skill: "code-review" })` run
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T082.md`
- [ ] Real-repo run pasted (AC 8)
- [ ] Supervisor notified: task ready for Stage 4 review
