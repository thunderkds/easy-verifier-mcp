# TASK_GUIDE — T080: Evaluation guide refresh after DDR-0011 (T074–T077)
**Date**: 2026-10-05
**Complexity Level**: C1
**Risk Level**: Low
**Priority**: P1
**Assigned agent**: Supervisor (docs-only)
**Agent guide**: `.claude/agents/general-agent-template.md`

---

## Requirement (Pillar 1 — Adapt the requirement)

User (2026-10-05): "check the guide if mismatch and need to update" → "so update them all for the
latest". `docs/EVALUATION_GUIDE.md` was written in T071 before T074–T077 changed architecture and
requirement-fidelity to documents 20 / code 80. `SCORING_RULES.md` and `AREA_COVERAGE.md` were updated
with those tasks; the guide was not.

Mismatches found (Supervisor, 2026-10-05, develop `7d64f08`):
1. `EVALUATION_GUIDE.md:77-79` — "The requirement-fidelity traceability metrics always abstain from a
   read-only pack". False since T075: routes↔tests, commit issue references and requirement items are
   measured; each abstains only on its own empty input (no route, < 20 commits, no item).
2. Worked example coffee-shop-api — "2 of 7 rated", architecture and requirement-fidelity listed as
   warnings. Now both are rated (architecture 80, requirement-fidelity 50 per T074/T077 evidence).
3. Worked example bryony — architecture 70; now 83 (T074 evidence).
4. Missing: since T074/T077 a missing architecture / requirements document is a failed rule, not missing
   evidence — a reader cannot learn this from "When to trust a number".

**Restated intent**:
> The guide states only what the develop code does today, and its worked examples are numbers from a
> fresh `score` run with today's develop code, dated.

**Out of scope**: any `src/` change; changing SCORING_RULES/AREA_COVERAGE (already current); T078/T079.

**Requirement Refs**: FR-066 (evaluation docs), FR-067…FR-071 (DDR-0011 code-derived rules).

### Requirement Fidelity Gate

- [x] Restated intent matches the request
- [x] Each mismatch cites a guide line and the task that changed the behaviour
- [x] Every AC traces to the Requirement
- [x] Refs exist in `PRD.md`

---

## Dependencies & Reachability

**Depends on**: None (T074–T077 Done)
**Entry point**: `docs/EVALUATION_GUIDE.md`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to |
|---|---|---|
| 1 | The guide no longer claims requirement-fidelity traceability always abstains; it names the three code rules and their own abstention conditions | FR-066, FR-069 |
| 2 | "When to trust a number" says a missing architecture/requirements document is a failed rule once the role search ran, not a warning | FR-066, FR-067 |
| 3 | Worked examples are dated 2026-10-05 and every number equals a fresh CLI `score --scope project` run on coffee-shop-api and bryony (develop `7d64f08`) | FR-066 |
| 4 | Every new backticked identifier is declared and found in `src/` (T071 doc test) | FR-066 |
| 5 | A new test pins AC 1–3 so the stale claims cannot return | FR-066 |

### Verification Command

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/test_t071_evaluation_docs.py tests/test_t080_evaluation_guide_refresh.py tests/test_t072_area_coverage_doc.py -q
```

## Files to Change

| File | Change |
|---|---|
| `docs/EVALUATION_GUIDE.md` | fix requirement-fidelity line, add document-rule note, re-run worked examples (force-add; `docs/` is gitignored) |
| `tests/test_t071_evaluation_docs.py` | DECLARED gains new identifiers; example date 2026-10-05 |
| `tests/test_t080_evaluation_guide_refresh.py` | new |

---

## Evidence

| Gate | Result | Evidence |
|---|---|---|
| New test(s) cover acceptance criteria | ☑ pass | `tests/test_t080_evaluation_guide_refresh.py` (3 tests, AC 1/2/3/5); against the pre-fix guide (`git show HEAD:docs/EVALUATION_GUIDE.md`): `3 failed in 0.13s`; after: `3 passed in 0.10s`. Doc tests: `92 passed in 0.87s` (t071 + t072 + t080; AC 4 via t071 DECLARED + src lookup) |
| Full suite passes | ☑ pass | `2001 passed, 2 skipped in 315.80s`; `ruff check tests/` → All checks passed; `ruff format --check` → 2 files already formatted |
| Real-repo numbers match the examples | ☑ pass | CLI `score --scope project`, develop `7d64f08`, 2026-10-05. coffee-shop-api: overall 65, architecture 80 / code-quality 71 / requirement-fidelity 50 / security 59; warnings blast-radius, test-strategy (0.30); routes "0 of 17 route(s) have no test"; "9 of 42 code-changing commit(s) also changed documentation"; "0 of 51 non-merge local commit(s) … reference an issue"; items abstained "no requirement item was found in the 13 … document(s)"; top gains redaction +10, issue refs +6, max_function_ccn +4. bryony (`project/bryony/bryony`, the git repo): overall 69, architecture 83 / code-quality 67 / test-strategy 75 / security 50; batch 1 of 6, 200 of 1178; requirement-fidelity below_coverage_floor (no requirements/spec doc, no route matched); top gains redaction +9, covering-test share +6, decision_records_missing +4. (A first run on the non-git parent `project/bryony` gave 66 / 1253 files / no churn: discarded, wrong target.) |
| code-review | ☑ pass | Supervisor self-review of the diff (C1 docs-only): every number was traced back to the run JSON, and two over-claims were fixed: "adding the document is a P1 fix" (P0/P1 grouping depends on the threshold distance) and "21% of code commits" (now "9 of 42 … (21%)"). No P0–P2 findings |
| UI visual regression | ☐ N/A | docs-only, no UI |
| UI design-system compliance | ☐ N/A | docs-only, no UI |
| UI responsiveness | ☐ N/A | docs-only, no UI |
