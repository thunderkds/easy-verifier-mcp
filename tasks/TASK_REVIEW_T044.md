# TASK_REVIEW — T044: New dimension: api (#7 API contracts, validation, versioning)

> Sibling of `tasks/TASK_GUIDE_T044.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t044_api.py` (18 tests): AC1 discovery + purpose + three roles; AC2 four rules on area #7, cited metric/threshold, weights sum 100; AC4 floor `CoverageFloor(0.25, "inclusive")` (also pinned in `tests/test_judge.py::test_floor_table_is_complete_static_data_and_matches_live_discovery`); AC5 all-met fixture rates 100 under changes scope (all four rules compute) and under project scope (breaking abstains), no-roles fixture abstains `below_coverage_floor` naming all three misses; edge cases: library (validation, no route/spec) abstains `all_metrics_abstained` never 0, spec generated from code credited with "generates one", narrow scope never reports presence as missing; sabotage pairs (each of spec / version / validation flipped alone flips exactly its metric); breaking change counts a removed `POST /v1/users` route and a renamed spec path (2); proto `package shop.v1;` counts; external URL, import path, `v1.2.3` and a versioned client URL outside route files do not count; AC3 spec role never matches source (`src/configs/swagger.config.ts`, `src/openapi.ts`, ...) and no framework literal in `dimensions/api.py`. `18 passed in 2.05s`. |
| Verification command run | ☑ pass | see "Full smoke suite" row for the full run; `python -m ruff check src tests` → `All checks passed!` |
| Negative cases hold | ☑ pass | no-roles abstain, library abstain, narrow-scope abstain, external/import/client-URL version strings rejected, spec role negative paths (all in the test file above). The client-URL test exists because the first real-repo run credited node-monorepo with versioning from `backend/platform/similarweb/services/base.js:36` (an outbound SimilarWeb URL); fixed by counting path literals only in route-declaring files. |
| verify | ☑ pass | Supervisor Stage 5, 2026-10-07 09:29 UTC, commit 519a4e8 — pass: list-dimensions → 10 dims incl. api; MCP tools/list → 14 tools incl. api; api on nest-api CLI vs MCP structuredContent identical (parity True), 37 excerpts, sources_missing ['api-spec']. Independent full-suite re-run (task image override): 2258 passed, 2 skipped in 238.55s; ruff All checks passed. The earlier one-off adapter-parity failure did not reproduce. |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Supervisor Stage 4 code-review over git diff 6dfab5f..HEAD (43 files): dimensions/api.py, core roles/metrics/metric_tables/registry/judge/improve/report, curated TOMLs, docs, tests. api-spec matcher probed against source paths (swagger.config.ts, openapi.ts, openapi.config.js, openapi.spec.ts → no match). P0/P1/P2 none. P3: api.py imports private helpers from requirement_fidelity/blast_radius (left as is). Weights 30/30/20/20 reviewed: cited, sum 100, accepted under user policy 2026-10-07. Security (manual): reads via read_source; regexes fixed patterns or token_regex; no findings. Known: node-monorepo abstains (no route tokens for webapp.get → T079; batch-1 sampling). |
| Full smoke suite still green (no regression) | ☐ pass / ☐ fail | [Supervisor to re-run] Implementer run: `cd <worktree> && COMPOSE_FILE=compose.yaml:<scratch>/compose.t044.yaml PYTHONPATH=src <main>/.venv/bin/python -m pytest -q` → `2258 passed, 2 skipped in 277.46s (0:04:37)`, exit 0 (image `easy-verifier-mcp:t044`, PyPI check 200 in 0.18s first). One earlier full run had a single failure in `tests/integration/test_adapter_parity.py::test_score_with_the_same_picks_matches_across_adapters` (overall/plan detail differed CLI vs MCP) while a concurrent CLI process was running; it passed 2/2 alone and in the clean run above. Not reproduced, flagged as possibly flaky. Without the override (stale shared `0.1.0` image) the container tests fail `missing=['api', 'supply-chain']`, as documented for T041. |
| **UI: Visual regression (diff or verdict pasted)** | ☐ N/A | pure backend task |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☐ N/A | pure backend task |
| **UI: Responsiveness at target viewports** | ☐ N/A | pure backend task |

### Weights (proposed by T044, accepted under user policy 2026-10-07; floor 0.25 user decision 2026-10-07)

| Metric | Weight | Threshold | Metric citation | Threshold citation | Rationale |
|---|---|---|---|---|---|
| `api_spec_missing` | 30 | ≤ 0 | OpenAPI 3.1.0 / GraphQL spec / proto3 guide | same | a machine-readable contract is the core of #7, measurable in every scope |
| `request_validation_missing` | 30 | ≤ 0 | OWASP ASVS 4.0.3 V5.1 | OWASP Input Validation Cheat Sheet | the other half of "contract and validation"; unvalidated input at an entry point |
| `api_version_missing` | 20 | ≤ 0 | Google AIP-185 | same | evolution control; an internal API may legitimately ship one version |
| `breaking_api_changes_observed` | 20 | ≤ 0 | Google AIP-180 | same | evolution control, measurable only on a changes-scope diff; abstains elsewhere leaving 80% measured (DDR-0010 floor 50%) |

First draft was 35/25/20/20; changed to 30/30/20/20 because no pass/fail/abstain combination of the first draft can rate exactly 50, which `tests/test_judge.py::_rating_with_value` (used by 7 overall tests) requires of every dimension.

### Real repositories (CLI `score --scope project`, before = main checkout `6dfab5f`, after = this branch)

| Repo | Roles found | Coverage vs 0.25 | spec | version | validation | breaking | api | Overall before → after |
|---|---|---|---|---|---|---|---|---|
| node-monorepo (Express) | none | 0.00 < 0.25 | abstain | abstain | abstain | abstain (project scope) | abstains `below_coverage_floor` | 62 → 62 |
| fullstack-ts (NestJS) | routes (57), validation (77 sites) | 0.67 | 1 (no spec file, no generator) | 1 | 0 | abstain | 38 | 57 → 55 |
| python-ml (FastAPI) | routes (5), validation (56 sites) | 0.67 | 0 (generated: `FastAPI(` src/api/main.py:37) | 1 | 0 | abstain | 75 | 64 → 66 |
| nest-api (NestJS) | routes, validation (33 sites) | 0.67 | 0 (generated: `SwaggerModule.createDocument` src/configs/swagger.config.ts:17) | 0 (`app.enableVersioning` src/main.ts:33) | 0 | abstain | 100 | 72 → 77 |

No other dimension's rating changed on any repo.

**node-monorepo abstention is a known defect with two causes outside this task's scope, proven by probe:** (1) node-monorepo routes are `webapp.get('/api/...')`, which no curated `route_tokens` value matches — that is Kanban **T079** (open, shared route tokens also drive requirement-fidelity); (2) node-monorepo has 1178 source files, so the default scan is priority batch 1 of 6 (200 files) and no router file is in it. Probe with T079-style tokens (`webapp.get(` etc.) monkeypatched: batch 1 still finds 0 routes; `--batches all` finds 15 routes (backend/server/dashboard/router.js:83, ...) and gives spec 1, version 1, validation 1 (no validation library) → api would rate 0. The miss reasons and abstentions now state the bound ("sample: batches 1 of 6, 200 of 1178 source files -- the rest were not scanned (--batches)").

### Known limitations

- `request_validation_missing` is repository level (any validation token beside routes), not per route.
- A version prefix set only in a file with no route (e.g. NestJS `setGlobalPrefix('api/v1')` in `main.ts`) is not seen: path literals count only in route-declaring files (to reject outbound client URLs). `enableVersioning` / `@Version` / DRF / ASP.NET versioning markers are seen.
- Breaking changes: a YAML/JSON/GraphQL key counts as removed only if no added line restores the same key at the same indentation in that file, so a removal masked by an unrelated same-named key re-added elsewhere is missed (under-reports, never over-reports).
- Narrow scopes: spec/version/validation absence abstains ("judged only under project scope"); a change touching only routes therefore usually abstains `insufficient_measured_weight`.
- Container image `easy-verifier-mcp:t044` (compose override) was built before the last commit's sample-note wording change, which the container tests do not exercise. The shared `0.1.0` tag was not touched.
- No documentation rule was added for #7: every part named in AC 2 is measured from code; contract conformance of a running service is stated as not verifiable offline in the purpose.

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE**: captured 2026-10-07 before any T044 implementation commit (tip 6dfab5f):

```
$ date -u; PYTHONPATH=src .venv/bin/python -m easy_verifier.adapters.cli list-dimensions
Wed Oct  7 08:42:36 AM UTC 2026
[ ...JSON abridged to the dimension names... ]
['architecture', 'blast-radius', 'code-quality', 'reliability', 'requirement-fidelity', 'security', 'solution-fit', 'supply-chain', 'test-strategy']
```

9 dimensions; no `api` entry.

**AFTER**: same command on this branch:

```
$ date -u; PYTHONPATH=src .venv/bin/python -m easy_verifier.adapters.cli list-dimensions
Wed Oct  7 09:12:45 AM UTC 2026
['api', 'architecture', 'blast-radius', 'code-quality', 'reliability', 'requirement-fidelity', 'security', 'solution-fit', 'supply-chain', 'test-strategy']
api purpose: Gather citable evidence about API contracts, request validation and versioning from specification files (OpenAPI, GraphQL, protobuf), route definitions and validation code in source files, and, for a change, the endpoints and specification fields it removes, without judging them; whether a running service honours its contract cannot be verified offline and is not examined.
api roles: [('api-spec', 22 patterns), ('route definitions in source files', 0), ('request validation in source files', 0)]
```

and `score --scope project` now rates `api` on real repositories: nest-api 100, python-ml 75, fullstack-ts 38, node-monorepo abstains (see Evidence).

**DELTA**: A user can now get a cited, rule-based rating of area #7 (API specification, versioning, request validation, and removed endpoints/fields in a change), with abstention instead of 0 for repositories that have no API.

**WITNESS**: Supervisor (independent of the implementer), 2026-10-07 09:29 UTC — re-ran list-dimensions, CLI+MCP api on nest-api, and the full suite from the main checkout with active_task=T044.
