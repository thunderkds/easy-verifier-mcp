# TASK_REVIEW — T102: Stray scan outputs with private filenames

> Sibling of `tasks/TASK_GUIDE_T102.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t100_no_personal_identifiers.py::test_no_tracked_path_contains_a_personal_identifier` (red `1 failed, 2 passed` before the removal, green after). Supervisor rerun: `3 passed in 1.23s` |
| Verification command run | ☑ pass | `2 failed, 2855 passed, 2 skipped in 449.28s`. The only failures are the 2 known container tests. ruff: All checks passed! |
| Negative cases hold | ☑ pass | Supervisor: `git ls-files` path check for the private tokens gives 0; the commit message has no names; nothing in src/tests referenced the removed files |
| verify | ☑ pass | No runtime surface changed (files deleted, test added). Guard rerun confirms — pass |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Review covered 8 deletions, `.gitignore`, and one new test. P0–P3: none. Low risk, so no security-review is required. Pass |
| Full smoke suite still green (no regression) | ☑ pass | No new failures |
| **UI: Visual regression (diff or verdict pasted)** | ☑ N/A | No UI |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☑ N/A | No UI |
| **UI: Responsiveness at target viewports** | ☑ N/A | No UI |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE** (captured before any implementation commit; filenames withheld, count only):

```
$ date -u
2026-10-14T10:54:38Z
$ git ls-files | grep -E '^[^/]*_before\.(json|err)$' | wc -l
8
$ pytest -q tests/test_t100_no_personal_identifiers.py
..                                                                       [100%]
2 passed in 0.73s
```

**AFTER**: tracked root `*_before.*` count 0, guard test `3 passed in 1.23s` (Supervisor, 2026-10-14).

**DELTA**: A private repo name can no longer reach the remote through a file name; the guard test now checks paths as well as contents.

**WITNESS**: Supervisor, 2026-10-14: path check and guard rerun.