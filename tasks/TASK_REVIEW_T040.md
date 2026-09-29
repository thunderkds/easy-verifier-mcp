# TASK_REVIEW — T040: [Short Title]

> Sibling of `tasks/TASK_GUIDE_T040.md`. Everything here is **filled by the reviewer at Stage
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

**BEFORE**:

Fixture (`<scratchpad>/t040-fixture`, one git commit): `src/app/auth.py` (Flask session,
`set_cookie` without flags, `SESSION_COOKIE_SECURE = False`, a bare `# TODO`, a `# FIXME(ABC-123)`,
a `# type: ignore`), `tests/test_auth.py` (a test with no assertion, an `@pytest.mark.skip` test, a
`requests.get` in a unit test), `tsconfig.json` without `strict`, `pyproject.toml` `[tool.mypy]`
without `strict`, `docs/PRD.md`. `summarize.py` prints each dimension's rule inputs with their area,
the computed metric names, and which rule inputs carry each of the six T040 areas.

```text
captured: 2026-09-29T06:05:39Z  worktree HEAD=1473029 (no T040 implementation commit yet)
$ PYTHONPATH=src python -m easy_verifier.adapters.cli score --repo <scratchpad>/t040-fixture --scope project </dev/null > before.json; python summarize.py before.json
score exit=0
architecture: rating_abstention value=None reason=below_coverage_floor
blast-radius: rating_abstention value=None reason=all_metrics_abstained
code-quality: rating value=80 reason=None
   rule functions_over_ccn_10_share [Maintainability, reuse, library judgment, patterns] value=0.0 w=40 passed=True
   rule max_function_ccn [Maintainability, reuse, library judgment, patterns] value=1 w=20 passed=True
   rule lint_config_missing [Type safety & code quality] value=0 w=20 passed=True
   rule format_config_missing [Type safety & code quality] value=1 w=20 passed=False
requirement-fidelity: rating_abstention value=None reason=below_coverage_floor
security: rating value=80 reason=None
   rule redaction_hits_observed [Threat modeling, abuse cases, appsec] value=0 w=40 passed=True
   rule sink_hits_observed [Threat modeling, abuse cases, appsec] value=0 w=40 passed=True
   rule lockfile_missing [Dependencies, vulns, licenses, obsolescence] value=1 w=20 passed=False
solution-fit: rating_abstention value=None reason=no_static_rule
test-strategy: rating value=65 reason=None
   rule source_files_without_covering_test_share [Test strategy, coverage, false confidence, isolation] value=0.0 w=35 passed=True
   rule assertion_density_per_test [Test strategy, coverage, false confidence, isolation] value=0.6666666666666666 w=35 passed=False
   rule test_config_and_ci_missing [Test strategy, coverage, false confidence, isolation] value=0 w=30 passed=True
overall: {'kind': 'overall_rating', 'value': 75}
metric names computed (26): acceptance_criteria_traced_to_code_share, acceptance_criteria_traced_to_test_share, architecture_description_missing, assertion_density_per_test, assertions_observed, changed_files_in_churn_hotspots_share, decision_records_missing, declared_source_coverage, evidence_lines_observed, excerpts_observed, format_config_missing, functions_over_ccn_10_share, lint_config_missing, lockfile_missing, max_fan_in_changed, max_function_ccn, mean_excerpt_lines, redacted_file_share, redaction_hits_observed, sink_hits_observed, source_file_share, source_files_without_covering_test, source_files_without_covering_test_share, test_config_and_ci_missing, test_to_source_ratio, top_level_import_cycles
  metric name containing 'skip': []
  metric name containing 'cookie': []
  metric name containing 'strict': []
  metric name containing 'type_ignore': []
  metric name containing 'todo': []
  metric name containing 'removed': []
  metric name containing 'co_change': []
  metric name containing 'network': []
area 'Backward compatibility & upgrade safety': rated inputs = []
area 'AuthN/Z, sessions, offboarding': rated inputs = []
area 'Test strategy, coverage, false confidence, isolation': rated inputs = ['source_files_without_covering_test_share', 'assertion_density_per_test', 'test_config_and_ci_missing']
area 'Type safety & code quality': rated inputs = ['lint_config_missing', 'format_config_missing']
area 'Documentation source-of-truth governance': rated inputs = []
area 'Technical-debt lifecycle & closure evidence': rated inputs = []
```

No metric or rule exists for the six areas' new signals (no skip/cookie/strict/type-ignore/TODO/removed-symbol/co-change/network metric); areas #5, #8, #27 and #31 carry no rated input at all.

**AFTER**: same fixture, same command, after the wiring commit (implementer capture; the reviewer should re-run it).

```text
captured: 2026-09-29T09:54:17Z  worktree HEAD=f669a88
$ PYTHONPATH=src python -m easy_verifier.adapters.cli score --repo <scratchpad>/t040-fixture --scope project </dev/null > after.json; python summarize.py after.json
score exit=0
architecture: rating_abstention value=None reason=below_coverage_floor
blast-radius: rating_abstention value=None reason=all_metrics_abstained
code-quality: rating value=75 reason=None
   rule functions_over_ccn_10_share [Maintainability, reuse, library judgment, patterns] value=0.0 w=30 passed=True
   rule max_function_ccn [Maintainability, reuse, library judgment, patterns] value=1 w=15 passed=True
   rule lint_config_missing [Type safety & code quality] value=0 w=15 passed=True
   rule format_config_missing [Type safety & code quality] value=1 w=10 passed=False
   rule type_escapes_per_kloc [Type safety & code quality] value=125.0 w=15 passed=False
   rule todo_without_ticket_share [Technical-debt lifecycle & closure evidence] value=0.5 w=15 passed=True
requirement-fidelity: rating_abstention value=None reason=below_coverage_floor
security: rating value=80 reason=None
   rule redaction_hits_observed [Threat modeling, abuse cases, appsec] value=0 w=40 passed=True
   rule sink_hits_observed [Threat modeling, abuse cases, appsec] value=0 w=40 passed=True
   rule lockfile_missing [Dependencies, vulns, licenses, obsolescence] value=1 w=20 passed=False
solution-fit: rating_abstention value=None reason=no_static_rule
test-strategy: rating value=45 reason=None
   rule source_files_without_covering_test_share [Test strategy, coverage, false confidence, isolation] value=0.0 w=25 passed=True
   rule assertion_density_per_test [Test strategy, coverage, false confidence, isolation] value=0.6666666666666666 w=20 passed=False
   rule test_config_and_ci_missing [Test strategy, coverage, false confidence, isolation] value=0 w=20 passed=True
   rule tests_without_assertions_share [Test strategy, coverage, false confidence, isolation] value=0.3333333333333333 w=15 passed=False
   rule skipped_test_share [Test strategy, coverage, false confidence, isolation] value=0.3333333333333333 w=10 passed=False
   rule network_calls_in_unit_tests_observed [Test strategy, coverage, false confidence, isolation] value=1 w=10 passed=False
overall: {'kind': 'overall_rating', 'value': 67}
metric names computed (31): acceptance_criteria_traced_to_code_share, acceptance_criteria_traced_to_test_share, architecture_description_missing, assertion_density_per_test, assertions_observed, changed_files_in_churn_hotspots_share, decision_records_missing, declared_source_coverage, evidence_lines_observed, excerpts_observed, format_config_missing, functions_over_ccn_10_share, lint_config_missing, lockfile_missing, max_fan_in_changed, max_function_ccn, mean_excerpt_lines, network_calls_in_unit_tests_observed, redacted_file_share, redaction_hits_observed, sink_hits_observed, skipped_test_share, source_file_share, source_files_without_covering_test, source_files_without_covering_test_share, test_config_and_ci_missing, test_to_source_ratio, tests_without_assertions_share, todo_without_ticket_share, top_level_import_cycles, type_escapes_per_kloc
  metric name containing 'skip': ['skipped_test_share']
  metric name containing 'cookie': []
  metric name containing 'strict': []
  metric name containing 'type_ignore': []
  metric name containing 'todo': ['todo_without_ticket_share']
  metric name containing 'removed': []
  metric name containing 'co_change': []
  metric name containing 'network': ['network_calls_in_unit_tests_observed']
area 'Backward compatibility & upgrade safety': rated inputs = []
area 'AuthN/Z, sessions, offboarding': rated inputs = []
area 'Test strategy, coverage, false confidence, isolation': rated inputs = ['source_files_without_covering_test_share', 'assertion_density_per_test', 'test_config_and_ci_missing', 'tests_without_assertions_share', 'skipped_test_share', 'network_calls_in_unit_tests_observed']
area 'Type safety & code quality': rated inputs = ['lint_config_missing', 'format_config_missing', 'type_escapes_per_kloc']
area 'Documentation source-of-truth governance': rated inputs = []
area 'Technical-debt lifecycle & closure evidence': rated inputs = ['todo_without_ticket_share']
```

**DELTA**: [one sentence — what a user can now do that they could not before]

**WITNESS**: [who ran it and when — derived from `memory/event-trace/T040.jsonl`, never the
implementing agent alone]
