# TASK_GUIDE — T021: `core/assessment.py` — findings rollup and rating/assessment divergence
**Date**: 2026-08-26
**Complexity Level**: C2
**Risk Level**: Medium
**Priority**: P1
**Assigned agent**: Backend-Implementer
**Agent guide**: `.claude/agents/backend.md`

---

## Mandatory Startup (Do Not Skip)

1. Read `PROJECT_SPEC.md` — Glossary entries **Assessment**, **Divergence**, **Finding**, **Rating**
2. Read `memory/MEMORY.md`
3. Read this file completely
4. Read `.claude/agents/backend.md`
5. Read `docs/ddr/0003-...md` Decision item 6 — divergence is reported, never reconciled
6. C2: read `memory/codebase-map.md`

---

## Requirement (Pillar 1 — Adapt the requirement)

**Restated intent**:
> When the calling agent submits findings, `core/assessment.py` computes an **assessment** (0–100)
> per dimension as a severity- and confidence-weighted rollup of those findings, and computes the
> **divergence** between it and T020's rating where both exist. The engine does the arithmetic; the
> judgment stays the agent's. Disagreement is surfaced as signal, never blended away.

**Out of scope**:
- Interpreting what a divergence *means* — that is the calling agent's job (FR-026).
- Reconciling, blending, or averaging rating and assessment into one figure. Explicitly prohibited.
- Making findings a precondition for any number (FR-030 — T020 stands alone without this task).

**Requirement Refs**:
- FR-029: severity/confidence-weighted rollup of submitted findings
- FR-029a: rating and assessment rendered side by side with divergence; never blended
- FR-026: interpretation belongs to the caller
- FR-015: findings already carry evidence + confidence (`core/findings.py`)

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [ ] Restated intent confirmed to match the user's request (by Supervisor / user)
- [ ] Domain terms align with the glossary — **assessment**, never "agent score"
- [ ] Every Acceptance Criterion below traces to a line in the Requirement
- [ ] All Requirement Refs exist in `PRD.md` and are fully covered by the Acceptance Criteria above

> **Open design question — decide with the Supervisor BEFORE implementing.** `Finding` currently has
> no `severity` field (`core/findings.py:57` — dimension, title, detail, evidence_ref, confidence,
> suggestion). A severity-weighted rollup needs one. Adding it changes the `write_report` input
> contract that T013 shipped. Options: (a) add `severity` as a required field — breaks any existing
> caller; (b) add it optional with a declared default, and state the default in the assessment's own
> provenance so a reader knows the weighting was assumed rather than supplied. **(b) is the
> Supervisor's recommendation** — it keeps FR-015's two mandatory fields exactly two, and it makes an
> assumed weight visible instead of silent. Do not decide this alone.

---

## Dependencies & Reachability

**Depends on**: T013 — `Finding` and `validate_findings()`; T020 — `Rating` / `RatingAbstention`.

**Entry point**: `assess`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | `assess(findings_by_dimension)` returns a per-dimension `Assessment` (0–100) weighted by severity and confidence | FR-029 |
| 2 | The weighting table is **declared static data**, and every `Assessment` carries the findings it was computed from, so the number is recomputable by hand | FR-029, Constraint 1a |
| 3 | A dimension with **no** submitted findings produces **no** assessment — a distinct absence, never `0` and never "perfect" | FR-028a precedent, Constraint 1b |
| 4 | Where a rating and an assessment both exist, `divergence` is computed and carried **with both inputs**; where either is absent, divergence is absent with a reason | FR-029a |
| 5 | Nothing in this module blends, averages, or reconciles a rating with an assessment. Asserted structurally — no code path returns a single merged quality number | FR-029a |
| 6 | Where severity is absent and a default was applied, the `Assessment` says so in its own provenance | Open design question (b) |
| 7 | An assessment over findings citing an **abstaining** dimension is still computed — the agent may legitimately have judged what the rules could not measure — and the pairing renders as "assessment without rating", with the abstention reason intact | FR-028a, FR-029a |
| 8 | Deterministic: same findings in, byte-identical assessment out, across processes and adapters | FR-022 |

---

## Evaluation & Acceptance

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | 3 findings on `security` (1 high/high-confidence, 2 low) | An assessment recomputable by hand in the test from the declared weights | automated test |
| 2 | A dimension with zero findings | No assessment; a distinct absence with a reason. Not `0`, not `100` | automated test |
| 3 | `security` rating 62, assessment 41 | Divergence 21 reported with both inputs; **no** merged figure exists anywhere in the returned value | automated test |
| 4 | Findings on a dimension that abstained from rating | Assessment computed; pairing states "assessment without rating" + the abstention reason | automated test |
| 5 | Findings with no `severity` supplied | Assessment computed with the declared default **and** provenance saying the default was applied | automated test |

### Verification Command (exact, runnable)

```bash
cd <worktree> && PATH=.venv/bin:$PATH python -m pytest tests/test_assessment.py -q
```

---

## Approach

**Pattern reference**: `src/easy_verifier/core/findings.py` — same layer, same discipline about what
it refuses to do; imitate its docstrings that state prohibitions explicitly (`suggestion` is
"advisory text only — never written, patched, or executed by anything in this engine, including this
module"). AC #5 deserves that same kind of docstring.

---

## Edge Case Checklist

- [ ] A finding whose `dimension` names a dimension that was never run
- [ ] All findings at the same severity — the weighting must not degenerate to a constant
- [ ] `MAX_FINDINGS` submissions on one dimension — no unbounded arithmetic or precision drift
- [ ] Divergence sign: state in the data which direction means "agent is harsher", never leave it to the reader's inference
- [ ] Confidence is a **closed domain** (see `report.py`) — an unexpected value must be refused at validation, not silently weighted zero
- [ ] Rating absent **and** assessment absent — the pairing must still be a valid, renderable value

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/core/assessment.py` | New. `Assessment`, `Divergence`, `assess()`, declared weight table |
| `src/easy_verifier/core/findings.py` | Add optional `severity` to `Finding` + validation, **only** per the resolved open design question |
| `tests/test_assessment.py` | New |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| `src/easy_verifier/core/judge.py` | T020's rating contract is fixed; this task consumes it |
| `src/easy_verifier/core/metrics.py` | Not an input to an assessment |

---

## Test Plan

Unit tests over hand-built findings and ratings. Hardwire each weight to both extremes and re-run.
AC #5 (no blending) needs a structural test, not a behavioral one — a future refactor could
reintroduce a merged figure and every behavioral test would still pass.

---

## Completion Checklist

- [ ] Open design question resolved with the Supervisor **before** implementation
- [ ] Implementation done
- [ ] Self-review: `Skill({ skill: "code-review" })` run
- [ ] Security review: **required (Medium risk)** — built-in cannot run here; review the diff surface directly and record the substitution
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T021.md`'s Evidence table
- [ ] `Skill({ skill: "verify" })` run
- [ ] `memory/MEMORY.md` updated
- [ ] Supervisor notified: task ready for Stage 4 review
