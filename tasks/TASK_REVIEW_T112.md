# TASK_REVIEW — T112: Agent-confirmed test ↔ changed-symbol pairs

> Sibling of `tasks/TASK_GUIDE_T112.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☐ pass / ☐ fail | [test file path(s) — required before Done] |
| Verification command run | ☐ pass / ☐ fail | [paste actual output] |
| Negative cases hold | ☐ pass / ☐ fail | |
| verify | ☐ pass / ☐ fail / ☐ N/A | [what was observed — must literally state "pass" or "fail" here too, e.g. "skill run, feature confirmed working — pass": the merge gate scans this Notes column for the word "pass", not just the Result column] |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☐ pass / ☐ fail | [what was reviewed vs. skipped, and why] |
| Full smoke suite still green (no regression) | ☐ pass / ☐ fail | |
| **UI: Visual regression (diff or verdict pasted)** | ☐ pass / ☐ fail / ☐ N/A | [screenshot path or LLM verdict — required for UI tasks, Hard-Stop Gate 6] |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☐ pass / ☐ fail / ☐ N/A | [method used + output] |
| **UI: Responsiveness at target viewports** | ☐ pass / ☐ fail / ☐ N/A | [viewports tested, any overflow findings] |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE** (captured 2026-10-17T03:17:04Z by backend-developer on `feat/T112-test-symbol-pairs` at
`c457c70` -- no implementation commit yet). Synthetic repo (built by a scratch script): root
`pyproject.toml`; `utils/dates.py` defines `def parse_date(text)`; `tests/test_api.py` imports and
calls `parse_date`. Commit 1 `chore: initial`; commit 2 `fix: parse_date added one day` edits the
body of `parse_date` and adds `test_parse_date_keeps_the_day` (calling `parse_date`) to
`tests/test_api.py`.

```
$ date -u +%Y-%m-%dT%H:%M:%SZ
2026-10-17T03:17:04Z
$ PYTHONPATH=src:<py312 site-packages> python3.12 -m easy_verifier.adapters.cli score \
    --repo <scratch>/demo --scope changes --ref HEAD < /dev/null > before.json   # exit=0
change_risk 0 | kind bugfix detected
  bugfix_without_regression_test = 0 passed=False
    cites: ['utils/dates.py']
    derivation (metrics): "0 matched test files: none of the test files added or changed
    (tests/test_api.py) matches the 1 changed source file(s) cited; a test file counts when it is
    added or changed in this change and its name is a conventional test name of a changed source
    file in the same project (test-strategy's correspondence; project boundaries read from
    manifests anywhere above the files); a deleted test never counts"
```

The changed test calls the changed function, but because its name does not correspond
(`test_api.py` vs `dates.py`) the bugfix scores 0 / fail.

**AFTER**: [same command, post-change] OR [verbatim excerpt of the new content]

**DELTA**: [one sentence — what a user can now do that they could not before]

**WITNESS**: [who ran it and when — derived from `memory/event-trace/Txxx.jsonl`, never the
implementing agent alone]

---

## Deviations and edge-case rules (backend-developer; rules 1-8 accepted by the Supervisor 2026-10-17)

1. **Deviation -- project boundary for symbol pairs is manifest-only.** A symbol pair needs the
   source and test to share the deepest directory holding a project manifest (repository root
   when none does). test-strategy's `_project_boundary` also cuts at the first non-layout
   directory, so `utils/dates.py` (project `utils`) and `tests/test_api.py` (project root) would
   be different projects and the guide's own AC2 example could never pair. Name pairs keep
   `_correspondence` unchanged; cross-project tests (separate manifests) still never pair.
2. Enclosing declaration = the nearest declaration above the changed line inside its hunk, else
   the one git names in the hunk header (a header alone misses a small function whose `def`
   line is a context line of the hunk).
3. A symbol under 4 characters or in `COMMON_SYMBOLS` never pairs; a name the test declares
   itself is never a reference.
4. The cited `ref` prefers the first line the diff added to the test that names the symbol,
   else the first line naming it.
5. Worktree scope reads `git diff HEAD` (not used above the changes-diff ceiling); an untracked
   file counts every line as added.
6. `needs_input.test_pairs` is not asked when there is neither a proposal nor an unpaired
   changed test (nothing to judge); asked until at least one answer entry applies.
7. Duplicate answers, rejecting a pair that was not proposed, and added pairs without a valid
   `ref` are listed in `rejected` and change nothing.
8. A bugfix with changed source now reads its changed tests through `_changed_code` (as the
   feature rule already did); a bugfix with no changed source still reads nothing.

## AC9 -- pre-registered expectations (written 2026-10-17, before any AC9 run)

Command per row: `cli score --repo <real-repos>/<alias> --scope changes --ref <ref> < /dev/null`,
run in the background one at a time, on branch `feat/T112-test-symbol-pairs`.

| # | Repo / ref | Expected |
|---|---|---|
| (a) | node-monorepo `09be767d0` (bugfix, no test) | `change_risk` 0, `bugfix_without_regression_test` 0 fail; `test_pairs.pairs` = [], `unpaired_tests` = [] (no proposals; MCP would not ask) |
| (b) | fullstack-ts `522d666` (bugfix with test, T108) | still 100, metric 1; `InventoryPage.tsx -> InventoryPage.test.tsx` now `basis: "symbol"` (symbol `InventoryPage`, from the `export function InventoryPage()` hunk header), status detected; `IngredientFormDialog.tsx` pairs by symbol only if the test names one of its changed symbols -- expected unpaired |
| (c) | fullstack-ts `c2edf83` (no kind prefix -> feature) -- found by the search below | `apps/web/src/components/LowStockWidget/api.ts -> LowStockWidget.test.tsx` `basis: "symbol"` (symbol `fetchLowStock`), a pair the name rule cannot make (`api.ts` vs `LowStockWidget.test.tsx`); `LowStockWidget.tsx -> LowStockWidget.test.tsx` present (symbol or name); the api-side sources (`alerts.*`, dto, module) unpaired |

Search used for (c): a scratch script that, for the newest 300 non-merge commits of a repo, parses
`git show -M <sha>` with `_diff_files`, takes `change_risk.changed_symbols` of each changed source
and lists changed tests that reference one (`_references`) but are not a name match
(`_correspondence`). fullstack-ts: 69 candidate pairs; node-monorepo: none printed (run under a 300 s timeout, so
not proven exhaustive).
