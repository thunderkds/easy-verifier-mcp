# TASK_GUIDE — T110: `change-risk` rules for feature, refactor and chore
**Date**: 2026-10-16
**Complexity Level**: C2
**Risk Level**: Medium (new rated rules change `change_risk` for most changes)
**Priority**: P1
**Assigned agent**: backend-developer
**Agent guide**: `.claude/agents/backend.md`

---

## Mandatory Startup (Do Not Skip)

Before writing any code:
1. Read `PROJECT_SPEC.md` (glossary: **Change kind**, **Matched test**)
2. Read `memory/MEMORY.md`
3. Read this file completely
4. Read `.claude/agents/backend.md`
5. Apply the C2 process from the Complexity matrix in `.claude/agents/general-agent-template.md`
6. Read `PRD.md` FR-082; `docs/ddr/0014-change-risk-dimension.md`
7. Read T108's `src/easy_verifier/dimensions/change_risk.py` and its rule entries in `core/judge.py`

---

## Requirement (Pillar 1 — Adapt the requirement)

User, 2026-10-16: S1 rule table "Approve".

**Restated intent**:
> Replace T108's "rules for <kind> arrive in T110" abstention with the approved rules:
> **feature** — `new_code_without_test_share` ≤ 0.20 (share of changed source files with no matched
> test); **refactor** — `refactor_tests_deleted` = 0 (test files the diff deletes) and
> `refactor_uncovered_share` ≤ 0.20 (share of changed source files with **no covering test anywhere in
> the repository**, changed or not); **chore** — no rule, abstain with reason "chore: no test
> expectation". Mixed kinds keep T108's "most demanding wins". Thresholds are project defaults.

**Out of scope**: the bugfix rule (T108), the gate (T109), symbol matching (S2), weights of other
dimensions.

**Requirement Refs**: FR-082, US-022.

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [x] Restated intent confirmed against the user's request (Supervisor, 2026-10-16)
- [x] Domain terms align with `PROJECT_SPEC.md`
- [x] Every Acceptance Criterion traces to the Requirement
- [x] Requirement Refs exist in `PRD.md`

---

## Dependencies & Reachability

**Depends on**: T108
**Entry point**: `score_repository` via CLI/MCP `score` at `changes`/`worktree` scope, dimension `change-risk`

---

## Acceptance Criteria

| # | Criterion (testable) |
|---|----------------------|
| 1 | Three rules added to the `change-risk` rule table with the thresholds above, project-default citation, and each failing rule citing the offending files (uncovered changed sources, deleted tests) |
| 2 | Only the rules for the active kind apply; the others are not evaluated (no silent zero) — a test per kind |
| 3 | Chore abstains with the exact reason "chore: no test expectation"; a docs/lockfile-only diff detected as chore never fails a test rule |
| 4 | `refactor_uncovered_share` counts a changed source file as covered when any test in the repository corresponds to it (naming correspondence within one project); `new_code_without_test_share` counts only **matched** tests (added/changed in the scope) |
| 5 | A deleted test never counts as matched or covering (shared with T108) |
| 6 | **Real repos, pre-registered** (write expectations first, then run in background one at a time): one feature commit with tests (passes), one feature commit without (fails), one refactor commit (alias + hash, expectation stated), one docs-only commit (chore abstains). Paste each `change_risk` headline |
| 7 | Tests in `tests/test_t110_change_kind_rules.py` cover AC1–AC5 on synthetic repos; T108's tests stay green unchanged |

---

## Evaluation & Acceptance

### Success Criteria (observable, pass/fail)
- Each kind rates (or abstains) as specified on synthetic and real repos.
- New tests pass; full suite and ruff green.

### Verification Command (exact, runnable)

Py3.12 venv as in T107.

```bash
<py312> -m pytest -q tests/test_t110_change_kind_rules.py
<py312> -m pytest -q          # background
<py312> -m ruff check src tests
```

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T110.md`.

---

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T110.md`. BEFORE = a feature commit's `change_risk` abstaining with
> "rules for feature arrive in T110".

---

## UI / Design Acceptance Criteria

> N/A — the report block from T108 renders new rules without layout change. All three UI Evidence rows are ☐ N/A.

---

## Approach

**Pattern reference**: T108's `bugfix_without_regression_test` rule entry and metric — same shape.

1. Capture BEFORE. 2. Metrics + rules, test-first, one kind at a time. 3. AC6 real repos.

---

## Edge Case Checklist

- [ ] Feature diff with zero changed source files (tests only) → abstain "no changed source code", not 0/0
- [ ] Refactor renaming a source file and its test together (`R` entries) → covered, nothing deleted
- [ ] Refactor that moves a test (delete + add) → not a deletion when the content is a rename git detects
- [ ] Monorepo: a test in another project does not cover

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/dimensions/change_risk.py` | metrics inputs |
| `src/easy_verifier/core/judge.py`, `core/metrics.py` | 3 rules + metrics |
| `tests/test_t110_change_kind_rules.py` | new |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| other dimensions | out of scope |
| `src/easy_verifier/core/gate.py` | T109 |

---

## Test Plan

Synthetic git repos per kind; real-repo runs are evidence, not tests.

---

## Completion Checklist

- [ ] Implementation committed on `feat/T110-change-kind-rules`
- [ ] AC6 expectations written before the runs; results pasted after
- [ ] No private name or path in any tracked file (T100 guard green)
- [ ] Supervisor notified: ready for Stage 4 review
