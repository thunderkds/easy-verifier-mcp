# TASK_GUIDE — T026: Any-language source roles, `.easy-verifier.toml`, and agent-input picks replay
**Date**: 2026-09-26
**Complexity Level**: C3
**Risk Level**: High
**Priority**: P1
**Assigned agent**: backend-developer
**Agent guide**: `.claude/agents/backend.md`

---

## Mandatory Startup (Do Not Skip)

Before writing any code:
1. Read `PROJECT_SPEC.md`
2. Read `memory/MEMORY.md`
3. Read this file completely
4. Read `.claude/agents/backend.md`
5. Note the **Complexity Level** above and apply the matching process from the Complexity matrix in `.claude/agents/general-agent-template.md`
6. Read `memory/codebase-map.md`
7. Read `docs/ddr/0006-any-language-roles-and-agent-hard-gates.md`, `docs/ddr/0003-abstain-from-rating-below-coverage-floor.md`, `docs/ddr/0005-adapter-parity-is-byte-equality-after-declared-normalization.md`, `docs/ddr/0002-never-read-secret-bearing-files.md`
8. Read `BRAINSTORMING_LOG_source-discovery.md` (Option A is the approved path)

---

## Requirement (Pillar 1 — Adapt the requirement)

User (2026-09-26), after running the v0.1.0 image against kitchd, bryony and ai-training and seeing
2–5 of 7 dimensions abstain: "we scope the project in the language and the specific docs, not open
wide for flexible in any" → "this repo can evaluate any language with no boundary".

**Restated intent**:
> Every dimension seeks **source roles** instead of exact filenames. Roles are filled by
> language-agnostic patterns first, then by ecosystem pattern tables (Python, JS/TS, Rust, Java)
> auto-activated from manifests, then by the target's optional add-only `.easy-verifier.toml`, then
> by caller-supplied **picks** replayed from an agent-input document. Coverage becomes roles filled ÷
> roles declared, and every result says where its sources came from.

**Out of scope** (what this task explicitly does NOT do):
- Emitting `needs_input` / candidate lists (T027).
- Gate evaluations, blend, rating provenance, overall disclosure changes (T028). T026 must accept an
  agent-input document containing only `picks`; a `gate_evaluations` key is rejected as
  "not yet supported" until T028 lands.
- A Go ecosystem table (generic patterns only).
- Any model call (FR-040 / NFR-001).

**Requirement Refs**:
- FR-016 (amended): coverage over roles
- FR-022 (amended): parity with agent input as part of the input
- FR-031: roles declared as static data with patterns
- FR-032: language-agnostic defaults + ecosystem tables, never exempting a role
- FR-033: `.easy-verifier.toml`, add-only, unknown keys rejected
- FR-034: agent input `picks`, MCP argument + CLI `--agent-input PATH`, validated, CLI replays only
- FR-039 (sources half): per-dimension source provenance `rules` / `+ config` / `+ agent picks (N files)`
- NFR-005: no config file required; NFR-007: read-only outside `reports/`
- US-013, US-014, US-009

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [x] Restated intent confirmed to match the user's request (Supervisor, from Stage 0.5 grilling 2026-09-26)
- [x] Domain terms align with `PROJECT_SPEC.md` glossary (source role, ecosystem pattern set, agent input, picks — added 2026-09-26)
- [x] Every Acceptance Criterion below traces to a line in the Requirement
- [x] All Requirement Refs exist in `PRD.md` and are fully covered by the Acceptance Criteria

---

## Dependencies & Reachability

**Depends on**: None

**Entry point**: `score_repository`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | Every one of the 7 dimension descriptors declares `roles` (name + patterns) as static data; `sources_sought` equals the tuple of role names; `list-dimensions` output lists roles and their patterns. | FR-031, FR-013a |
| 2 | `coverage_score` = roles filled ÷ roles declared for **all seven** dimensions, including the bespoke `security`, `test-strategy`, `blast-radius` loops — not only `_doc_extract`. | FR-016 amended |
| 3 | A fixture repo in a language with **no** ecosystem table (e.g. an Elixir/Kotlin-shaped tree with `docs/specs/*.md`, `test/*_test.exs`, a `*.lock`, `.github/workflows/ci.yml`) fills roles via generic patterns and scores ≥1 dimension that abstains on `main` today. | FR-032, US-013 |
| 4 | A JS/TS pnpm-monorepo fixture (`package.json`, `pnpm-lock.yaml`, `eslint.config.js`, `vitest.config.ts`, `*.test.ts`) fills lint/lockfile/test-config/test-file roles via the JS/TS table; Python, Rust (`Cargo.toml`/`Cargo.lock`/`clippy.toml`), Java (`pom.xml` or `build.gradle*`, `src/test/java/**/*Test.java`) each have one fixture test. | FR-032 |
| 5 | No ecosystem table can add, remove or exempt a role — asserted by a test that the role-name set is identical with every table active vs. none. | FR-032, DDR-0006 |
| 6 | Files under excluded vendor/build dirs (`node_modules`, `target`, `dist`, `build`, `.venv`, `vendor`, `.git`) never fill a role. | Edge 1 |
| 7 | `.easy-verifier.toml` with `[roles] <role> = ["glob", …]` adds paths; absent file → output byte-identical to the no-config run; unknown key, unknown role, wrong type, or any attempt to set a floor / remove a role → `ValidationError` naming the key (CLI exit 2, MCP validation error). | FR-033, NFR-005 |
| 8 | `score` accepts agent input `{"picks": {role: [paths]}}` — MCP as `agent_input` argument, CLI as `--agent-input PATH`. Picks are additive. Rejected with a named error: absolute path, `..` escape, symlink resolving outside repo, non-existent file, unknown role, secret-bearing file (DDR-0002), and a `gate_evaluations` key (not yet supported). | FR-034 |
| 9 | A role matched only by a secret-bearing file is **not** filled; its miss reason is `excluded: secret-bearing`. | Edge 4, DDR-0002 |
| 10 | Each dimension in `score` output and in the HTML report carries a one-line source provenance: `rules`, `rules + config`, `rules + agent picks (N files)` (combinable). No agent text is rendered. | FR-039 |
| 11 | Adapter parity (`tests/integration/test_adapter_parity.py`) passes for (a) no agent input and (b) the same picks via MCP arg and CLI file, **without** adding a rule to the DDR-0005 normalization list. | FR-022 amended, DDR-0005 |
| 12 | Role resolution is deterministic (sorted) and bounded by a declared cap; hitting the cap sets explicit truncation, never a silent stop. | Edge 2, 3, NFR-009 |
| 13 | Existing test suite passes; every snapshot changed by the coverage-semantics change is updated in this task with the before/after coverage diff explained in the review Evidence. | Edge 11 |

---

## Evaluation & Acceptance (How we know the agent worked correctly)

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | Generic-language fixture, no config | ≥1 dimension rated that abstains on `develop` HEAD `6328455` | automated test |
| 2 | Real repo `kitchd` via Docker (rebuilt image) | Fewer abstentions than the 2026-09-26 baseline (code-quality, security abstained) | `verify` run, output pasted |
| 3 | `.easy-verifier.toml` with `coverage_floor = 0.1` | exit 2, message names `coverage_floor` | automated test |
| 4 | picks `{"lockfile": ["../etc/passwd"]}` | validation error naming the path | automated test |
| 5 | Same picks via CLI and MCP | byte-equal after DDR-0005 normalization | parity test |

### Verification Command (exact, runnable)

```bash
python -m pytest -q
python -m ruff check src tests
docker compose build && bash scripts/verify_container.sh
```

### Evidence (filled by reviewer at Stage 4/5)

> Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T026.md`.

---

## Demonstration

> See `tasks/TASK_REVIEW_T026.md`.

---

## Approach

**Pattern reference**: `src/easy_verifier/dimensions/code_quality.py` — static descriptor data + one
lazy `collect`; no base class, no registry. `src/easy_verifier/core/context.py` `read_sources` (glob
expansion) and `_EXCLUDED_DIRS` walk — reuse, do not write a new walker.
`src/easy_verifier/core/findings.py` — named, all-errors-at-once `ValidationError` style for TOML and
picks validation.

Option A from `BRAINSTORMING_LOG_source-discovery.md`:
- `SourceRole(name, patterns)` frozen dataclass in `core/models.py`; `DimensionDescriptor.roles`;
  `sources_sought` derived from role names so downstream shapes (`CoverageSummary`, FR-016a miss
  list, discovery) keep working.
- New `core/roles.py`: `GENERIC_PATTERNS`, `ECOSYSTEM_PATTERNS` (plain dict tables, activated by
  manifest presence), `load_repo_config()` via stdlib `tomllib`, `resolve(...)` producing a sorted,
  bounded `{role: files}` with per-file origin (`rules` / `config` / `pick`) for provenance.
- `core/pipeline.py`: count coverage by role.
- `core/score.py` + both adapters: thread `agent_input` (picks only in this task).
- Recommended TOML shape (lock it in the test):
  ```toml
  [roles]
  requirements-doc = ["docs/specs/*.md"]
  lint-config = ["tools/lint/*.json"]
  ```

---

## Edge Case Checklist

- [ ] Vendor/build dirs never fill a role (extend `_EXCLUDED_DIRS` only if a listed dir is missing)
- [ ] Role resolution bounded with explicit truncation on monorepos
- [ ] Deterministic ordering of resolved files and provenance
- [ ] Secret-bearing match → role not filled, reason `excluded: secret-bearing`
- [ ] Picks: absolute, `..`, symlink escape, missing file, unknown role, secret-bearing → named errors
- [ ] TOML: unknown key/role, wrong type, floor/removal attempts → named errors; absent file → no change
- [ ] Snapshot churn explained, not silently regenerated
- [ ] DDR-0005 normalization list unchanged — if parity needs a new rule, STOP and report

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/core/models.py` | `SourceRole`; `DimensionDescriptor.roles`; provenance field on pack/rating output |
| `src/easy_verifier/core/roles.py` (new) | generic + ecosystem tables, TOML loader, resolver, picks validation |
| `src/easy_verifier/core/pipeline.py` | role-based found/missing/coverage |
| `src/easy_verifier/core/context.py` | expose resolved role files to `collect` (minimal) |
| `src/easy_verifier/dimensions/*.py` | replace `SOURCES_SOUGHT` filenames with role data; bespoke loops iterate resolved role files |
| `src/easy_verifier/core/score.py` | `agent_input` parameter (picks) |
| `src/easy_verifier/core/report.py` | source provenance line |
| `src/easy_verifier/adapters/cli.py` | `--agent-input PATH` on `score` and `write-report` |
| `src/easy_verifier/adapters/mcp_server.py` | `agent_input` argument on `score` and `write_report` |
| `tests/…` + fixture repos | per AC |
| `README.md`, `docs/LOCAL_MCP_GUIDE.md`, `docs/DOCKER_MCP_GUIDE.md` | roles, TOML, `--agent-input` (doc-truth test `test_t018_readme.py` must stay green) |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| `src/easy_verifier/core/redact.py` | redaction policy is unchanged; reuse only |
| `src/easy_verifier/core/budget.py` | budget policy unchanged |
| `src/easy_verifier/core/findings.py` rules | reuse the validation style, do not fork or loosen it |
| `Dockerfile`, `compose.yaml` | hardening (`--network none`, read-only, non-root) stays |
| `src/easy_verifier/core/gate.py` | created by T027/T028, not here |

---

## Test Plan

Unit: role resolution per table, generic patterns, exclusions, TOML validation matrix, picks
validation matrix, coverage arithmetic by role. Integration: five fixture repos (generic, Python,
JS/TS monorepo, Rust, Java), adapter parity with and without picks, report provenance rendering.
Live: rebuilt Docker image against `kitchd` (read-only mount, `--user $(id -u):$(id -g)`) —
compare to the 2026-09-26 baseline.

---

## Completion Checklist

- [ ] Implementation done
- [ ] Self-review: `Skill({ skill: "code-review" })` run
- [ ] Security review: `Skill({ skill: "security-review" })` run (High risk — path validation surface)
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T026.md` Evidence (Hard-Stop Gate 5)
- [ ] `Skill({ skill: "verify" })` run — feature confirmed on the real CLI, MCP stdio and Docker image
- [ ] `memory/MEMORY.md` updated (if new patterns learned)
- [ ] Supervisor notified: task ready for Stage 4 review
