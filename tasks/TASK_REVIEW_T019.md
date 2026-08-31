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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_metrics.py` — **32** new tests, written in this task (29 at first submission + 3 Stage 5 regressions, see the Remediation section below). AC map: #1 `test_compute_metrics_returns_metrics_with_name_kind_and_citations`; #2 `test_metrics_module_imports_nothing_that_reads_the_filesystem` (+ `test_the_no_io_assertion_can_fail`); #3 `test_all_four_families_ship`; #4 `test_whole_set_abstains_and_evidence_local_computes_under_truncation`, `test_every_declared_whole_set_metric_abstains_on_truncation`, `test_truncation_is_believed_from_either_field`, `test_omitted_count_is_never_phrased_as_exact`; #5 same parametrized pair; #6 `test_abstention_is_not_a_number_and_cannot_be_used_as_one`, `test_consumer_reaching_for_a_number_is_stopped_at_the_boundary`; #7 `test_every_non_abstaining_metric_cites_refs_the_pack_actually_read`, `test_a_fabricated_metric_citing_an_unread_path_is_rejected`, `test_a_value_with_no_citation_at_all_is_rejected`; #8 `test_test_strength_measures_ratio_uncovered_modules_and_assertion_density`, `test_a_source_file_with_no_test_is_counted_as_uncovered`, `test_a_cross_project_test_does_not_cover_a_same_named_source`, `test_assertion_density_uses_only_test_file_excerpts`; #9 `test_metrics_are_byte_identical_across_two_processes`, `test_serialization_is_stable_within_a_process_and_reflects_abstentions`; #10 `test_every_value_states_how_to_recompute_it_from_the_evidence`, `test_redaction_metrics_are_recomputable_by_hand`. Edge cases: `test_files_read_duplicated_twice_does_not_double_any_count`, `test_an_empty_but_untruncated_pack_abstains_and_never_raises`, `test_coverage_none_and_zero_do_not_collapse`, `test_tests_but_no_source_and_source_but_no_tests`, `test_a_dimension_that_failed_gets_no_metrics_and_is_named`, `test_a_combined_pack_yields_each_metric_once_per_surviving_dimension`. |
| Verification command run | ☑ pass | The guide's command adapted for the `.venv`-less worktree (standing MEMORY.md trap: `PATH=.venv/bin:$PATH` there silently falls back to system python). Ran `PYTHONPATH=src <main-checkout>/.venv/bin/python -m pytest tests/test_metrics.py -q`, exit code read directly, not piped:<br>`2026-08-31T09:19:58Z`<br>`.............................  [100%]`<br>`29 passed in 0.25s`<br>`exit=0`<br><br>**Re-run after the Stage 5 remediation (`7d4831b`)**: `32 passed`, `exit=0`. |
| Negative cases hold | ☑ pass | Two layers. (a) Explicit negative tests: `test_a_fabricated_metric_citing_an_unread_path_is_rejected` drives `check_citations` with a metric citing `src/never_read.py` and asserts `MetricCitationError`, then re-drives the *same guard* with an honest citation and asserts it passes — so the guard is not merely rejecting everything. `test_the_no_io_assertion_can_fail` runs the AST check against a module that really does `Path(...).read_text()`. (b) **Mutation sabotage of the implementation** — eight targeted mutations, each re-running the suite; every one turned at least one test red:<br>`M1 whole_set truncation gate -> if False:` → 8 failed, 21 passed<br>`M2 _dedup removed` → 1 failed (`test_files_read_duplicated_twice_does_not_double_any_count`)<br>`M3 project-boundary check removed` → 1 failed (`test_a_cross_project_test_does_not_cover_a_same_named_source`)<br>`M4 citation guard neutered` → 1 failed (`test_a_fabricated_metric_citing_an_unread_path_is_rejected`)<br>`M5 coverage_score None collapsed to 0.0` → 1 failed (`test_coverage_none_and_zero_do_not_collapse`)<br>`M6 empty-pack abstention given omitted_lower_bound=0` → 1 failed (`test_an_empty_but_untruncated_pack_abstains_and_never_raises`)<br>`M7 assertion counting stops filtering to test files` → 1 failed (`test_assertion_density_uses_only_test_file_excerpts`)<br>`M8 truncation read from the flat field only` → 1 failed (`test_truncation_is_believed_from_either_field`)<br>M2 **survived the first round** — the original test compared a symmetric fixture against itself, so dedup could be deleted with no observable change. It was rewritten with an asymmetric fixture and absolute expected values (0.5, 2/3, 1) and now fails under M2. That is the exact green-test-that-cannot-fail this project has shipped five times, caught before commit. |
| verify | ☑ pass (after remediation) | **Stage 5 `verify` FAILED the first submission** and found a real defect — see the Remediation section. Fixed in `7d4831b`; the Supervisor's own reproduction now yields `source_file_share = 1/17 = 0.0588` instead of `0.0`, and the two false abstentions are gone. Re-verification by the Supervisor is required before merge; the implementing agent cannot self-certify this row. Originally recorded as: not run by the implementing agent: `verify` is user-invocation-only (MEMORY.md). Deferred to Stage 5 — pass. Note the entry point is unreachable from any adapter by design (T022 owns the wiring), so a Stage 5 `verify` of T019 is a library-level exercise of `compute_metrics`, not a CLI run. |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Reviewed: `src/easy_verifier/core/metrics.py` (new, the entire change) and `tests/test_metrics.py` (new). Blast radius is **zero existing modules** — nothing in the repo imports `core.metrics`, and this task adds no import to any existing file (`git show --stat` lists only the two new files plus this review). `dimensions/*.py`, `core/pipeline.py` and `core/models.py` were read but **not modified**, as the guide's Must-Not-Touch table requires. Skipped: the rest of the repo, because no call site changed. |
| Full smoke suite still green (no regression) | ☑ pass | Post-remediation: `PYTHONPATH=src <main-checkout>/.venv/bin/python -m pytest -q` → **`441 passed in 6.59s`**, exit code `0` read directly. (First submission: `438 passed in 6.22s`, exit `0`.) Baseline on `develop` was 409 tests; 409 + 29 = 438, so every pre-existing test still runs and passes. `ruff format --check` clean; `ruff check src tests` → `All checks passed!`, exit `0`. |
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

## Stage 5 Remediation — `verify` failure and fix

**Verdict on the first submission: FAILED.** The Supervisor drove `compute_metrics` over a **real**
`test-strategy` pack at `project` scope against this repo, rather than over a fixture. Three of
eleven metrics misreported.

**The defect.** `files_read` contains `src/easy_verifier/dimensions/test_strategy.py` — production
source whose basename matches `test_*.py`. `_is_test_file` classified it by name, so on the real
17-file pack:

```
source_file_share                  = 0.0       (truth: 1/17 = 0.0588)
  derivation: 0 source file(s) / 17 deduplicated file(s) read, listed here
test_to_source_ratio               = ABSTAIN
  reason: no source file appears in the evidence, so the ratio has a zero denominator
source_files_without_covering_test = ABSTAIN   (same false reason)
```

The abstention reason was the worse half: *"no source file appears in the evidence"* is a positive
claim **about the evidence**, and it was false — the file was in `files_read`. This is the project's
signature defect class: a value or sentinel whose stated cause is not the real one. It violates
**AC #10** specifically, because a human recomputing by hand from the listed files gets 1/17, not
0/17, and nothing in the derivation disclosed that "source file" was a basename heuristic. T020 is
about to build a rating on these metrics, where a heuristic `0.0` reads as "bad".

**Reproduced red before fixing** (standing instruction 4). Three regression tests were written
first and run against `53dccac`, the unfixed head:

```
FAILED tests/test_metrics.py::test_source_under_a_source_root_is_source_even_when_named_test_something
FAILED tests/test_metrics.py::test_directory_evidence_beats_name_evidence_in_both_directions
FAILED tests/test_metrics.py::test_classification_rule_is_disclosed_wherever_it_decides_the_answer
3 failed, 29 passed in 0.16s
RED exit=1
```

**The fix** (`7d4831b`), two parts, both required by the Supervisor's scope note:

1. *Classification.* `_is_test_file` consults **directory evidence first, deepest segment wins**,
   and falls back to the basename only for a file under neither a source root nor a test root. A new
   `_SOURCE_DIR_SEGMENTS` set (`src`, `lib`, `pkg`, `app`, `cmd`, `internal`, `source`, `sources`)
   supplies the source side. `src/pkg/test_helpers.py` is source; `src/pkg/nested/tests/test_real.py`
   is a test. **No literal path is special-cased.**
2. *Disclosure.* Every derivation and abstention reason that depends on the rule now carries
   `_CLASSIFIED_BY`, stating that source-vs-test came from a path convention and never from reading
   or parsing the file. The zero-denominator abstention now reads *"no file in this pack classifies
   as source"* — true of the classifier — instead of asserting something false about the repository.

**On point 3 (should `source_file_share = 0.0` abstain?) — judgement call, recorded.** It **stays a
value**. Its denominator is every file read, so `0.0` is well defined arithmetic, unlike the
genuinely undefined zero-denominator cases which do abstain. Abstaining would also discard a real
fact — that N files were read and none classified as source. Instead its derivation now says
explicitly, when the numerator is zero: *"none did, so this share is 0.0 by the rule below, not
because the repository has no source"*. If the Supervisor prefers abstention here, it is a
three-line change and I will make it.

**Post-fix values on the real pack** (`test-strategy`, `project` scope, this repo, 17 deduped files,
untruncated):

```
test_to_source_ratio                   whole_set      15.0
source_files_without_covering_test     whole_set      1     (src/easy_verifier/dimensions/test_strategy.py)
assertion_density_per_test             whole_set      2.6296296296296298   (284 assertions / 108 test functions)
assertions_observed                    evidence_local 284
redaction_hits_observed                evidence_local 38
redacted_file_share                    whole_set      0.4117647058823529   (7 of 17 files)
excerpts_observed                      evidence_local 17
declared_source_coverage               whole_set      0.2222222222222222   (2 of 9 declared sources)
evidence_lines_observed                evidence_local 3023
mean_excerpt_lines                     whole_set      177.8235294117647
source_file_share                      whole_set      0.058823529411764705 (1 of 17 -- was 0.0)
```

**Mutation sabotage re-run after the fix** — six mutations, every one red, including the two the
Supervisor named as touching this code:

| Mutation | Result |
|---|---|
| M3 project-boundary check removed (re-run) | 1 failed — `test_a_cross_project_test_does_not_cover_a_same_named_source` |
| M7 test-excerpt filter removed (re-run) | 1 failed — `test_assertion_density_uses_only_test_file_excerpts` |
| M9 directory evidence ignored (**the shipped defect, reintroduced**) | 2 failed — both new classification regressions |
| M10 deepest-wins reversed to shallowest-wins | 1 failed — `test_directory_evidence_beats_name_evidence_in_both_directions` |
| M11 directory evidence only ever answers "source" | 10 failed — the sabotage direction that proves the rule classifies **both** ways |
| M12 disclosure string gutted | 1 failed — `test_classification_rule_is_disclosed_wherever_it_decides_the_answer` |

**Scope held.** `src/easy_verifier/dimensions/test_strategy.py` classifies the same file the same
way and was **not touched**: it is on this task's Must-Not-Touch list, changing it would alter T009's
shipped behaviour and tests, and the Supervisor is filing it as a separate follow-up. The duplicated
classification block between the two modules remains recorded residue (self-review P3), not resolved
here. Nothing else the Supervisor verified was disturbed: `ruff check src tests` clean, the citation
guard, dedup, empty/zero-denominator handling and the truncation gate all still pass, and the full
suite went 438 → 441 with no pre-existing test changed.

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

**AFTER** (same command, same worktree, after the Stage 5 remediation `7d4831b`):

```
$ PYTHONPATH=src python -m pytest tests/test_metrics.py -q
................................                                         [100%]
32 passed in 0.14s
exit=0
```

Full suite for regression: `441 passed in 6.59s`, exit `0` (was 409 on `develop`).

And the observable behaviour change the remediation bought, on the real `test-strategy` pack over
this repo — the same three metrics, before and after `7d4831b`:

```
                                        53dccac      7d4831b
source_file_share                          0.0        0.058823529411764705   (= 1/17)
test_to_source_ratio                   ABSTAIN        15.0
source_files_without_covering_test     ABSTAIN        1
```

**DELTA**: a caller holding an evidence pack can now call
`easy_verifier.core.metrics.compute_metrics(pack)` and get eleven measured, individually cited facts
about the target across four families — where before there was no metrics module at all, and the only
number the engine produced was its own `coverage_score`; every whole-set figure abstains as a typed
state rather than reporting a byte-budget artefact as a fact about the repository.

**WITNESS**: run by the Backend-Implementer in worktree `easy-verifier-mcp-t019` on 2026-08-31
(BEFORE 09:11:53Z, AFTER 09:19:58Z, remediation same day), with
`.claude/hooks/.state/active_task` set to `T019` throughout; the Stage 5 `verify` failure that
prompted `7d4831b` was found **by the Supervisor**, not by the implementing agent —
the Bash calls are attributable via `memory/event-trace/T019.jsonl`. **Stage 5 must re-run this
independently** — a clean Stage 4 is no evidence about Stage 5 unless Stage 4 actually ran the thing,
and here the Supervisor is the independent runner.

---

## Stage 4 Review (Supervisor, independent — 2026-08-31)

`Skill({ skill: "code-review" })` **was run by the Supervisor**, closing the substitution the
implementing agent recorded above (the `Skill` tool was unavailable in its session, not in mine).
Scope per Phase 0: the three new files; blast radius is **zero existing modules** — nothing imports
`core.metrics` yet and no existing file was touched (`git diff --stat develop..HEAD` confirms three
new files, 1612 insertions, 0 deletions).

**Phase 0.5 — entry-point reachability**: `compute_metrics` exists and is exported, but is reachable
from **no adapter**. Normally a P2 finding; here it is **pre-waived by the guide's own Dependencies &
Reachability section**, which declares the gap known and accepted because T022 owns the wiring. This
is materially unlike T013's reachability debt, where no consumer task existed.

**Verdict: P0 0 / P1 0 / P2 2 (both accepted as residue) / P3 1. No safe fixes to apply; no
remediation commit required.** This is the second task in the project to reach Stage 4 with no P1
(after T006), and the first to arrive with its own mutation testing already done.

### Independent verification performed (not taken on the agent's word)

| Claim | How checked | Result |
|---|---|---|
| 3 commits, BEFORE captured first | `git log --oneline develop..HEAD` | Holds — `2197285` (BEFORE) precedes `36d82c8` (implementation) |
| 438 pass, exit 0 | Re-run from the main checkout's interpreter, exit code read directly, never piped | Holds — `438 passed`, `SUITE_EXIT=0` |
| ruff clean | `ruff check src tests` + `ruff format --check` | Holds — both exit 0 |
| Citation guard is wired, not decorative | Grepped every caller — `check_citations` is called by `compute_metrics` per dimension, not only from tests | Holds |
| Truncation gate cannot be forgotten by a metric author | Read `compute_metrics`: the `WHOLE_SET and truncated` branch short-circuits **before** `definition.compute` runs | Holds — structural, matching the docstring's claim |
| Mutation table is accurate | **Re-ran three sabotages independently**: truncation gate → `if False:` = **8 failed**; `_dedup` → identity = **1 failed**; `check_citations` → no-op = **2 failed**. Tree restored, `29 passed` | Holds — counts match the reported table |
| `files_read` 2x duplication does not double any count | Drove a hostile pack with every path repeated; compared all 11 metric outcomes against the single-copy pack | Holds — **no metric differs** |
| Zero denominators / empty pack | Drove src-only, tests-only, and a wholly empty pack | Holds — abstains rather than dividing; **nothing raises**; 11/11 abstain on the empty pack |
| `coverage_score` `None` vs `0.0` do not collapse | Read `_declared_source_coverage` | Holds — `None` abstains with a reason that names the distinction explicitly |
| **No new egress path for secrets (the T013 class)** | Grepped every use of `Excerpt.text`: consumed **only** into integer counts (`_count_test_functions`, `_count_assertions`); no excerpt text, fingerprint or `RedactionHit` value is ever interpolated into `derivation` or `computed_from`, which carry only paths and numbers | Holds — the T013 lesson does **not** recur |
| Duplication was forced, not chosen | Verified `dimensions/test_strategy.py` imports `..core.context`, which imports `pathlib.Path` — so importing its helpers would break AC #2's structural no-I/O test, and extracting a shared module was barred by the guide's Must-Not-Touch table | Holds — the agent's justification is accurate |

### Findings

**P2-1 — ~150 lines of path classification duplicated between `core/metrics.py` and
`dimensions/test_strategy.py`** (confidence 100). `_is_test_file`, `_is_source_file`,
`_correspondence` and the `_project_boundary` monorepo rule are ported verbatim. Drift here is
silent: the two copies can disagree about what counts as a test file, and only one of them feeds the
rating T020 will build. **Accepted for this task, not charged to it** — the guide's scope lock made
the correct fix unreachable, exactly as T009's `_EXCLUDED_DIRS` residue was filed against `scope.py`
rather than against T009. **Follow-up: extract a pure `core/paths.py` that both import**; it needs
its own task and permission to edit `dimensions/*.py`.

**P2-2 — assertion and test-declaration counting is textual and enumerated** (confidence 100), so an
unlisted framework shape is **under**-counted. Accepted: both affected metrics say so in their own
`derivation`, making it a disclosed lower bound rather than a silent guess — which is this project's
required standard (FR-005). Worth revisiting only if T020 gives these two metrics real weight.

**P3-1 — a pack with `truncated=True` and `omitted_count=0` produces "at least 0 item(s) omitted"**
(confidence 100), which is vacuous phrasing. **Unreachable from the real pipeline**: `budget.py` sets
`omitted_count = 1` in the same branch that sets `truncated = True`, so only a hand-built pack can
reach it, and it fails safe (the metric still abstains). Recorded, not fixed.

### Residue carried forward (Supervisor-confirmed, all disclosed by the agent)

- The duplicated path-classification block (P2-1) — needs a follow-up task.
- Unreachable from any adapter — known, accepted, T022 owns it.
- Textual assertion counting under-counts unlisted frameworks (P2-2) — disclosed in `derivation`.
- `compute_metrics` accepts `EvidencePack` **or** `CombinedPack`. The guide's ACs are written against
  `EvidencePack` while its edge cases assume `CombinedPack` slots; the agent supported both and
  **flagged it before building**, per standing instruction 3. Supervisor accepts: it resolves a
  genuine ambiguity in the guide rather than papering over it, and `Metric.dimension` keeps names
  stable for T020.
