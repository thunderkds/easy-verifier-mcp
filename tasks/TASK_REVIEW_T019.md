# TASK_REVIEW — T019: `core/metrics.py` — measured facts computed over the evidence pack

> Sibling of `tasks/TASK_GUIDE_T019.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_metrics.py` — 29 new tests, written in this task. AC map: #1 `test_compute_metrics_returns_metrics_with_name_kind_and_citations`; #2 `test_metrics_module_imports_nothing_that_reads_the_filesystem` (+ `test_the_no_io_assertion_can_fail`); #3 `test_all_four_families_ship`; #4 `test_whole_set_abstains_and_evidence_local_computes_under_truncation`, `test_every_declared_whole_set_metric_abstains_on_truncation`, `test_truncation_is_believed_from_either_field`, `test_omitted_count_is_never_phrased_as_exact`; #5 same parametrized pair; #6 `test_abstention_is_not_a_number_and_cannot_be_used_as_one`, `test_consumer_reaching_for_a_number_is_stopped_at_the_boundary`; #7 `test_every_non_abstaining_metric_cites_refs_the_pack_actually_read`, `test_a_fabricated_metric_citing_an_unread_path_is_rejected`, `test_a_value_with_no_citation_at_all_is_rejected`; #8 `test_test_strength_measures_ratio_uncovered_modules_and_assertion_density`, `test_a_source_file_with_no_test_is_counted_as_uncovered`, `test_a_cross_project_test_does_not_cover_a_same_named_source`, `test_assertion_density_uses_only_test_file_excerpts`; #9 `test_metrics_are_byte_identical_across_two_processes`, `test_serialization_is_stable_within_a_process_and_reflects_abstentions`; #10 `test_every_value_states_how_to_recompute_it_from_the_evidence`, `test_redaction_metrics_are_recomputable_by_hand`. Edge cases: `test_files_read_duplicated_twice_does_not_double_any_count`, `test_an_empty_but_untruncated_pack_abstains_and_never_raises`, `test_coverage_none_and_zero_do_not_collapse`, `test_tests_but_no_source_and_source_but_no_tests`, `test_a_dimension_that_failed_gets_no_metrics_and_is_named`, `test_a_combined_pack_yields_each_metric_once_per_surviving_dimension`. |
| Verification command run | ☑ pass | The guide's command adapted for the `.venv`-less worktree (standing MEMORY.md trap: `PATH=.venv/bin:$PATH` there silently falls back to system python). Ran `PYTHONPATH=src <main-checkout>/.venv/bin/python -m pytest tests/test_metrics.py -q`, exit code read directly, not piped:<br>`2026-08-31T09:19:58Z`<br>`.............................  [100%]`<br>`29 passed in 0.25s`<br>`exit=0` |
| Negative cases hold | ☑ pass | Two layers. (a) Explicit negative tests: `test_a_fabricated_metric_citing_an_unread_path_is_rejected` drives `check_citations` with a metric citing `src/never_read.py` and asserts `MetricCitationError`, then re-drives the *same guard* with an honest citation and asserts it passes — so the guard is not merely rejecting everything. `test_the_no_io_assertion_can_fail` runs the AST check against a module that really does `Path(...).read_text()`. (b) **Mutation sabotage of the implementation** — eight targeted mutations, each re-running the suite; every one turned at least one test red:<br>`M1 whole_set truncation gate -> if False:` → 8 failed, 21 passed<br>`M2 _dedup removed` → 1 failed (`test_files_read_duplicated_twice_does_not_double_any_count`)<br>`M3 project-boundary check removed` → 1 failed (`test_a_cross_project_test_does_not_cover_a_same_named_source`)<br>`M4 citation guard neutered` → 1 failed (`test_a_fabricated_metric_citing_an_unread_path_is_rejected`)<br>`M5 coverage_score None collapsed to 0.0` → 1 failed (`test_coverage_none_and_zero_do_not_collapse`)<br>`M6 empty-pack abstention given omitted_lower_bound=0` → 1 failed (`test_an_empty_but_untruncated_pack_abstains_and_never_raises`)<br>`M7 assertion counting stops filtering to test files` → 1 failed (`test_assertion_density_uses_only_test_file_excerpts`)<br>`M8 truncation read from the flat field only` → 1 failed (`test_truncation_is_believed_from_either_field`)<br>M2 **survived the first round** — the original test compared a symmetric fixture against itself, so dedup could be deleted with no observable change. It was rewritten with an asymmetric fixture and absolute expected values (0.5, 2/3, 1) and now fails under M2. That is the exact green-test-that-cannot-fail this project has shipped five times, caught before commit. |
| verify | ☐ pass / ☐ fail / ☑ N/A | Not run by the implementing agent: `verify` is user-invocation-only (MEMORY.md). Deferred to Stage 5 — pass. Note the entry point is unreachable from any adapter by design (T022 owns the wiring), so a Stage 5 `verify` of T019 is a library-level exercise of `compute_metrics`, not a CLI run. |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Reviewed: `src/easy_verifier/core/metrics.py` (new, the entire change) and `tests/test_metrics.py` (new). Blast radius is **zero existing modules** — nothing in the repo imports `core.metrics`, and this task adds no import to any existing file (`git show --stat` lists only the two new files plus this review). `dimensions/*.py`, `core/pipeline.py` and `core/models.py` were read but **not modified**, as the guide's Must-Not-Touch table requires. Skipped: the rest of the repo, because no call site changed. |
| Full smoke suite still green (no regression) | ☑ pass | `PYTHONPATH=src <main-checkout>/.venv/bin/python -m pytest -q` → `438 passed in 6.22s`, exit code `0` read directly. Baseline on `develop` was 409 tests; 409 + 29 = 438, so every pre-existing test still runs and passes. `ruff format --check` clean; `ruff check src tests` → `All checks passed!`, exit `0`. |
| **UI: Visual regression (diff or verdict pasted)** | ☑ N/A | Pure-backend task: one library module and its unit tests. No UI component, no rendered output. |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☑ N/A | As above — nothing is rendered. |
| **UI: Responsiveness at target viewports** | ☑ N/A | As above — nothing is rendered. |

---

## Self-review (Stage 4 prep, run by the implementing agent)

**`code-review` skill**: the `Skill` tool is **disabled in this session** (`Error: No such tool
available: Skill`), for subagents as well. A manual structured review of the full diff was performed
instead, with P0–P3 severities; this substitution is recorded here rather than silently omitted.

**`security-review`: N/A.** This task adds **no filesystem, subprocess or network primitive**. The
module's entire import set is `__future__`, `json`, `re`, `collections.abc`, `dataclasses`,
`pathlib.PurePosixPath` and `.models` — asserted as a **whitelist** by
`test_metrics_module_imports_nothing_that_reads_the_filesystem`, which also walks the AST for `open`,
any `read_*` attribute call, and `read_text`/`write_text`. Risk Level is Low per the guide. Two
adjacent security properties were checked anyway and hold: (a) no secret material can be introduced
here, because metrics never see raw file bytes — only the pack, whose excerpts were already redacted
at the evidence layer, and `RedactionHit` carries no value field; the redaction metrics read only
`len(hits)` and `hit.path`, never a fingerprint or value. (b) No test fixture in
`tests/test_metrics.py` contains a credential-shaped string; the one `RedactionHit` fixture uses a
plainly synthetic 12-hex fingerprint `0123456789ab` and a `detector` label, with no vendor prefix —
so GitHub push protection has nothing to match on.

**Findings (self-review), all resolved before the final commit:**

| Sev | Finding | Resolution |
|-----|---------|-----------|
| P2 | `_PackView.test_excerpts` typed `tuple[object, ...]` and `_excerpt_lines(excerpt)` untyped — the two places that touch `Excerpt` fields had no type to check them against. | Imported `Excerpt` from `.models` and typed both; `MetricSet.__iter__` typed `Iterator[Metric]`. |
| P2 | `allowed_refs` was a one-line public wrapper delegating to an identical private `_allowed_refs` — an abstraction with no second implementation behind it. | Collapsed into one public function (Simplicity First). |
| P2 | The dedup test could not fail (see the mutation table, M2). | Fixture made asymmetric and pinned to absolute values. |
| P3 | `check_citations(metrics[-len(METRIC_DEFINITIONS):], ...)` validates the just-appended slice by arithmetic on the shared list. | Left as is: `METRIC_DEFINITIONS` is a module-level constant and the loop appends exactly that many per dimension, so the slice cannot mis-align. Noted for the reviewer. |
| P3 | `redacted_file_share` counts only redaction hits whose `path` is in `files_read`; a hit recorded on an excerpt the byte budget later rejected is excluded from the numerator. | Correct behaviour — numerator and denominator must range over the same set — and the metric is `whole_set`, so on any truncated pack it abstains outright rather than reporting the partial share. |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE** (captured 2026-08-31T09:11:53Z in worktree `easy-verifier-mcp-t019`, before any
implementation commit existed — `git log develop..HEAD` was empty):

```
2026-08-31T09:11:53Z
$ ls src/easy_verifier/core/metrics.py tests/test_metrics.py
ls: cannot access 'src/easy_verifier/core/metrics.py': No such file or directory
ls: cannot access 'tests/test_metrics.py': No such file or directory
$ PYTHONPATH=src python -m pytest tests/test_metrics.py -q
ERROR: file or directory not found: tests/test_metrics.py

no tests ran in 0.00s
exit=4
```

**AFTER** (same command, same worktree, after `36d82c8`):

```
2026-08-31T09:19:58Z
$ PYTHONPATH=src python -m pytest tests/test_metrics.py -q
.............................                                            [100%]
29 passed in 0.25s
exit=0
```

Full suite for regression: `438 passed in 6.22s`, exit `0` (was 409 on `develop`).

**DELTA**: a caller holding an evidence pack can now call
`easy_verifier.core.metrics.compute_metrics(pack)` and get eleven measured, individually cited facts
about the target across four families — where before there was no metrics module at all, and the only
number the engine produced was its own `coverage_score`; every whole-set figure abstains as a typed
state rather than reporting a byte-budget artefact as a fact about the repository.

**WITNESS**: run by the Backend-Implementer in worktree `easy-verifier-mcp-t019` on 2026-08-31
(BEFORE 09:11:53Z, AFTER 09:19:58Z), with `.claude/hooks/.state/active_task` set to `T019` for both;
the Bash calls are attributable via `memory/event-trace/T019.jsonl`. **Stage 5 must re-run this
independently** — a clean Stage 4 is no evidence about Stage 5 unless Stage 4 actually ran the thing,
and here the Supervisor is the independent runner.
