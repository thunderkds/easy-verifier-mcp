# TASK_GUIDE — T020: `core/judge.py` — declared rules, coverage floors, and abstention
**Date**: 2026-08-26
**Complexity Level**: C2
**Risk Level**: Medium
**Priority**: P0
**Assigned agent**: Backend-Implementer
**Agent guide**: `.claude/agents/backend.md`

---

## Mandatory Startup (Do Not Skip)

1. Read `PROJECT_SPEC.md` — Critical Constraints 1, 1a, 1b and the Glossary entries **Rating**, **Metric**, **Coverage score**
2. Read `memory/MEMORY.md`
3. Read this file completely
4. Read `.claude/agents/backend.md`
5. **Read `docs/ddr/0003-abstain-from-rating-below-coverage-floor.md` in full.** This task *is* that DDR. Its Context section explains why the obvious implementation is wrong
6. C2: read `memory/codebase-map.md`

---

## Requirement (Pillar 1 — Adapt the requirement)

The scoring half of the user's 2026-08-26 request: point the verifier at code, get a number that
identifies quality.

**Restated intent**:
> `core/judge.py` turns a `MetricSet` into a **rating** (0–100) per dimension using rules declared as
> static, inspectable data. Below a declared per-dimension **coverage floor** it emits no rating at
> all — a structured abstention naming the floor, the achieved coverage, and the sources not reached.
> The **overall** rating averages only the dimensions that rated and discloses, in the same field,
> who abstained and why.

**Out of scope**:
- Anything derived from the caller's findings — that is the *assessment*, T021.
- Any LLM call, under any framing including "just for scoring" (Constraint 1a).
- Adapter or report wiring — T022.

**Requirement Refs**:
- FR-028: per-dimension rating from rules declared as static, inspectable data
- FR-028a: coverage floor; abstention as a distinct state, never `0`/`None`/a low rating
- FR-028b: overall averages only raters and discloses abstainers with reasons
- FR-013 (as amended): a rating must cite the metric values it was computed from
- NFR-001, Critical Constraints 1a/1b

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [ ] Restated intent confirmed to match the user's request (by Supervisor / user)
- [ ] Domain terms align with the glossary — **rating**, never "score"; `coverage_score` keeps its existing meaning and is *input*, not output
- [ ] Every Acceptance Criterion below traces to a line in the Requirement
- [ ] All Requirement Refs exist in `PRD.md` and are fully covered by the Acceptance Criteria above

> **Initial floor values are a judgment call, not a fact.** Propose them to the Supervisor with your
> reasoning **before** implementing. Set too high the tool abstains constantly and is useless; set
> too low the guarantee is theatre (DDR-0003, Negative consequences).

---

## Dependencies & Reachability

**Depends on**: T019 — `compute_metrics()` and the `Metric` / abstention types.

**Entry point**: `rate`
> Surfaced through the `score` operation in T022.

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | `rate(metrics, coverage)` returns a `Rating` (0–100) **or** a `RatingAbstention`, never both and never a number standing in for absence | FR-028, FR-028a |
| 2 | Scoring rules are **declared static data** — a table of metric name → weight/threshold — readable without reading the scoring code. A threshold change is a value edit, not a code edit | FR-028 |
| 3 | Every `Rating` carries the metric values it was computed from, and is **recomputable by hand** from them | FR-013 (amended), Constraint 1a |
| 4 | Each dimension declares a **coverage floor** as static data. Below it, `rate` returns an abstention naming the floor, the achieved coverage, and the named sources not reached | FR-028a |
| 5 | A `RatingAbstention` is a distinct type. A consumer cannot extract a numeric value from it without explicitly handling it — asserted at the **consumer boundary**, not only on the dataclass | FR-028a, Constraint 1b |
| 6 | A dimension whose metrics all abstained (truncated pack) cannot produce a rating | FR-027a, FR-028a |
| 7 | `rate_overall(...)` averages **only** the dimensions that rated, and carries in the same value: how many of seven contributed, which abstained, and each abstention's reason | FR-028b |
| 8 | **A test proves that an abstaining dimension can RAISE the overall**, and that the disclosure states this — the trap DDR-0003 flags as load-bearing | FR-028b, DDR-0003 |
| 9 | No module import, attribute access, environment variable or config path in this module can reach a model, an API client, or the network. Asserted structurally | NFR-001, Constraint 1a |
| 10 | Ratings are deterministic and adapter-independent — same metrics in, byte-identical rating out | FR-022 |
| 11 | Zero dimensions rating (all seven abstained) produces an **overall abstention**, not `0` and not a crash | FR-028a/b |

---

## Evaluation & Acceptance

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | Full metrics, coverage 0.88, floor 0.60 | A numeric rating carrying its inputs; recomputable by hand in the test | automated test |
| 2 | Coverage 0.33, floor 0.60 | Abstention naming floor **0.60**, achieved **0.33**, and the unreached sources by name. No number anywhere in the value | automated test |
| 3 | Six dimensions rate ~70, the seventh would have rated 20 but abstains | Overall **rises** vs. the all-seven case, **and** discloses "5 of 7" style provenance plus the abstainer's reason | automated test (AC #8) |
| 4 | All seven abstain | Overall abstention — not `0`, not `None`, no exception | automated test |
| 5 | Floor hardwired to 0.0, then to 1.0, on the same input | Results differ (rating vs. abstention). A test passing under both is pinning nothing | automated test (sabotage) |

### Verification Command (exact, runnable)

```bash
cd <worktree> && PATH=.venv/bin:$PATH python -m pytest tests/test_judge.py -q
```

---

## Approach

**Pattern reference**: `src/easy_verifier/core/synthesis.py:_aggregate_coverage` — it is the closest
prior art for "aggregate several per-dimension results and disclose what bounded the aggregate", and
its T012 Stage 4 P1 fix (the `method` value discloses the exclusion) is precisely the pattern AC #7
generalizes. Read that fix before writing `rate_overall`.

Declare floors and weights beside `sources_sought` in the dimension descriptors **as data**, or in a
single declared table in this module — either is acceptable, a hand-maintained second list is not
(the drift failure of T003/T008/T010).

---

## Edge Case Checklist

- [ ] `coverage_score is None` (sought nothing) — is that below the floor, or not applicable? Decide explicitly and document; do **not** let `None` compare as zero
- [ ] A dimension that raised entirely (`slot.pack is None`) — must abstain with a *different* reason than a floor miss
- [ ] Floor exactly equal to achieved coverage — boundary must be declared inclusive or exclusive in the data, and tested at the boundary
- [ ] A metric that abstains vs. a metric legitimately valued `0` — must not collapse (this is the project's seventh-instance defect)
- [ ] Rounding: a rating rendered as `62` must not be `61.5` in one adapter and `62.4` in the other (FR-022)
- [ ] An abstention reason must never be assembled by substring-matching prose — T013's AC #14 residue (c) is exactly this failing quietly

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/core/judge.py` | New. `Rating`, `RatingAbstention`, `OverallRating`, `rate()`, `rate_overall()`, declared rule + floor tables |
| `src/easy_verifier/dimensions/*.py` | **Data only** — add a declared `coverage_floor` to each descriptor. No logic |
| `tests/test_judge.py` | New |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| `src/easy_verifier/core/metrics.py` | T019's contract is fixed; consume it, don't reshape it |
| `src/easy_verifier/core/pipeline.py` | The evidence choke point is unchanged by rating |
| `src/easy_verifier/core/report.py` | Rendering is T022 |

---

## Test Plan

Unit tests over hand-built `MetricSet`s. **Mandatory technique, from this project's own history**:
for every threshold and floor, hardwire the predicate to both extremes and re-run. A test that
passes under both is pinning nothing — five prior tasks shipped exactly that defect. AC #8's test is
the one most likely to be written to pass trivially; the Supervisor signs off on that test's shape
before it is written (the implementing agent must not be the sole author of its own oracle).

---

## Completion Checklist

- [ ] Floor values proposed to Supervisor **before** implementation
- [ ] Implementation done
- [ ] Self-review: `Skill({ skill: "code-review" })` run
- [ ] Security review: **required (Medium risk)** — the built-in skill cannot run in this repo (remote is `github`, not `origin`); review the diff surface directly and record the substitution, per the T008/T013 precedent
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T020.md`'s Evidence table
- [ ] `Skill({ skill: "verify" })` run
- [ ] `memory/MEMORY.md` updated
- [ ] Supervisor notified: task ready for Stage 4 review
