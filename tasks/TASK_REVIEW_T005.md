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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t005_budget.py` — 26 tests covering AC #1-#9 and the Edge Case Checklist, rewritten post-Stage-4 around the `collect`-callable, tiered-pass API: tiering order (including the Stage 4 P1 regression `test_changed_files_are_admitted_first_even_after_a_long_tier_3_prefix`), per-pass laziness (`InstrumentedCollect.history`, one entry per `collect()` call), truncation semantics, oversized excerpt, UTF-8 byte accounting, determinism, dedup within and across passes, zero/negative limit, and pass-skipping when a tier's membership is empty. |
| Verification command run | ☑ pass | `PYTHONPATH=src .venv/bin/python -m pytest tests/test_t005_budget.py -q` → `26 passed in 0.08s`. Full suite: `PYTHONPATH=src .venv/bin/python -m pytest -q` → `224 passed in 0.62s` (2026-08-17T02:51:04Z; 198 pre-existing + 26 new, zero regressions after the Stage 4 rework). `ruff check src tests` → `All checks passed!`. |
| Negative cases hold | ☑ pass | `test_non_positive_limit_raises_a_structured_error` (0, -1, -1000 → `BudgetError`); `test_a_lone_oversized_excerpt_is_omitted_with_truncation_stated_not_silent`; `test_an_oversized_excerpt_does_not_infinite_loop_on_an_infinite_stream`; `test_tier_1_pass_stops_at_its_own_misfit_without_ever_reaching_tier_3` and `test_a_raise_in_a_later_pass_still_returns_a_valid_pack` (an injected exception past the natural stopping point in either a tier-1 or a tier-3 pass never fires). |
| verify | ☑ pass | Manual self-review (no `Skill()` tool available to this agent), two rounds: (1) initial implementation — read the diff, confirmed the T001 redaction seam still governs pack text; (2) Stage 4 P1/P2 fixes — re-derived `budget()`'s per-tier-pass algorithm from the coordinator's resolution, confirmed against a hand simulation before coding, then confirmed with a live end-to-end run (`git worktree` scope, real changed file) showing `changed.md` now ranks ahead of an unrelated excerpt under a tight budget — see the pipeline.py diff snippet below. `grep` for `eval`/`exec`/`shell=True`/`subprocess`/`open(` in `budget.py` returned nothing — pass. |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Stage 4 fix touched exactly the files flagged: `core/budget.py` (tier-pass rewrite, eviction machinery removed), `core/pipeline.py` (wired `resolve_scope` in, `collect` now passed as a callable), `tests/test_t005_budget.py` (rewritten for the new API + P1 regression test). `core/models.py` untouched by the fix (P1/P2 required no model change). Verified `run_dimension`'s public signature is unchanged (P2 constraint) via `git diff` on its `def` line. |
| Full smoke suite still green (no regression) | ☑ pass | `224 passed in 0.62s`, no `xfail`/`skip`. |
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

---

## Stage 4 Follow-up — P1 + P2 Resolution (2026-08-17)

Code review found the original single-pass, single-eviction implementation did not deliver real
relevance ordering in the general case (P1), and that `pipeline.py` hardcoded `scope=None`, so tier 1
could never fire in production (P2). Both were user-decided; implemented as directed, not re-argued.

**P1 fix**: `budget()`'s signature changed from `budget(excerpts: Iterable[Excerpt], scope,
limit_bytes)` to `budget(collect: Callable[[], Iterable[Excerpt]], scope, limit_bytes)`. It now makes
up to three passes — tier 1, then tier 2, then tier 3 — each calling `collect()` fresh, admitting only
that pass's tier, and stopping (all passes) the instant an excerpt does not fit. A tier whose
membership is empty (e.g. no `scope`) is skipped without a `collect()` call, which is what keeps a
scope-less caller down to the original single pass. The eviction machinery from the first draft is
removed entirely.

**P1 regression evidence** — before the fix (reproducing the reviewer's repro exactly: 6 tier-3
excerpts before 3 tier-1 excerpts, 2000 bytes each, limit 10 000):
```
admitted: ['other0.md', 'other1.md', 'other2.md', 'other3.md', 'other4.md']
zero changed-file excerpts admitted
```
After the fix, `tests/test_t005_budget.py::test_changed_files_are_admitted_first_even_after_a_long_tier_3_prefix`
pins the corrected behavior:
```
$ PYTHONPATH=src .venv/bin/python -m pytest tests/test_t005_budget.py::test_changed_files_are_admitted_first_even_after_a_long_tier_3_prefix -q
.                                                                        [100%]
1 passed in 0.03s
```

**P2 fix**: `run_dimension` now calls `resolve_scope(scope, context.repo_path, context)` (T003) and
passes the resulting `Scope` to `budget()`. `project`/`worktree` need no extra arguments and resolve
for real; `changes`/`task` need `ref`/`task_id` this function's signature has no way to accept, so
those two kinds still fall back to `scope=None` for tiering purposes — a documented limitation, not a
regression, and `run_dimension`'s public signature is unchanged per the resolution's constraint.

**P2 live evidence** — a `worktree` scope on a real git repo with one untracked (changed) file and one
unrelated file, both offered by `collect` in the "wrong" order, under a budget too tight for both:
```
$ PYTHONPATH=src .venv/bin/python -c "... run_dimension(descriptor, d, scope='worktree', budget_bytes=60) ..."
['changed.md']
True 1 TruncationRecord(truncated=True, omitted_count=1)
```
`changed.md` (the real, git-detected change) is admitted; `irrelevant.md` is the one truncated —
confirming tier 1 fires end to end in production, not only inside `budget.py`'s own unit tests.

**Full suite after both fixes**:
```
$ date -u +"%Y-%m-%dT%H:%M:%SZ"
2026-08-17T02:51:04Z
$ PYTHONPATH=src .venv/bin/python -m pytest -q
........................................................................ [ 32%]
........................................................................ [ 64%]
........................................................................ [ 96%]
........                                                                 [100%]
224 passed in 0.62s
$ ruff check src tests
All checks passed!
```
