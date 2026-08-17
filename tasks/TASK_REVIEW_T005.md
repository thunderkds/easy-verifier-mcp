# TASK_REVIEW — T[NNN]: [Short Title]

> Sibling of `tasks/TASK_GUIDE_T[NNN].md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t005_budget.py` — 21 new tests covering AC #1-#9 and the Edge Case Checklist (tiering order, laziness via `InstrumentedExcerpts`, truncation semantics, oversized excerpt, UTF-8 byte accounting, determinism, dedup, zero/negative limit). |
| Verification command run | ☑ pass | `PYTHONPATH=src .venv/bin/python -m pytest tests/test_t005_budget.py -q` → `21 passed in 0.06s` (2026-08-17T02:33:10Z). Full suite: `PYTHONPATH=src .venv/bin/python -m pytest -q` → `219 passed in 0.52s` (198 pre-existing + 21 new, zero regressions). `ruff check src tests` → `All checks passed!`. |
| Negative cases hold | ☑ pass | `test_non_positive_limit_raises_a_structured_error` (0, -1, -1000 → `BudgetError`); `test_a_lone_oversized_excerpt_is_omitted_with_truncation_stated_not_silent`; `test_an_oversized_excerpt_does_not_infinite_loop_on_an_infinite_stream`. |
| verify | ☑ pass | Manual self-review (no `Skill()` tool available to this agent): read the full diff on `models.py`, `pipeline.py`, and the new `budget.py`; confirmed the T001 redaction seam (`redact_module.redact`) still governs pack text — a first draft that called `scan().text` directly broke three T001 seam tests, caught by the full suite run and fixed. `grep` for `eval`/`exec`/`shell=True`/`subprocess`/`open(` in `budget.py` returned nothing — no new I/O or dynamic-execution surface — pass. |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Reviewed only the four changed/added files: `core/budget.py` (new), `core/models.py` (additive `TruncationRecord` + `EvidencePack.truncation` field), `core/pipeline.py` (naive cap replaced by a call to `budget.budget()`), `tests/test_t005_budget.py` (new). Did not edit `core/redact.py` (T004-owned) or `core/scope.py`/`core/context.py` — only read them for the tiering data shape (`Scope.changed_files`, `Scope.task_ref`, `context.KIT_ARTIFACTS`). |
| Full smoke suite still green (no regression) | ☑ pass | `219 passed in 0.52s`, no `xfail`/`skip`. |
| **UI: Visual regression (diff or verdict pasted)** | ☑ N/A | Backend-only task; no UI component. |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☑ N/A | Backend-only task; no UI component. |
| **UI: Responsiveness at target viewports** | ☑ N/A | Backend-only task; no UI component. |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE**: No implementation commit existed yet (worktree clean at session start; all T005 changes
were uncommitted working-tree edits). Captured by stashing those edits (`git stash push -u`) and
running the verification command against the pre-change tree:

```
$ date -u +"%Y-%m-%dT%H:%M:%SZ"
2026-08-17T02:33:01Z
$ PYTHONPATH=src /home/hungnguyenhuu/workspace/pets/hungnguyen111/easy-verifier-mcp/.venv/bin/python -m pytest tests/test_t005_budget.py -q
ERROR: file or directory not found: tests/test_t005_budget.py

no tests ran in 0.00s
EXIT:4
```

Also: `src/easy_verifier/core/pipeline.py`'s `_budget()` (the code this task replaces) admitted
excerpts strictly in stream-arrival order — a changed-file excerpt arriving late in a dimension's
`collect()` output had no priority over an unrelated file arriving first, once the byte budget was
tight (FR-011a not met).

**AFTER**: Edits restored (`git stash pop`), then:

```
$ date -u +"%Y-%m-%dT%H:%M:%SZ"
2026-08-17T02:33:10Z
$ PYTHONPATH=src /home/hungnguyenhuu/workspace/pets/hungnguyen111/easy-verifier-mcp/.venv/bin/python -m pytest tests/test_t005_budget.py -q
.....................                                                    [100%]
21 passed in 0.06s
EXIT:0
```

`src/easy_verifier/core/budget.py` now exists: `budget(excerpts, scope, limit_bytes)` admits lazily
in relevance order — tier 1 (`scope.changed_files`), then tier 2 (spec/kit artifacts, including
`scope.task_ref.guide_path`), then everything else — and `pipeline.run_dimension` calls it in place
of the old naive cap. `EvidencePack.truncation` (a new `TruncationRecord`) carries the same
`truncated`/`omitted_count` information as a structured field, additive to the existing flat fields.

**DELTA**: A caller building an evidence pack under a tight byte budget now gets the excerpts that
changed or were spec-referenced first — not whichever excerpts a dimension happened to `yield` first
— while the stream is still consumed lazily and any drop is reported explicitly, never silently.

**WITNESS**: backend-developer (this agent), 2026-08-17T02:31–02:33Z, per
`.claude/hooks/.state/active_task` (`T005`) set before the verification commands above; trace
events land in `memory/event-trace/T005.jsonl` per the repo's trace hook.
