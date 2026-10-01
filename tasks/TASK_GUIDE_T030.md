# TASK_GUIDE — T030: Registry schema, loader, curated entries for 9 languages; discovery reads from it
**Date**: 2026-09-28
**Complexity Level**: C2
**Risk Level**: Medium
**Priority**: P0
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
7. Read `docs/ddr/0007-cited-reference-registry-and-reference-gate.md` and `BRAINSTORMING_LOG_reference-registry.md` (approved rule table, edge cases)

---

## Requirement (Pillar 1 — Adapt the requirement)

User (2026-09-28): the scoring needs a source of truth; "Do we make sure all of the pattern map with the language, or technicals we are work in". Decided: one cited registry (G1, B-path A), curated in the package for 9 languages (G6).

**Restated intent**:
> All language patterns used by discovery come from one data registry in which every field carries a citation link and a source tag; `core/roles.py` has no hard-coded ecosystem table left.

**Out of scope**:
- Metrics tables (T031)
- Local layer / `~/.easy-verifier-sot/` (T036)
- Frameworks beyond the merge rule (T037)
- Rules (T035)

**Requirement Refs**:
- FR-041: one registry, every field cited
- FR-042: curated layer, 9 languages
- FR-044 (merge half): framework entry only adds to its language entry
- FR-031/FR-032/FR-033 behaviour preserved

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [ ] Restated intent confirmed to match the user's request (by Supervisor / user — not the implementing agent)
- [ ] Domain terms align with `PROJECT_SPEC.md` glossary (`grill-with-docs` run if terminology was fuzzy)
- [ ] Every Acceptance Criterion below traces to a line in the Requirement
- [ ] All Requirement Refs exist in `PRD.md` and are fully covered by the Acceptance Criteria above

> An agent must NOT start implementing until this gate is checked. If anything here is unclear,
> STOP and ask the Supervisor (Karpathy: Think Before Coding).

---

## Dependencies & Reachability

**Depends on**: T029 — redaction must not rewrite citations/paths

**Entry point**: `load_registry`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | `registry/curated/<lang>.toml` exists for python, js-ts, rust, java, go, kotlin, csharp, ruby, php; every field is `{value, citation_url, source_tag="curated"}` with an `https://` link | one cited registry, 9 languages |
| 2 | `load_registry()` validates schema (bounded size, UTF-8, known fields) and rejects a bad entry with a warning, never a crash | robust loader |
| 3 | `core/roles.py` ECOSYSTEM_PATTERNS is removed; discovery reads the same patterns from the registry; all existing role/coverage tests pass unchanged for the 4 former languages | no second copy, behaviour preserved |
| 4 | A Go, Kotlin and C# fixture repo each fill `package-manifest`, `lint-config`, `test-config` roles via their registry entries | new languages covered |
| 5 | A framework entry merges add-only into its language (union, deterministic order); it cannot remove a pattern | FR-044 merge rule |

---

## Evaluation & Acceptance (How we know the agent worked correctly)

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | fixture Kotlin repo with `build.gradle.kts`, `detekt.yml` | roles filled from `kotlin.toml` | automated test |
| 2 | curated file with a field lacking `citation_url` | load fails that entry with a named warning | automated test |

### Verification Command (exact, runnable)

```bash
python -m pytest -q
python -m ruff check src tests
```

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T030.md`.

---

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T030.md`.

---

## UI / Design Acceptance Criteria

> N/A — pure backend task (no UI component). All three UI Evidence rows are ☐ N/A.

---

## Approach

**Pattern reference**: `core/roles.py` `load_repo_config` — bounded TOML reading (MAX_CONFIG_BYTES, glob limits, error line caps); reuse its limits

Data-first: define the entry schema once (dataclass), load curated TOML via `tomllib`, expose a pure lookup `patterns_for(role, languages)`. Language activation stays manifest-based (existing behaviour). Keep citations to official docs (e.g. Gradle, detekt, dotnet test) — no invented links.

---

## Edge Case Checklist

- [ ] Manifest shared by two ecosystems (e.g. `pyproject.toml` in a JS repo) — both activate, union patterns
- [ ] Case-sensitive globs preserved (`*Test.*` must not match `latest.json`)
- [ ] Registry file present but empty

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/core/registry.py` | new: schema + loader + lookup |
| `src/easy_verifier/registry/curated/*.toml` | new: 9 language entries |
| `src/easy_verifier/core/roles.py` | read ecosystem patterns from registry |
| `pyproject.toml` | package data for `registry/curated` |
| `tests/` | loader + per-language discovery tests |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| src/easy_verifier/core/metrics.py | T031 |
| src/easy_verifier/core/judge.py | T035 |
| GENERIC_PATTERNS semantics | FR-032 language-agnostic defaults stay |

---

## Test Plan

Unit tests for schema validation; parity tests proving the 4 former ecosystems discover identically; fixtures for Go/Kotlin/C#.

---

## Completion Checklist

- [ ] Implementation done
- [ ] Self-review: `Skill({ skill: "code-review" })` run
- [ ] Security review: `Skill({ skill: "security-review" })` run (Medium risk)
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T030.md`'s Evidence table (Hard-Stop Gate 5)
- [ ] `Skill({ skill: "verify" })` run — feature confirmed working at a real surface
- [ ] `memory/MEMORY.md` updated (if new patterns or feedback learned)
- [ ] Supervisor notified: task ready for Stage 4 review
