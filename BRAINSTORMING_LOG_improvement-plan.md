# BRAINSTORMING_LOG.md — Improvement Plan
**Generated**: 2026-10-02
**Task / Context**: New feature (pre-Stage 2): after `score`, tell the owner of the **scored target repo** what to change to raise its rating.
**Skill**: `Skill({ skill: "brainstorming" })` — tier **Standard** (2–3 viable directions, touches score/report output, no architecture change)

---

## The Problem Space

The engine scores a target repo but stops at the number. FR-023 already lets a *finding* carry a
`suggestion` (`core/findings.py:78`, rendered at `core/report.py:909`), but nothing links an **unmet
rating rule** to "what to change and what it is worth". The user wants a post-score improvement plan.

Verified facts that shape the design:
- A dimension rating is `100 * sum(earned_weight) / sum(weight)` over binary threshold rules
  (`core/judge.py`, `_RATING_METHOD`); unmet = 0. ~27 declared `RatingRule`s in `RATING_RULES` (`judge.py:239`).
- Overall = mean of contributing dimension ratings, abstentions excluded (`_OVERALL_RATING_METHOD`, `rate_overall` `judge.py:1029`).
- Rounding happens once (ties to even) → a gain must be **recomputed**, never derived from `weight` alone.
- `BORDERLINE_BAND = 0.10` (`judge.py:491`) already defines "near the threshold" for the evaluate gate (FR-036).
- Gated dimensions may carry a blended final (FR-038: `final = R·(1−w) + A·w`); the agent part is not reproducible by the engine.
- FR-026 / `core/synthesis.py` docstring: engine does "aggregation and presentation only … never a cross-dimension narrative, correlation, **ranking**".
- FR-024 / NFR-007: suggestions are advisory text; the engine never patches the target repo.

Non-negotiable constraints: no LLM inference in the engine; adapter parity (DDR-0005); miss-list
honesty (a gap's reason must be the real one); agent prose redacted+escaped at the report boundary
(`_Ctx.agent_text()`).

---

## Decisions Locked with the User (this session)

| # | Question | Answer |
|---|---|---|
| Q1 | Who writes the "how to fix" text? | **Both** — a static engine fix line per rule (default), overridable by a repo-specific agent suggestion; report labels which. |
| Q2 | How is the plan ordered? | **By priority group, then list every item in the group.** |
| Q3 | What puts a gap in a higher group? | **Closeness to threshold**, points gained as tie-breaker inside a group: P0 = near-miss (unmet, within ±`BORDERLINE_BAND`), P1 = clear failure, P2 = abstained metric (not measurable yet). |

---

## Questions for the User (still open — resolve at Stage 2 grilling)

1. FR-026 bans engine "ranking". Ordering across dimensions by group + computed points is arithmetic, not interpretation — **amend FR-026 with one line** ("ordering by a declared, recomputed gain is presentation") via a DDR? (Supervisor default: yes, DDR-0009.)
2. P2 (abstained) gains are **two-sided**: measuring the metric can raise *or lower* the score. Show a range `[if fail, if pass]`? (Supervisor default: yes.)
3. Blended (gated) dimensions: compute the gain on the **rules part** only and say so? (Supervisor default: yes.)

---

## Alternative Paths

| Option | Name | Summary | Invasiveness | Code Volume | Regression Risk | Recommended? |
|---|---|---|---|---|---|---|
| A | Report-only | Compute the plan inside `report.py` at render time from `Rating.inputs` | Low | ~250 lines | Low | |
| B | Core `improve` module | New `core/improve.py` computes `ImprovementPlan` from ratings; `score` result carries it (both adapters); report renders it; `write_report` accepts agent overrides | Medium | ~500 lines + tests | Medium | ✅ Yes |
| C | Agent-only | Pack the failed rule inputs into `needs_input`; the agent writes the whole plan | Low | ~120 lines | Low | |

### Option A — Report-only
**Approach**: a render-time helper walks each `Rating.inputs`, picks unmet rules, recomputes the gain, prints grouped tables with the static fix line.
**Pros**: smallest surface; no model/schema change; no parity work.
**Cons**: the plan exists only in HTML — CLI/MCP JSON callers (and the agent that should write overrides) never see it; the agent cannot target a gap it cannot name.
**Why it might fail**: Q1 "both" needs the agent to see the gaps *before* it writes — report-only makes the agent half impossible.

### Option B — Core `improve` module (recommended)
**Approach**:
1. `core/improve.py` — pure function `improvement_plan(ratings, overall) -> ImprovementPlan`. For each unmet `RatingInput`: flip it to passed, **re-run** the dimension and overall arithmetic, record `dimension_gain` and `overall_gain`. For each `unavailable_metrics` entry: recompute both "pass" and "fail" → gain range. Classify P0/P1/P2 by `BORDERLINE_BAND`; sort by `overall_gain` desc, then metric name (stable).
2. `FIX_HINTS: dict[str, str]` — one static line per declared rule metric, beside the plan code; a test asserts **every** `RATING_RULES` metric has a hint (no silent gap when a rule is added).
3. `ScoreResult.improvement_plan` serialized in both adapters (parity: pure function of ratings → byte-equal).
4. `write_report` accepts optional `improvements: [{metric_name, dimension, suggestion}]`; validated (must name an existing gap; string; length cap); rendered through `ctx.agent_text()`; labelled *agent* vs *engine*.
5. Report section "Improvement plan" — P0/P1/P2 groups, each row: dimension · area · metric · now → threshold · gain (dim / overall) · cited files · fix (engine|agent).
**Pros**: one computation, every surface; agent sees exact gap IDs; fully testable arithmetic; fits "engine computes, agent interprets".
**Cons**: touches `score.py`, both adapters, `report.py`, `findings`-style validation; a new spec line (FR-026 amendment).
**Why it might fail**:
- Gain derived from weight instead of recompute → wrong by rounding (ties to even). Mitigation: recompute only; test a tie case.
- Gated dimension: presenting a rules-only gain as if final moves by that much. Mitigation: label "rules part; final also depends on gate".
- P2 misread as a promised gain. Mitigation: range display, never a single positive number.
- Goodhart: "delete skipped tests" raises `skipped_test_share`. Mitigation: static hints written as the *real* fix ("re-enable or remove obsolete skipped tests with a reason"), never "delete".
- Miss-list class: a hint whose cited files are empty must say *why* (metric computed repo-wide), not show blank.

### Option C — Agent-only
**Approach**: emit unmet rule inputs to the agent; it returns the whole plan as findings with suggestions.
**Pros**: least code; repo-specific text.
**Cons**: CLI gets nothing; gains are agent arithmetic (not reproducible, breaks "engine computes"); no static default (contradicts Q1).
**Why it might fail**: a hallucinated "+8 points" is exactly the low-confidence risk the product exists to surface.

---

## 50% Rule Check

Ship B in two slices; slice 1 alone delivers the user value:
- **Slice 1 (~250 lines)**: `improve.py` + `FIX_HINTS` + `ScoreResult.improvement_plan` + report section (engine hints only). Covers Q2/Q3 fully and Q1's engine half.
- **Slice 2 (~150 lines)**: `write_report` agent overrides + labels (Q1's agent half).
Cut further if needed: P2 range → show "unknown (not measured)" instead of computing two scenarios.

---

## Recommended Path

**Option B — Core `improve` module**, delivered as two tasks (slice 1 → slice 2), plus DDR-0009 amending FR-026.

## Surgical Scope

**Should touch**: new `src/easy_verifier/core/improve.py`; `core/score.py` (attach plan); `core/report.py` (section + agent override render); `core/findings.py` or `write_report` validation (slice 2); adapters only if `ScoreResult` serialization is not already generic; `PRD.md` (FR-026 amendment + new FR); `docs/ddr/0009-*.md`; `docs/SCORING_FLOW.md`.
**Must not touch**: `judge.py` arithmetic, `RATING_RULES` weights/thresholds, `BORDERLINE_BAND` (read only); `synthesis.py` behaviour; redaction layer; gate logic in `gate.py`.

## Edge Case Checklist (for TASK_GUIDEs)

- [ ] Rounding tie: flipping one rule produces a .5 → gain from recompute, not weight.
- [ ] Threshold 0 rule: near-miss band is zero-width → never P0 (matches FR-036).
- [ ] Comparison direction (≤ vs ≥) respected when computing "now → threshold" and near-miss.
- [ ] Dimension fully abstained (coverage floor, failed): no rows; one line stating why (reason code), never silently omitted.
- [ ] Gated/blended dimension: gain labelled "rules part".
- [ ] P2 range may be negative on the low end — rendered, never clipped to 0.
- [ ] Every `RATING_RULES` metric has a `FIX_HINTS` entry (test enumerates).
- [ ] Agent override naming a non-existent gap → validation error, not silently dropped.
- [ ] Agent override text with a secret → redacted (`agent_text`).
- [ ] CLI vs MCP JSON byte-equal after DDR-0005 normalization.
- [ ] All rules passed → plan says "no gaps" explicitly.

## Next Actions (Stage 2)

1. Resolve the 3 open questions (grill-with-docs, `mode=requirement`).
2. Write DDR-0009 + PRD amendment (FR-026 ordering; new FR for improvement plan).
3. Two Kanban rows + TASK_GUIDEs: slice 1 (C2, Risk Low–Med, P1), slice 2 (C2, Risk Med — new agent-text egress, so `security-review`, P1).
4. Done = verified on a real repo (bryony/kitchd/ai-training), not fixtures only.
