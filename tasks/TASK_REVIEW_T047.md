# TASK_REVIEW — T047: Pack mechanism + healthcare pack (#9 PHI, #28 BAA/residency)

> Sibling of `tasks/TASK_GUIDE_T047.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☒ pass (implementer; reviewer to confirm) | `tests/test_t047_packs.py` — 26 tests: AC1 config/agent pick/unknown name/nothing-else-activates; AC2 cited rules, registry patterns, SSN fixture fails + redacted, placeholders (000-00-0000, 123-45-6789, 111-11-1111, 666-, 9xx-) not counted, log PHI (incl. this.logger/self.logger), doc rules present/missing; AC3 inactive pack leaves no trace, areas stay unruled; AC4 areas + disclosure, HTML report card with and without pack; replay byte-equal; CLI. `pytest -q tests/test_t047_packs.py` → `26 passed in 2.79s` |
| Verification command run | ☒ pass (implementer) | 2026-10-06T05:52:21Z `python -m pytest -q` → `2133 passed, 2 skipped in 234.98s` exit=0; `python -m ruff check src tests` → `All checks passed!` |
| Negative cases hold | ☒ pass (implementer) | unknown pack → note, ignored; `packs = "healthcare"` / agent `packs: "healthcare"` → validation error naming `packs`; no config → no healthcare anywhere in payload or report; log rule abstains with no log statement; `--repo .` config path (t026) |
| verify | ☒ pass | Supervisor 2026-10-06 on `bcc36b4`: scratch clone of the repo containing nest-api, `score --repo <clone>/nest-api --scope project < /dev/null` → no pack: overall 72, 11 areas measured, 17 without rule (= develop); with `packs = ["healthcare"]`: overall 77, 13 measured, 15 without rule, healthcare 100, disclosure ends "packs active: healthcare" — pass |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☒ pass | Supervisor code-review of `develop...feat/T047-packs-healthcare` (packs/, registry/packs/healthcare.toml, judge/score/roles/registry/metrics/report/gate wiring, tests) + adversarial PHI-masking probe. Found P1 `import easy_verifier.packs` circular import, P2 `DOB 1984-03-12` (space-only label) neither counted nor masked → could leak via a context line; both fixed test-first in `bcc36b4` and re-probed (`MRN [PHI ssn redacted] DOB [PHI dob redacted]`). Security: values never hashed (enumerable SSN space), excerpts masked, paths cited in redacted form — pass |
| Full smoke suite still green (no regression) | ☒ pass | Supervisor rerun on `bcc36b4`: `2136 passed, 2 skipped in 250.70s`; `ruff check src tests` → All checks passed — pass |
| **UI: Visual regression (diff or verdict pasted)** | ☒ N/A (pure backend; the report change adds no UI component, it renders the existing score card for one more slot) | [screenshot path or LLM verdict — required for UI tasks, Hard-Stop Gate 6] |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☒ N/A (pure backend; the report change adds no UI component, it renders the existing score card for one more slot) | [method used + output] |
| **UI: Responsiveness at target viewports** | ☒ N/A (pure backend; the report change adds no UI component, it renders the existing score card for one more slot) | [viewports tested, any overflow findings] |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE**: captured on develop f7994d3 (no T047 commit yet) against a scratch git repo with `tests/fixtures/patient.json` = `{"name": "Jane", "ssn": "<SSN-shaped value>"}`. With the pack configured the config is rejected; without the config, #9 ("PHI minimization, retention, test-data safety") and #28 ("Vendor, BAA, data classification, residency") are in `areas_without_rule`:

```text
2026-10-06T05:11:38Z
$ cat .easy-verifier.toml
packs = ["healthcare"]
$ python -m easy_verifier.adapters.cli score --repo <demo>
validation error: .easy-verifier.toml: 1 error(s): packs: unknown key; only [roles] and [conventions] are accepted, and they may only add paths to existing roles or patterns to conventions (no floors, rules or removals)
exit=2

2026-10-06T05:11:44Z
$ python -m easy_verifier.adapters.cli score --repo <demo without .easy-verifier.toml> | jq areas_without_rule
exit=0
.areas_without_rule ["Financial integrity & historical reconstruction", "Data model, constraints, migrations", "Transactions, concurrency, idempotency", "API contracts, validation, versioning", "PHI minimization, retention, test-data safety", "Infra security: IAM, networking, KMS, secrets", "Observability, auditing, SLOs, error budgets", "Accessibility, responsive UX, browser compat", "CI quality & reproducibility", "Artifact provenance, SBOM, signing, promotion, rollback", "Terraform state, environment, account, drift", "Database HA, backups, restore, DR", "Incident response, change mgmt, access review", "Configuration ownership & operational readiness", "Vendor, BAA, data classification, residency", "AI-assisted-development safety", "Developer experience & deterministic local setup"]
```

**AFTER**: same demo repo, same config, after commits 55d2396/c1c3267:

```text
2026-10-06T05:52:46Z
$ cat .easy-verifier.toml
packs = ["healthcare"]
$ python -m easy_verifier.adapters.cli score --repo <demo>   (summarised: healthcare rating, its metric, disclosure tail, #9/#28 in areas_without_rule)
exit=0
healthcare: rating 0 [('phi_values_in_test_data_observed', 1, 'fail', 'PHI minimization, retention, test-data safety')]
citation: HIPAA Privacy Rule 45 CFR §164.514(b)(2) de-identification (safe harbor: SSNs, medical record numbers and birth dates are identifiers)
1 PHI-shaped value(s) in 2 test-data file(s): tests/fixtures/patient.json:1 (ssn); matched
disclosure ends: mber is given); packs active: healthcare
#9 in areas_without_rule: False | #28: False
SSN-shaped value present in payload: False
```


**DELTA**: A repository can now enable the healthcare pack (`packs = ["healthcare"]` or `agent_input.packs`) and get a cited, redacted #9 PHI rating plus #28/#9 document checks in the score, the disclosure and the report; repositories that do not enable it are scored byte-for-byte as before.

**WITNESS**: Supervisor, 2026-10-06 — Stage 4 review + masking probe (2 findings fixed), full suite rerun (2136 passed), live nest-api pack/no-pack runs (72 → 77, healthcare 100). Weights 50/50 and floor 0.25 user-approved.


## Implementer notes (backend-developer, 2026-10-06)

**Real-repo proof** (scratch clones, originals untouched; `fin_runs.txt`):

```text
2026-10-06T05:35:55Z
branch nopack exit=0
develop nopack exit=0
$ cmp develop(f7994d3) vs branch no-pack payload
cmp: identical (1425093 bytes)
node-monorepo pack exit=0
nest-api nopack exit=0
nest-api pack exit=0
2026-10-06T05:36:41Z
```

| Repo | No pack | With pack | healthcare rating | Metrics |
|---|---|---|---|---|
| node-monorepo (`/tmp/claude-1000/t047-bry-clean`) | overall 67 (5 of 8), areas measured 12, without rule 17 | overall 73 (6 of 9), measured 14, without rule 15, disclosure "...; packs active: healthcare" | 100 (rules) | test data 0 in 40 test-data files; log statements 0 on 242 log lines of 200 source files (batch 1 of 6); all 4 documents missing |
| nest-api (`/tmp/claude-1000/t047-nest-api`) | overall 72 (5 of 8) | overall 77 (6 of 9) | 100 (rules) | test data 0 in 10 files; log statements 0 on 7 log lines of 85 source files; all 4 documents missing |

`cmp` develop f7994d3 `src` vs branch, both no-pack on the same clean node-monorepo clone: **identical (1425093 bytes)**.

**Defects found by the real-repo runs and fixed test-first:** (1) nest-api's log rule abstained although the repo logs via NestJS `this.logger.log(...)`; added a cited `this.logger` entry and `self.` prefix (test `test_class_held_logger_calls_count`). (2) nest-api with the pack exited 2: a migration file name redacts as a secret in `files_read`, so the metric cited a path the pack "never read"; pack citations and listed paths are now redacted like `files_read` (test `test_cited_paths_are_redacted_like_files_read`). Earlier: `compute_metrics` checked citations over a fixed-size slice (broke once a pack computes fewer metrics); `load_repo_packs` did not resolve `--repo .` (caught by t026).

**Design decision:** a pack's areas count as covered only in a run where the pack is active (`areas_without_rule(packs)`, derived from the run's own ratings). In other runs nothing measured #9/#28, and this is what keeps non-pack payloads byte-identical.

**Pending:** rule weights 50/50 are a proposal marked pending in `judge.py`; Supervisor obtaining user sign-off.

**Known limitations (accepted by Supervisor):** (a) a pack is picked over MCP via `agent_input.packs` (documented in the `score` tool description), not offered in `needs_input`, to avoid an extra round on every repo; (b) PHI in logs is matched on literal values only — logging a PHI field by name (`patient.ssn`) is not detected. Also: matched PHI values are masked as `[PHI <kind> redacted]` with no hash (SSN space ~10^9 is enumerable, so even a truncated SHA-256 would be reversible); assessments of findings cover dimensions only, not packs.
