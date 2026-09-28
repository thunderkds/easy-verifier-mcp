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

**AFTER**: [same command, post-change] OR [verbatim excerpt of the new content]

**DELTA**: [one sentence — what a user can now do that they could not before]

**WITNESS**: [who ran it and when — derived from `memory/event-trace/T052.jsonl`, never the
implementing agent alone]
