# Scoring rules (no LLM)

Every rating is fixed arithmetic over measured facts. The rules, thresholds, weights, and coverage
floors are static data in `src/easy_verifier/core/judge.py`; the registry-field mapping is in
`src/easy_verifier/core/metric_tables.py` (`FIELD_METRICS`, `ROLE_METRICS`). The session around
these rules is drawn in [`SCORING_FLOW.md`](SCORING_FLOW.md).
Which of the 32 evaluation areas each rule belongs to, and which areas have no rule yet, is in
[`AREA_COVERAGE.md`](AREA_COVERAGE.md).

## How a dimension is rated

1. **Coverage floor.** If too few of the dimension's source roles were filled, the dimension
   abstains (`below_coverage_floor`) instead of guessing.
2. **Pass/fail per rule.** Each rule compares one metric to a threshold (`at_most` or `at_least`).
   A pass earns the rule's full weight; a fail earns 0. Each dimension's weights total 100.
3. **Abstained metrics are excluded** from both numerator and denominator. If every metric
   abstained, the dimension abstains (`all_metrics_abstained`).
4. **Measured-weight floor** (`MEASURED_WEIGHT_FLOOR = 0.50`, DDR-0010). If the measured rules'
   weight is below half of the dimension's declared rule weight, the dimension abstains
   (`insufficient_measured_weight`) with `measured_share` and every unmeasured rule and its
   reason. Exactly 0.50 is rated.
5. **Rating** = `round(100 × earned weight ÷ available weight)`.
6. **Overall** = the average of the dimensions that produced a rating.

An abstention for missing evidence (`insufficient_measured_weight`, `below_coverage_floor`,
`coverage_not_applicable`, `all_metrics_abstained`, `dimension_failed`) never gets a number from
anyone. It appears in the payload's `warnings`, in the report's "Evidence warnings" block, and in
the improvement plan's abstained lines (with the unmeasured rules to fix).

The only judgment input is the calling agent's `gate_evaluations`, blended as
`rules × (1 − w) + agent × w` with `w = 0.5 × confidence` and always shown with its parts. It is
accepted only for solution-fit (`no_static_rule`) and for dimensions with a borderline input.

### Coverage floors

| Dimension | Floor |
|---|---|
| architecture | 0.40 |
| solution-fit | 0.50 |
| requirement-fidelity | 0.50 |
| code-quality | 0.16 |
| security | 0.25 |
| test-strategy | 0.20 |
| blast-radius | 0.25 |

architecture (DDR-0011, T074): documents carry 20 and code 80. A missing architecture description or
decision record is a failed rule whenever the role search ran, never missing evidence. Coverage also
seeks "source files with import statements", so a repository with code and a README reaches the
0.40 floor. `layer_direction_violations` counts import statements from a lower to a higher layer
(data → service, service → api, data → api) between files the `layer_paths` conventions classify;
`shared` files (modules, config, utils, constants, enums, types) and unclassified files never count,
and the rule abstains when fewer than 50% of the non-shared source files quoted classify. DTOs,
schemas, exceptions and providers are `shared` boundary contracts. Only the curated `layer_paths`
apply for now: local-layer and `.easy-verifier.toml` layer paths are not used in scoring until
conventions are embedded for replay (T075). A README heading naming "Architecture" fills the
`architecture-doc` role (coverage) and passes the description rule, citing the same excerpt.

## Rules and the registry fields they read

Metrics come from static analysis: file and pattern matching, complexity counts, the import graph,
git history and churn, and per-language patterns from the registry (vendored Linguist, CWE, and
ASVS data, plus local research in the source-of-truth layer). Each rule reads the registry fields
listed; *(opt)* marks optional refinements the metric computes without. "Delimiters" means
`comment_delimiters` + `string_delimiters`.

| Dimension | Rule | Weight | Pass when | Registry fields read |
|---|---|---|---|---|
| architecture | `architecture_description_missing` | 10 | = 0 | `roles.architecture-doc`; a README heading naming "Architecture" also passes |
| | `decision_records_missing` | 10 | = 0 | `roles.decision-record` |
| | `top_level_import_cycles` | 40 | = 0 | `source_extensions`, delimiters, `import_syntax` |
| | `layer_direction_violations` | 40 | = 0 | `source_extensions`, delimiters, `import_syntax`, conventions `layer_paths` |
| requirement-fidelity | `requirements_doc_missing` | 10 | = 0 | `roles.requirements-doc`; a missing document fails (1) once the role search ran to completion. `requirements_docs_count` stays computed, unrated (T077) |
| | `code_commits_with_docs_share` | 10 | ≥ 0.30 | `source_extensions`, `test_name_patterns`, `colocated_test_name_patterns` *(opt)*; the target's own git history, paths relative to it (a subdirectory of a larger repository reads only its own commits, T077). No document = the real share from history, not an abstention (T075) |
| | `routes_without_test_share` | 40 | ≤ 0.20 | `source_extensions`, delimiters, `route_tokens`, conventions `route_files`, `test_name_patterns`; whole files; a route is tested when a test names its path's static segments or its handler; abstains with no route |
| | `commits_with_issue_reference_share` | 20 | ≥ 0.50 | conventions `issue_reference_patterns`, `issue_reference_exclusions`; last 200 non-merge commits of the target's own history (paths relative to it, T077); abstains below 20 commits |
| | `requirement_items_traced_share` | 20 | ≥ 0.80 | conventions `requirement_item_patterns` (curated: ids, Gherkin scenarios, OpenAPI `operationId`; checklist lines are plan tasks and only count when a repository declares them, T077); items from `roles.requirements-doc` / `roles.spec-doc` (incl. `docs/requirements*/`, OpenAPI/Swagger) traced in code or tests; abstains with no item |
| code-quality | `functions_over_ccn_10_share` | 25 | ≤ 0.10 | `source_extensions`, delimiters, `branch_keywords`, `function_start` |
| | `max_function_ccn` | 15 | ≤ 15 | `source_extensions`, delimiters, `branch_keywords`, `function_start` |
| | `lint_config_missing` | 10 | = 0 | `roles.lint-config` |
| | `format_config_missing` | 10 | = 0 | `roles.format-config` |
| | `type_escapes_per_kloc` | 15 | ≤ 5 | `source_extensions`, delimiters, `type_escapes`, `type_stub_names` *(opt)* |
| | `todo_without_ticket_share` | 15 | ≤ 0.50 | `source_extensions`, delimiters |
| | `strict_type_config_missing` | 10 | = 0 | `type_config_files`, `type_strict`, `type_strict_off`, `type_config_extends` (all *opt*; abstains without a type checker config) |
| security | `redaction_hits_observed` | 35 | = 0 | none (built-in secret patterns) |
| | `sink_hits_observed` | 35 | = 0 | `source_extensions`, delimiters, `security_sinks`, `interpolating_strings` *(opt)* |
| | `lockfile_missing` | 15 | = 0 | `roles.lockfile` |
| | `cookie_flags_missing_observed` | 15 | = 0 | `source_extensions`, `test_name_patterns`, `colocated_test_name_patterns` *(opt)*, delimiters, `cookie_calls`, `auth_markers`, `cookie_secure` / `cookie_httponly` / `cookie_samesite` *(opt)*; abstains where no auth or session code was read |
| test-strategy | `source_files_without_covering_test_share` | 25 | ≤ 0.20 | `source_extensions`, `test_name_patterns`, `colocated_test_name_patterns` *(opt)*, `test_candidates` *(opt)* |
| | `assertion_density_per_test` | 20 | ≥ 1.0 | `test_name_patterns`, `colocated_test_name_patterns` *(opt)*, `test_declarations`, `assertions` |
| | `test_config_and_ci_missing` | 20 | = 0 | `roles.test-config`, `roles.ci-workflow` |
| | `tests_without_assertions_share` | 15 | ≤ 0.10 | `test_name_patterns`, `colocated_test_name_patterns` *(opt)*, `test_declarations`, `assertions`, delimiters |
| | `skipped_test_share` | 10 | ≤ 0.05 | `test_name_patterns`, `colocated_test_name_patterns` *(opt)*, `test_declarations`, delimiters, `skip_markers` |
| | `network_calls_in_unit_tests_observed` | 10 | = 0 | `test_name_patterns`, `colocated_test_name_patterns` *(opt)*, delimiters, `network_calls` |
| blast-radius | `max_fan_in_changed` | 35 | ≤ 20 | `source_extensions`, delimiters, `import_syntax` |
| | `changed_files_in_churn_hotspots_share` | 35 | ≤ 0.20 | none (git history) |
| | `public_symbols_removed` | 15 | = 0 | `source_extensions`, `test_name_patterns`, `colocated_test_name_patterns` *(opt)*, `public_declarations` |
| | `destructive_migration_ops` | 15 | = 0 | none (generic patterns) |
| solution-fit | none by design | — | — | always abstains (`no_static_rule`); judging fit is left to the agent |

Every threshold carries a citation in the output: ISO/IEC 42010, 29148, 26514, 5055, 29119,
McCabe, NIST SP 500-235, CWE Top 25, OWASP ASVS, Henry–Kafura, Nagappan–Ball, SemVer, or
`project default` where no external standard fixes the number.

### Fields that feed no rule directly

- `manifests` detects the language and switches on its `roles.*` globs.
- `frameworks` detects framework entries. A framework can only add `test_name_patterns`,
  `test_declarations`, `assertions`, `security_sinks`, `roles.test-config`, and
  `roles.lint-config` to its language.

This mapping is what `needs_input.reference` uses: when a detected language or framework lacks a
required field, its `why` names the rules that read it.
