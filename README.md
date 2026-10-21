# easy-verifier-mcp

A local, no-LLM engine that gathers **evidence** about a repository — file excerpts, citations,
lists of what it looked for and didn't find — and computes inspectable quality ratings from
declared rules over measured facts. A calling agent can optionally submit its own findings for a
separate assessment and divergence. The engine performs no inference and requires no model API
key: nothing here calls an LLM.

## What it refuses to do

- **No inferred verdict.** Ratings are deterministic arithmetic over cited metrics. Caller findings
  produce a separate assessment; the engine never blends the two or invents a judgment.
- **No inventing context.** A source it did not find is reported as missing, never guessed at or
  filled in.
- **No coverage number without its miss list.** A "found 4/6" is always shown next to the two
  sources that weren't found, so the number is auditable rather than a bare percentage.
- **No execution of target-repository code**, ever — evaluation is read-only.
- **No writes outside the evaluated repo's `reports/` directory** (or the reports directory you
  name in `EASY_VERIFIER_REPORTS_DIR`), and never into this repo.
- **No outbound network requests.** Everything runs locally; secret values are redacted to a
  non-reversible fingerprint the moment they're read, never returned raw.

## The dimensions

Each dimension is a separate, independently callable unit — not one monolithic "evaluate" call.

| Dimension | What it looks at |
|---|---|
| `architecture` | Structural fit against the project's declared design |
| `solution-fit` | Whether the change addresses the stated problem |
| `requirement-fidelity` | Whether the change matches its requirement/spec |
| `code-quality` | Style, readability, and maintainability signals |
| `security` | Injection, secret handling, and other security-relevant evidence — available in every mode and scope |
| `test-strategy` | What is and isn't covered by tests |
| `blast-radius` | What else in the repo depends on, or is touched by, the change |
| `reliability` | Error handling, outbound-call deadlines, retry backoff and queries in loops; transaction and idempotency code quoted for the agent; business-continuity document present or missing |
| `supply-chain` | Dependency pinning and licences, CI reproducibility, and provenance, SBOM and signing steps; live vulnerability status is not verifiable offline |
| `data` | Migrations beside a schema, a rollback per migration, NOT NULL/unique/foreign-key constraints, and DROP/RENAME operations in migrations; whether a live database matches the schema is not verifiable offline |
| `operations` | Logging/tracing library in use, audit-log writes, CODEOWNERS, agent guardrails (hooks, deny lists) and no secrets in agent configuration, a tool-version pin and a devcontainer or one-command setup; runbook, incident/change-management, SLO and coding-agent instruction documents are checked for presence only. Whether incidents are handled or SLOs met is not verifiable offline |
| `infrastructure` | Wildcard IAM actions/resources and RBAC verbs, internet-open (0.0.0.0/0) ingress and storage with encryption off in Terraform, Kubernetes and CloudFormation files; a locked remote Terraform state backend and per-environment separation; database backup and high-availability settings; a disaster-recovery document is checked for presence only. Live drift and restore drills are not verifiable offline |
| `change-risk` | Rates a change, not the repository, at `changes`/`worktree` scope only: detects whether it is a bugfix, feature, refactor or chore (branch name, commit subjects, fix issue references, file kinds) and, for a bugfix, checks that a test added or changed in the change matches the changed code. Reported as the separate `change_risk` headline, never averaged into the overall; feature, refactor and chore rules arrive in a later slice |
| `api` | API specification (OpenAPI, GraphQL, protobuf, or generated from code), request validation at entry points, API versioning, and endpoints or spec fields a change removes; whether a running service honours its contract is not verifiable offline |

## Scopes

Every dimension runs against one of four scopes, and a narrow scope with no selector gathers **no
evidence** rather than silently widening to the whole repository:

| Scope | Selector | What it evaluates |
|---|---|---|
| `task` | `--task-id` | One task's `tasks/TASK_GUIDE_Txxx.md` and its acceptance criteria (kit-aware mode only) |
| `changes` | `--ref` (**required**) | A git diff/commit range/branch — no network remote required |
| `worktree` | none | Uncommitted working-tree changes |
| `project` | none | The whole repository |

A narrow scope with no selector is a refusal, not a fallback: `task` without `--task-id` and
`changes` without `--ref` both gather nothing and say so in a warning, rather than quietly
evaluating the whole project.

### Checking a feature or bugfix

To rate only what a branch changes, use the `changes` scope with the range the branch adds on top
of its base:

```console
python -m easy_verifier.adapters.cli score --repo . --scope changes --ref main...HEAD < /dev/null
```

- `--ref main...HEAD` (three dots) diffs from the point the branch left `main`, so the whole branch
  is rated and later commits on `main` are not.
- A bare commit or branch name (`--ref 09be767d0`, `--ref fix/login`) means **that one commit**
  against its parent, not the whole branch.
- Uncommitted work: `--scope worktree` (no `--ref`).
- Through MCP, ask the agent to *"score my changes against main with easy-verifier"*; the `score`
  tool takes `scope="changes"` and `ref="main...HEAD"`.
- `< /dev/null`: when stdin is not a terminal, `score` reads optional findings JSON from it. A
  script or agent shell that leaves stdin open makes it wait forever.

**Reading a change score (2026-10-16).** A `changes` or `worktree` score has two headlines:
`overall`, the mean of the repository-health dimensions that could be rated, and `change_risk`, a
separate rating of the change itself. `change_risk` is never averaged into `overall`. It is rated
only at `changes` and `worktree` scope; at `project` and `task` scope it abstains with a stated
reason. Read both numbers.

- **Change kind.** Each change has one kind: `bugfix`, `feature`, `refactor` or `chore`
  (docs, config or dependency-only). The engine proposes it from the branch name, the commit
  subjects, issue references and the kinds of files changed; with no signal it proposes `feature`,
  and a mixed change takes the most demanding kind (bugfix, then feature, refactor, chore). The
  payload says where the kind came from: `change_kind: {value, source}`, with `source` either
  `detected` or `confirmed`, and lists the signals it used.
- **Confirming the kind.** Through MCP, `score` returns `needs_input.change_kind` (the proposal,
  the signals, the allowed values) and the agent confirms or overrides it by calling `score` again
  with `agent_input.change_kind`. The CLI never asks; give the same answer in a file and pass its
  path (the CLI takes a path, not inline JSON):

  ```console
  echo '{"change_kind": {"value": "bugfix", "reason": "swaps operands to fix a wrong sum"}}' > agent-input.json
  python -m easy_verifier.adapters.cli score --repo . --scope changes --ref main...HEAD --agent-input agent-input.json < /dev/null
  ```

- **What each kind requires.**

  | Kind | Rule | Passes when |
  |---|---|---|
  | `bugfix` | `bugfix_without_regression_test` | at least one test file added or changed in the change is matched to changed code |
  | `feature` | `new_code_without_test_share` | at most 20% of changed source files lack a matched test |
  | `refactor` | `refactor_tests_deleted`, `refactor_uncovered_share` | the change deletes no test, and at most 20% of changed source files lack any covering test in the repository |
  | `chore` | none | the dimension abstains: "chore: no test expectation" |

  A test the change deletes never counts as matched. Matching is by naming correspondence
  (`foo.py` and `test_foo.py`, within one project); tests are searched repository-wide.
- **Fewer abstentions.** At a narrow scope, context files (test config, CI workflow, lockfile,
  lint config, package manifest, container config, API spec, project documents) are now read from
  the whole repository, while the files measured stay the changed ones. Test-strategy, security and
  supply-chain no longer abstain just because their files are outside the diff.
- **Still repository-level.** Architecture rates the repository's documents, not the change, and
  blast-radius `max_fan_in_changed` abstains when the reference sweep stops at its file ceiling.
  Other dimensions still abstain when they have too little evidence; read `overall.abstentions` and
  `warnings` before trusting `overall`.
- **Not yet.** Test-to-symbol pairing, reach to entry points, missed co-change and contract-change
  rules are not yet available.

Example (a one-file node-monorepo bugfix, commit subject "Bugfix/ Update condition time range",
no test): before these changes `overall` was 97 (architecture 90, code-quality 100, blast-radius 100;
test-strategy, security and requirement-fidelity abstained). Now `overall` is 85 (security 100 and
supply-chain 35 are rated) and `change_risk` is 0: kind `bugfix`, detected from the commit subject,
and `bugfix_without_regression_test` fails, citing the changed source file with no matched test.
A bugfix that changes a matching test file passes the rule.

## Two modes: kit-aware and standalone

If the target repository carries kit artifacts (`PROJECT_SPEC.md`, `PRD.md`,
`PROJECT_KANBAN.md`, `tasks/TASK_GUIDE_*.md`, `memory/`), the engine runs in **kit-aware mode** and
treats those as ground truth. Otherwise it runs in **standalone mode**: it scans whatever
documentation exists (`README*`, `docs/`, ADRs, `CONTRIBUTING*`) first, and only falls back to
reading code where the docs are silent. Every standalone response and rendered report carries an
explicit warning that context is limited — it is never left implicit.

## Running it

Two adapters share one core; neither has evaluation logic of its own, so they cannot drift apart.

Install the package into a Python 3.11+ environment for both console entry points:

```console
python -m pip install .
```

### CLI — no server or container required

```bash
python -m easy_verifier.adapters.cli security --repo . --scope project
```

This prints one dimension's evidence pack as JSON to stdout (warnings, if any, go to stderr so
stdout stays parseable). `--scope` accepts `task`, `changes`, `worktree`, or `project`; `--ref` and
`--task-id` supply the `changes`/`task` selectors.

A discovery command lists every dimension with its purpose and declared sources, so a caller
doesn't need to already know the dimension names above:

```bash
python -m easy_verifier.adapters.cli list-dimensions
```

Run several dimensions in one call and receive an aggregate coverage summary:

```bash
python -m easy_verifier.adapters.cli combined --repo . --dimensions security,architecture
```

Rate every dimension in one call. The result includes every cited metric and an overall
disclosure naming which dimensions contributed or abstained:

```bash
python -m easy_verifier.adapters.cli score --repo . --scope project
```

Pass optional findings through `--findings PATH` or stdin to add the caller-derived assessments and
rating-to-assessment divergences to the same JSON output.

#### How each dimension is rated

Full rule table (thresholds, weights, coverage floors, and the registry fields each rule reads):
[`docs/SCORING_RULES.md`](docs/SCORING_RULES.md).

Each dimension has its own rules, declared as data in `judge.RATING_RULES`. A rule compares one
metric with a threshold. A met rule earns its weight and an unmet rule earns zero. The weights in
each dimension add up to 100. A metric that abstains is left out of both the earned and the total
weight, and if every metric abstains the dimension abstains (`all_metrics_abstained`). Each rule
cites its **metric** source and its **threshold** source separately. `project-default` means the
standard names the measure but publishes no number, so the number is ours. Every rating input in
the `score` output carries `metric_citation`, `threshold_citation` and `source_tag` (`curated` for
every rule shipped in the package), and the HTML report shows them as links.

<!-- rating-rules:start -->
| Dimension | Metric | Rule | Weight | Metric cites | Threshold cites |
|---|---|---|---|---|---|
| `architecture` | `architecture_description_missing` | ≤ 0 | 10 | [ISO/IEC/IEEE 42010:2022 (architecture description)](https://www.iso.org/standard/74393.html) | [ISO/IEC/IEEE 42010:2022 (architecture description)](https://www.iso.org/standard/74393.html) |
| `architecture` | `decision_records_missing` | ≤ 0 | 10 | [ISO/IEC/IEEE 42010:2022 (architecture description)](https://www.iso.org/standard/74393.html) | [ISO/IEC/IEEE 42010:2022 (architecture description)](https://www.iso.org/standard/74393.html) |
| `architecture` | `top_level_import_cycles` | ≤ 0 | 40 | [Martin 1996, Granularity (Acyclic Dependencies Principle)](https://web.archive.org/web/2015/http://www.objectmentor.com/resources/articles/granularity.pdf) | [Martin 1996, Granularity (Acyclic Dependencies Principle)](https://web.archive.org/web/2015/http://www.objectmentor.com/resources/articles/granularity.pdf) |
| `architecture` | `layer_direction_violations` | ≤ 0 | 40 | [Martin 1997, Stability (Stable Dependencies Principle)](https://web.archive.org/web/2015/http://www.objectmentor.com/resources/articles/stability.pdf) | [Martin 1997, Stability (Stable Dependencies Principle)](https://web.archive.org/web/2015/http://www.objectmentor.com/resources/articles/stability.pdf) |
| `solution-fit` | — (no static rule: abstains as `no_static_rule`, rated only at the evaluate gate) | — | — | [ISO/IEC 25010:2023 (functional suitability)](https://www.iso.org/standard/78176.html) | — |
| `requirement-fidelity` | `requirements_doc_missing` | ≤ 0 | 10 | [ISO/IEC/IEEE 29148:2018 (requirements engineering, traceability)](https://www.iso.org/standard/72089.html) | [ISO/IEC/IEEE 29148:2018 (requirements engineering, traceability)](https://www.iso.org/standard/72089.html) |
| `requirement-fidelity` | `code_commits_with_docs_share` | ≥ 0.3 | 10 | [ISO/IEC/IEEE 26514:2022 (design and development of information for users)](https://www.iso.org/standard/77451.html) | project-default |
| `requirement-fidelity` | `routes_without_test_share` | ≤ 0.2 | 40 | [ISO/IEC/IEEE 29119-4:2021 (test techniques, coverage)](https://www.iso.org/standard/79430.html); [ISO/IEC/IEEE 29148:2018 (requirements engineering, traceability)](https://www.iso.org/standard/72089.html) | project-default |
| `requirement-fidelity` | `commits_with_issue_reference_share` | ≥ 0.5 | 20 | [ISO/IEC/IEEE 29148:2018 (requirements engineering, traceability)](https://www.iso.org/standard/72089.html) | project-default |
| `requirement-fidelity` | `requirement_items_traced_share` | ≥ 0.8 | 20 | [ISO/IEC/IEEE 29148:2018 (requirements engineering, traceability)](https://www.iso.org/standard/72089.html) | project-default |
| `code-quality` | `functions_over_ccn_10_share` | ≤ 0.1 | 25 | [McCabe 1976, A Complexity Measure](https://doi.org/10.1109/TSE.1976.233837); [ISO/IEC 5055:2021 (automated source code quality measures)](https://www.iso.org/standard/80623.html) | [NIST SP 500-235 (Watson & McCabe 1996)](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication500-235.pdf) |
| `code-quality` | `max_function_ccn` | ≤ 15 | 15 | [McCabe 1976, A Complexity Measure](https://doi.org/10.1109/TSE.1976.233837); [NIST SP 500-235 (Watson & McCabe 1996)](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication500-235.pdf) | [NIST SP 500-235 (15 with justification)](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication500-235.pdf) |
| `code-quality` | `lint_config_missing` | ≤ 0 | 10 | [ISO/IEC 5055:2021 (automated source code quality measures)](https://www.iso.org/standard/80623.html) | project-default |
| `code-quality` | `format_config_missing` | ≤ 0 | 10 | [ISO/IEC 5055:2021 (automated source code quality measures)](https://www.iso.org/standard/80623.html) | project-default |
| `code-quality` | `type_escapes_per_kloc` | ≤ 5 | 15 | [ISO/IEC 5055:2021 (automated source code quality measures)](https://www.iso.org/standard/80623.html) | project-default |
| `code-quality` | `todo_without_ticket_share` | ≤ 0.5 | 15 | [ISO/IEC 5055:2021 (automated source code quality measures)](https://www.iso.org/standard/80623.html) | project-default |
| `code-quality` | `strict_type_config_missing` | ≤ 0 | 10 | [ISO/IEC 5055:2021 (automated source code quality measures)](https://www.iso.org/standard/80623.html); [mypy configuration file, strict option](https://mypy.readthedocs.io/en/stable/config_file.html); [TypeScript TSConfig reference, strict](https://www.typescriptlang.org/tsconfig/#strict) | project-default |
| `security` | `redaction_hits_observed` | ≤ 0 | 35 | [CWE-798 Use of Hard-coded Credentials](https://cwe.mitre.org/data/definitions/798.html); [OWASP ASVS 5.0.0 V13.3.1 (secrets management)](https://github.com/OWASP/ASVS/blob/v5.0.0_release/5.0/docs_en/OWASP_Application_Security_Verification_Standard_5.0.0_en.json) | [OWASP ASVS 5.0.0 V13.3.1 (secrets management)](https://github.com/OWASP/ASVS/blob/v5.0.0_release/5.0/docs_en/OWASP_Application_Security_Verification_Standard_5.0.0_en.json) |
| `security` | `sink_hits_observed` | ≤ 0 | 35 | [CWE Top 25 (CWE-95, CWE-78, CWE-89)](https://cwe.mitre.org/top25/) | [CWE Top 25 (CWE-95, CWE-78, CWE-89)](https://cwe.mitre.org/top25/) |
| `security` | `lockfile_missing` | ≤ 0 | 15 | [OWASP ASVS 5.0.0 V15.1.2 (third-party component inventory)](https://github.com/OWASP/ASVS/blob/v5.0.0_release/5.0/docs_en/OWASP_Application_Security_Verification_Standard_5.0.0_en.json) | [OWASP ASVS 5.0.0 V15.1.2 (third-party component inventory)](https://github.com/OWASP/ASVS/blob/v5.0.0_release/5.0/docs_en/OWASP_Application_Security_Verification_Standard_5.0.0_en.json) |
| `security` | `cookie_flags_missing_observed` | ≤ 0 | 15 | [OWASP ASVS 5.0.0 V3.3 (cookie setup: V3.3.1 Secure, V3.3.2 SameSite, V3.3.4 HttpOnly)](https://github.com/OWASP/ASVS/blob/v5.0.0_release/5.0/docs_en/OWASP_Application_Security_Verification_Standard_5.0.0_en.json) | project-default |
| `test-strategy` | `source_files_without_covering_test_share` | ≤ 0.2 | 25 | [ISO/IEC/IEEE 29119-4:2021 (test techniques, coverage)](https://www.iso.org/standard/79430.html) | project-default |
| `test-strategy` | `assertion_density_per_test` | ≥ 1 | 20 | [Kudrjavets, Nagappan & Ball 2006, Assessing the Relationship between Software Assertions and Faults](https://doi.org/10.1109/ISSRE.2006.13) | project-default |
| `test-strategy` | `test_config_and_ci_missing` | ≤ 0 | 20 | [ISO/IEC/IEEE 29119-2:2021 (test processes, test environment)](https://www.iso.org/standard/79428.html) | project-default |
| `test-strategy` | `tests_without_assertions_share` | ≤ 0.1 | 15 | [ISO/IEC/IEEE 29119-4:2021 (test techniques, coverage)](https://www.iso.org/standard/79430.html); [Kudrjavets, Nagappan & Ball 2006, Assessing the Relationship between Software Assertions and Faults](https://doi.org/10.1109/ISSRE.2006.13) | project-default |
| `test-strategy` | `skipped_test_share` | ≤ 0.05 | 10 | [ISO/IEC/IEEE 29119-2:2021 (test processes, test environment)](https://www.iso.org/standard/79428.html) | project-default |
| `test-strategy` | `network_calls_in_unit_tests_observed` | ≤ 0 | 10 | [ISO/IEC/IEEE 29119-2:2021 (test processes, test environment)](https://www.iso.org/standard/79428.html) | project-default |
| `blast-radius` | `max_fan_in_changed` | ≤ 20 | 35 | [Henry & Kafura 1981, Software Structure Metrics Based on Information Flow](https://doi.org/10.1109/TSE.1981.231113) | project-default |
| `blast-radius` | `changed_files_in_churn_hotspots_share` | ≤ 0.2 | 35 | [Nagappan & Ball 2005, Use of Relative Code Churn Measures to Predict System Defect Density](https://doi.org/10.1145/1062455.1062514) | project-default |
| `blast-radius` | `public_symbols_removed` | ≤ 0 | 15 | [Semantic Versioning 2.0.0 (backward-incompatible public API changes)](https://semver.org/spec/v2.0.0.html) | project-default |
| `blast-radius` | `destructive_migration_ops` | ≤ 0 | 15 | [Semantic Versioning 2.0.0 (backward-incompatible public API changes)](https://semver.org/spec/v2.0.0.html); [Fowler, Parallel Change (expand and contract)](https://martinfowler.com/bliki/ParallelChange.html) | project-default |
| `blast-radius` | `high_reach_files_without_test_share` | ≤ 0.2 | 50 | [Henry & Kafura 1981, Software Structure Metrics Based on Information Flow](https://doi.org/10.1109/TSE.1981.231113); [ISO/IEC/IEEE 29119-4:2021 (test techniques, coverage)](https://www.iso.org/standard/79430.html) | project-default |
| `blast-radius` | `high_reach_churn_hotspot_share` | ≤ 0.3 | 50 | [Henry & Kafura 1981, Software Structure Metrics Based on Information Flow](https://doi.org/10.1109/TSE.1981.231113); [Nagappan & Ball 2005, Use of Relative Code Churn Measures to Predict System Defect Density](https://doi.org/10.1145/1062455.1062514) | project-default |
| `reliability` | `swallowed_errors_observed` | ≤ 0 | 35 | [CWE-390 Detection of Error Condition Without Action](https://cwe.mitre.org/data/definitions/390.html); [CWE-1069 Empty Exception Block (an ISO/IEC 5055 reliability weakness)](https://cwe.mitre.org/data/definitions/1069.html); [ISO/IEC 5055:2021 (automated source code quality measures)](https://www.iso.org/standard/80623.html) | project-default |
| `reliability` | `outbound_calls_without_timeout_observed` | ≤ 0 | 35 | [CWE-400 Uncontrolled Resource Consumption](https://cwe.mitre.org/data/definitions/400.html); [Google SRE book, Addressing Cascading Failures (deadlines; retries with randomized exponential backoff)](https://sre.google/sre-book/addressing-cascading-failures/) | project-default |
| `reliability` | `retries_without_backoff_observed` | ≤ 0 | 10 | [Google SRE book, Addressing Cascading Failures (deadlines; retries with randomized exponential backoff)](https://sre.google/sre-book/addressing-cascading-failures/) | project-default |
| `reliability` | `queries_in_loops_observed` | ≤ 0 | 20 | [CWE-1050 Excessive Platform Resource Consumption within a Loop (an ISO/IEC 5055 performance efficiency weakness)](https://cwe.mitre.org/data/definitions/1050.html); [ISO/IEC 5055:2021 (automated source code quality measures)](https://www.iso.org/standard/80623.html) | project-default |
| `healthcare` | `phi_values_in_test_data_observed` | ≤ 0 | 50 | [HIPAA Privacy Rule 45 CFR §164.514(b)(2) de-identification (safe harbor: SSNs, medical record numbers and birth dates are identifiers)](https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-C/part-164/subpart-E/section-164.514) | [HIPAA Privacy Rule 45 CFR §164.514(b)(2) de-identification (safe harbor: SSNs, medical record numbers and birth dates are identifiers)](https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-C/part-164/subpart-E/section-164.514) |
| `healthcare` | `phi_values_in_log_statements_observed` | ≤ 0 | 50 | [HIPAA Privacy Rule 45 CFR §164.514(b)(2) de-identification (safe harbor: SSNs, medical record numbers and birth dates are identifiers)](https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-C/part-164/subpart-E/section-164.514) | [HIPAA Privacy Rule 45 CFR §164.514(b)(2) de-identification (safe harbor: SSNs, medical record numbers and birth dates are identifiers)](https://www.ecfr.gov/current/title-45/subtitle-A/subchapter-C/part-164/subpart-E/section-164.514) |
| `finance` | `float_money_observed` | ≤ 0 | 50 | [CWE-1339 Insufficient Precision or Accuracy of a Real Number](https://cwe.mitre.org/data/definitions/1339.html); [ISO/IEC 5055:2021 (automated source code quality measures)](https://www.iso.org/standard/80623.html); [PostgreSQL documentation, Numeric Types (numeric is recommended for monetary amounts; float types are inexact)](https://www.postgresql.org/docs/current/datatype-numeric.html) | project-default |
| `finance` | `ledger_tables_without_audit_columns_observed` | ≤ 0 | 25 | [NIST SP 800-53 Rev. 5 AU-3 Content of Audit Records (when the event occurred and the identity associated with it)](https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final); [SEC Rule 17a-4(f)(2)(i) (records kept with a time-stamped audit trail of every modification and deletion, or non-rewriteable and non-erasable)](https://www.ecfr.gov/current/title-17/chapter-II/part-240/section-240.17a-4) | project-default |
| `finance` | `ledger_rows_mutated_observed` | ≤ 0 | 25 | [SEC Rule 17a-4(f)(2)(i) (records kept with a time-stamped audit trail of every modification and deletion, or non-rewriteable and non-erasable)](https://www.ecfr.gov/current/title-17/chapter-II/part-240/section-240.17a-4); [Fowler, Reversal Adjustment (an accounting entry is corrected by a reversing entry, not edited)](https://martinfowler.com/eaaDev/ReversalAdjustment.html) | project-default |
| `frontend-a11y` | `images_without_alt_observed` | ≤ 0 | 25 | [WCAG 2.2 SC 1.1.1 Non-text Content (Level A)](https://www.w3.org/WAI/WCAG22/Understanding/non-text-content.html) | [WCAG 2.2 Conformance Requirement 1 (every success criterion of the level is satisfied: one failure fails conformance)](https://www.w3.org/TR/WCAG22/#conformance-reqs) |
| `frontend-a11y` | `form_controls_without_label_observed` | ≤ 0 | 25 | [WCAG 2.2 SC 1.3.1 Info and Relationships (Level A)](https://www.w3.org/WAI/WCAG22/Understanding/info-and-relationships.html); [WCAG 2.2 SC 4.1.2 Name, Role, Value (Level A)](https://www.w3.org/WAI/WCAG22/Understanding/name-role-value.html) | [WCAG 2.2 Conformance Requirement 1 (every success criterion of the level is satisfied: one failure fails conformance)](https://www.w3.org/TR/WCAG22/#conformance-reqs) |
| `frontend-a11y` | `aria_hidden_focusable_observed` | ≤ 0 | 20 | [WCAG 2.2 SC 4.1.2 Name, Role, Value (Level A)](https://www.w3.org/WAI/WCAG22/Understanding/name-role-value.html); [W3C Using ARIA, fourth rule (do not use aria-hidden="true" on a focusable element)](https://www.w3.org/TR/using-aria/#4thrule) | [WCAG 2.2 Conformance Requirement 1 (every success criterion of the level is satisfied: one failure fails conformance)](https://www.w3.org/TR/WCAG22/#conformance-reqs) |
| `frontend-a11y` | `viewport_missing_or_zoom_disabled_observed` | ≤ 0 | 15 | [WCAG 2.2 SC 1.4.4 Resize Text (Level AA)](https://www.w3.org/WAI/WCAG22/Understanding/resize-text.html); [WCAG 2.2 SC 1.4.10 Reflow (Level AA)](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html) | [WCAG 2.2 Conformance Requirement 1 (every success criterion of the level is satisfied: one failure fails conformance)](https://www.w3.org/TR/WCAG22/#conformance-reqs) |
| `frontend-a11y` | `browser_support_declaration_missing` | ≤ 0 | 15 | [ISO/IEC 25010:2023 (compatibility; flexibility: adaptability to operational environments)](https://www.iso.org/standard/78176.html); [Browserslist (shared browser-target configuration read by Babel, Autoprefixer, ESLint and bundlers)](https://github.com/browserslist/browserslist) | project-default |
| `supply-chain` | `lockfile_missing` | ≤ 0 | 20 | [OpenSSF Scorecard, Pinned-Dependencies check](https://github.com/ossf/scorecard/blob/main/docs/checks.md#pinned-dependencies) | [OpenSSF Scorecard, Pinned-Dependencies check](https://github.com/ossf/scorecard/blob/main/docs/checks.md#pinned-dependencies) |
| `supply-chain` | `licence_file_missing` | ≤ 0 | 15 | [OpenSSF Scorecard, License check; SPDX license identifiers](https://github.com/ossf/scorecard/blob/main/docs/checks.md#license) | [OpenSSF Scorecard, License check; SPDX license identifiers](https://github.com/ossf/scorecard/blob/main/docs/checks.md#license) |
| `supply-chain` | `ci_actions_unpinned_share` | ≤ 0 | 20 | [OpenSSF Scorecard, Pinned-Dependencies check](https://github.com/ossf/scorecard/blob/main/docs/checks.md#pinned-dependencies) | [OpenSSF Scorecard, Pinned-Dependencies check](https://github.com/ossf/scorecard/blob/main/docs/checks.md#pinned-dependencies) |
| `supply-chain` | `ci_lockfile_install_missing` | ≤ 0 | 20 | [OpenSSF Scorecard, Pinned-Dependencies check](https://github.com/ossf/scorecard/blob/main/docs/checks.md#pinned-dependencies) | [OpenSSF Scorecard, Pinned-Dependencies check](https://github.com/ossf/scorecard/blob/main/docs/checks.md#pinned-dependencies) |
| `supply-chain` | `ci_provenance_step_missing` | ≤ 0 | 25 | [SLSA v1.0 (build track: provenance)](https://slsa.dev/spec/v1.0/levels); [CycloneDX specification overview; SPDX specification](https://cyclonedx.org/specification/overview/) | [SLSA v1.0 (build track: provenance)](https://slsa.dev/spec/v1.0/levels) |
| `api` | `api_spec_missing` | ≤ 0 | 30 | [OpenAPI Specification 3.1.0; GraphQL specification; Protocol Buffers language guide (proto3)](https://spec.openapis.org/oas/v3.1.0) | [OpenAPI Specification 3.1.0; GraphQL specification; Protocol Buffers language guide (proto3)](https://spec.openapis.org/oas/v3.1.0) |
| `api` | `api_version_missing` | ≤ 0 | 20 | [Google AIP-185 (API versioning)](https://google.aip.dev/185) | [Google AIP-185 (API versioning)](https://google.aip.dev/185) |
| `api` | `request_validation_missing` | ≤ 0 | 30 | [OWASP ASVS 4.0.3, V5 Validation, Sanitization and Encoding (V5.1 input validation)](https://github.com/OWASP/ASVS/blob/v4.0.3/4.0/en/0x13-V5-Validation-Sanitization-Encoding.md) | [OWASP Input Validation Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Input_Validation_Cheat_Sheet.html) |
| `api` | `breaking_api_changes_observed` | ≤ 0 | 20 | [Google AIP-180 (backwards compatibility)](https://google.aip.dev/180) | [Google AIP-180 (backwards compatibility)](https://google.aip.dev/180) |
| `data` | `migrations_missing` | ≤ 0 | 30 | [Fowler & Sadalage, Evolutionary Database Design (every database change is a migration)](https://martinfowler.com/articles/evodb.html) | [Fowler & Sadalage, Evolutionary Database Design (every database change is a migration)](https://martinfowler.com/articles/evodb.html) |
| `data` | `migrations_without_rollback_share` | ≤ 0 | 30 | [Rails Guides, Active Record Migrations (reversible change; up/down methods)](https://guides.rubyonrails.org/active_record_migrations.html); [Liquibase, Rollback (a rollback for every changeset)](https://docs.liquibase.com/workflows/liquibase-community/using-rollback.html) | [Liquibase, Rollback (a rollback for every changeset)](https://docs.liquibase.com/workflows/liquibase-community/using-rollback.html) |
| `data` | `schema_constraints_missing` | ≤ 0 | 20 | [ISO/IEC 5055:2021 (automated source code quality measures)](https://www.iso.org/standard/80623.html); [PostgreSQL documentation, 5.5 Constraints (NOT NULL, unique, foreign key)](https://www.postgresql.org/docs/current/ddl-constraints.html) | [ISO/IEC 5055:2021 (automated source code quality measures)](https://www.iso.org/standard/80623.html) |
| `data` | `destructive_migration_ops_observed` | ≤ 0 | 20 | [Fowler, Parallel Change (expand and contract)](https://martinfowler.com/bliki/ParallelChange.html); [Fowler & Sadalage, Evolutionary Database Design (every database change is a migration)](https://martinfowler.com/articles/evodb.html) | [Fowler, Parallel Change (expand and contract)](https://martinfowler.com/bliki/ParallelChange.html) |
| `operations` | `logging_library_missing` | ≤ 0 | 20 | [OpenTelemetry, Observability primer (logs, metrics and traces emitted by instrumented code)](https://opentelemetry.io/docs/concepts/observability-primer/); [Google SRE book, Monitoring Distributed Systems](https://sre.google/sre-book/monitoring-distributed-systems/) | [Google SRE book, Monitoring Distributed Systems](https://sre.google/sre-book/monitoring-distributed-systems/) |
| `operations` | `audit_log_writes_missing` | ≤ 0 | 10 | [NIST SP 800-53 Rev. 5 AU-2 Event Logging (identify the events the system logs for audit)](https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final); [OWASP Logging Cheat Sheet (which events to record; audit trails)](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html) | [NIST SP 800-53 Rev. 5 AU-2 Event Logging (identify the events the system logs for audit)](https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final) |
| `operations` | `codeowners_missing` | ≤ 0 | 20 | [GitHub Docs, About code owners](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners); [Google SRE book, The Evolving SRE Engagement Model (production readiness review: a named owner for each service)](https://sre.google/sre-book/evolving-sre-engagement-model/) | [Google SRE book, The Evolving SRE Engagement Model (production readiness review: a named owner for each service)](https://sre.google/sre-book/evolving-sre-engagement-model/) |
| `operations` | `agent_guardrails_missing` | ≤ 0 | 10 | [OWASP Top 10 for LLM Applications 2025, LLM06 Excessive Agency (constrain what an agent may do; human approval for high-impact actions)](https://genai.owasp.org/llmrisk/llm062025-excessive-agency/) | [OWASP Top 10 for LLM Applications 2025, LLM06 Excessive Agency (constrain what an agent may do; human approval for high-impact actions)](https://genai.owasp.org/llmrisk/llm062025-excessive-agency/) |
| `operations` | `agent_config_secrets_observed` | ≤ 0 | 20 | [OWASP Top 10 for LLM Applications 2025, LLM02 Sensitive Information Disclosure](https://genai.owasp.org/llmrisk/llm022025-sensitive-information-disclosure/); [OWASP ASVS 5.0.0 V13.3.1 (secrets management)](https://github.com/OWASP/ASVS/blob/v5.0.0_release/5.0/docs_en/OWASP_Application_Security_Verification_Standard_5.0.0_en.json) | [OWASP ASVS 5.0.0 V13.3.1 (secrets management)](https://github.com/OWASP/ASVS/blob/v5.0.0_release/5.0/docs_en/OWASP_Application_Security_Verification_Standard_5.0.0_en.json) |
| `operations` | `tool_version_pin_missing` | ≤ 0 | 10 | [The Twelve-Factor App, X. Dev/prod parity](https://12factor.net/dev-prod-parity) | [The Twelve-Factor App, X. Dev/prod parity](https://12factor.net/dev-prod-parity) |
| `operations` | `dev_environment_missing` | ≤ 0 | 10 | [The Twelve-Factor App, X. Dev/prod parity](https://12factor.net/dev-prod-parity); [Development Containers specification (devcontainer.json)](https://containers.dev/implementors/spec/) | [The Twelve-Factor App, X. Dev/prod parity](https://12factor.net/dev-prod-parity) |
| `infrastructure` | `iac_wildcard_iam_observed` | ≤ 0 | 20 | [AWS IAM User Guide, Security best practices (apply least-privilege permissions)](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html); [Kubernetes documentation, Role Based Access Control practices (avoid wildcards)](https://kubernetes.io/docs/concepts/security/rbac-good-practices/); [CIS Kubernetes Benchmark 5.1.3 (minimize wildcard use in Roles and ClusterRoles)](https://www.cisecurity.org/benchmark/kubernetes) | [CIS Amazon Web Services Foundations Benchmark (IAM: no full '*' administrative policies; networking: no 0.0.0.0/0 ingress; storage: encryption at rest)](https://www.cisecurity.org/benchmark/amazon_web_services) |
| `infrastructure` | `iac_open_ingress_observed` | ≤ 0 | 20 | [Amazon VPC User Guide, Security group rules](https://docs.aws.amazon.com/vpc/latest/userguide/vpc-security-group-rules.html) | [CIS Amazon Web Services Foundations Benchmark (IAM: no full '*' administrative policies; networking: no 0.0.0.0/0 ingress; storage: encryption at rest)](https://www.cisecurity.org/benchmark/amazon_web_services) |
| `infrastructure` | `iac_unencrypted_storage_observed` | ≤ 0 | 15 | [Amazon RDS User Guide, Encrypting Amazon RDS resources](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/Overview.Encryption.html) | [CIS Amazon Web Services Foundations Benchmark (IAM: no full '*' administrative policies; networking: no 0.0.0.0/0 ingress; storage: encryption at rest)](https://www.cisecurity.org/benchmark/amazon_web_services) |
| `infrastructure` | `terraform_locked_remote_state_missing` | ≤ 0 | 15 | [HashiCorp Terraform documentation, Backend block configuration](https://developer.hashicorp.com/terraform/language/backend); [HashiCorp Terraform documentation, State locking](https://developer.hashicorp.com/terraform/language/state/locking) | [HashiCorp Terraform documentation, State locking](https://developer.hashicorp.com/terraform/language/state/locking) |
| `infrastructure` | `terraform_environment_separation_missing` | ≤ 0 | 5 | [HashiCorp Terraform documentation, Workspaces (separate state per environment)](https://developer.hashicorp.com/terraform/language/state/workspaces) | [HashiCorp Terraform documentation, Workspaces (separate state per environment)](https://developer.hashicorp.com/terraform/language/state/workspaces) |
| `infrastructure` | `database_backup_unconfigured` | ≤ 0 | 15 | [AWS Well-Architected Reliability Pillar REL09-BP01/BP03 (identify and back up all data; perform data backup automatically)](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_backing_up_data_identified_backups_data.html) | [AWS Well-Architected Reliability Pillar REL09-BP01/BP03 (identify and back up all data; perform data backup automatically)](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_backing_up_data_identified_backups_data.html) |
| `infrastructure` | `database_ha_unconfigured` | ≤ 0 | 10 | [AWS Well-Architected Reliability Pillar REL10-BP01 (deploy the workload to multiple locations)](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_fault_isolation_multiaz_region_system.html) | [AWS Well-Architected Reliability Pillar REL10-BP01 (deploy the workload to multiple locations)](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_fault_isolation_multiaz_region_system.html) |
| `change-risk` | `bugfix_without_regression_test` | ≥ 1 | 25 | [ISO/IEC/IEEE 29119-2:2021 (test processes, test environment)](https://www.iso.org/standard/79428.html) | project-default |
| `change-risk` | `new_code_without_test_share` | ≤ 0.2 | 25 | [ISO/IEC/IEEE 29119-2:2021 (test processes, test environment)](https://www.iso.org/standard/79428.html) | project-default |
| `change-risk` | `refactor_tests_deleted` | ≤ 0 | 25 | [ISO/IEC/IEEE 29119-2:2021 (test processes, test environment)](https://www.iso.org/standard/79428.html) | project-default |
| `change-risk` | `refactor_uncovered_share` | ≤ 0.2 | 25 | [ISO/IEC/IEEE 29119-2:2021 (test processes, test environment)](https://www.iso.org/standard/79428.html) | project-default |
<!-- rating-rules:end -->

The `*_missing` metrics are 1 when the dimension's source role (for example `lint-config`) has no
file read, else 0. On a truncated pack an unfilled role abstains, because the budget may have
dropped the file. The requirement-fidelity metrics and `changed_files_in_churn_hotspots_share`
cannot be derived from a read-only pack, so they always abstain with a stated reason. A dimension
whose measured rules carry less than half of its declared rule weight abstains
(`insufficient_measured_weight`, DDR-0010); missing evidence is reported as a warning, never gated.

#### Source roles — any language, no configuration required

Each dimension seeks **source roles** rather than exact filenames: a `lockfile`, a
`requirements-doc`, a `ci-workflow`, a `test-file`, and so on. `list-dimensions` prints every
role with its glob patterns. Roles are filled in this order:

1. **Generic patterns**, which work in any language (`**/*.lock`, `**/test/**`, `**/*_test.*`,
   `.github/workflows/*.yml`, `docs/**/*requirement*.md`, …).
2. **Ecosystem pattern sets** for Python, JS/TS, Rust, and Java. Each is switched on when its
   manifest is present (`pyproject.toml`, `package.json`, `Cargo.toml`, `pom.xml`/`build.gradle*`)
   and can only add patterns. It never adds, removes, or exempts a role.
3. An optional **`.easy-verifier.toml`** in the target repository, which may only add globs to
   existing roles:

   ```toml
   [roles]
   requirements-doc = ["docs/specs/*.md"]
   lint-config = ["tools/lint/*.json"]
   ```

   The same file may switch on an optional pack (T047); a pack is never switched on any other way
   except an agent pick (`{"packs": ["healthcare"]}` in the agent-input document):

   ```toml
   packs = ["healthcare"]
   ```

   The healthcare pack rates PHI-shaped values in test data and log statements (area 9, values
   never shown) and checks retention, BAA, data classification and residency documents (areas 9
   and 28). The finance pack (`packs = ["finance"]`, T048) rates area 3: money-named fields
   declared as binary floating point (`amount: float`, `costPerUnit Float`, and TS/JS
   `price: number` only in entity, model, schema and migration files), and,
   only where a ledger, transaction or payment table or model is declared, ledger tables with no
   audit column and updates or deletes of ledger rows; with no ledger those two rules abstain.
   Whether a ledger is correct is judgment: its code is quoted for the agent, never rated. The
   frontend accessibility pack (`packs = ["frontend-a11y"]`, T049) rates area 19 from markup text
   (HTML, JSX/TSX, Vue, Svelte, Jinja, ERB; tests, stories and build output excluded): images
   without `alt` (`alt=""` is allowed), form controls without a label, `aria-label`,
   `aria-labelledby` or `title`, and `aria-hidden` on a focusable element (WCAG 2.2 SC 1.1.1,
   1.3.1, 4.1.2), HTML entry documents with no viewport or with zoom disabled (SC 1.4.4; a Next.js
   root layout or Nuxt config gets the framework's default viewport), and no declared browser
   support (browserslist, Babel `targets`, Vite `build.target`). A tag with a spread or template
   expression is listed as not verifiable, never counted as missing. An unknown pack name is a
   warning and is ignored. Without `packs`, output is unchanged.

   Any other key, an unknown role, a wrong type, an empty list, or an attempt to set a floor is a
   validation error that names the key (exit 2). Without the file, output is unchanged.
4. **Agent-input picks**, a JSON document of the form
   `{"picks": {"requirements-doc": ["notes/wants.md"]}}`. The CLI replays it with
   `--agent-input PATH` on `score` and `write-report`, and MCP takes it as the `agent_input`
   argument. Picks only add files. A pick that is absolute, escapes the repository, does not exist,
   is secret-bearing, sits under a vendor or build directory, or names an unknown role is rejected
   with a named error. The same document may carry `gate_evaluations`
   (`{"<dimension>": {"score": 0-100, "confidence": 0-1, "evidence_refs": ["path:1-9"]}}`),
   accepted only for a dimension at a hard gate (below).

   ```console
   easy-verifier score --repo /path/to/repo --agent-input agent-input.json
   ```

Coverage is *roles filled ÷ roles declared*. A role counts as filled only when one of its files
was actually read, and every role counts in every repository. Files under `node_modules`,
`target`, `dist`, `build`, `.venv`, `vendor`, and `.git` never fill a role. Each dimension's output
and HTML report carries a sources provenance line: `rules`, `rules + config`, or
`rules + agent picks (N files)`. Coverage and ratings are not comparable with v0.1.0, which counted
exact filenames.

**Hard gates (MCP `score` only).** The CLI never asks. Over MCP, `score` may return `needs_input`
with at most one of picks or gate evaluations per response, and at most two extra rounds:

1. `needs_input.picks`: some roles are unfilled but the repository has candidate files.
2. `needs_input.gate_evaluations`: a list of `{dimension, reason, evidence_refs, omitted}`. It is
   asked on the call that carries picks, or on the first call when nothing needs picking. A
   dimension is gated when its rules abstain `no_static_rule` (`abstained`; an abstention for
   missing evidence is a warning and never gated) or when a rule input's metric lies
   within ±10% of its threshold (`borderline: <metric>`; a threshold of 0 is never
   borderline). Only reference ids are listed, at most 20 per dimension.
3. `needs_input.reference` rides along with either question and adds no round. It lists only
   the registry fields the rules read that a language or framework in `detected_stack` lacks
   (`{language | framework + extends, field, why}`; frameworks are asked only test naming, test
   declarations, assertions and security sinks; optional fields never), at most 20 per call, languages first, plus
   an `omitted` count. Its fixed instructions: at most 2 lookups per field, official docs first,
   a clear https link; otherwise ask the user one question at a time with a recommended answer
   and submit it as `user-supplied`. Answers return as `registry_entries`.

A valid evaluation cites at least one ref from that dimension's pack. It blends into the rules
rating R with `w = 0.5 × confidence`, so `final = R·(1−w) + A·w`, rounded half up. If the rules
abstained, the agent's score stands alone, labelled `agent-rated`, and the abstention record is
kept beside it. The number is always shown with its parts, for example
`74 = rules 68 + agent 88 (w 0.30)`. The overall discloses how many dimensions were rule-rated,
blended, or agent-rated, and which abstained. An evaluation for an ungated dimension is rejected.
Outside a gate the agent changes no number. Findings assessments are never blended. `rationale`
may be sent but is never written to any output. Save the final `agent_input` and replay it with
`--agent-input` to reproduce the same result from the CLI.

`write-report` accepts findings from `--findings PATH`, or from stdin when the flag is omitted.
The named file takes precedence when both are supplied:

```console
easy-verifier write-report --repo /path/to/repo --findings findings.json
```

Validation failures exit 2, operational failures exit 3, errors stay on stderr, and only the JSON
result is written to stdout.

### MCP — stdio by default

The MCP adapter exposes the same dimensions, discovery, combined pack, `score`, and `write_report`
as MCP tools. The default transport is **stdio**, so there is no port and no server lifecycle to
manage: your MCP client starts the server on demand. Two HTTP opt-ins exist, and both bind to
`127.0.0.1` only: `--transport streamable-http` (one shared server at `/mcp`, port from
`EASY_VERIFIER_PORT`, default `8766`; see Docker below) and the legacy HTTP/SSE `--http`.

Setup for Claude Code, Claude Desktop, Cursor, and other clients:
[`docs/LOCAL_MCP_GUIDE.md`](docs/LOCAL_MCP_GUIDE.md).

How a scoring session runs, round by round (diagram):
[`docs/SCORING_FLOW.md`](docs/SCORING_FLOW.md).
The rules, thresholds, weights, and registry fields behind every rating:
[`docs/SCORING_RULES.md`](docs/SCORING_RULES.md).

### Docker — one shared scoring container

Start one container once; every repository points at it. It runs with pinned Python and MCP
versions as UID/GID `10001`, drops all capabilities, has a read-only root filesystem, and mounts
your repositories read-only. It keeps running across sessions and reboots
(`--restart unless-stopped`).

#### Quick start: pull and run

1. Pull the image:

   ```console
   docker pull temvar/easy-verifier-mcp:0.1.0
   ```

2. Create the reports and reference-registry directories, owned by the container's UID `10001`:

   ```console
   mkdir -p ~/.easy-verifier-reports ~/.easy-verifier-sot
   sudo chown 10001:10001 ~/.easy-verifier-reports ~/.easy-verifier-sot
   ```

3. Start it once. Replace both `/home/you/code` with the absolute parent directory of the
   repositories you want to score:

   ```console
   docker run -d --name easy-verifier --restart unless-stopped --init \
     --read-only --network host --cap-drop ALL \
     --security-opt no-new-privileges:true \
     --tmpfs /tmp:rw,noexec,nosuid,nodev,size=16m \
     -e EASY_VERIFIER_REPORTS_DIR=$HOME/.easy-verifier-reports \
     -e EASY_VERIFIER_SOT=/sot \
     -v /home/you/code:/home/you/code:ro \
     -v $HOME/.easy-verifier-reports:$HOME/.easy-verifier-reports \
     -v $HOME/.easy-verifier-sot:/sot \
     temvar/easy-verifier-mcp:0.1.0 --transport streamable-http
   ```

4. Register it from any repository (once per Claude config directory with `--scope user`):

   ```console
   claude mcp add --transport http easy-verifier http://127.0.0.1:8766/mcp
   ```

Then pass the repository's **absolute** path as the tool's `repo` argument (for example
`/home/you/code/my-service`). Reports go to `~/.easy-verifier-reports/<repo name>/`, never into
the repository. Stop it with `docker rm -f easy-verifier`; to upgrade, remove it, `docker pull`
again and rerun the same `docker run -d` command.

> **Exposure.** The server listens on `127.0.0.1:8766` only (the container uses `--network host`,
> so its loopback is the host's) and has no authentication: while it runs, **any local process**
> on this machine can read, read-only, the repositories under the mounted workspace through it,
> and write reports into the reports directory. Nothing is reachable from another machine. If that
> is not acceptable, use one container per session instead.

To build the same image from a clone instead, use the `scorer` service in `compose.yaml` (remove
a `docker run` container first with `docker rm -f easy-verifier`):

```console
docker compose build scorer
mkdir -p ~/.easy-verifier-reports && sudo chown 10001:10001 ~/.easy-verifier-reports
EASY_VERIFIER_WORKSPACE=/home/you/code docker compose up -d scorer
```

Stop it with `docker compose down scorer`; upgrade with `docker compose build scorer` and the same
`up -d scorer` command. Build from source in full, the alternative of one container per session
over stdio with no network at all (your MCP client runs `docker run -i` on demand), and
troubleshooting: [`docs/DOCKER_MCP_GUIDE.md`](docs/DOCKER_MCP_GUIDE.md).

### Final release gate

Run the repository's fail-closed release gate from a clean, published candidate:

```console
bash scripts/verify_release_gate.sh
```

The command runs the host integration suite, requires the container integration tests, runs the
container verifier, and emits the KPI summary only after those checks pass. A zero exit status is
required for release. Docker, MCP stdio, or another required boundary that is unavailable is
reported as `NOT VERIFIED` and causes a non-zero exit; skipped or historical output is not release
evidence. Record the exact commit, environment, command output, and any unavailable proof in
`tasks/TASK_REVIEW_T023.md`.

## Where reports go

Reports are written into the **evaluated repository's** `reports/` directory, never into this
repo's — even when the two happen to be the same checkout (as they will be if you point this tool
at itself). Nothing is overwritten; filenames are unique per scope and timestamp.

When `EASY_VERIFIER_REPORTS_DIR` is set to an absolute path (the shared Docker container sets it),
reports go to `$EASY_VERIFIER_REPORTS_DIR/<repo directory name>/` instead, the repository is not
touched, and `write_report` returns the report's absolute path.

Every report also gets a JSON score summary with the same base name (`evidence-report-<scope>-<UTC>.json`)
in the same directory, for programs that read scores over time. Keys: `schema_version` (1), `scope`,
`generated_at` (UTC), `overall` and per-dimension `dimensions[]` (`value`/`rating`, `abstained`,
`reason_code`). A withheld rating has a `null` value, never 0; no finding text or excerpts are included.

Each full all-dimension report includes a score panel with the rule-based rating, optional caller
assessment, divergence where both exist, and the cited metrics. A withheld rating is displayed as
an abstention with its coverage boundary, never as zero or a low score.

## Reading a report

A number counts declared rules met, weighted; it is not a judgment of quality. Before acting on one:

- **Overall** is the mean of the dimensions that produced a number. Abstentions are left out, so
  read it with its disclosure ("N of 9 dimensions contributed").
- **Trust** a dimension number as far as its evidence: coverage floor, at least 50% of its rule
  weight measured, a `sample: … files` label on large repositories, and any blended or agent-rated
  part shown beside it.
- **Warnings** ("What we couldn't measure") name what to add for a missing number; no agent can
  fill one in.
- **Improvement plan**: fix P0 (near miss) first, then P1, by recomputed `overall_gain`; P2 rules
  need evidence before they can be measured. Open the cited files first.

Full guide, with worked examples: [`docs/EVALUATION_GUIDE.md`](docs/EVALUATION_GUIDE.md).

## Documentation

| Doc | What it covers |
|---|---|
| [`docs/LOCAL_MCP_GUIDE.md`](docs/LOCAL_MCP_GUIDE.md) | Install locally and register the stdio MCP server with Claude Code, Claude Desktop, Cursor |
| [`docs/DOCKER_MCP_GUIDE.md`](docs/DOCKER_MCP_GUIDE.md) | Run the hardened container as an MCP server, one registration for every repository, troubleshooting |
| [`docs/SCORING_FLOW.md`](docs/SCORING_FLOW.md) | Round-by-round flow of an MCP scoring session (diagram) |
| [`docs/SCORING_RULES.md`](docs/SCORING_RULES.md) | Every rating rule: threshold, weight, coverage floor, registry fields read |
| [`docs/EVALUATION_GUIDE.md`](docs/EVALUATION_GUIDE.md) | What each part of a score or report means, when to trust a number, how to act on it |
| [`docs/AREA_COVERAGE.md`](docs/AREA_COVERAGE.md) | Which of the 32 evaluation areas have rules today, which rules, and which task adds the rest |
| [`docs/RELEASE_GUIDE.md`](docs/RELEASE_GUIDE.md) | Release process |

## License

See `LICENSE`.
