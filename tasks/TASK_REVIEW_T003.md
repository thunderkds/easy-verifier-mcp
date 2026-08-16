# TASK_REVIEW — T003: scope.py — task/changes/worktree/project scope resolution

> Sibling of `tasks/TASK_GUIDE_T003.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t003_scope.py` — 30 tests, one per AC #1–#9 plus Success Criteria 1–4 and the Edge Case Checklist (root commit, invalid ref, ambiguous task id, git-absent structured results, no-remote static check). |
| Verification command run | ☑ pass | `PYTHONPATH=src python3 -m pytest tests/test_t003_scope.py -q` → `30 passed in 0.23s` (2026-08-16T09:23:37Z, see AFTER). |
| Negative cases hold | ☑ pass | Covered in `tests/test_t003_scope.py`: invalid ref (`test_changes_scope_with_an_invalid_ref_is_a_structured_error`), unknown task id (`test_task_scope_for_a_nonexistent_id_lists_known_ids`), ambiguous task id (`test_task_scope_two_guides_matching_one_id_is_a_deterministic_error`), no git repo for `changes`/`worktree` (`test_no_git_repo_project_works_changes_and_worktree_are_structured`), standalone `task` refusal not widening to `project` (`test_task_scope_standalone_refusal_does_not_fall_back_to_project_scope`), unknown `kind` and missing required args raise `ScopeError`. |
| verify | ☑ pass | Ran the guide's exact Verification Command directly (`pytest tests/test_t003_scope.py -q`) plus the full repo suite — both green, no regressions — pass. |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Only `src/easy_verifier/core/scope.py` (new) and `tests/test_t003_scope.py` (new) were added; no existing file was edited. `models.py`, `pipeline.py`, and `cli.py` were deliberately **not** touched — see Notes below. |
| Full smoke suite still green (no regression) | ☑ pass | `PYTHONPATH=src python3 -m pytest tests/ -q` → `196 passed in 0.48s` (166 pre-existing + 30 new; 2026-08-16, post-change). `ruff check src tests` → `All checks passed!`; `ruff format --check src tests` → `18 files already formatted`. |
| **UI: Visual regression (diff or verdict pasted)** | ☐ N/A | Pure backend module (`scope.py`), no UI component. |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☐ N/A | Pure backend module, no UI component. |
| **UI: Responsiveness at target viewports** | ☐ N/A | Pure backend module, no UI component. |

**Note — deliberate deviation from the guide's "Files to Change (Predicted)" table**: the guide lists
`models.py` (add `Scope`), `pipeline.py` (accept a resolved `Scope`), and `cli.py` (`--scope`/`--task`/
`--range` flags) as predicted files. `memory/MEMORY.md`'s decisions record states plainly:
"`run_dimension()`'s contract is fixed... changing the contract is a broad, cross-cutting rewrite" —
and the spawn prompt for this task repeats that constraint verbatim. Wiring `resolve_scope()`'s output
into `run_dimension()`'s signature, or into the CLI's argument surface, would be exactly that kind of
change and is not required by any of the nine Acceptance Criteria, all of which test `resolve_scope`
directly. `Scope`/`TaskRef` are defined in the new `scope.py` itself rather than in `models.py`, since
nothing outside `scope.py` consumes them yet — adding an unused import surface to the shared `models.py`
module would be speculative (Simplicity First). This wiring is left for whichever task integrates scope
selection into the pipeline/CLI (per the codebase map, `budget.py`'s relevance ordering — T005/T012 per
`PROJECT_SPEC.md`'s layer map — is the next consumer). Flagged for Supervisor confirmation at Stage 4.

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE**: Captured 2026-08-16T09:18:47Z, before any T003 implementation commit exists, in worktree
`/home/hungnguyenhuu/workspace/pets/hungnguyen111/easy-verifier-mcp/.claude/worktrees/agent-a9350b8c7f8100e4c`:

```
$ date -u +%Y-%m-%dT%H:%M:%SZ
2026-08-16T09:18:47Z
$ ls src/easy_verifier/core/scope.py
ls: cannot access 'src/easy_verifier/core/scope.py': No such file or directory
$ PYTHONPATH=src python3 -c "from easy_verifier.core.scope import resolve_scope"
Traceback (most recent call last):
  File "<string>", line 1, in <module>
ModuleNotFoundError: No module named 'easy_verifier.core.scope'
$ ls tests/test_t003_scope.py
ls: cannot access 'tests/test_t003_scope.py': No such file or directory
```

Baseline full suite (166 tests, pre-T003) at 2026-08-16T09:18:51Z:
```
$ PYTHONPATH=src python3 -m pytest tests/ -q
........................................................................ [ 43%]
........................................................................ [ 86%]
......................                                                   [100%]
166 passed in 0.51s
```

**AFTER**: Captured 2026-08-16T09:23:37Z, in the same worktree, after the implementation:

```
$ date -u +%Y-%m-%dT%H:%M:%SZ
2026-08-16T09:23:37Z
$ PYTHONPATH=src python3 -c "
from easy_verifier.core.scope import resolve_scope
from easy_verifier.core.context import detect_context
ctx = detect_context('.')
s = resolve_scope('task', '.', ctx, task_id='t003')
print('task_ref:', s.task_ref.task_id, s.task_ref.guide_path, len(s.task_ref.acceptance_criteria), 'criteria')
"
task_ref: T003 tasks/TASK_GUIDE_T003.md 9 criteria
$ PYTHONPATH=src python3 -m pytest tests/test_t003_scope.py -q
..............................                                           [100%]
30 passed in 0.23s
```

Full suite, same timestamp:
```
$ PYTHONPATH=src python3 -m pytest tests/ -q
........................................................................ [ 36%]
........................................................................ [ 73%]
....................................................                     [100%]
196 passed in 0.48s
```

**DELTA**: A caller can now ask for a narrower question than "the whole repo" — `resolve_scope("task", repo, ctx, task_id="T003")` (lowercase/`TASK_GUIDE_T007.md` forms normalized too) resolves a task ID to its guide and parsed Acceptance Criteria, `"changes"` derives a changed-file list and diff for a range/commit/branch via local git only, `"worktree"` reports uncommitted modifications, and `"project"` lists the relevant file set with vendored/`.git` dirs excluded — none of which `resolve_scope` could do before this commit (it did not exist).

**WITNESS**: Implementing agent (backend-developer, Task T003), 2026-08-16, via the Bash calls timestamped above in this worktree — Stage 4/5 reviewer to independently re-run the Verification Command and confirm against `memory/event-trace/T003.jsonl` per standing procedure (T001's merge-gate trap (a) in `memory/MEMORY.md`).
