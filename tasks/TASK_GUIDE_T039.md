# TASK_GUIDE — T039: Shared documentation-present rule, overall rating over N dimensions, area labels
**Date**: 2026-09-28
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
7. Read `docs/ddr/0008-thirteen-dimensions-rule-groups-and-optional-packs.md` and `BRAINSTORMING_LOG_evaluation-areas.md` (32-area mapping table)

---

## Requirement (Pillar 1 — Adapt the requirement)

User (2026-09-28) supplied 32 evaluation areas; decided E2 (areas as named rule groups), E3 (unverifiable areas = documentation present/missing, never scored).

**Restated intent**:
> The engine supports named rule groups, a shared 'documentation present / missing' rule that never produces a number, and an overall rating over any number of declared dimensions.

**Out of scope**:
- Implementing specific new dimensions (T041–T046)
- Area rule groups in existing dimensions (T040)

**Requirement Refs**:
- FR-051: rule groups with area labels
- FR-052: documentation present/missing, never scored
- FR-054: overall over all declared dimensions

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [ ] Restated intent confirmed to match the user's request (by Supervisor / user — not the implementing agent)
- [ ] Domain terms align with `PROJECT_SPEC.md` glossary (`grill-with-docs` run if terminology was fuzzy)
- [ ] Every Acceptance Criterion below traces to a line in the Requirement
- [ ] All Requirement Refs exist in `PRD.md` and are fully covered by the Acceptance Criteria above

> An agent must NOT start implementing until this gate is checked. If anything here is unclear,
> STOP and ask the Supervisor (Karpathy: Think Before Coding).

---

## Dependencies & Reachability

**Depends on**: T035 — per-dimension rule data

**Entry point**: `documentation_present`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | Rules carry an `area` label (one of the 32 names); `score` output and report group rule results by area | rule groups |
| 2 | `documentation_present` rule type: result `present` (cited file) / `missing`; contributes 0 weight and never a number | E3 |
| 3 | `rate_overall` accepts any number of declared dimensions (not exactly seven); disclosure unchanged in form | FR-054 |
| 4 | Existing 7-dimension outputs unchanged except area labels | no regression |

---

## Evaluation & Acceptance (How we know the agent worked correctly)

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | repo with `docs/runbook.md` | incident-response area: documentation present, cites file, no number | automated test |
| 2 | 8 fake dimensions | overall averages raters, discloses 8 | automated test |

### Verification Command (exact, runnable)

```bash
python -m pytest -q
python -m ruff check src tests
```

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T039.md`.

---

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T039.md`.

---

## UI / Design Acceptance Criteria

> N/A — pure backend task (no UI component). All three UI Evidence rows are ☐ N/A.

---

## Approach

**Pattern reference**: `core/judge.py` `rate_overall` and `RatingAbstention` disclosure

Rule groups are a label on rule data, not a new structure. Keep the dimension list discovered from `dimensions/` (`dimension_names`) as the single truth for N.

---

## Edge Case Checklist

- [ ] Area with only documentation rules → dimension-level abstention reason must be explicit
- [ ] Report layout with 32 areas stays readable (group collapsed by dimension)

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/core/judge.py` | area label, doc rule, N-dim overall |
| `src/easy_verifier/core/report.py` | area grouping |
| `tests/` |  |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| COVERAGE_FLOORS existing values | user decision |

---

## Test Plan

Doc-rule tests; N-dimension overall tests; report snapshot.

---

## Completion Checklist

- [ ] Implementation done
- [ ] Self-review: `Skill({ skill: "code-review" })` run
- [ ] Security review: `Skill({ skill: "security-review" })` run (Medium risk)
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T039.md`'s Evidence table (Hard-Stop Gate 5)
- [ ] `Skill({ skill: "verify" })` run — feature confirmed working at a real surface
- [ ] `memory/MEMORY.md` updated (if new patterns or feedback learned)
- [ ] Supervisor notified: task ready for Stage 4 review
