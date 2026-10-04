# TASK_GUIDE — T065: Improvement plan (engine) — unmet rules grouped P0/P1/P2, recomputed gain, static fix lines
**Date**: 2026-10-03
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
6. Read `memory/codebase-map.md`, `docs/ddr/0009-improvement-plan-ordered-by-recomputed-gain.md`, and `BRAINSTORMING_LOG_improvement-plan.md`

---

## Requirement (Pillar 1 — Adapt the requirement)

User (2026-10-02): "you are scoring repos another, so after score, we should suggest to make the repos
(that we score) better." Brainstorm answers: fix text from **both** engine and agent; **sort by
priority group and list out** every item; groups by **closeness to threshold** (P0 near-miss, P1 clear
failure, P2 abstained), points gained as tie-breaker. Defaults accepted ("yes", 2026-10-03): FR-026
amended for ordering; P2 shows a gain range; gated dimensions show rules-part gain only.

**Restated intent**:
> After `score`, the owner of the scored repo gets an improvement plan — every unmet or unmeasurable
> rule, grouped P0/P1/P2, each with what fixing it is worth (exactly recomputed) and a standard fix
> line — in both adapters' JSON and in the HTML report.

**Out of scope** (this task):
- Agent-supplied repo-specific fix text and its `write_report` validation → **T066**.
- Any change to rule weights, thresholds, `BORDERLINE_BAND`, coverage floors, or gate logic.
- Estimating effort, or any narrative/cross-dimension interpretation (FR-026 still holds).
- Auto-fixing anything in the target repo (FR-024).

**Requirement Refs**:
- FR-055: plan in `score` output (both adapters) + report; abstained dimension → reason line; "no gaps" stated.
- FR-056: P0/P1/P2 grouping, order, recomputed gain, P2 range, gated label.
- FR-057 (engine half): one static fix line per declared rule metric, labelled `engine`.
- FR-026 (amended), FR-022/DDR-0005 (parity).

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [x] Restated intent confirmed to match the user's request (Supervisor, from brainstorm answers 2026-10-02/03)
- [x] Domain terms align with `PROJECT_SPEC.md` glossary (rule input, abstention, gated rating, near-miss = `BORDERLINE_BAND`)
- [x] Every Acceptance Criterion below traces to a line in the Requirement
- [x] All Requirement Refs exist in `PRD.md` and are fully covered by the Acceptance Criteria above

---

## Dependencies & Reachability

**Depends on**: None
**Entry point**: `improvement_plan`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | `ScoreResult.to_dict()` has an `improvement_plan` key with `groups` P0, P1, P2 (always present, possibly empty) and per-dimension `abstained` lines | FR-055 |
| 2 | Each item carries dimension, area, metric_name, current value, comparison, threshold, weight, metric citation files, `dimension_gain`, `overall_gain`, `fix` `{text, source: "engine"}` | FR-055, FR-057 |
| 3 | An unmet input within ±`BORDERLINE_BAND` of its threshold is P0; otherwise P1; a threshold of 0 is never P0 | FR-056 |
| 4 | Each abstained rule metric of a rated dimension is P2 with `overall_gain` as a range `[low, high]`; a negative `low` is kept, not clipped | FR-056 |
| 5 | Gains are recomputed with the real round-once arithmetic: a fixture where weight-based gain and recomputed gain differ (rounding tie) asserts the recomputed value | FR-056 |
| 6 | Order inside a group: overall gain desc (P2 by high end), then dimension, then metric name — deterministic | FR-056 |
| 7 | A gated/blended dimension's items carry `gain_basis: "rules"`; non-gated carry `"final"` | FR-056 |
| 8 | A dimension whose rating abstained yields no items and one `abstained` entry with its reason code | FR-055 |
| 9 | All rules met and nothing abstained → all groups empty and the report says "No gaps" explicitly | FR-055 |
| 10 | Every metric in `judge.RATING_RULES` has a `FIX_HINTS` entry; a test enumerates them (adding a rule without a hint fails) | FR-057 |
| 11 | CLI and MCP `score` payloads stay byte-equal after DDR-0005 normalization with the new key | FR-022, DDR-0005 |
| 12 | HTML report renders an "Improvement plan" section: P0 → P1 → P2, every item listed, fix labelled `engine` | FR-055 |
| 13 | Real-repo run: `score` on bryony shows a non-empty plan whose top P0/P1 gain, applied by hand to the rating arithmetic, matches | done-means-real-repo-verified |

---

## Evaluation & Acceptance

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | Synthetic ratings: one dimension with rules (w 40 met, w 35 unmet value 0.31 vs ≥0.30-style near band, w 25 unmet far) | near item in P0, far item in P1, gains equal hand-computed recompute | automated test (Supervisor-signed oracle values in test) |
| 2 | Rounding-tie fixture | recomputed gain ≠ naive weight share, test asserts recomputed | automated test |
| 3 | Rated dimension with one abstained metric | P2 item with `[low, high]`, low may be < 0 | automated test |
| 4 | Dimension `RatingAbstention(below_coverage_floor)` | no items; `abstained` entry with reason code | automated test |
| 5 | `GatedRating` dimension | items with `gain_basis: "rules"` | automated test |
| 6 | All met | empty groups; report contains "No gaps" | automated test + rendered HTML |
| 7 | New rule added to `RATING_RULES` without hint | hint-coverage test fails | automated test |
| 8 | Same repo via CLI and MCP | normalized payloads byte-equal | existing parity test extended |
| 9 | bryony real repo | plan printed; one gain hand-verified | `verify` skill, pasted output |

### Verification Command (exact, runnable)

```bash
.venv/bin/pytest tests/test_t065_improvement_plan.py -q
.venv/bin/pytest -q && .venv/bin/ruff check src tests
.venv/bin/easy-verifier score --repo /home/hungnguyenhuu/workspace/project/bryony/bryony --scope project </dev/null \
  | python3 -c "import json,sys; p=json.load(sys.stdin)['improvement_plan']; print(json.dumps(p, indent=1)[:4000])"
```

### Evidence

> Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T065.md`.

---

## Demonstration

> See `tasks/TASK_REVIEW_T065.md`.

---

## UI / Design Acceptance Criteria

The report section is generated HTML in an existing self-contained report; it reuses the report's
existing table/card styles, no new design tokens.

### 1. Visual Regression

| Screen / Component | Verification method | Expected result |
|-------------------|---------------------|-----------------|
| Report "Improvement plan" section | Headless Chromium screenshot (`--host-resolver-rules="MAP * ~NOTFOUND"`) + LLM vision | P0/P1/P2 headings in order, every item row visible, no layout break of existing panels |

### 2. Design-System Compliance

| Criterion | Verification method | Expected result |
|-----------|---------------------|-----------------|
| Colors match design tokens | CSS audit of new rules in `report.py` stylesheet | only existing palette values reused |
| Typography matches spec | computed style | same font/size as existing findings/score tables |
| Spacing / layout matches spec | visual | consistent with score panel |

### 3. Layout / Responsiveness

| Viewport | Verification method | Expected result |
|----------|---------------------|-----------------|
| Mobile (320–480px) | headless Chromium `--window-size=400,900` | table scrolls inside its box; no page horizontal scroll |
| Tablet (768px) | headless Chromium | readable table |
| Desktop (1024px+) | headless Chromium | full table |

---

## Approach

**Pattern reference**: `src/easy_verifier/core/judge.py` — `_RATING_METHOD` / `rate_overall` arithmetic (round once, ties to even, abstentions excluded) and frozen-dataclass + `to_dict` style; `src/easy_verifier/core/synthesis.py` — aggregation-only module shape.

1. New `src/easy_verifier/core/improve.py`: frozen dataclasses `PlanItem`, `ImprovementPlan`; pure `improvement_plan(ratings, overall) -> ImprovementPlan`.
   - For each unmet `RatingInput`: recompute that dimension's value with the input's `earned_weight = weight`, and the overall with that dimension replaced. **Reuse the judge's arithmetic** (extract a small shared helper only if needed; never duplicate the rounding rule in a second form).
   - For each `unavailable_metrics` entry of a rated dimension whose metric has a declared rule: recompute with that rule added as failed (low) and as passed (high).
   - Classify using `judge.BORDERLINE_BAND` (read, do not copy the value) with the comparison direction respected.
   - `FIX_HINTS: dict[str, str]` — one line per rule metric, describing the real remedy (never a metric-gaming move like "delete skipped tests").
2. `core/score.py`: compute the plan in the shared path; add `improvement_plan` to `ScoreResult.to_dict()` (both adapters inherit it).
3. `core/report.py`: `_render_improvement_plan(ctx, score)` after the score panel; engine text still escaped.
4. `docs/SCORING_FLOW.md`: one short section describing the plan.

---

## Edge Case Checklist

- [ ] Rounding tie → recomputed gain, not weight share
- [ ] Threshold 0 → never P0
- [ ] Comparison direction (≤ vs ≥) for near-miss and display
- [ ] Fully abstained dimension → reason line, not silence
- [ ] Gated dimension → `gain_basis: "rules"`
- [ ] P2 low end negative → kept
- [ ] Hint coverage enumerates `RATING_RULES`
- [ ] Item with no metric citation files → states the metric is repo-wide, never a blank cell (miss-list class)
- [ ] All met → explicit "No gaps"
- [ ] Parity byte-equal after DDR-0005 normalization
- [ ] Replay (`--agent-input`) of a stored report reproduces the same plan

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/core/improve.py` | new: plan computation + `FIX_HINTS` |
| `src/easy_verifier/core/score.py` | attach plan; serialize in `to_dict` |
| `src/easy_verifier/core/report.py` | render "Improvement plan" section |
| `src/easy_verifier/core/judge.py` | only if a tiny shared arithmetic helper must be extracted — no rule/threshold/weight change |
| `tests/test_t065_improvement_plan.py` | new |
| `tests/snapshots/*` | regenerate only snapshots that change by the new key, with diff reviewed |
| `docs/SCORING_FLOW.md` | describe the plan |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| `RATING_RULES`, `COVERAGE_FLOORS`, `BORDERLINE_BAND` values | user-signed data |
| `src/easy_verifier/core/gate.py` | gate logic unchanged |
| `src/easy_verifier/core/redact.py` | no new egress in this slice |
| `src/easy_verifier/core/findings.py` | agent overrides are T066 |

---

## Test Plan

Unit tests on synthetic `Rating`/`RatingAbstention`/`GatedRating` objects for every AC; extend the
existing CLI/MCP parity test; render the report and screenshot it; Stage 5 real-repo run on bryony
(plus kitchd as a second repo).

---

## Completion Checklist

- [ ] Implementation done
- [ ] Self-review: `Skill({ skill: "code-review" })` run
- [ ] Security review: `Skill({ skill: "security-review" })` run (Medium risk)
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T065.md` (Hard-Stop Gate 5)
- [ ] `Skill({ skill: "verify" })` run on bryony — real repo
- [ ] `memory/MEMORY.md` updated (if new patterns learned)
- [ ] Supervisor notified: task ready for Stage 4 review
