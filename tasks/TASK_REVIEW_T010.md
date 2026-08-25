# TASK_REVIEW — T010: blast-radius dimension (bespoke)

> Sibling of `tasks/TASK_GUIDE_T010.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t010_blast_radius.py` — 19 tests, one per AC plus the Stage 4 regression. AC #2 `test_referencing_files_are_surfaced_with_the_citing_line`, AC #3 `test_a_file_nothing_references_yields_an_explicit_zero`, AC #5 `test_the_pack_states_that_reference_discovery_is_textual`, AC #6 `test_no_risk_score_severity_or_verdict_anywhere_in_the_module`, AC #7 `test_project_scope_reports_repo_wide_hotspots`, AC #8 `test_the_last_relevance_pass_is_abandoned_and_reads_stay_bounded` + `test_collect_returns_a_generator_rather_than_a_materialised_list`, AC #9 `test_standalone_mode_carries_the_limited_context_warning`, AC #10 `test_only_read_only_git_subcommands_are_ever_invoked` + `test_an_executable_in_the_target_repo_is_never_run`. Stage 4 P1 pinned by `test_a_cap_truncated_sweep_never_reports_a_repository_wide_zero`, **confirmed red on `f8aa94d`** (`AssertionError: assert 'ceiling' in 'examined: no referencing line was found in the 400 repository file(s) scanned for the 1 scope file(s)'`) |
| Verification command run | ☑ pass | `pytest tests/test_t010_blast_radius.py -q` → `19 passed in 1.12s`. Full suite `333 passed in 2.57s`, `ruff check src tests` → `All checks passed!`. Run with the main checkout's interpreter (agent worktrees have no `.venv`), pytest exit code read directly, not piped through `tail` |
| Negative cases hold | ☑ pass | Driven at the real CLI: `--scope changes` with no `--ref` → `files_read: 0`, coverage 0.0, explicit unresolved-scope warning (**T008's Stage 5 widening defect does not recur**); bogus `--ref` → `examined: the resolved changes scope named no files`; `--budget-bytes 150` → `truncated: true`, `omitted: 1`, reads bounded at 34 files and the references source correctly **absent** from the miss list because it produced evidence (the T007/T008/T009 contradiction does not appear); non-git directory → all three history sources honestly refused; `--budget-bytes 0` → pre-existing uncaught `BudgetError` traceback, already on the open follow-up list, not charged to T010 |
| verify | ☑ pass | `verify` skill run by the Supervisor at the real CLI surface (`python -m easy_verifier.adapters.cli blast-radius`) — 10 steps, 6 of them probes — **pass**. The Stage 4 P1 fix was re-confirmed at the surface on a purpose-built repo (scope file `aaa/target.py`, 500 fillers, sole importer at `zzz/consumer.py` beyond the 400-file ceiling): the pack now warns `The reference sweep stopped at its ceiling of 400 repository file(s)…` and the miss reason says `…and the sweep stopped at its ceiling of 400 file(s) — files beyond it were never opened`. **First task in this project to clear Stage 5 on the first attempt** (T008 and T009 both failed it) |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Reviewed: `dimensions/blast_radius.py` (620 lines), `dimensions/__init__.py`, `tests/test_t010_blast_radius.py`, `tests/test_t001_pipeline.py` (registry assertion). Read but not reviewed, as consumed contracts: `core/pipeline.py:_missing_sources`, `core/context.py:read_source`/`iter_code_sources`, `core/scope.py` git helper (convention comparison only). Conditional reviewers activated: security (subprocess surface), performance (repo-wide sweep), adversarial (>50 lines). Skipped: migration (no schema), api (no endpoint change) |
| Full smoke suite still green (no regression) | ☑ pass | `333 passed in 2.57s` post-fix, up from 314 on `develop` (19 new). `ruff check src tests` clean |
| **UI: Visual regression (diff or verdict pasted)** | ☐ N/A | Pure-backend task — the dimension has no UI; its only surface is the CLI adapter, verified above |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☐ N/A | Pure-backend task, as above |
| **UI: Responsiveness at target viewports** | ☐ N/A | Pure-backend task, as above |

### Stage 4 findings

`code-review` run by the Supervisor: **P0 0 / P1 1 (fixed) / P2 3 / P3 2**. `security-review` ☐ N/A
(Low risk) — the subprocess surface was nonetheless reviewed directly: explicit argv, never
`shell=True`, only `log` and `rev-parse` ever invoked, no remote contact, no target code executed
(NFR-007/NFR-012), all three pinned by tests.

**P1 (fixed, `b33ea8b`) — a cap-truncated reference sweep reported a repository-wide zero.** With
the only referencing file sorting past `MAX_SCAN_FILES`, the pack stated `examined: no referencing
line was found in the 400 repository file(s) scanned` and carried **no warning about the ceiling** —
a bounded sweep asserting an unbounded absence, in the one place AC #5 requires honesty (the
dimension may over-report; it may not go silent). Same relevance-blind-cap class as T008's
alphabetical `sorted(scope.files)[:200]` candidate cap. Its own suite could not see it: the
zero-reference test uses a repo small enough that the sweep genuinely exhausts, so the capped path
had **no assertion on its miss reason at all** — the T008 blind spot verbatim.

**Accepted residue, not fixed:**

(a) **A manifest read but declaring nothing is credited in `sources_found`** and counts toward
`coverage_score`, with nothing in the pack saying it declared nothing. On this repo `pyproject.toml`
is "found" at coverage 0.375 while contributing zero excerpts, so the caller cannot distinguish
"read, declared nothing" from "the budget dropped the excerpt". This follows `read_source`'s
documented shared semantics (found = read, may contribute no excerpt) and matches T008's accepted
residue (c) on coverage as a weak signal.

(b) **Reference selection is walk-order-blind.** The ceiling is now honest, but a likelier consumer
is still not preferred over 400 fillers. T008 solved its equivalent with category ranking; doing so
here is a design change and was deliberately left out of a review-stage fix under Scope Locking.

(c) **`files_read` is duplicated 2×** — 800 entries for a 400-file sweep, 70 for 35 unique files on
this repo. Two causes: `budget` invokes `collect` once per tier pass, and the dimension re-opens each
manifest in the reference sweep after the entry-point probe. This is T009's recorded residue, now
visible on a **default** invocation rather than only under `task` scope; **filed against the shared
layer, not charged to T010**.

(d) **`project` scope yields zero citable excerpts unless the repo declares an entry point** — all
hotspot evidence rides in `warnings` text rather than the excerpt list FR-011 asks for, and in a
non-git directory the pack is completely empty (0 excerpts, all 8 sources missing) because
references are excluded as quadratic and hotspots need git. Honest in every case, but there is no
evidence path at all for that combination. This is the guide's own hotspots-as-warning design, so it
is recorded for a decision rather than fixed here.

(e) **A typo'd `--ref` is indistinguishable from "nothing changed"** — both produce a confident empty
pack. `resolve_scope` does not raise for a nonexistent ref; T008 recorded that behaviour as correct,
so this is pre-existing and not T010's.

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE**: captured `2026-08-24T10:32:41Z`, in the T010 worktree, before any implementation
commit existed (`git log develop..HEAD` was empty):

```console
$ date -u +%Y-%m-%dT%H:%M:%SZ
2026-08-24T10:32:41Z

$ PYTHONPATH=src .venv/bin/python -m pytest tests/test_t010_blast_radius.py -q
ERROR: file or directory not found: tests/test_t010_blast_radius.py

no tests ran in 0.00s
pytest exit=4

$ PYTHONPATH=src .venv/bin/python -m easy_verifier.adapters.cli blast-radius --repo . \
    --scope changes --ref HEAD~1..HEAD
usage: easy-verifier [-h] [--repo REPO]
                     [--scope {changes,project,task,worktree}] [--ref REF]
                     [--task-id TASK_ID] [--budget-bytes BUDGET_BYTES]
                     {architecture,code-quality,requirement-fidelity,security,solution-fit,test-strategy}
easy-verifier: error: argument dimension: invalid choice: 'blast-radius' (choose from 'architecture',
'code-quality', 'requirement-fidelity', 'security', 'solution-fit', 'test-strategy')
```

> Note: the guide's Verification Command reads `--range HEAD~1..HEAD`; the CLI's flag is `--ref`.
> The command above uses the corrected flag, and the guide text has been corrected in this task.

**AFTER**: same commands, `2026-08-24T10:42:04Z`, in the T010 worktree:

```console
$ date -u +%Y-%m-%dT%H:%M:%SZ
2026-08-24T10:42:04Z

$ PYTHONPATH=src .venv/bin/python -m pytest tests/test_t010_blast_radius.py -q
..................                                                       [100%]
18 passed in 1.01s
pytest exit=0

$ PYTHONPATH=src .venv/bin/python -m easy_verifier.adapters.cli blast-radius --repo . \
    --scope changes --ref HEAD~1..HEAD | head -30
warning [kit-aware]: Method: reference evidence in this pack comes from a textual search for
each scope file's path, dotted module path and file stem across the repository's code files. It
is not a resolved import graph — no target code was parsed, imported or run — so a same-named
symbol in an unrelated module is reported (over-reporting) and an aliased or dynamically formed
reference is not (under-reporting). Co-change evidence counts files appearing in the same local
git commits as a scope file: correlation in history, not a dependency.
warning [kit-aware]: Entry points were looked for in these packaging manifests: pyproject.toml,
setup.py, package.json, Cargo.toml, go.mod; by these declaration markers: [project.scripts],
[project.gui-scripts], [project.entry-points, console_scripts, entry_points, [[bin]], "bin",
"exports", "main", module ; and in entry-point-shaped files (__init__.py, __main__.py, main.*,
cli.*, app.*, server.*, routes.*, urls.py, index.*) surfaced by the reference search. Manifests
that are not in the repository are named in sources_missing.
warning [kit-aware]: Files that changed alongside the scope file(s) within the last 200 local
commits (number of commits they shared, not a dependency): PROJECT_KANBAN.md (2),
PROJECT_SPEC.md (1), memory/MEMORY.md (1), memory/NEXT-SESSION.md (1),
tasks/TASK_GUIDE_T001.md (1), … and 5 more. History is not followed across renames, so a file
renamed inside this window contributes only under its current name.
{
  "dimension": "blast-radius",
  "mode": "kit-aware",
  "scope": "changes",
  "files_read": [
    "pyproject.toml",
    ...
```

**DELTA**: a caller can now ask `easy-verifier blast-radius` for a repository's *code-dependency*
reach — which files textually reference the active scope, which files local git history shows
changing alongside them, and which packaging manifests declare downstream entry points — with the
discovery method stated in the pack itself and no risk rating anywhere.

**WITNESS**: Supervisor, 2026-08-25 — Stage 4 `code-review` and Stage 5 `verify` both run in the
main checkout's interpreter against the T010 worktree, independently of the implementing agent. The
AFTER capture above is the implementer's (18 tests, `f8aa94d`); the Supervisor's own post-fix
re-run at the same surface is `19 passed in 1.12s` with the full suite at `333 passed`, plus the
ten-step CLI verification recorded in the `verify` row. The Stage 4 P1 was found by driving the
surface with a repo built to embarrass the implementation (500 fillers, sole importer past the scan
ceiling), never by reading the diff.
