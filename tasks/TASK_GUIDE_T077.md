# TASK_GUIDE — T077: T075 review fixes — honest requirement-fidelity on real repos
**Date**: 2026-10-04
**Complexity Level**: C2
**Risk Level**: Medium
**Priority**: P0
**Assigned agent**: backend-developer
**Agent guide**: `.claude/agents/backend.md`

---

## Mandatory Startup (Do Not Skip)

1. Read `PROJECT_SPEC.md`, `memory/MEMORY.md`, this file, `.claude/agents/backend.md`
2. Read `tasks/TASK_GUIDE_T075.md` and `tasks/TASK_REVIEW_T075.md` (Design) — this task finishes T075 on the **same branch**
3. Read `<repo>/docs/ddr/0011-code-derived-rules-and-flexible-conventions.md` (incl. the 2026-10-04 addendum)

---

## Requirement (Pillar 1 — Adapt the requirement)

Supervisor Stage 4 review of T075 (2026-10-04): nest-api scored requirement-fidelity **0**, wrong for
known reasons. The user asked for the wave to run automatically; a number known to be wrong is not
shippable (DDR-0010 spirit). Decisions (Supervisor, under DDR-0011's "flexible, not one format"):
A — add `requirements_doc_missing` (document rule, 10, at most 0) replacing `requirements_docs_count` in
the rating (the count stays computed, unrated); B — checklist lines (`- [ ]`/`- [x]`) are plan tasks, not
requirement items: drop them from curated defaults (a repo may declare them).

**Restated intent**:
> requirement-fidelity on real repos reflects real routes, real tests, real requirement items and the
> repo's own git history, and a missing requirements document is a failed rule — no artefact of a parser
> or path bug.

**Out of scope**: embedding local/config conventions for replay (T078); other dimensions.

**Requirement Refs**: FR-067, FR-068, FR-070.

### Requirement Fidelity Gate

- [x] Restated intent confirmed (Supervisor review, user mandate "run automatically")
- [x] Domain terms align (Requirement item, Convention pattern)
- [x] Every AC traces to the Requirement
- [x] All Requirement Refs exist in `PRD.md`

---

## Dependencies & Reachability

**Depends on**: T075 — same branch `feat/T075-requirement-fidelity-code-rules`
**Entry point**: `requirements_doc_missing`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to |
|---|---|---|
| 1 | `requirements_doc_missing` (value 1 when the requirements-doc role search found nothing, 0 otherwise; at most 0; weight 10; ISO/IEC/IEEE 29148) replaces `requirements_docs_count` in `RATING_RULES['requirement-fidelity']`; the count is still computed but unrated | FR-067 |
| 2 | Curated `requirement_item_patterns` no longer include checklist lines; a repo can add them via its conventions | FR-068 |
| 3 | `find_routes` handler name survives multi-line decorators (`@ApiResponse({\n ... })`, stacked decorators) — NestJS, Spring, ASP.NET fixtures | FR-070 |
| 4 | A regression test that **fails without** `git log --relative` (target directory nested inside a larger git repository) | FR-070 |
| 5 | The same path-prefix bug is fixed for the existing co-change metric (`code_commits_with_docs_share` / T055 `_commit_file_sets`) with a test | FR-070 |
| 6 | Full suite green except the 2 known container tests; `docs/SCORING_RULES.md` / `AREA_COVERAGE.md` updated; T072 sync test passes | FR-066 |

## Evaluation & Acceptance

### Verification Command

```bash
cd <worktree> && PYTHONPATH=src <repo>/.venv/bin/python -m pytest tests/test_t075_requirement_fidelity_code_rules.py tests/test_t077_rf_review_fixes.py -q
```

### Evidence

> Filled by the reviewer in `tasks/TASK_REVIEW_T077.md`.

## Demonstration

> BEFORE (Supervisor): T075 branch on nest-api — requirement-fidelity 0; routes 11/17 untested (most "(no handler)"); requirement items 0/300 (plan checklists); issue refs abstained (path prefix).

## UI / Design Acceptance Criteria

Pure backend — ☐ N/A.

## Approach

**Pattern reference**: `core/structure.py` `find_routes` / `_decorated_name`; `dimensions/requirement_fidelity.py`; `core/git.py` `run_git_text`; T074's `architecture_description_missing` (missing-doc rule pattern).

Budget ~55 tool calls; the Supervisor does real-repo verification.

## Files to Change (Predicted)

| File | Change |
|---|---|
| `core/judge.py`, `core/metrics.py`, `dimensions/requirement_fidelity.py`, `core/structure.py`, `registry/curated/conventions.toml` | fixes above |
| `tests/test_t077_rf_review_fixes.py` | new |

## Files Must NOT Touch

| File | Reason |
|---|---|
| rating arithmetic, gates, floor logic | DDR-0010 |
| conventions replay embedding | T078 |

## Completion Checklist

- [ ] Implementation done; tests pass; ruff clean
- [ ] Supervisor notified
