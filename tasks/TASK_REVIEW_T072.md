# TASK_REVIEW — T072: Area coverage doc

> Sibling of `tasks/TASK_GUIDE_T072.md`. Everything here is **filled by the reviewer at Stage
> 4/5** — it is deliberately NOT in the guide, because the implementing agent re-reads the guide on
> every turn and never fills these two sections.
>
> Consumers resolve each section **guide first, this file second** (`.claude/hooks/lib/guide_sections.py`):
> a legacy guide that still carries these sections inline keeps working unchanged, and a stray
> review file can never override an inline section.

---

## Evidence

| Check | Result | Notes / output snippet |
|-------|--------|------------------------|
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t072_area_coverage_doc.py` (6 tests: one row per AREAS in order; row rules == RATING_RULES by area; status vs has-rule; Not-yet rows name home + task; summary counts; documentation checks listed) → 6 passed — pass |
| Verification command run | ☑ pass | `pytest tests/test_t072_area_coverage_doc.py tests/test_t071_evaluation_docs.py tests/test_t018_readme.py -q` → 89 passed, 1 skipped (README test first failed on the word 'planned' in the new row; reworded) — pass |
| Negative cases hold | ☑ pass | the README 'planned' guard caught the first wording; the row/rule comparison is exact-set, so any added/moved rule fails the test — pass |
| verify | ☐ N/A | docs-only; no src/ change — N/A |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | new doc generated from judge.AREAS / RATING_RULES / DOCUMENTATION_RULES; planned homes from BRAINSTORMING_LOG_evaluation-areas.md + Kanban T041–T049; 3 link edits — pass |
| Full smoke suite still green (no regression) | ☑ pass | docs + one test; doc/README suites green — pass |
| **UI: Visual regression (diff or verdict pasted)** | ☐ N/A | docs only |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☐ N/A | docs only |
| **UI: Responsiveness at target viewports** | ☐ N/A | docs only |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE**: no doc mapped the 32 areas — `grep -i area docs/*.md README.md` returned nothing relevant (2026-10-04, develop `5b9dd7c`).

**AFTER**: `docs/AREA_COVERAGE.md` — Summary: Covered 4 · Partial 7 · Not yet 21; 32-row mapping table with rules, planned home (T041–T049) and notes; linked from README, EVALUATION_GUIDE, SCORING_RULES.

**DELTA**: a reader can see which of the 32 areas a score actually covers and which task adds the rest.

**WITNESS**: Supervisor, 2026-10-04 — doc generated from code and verified by the new test.
