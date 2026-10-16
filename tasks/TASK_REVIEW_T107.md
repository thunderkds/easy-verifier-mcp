# TASK_REVIEW — T107: change-risk slice 1

> Sibling of `tasks/TASK_GUIDE_T107.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t107_context_roles_repo_wide.py` (43 tests; 23 failed pre-fix — `assert 'vitest.config.ts' in ('src/app.js', 'src/app.js')`). Supervisor re-run: t107 + t008 + t044 + t100 → `81 passed in 10.27s` — pass |
| Verification command run | ☑ pass | `ruff check src tests` → `All checks passed!`; worktree clean — pass |
| Negative cases hold | ☑ pass | Empty/unresolved narrow scope still reads nothing (refusal tests t008/t009 green; agent sabotage: removing the empty-scope guard fails them); secret-bearing `credential-file` is not a context role; project scope short-circuits in `role_files_in_scope` — pass |
| verify | ☑ pass | Supervisor independent real-repo run 2026-10-16 11:49 UTC, node-monorepo `score --scope changes --ref 09be767d0`: `overall 85, contributors 5` (architecture 90, blast-radius 100, code-quality 100, security 100, supply-chain 35); was 97 with 3 contributors. No remaining abstention cites a context role outside the diff. AC4: project payloads raw-byte EQUAL on self/fullstack-ts/python-ml/node-monorepo (agent, `.local/t107/{before,after}`) — pass |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Reviewed the 13-file diff: `roles.py` (CONTEXT_ROLES, `role_files_in_scope`, `note_context_roles`) and the one-line probe change in 8 dimensions, the new tests, the 2 updated tests. code-review: P0/P1/P2 none; P3: the context note is a pack warning only, absent from the combined score JSON (agent note 3) — candidate for T108's payload work. Security (Medium): no new file class read — context roles are the same files project scope already reads, through the same redacting reader — pass |
| Full smoke suite still green (no regression) | ☑ pass | Agent, run alone: `2983 passed, 3 skipped in 565.54s (0:09:25)`, exit 0. Two pre-FR-078 expectations updated by Supervisor decision (t008 manifest-as-context, t044 api_spec_missing measured) — authorised spec change, see Notes — pass |
| **UI: Visual regression (diff or verdict pasted)** | ☑ N/A | No UI |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☑ N/A | No UI |
| **UI: Responsiveness at target viewports** | ☑ N/A | No UI |

---

## Demonstration

**BEFORE**: captured 2026-10-16T11:16:34Z–11:16:44Z on develop `29ef8fe` (no T107 code), py3.12 venv,
`python -m easy_verifier.adapters.cli score --repo <real-repos>/node-monorepo --scope changes --ref 09be767d0 < /dev/null`
(payload under the worktree's git-ignored `.local/t107/before/`; summary = overall + per-dimension rating/abstention,
with every `"not in the resolved … scope"` miss listed):

```
overall: 97 (3 of 13 rated: architecture, code-quality, blast-radius)
  api: ABSTAIN below_coverage_floor (coverage 0.0 / floor 0.25)
  architecture: 90
  blast-radius: 100
  code-quality: 100
  data: ABSTAIN below_coverage_floor (coverage 0.0 / floor 0.25)
  infrastructure: ABSTAIN below_coverage_floor (coverage 0.0 / floor 0.25)
      - container-config: not in the resolved changes scope
  operations: ABSTAIN below_coverage_floor (coverage 0.0 / floor 0.25)
      - dev-environment: not in the resolved changes scope
  reliability: ABSTAIN insufficient_measured_weight (coverage 0.25 / floor 0.25)
      - readme: not in the resolved scope
  requirement-fidelity: ABSTAIN below_coverage_floor (coverage 0.2 / floor 0.5)
  security: ABSTAIN below_coverage_floor (coverage 0.0 / floor 0.25)
      - package-manifest: not in the resolved changes scope
      - lockfile: not in the resolved changes scope
      - auth-code: not in the resolved changes scope
      - container-config: not in the resolved changes scope
      - ci-workflow: not in the resolved changes scope
  solution-fit: ABSTAIN no_static_rule (coverage 0.0 / floor 0.5)
  supply-chain: ABSTAIN below_coverage_floor (coverage 0.0 / floor 0.4)
      - package-manifest: not in the resolved changes scope
      - lockfile: not in the resolved changes scope
      - ci-workflow: not in the resolved changes scope
      - licence-file: not in the resolved changes scope
  test-strategy: ABSTAIN below_coverage_floor (coverage 0.0 / floor 0.2)
      - test-config: not in the resolved changes scope
      - test-file: not in the resolved changes scope
      - ci-workflow: not in the resolved changes scope
```

Note: requirement-fidelity's stated misses here are `requirements-doc`/`spec-doc` "not found: no file in the
repository matched", route handlers not found in the 1 in-scope source file, and "no in-scope test file" —
none is a context role outside the diff.

**AFTER**: captured 2026-10-16T11:34:26Z–11:34:42Z, same command, T107 working tree (uncommitted at run time;
code identical to the T107 commit):

```
overall: 85 (5 of 13 rated: architecture, code-quality, security, blast-radius, supply-chain)
  api: ABSTAIN below_coverage_floor (coverage 0.0 / floor 0.25)
  architecture: 90
  blast-radius: 100
  code-quality: 100
  data: ABSTAIN below_coverage_floor (coverage 0.0 / floor 0.25)
  infrastructure: ABSTAIN all_metrics_abstained (coverage 0.25 / floor 0.25)
  operations: ABSTAIN below_coverage_floor (coverage 0.0 / floor 0.25)
      - dev-environment: not in the resolved changes scope
  reliability: ABSTAIN insufficient_measured_weight (coverage 0.5 / floor 0.25)
  requirement-fidelity: ABSTAIN below_coverage_floor (coverage 0.2 / floor 0.5)
  security: 100
  solution-fit: ABSTAIN no_static_rule (coverage 0.0 / floor 0.5)
  supply-chain: 35
  test-strategy: ABSTAIN insufficient_measured_weight (coverage 0.5 / floor 0.2)
      - test-file: not in the resolved changes scope
```

The test-strategy pack (CLI `test-strategy`, same repo/ref) carries the AC3 note:
`Read as repository context at the changes scope, not as changed files: test-config, ci-workflow. …`

**DELTA**: every `"not in the resolved … scope"` miss for a context role is gone (security and supply-chain now
rate, test-strategy/reliability/infrastructure clear their coverage floor); the two remaining are measured or
non-FR-078 roles (`test-file`, `dev-environment`), and overall moves 97 → 85.

**WITNESS**: backend-developer agent (T107), 2026-10-16, py3.12 venv in the T107 worktree.

**AC4 (project scope, before 11:16Z vs after 11:34Z)** — raw payload bytes and the DDR-0005 normalization
(`tests/integration/test_adapter_parity.normalize`) both compared:

```
self: raw EQUAL (1145004 vs 1145004 bytes); normalized EQUAL
fullstack-ts: raw EQUAL (1866660 vs 1866660 bytes); normalized EQUAL
python-ml: raw EQUAL (1470414 vs 1470414 bytes); normalized EQUAL
node-monorepo: raw EQUAL (2264964 vs 2264964 bytes); normalized EQUAL
```

`self` = a clone of this repo pinned at develop `29ef8fe`, scored by the old and the new code (scoring the live
worktree would differ only because its own source changed).

---

## Notes (implementer, 2026-10-16)

- **Two existing test expectations changed — Supervisor-authorised spec change (FR-078), not a test fix.**
  Both passed on develop `29ef8fe` and encoded the pre-FR-078 behaviour:
  1. `tests/test_t008_security.py::test_changes_scope_reads_only_the_explicit_ref_file_set` → renamed
     `test_changes_scope_measures_only_the_ref_files_and_reads_manifest_as_context`: `requirements.txt`
     (package-manifest, outside the diff) is now read as context; `src/auth.py` stays the only code file read.
  2. `tests/test_t044_api.py::test_a_narrow_scope_never_reports_presence_as_missing` → renamed
     `test_a_narrow_scope_measures_the_repo_spec_and_abstains_on_validation`: `api_spec_missing` is a measured
     0 when the spec exists repo-wide (option a); `request_validation_missing` (code, scope-only) still abstains.
  Each carries a one-line `FR-078 / T107` comment.
- **Guide inaccuracy (AC5 "Before")**: the guide says requirement-fidelity abstained because context roles were
  "not in the resolved changes scope". The real BEFORE payload shows otherwise: its misses are
  `requirements-doc`/`spec-doc` "not found: no file in the repository matched", no route handler in the 1
  in-scope source file, and "no in-scope test file". It still abstains after T107, for those same reasons.
- Role mapping (licence-file counted as a project document; dev-environment, codeowners, agent-config,
  tool-version-pin, release-config, observability-config, schema-file, IaC roles, auth-code stay measured)
  and the empty-narrow-scope guard were accepted by the Supervisor as-is.
- Final verification: `pytest -q` (full suite, run alone) → `2983 passed, 3 skipped in 565.54s`;
  `ruff check src tests` → `All checks passed!`; T107 + t008 + t044 + adapter parity → `84 passed in 63.10s`.
