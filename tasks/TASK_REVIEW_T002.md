# TASK_REVIEW — T002: context.py — kit detection, kit-aware/standalone modes

> Sibling of `tasks/TASK_GUIDE_T002.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t002_context.py` — 35 tests, written before the implementation (first run: `no tests ran`, then a collection ImportError on the not-yet-existing API). Mapping: AC#1 `test_detect_context_returns_the_declared_fields`, `test_found_and_missing_partition_the_artifact_checklist`; AC#2 `test_any_single_kit_artifact_makes_the_repo_kit_aware`, `test_no_kit_artifact_is_standalone`; AC#3 `test_partial_kit_repo_is_kit_aware_with_the_rest_recorded_missing` + `..._not_silently_downgraded_to_standalone` + `..._not_assumed_complete`; AC#4 four tests incl. `test_every_standalone_evidence_pack_carries_the_warning` (structural, via `run_dimension`) and `test_a_hand_built_standalone_context_still_gets_the_warning`; AC#5 six discovery tests; AC#6 six "not on disk" tests; AC#7 `test_detect_context_writes_nothing_to_the_target_repo`; AC#8 `test_an_installed_package_directory_is_the_standalone_fixture`. |
| Verification command run | ☑ pass | `cd <worktree> && PATH=.venv/bin:$PATH python -m pytest tests/test_t002_context.py -q` — the implementing agent's sandbox refuses an env-var-prefixed command, so the agent ran the equivalent `.venv/bin/python -m pytest tests/test_t002_context.py -q`: <br>`...................................  [100%]` <br>`35 passed in 0.07s` <br>The prefixed form must be re-run by the Supervisor from the main checkout at Stage 5 (see `memory/MEMORY.md` merge-gate note). |
| **Stage 4 P2 fixed and regression-tested** | ☑ pass | `_walk` followed symlinked directories out of the repo, advertising in `doc_sources` paths `read_source` can never honor. Fixed by applying `read_source`'s containment test (`resolve().is_relative_to(repo)`) on entry to `_walk`. Reproduced first as a failing test (`AssertionError: 'docs/escape/secret-plan.md' != 'docs/real.md'`), then green. Re-run 2026-08-15T16:52:44+07:00: `enumerated: ('docs/real.md',)`. **Found while fixing**: the same escape one level up — `docs/` *itself* being the symlink — was not covered by the reviewer's suggested fix (a check in the recursive branch); the check is on entry to `_walk` instead, which covers both roots. `docs/ itself an escaping link: ()`. Two regression tests added. |
| Negative cases hold | ☑ pass | Covered as tests, not assertions-by-eye: directory-where-file-expected, file-where-directory-expected, broken symlink, `tasks/` with no guides, empty `memory/`, kit artifact only in a subdirectory, empty repo, file target path, nonexistent target path, `docs/` with 250 files (bounded at `MAX_DOC_SOURCES`). |
| verify | ☑ pass | **Run independently by the Supervisor at Stage 5, 2026-08-16** — the agent could not (`Skill` disabled in its session, so it recorded the row honestly as not-run rather than ticking it). Feature confirmed working in the real CLI, both modes, which is the AC#2/AC#4 behaviour this task exists for — **pass**:<br>`$ python -m easy_verifier.adapters.cli architecture --repo .` → `"mode": "kit-aware"`, `files_read: [PROJECT_SPEC.md, BRAINSTORMING_LOG.md, README.md]`<br>`$ python -m easy_verifier.adapters.cli architecture --repo src/easy_verifier` → `"mode": "standalone"`, `files_read: []`, and the AC#4 advisory is emitted on stderr: `warning [standalone]: Limited context: no kit artifacts … were found in this repository.`<br>Kit detection flips the mode on a real directory and the standalone warning fires — verified, not asserted. |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Reviewed: `core/context.py` (all of it), `core/models.py` (the one appended field), `core/pipeline.py` (the three edited hunks), `adapters/cli.py` (the one added block), `tests/test_t002_context.py`. Skipped: `core/redact.py` (T004), `dimensions/` (untouched; exercised via the smoke run). `run_dimension()`'s signature is unchanged; the only cross-cutting move is `RepoPathError`/`DEFAULT_SCOPE` relocating to `context.py` with a re-export from `pipeline`, checked by grep for both names across `src` and `tests`. |
| Full smoke suite still green (no regression) | ☑ pass | `.venv/bin/python -m pytest -q` → `84 passed in 0.22s` (T001's 49 + T002's 35). `.venv/bin/ruff check src tests` → `All checks passed!`; `ruff format --check src tests` → `12 files already formatted`. |
| **UI: Visual regression (diff or verdict pasted)** | ☑ N/A | Pure-backend task: detection logic in `core/`, no UI component. HTML rendering is T013. |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☑ N/A | Same — no UI surface in this task. |
| **UI: Responsiveness at target viewports** | ☑ N/A | Same — no UI surface in this task. |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE**: captured 2026-08-15T16:45:01+07:00, on `develop` (merged T001), before any T002
implementation commit existed:

```
$ date -Is; .venv/bin/python -m pytest tests/test_t002_context.py -q
2026-08-15T16:45:01+07:00
no tests ran in 0.00s

$ .venv/bin/python -c "<probe: see below>"
detect_context present: False
partial kit repo mode: kit-aware
artifacts_missing recorded: False
standalone warning field: False
```

The probe builds a temp repo containing `PROJECT_SPEC.md` and nothing else. T001's `detect_mode()`
calls it `kit-aware` but has nowhere to record that `PRD.md`, `PROJECT_KANBAN.md`,
`tasks/TASK_GUIDE_*.md` and `memory/` were sought and not found — the partial-kit case (AC #3) is
indistinguishable from a complete kit. There is no `detect_context`, no `artifacts_missing`, and no
standalone limited-context warning anywhere in the object every dimension receives.

**AFTER**: captured 2026-08-15T16:48:23+07:00, same commands, after commit `2b6a00a`. (The
Stage 4 P2 fix landed after this capture and took the suite from 32 to 35 tests; its own
before/after reproduction is in the Evidence table row above.)

```
$ date -Is; .venv/bin/python -m pytest tests/test_t002_context.py -q
2026-08-15T16:48:23+07:00
................................                                         [100%]
32 passed in 0.05s

$ .venv/bin/python -c "<same probe repo: PROJECT_SPEC.md and nothing else>"
mode: kit-aware
found: ('PROJECT_SPEC.md',)
missing: PRD.md -> not found in the target repository
missing: PROJECT_KANBAN.md -> not found in the target repository
missing: tasks/ -> not found in the target repository
missing: tasks/TASK_GUIDE_*.md -> no tasks/ directory in the target repository
missing: memory/ -> not found in the target repository
standalone warning: Limited context: no kit artifacts (PROJECT_SPEC.md, PRD.md,  ...
```

And end-to-end through the CLI, on a standalone directory (`src/easy_verifier`):

```
$ .venv/bin/python -m easy_verifier.adapters.cli architecture --repo src/easy_verifier
warning [standalone]: Limited context: no kit artifacts (PROJECT_SPEC.md, PRD.md,
PROJECT_KANBAN.md, tasks/TASK_GUIDE_*.md, memory/) were found in this repository. There is
no declared ground truth to check against, so findings rest only on documents discovered in
the repo and, where the documents are silent, on the code itself.
{
  "dimension": "architecture",
  "mode": "standalone",
  ...
```

**DELTA**: A caller can now tell a partial kit repo from a complete one — the five artifacts
that were sought and not found are named, with a reason each, instead of being invisible behind a
bare `kit-aware` — and any standalone run carries the limited-context warning in the pack itself,
so no tool response or report can omit it.

**WITNESS**: [who ran it and when — derived from `memory/event-trace/Txxx.jsonl`, never the
implementing agent alone]
