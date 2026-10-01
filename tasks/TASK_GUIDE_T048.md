# TASK_GUIDE — T048: Finance pack (#3 financial integrity & historical reconstruction)
**Date**: 2026-09-28
**Complexity Level**: C2
**Risk Level**: Medium
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
6. Read `memory/codebase-map.md`
7. Read `docs/ddr/0008-thirteen-dimensions-rule-groups-and-optional-packs.md` and `BRAINSTORMING_LOG_evaluation-areas.md` (32-area mapping table)
8. Read `docs/ddr/0007-cited-reference-registry-and-reference-gate.md` and `BRAINSTORMING_LOG_reference-registry.md` (approved rule table, edge cases)

---

## Requirement (Pillar 1 — Adapt the requirement)

Decided E1: finance is an optional pack; area #3 financial integrity & historical reconstruction.

**Restated intent**:
> When active, the finance pack flags floating-point money handling and missing audit/immutability evidence, and routes ledger-correctness judgment to the evaluate gate.

**Out of scope**:
- Accounting correctness judgment by rules (goes to evaluate gate)

**Requirement Refs**:
- FR-053
- FR-043 (cited rules)
- FR-036 (judgment at evaluate gate)

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [ ] Restated intent confirmed to match the user's request (by Supervisor / user — not the implementing agent)
- [ ] Domain terms align with `PROJECT_SPEC.md` glossary (`grill-with-docs` run if terminology was fuzzy)
- [ ] Every Acceptance Criterion below traces to a line in the Requirement
- [ ] All Requirement Refs exist in `PRD.md` and are fully covered by the Acceptance Criteria above

> An agent must NOT start implementing until this gate is checked. If anything here is unclear,
> STOP and ask the Supervisor (Karpathy: Think Before Coding).

---

## Dependencies & Reachability

**Depends on**: T047 — pack mechanism

**Entry point**: `finance`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | Money-named fields/vars typed as float/double = 0 (ISO/IEC 5055 reliability; language decimal-type docs cited per language) | float money |
| 2 | Ledger/transaction tables have audit columns (created_at/by) and no UPDATE/DELETE on ledger rows in code (append-only evidence) | historical reconstruction |
| 3 | Inactive pack → no output | optional |

---

## Evaluation & Acceptance (How we know the agent worked correctly)

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | `amount: float` in a payments model | rule unmet, cited | automated test |
| 2 | `amount: Decimal` | rule met | automated test |

### Verification Command (exact, runnable)

```bash
python -m pytest -q
python -m ruff check src tests
```

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T048.md`.

---

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T048.md`.

---

## UI / Design Acceptance Criteria

> N/A — pure backend task (no UI component). All three UI Evidence rows are ☐ N/A.

---

## Approach

**Pattern reference**: T047 healthcare pack

Name heuristics (amount, price, balance, total, fee) + type tokens from registry; conservative, cited.

---

## Edge Case Checklist

- [ ] Float used for non-money `amount_of_items`
- [ ] Currency stored as integer minor units (valid)

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/registry/packs/finance.toml` | new |
| `src/easy_verifier/core/metrics.py` | pack metrics |
| `tests/` |  |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| healthcare pack | separate |

---

## Test Plan

Float/Decimal fixtures per language; append-only fixtures.

---

## Completion Checklist

- [ ] Implementation done
- [ ] Self-review: `Skill({ skill: "code-review" })` run
- [ ] Security review: `Skill({ skill: "security-review" })` run (Medium risk)
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T048.md`'s Evidence table (Hard-Stop Gate 5)
- [ ] `Skill({ skill: "verify" })` run — feature confirmed working at a real surface
- [ ] `memory/MEMORY.md` updated (if new patterns or feedback learned)
- [ ] Supervisor notified: task ready for Stage 4 review
