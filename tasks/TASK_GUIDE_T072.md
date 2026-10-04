# TASK_GUIDE — T072: Area coverage doc — map the 32 evaluation areas to today's rules and planned homes
**Date**: 2026-10-04
**Complexity Level**: C1
**Risk Level**: Low
**Priority**: P1
**Assigned agent**: Supervisor (docs-only)
**Agent guide**: `.claude/agents/general-agent-template.md`

---

## Requirement (Pillar 1 — Adapt the requirement)

User (2026-10-04), after asking where the 32 conditions are mapped to the repos: "add it to the document
to refer, if the currently map, update the docs, if not, create the new one". No existing doc mapped
the areas (docs never mention them), so a new doc is created.

**Restated intent**:
> One reference page listing all 32 areas with the rules that measure each today, the status (covered /
> partial / not yet) and the planned dimension/pack and task for the rest — kept honest by a test.

**Out of scope**: building any new rule or dimension (T041–T049).

**Requirement Refs**: FR-051 (areas shown by name), FR-066 (evaluation docs).

### Requirement Fidelity Gate

- [x] Restated intent matches the request
- [x] Area names taken verbatim from `judge.AREAS`
- [x] Every AC traces to the Requirement
- [x] Refs exist in `PRD.md`

---

## Dependencies & Reachability

**Depends on**: None
**Entry point**: `docs/AREA_COVERAGE.md`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to |
|---|---|---|
| 1 | `docs/AREA_COVERAGE.md` has one row per `judge.AREAS` entry, in order, with the exact name | FR-051 |
| 2 | Each row's rules equal `judge.RATING_RULES` filtered by that area; documentation checks listed | FR-051 |
| 3 | Status is "Not yet" exactly when the area has no rule; each "Not yet" row names a planned home and task | FR-066 |
| 4 | Summary counts equal the rows | FR-066 |
| 5 | README docs table, EVALUATION_GUIDE and SCORING_RULES link the page | FR-066 |

### Verification Command

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/test_t072_area_coverage_doc.py tests/test_t071_evaluation_docs.py tests/test_t018_readme.py -q
```

## Files to Change

| File | Change |
|---|---|
| `docs/AREA_COVERAGE.md` | new (force-added; `docs/` is gitignored) |
| `README.md`, `docs/EVALUATION_GUIDE.md`, `docs/SCORING_RULES.md` | links |
| `tests/test_t072_area_coverage_doc.py` | new |
