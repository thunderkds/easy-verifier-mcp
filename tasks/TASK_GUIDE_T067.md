# TASK_GUIDE — T067: Evidence floor — no number below 50% measured weight; evidence-lack is a warning, never agent-rated
**Date**: 2026-10-03
**Complexity Level**: C2
**Risk Level**: Medium
**Priority**: P0
**Assigned agent**: backend-developer
**Agent guide**: `.claude/agents/backend.md`

---

## Mandatory Startup (Do Not Skip)

1. Read `PROJECT_SPEC.md`
2. Read `memory/MEMORY.md`
3. Read this file completely
4. Read `.claude/agents/backend.md`
5. Apply the C2 process from `.claude/agents/general-agent-template.md`
6. Read `memory/codebase-map.md` and `docs/ddr/0010-evidence-floor-and-priority-batches.md` (main checkout only; `docs/ddr` is gitignored), plus `docs/ddr/0006-*.md` for the gate behaviour being amended

---

## Requirement (Pillar 1 — Adapt the requirement)

User (2026-10-03), after node-monorepo scored code-quality 100 from 2 of 6 rules: "with LLM and we still do
not evaluate it. Looks not good at all … for the lack of files to evaluate, we do not hallucinate,
just warning, or raise about the bugs." Supervisor proposal accepted ("yes"): 50% measured-weight
floor; evidence-lack abstentions are not agent-rated at the gate; only solution-fit (`no_static_rule`)
stays agent-rated.

**Restated intent**:
> A dimension shows a number only when at least half of its rule weight was actually measured. When
> evidence is missing, the output says so as a warning (and the improvement plan lists what is
> missing) instead of a number — neither the rules nor the LLM invent one.

**Out of scope**:
- Reading more files on large repos (T068).
- Changing any rule weight/threshold, coverage floor, or the borderline band.
- Changing how solution-fit is agent-rated, or borderline gates.

**Requirement Refs**:
- FR-058: measured-weight floor → `insufficient_measured_weight` abstention with share + unmeasured rules.
- FR-059: evidence-lack abstention → warning + improvement-plan line; never gated, never agent-rated.
- FR-036 (amended): gate only `no_static_rule` abstentions and borderline inputs.
- FR-028b: overall disclosure still lists every abstention.

### Requirement Fidelity Gate

- [x] Restated intent confirmed (Supervisor, user "yes" 2026-10-03)
- [x] Domain terms align with glossary (rule input, abstention, gate, measured weight)
- [x] Every AC traces to the Requirement
- [x] All Requirement Refs exist in `PRD.md`

---

## Dependencies & Reachability

**Depends on**: None
**Entry point**: `MEASURED_WEIGHT_FLOOR`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to |
|---|----------------------|-----------|
| 1 | `judge.MEASURED_WEIGHT_FLOOR = Decimal("0.50")` declared data; `rate()` abstains `insufficient_measured_weight` when measured weight / declared rule weight < floor (exactly 0.50 is rated) | FR-058 |
| 2 | The abstention carries the measured share and every unmeasured rule (name + reason); `to_dict` and validation round-trip | FR-058 |
| 3 | `detect_evaluate_gates` gates abstentions only with `no_static_rule`; `insufficient_measured_weight`, `below_coverage_floor`, `coverage_not_applicable`, `all_metrics_abstained`, `dimension_failed` are not gated; borderline gating unchanged | FR-059, FR-036 |
| 4 | A `gate_evaluations` entry submitted for an evidence-lack dimension is rejected/ignored with an explicit error (never turns it agent-rated) | FR-059 |
| 5 | Score payload carries a `warnings` entry per evidence-lack abstention (dimension, reason, unmeasured rules); report shows them as a visible warning block | FR-059 |
| 6 | Improvement plan's abstained line for `insufficient_measured_weight` lists the unmeasured rules with reasons (what to add to the repo) | FR-059 |
| 7 | CLI and MCP payloads byte-equal after DDR-0005 normalization | FR-022 |
| 8 | Real repo node-monorepo: code-quality no longer 100 — abstains `insufficient_measured_weight` (20%), warning shown; MCP `score` with gates asks the agent only about solution-fit (+ any borderline) | user report |
| 9 | Second real repo (fullstack-ts or python-ml) re-run: before/after per-dimension table pasted; any dimension that newly abstains is explained | done-means-real-repo-verified |

---

## Evaluation & Acceptance

### Success Criteria

| # | Given | Expect | How |
|---|-------|--------|-----|
| 1 | Rating fixture: measured 20 of 100 weight | abstains `insufficient_measured_weight`, share 0.20, 4 unmeasured listed | automated |
| 2 | Measured exactly 50 of 100 | rated | automated (boundary) |
| 3 | Measured 49 of 100 (or 0.499 share) | abstains | automated |
| 4 | Ratings with each evidence-lack reason + one `no_static_rule` + one borderline | gates = {solution-fit: abstained, X: borderline} only | automated |
| 5 | gate_evaluations for `requirement-fidelity` (below_coverage_floor) | validation error naming it; no agent-rated result | automated |
| 6 | node-monorepo CLI + MCP | code-quality abstains with warning; overall from architecture/security/test-strategy; report warning visible | verify, pasted |

### Verification Command

```bash
cd <worktree> && PYTHONPATH=src <repo>/.venv/bin/python -m pytest tests/test_t067_evidence_floor.py -q
cd <worktree> && PYTHONPATH=src <repo>/.venv/bin/python -m pytest -q
```

### Evidence

> Filled by the reviewer in `tasks/TASK_REVIEW_T067.md`.

---

## Demonstration

> See `tasks/TASK_REVIEW_T067.md`.

---

## UI / Design Acceptance Criteria

The report gains a warning block; reuse the report's existing warning styling (`_render_warnings`).

### 1. Visual Regression

| Screen / Component | Verification method | Expected result |
|---|---|---|
| Report warning block for evidence-lack | headless Chromium screenshot + LLM vision | warning visible near the score panel, names dimension + unmeasured rules |

### 2. Design-System Compliance

| Criterion | Verification method | Expected result |
|---|---|---|
| Colors / typography | CSS audit | existing warning classes reused, no new tokens |

### 3. Layout / Responsiveness

| Viewport | Verification method | Expected result |
|---|---|---|
| 400px (iframe — headless Chrome min window is 500px) / 1280px | screenshot | no horizontal page scroll |

---

## Approach

**Pattern reference**: `src/easy_verifier/core/judge.py` `rate()` + `_ABSTENTION_REASONS` + `BORDERLINE_BAND` (declared-data style); `src/easy_verifier/core/gate.py` `detect_evaluate_gates` (the `documentation_only` exclusion is the existing precedent).

Add the floor check in `rate()` after inputs/unavailable are partitioned (declared weight = sum of the dimension's `RATING_RULES` weights). New reason code + text; abstention keeps `unavailable_metrics`. Restrict gating; make `apply_gate_evaluations` refuse evidence-lack dimensions. Surface warnings in `ScoreResult.to_dict` and the report. Update existing T028 tests whose expectation was agent-rating of an evidence-lack abstention — each changed test must cite DDR-0010 in a comment.

---

## Edge Case Checklist

- [ ] Exactly 50% → rated (inclusive)
- [ ] Decimal arithmetic for the share (no float hair at 0.5)
- [ ] Dimension with no declared rules (solution-fit) still `no_static_rule`, still gated
- [ ] documentation_only still never gated
- [ ] Overall abstains `no_dimension_rated` cleanly if the floor removes every contributor
- [ ] Replay of an old stored agent input carrying gate_evaluations for a now-ungated dimension → explicit error, not silent drop
- [ ] Improvement plan (T065) still totals correctly with fewer contributors

---

## Files to Change (Predicted)

| File | Change |
|---|---|
| `src/easy_verifier/core/judge.py` | floor constant, reason code, `rate()` check |
| `src/easy_verifier/core/gate.py` | gate only `no_static_rule` + borderline; refuse evidence-lack evaluations |
| `src/easy_verifier/core/score.py` | `warnings` in payload |
| `src/easy_verifier/core/report.py` | warning block |
| `src/easy_verifier/core/improve.py` | abstained line lists unmeasured rules |
| `tests/test_t067_evidence_floor.py` | new |
| existing gate tests | updated expectations, citing DDR-0010 |
| `docs/SCORING_FLOW.md`, `docs/SCORING_RULES.md` | describe floor + gate change |

## Files Must NOT Touch

| File | Reason |
|---|---|
| `RATING_RULES` weights/thresholds, `COVERAGE_FLOORS`, `BORDERLINE_BAND` | user-signed data |
| `src/easy_verifier/dimensions/_code_extract.py`, test-strategy caps | T068 |
| `src/easy_verifier/core/redact.py` | unrelated |

---

## Test Plan

Unit tests per AC; adjust gate tests; parity test; Stage 5 on node-monorepo (CLI + MCP with gates) and a second real repo with a before/after table.

---

## Completion Checklist

- [ ] Implementation done
- [ ] `Skill({ skill: "code-review" })`
- [ ] `Skill({ skill: "security-review" })` (Medium)
- [ ] Lint passes
- [ ] Tests written AND pass — pasted in `tasks/TASK_REVIEW_T067.md`
- [ ] `Skill({ skill: "verify" })` on node-monorepo + second repo
- [ ] Supervisor notified
