# Scoring rules (no LLM)

Every rating is fixed arithmetic over measured facts. The rules, thresholds, weights, and coverage
floors are static data in `src/easy_verifier/core/judge.py`; the registry-field mapping is in
`src/easy_verifier/core/metric_tables.py` (`FIELD_METRICS`, `ROLE_METRICS`). The session around
these rules is drawn in [`SCORING_FLOW.md`](SCORING_FLOW.md).

## How a dimension is rated

1. **Coverage floor.** If too few of the dimension's source roles were filled, the dimension
   abstains (`below_coverage_floor`) instead of guessing.
2. **Pass/fail per rule.** Each rule compares one metric to a threshold (`at_most` or `at_least`).
   A pass earns the rule's full weight; a fail earns 0. Each dimension's weights total 100.
3. **Abstained metrics are excluded** from both numerator and denominator. If every metric
   abstained, the dimension abstains (`all_metrics_abstained`).
4. **Rating** = `round(100 × earned weight ÷ available weight)`.
5. **Overall** = the average of the dimensions that produced a rating.

The only judgment input is the calling agent's `gate_evaluations`, blended as
`rules × (1 − w) + agent × w` with `w = 0.5 × confidence` and always shown with its parts.

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

## Rules and the registry fields they read

Metrics come from static analysis: file and pattern matching, complexity counts, the import graph,
git history and churn, and per-language patterns from the registry (vendored Linguist, CWE, and
ASVS data, plus local research in the source-of-truth layer). Each rule reads the registry fields
listed; *(opt)* marks optional refinements the metric computes without. "Delimiters" means
`comment_delimiters` + `string_delimiters`.

| Dimension | Rule | Weight | Pass when | Registry fields read |
|---|---|---|---|---|
| architecture | `architecture_description_missing` | 30 | = 0 | `roles.architecture-doc` |
| | `decision_records_missing` | 30 | = 0 | `roles.decision-record` |
| | `top_level_import_cycles` | 40 | = 0 | `source_extensions`, delimiters, `import_syntax` |
| requirement-fidelity | `acceptance_criteria_traced_to_code_share` | 35 | ≥ 0.80 | `source_extensions`, `test_name_patterns`, `colocated_test_name_patterns` *(opt)* |
| | `acceptance_criteria_traced_to_test_share` | 35 | ≥ 0.80 | `source_extensions`, `test_name_patterns`, `colocated_test_name_patterns` *(opt)* |
| | `requirements_docs_count` | 15 | ≤ 1 | none (generic role patterns) |
| | `code_commits_with_docs_share` | 15 | ≥ 0.30 | `source_extensions`, `test_name_patterns`, `colocated_test_name_patterns` *(opt)*; git history |
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
