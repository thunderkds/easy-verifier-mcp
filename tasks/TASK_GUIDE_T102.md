# TASK_GUIDE — T102: Stray real-repo scan outputs at the repo root carry private names in their filenames
**Date**: 2026-10-14
**Complexity Level**: C0
**Risk Level**: Low
**Priority**: P0 (follow-up gap in T100; blocks the next push)
**Assigned agent**: backend-developer
**Agent guide**: `.claude/agents/backend.md`
**Depends on**: none

## Bug Fix Task Guide — T102

### Mental Model (Supervisor)
- **Observed:** 8 tracked files at the repo root, committed by accident in T035 (`0244c94`), are named
  `<real-repo>_before.json` / `<real-repo>_before.err` for 3 private repos plus this repo. The T100 guard
  test checks file **contents** only, so the names slipped through. The JSON payloads also list the
  private repos' file structure. Two task reviews (`TASK_REVIEW_T049.md`, `TASK_REVIEW_T056.md`) and one
  of the JSON files mention the `_before.json` naming.
- **Expected:** none of the 8 files is tracked; every tracked **path** passes the same identifier check
  as contents; mentions of the deleted files in tracked docs no longer point at a missing file in a
  misleading way. Leave historical evidence text as it is, apart from naming.
- **Divergence point:** `tests/test_t100_no_personal_identifiers.py` scans contents of `git ls-files`,
  not the paths themselves.

### Acceptance Criteria
| # | Criterion |
|---|-----------|
| 1 | `git rm` all 8 root `*_before.json` / `*_before.err` files (they are scratch outputs; nothing imports them; confirm with `git grep`) |
| 2 | The guard test also fails on a tracked **path** containing a forbidden token. Write it first, red before the removal and green after. Keep the reversed-token storage |
| 3 | Add `/*_before.json` and `/*_before.err` to `.gitignore` so the scan scratch cannot be re-committed |
| 4 | Full suite passes (apart from the 2 known container tests) and ruff is clean |

### Diagnosis Gates (Pillar 1)
- [ ] Reproduced: the guard test passes while the private filenames are tracked
- [ ] Hypothesis confirmed: paths are not checked

### Fix Gates (Pillar 2)
- [ ] Regression test red before, green after
- [ ] AC 1–4 pasted

### Cleanup Checklist (Pillar 3)
- [ ] Post-mortem line: the T100 guide's AC1 searched contents with `git grep`, which never matches a file **name**

### Files Must NOT Touch
`src/`, and anything outside the 8 files, `.gitignore`, the guard test, and the review file.

### Verification Command
```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check src tests
```

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T102.md`.

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T102.md`.

## UI / Design Acceptance Criteria

> N/A — no UI. All three UI Evidence rows are ☐ N/A.
