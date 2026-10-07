# Area coverage: the 32 evaluation areas and the rules behind them

This page maps each of the 32 evaluation areas to the rating rules that measure it today, and to
the planned work for the areas that have none yet. Use it to see what a score does and does not
cover: a dimension number speaks only for the areas whose rules it contains.

Source of truth in code:

- The 32 area names: `judge.AREAS` in `src/easy_verifier/core/judge.py`.
- Each rating rule's area: the `area` field of every rule in `judge.RATING_RULES`.
- Documentation-only checks: `judge.DOCUMENTATION_RULES` (present or missing, never a number).

The planned mapping and its reasoning are in `BRAINSTORMING_LOG_evaluation-areas.md` (decision
DDR-0008). Rule thresholds, weights and citations are in [`SCORING_RULES.md`](SCORING_RULES.md).
`tests/test_t072_area_coverage_doc.py` fails if this table and the code disagree.

## Summary

| Status | Areas | Meaning |
|---|---|---|
| Covered | 4 | At least one rule measures the area as planned |
| Partial | 16 | Rules exist, but part of the area is not measured yet (see Notes) |
| Not yet | 12 | No rule; the planned dimension or pack is not built |

11 dimensions exist today: the original 7, reliability (T043), supply-chain (T041), api (T044) and data (T045), plus the optional healthcare
(T047) and finance (T048) packs, which rate only in repositories that enable them
(`.easy-verifier.toml` `packs = ["healthcare"]` / `["finance"]` or an agent pick). The 2 remaining
planned dimensions (infrastructure, operations) and the remaining optional pack
(frontend accessibility) are tasks T042, T046 and T049 on the Kanban.

**What this means for a score.** A repository's overall can rest on only a few areas. For example,
coffee-shop-api (2026-10-04) scored 65 from code-quality and security alone, which together cover
areas 8, 10, 17, 18, 20 and 31; of those, its run measured 10, 17, 18 and 20. The other areas were
either not rated for lack of evidence or have no rule at all.

Every score now says this itself: the payload's `areas_measured` and `areas_without_rule` (both in
area order, derived from the rule tables) and the report's "Areas no rule covers yet" list (T082).
An optional pack's rules count there only in a run where the pack is enabled: in any other run areas 9
and 28 (healthcare) and 3 (finance) stay listed, because nothing measured them.

Class (planned areas): **S** static rule from code/config · **G** evidence gathered, judgment at the
agent gate · **X** process or live-system fact: only documentation presence is checked.

## Mapping

| # | Area | Status | Rules today (`dimension` · `metric`) | Planned home | Notes |
|---|---|---|---|---|---|
| 1 | Architecture & dependency direction | Partial | `architecture` · `architecture_description_missing`<br>`architecture` · `decision_records_missing`<br>`architecture` · `top_level_import_cycles`<br>`architecture` · `layer_direction_violations` | — | layers from curated `layer_paths` conventions (local/config paths from T075); abstains below 50% classified |
| 2 | Business-rule correctness | Partial | `requirement-fidelity` · `routes_without_test_share`<br>`requirement-fidelity` · `commits_with_issue_reference_share`<br>`requirement-fidelity` · `requirement_items_traced_share` | — | textual: routes ↔ tests by path segments or handler name, commit issue references, requirement items in any declared form (T075, DDR-0011) |
| 3 | Financial integrity & historical reconstruction | Partial | `finance` · `float_money_observed`<br>`finance` · `ledger_tables_without_audit_columns_observed`<br>`finance` · `ledger_rows_mutated_observed` | — | optional pack, rated only when enabled; money-named fields declared as binary floating point (integer minor units and decimal types are exact); ledger audit columns and update/delete of ledger rows only where a ledger, transaction or payment table is declared (else both abstain); ledger correctness is judgment, quoted for the agent (class G) |
| 4 | Data model, constraints, migrations | Partial | `data` · `migrations_missing`<br>`data` · `migrations_without_rollback_share`<br>`data` · `schema_constraints_missing`<br>`data` · `destructive_migration_ops_observed` | — | migrations present beside a schema (schema files or data models in code), a rollback per migration, any NOT NULL/unique/foreign-key constraint declared (not per table), DROP/RENAME in up migrations quoted for the agent; whether the live database matches the schema is not verifiable offline |
| 5 | Backward compatibility & upgrade safety | Partial | `blast-radius` · `max_fan_in_changed`<br>`blast-radius` · `changed_files_in_churn_hotspots_share`<br>`blast-radius` · `public_symbols_removed`<br>`blast-radius` · `destructive_migration_ops` | — | measured only at `--scope changes` |
| 6 | Transactions, concurrency, idempotency | Not yet | — | reliability (T043), evidence only | class G: no rule by design (needs judgment); the reliability pack quotes transaction, lock and idempotency code (registry `transaction_markers`) for the calling agent |
| 7 | API contracts, validation, versioning | Partial | `api` · `api_spec_missing`<br>`api` · `api_version_missing`<br>`api` · `request_validation_missing`<br>`api` · `breaking_api_changes_observed` | — | specification presence (committed or generated), versioning, request validation at repository level (not per route), removed routes/spec keys in changes scope only; contract conformance of a running service is not verifiable offline |
| 8 | AuthN/Z, sessions, offboarding | Partial | `security` · `cookie_flags_missing_observed`<br>`security` documentation check | — | offboarding is process (documentation check only) |
| 9 | PHI minimization, retention, test-data safety | Partial | `healthcare` · `phi_values_in_test_data_observed`<br>`healthcare` · `phi_values_in_log_statements_observed`<br>`healthcare` documentation check | — | optional pack, rated only when enabled; PHI-shaped values (SSN, labelled MRN / birth date; placeholders excluded) in test data and log statements; retention is a documentation check; minimization in production data is not verifiable |
| 10 | Threat modeling, abuse cases, appsec | Covered | `security` · `redaction_hits_observed`<br>`security` · `sink_hits_observed` | — |  |
| 11 | Infra security: IAM, networking, KMS, secrets | Not yet | — | infrastructure (T042) | class S |
| 12 | Error handling & safe degradation | Partial | `reliability` · `swallowed_errors_observed` | — | empty handlers only (registry `swallowed_errors`; a handler holding a comment, and Go's `if err != nil` handling, never count); safe degradation not measured |
| 13 | Retries, deadlines, unknown outcomes, vendor outages | Partial | `reliability` · `outbound_calls_without_timeout_observed`<br>`reliability` · `retries_without_backoff_observed` | — | calls and retry libraries with no default deadline or delay (curated per language); unknown outcomes and vendor outages not measured |
| 14 | Observability, auditing, SLOs, error budgets | Not yet | — | operations (T046) | class S / X |
| 15 | Performance, scalability, capacity, cost | Partial | `reliability` · `queries_in_loops_observed` | — | query-in-loop only (textual, by indentation); capacity and cost not verifiable from a repository |
| 16 | Test strategy, coverage, false confidence, isolation | Covered | `test-strategy` · `source_files_without_covering_test_share`<br>`test-strategy` · `assertion_density_per_test`<br>`test-strategy` · `test_config_and_ci_missing`<br>`test-strategy` · `tests_without_assertions_share`<br>`test-strategy` · `skipped_test_share`<br>`test-strategy` · `network_calls_in_unit_tests_observed` | — |  |
| 17 | Type safety & code quality | Covered | `code-quality` · `lint_config_missing`<br>`code-quality` · `format_config_missing`<br>`code-quality` · `type_escapes_per_kloc`<br>`code-quality` · `strict_type_config_missing` | — |  |
| 18 | Maintainability, reuse, library judgment, patterns | Partial | `code-quality` · `functions_over_ccn_10_share`<br>`code-quality` · `max_function_ccn` | — | duplication not yet measured |
| 19 | Accessibility, responsive UX, browser compat | Not yet | — | frontend accessibility pack (T049) | class S |
| 20 | Dependencies, vulns, licenses, obsolescence | Partial | `security` · `lockfile_missing`<br>`supply-chain` · `lockfile_missing`<br>`supply-chain` · `licence_file_missing` | — | lockfile and licence file presence; live vulnerability status (CVE feeds) is not verifiable offline (class X) and obsolescence is not measured |
| 21 | CI quality & reproducibility | Partial | `supply-chain` · `ci_actions_unpinned_share`<br>`supply-chain` · `ci_lockfile_install_missing` | — | external CI actions pinned by SHA and a lockfile-faithful install (registry `lockfile_install`); abstain where no CI workflow is quoted; other CI quality not measured |
| 22 | Artifact provenance, SBOM, signing, promotion, rollback | Partial | `supply-chain` · `ci_provenance_step_missing`<br>`supply-chain` documentation check | — | an SBOM, signing or provenance step in CI or release configuration; rollback is a documentation check (present or missing, never a number); promotion not measured |
| 23 | Terraform state, environment, account, drift | Not yet | — | infrastructure (T042) | class S / X |
| 24 | Database HA, backups, restore, DR | Not yet | — | infrastructure (T042) | class S / X |
| 25 | Incident response, change mgmt, access review | Not yet | — | operations (T046) | class X |
| 26 | Configuration ownership & operational readiness | Not yet | — | operations (T046) | class S |
| 27 | Documentation source-of-truth governance | Covered | `requirement-fidelity` · `requirements_doc_missing`<br>`requirement-fidelity` · `code_commits_with_docs_share` | — |  |
| 28 | Vendor, BAA, data classification, residency | Not yet | `healthcare` documentation check | healthcare pack (T047), documentation only | class X: optional pack; only BAA, data-classification and residency documents' presence is checked (never a number) |
| 29 | AI-assisted-development safety | Not yet | — | operations (T046) | class S |
| 30 | Developer experience & deterministic local setup | Not yet | — | operations (T046) | class S |
| 31 | Technical-debt lifecycle & closure evidence | Partial | `code-quality` · `todo_without_ticket_share` | — | debt age via git blame not yet measured |
| 32 | Business continuity & degraded modes | Not yet | `reliability` documentation check | reliability (T043), documentation only | class X: only a continuity, BCP, degraded-mode, resilience or fallback document's presence is checked (never a number) |

## Keeping this page current

When a task adds or moves a rating rule, update its row here in the same commit. The test compares
every row's rules with `judge.RATING_RULES` by area, and every status with whether the area has a
rule.
