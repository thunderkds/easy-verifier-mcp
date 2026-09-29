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
- **No writes outside the evaluated repo's `reports/` directory**, and never into this repo.
- **No outbound network requests.** Everything runs locally; secret values are redacted to a
  non-reversible fingerprint the moment they're read, never returned raw.

## The seven dimensions

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

Rate all seven dimensions in one call. The result includes every cited metric and an overall
disclosure naming which dimensions contributed or abstained:

```bash
python -m easy_verifier.adapters.cli score --repo . --scope project
```

Pass optional findings through `--findings PATH` or stdin to add the caller-derived assessments and
rating-to-assessment divergences to the same JSON output.

#### How each dimension is rated

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
| `architecture` | `architecture_description_missing` | ≤ 0 | 30 | [ISO/IEC/IEEE 42010:2022 (architecture description)](https://www.iso.org/standard/74393.html) | [ISO/IEC/IEEE 42010:2022 (architecture description)](https://www.iso.org/standard/74393.html) |
| `architecture` | `decision_records_missing` | ≤ 0 | 30 | [ISO/IEC/IEEE 42010:2022 (architecture description)](https://www.iso.org/standard/74393.html) | [ISO/IEC/IEEE 42010:2022 (architecture description)](https://www.iso.org/standard/74393.html) |
| `architecture` | `top_level_import_cycles` | ≤ 0 | 40 | [Martin 1996, Granularity (Acyclic Dependencies Principle)](https://web.archive.org/web/2015/http://www.objectmentor.com/resources/articles/granularity.pdf) | [Martin 1996, Granularity (Acyclic Dependencies Principle)](https://web.archive.org/web/2015/http://www.objectmentor.com/resources/articles/granularity.pdf) |
| `solution-fit` | — (no static rule: abstains as `no_static_rule`, rated only at the evaluate gate) | — | — | [ISO/IEC 25010:2023 (functional suitability)](https://www.iso.org/standard/78176.html) | — |
| `requirement-fidelity` | `acceptance_criteria_traced_to_code_share` | ≥ 0.8 | 35 | [ISO/IEC/IEEE 29148:2018 (requirements engineering, traceability)](https://www.iso.org/standard/72089.html) | project-default |
| `requirement-fidelity` | `acceptance_criteria_traced_to_test_share` | ≥ 0.8 | 35 | [ISO/IEC/IEEE 29148:2018 (requirements engineering, traceability)](https://www.iso.org/standard/72089.html) | project-default |
| `requirement-fidelity` | `requirements_docs_count` | ≤ 1 | 15 | [ISO/IEC/IEEE 26514:2022 (design and development of information for users)](https://www.iso.org/standard/77451.html); [ISO/IEC/IEEE 29148:2018 (requirements engineering, traceability)](https://www.iso.org/standard/72089.html) | project-default |
| `requirement-fidelity` | `code_commits_with_docs_share` | ≥ 0.3 | 15 | [ISO/IEC/IEEE 26514:2022 (design and development of information for users)](https://www.iso.org/standard/77451.html) | project-default |
| `code-quality` | `functions_over_ccn_10_share` | ≤ 0.1 | 30 | [McCabe 1976, A Complexity Measure](https://doi.org/10.1109/TSE.1976.233837); [ISO/IEC 5055:2021 (automated source code quality measures)](https://www.iso.org/standard/80623.html) | [NIST SP 500-235 (Watson & McCabe 1996)](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication500-235.pdf) |
| `code-quality` | `max_function_ccn` | ≤ 15 | 15 | [McCabe 1976, A Complexity Measure](https://doi.org/10.1109/TSE.1976.233837); [NIST SP 500-235 (Watson & McCabe 1996)](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication500-235.pdf) | [NIST SP 500-235 (15 with justification)](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication500-235.pdf) |
| `code-quality` | `lint_config_missing` | ≤ 0 | 15 | [ISO/IEC 5055:2021 (automated source code quality measures)](https://www.iso.org/standard/80623.html) | project-default |
| `code-quality` | `format_config_missing` | ≤ 0 | 10 | [ISO/IEC 5055:2021 (automated source code quality measures)](https://www.iso.org/standard/80623.html) | project-default |
| `code-quality` | `type_escapes_per_kloc` | ≤ 5 | 15 | [ISO/IEC 5055:2021 (automated source code quality measures)](https://www.iso.org/standard/80623.html) | project-default |
| `code-quality` | `todo_without_ticket_share` | ≤ 0.5 | 15 | [ISO/IEC 5055:2021 (automated source code quality measures)](https://www.iso.org/standard/80623.html) | project-default |
| `security` | `redaction_hits_observed` | ≤ 0 | 40 | [CWE-798 Use of Hard-coded Credentials](https://cwe.mitre.org/data/definitions/798.html); [OWASP ASVS 5.0.0 V13.3.1 (secrets management)](https://github.com/OWASP/ASVS/blob/v5.0.0_release/5.0/docs_en/OWASP_Application_Security_Verification_Standard_5.0.0_en.json) | [OWASP ASVS 5.0.0 V13.3.1 (secrets management)](https://github.com/OWASP/ASVS/blob/v5.0.0_release/5.0/docs_en/OWASP_Application_Security_Verification_Standard_5.0.0_en.json) |
| `security` | `sink_hits_observed` | ≤ 0 | 40 | [CWE Top 25 (CWE-95, CWE-78, CWE-89)](https://cwe.mitre.org/top25/) | [CWE Top 25 (CWE-95, CWE-78, CWE-89)](https://cwe.mitre.org/top25/) |
| `security` | `lockfile_missing` | ≤ 0 | 20 | [OWASP ASVS 5.0.0 V15.1.2 (third-party component inventory)](https://github.com/OWASP/ASVS/blob/v5.0.0_release/5.0/docs_en/OWASP_Application_Security_Verification_Standard_5.0.0_en.json) | [OWASP ASVS 5.0.0 V15.1.2 (third-party component inventory)](https://github.com/OWASP/ASVS/blob/v5.0.0_release/5.0/docs_en/OWASP_Application_Security_Verification_Standard_5.0.0_en.json) |
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
<!-- rating-rules:end -->

The `*_missing` metrics are 1 when the dimension's source role (for example `lint-config`) has no
file read, else 0. On a truncated pack an unfilled role abstains, because the budget may have
dropped the file. The requirement-fidelity metrics and `changed_files_in_churn_hotspots_share`
cannot be derived from a read-only pack, so they always abstain with a stated reason. That makes
requirement-fidelity and project-scope blast-radius abstain and go to the evaluate gate.

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
   dimension is gated when its rules abstain (`abstained`) or when a rule input's metric lies
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
manage: your MCP client starts the server on demand. An HTTP/SSE opt-in exists, and it binds to
`127.0.0.1` only.

Setup for Claude Code, Claude Desktop, Cursor, and other clients:
[`docs/LOCAL_MCP_GUIDE.md`](docs/LOCAL_MCP_GUIDE.md).

### Docker — read-only target, writable reports only

The container runs with pinned Python and MCP versions as UID/GID `10001`. It drops all
capabilities, has no network, publishes no ports, and mounts the target repository read-only.
Only `reports/` is writable. The target needs no package or executable installed.

```console
docker compose build
```

Registering the container with an MCP client, preparing `reports/`, and troubleshooting:
[`docs/DOCKER_MCP_GUIDE.md`](docs/DOCKER_MCP_GUIDE.md).

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

Each full seven-dimension report includes a score panel with the rule-based rating, optional caller
assessment, divergence where both exist, and the cited metrics. A withheld rating is displayed as
an abstention with its coverage boundary, never as zero or a low score.

## License

See `LICENSE`.
