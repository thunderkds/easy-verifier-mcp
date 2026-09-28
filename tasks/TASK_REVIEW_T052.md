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

**AFTER**: implementing agent, same CLI command, after the implementation commits (HEAD shown).

```text
HEAD cbf1a84
$ easy-verifier score --repo . --scope project   # 2026-09-28T13:16:58Z
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
$ easy-verifier score --repo . --scope changes --ref 75650d6   # 2026-09-28T13:16:59Z
exit=0
  architecture           rating 100  [architecture_description_missing=0✓; decision_records_missing=0✓; top_level_import_cycles=0✓]
  blast-radius           rating 100  [max_fan_in_changed=18✓; changed_files_in_churn_hotspots_share=0.14285714285714285✓]
  code-quality           rating  20  [functions_over_ccn_10_share=0.12280701754385964✗; max_function_ccn=20✗; lint_config_missing=0✓; format_config_missing=1✗]
  requirement-fidelity   rating   0  [acceptance_criteria_traced_to_code_share=0.7136752136752137✗; acceptance_criteria_traced_to_test_share=0.75✗]
  security               abstain below_coverage_floor
  solution-fit           abstain no_static_rule
  test-strategy          rating  35  [source_files_without_covering_test_share=1.0✗; assertion_density_per_test=2.4285714285714284✓; test_config_and_ci_missing=1✗]
  overall: 51 | 5 of 7
$ easy-verifier score --repo <kitchd> --scope project   # 2026-09-28T13:17:01Z
exit=0
  architecture           rating 100  [architecture_description_missing=0✓; decision_records_missing=0✓] abstained-metrics: top_level_import_cycles
  blast-radius           abstain all_metrics_abstained
      max_fan_in_changed: no import statement was found in this pack's code-file excerpts, so there is no import graph to measure; that is not the same as a graph without edges. import statements are the registry's import tokens, found textually in excerpt
      changed_files_in_churn_hotspots_share: a churn-hotspot share needs the changed files of a narrow scope and a repository-wide ranking; only the blast-radius pack at changes, worktree or task scope gathers them (at project scope every file is in scope, so the share would
  code-quality           rating 100  [lint_config_missing=0✓; format_config_missing=0✓] abstained-metrics: functions_over_ccn_10_share,max_function_ccn
  requirement-fidelity   rating  50  [acceptance_criteria_traced_to_code_share=0.8156862745098039✓; acceptance_criteria_traced_to_test_share=0.011764705882352941✗]
  security               rating  60  [redaction_hits_observed=59✗; sink_hits_observed=0✓; lockfile_missing=0✓]
  solution-fit           abstain no_static_rule
  test-strategy          rating 100  [test_config_and_ci_missing=0✓] abstained-metrics: source_files_without_covering_test_share,assertion_density_per_test
  overall: 82 | 5 of 7
$ easy-verifier score --repo <kitchd> --scope changes --ref HEAD~3   # 2026-09-28T13:17:03Z
exit=0
  architecture           rating 100  [architecture_description_missing=0✓; decision_records_missing=0✓; top_level_import_cycles=0✓]
  blast-radius           rating 100  [max_fan_in_changed=6✓; changed_files_in_churn_hotspots_share=0.0✓]
  code-quality           rating 100  [functions_over_ccn_10_share=0.0✓; max_function_ccn=9✓; lint_config_missing=0✓; format_config_missing=0✓]
  requirement-fidelity   rating  50  [acceptance_criteria_traced_to_code_share=0.8156862745098039✓; acceptance_criteria_traced_to_test_share=0.011764705882352941✗]
  security               abstain below_coverage_floor
  solution-fit           abstain no_static_rule
  test-strategy          abstain below_coverage_floor
  overall: 88 | 4 of 7
```

Side by side (T052 dimensions and overall):

| repo | scope | run | blast-radius | requirement-fidelity | overall |
|---|---|---|---|---|---|
| easy-verifier-mcp | project | BEFORE | abst [all_metrics_abstained] | abst [all_metrics_abstained] | 75 (4/7) |
| easy-verifier-mcp | project | AFTER | abst [all_metrics_abstained] (by design at project scope) | 0 [code 0.714 ✗, test 0.750 ✗] | 60 (5/7) |
| easy-verifier-mcp | changes --ref 75650d6 | BEFORE | 100 [fan-in 19 ✓; hotspot share abst] | abst | 74 (4/7) |
| easy-verifier-mcp | changes --ref 75650d6 | AFTER | 100 [fan-in 18 ✓; hotspot share 0.143 ✓] | 0 [code 0.714 ✗, test 0.750 ✗] | 51 (5/7) |
| kitchd | project | BEFORE | abst [all_metrics_abstained] | abst [all_metrics_abstained] | 90 (4/7) |
| kitchd | project | AFTER | abst (by design at project scope) | 50 [code 0.816 ✓, test 0.012 ✗] | 82 (5/7) |
| kitchd | changes --ref HEAD~3 | BEFORE | 100 [fan-in 6 ✓; hotspot share abst] | abst | 100 (3/7) |
| kitchd | changes --ref HEAD~3 | AFTER | 100 [fan-in 6 ✓; hotspot share 0.0 ✓] | 50 [code 0.816 ✓, test 0.012 ✗] | 88 (4/7) |

Caveat: on this repo the `changes --ref 75650d6` diff now includes T052's own commits, so its
code-quality/fan-in inputs differ for that reason (fan-in 19→18 is also the new restriction of
fan-in targets to the changed files). kitchd's diff is identical before/after.

Pack size and wall time (before = `git archive 7de1e21 src`, after = HEAD, same machine):

```text
before easy-verifier project  requirement-fidelity  pack_json=129322B excerpt_bytes=118587 excerpts=55 truncated=True files_read=23 wall_ms=182
before easy-verifier project  blast-radius          pack_json=3038B excerpt_bytes=17 excerpts=1 truncated=False files_read=1 wall_ms=161
before easy-verifier project  score wall_ms=1123
before easy-verifier changes  requirement-fidelity  pack_json=131056B excerpt_bytes=118587 excerpts=55 truncated=True files_read=55 wall_ms=174
before easy-verifier changes  blast-radius          pack_json=47791B excerpt_bytes=12261 excerpts=184 truncated=False files_read=103 wall_ms=311
before easy-verifier changes  score wall_ms=831
before kitchd        project  requirement-fidelity  pack_json=137240B excerpt_bytes=119724 excerpts=106 truncated=True files_read=34 wall_ms=352
before kitchd        project  blast-radius          pack_json=3444B excerpt_bytes=56 excerpts=2 truncated=False files_read=6 wall_ms=328
before kitchd        project  score wall_ms=1817
before kitchd        changes  requirement-fidelity  pack_json=138906B excerpt_bytes=119724 excerpts=106 truncated=True files_read=53 wall_ms=237
before kitchd        changes  blast-radius          pack_json=39471B excerpt_bytes=1051 excerpts=22 truncated=False files_read=312 wall_ms=511
before kitchd        changes  score wall_ms=1168
after  easy-verifier project  requirement-fidelity  pack_json=270525B excerpt_bytes=119366 excerpts=593 truncated=True files_read=140 wall_ms=340
after  easy-verifier project  blast-radius          pack_json=3049B excerpt_bytes=17 excerpts=1 truncated=False files_read=1 wall_ms=168
after  easy-verifier project  score wall_ms=1387
after  easy-verifier changes  requirement-fidelity  pack_json=272259B excerpt_bytes=119366 excerpts=593 truncated=True files_read=140 wall_ms=341
after  easy-verifier changes  blast-radius          pack_json=48673B excerpt_bytes=12261 excerpts=184 truncated=False files_read=103 wall_ms=343
after  easy-verifier changes  score wall_ms=1123
after  kitchd        project  requirement-fidelity  pack_json=220460B excerpt_bytes=119839 excerpts=367 truncated=True files_read=304 wall_ms=542
after  kitchd        project  blast-radius          pack_json=3455B excerpt_bytes=56 excerpts=2 truncated=False files_read=6 wall_ms=329
after  kitchd        project  score wall_ms=2133
after  kitchd        changes  requirement-fidelity  pack_json=222126B excerpt_bytes=119839 excerpts=367 truncated=True files_read=305 wall_ms=453
after  kitchd        changes  blast-radius          pack_json=39743B excerpt_bytes=1051 excerpts=22 truncated=False files_read=312 wall_ms=552
after  kitchd        changes  score wall_ms=1403
```

Sabotage matrix over `tests/test_t052_ac_trace_and_churn.py` (each guard forced open, file restored):

```text
S1 metric counts any excerpt as a trace (docs count): CAUGHT -- 7 failed, 8 passed in 1.16s
     test_three_of_four_criteria_named_in_code_give_a_share_of_075
     test_docs_only_mention_is_no_trace_but_the_same_id_in_code_is
     test_an_id_in_a_test_file_traces_to_a_test_not_to_code
     test_fr_ids_are_criteria_and_trace_keys_with_exact_boundaries
     test_a_budget_that_drops_trace_lines_abstains_instead_of_undercounting
     test_a_trace_search_that_hits_its_file_ceiling_abstains
     test_more_criteria_than_the_ceiling_abstains
S2 test files classified as code: CAUGHT -- 3 failed, 12 passed in 1.16s
     test_three_of_four_criteria_named_in_code_give_a_share_of_075
     test_an_id_in_a_test_file_traces_to_a_test_not_to_code
     test_a_budget_that_drops_trace_lines_abstains_instead_of_undercounting
S3 budget-dropped evidence ignored: CAUGHT -- 1 failed, 14 passed in 1.18s
     test_a_budget_that_drops_trace_lines_abstains_instead_of_undercounting
S4 trace search cap ignored: CAUGHT -- 1 failed, 14 passed in 1.12s
     test_a_trace_search_that_hits_its_file_ceiling_abstains
S10 criteria cap ignored: CAUGHT -- 1 failed, 14 passed in 1.15s
     test_more_criteria_than_the_ceiling_abstains
S5 sweep cap ignored for fan-in: CAUGHT -- 1 failed, 14 passed in 1.08s
     test_a_reference_sweep_that_hits_its_ceiling_abstains_on_fan_in
S6 churn ranked over the scope only: CAUGHT -- 1 failed, 14 passed in 1.07s
     test_share_of_changed_files_in_the_repo_wide_top_10_percent
S7 shallow check disabled: CAUGHT -- 1 failed, 14 passed in 1.08s
     test_a_shallow_clone_abstains_with_a_reason
S8 min-commit guard disabled: CAUGHT -- 1 failed, 14 passed in 1.08s
     test_little_history_abstains_with_a_reason
S9 FR boundary loosened: CAUGHT -- 1 failed, 14 passed in 1.08s
     test_fr_ids_are_criteria_and_trace_keys_with_exact_boundaries
```

**DELTA**: In kit-aware mode requirement-fidelity now rates from cited acceptance-criterion lines and
the code/test lines that name them, and blast-radius at changes scope rates the changed files'
share of the repository-wide churn hotspots (plus a fan-in that abstains when its sweep was capped),
instead of both dimensions always abstaining.

**WITNESS**: [who ran it and when — derived from `memory/event-trace/T052.jsonl`, never the
implementing agent alone]
