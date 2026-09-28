# TASK_REVIEW — T035: Per-dimension cited rules for the existing 7 dimensions

> Sibling of `tasks/TASK_GUIDE_T035.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t035_cited_rules.py` (rule table = approved table, weights sum 100, every input carries metric/threshold citation + source_tag, solution-fit `no_static_rule` at any coverage, role-missing metrics 0/1/abstain-on-truncation, CCN 30% earns 0 of 40, README table doc-truth, ASVS URL = vendored, hostile label/URL escaped) + T013 oracle extended (`test_full_score_panel_with_cited_links_loads_nothing`, scanner self-test). 8 sabotage pairs S1–S8 each caught. Supervisor re-run `1127 passed, 2 skipped in 37.54s` |
| Verification command run | ☑ pass | Supervisor 2026-09-28 07:42 UTC: pytest `1127 passed, 2 skipped` (exit 0); `ruff check src tests` → `All checks passed!` (exit 0) |
| Negative cases hold | ☑ pass | solution-fit abstains `no_static_rule` at coverage 1.0/0.5/0.0; unfilled role on truncated pack abstains (not 1); report: http anchor, anchor without rel=noreferrer, img/link/iframe/src/url()/@import all still flagged by the self-containment scanner; hostile citation label and URL escaped |
| verify | ☑ pass | Real CLI 07:42 UTC `score --repo . --scope project </dev/null` on this repo: architecture 100, blast-radius all_metrics_abstained, code-quality 50, requirement-fidelity all_metrics_abstained, security 50, solution-fit no_static_rule, test-strategy 100, overall 75 (4/7) — matches agent AFTER table. HITL: user signed off 2026-09-28 ('Merge + fix tasks'): 4-repo before/after easy-verifier 60→75, kitchd 51→90, bryony 63→78, ai-training 61→70 — pass |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Reviewed `core/judge.py` (per-dimension RATING_RULES, Citation, RatingRule/RatingInput citation fields, `_validate_declared_data`, `no_static_rule`), `core/metrics.py` (role-missing metrics, coverage share, not-derivable abstentions), `core/report.py` (escaped citation anchors), README rating section, updated tests, T013 oracle. Code review P0 0, P1 0. Supervisor rulings: `*_missing` ≤0 metrics (avoid permanent borderline), ASVS 5.0.0 V13.3.1/V15.1.2, Martin archive link, failure precedence over no_static_rule, keep https+noreferrer anchors with a precise resource-load oracle. User-accepted follow-ups: T051 (redaction false positives — sha256 hashes in lock files, long test identifiers, git-ignored `.claude/` scanned; 40/100 of security weight), T052 (AC tracing for requirement-fidelity + churn evidence for blast-radius; both always abstain now so overall averages 4/7). Citation URLs not fetched. Security inline (Med): output escaped; no new I/O |
| Full smoke suite still green (no regression) | ☑ pass | full suite 1127 passed, 2 skipped |
| **UI: Visual regression (diff or verdict pasted)** | ☑ N/A | Pure backend task, no UI |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☑ N/A | Pure backend task, no UI |
| **UI: Responsiveness at target viewports** | ☑ N/A | Pure backend task, no UI |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE**: captured before any T035 implementation commit (HEAD 685f07a), real CLI
`PYTHONPATH=src python -m easy_verifier.adapters.cli score --scope project --repo <repo> </dev/null`,
per-dimension rating/abstention + overall (old 11 shared rules applied to every dimension):

```text
### easy-verifier-mcp (/home/hungnguyenhuu/workspace/pets/hungnguyen111/easy-verifier-mcp-T035) -- 2026-09-28T07:17:16Z exit=0
  architecture           rating 65
  blast-radius           rating 64
  code-quality           rating 50
  requirement-fidelity   rating 50
  security               rating 50
  solution-fit           rating 82
  test-strategy          rating 60
  overall: {'kind': 'overall_rating', 'value': 60}
### kitchd (/home/hungnguyenhuu/workspace/pets/hungnguyen111/kitchd) -- 2026-09-28T07:17:17Z exit=0
  architecture           rating 45
  blast-radius           rating 64
  code-quality           rating 41
  requirement-fidelity   rating 50
  security               rating 50
  solution-fit           rating 45
  test-strategy          rating 60
  overall: {'kind': 'overall_rating', 'value': 51}
### bryony (/home/hungnguyenhuu/workspace/project/bryony/bryony) -- 2026-09-28T07:17:19Z exit=0
  architecture           rating 82
  blast-radius           rating 64
  code-quality           rating 82
  requirement-fidelity   abstain (achieved coverage is below the declared floor)
  security               rating 29
  solution-fit           abstain (achieved coverage is below the declared floor)
  test-strategy          rating 57
  overall: {'kind': 'overall_rating', 'value': 63}
### ai-training (/home/hungnguyenhuu/workspace/training/hoang.hoan/ai-training) -- 2026-09-28T07:17:26Z exit=0
  architecture           rating 65
  blast-radius           rating 50
  code-quality           rating 50
  requirement-fidelity   rating 82
  security               rating 60
  solution-fit           abstain (achieved coverage is below the declared floor)
  test-strategy          rating 60
  overall: {'kind': 'overall_rating', 'value': 61}
```

**AFTER**: same CLI command, post-change (commit 0244c94; scoring code unchanged by later commits
783865c, which touched report rendering/tests/README only). Per dimension: rating [inputs, ✓ met /
✗ unmet] and metrics that abstained:

```text
### easy-verifier-mcp (/home/hungnguyenhuu/workspace/pets/hungnguyen111/easy-verifier-mcp-T035) -- 2026-09-28T07:33:01Z exit=0
  architecture           rating 100  [architecture_description_missing=0✓; decision_records_missing=0✓; top_level_import_cycles=0✓]
  blast-radius           abstain all_metrics_abstained
  code-quality           rating  50  [max_function_ccn=59✗; lint_config_missing=0✓] abstained-metrics: functions_over_ccn_10_share,format_config_missing
  requirement-fidelity   abstain all_metrics_abstained
  security               rating  50  [redaction_hits_observed=22✗; sink_hits_observed=0✓] abstained-metrics: lockfile_missing
  solution-fit           abstain no_static_rule
  test-strategy          rating 100  [test_config_and_ci_missing=0✓] abstained-metrics: source_files_without_covering_test_share,assertion_density_per_test
  overall: 75 | 4 of 7 dimensions contributed (4 rule-rated, 0 blended, 0 agent-rated); ratings average co
### kitchd (/home/hungnguyenhuu/workspace/pets/hungnguyen111/kitchd) -- 2026-09-28T07:33:02Z exit=0
  architecture           rating 100  [architecture_description_missing=0✓; decision_records_missing=0✓] abstained-metrics: top_level_import_cycles
  blast-radius           abstain all_metrics_abstained
  code-quality           rating 100  [lint_config_missing=0✓; format_config_missing=0✓] abstained-metrics: functions_over_ccn_10_share,max_function_ccn
  requirement-fidelity   abstain all_metrics_abstained
  security               rating  60  [redaction_hits_observed=222✗; sink_hits_observed=0✓; lockfile_missing=0✓]
  solution-fit           abstain no_static_rule
  test-strategy          rating 100  [test_config_and_ci_missing=0✓] abstained-metrics: source_files_without_covering_test_share,assertion_density_per_test
  overall: 90 | 4 of 7 dimensions contributed (4 rule-rated, 0 blended, 0 agent-rated); ratings average co
### bryony (/home/hungnguyenhuu/workspace/project/bryony/bryony) -- 2026-09-28T07:33:04Z exit=0
  architecture           rating  50  [architecture_description_missing=0✓; decision_records_missing=1✗] abstained-metrics: top_level_import_cycles
  blast-radius           abstain all_metrics_abstained
  code-quality           rating 100  [lint_config_missing=0✓; format_config_missing=0✓] abstained-metrics: functions_over_ccn_10_share,max_function_ccn
  requirement-fidelity   abstain below_coverage_floor (cov 0.0 < 0.5)
  security               rating  60  [redaction_hits_observed=132✗; sink_hits_observed=0✓; lockfile_missing=0✓]
  solution-fit           abstain no_static_rule
  test-strategy          rating 100  [assertion_density_per_test=7.764✓; test_config_and_ci_missing=0✓] abstained-metrics: source_files_without_covering_test_share
  overall: 78 | 4 of 7 dimensions contributed (4 rule-rated, 0 blended, 0 agent-rated); ratings average co
### ai-training (/home/hungnguyenhuu/workspace/training/hoang.hoan/ai-training) -- 2026-09-28T07:33:11Z exit=0
  architecture           rating  70  [architecture_description_missing=0✓; decision_records_missing=1✗; top_level_import_cycles=0✓]
  blast-radius           abstain all_metrics_abstained
  code-quality           rating  50  [max_function_ccn=32✗; lint_config_missing=0✓] abstained-metrics: functions_over_ccn_10_share,format_config_missing
  requirement-fidelity   abstain all_metrics_abstained
  security               rating  60  [redaction_hits_observed=271✗; sink_hits_observed=0✓; lockfile_missing=0✓]
  solution-fit           abstain no_static_rule
  test-strategy          rating 100  [test_config_and_ci_missing=0✓] abstained-metrics: source_files_without_covering_test_share,assertion_density_per_test
  overall: 70 | 4 of 7 dimensions contributed (4 rule-rated, 0 blended, 0 agent-rated); ratings average co
```

Side by side (overall and per-dimension; "abst" = abstained, reason in brackets):

| repo | run | architecture | blast-radius | code-quality | requirement-fidelity | security | solution-fit | test-strategy | overall |
|---|---|---|---|---|---|---|---|---|---|
| easy-verifier-mcp | BEFORE | 65 | 64 | 50 | 50 | 50 | 82 | 60 | 60 (7/7) |
| easy-verifier-mcp | AFTER | 100 | abst [all_metrics_abstained] | 50 | abst [all_metrics_abstained] | 50 | abst [no_static_rule] | 100 | 75 (4/7) |
| kitchd | BEFORE | 45 | 64 | 41 | 50 | 50 | 45 | 60 | 51 (7/7) |
| kitchd | AFTER | 100 | abst [all_metrics_abstained] | 100 | abst [all_metrics_abstained] | 60 | abst [no_static_rule] | 100 | 90 (4/7) |
| bryony | BEFORE | 82 | 64 | 82 | abst [below_coverage_floor] | 29 | abst [below_coverage_floor] | 57 | 63 (5/7) |
| bryony | AFTER | 50 | abst [all_metrics_abstained] | 100 | abst [below_coverage_floor] | 60 | abst [no_static_rule] | 100 | 78 (4/7) |
| ai-training | BEFORE | 65 | 50 | 50 | 82 | 60 | abst [below_coverage_floor] | 60 | 61 (6/7) |
| ai-training | AFTER | 70 | abst [all_metrics_abstained] | 50 | abst [all_metrics_abstained] | 60 | abst [no_static_rule] | 100 | 70 (4/7) |

HITL: acceptability of these numbers is for the Supervisor/user to sign off; the implementing agent
does not judge it.

**DELTA**: Each dimension is now rated by its own standard-backed rules, and every rule input in `score` output and the report shows its metric citation, threshold citation and `curated` source tag.

**WITNESS**: Supervisor re-ran suite, ruff and the real CLI on 2026-09-28 (07:42 UTC); user signed off the 4-repo before/after table the same day.