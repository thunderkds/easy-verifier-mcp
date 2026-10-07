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
| reliability | 0.25 |
| supply-chain | 0.40 |
| api | 0.25 |
| healthcare *(optional pack)* | 0.25 |
| finance *(optional pack)* | 0.25 |

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

supply-chain (T041, floor 0.40 and weights user-approved 2026-10-07): five roles (package manifest,
lockfile, CI workflow, licence file, release configuration), so two of them reach the floor and a
repository with none of them abstains with every role named.

api (T044, floor 0.25 user decision 2026-10-07; weights proposed by T044 and accepted under user
policy 2026-10-07): three roles (committed API specification file; route definitions in source files;
request validation in source files), so one of them reaches the floor and a repository with none
abstains with every role named. A library with no route and no specification abstains
`insufficient_measured_weight`, never 0. The four metrics are computed over the whole text of the
in-scope source files (priority batches above 200, disclosed as a sample) and the changes-scope diff.

reliability (T043, floor user-approved 2026-10-06): its roles are three code pseudo-roles (source
files of a registry language; outbound HTTP client calls; database access calls) and the README, so
a repository with source code reaches the 0.25 floor and one with none of them abstains with every
role named. The four rules count findings over the whole text of the in-scope source files (priority
batches above 200, disclosed as a sample); test files are never scanned. Each count is textual and a
place to look, not a proven defect. The timeout, retry and loop rules abstain where no outbound call,
retry statement or query call was found: a repository with nothing to judge earns no pass for it.
Transaction, lock and idempotency code (#6) needs judgment, so it is quoted in the pack as evidence
for the calling agent and feeds no rule. Business continuity (#32) is a documentation rule: a
continuity, BCP, degraded-mode, resilience or fallback document is reported present or missing.

healthcare (optional pack, T047, floor user-approved 2026-10-06): rated only when the target's
`.easy-verifier.toml` lists it (`packs = ["healthcare"]`) or the agent picks it
(`agent_input.packs`); it is never guessed, and a repository that does not enable it is scored
exactly as before. Its roles are two pseudo-roles (test data files; log statements in source files),
so either one reaches the 0.25 floor. Both rules count PHI-shaped values (dashed SSNs, labelled
medical record numbers, labelled birth dates) over whole files: test data is any file under a
`test_data_paths` glob (the first 200 in path order), log statements are source lines matching
`log_calls`. Documented placeholders (`phi_placeholders`, e.g. `000-00-0000`, `123-45-6789`, a digit
repeated, `1970-01-01`) never count. A matched value is never shown: excerpts read
`[PHI <kind> redacted]`, and derivations give only path, line and kind. The log rule abstains when no
log statement was found. Retention (#9), business associate agreements, data classification and
residency (#28) are documentation rules: the document is reported present or missing. The pack's
patterns live in `registry/packs/healthcare.toml`, each with its citation. The 50/50 weights are
a proposal pending user sign-off.

finance (optional pack, T048, floor 0.25 user-approved 2026-10-06): enabled like healthcare
(`packs = ["finance"]` or `agent_input.packs`), never guessed. Two pseudo-roles (a money-named field
declaration; a ledger, transaction or payment table or model), so either one reaches the floor.
Identifier names are split into words; a name is money-named when a word is in `money_names`
(amount, price, balance, fee, cost, subtotal, …) and none is in `money_excluded_words` (count, qty,
items, pages, cents, micros, rate, id, …), so `amount_of_items`, `total_pages` and `amount_cents`
never count, and bare `total` (as often a row count) is not a money name. A money-named declaration
whose type matches `float_types` (Python `float`, Java/C#/Kotlin `double`, SQL
`float`/`real`/`double precision`, Prisma `Float`, Go `float64`, Rust `f64`, Mongoose `Number`)
counts in any file; TS/JS `number` (`persistence_float_types`) counts only in a `persistence_paths`
file (entities, models, schemas, Prisma schema, migrations), so DTOs, request/response types and
view models are skipped (user decision 2026-10-06); `Decimal`, `BigDecimal`, `decimal`, `numeric(…)` and integer minor units are exact. The
float rule abstains when no money-named declaration exists. A ledger is a table or model whose name
holds a `ledger_names` word (ledger, journal, transaction, payment, transfer, posting) and does not
end in a `non_ledger_heads` word (PaymentMethod, TransactionStatus are not ledgers). Its audit
column (created_at / created_by / timestamps, …) is looked for in its own declaration; one that
inherits from a base, audit or timestamp class is never counted. Update / delete sites (SQL `UPDATE
… SET`, `DELETE FROM`, ORM `update` / `delete` / `remove` / `destroy` calls) count only when their
target is a ledger declared in the same repository. With no ledger, both ledger rules abstain
(nothing to judge, never 0). Whether a ledger balances or is correct is judgment: ledger declarations
and mutation sites are quoted in the pack for the agent and feed no rule. The 50/25/25 weights are
user-approved (2026-10-06).

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
| reliability | `swallowed_errors_observed` | 35 | = 0 | `source_extensions`, `test_name_patterns`, `colocated_test_name_patterns` *(opt)*, delimiters, `swallowed_errors` *(opt)*; matched with comments kept, so a handler holding a comment does not count; Go's `if err != nil` handling never counts, only an empty branch |
| | `outbound_calls_without_timeout_observed` | 35 | = 0 | same file fields, `outbound_calls` / `call_timeouts` / `client_timeouts` *(opt)*; a call statement with no deadline token inside it, unless its file sets a client-wide deadline (a wrapper); abstains with no outbound call |
| | `retries_without_backoff_observed` | 10 | = 0 | same file fields, `retry_calls` / `retry_backoff` *(opt)*; abstains with no retry statement |
| | `queries_in_loops_observed` | 20 | = 0 | same file fields, `function_start`, `query_calls` / `loop_keywords` *(opt)*; a query on a line enclosed by a loop line (by indentation, up to its function) or after a `.method` loop token on its own line; a loop header runs its query once and never counts; abstains with no query call |
| healthcare *(optional pack)* | `phi_values_in_test_data_observed` | 50 | = 0 | pack fields `phi_values`, `phi_placeholders`, `test_data_paths` |
| | `phi_values_in_log_statements_observed` | 50 | = 0 | pack fields `phi_values`, `phi_placeholders`, `log_calls`; source files as reliability; abstains with no log statement |
| finance *(optional pack)* | `float_money_observed` | 50 | = 0 | pack fields `money_names`, `money_excluded_words`, `money_declarations`, `float_types`, `persistence_float_types`, `persistence_paths`, `schema_paths`; source files as reliability plus schema files; abstains with no money-named declaration |
| | `ledger_tables_without_audit_columns_observed` | 25 | = 0 | pack fields `ledger_names`, `non_ledger_heads`, `name_suffixes`, `ledger_declarations`, `entity_classes`, `entity_markers`, `audit_columns`; abstains with no ledger |
| | `ledger_rows_mutated_observed` | 25 | = 0 | pack field `ledger_mutations` against the declared ledgers; abstains with no ledger |
| supply-chain | `lockfile_missing` | 20 | = 0 | `roles.lockfile` |
| | `licence_file_missing` | 15 | = 0 | none (generic `licence-file` role patterns) |
| | `ci_actions_unpinned_share` | 20 | = 0 | none (generic CI facts in `core/roles.py`); abstains where no external `uses:` reference is quoted |
| | `ci_lockfile_install_missing` | 20 | = 0 | `lockfile_install` *(opt)*; abstains where no CI workflow is quoted |
| | `ci_provenance_step_missing` | 25 | = 0 | none (generic CI facts in `core/roles.py`); looks in CI workflows and release configuration |
| api | `api_spec_missing` | 30 | = 0 | none (generic `api-spec` role patterns); `api_spec_generators` *(opt)* credits a specification generated from code; abstains with no route and no specification |
| | `api_version_missing` | 20 | = 0 | `route_tokens`, `api_version_markers` *(opt)*, generic version segment `^v[0-9]+$` (AIP-185) over route paths, non-import path literals and specification paths/packages; abstains with no route and no specification |
| | `request_validation_missing` | 30 | = 0 | `route_tokens`, `request_validation` *(opt)*; repository level (any validation beside routes), not per route; abstains with no route |
| | `breaking_api_changes_observed` | 20 | = 0 | `route_tokens`, generic specification definition lines; changes scope only (routes or spec keys removed and not re-added), abstains elsewhere |
| solution-fit | none by design | — | — | always abstains (`no_static_rule`); judging fit is left to the agent |

supply-chain also carries one documentation rule (area #22, rollback): a document named for
rollback is *present* (with its file) or *missing*, never a number. Live vulnerability status
(CVE feeds) is not verifiable offline and has no rule.

Every threshold carries a citation in the output: ISO/IEC 42010, 29148, 26514, 5055, 29119,
McCabe, NIST SP 500-235, CWE Top 25, CWE-390/1069/400/1050, Google SRE, OWASP ASVS, OpenSSF Scorecard,
SLSA, CycloneDX/SPDX, Henry–Kafura,
Nagappan–Ball, SemVer, ISO 22301 (documentation rule), HIPAA 45 CFR §164.514 (healthcare pack;
§164.316, §164.504(e), NIST FIPS 199 and SP 800-144 for its documentation rules), CWE-1339,
PostgreSQL numeric types, NIST SP 800-53 AU-3, SEC Rule 17a-4(f) and Fowler's Reversal Adjustment
(finance pack; per-language decimal-type documentation in `registry/packs/finance.toml`), or
`project default` where no external standard fixes the number.

### Fields that feed no rule directly

- `lockfile_install` feeds `ci_lockfile_install_missing` only and is optional: a language without a
  frozen-lockfile install mode (Java, Kotlin) declares none (T041).
- `manifests` detects the language and switches on its `roles.*` globs.
- `frameworks` detects framework entries. A framework can only add `test_name_patterns`,
  `test_declarations`, `assertions`, `security_sinks`, `roles.test-config`, and
  `roles.lint-config` to its language.
- `transaction_markers` (T043) selects the transaction, lock and idempotency lines the reliability
  pack quotes for the calling agent; area #6 has no rule.

This mapping is what `needs_input.reference` uses: when a detected language or framework lacks a
required field, its `why` names the rules that read it.
