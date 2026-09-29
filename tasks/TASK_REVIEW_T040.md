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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t040_area_rule_groups.py` (23 tests). AC3 #16: met/unmet tests for tests_without_assertions_share, skipped_test_share (every unconditional skip counts, reason split disclosed) and network_calls_in_unit_tests_observed. AC4 #17: type_escapes_per_kloc, with generated stubs excluded. AC6 #31: todo_without_ticket_share cites ISO 5055 only. AC7: `test_signed_off_weight_table_and_areas[test-strategy|code-quality]` pins the user-signed weights (sum 100), areas and project-default thresholds. Stage 4 fixes: `test_a_test_cut_by_the_excerpt_limit_is_not_judged` + twin, clipped-only abstain, clip-marker pin against both excerpt producers, declaration-line test. Implementer red-first: 16 of 16 metrics tests, then 8 wiring tests. Changed pins, each justified in the implementer report: T035 APPROVED table and CCN weight 40→30; T028 `_rating_60` fixture +1 passing input; T037 cap test (13 required fields for an unknown language; corrected from the implementer's 16); README rating table regenerated; T037 OPTIONAL_FIELDS; test_metrics truncation pair |
| Verification command run | ☑ pass | Supervisor 2026-09-29T10:02Z at `83db118`: `pytest -q` gives `1450 passed, 2 skipped` (exit 0); `ruff check src tests` gives `All checks passed!` (exit 0) |
| Negative cases hold | ☑ pass | Zero denominators abstain: no tests, no TODO markers, no unit test scanned, no source scanned. Integration/e2e/functional tests are excluded from the network metric. `skipif` is not counted. A marker in a string is not counted. A test cut by the excerpt limit is not judged, and an excerpt holding only a cut test abstains. `COVERAGE_FLOORS` and evidence budgets are unchanged |
| verify | ☑ pass | Supervisor, real CLI `score --scope project`. (1) Six-area fixture (`t040-fixture`), 2026-09-29T10:02:29Z: test-strategy 45 (BEFORE 65), code-quality 75 (BEFORE 80). tests_without_assertions_share 0.33 unmet, skipped_test_share 0.33 unmet, network_calls 1 unmet, type_escapes_per_kloc 125 unmet, todo_without_ticket_share 0.5 met; every input carries its area. (2) P1 repro (209-line test file; test_last crosses the 200-line cut): before the fix "1 of 10 … no assertion: tests/test_core.py:191"; after "0 of 9 … none; 1 test(s) cut by the excerpt line limit were not judged" — pass |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Code review of the `1473029..HEAD` src diff (metrics, metric_tables, registry, judge, curated TOML) and the changed pin tests. P1 (confidence 100, reproduced): a test cut by the 200-line excerpt limit was counted as having no assertion, the miss-list defect class. P2: the reported line was one early (`^\s*` declaration match). Both fixed in `83db118`. Manual security review (the built-in skill needs `origin/HEAD`): new registry tokens go through the existing guarded token regex, local values are limited to at most 2 `*`, `type_stub_names` is base-name only, and there is no new I/O or egress; no findings. Behaviour note: an unknown language now has 13 required reference fields (was 10). **Correction 2026-09-29:** this row originally said 16, copied from the implementer's report; `required_fields()` at `15bca51` returns 13, so with frameworks the 20-request cap moves more fields into the already-disclosed `omitted`. Implementer fetch-checked all 56 citation URLs (HTTP 200 and syntax present); Supervisor did not re-fetch. Scope split to T055/T056 (user) |
| Full smoke suite still green (no regression) | ☑ pass | 1450 passed, 2 skipped, exit 0 |
| **UI: Visual regression (diff or verdict pasted)** | ☑ N/A | Pure backend task, no UI |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☑ N/A | Pure backend task, no UI |
| **UI: Responsiveness at target viewports** | ☑ N/A | Pure backend task, no UI |

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

**WITNESS**: Supervisor, 2026-09-29T10:02:29Z, independent re-run of the six-area fixture (numbers match the implementer's AFTER) plus the P1 repro. Recorded in `memory/event-trace/T040.jsonl`.