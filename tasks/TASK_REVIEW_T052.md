# TASK_REVIEW — T052: Make requirement-fidelity and blast-radius rate: AC tracing and churn-hotspot evidence

> Sibling of `tasks/TASK_GUIDE_T052.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t052_ac_trace_and_churn.py` — AC extraction from TASK_GUIDE tables + PRD FR ids, whole-word traces (FR-027 ≠ FR-027a), docs never count, code/test via shared classifier, bounded TraceSearch summary (counts, ≤20 untraced per kind, ≤30 quoted trace lines), abstain when budget dropped a listed ref or a cap hit, standalone abstains, fan-in only changed targets + abstain when capped, repo-wide churn top-10% ranking, shallow/<20 commits abstain, colocated test names (`src/app.controller.spec.ts` → test, `dimensions/test_strategy.py` → source, Go/Java/Kotlin/C#/Ruby). 14 guards sabotage-caught. Intentional updates: architecture snapshot keys, T010 read bound, T035 abstain test, T031 two-path classification change. Supervisor re-run `1236 passed, 2 skipped in 53.00s` |
| Verification command run | ☑ pass | Supervisor 2026-09-28 13:33 UTC: pytest `1236 passed, 2 skipped` (exit 0); `ruff check src tests` → `All checks passed!` (exit 0) |
| Negative cases hold | ☑ pass | Standalone mode keeps an honest abstention ('criteria are never inferred'); project-scope hotspot share abstains by design (10% by construction); prefix-style Python `test_*.py` inside src stays source |
| verify | ☑ pass | Supervisor real CLI kitchd `score --scope project </dev/null`: requirement-fidelity rates 0 (code share 0.761, test share 0.631 vs threshold 0.80), 5/7 contributors, overall 65 (was 90 at 4/7 under T035 with requirement-fidelity abstaining). Agent AFTER: this repo requirement-fidelity 0 (0.714/0.750); changes scope blast-radius 100 with hotspot share 0.143 (this repo) / 0.0 (kitchd); pack JSON this repo 129→148 KB (+14.8%), kitchd 137→166 KB (+20.9%) — pass |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Reviewed `dimensions/requirement_fidelity.py`, `dimensions/blast_radius.py`, `core/metrics.py`, `core/models.py`, `core/pipeline.py`, `core/context.py`, `core/registry.py` + `metric_tables.py` (colocated_test_name_patterns), `dimensions/test_strategy.py`, 6 curated TOML. Round 1 P1s fixed: unbounded trace_search/reach pack fields (→ compact summary) and colocated `*.spec.ts` counted as source (→ cited colocated patterns win over source dirs). Rulings: FR ids as criteria, drop backticked identifiers, EVIDENCE_LOCAL + completeness check, ≥20 commits, residual files_read growth (+15%/+21%) accepted as honest reads. Integration note: T037 gate must treat `colocated_test_name_patterns` as optional (Python/PHP/Rust omit it on purpose) — checked at merge. All git via core/git.py. Security inline (Med): bounded walks, no new execution paths |
| Full smoke suite still green (no regression) | ☑ pass | full suite 1236 passed, 2 skipped |
| **UI: Visual regression (diff or verdict pasted)** | ☑ N/A | Pure backend task, no UI |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☑ N/A | Pure backend task, no UI |
| **UI: Responsiveness at target viewports** | ☑ N/A | Pure backend task, no UI |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE**: captured by the implementing agent before any T052 implementation commit (worktree HEAD
7de1e21), real CLI `PYTHONPATH=src python -m easy_verifier.adapters.cli score --repo <repo> <scope> </dev/null`
on this repo (kit-aware) and on the external kit-aware repo kitchd (`<kitchd>` =
/home/hungnguyenhuu/workspace/pets/hungnguyen111/kitchd, read-only). Summary per dimension (rating
[inputs, ✓ met / ✗ unmet]) with the abstention reasons of the two T052 dimensions, clipped at 230 chars:

```text
HEAD 7de1e21
$ easy-verifier score --repo . --scope project   # 2026-09-28T12:53:47Z
exit=0
  architecture           rating 100  [architecture_description_missing=0✓; decision_records_missing=0✓; top_level_import_cycles=0✓]
  blast-radius           abstain all_metrics_abstained
      max_fan_in_changed: no import statement was found in this pack's code-file excerpts, so there is no import graph to measure; that is not the same as a graph without edges. import statements are the registry's import tokens, found textually in excerpt
      changed_files_in_churn_hotspots_share: the share of changed files in the top-10% churn hotspots is not derivable from a read-only evidence pack: the blast-radius pack gathers repository hotspots only at project scope, where every file is in scope so the share is 10% by
  code-quality           rating  50  [max_function_ccn=59✗; lint_config_missing=0✓] abstained-metrics: functions_over_ccn_10_share,format_config_missing
  requirement-fidelity   abstain all_metrics_abstained
      acceptance_criteria_traced_to_code_share: the share of acceptance criteria traced to code is not derivable from a read-only evidence pack: acceptance criteria are not extracted from requirement documents and no criterion-to-code trace exists in standalone mode (no task, t
      acceptance_criteria_traced_to_test_share: the share of acceptance criteria traced to a test is not derivable from a read-only evidence pack: acceptance criteria are not extracted from requirement documents and no criterion-to-test trace exists in standalone mode (no task,
  security               rating  50  [redaction_hits_observed=19✗; sink_hits_observed=0✓] abstained-metrics: lockfile_missing
  solution-fit           abstain no_static_rule
  test-strategy          rating 100  [test_config_and_ci_missing=0✓] abstained-metrics: source_files_without_covering_test_share,assertion_density_per_test
  overall: 75 | 4 of 7
$ easy-verifier score --repo . --scope changes --ref 75650d6   # 2026-09-28T12:53:48Z
exit=0
  architecture           rating 100  [architecture_description_missing=0✓; decision_records_missing=0✓; top_level_import_cycles=0✓]
  blast-radius           rating 100  [max_fan_in_changed=19✓] abstained-metrics: changed_files_in_churn_hotspots_share
      changed_files_in_churn_hotspots_share: the share of changed files in the top-10% churn hotspots is not derivable from a read-only evidence pack: the blast-radius pack gathers repository hotspots only at project scope, where every file is in scope so the share is 10% by
  code-quality           rating  60  [functions_over_ccn_10_share=0.09090909090909091✓; max_function_ccn=20✗; lint_config_missing=0✓; format_config_missing=1✗]
  requirement-fidelity   abstain all_metrics_abstained
      acceptance_criteria_traced_to_code_share: the share of acceptance criteria traced to code is not derivable from a read-only evidence pack: acceptance criteria are not extracted from requirement documents and no criterion-to-code trace exists in standalone mode (no task, t
      acceptance_criteria_traced_to_test_share: the share of acceptance criteria traced to a test is not derivable from a read-only evidence pack: acceptance criteria are not extracted from requirement documents and no criterion-to-test trace exists in standalone mode (no task,
  security               abstain below_coverage_floor
  solution-fit           abstain no_static_rule
  test-strategy          rating  35  [source_files_without_covering_test_share=1.0✗; assertion_density_per_test=2.4285714285714284✓; test_config_and_ci_missing=1✗]
  overall: 74 | 4 of 7
$ easy-verifier score --repo <kitchd> --scope project   # 2026-09-28T12:53:49Z
exit=0
  architecture           rating 100  [architecture_description_missing=0✓; decision_records_missing=0✓] abstained-metrics: top_level_import_cycles
  blast-radius           abstain all_metrics_abstained
      max_fan_in_changed: no import statement was found in this pack's code-file excerpts, so there is no import graph to measure; that is not the same as a graph without edges. import statements are the registry's import tokens, found textually in excerpt
      changed_files_in_churn_hotspots_share: the share of changed files in the top-10% churn hotspots is not derivable from a read-only evidence pack: the blast-radius pack gathers repository hotspots only at project scope, where every file is in scope so the share is 10% by
  code-quality           rating 100  [lint_config_missing=0✓; format_config_missing=0✓] abstained-metrics: functions_over_ccn_10_share,max_function_ccn
  requirement-fidelity   abstain all_metrics_abstained
      acceptance_criteria_traced_to_code_share: the share of acceptance criteria traced to code is not derivable from a read-only evidence pack: acceptance criteria are not extracted from requirement documents and no criterion-to-code trace exists in standalone mode (no task, t
      acceptance_criteria_traced_to_test_share: the share of acceptance criteria traced to a test is not derivable from a read-only evidence pack: acceptance criteria are not extracted from requirement documents and no criterion-to-test trace exists in standalone mode (no task,
  security               rating  60  [redaction_hits_observed=59✗; sink_hits_observed=0✓; lockfile_missing=0✓]
  solution-fit           abstain no_static_rule
  test-strategy          rating 100  [test_config_and_ci_missing=0✓] abstained-metrics: source_files_without_covering_test_share,assertion_density_per_test
  overall: 90 | 4 of 7
$ easy-verifier score --repo <kitchd> --scope changes --ref HEAD~3   # 2026-09-28T12:53:50Z
exit=0
  architecture           rating 100  [architecture_description_missing=0✓; decision_records_missing=0✓; top_level_import_cycles=0✓]
  blast-radius           rating 100  [max_fan_in_changed=6✓] abstained-metrics: changed_files_in_churn_hotspots_share
      changed_files_in_churn_hotspots_share: the share of changed files in the top-10% churn hotspots is not derivable from a read-only evidence pack: the blast-radius pack gathers repository hotspots only at project scope, where every file is in scope so the share is 10% by
  code-quality           rating 100  [functions_over_ccn_10_share=0.0✓; max_function_ccn=9✓; lint_config_missing=0✓; format_config_missing=0✓]
  requirement-fidelity   abstain all_metrics_abstained
      acceptance_criteria_traced_to_code_share: the share of acceptance criteria traced to code is not derivable from a read-only evidence pack: acceptance criteria are not extracted from requirement documents and no criterion-to-code trace exists in standalone mode (no task, t
      acceptance_criteria_traced_to_test_share: the share of acceptance criteria traced to a test is not derivable from a read-only evidence pack: acceptance criteria are not extracted from requirement documents and no criterion-to-test trace exists in standalone mode (no task,
  security               abstain below_coverage_floor
  solution-fit           abstain no_static_rule
  test-strategy          abstain below_coverage_floor
  overall: 100 | 3 of 7
```

Observed: requirement-fidelity is `all_metrics_abstained` in every run (both AC shares not derivable).
Blast-radius is `all_metrics_abstained` at project scope; at `--scope changes` `max_fan_in_changed`
already computes (19 / 6) but as a silent lower bound (the reference sweep cap is not reported as
truncation, T033 carry-forward P2), and `changed_files_in_churn_hotspots_share` abstains in every run.

**AFTER**: implementing agent, after the Stage 4 P1 fixes (compact `trace_search`; colocated test
names win over source roots), same CLI command:

```text
HEAD 31e2f13
$ easy-verifier score --repo . --scope project   # 2026-09-28T13:31:36Z
exit=0
  architecture           rating 100  [architecture_description_missing=0✓; decision_records_missing=0✓; top_level_import_cycles=0✓]
  blast-radius           abstain all_metrics_abstained
      max_fan_in_changed: no import statement was found in this pack's code-file excerpts, so there is no import graph to measure; that is not the same as a graph without edges. import statements are the registry's import tokens, found textually in excerpt
      changed_files_in_churn_hotspots_share: a churn-hotspot share needs the changed files of a narrow scope and a repository-wide ranking; only the blast-radius pack at changes, worktree or task scope gathers them (at project scope every file is in scope, so the share would
  code-quality           rating  50  [max_function_ccn=59✗; lint_config_missing=0✓] abstained-metrics: functions_over_ccn_10_share,format_config_missing
  requirement-fidelity   rating   0  [acceptance_criteria_traced_to_code_share=0.7136752136752137✗; acceptance_criteria_traced_to_test_share=0.75✗]
  security               rating  50  [redaction_hits_observed=19✗; sink_hits_observed=0✓] abstained-metrics: lockfile_missing
  solution-fit           abstain no_static_rule
  test-strategy          rating 100  [test_config_and_ci_missing=0✓] abstained-metrics: source_files_without_covering_test_share,assertion_density_per_test
  overall: 60 | 5 of 7
$ easy-verifier score --repo . --scope changes --ref 75650d6   # 2026-09-28T13:31:38Z
exit=0
  architecture           rating 100  [architecture_description_missing=0✓; decision_records_missing=0✓; top_level_import_cycles=0✓]
  blast-radius           rating 100  [max_fan_in_changed=18✓; changed_files_in_churn_hotspots_share=0.14285714285714285✓]
  code-quality           rating  20  [functions_over_ccn_10_share=0.12280701754385964✗; max_function_ccn=20✗; lint_config_missing=0✓; format_config_missing=1✗]
  requirement-fidelity   rating   0  [acceptance_criteria_traced_to_code_share=0.7136752136752137✗; acceptance_criteria_traced_to_test_share=0.75✗]
  security               abstain below_coverage_floor
  solution-fit           abstain no_static_rule
  test-strategy          rating  35  [source_files_without_covering_test_share=1.0✗; assertion_density_per_test=2.4285714285714284✓; test_config_and_ci_missing=1✗]
  overall: 51 | 5 of 7
$ easy-verifier score --repo <kitchd> --scope project   # 2026-09-28T13:31:39Z
exit=0
  architecture           rating 100  [architecture_description_missing=0✓; decision_records_missing=0✓] abstained-metrics: top_level_import_cycles
  blast-radius           abstain all_metrics_abstained
      max_fan_in_changed: no import statement was found in this pack's code-file excerpts, so there is no import graph to measure; that is not the same as a graph without edges. import statements are the registry's import tokens, found textually in excerpt
      changed_files_in_churn_hotspots_share: a churn-hotspot share needs the changed files of a narrow scope and a repository-wide ranking; only the blast-radius pack at changes, worktree or task scope gathers them (at project scope every file is in scope, so the share would
  code-quality           rating  67  [max_function_ccn=18✗; lint_config_missing=0✓; format_config_missing=0✓] abstained-metrics: functions_over_ccn_10_share
  requirement-fidelity   rating   0  [acceptance_criteria_traced_to_code_share=0.7607843137254902✗; acceptance_criteria_traced_to_test_share=0.6313725490196078✗]
  security               rating  60  [redaction_hits_observed=59✗; sink_hits_observed=0✓; lockfile_missing=0✓]
  solution-fit           abstain no_static_rule
  test-strategy          rating 100  [test_config_and_ci_missing=0✓] abstained-metrics: source_files_without_covering_test_share,assertion_density_per_test
  overall: 65 | 5 of 7
$ easy-verifier score --repo <kitchd> --scope changes --ref HEAD~3   # 2026-09-28T13:31:41Z
exit=0
  architecture           rating 100  [architecture_description_missing=0✓; decision_records_missing=0✓; top_level_import_cycles=0✓]
  blast-radius           rating 100  [max_fan_in_changed=6✓; changed_files_in_churn_hotspots_share=0.0✓]
  code-quality           rating 100  [functions_over_ccn_10_share=0.0✓; max_function_ccn=9✓; lint_config_missing=0✓; format_config_missing=0✓]
  requirement-fidelity   rating   0  [acceptance_criteria_traced_to_code_share=0.7607843137254902✗; acceptance_criteria_traced_to_test_share=0.6313725490196078✗]
  security               abstain below_coverage_floor
  solution-fit           abstain no_static_rule
  test-strategy          abstain below_coverage_floor
  overall: 75 | 4 of 7
```

| repo | scope | run | blast-radius | requirement-fidelity | overall |
|---|---|---|---|---|---|
| easy-verifier-mcp | project | BEFORE | abst [all_metrics_abstained] | abst [all_metrics_abstained] | 75 (4/7) |
| easy-verifier-mcp | project | AFTER | abst (by design at project scope) | 0 [code 0.714 ✗, test 0.750 ✗] | 60 (5/7) |
| easy-verifier-mcp | changes --ref 75650d6 | BEFORE | 100 [fan-in 19 ✓; hotspot abst] | abst | 74 (4/7) |
| easy-verifier-mcp | changes --ref 75650d6 | AFTER | 100 [fan-in 18 ✓; hotspot 0.143 ✓] | 0 [code 0.714 ✗, test 0.750 ✗] | 51 (5/7) |
| kitchd | project | BEFORE | abst | abst | 90 (4/7) |
| kitchd | project | AFTER | abst (by design) | 0 [code 0.761 ✗, test 0.631 ✗] | 65 (5/7) |
| kitchd | changes --ref HEAD~3 | BEFORE | 100 [fan-in 6 ✓; hotspot abst] | abst | 100 (3/7) |
| kitchd | changes --ref HEAD~3 | AFTER | 100 [fan-in 6 ✓; hotspot 0.0 ✓] | 0 [code 0.761 ✗, test 0.631 ✗] | 75 (4/7) |

Colocated-test fix effect: kitchd test share 0.012 → 0.631 (its `*.spec.ts` under `src/` are now tests);
its code share 0.816 → 0.761 (those spec files no longer count as code). This repo unchanged (0.714 / 0.750).
Test-strategy ratings unchanged on both repos (its classification-dependent metrics abstain on these
packs for truncation/coverage, before and after).

Caveat: on this repo the `changes --ref 75650d6` diff includes T052's own commits.

Pack JSON size and wall time (before = `git archive 7de1e21 src`, after = HEAD):

```text
before easy-verifier project  requirement-fidelity  pack_json=129322B excerpt_bytes=118587 excerpts=55 truncated=True files_read=23 wall_ms=175
before easy-verifier project  blast-radius          pack_json=3039B excerpt_bytes=17 excerpts=1 truncated=False files_read=1 wall_ms=163
before easy-verifier project  score wall_ms=1109
before easy-verifier changes  requirement-fidelity  pack_json=131056B excerpt_bytes=118587 excerpts=55 truncated=True files_read=55 wall_ms=171
before easy-verifier changes  blast-radius          pack_json=47795B excerpt_bytes=12261 excerpts=184 truncated=False files_read=103 wall_ms=306
before easy-verifier changes  score wall_ms=800
before kitchd        project  requirement-fidelity  pack_json=137240B excerpt_bytes=119724 excerpts=106 truncated=True files_read=34 wall_ms=347
before kitchd        project  blast-radius          pack_json=3444B excerpt_bytes=56 excerpts=2 truncated=False files_read=6 wall_ms=312
before kitchd        project  score wall_ms=1779
before kitchd        changes  requirement-fidelity  pack_json=138906B excerpt_bytes=119724 excerpts=106 truncated=True files_read=53 wall_ms=231
before kitchd        changes  blast-radius          pack_json=39471B excerpt_bytes=1051 excerpts=22 truncated=False files_read=312 wall_ms=504
before kitchd        changes  score wall_ms=1131
after  easy-verifier project  requirement-fidelity  pack_json=148443B excerpt_bytes=116506 excerpts=154 truncated=True files_read=140 wall_ms=331
after  easy-verifier project  blast-radius          pack_json=3050B excerpt_bytes=17 excerpts=1 truncated=False files_read=1 wall_ms=160
after  easy-verifier project  score wall_ms=1298
after  easy-verifier changes  requirement-fidelity  pack_json=150177B excerpt_bytes=116506 excerpts=154 truncated=True files_read=140 wall_ms=324
after  easy-verifier changes  blast-radius          pack_json=48677B excerpt_bytes=12261 excerpts=184 truncated=False files_read=103 wall_ms=340
after  easy-verifier changes  score wall_ms=980
after  kitchd        project  requirement-fidelity  pack_json=165858B excerpt_bytes=119834 excerpts=183 truncated=True files_read=304 wall_ms=526
after  kitchd        project  blast-radius          pack_json=3455B excerpt_bytes=56 excerpts=2 truncated=False files_read=6 wall_ms=316
after  kitchd        project  score wall_ms=2209
after  kitchd        changes  requirement-fidelity  pack_json=167524B excerpt_bytes=119834 excerpts=183 truncated=True files_read=305 wall_ms=418
after  kitchd        changes  blast-radius          pack_json=39743B excerpt_bytes=1051 excerpts=22 truncated=False files_read=312 wall_ms=520
after  kitchd        changes  score wall_ms=1375
```

requirement-fidelity pack JSON: this repo 129,322 → 148,443 B (+14.8%), kitchd 137,240 → 165,858 B (+20.9%).
Breakdown of the remaining growth: `trace_search` ≈3.5 KB; ~100/77 more (small) excerpts; and `files_read`
(+4.8 KB here, +13.9 KB on kitchd) — the honest list of code files the trace search opened.

Suite: 1236 passed, 2 skipped in 55.96s

Sabotage matrix over `tests/test_t052_ac_trace_and_churn.py`:

```text
S1 trace search treats test files as code: CAUGHT -- 5 failed, 26 passed in 1.36s
     test_three_of_four_criteria_named_in_code_give_a_share_of_075
     test_an_id_in_a_test_file_traces_to_a_test_not_to_code
     test_untraced_list_is_capped_and_counts_the_rest
     test_a_colocated_spec_under_src_traces_to_a_test
     test_quoted_trace_lines_are_capped_and_the_rest_counted
S2 test files classified as code: CAUGHT -- 13 failed, 18 passed in 1.59s
     test_three_of_four_criteria_named_in_code_give_a_share_of_075
     test_an_id_in_a_test_file_traces_to_a_test_not_to_code
     test_untraced_list_is_capped_and_counts_the_rest
     test_shared_classifier_colocated_names[src/app.controller.spec.ts-test]
     test_shared_classifier_colocated_names[apps/api/src/tasks/tasks.service.test.tsx-test]
     test_shared_classifier_colocated_names[internal/store/store_test.go-test]
     test_shared_classifier_colocated_names[src/main/java/com/x/FooTests.java-test]
     test_shared_classifier_colocated_names[src/main/kotlin/FooTest.kt-test]
     test_shared_classifier_colocated_names[src/App/FooTests.cs-test]
     test_shared_classifier_colocated_names[lib/foo_spec.rb-test]
     test_shared_classifier_colocated_names[tests/test_app.py-test]
     test_a_colocated_spec_under_src_traces_to_a_test
     test_quoted_trace_lines_are_capped_and_the_rest_counted
S3 budget-dropped evidence ignored: CAUGHT -- 1 failed, 30 passed in 1.34s
     test_a_budget_that_drops_trace_lines_abstains_instead_of_undercounting
S4 trace search cap ignored: CAUGHT -- 1 failed, 30 passed in 1.33s
     test_a_trace_search_that_hits_its_file_ceiling_abstains
S10 criteria cap ignored: CAUGHT -- 1 failed, 30 passed in 1.31s
     test_more_criteria_than_the_ceiling_abstains
S11 colocated names ignored: CAUGHT -- 8 failed, 23 passed in 1.36s
     test_shared_classifier_colocated_names[src/app.controller.spec.ts-test]
     test_shared_classifier_colocated_names[apps/api/src/tasks/tasks.service.test.tsx-test]
     test_shared_classifier_colocated_names[internal/store/store_test.go-test]
     test_shared_classifier_colocated_names[src/main/java/com/x/FooTests.java-test]
     test_shared_classifier_colocated_names[src/main/kotlin/FooTest.kt-test]
     test_shared_classifier_colocated_names[src/App/FooTests.cs-test]
     test_shared_classifier_colocated_names[lib/foo_spec.rb-test]
     test_a_colocated_spec_under_src_traces_to_a_test
S12 every test name wins over directories: CAUGHT -- 4 failed, 27 passed in 1.35s
     test_shared_classifier_colocated_names[src/main/java/com/x/FooTests.java-test]
     test_shared_classifier_colocated_names[src/easy_verifier/dimensions/test_strategy.py-source]
     test_shared_classifier_colocated_names[src/pkg/test_helpers.py-source]
     test_shared_classifier_colocated_names[lib/test_thing.rb-source]
S13 untraced list not capped: CAUGHT -- 1 failed, 30 passed in 1.31s
     test_untraced_list_is_capped_and_counts_the_rest
S14 quoted trace lines not capped: CAUGHT -- 1 failed, 30 passed in 1.32s
     test_quoted_trace_lines_are_capped_and_the_rest_counted
S5 sweep cap ignored for fan-in: CAUGHT -- 1 failed, 30 passed in 1.27s
     test_a_reference_sweep_that_hits_its_ceiling_abstains_on_fan_in
S6 churn ranked over the scope only: CAUGHT -- 1 failed, 30 passed in 1.32s
     test_share_of_changed_files_in_the_repo_wide_top_10_percent
S7 shallow check disabled: CAUGHT -- 1 failed, 30 passed in 1.31s
     test_a_shallow_clone_abstains_with_a_reason
S8 min-commit guard disabled: CAUGHT -- 1 failed, 30 passed in 1.33s
     test_little_history_abstains_with_a_reason
S9 FR boundary loosened: CAUGHT -- 1 failed, 30 passed in 1.33s
     test_fr_ids_are_criteria_and_trace_keys_with_exact_boundaries
```

**DELTA**: requirement-fidelity now measures how many acceptance criteria and FR ids are traced to code and tests, and blast-radius measures fan-in and repo-wide churn hotspots for changed files, so both dimensions rate instead of always abstaining.
over every criterion, a bounded cited sample in the pack), and blast-radius at changes scope rates the
changed files' share of repository-wide churn hotspots, instead of both always abstaining; colocated
test files (`*.spec.ts`, `*_test.go`, ...) are now tests wherever they sit.

**WITNESS**: Supervisor re-ran suite, ruff and the real CLI on kitchd on 2026-09-28 (13:33 UTC), independent of the implementing agent.