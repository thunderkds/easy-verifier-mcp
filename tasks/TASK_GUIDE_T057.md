# TASK_GUIDE — T057: Move migration knowledge from `blast_radius.py` constants into cited registry fields
**Date**: 2026-10-08
**Complexity Level**: C2
**Risk Level**: Medium
**Priority**: P2
**Assigned agent**: backend-developer
**Agent guide**: `.claude/agents/backend.md`

---

## Mandatory Startup (Do Not Skip)

Before writing any code:
1. Read `PROJECT_SPEC.md`
2. Read `memory/MEMORY.md`
3. Read this file completely
4. Read `.claude/agents/backend.md`
5. Apply the C2 process from the Complexity matrix in `.claude/agents/general-agent-template.md`
6. Read `memory/codebase-map.md`
7. Read `docs/ddr/0007-cited-reference-registry-and-reference-gate.md` (every pattern a rule uses is cited registry data)
8. Read `memory/decisions.md` entry "T055 git-evidence areas" (2026-09-29: "migration knowledge stays in the engine for now … follow-up T057")

---

## Requirement (Pillar 1 — Adapt the requirement)

T055 (blast-radius #5) and later T045 (data dimension #4) recognise schema migrations with engine constants in `src/easy_verifier/dimensions/blast_radius.py`:
- `MIGRATION_DIRS` (line ~705): directory names `migrations`, `migration`, `migrate`, `alembic`, `changelog` (any case), used by `_is_migration` (~946).
- `_DESTRUCTIVE` (line ~713): one case-insensitive regex for SQL DDL (`DROP TABLE/COLUMN/SCHEMA/DATABASE`, `RENAME COLUMN/TO`) and ORM migration API names (Rails/Alembic `drop_table`/`remove_column`, Django `RemoveField`/`DeleteModel`/`RenameField`, Knex/Laravel/Sequelize `dropColumn`/`renameColumn`/`dropIfExists`, EF Core `DropColumn`/`RenameTable`).
- `data.py` imports `_DESTRUCTIVE` and `_is_migration` from there ("one copy until T057").

DDR-0007 requires every pattern a rule judges with to be cited registry data with a source tag, extendable by the local layer.

**Restated intent**:
> The migration directory names and destructive-operation patterns live in cited registry fields — language-agnostic ones (directory names, SQL DDL) in the curated `conventions` entry, ORM API names in each language's curated toml with a citation per framework — and `blast_radius.py` / `data.py` read them from the registry. Scores and payloads on real repos stay **byte-identical** (pure relocation), except that derivations may name the registry as the pattern source.

**Amendment (user, AskUserQuestion 2026-10-08 — AC 3 gate resolved, option D):** the ORM destructive-operation pattern moves as **cited regex values** (existing `_REGEX_FIELDS` field kind in `core/registry.py`), exact same alternation as today; SQL DDL rows as plain tokens compiled with `re.IGNORECASE` (precedent: `provenance_steps`, `metric_tables.py:216`); migration directory names as a plain lowercase list in `conventions`. The regex field is **curated-only**: the local layer may not add values to it (no ReDoS path into a core dimension); the local layer may add directory names (AC 6). `.down.`/Flyway `U<n>`, comment/down/up regexes stay in the engine.

**Out of scope**:
- Adding new migration frameworks or new destructive operations (relocation only; anything new is a separate task).
- Changing #5 / #4 weights, thresholds or metric names.
- Using `.easy-verifier.toml` conventions in scoring (T078, in parallel) — just make the new fields ordinary `conventions` / language fields so T078 picks them up.

**Requirement Refs**:
- FR-041…FR-049 (DDR-0007 cited registry), FR-043 (cited rules)

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [x] Restated intent confirmed (Supervisor 2026-10-08 from Kanban row + T055 decision; user approved this lane 2026-10-08 "continue")
- [x] Domain terms align with `PROJECT_SPEC.md` glossary
- [x] Every Acceptance Criterion below traces to a line in the Requirement
- [x] All Requirement Refs exist in `PRD.md`

---

## Dependencies & Reachability

**Depends on**: T055, T045 (merged)

**Entry point**: `_is_migration`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | `MIGRATION_DIRS` and `_DESTRUCTIVE` no longer exist as engine constants; the values live in registry fields with `citation_url` per framework (Django, Rails, Alembic, Knex, Laravel, Sequelize, EF Core, Flyway, Liquibase, golang-migrate, Prisma docs) and `source_tag = "curated"` | relocation |
| 2 | Language-agnostic data (directory names, SQL DDL) in `registry/curated/conventions.toml`; ORM API names in the matching language toml (python, ruby, js-ts, php, csharp) | placement |
| 3 | Matching semantics preserved: directory names any case; SQL DDL case-insensitive; API names as today (`drop_table`, `dropColumn`, `DropColumn`, `RemoveField`, `*_if_exists` variants). **First check whether the registry token syntax (`metric_tables.token_regex`) can express case-insensitive and `_?` variants; if not, STOP and report the options to the Supervisor before inventing a new pattern kind** | no behaviour change |
| 4 | Every existing T055/T045 test passes unchanged (do not edit expected values) | no regression |
| 5 | Real repos: `score` payload sha256 for coffee-shop-api and kitchd  identical BEFORE vs AFTER, plus one `--scope changes --ref <range>` run on a repo with a migration in the range | byte-identical |
| 6 | The local layer can add a migration directory name (a test proves an added name makes a file a migration) | extendable (DDR-0007) |
| 7 | The registry validator knows the new fields (shape checks, required-field counts updated; `required_fields()` result reported) | registry integrity |

---

## Evaluation & Acceptance (How we know the agent worked correctly)

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | existing T055/T045 suites | green, no expectation edits | automated |
| 2 | local-layer entry adds `dbchanges` dir | file under `dbchanges/` is a migration | automated |
| 3 | coffee/kitchd payloads | sha256 equal before/after | real-repo run |

### Verification Command (exact, runnable)

```bash
python -m pytest -q
python -m ruff check src tests
```

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T057.md`.

---

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T057.md`.

BEFORE (before any code change, timestamped): `score --repo <coffee-shop-api> --scope project </dev/null | sha256sum` and the same for kitchd (run in background, `</dev/null`), plus the verbatim current `MIGRATION_DIRS` / `_DESTRUCTIVE` source quoted from `blast_radius.py`.

---

## UI / Design Acceptance Criteria

> N/A — pure backend task. All three UI Evidence rows are ☐ N/A.

---

## Real repos

real repos: coffee-shop-api `/home/hungnguyenhuu/workspace/training/tien.nguyen/nestjs-training/coffee-shop-api`, kitchd `/home/hungnguyenhuu/workspace/pets/hungnguyen111/kitchd`, bryony `/home/hungnguyenhuu/workspace/project/bryony/bryony` (read-only, `--repo` only).

---

## Approach

**Pattern reference**: T073's `conventions.toml` fields + `structure.convention_values`; T045's `migration_rollback_markers` per-language field (`registry/curated/python.toml:511`). Add fields, a small helper that returns the migration-dir set and destructive matcher from the registry, and swap the two consumers to it.

---

## Edge Case Checklist

- [ ] `.down.` files and Flyway `U<n>` undo files still excluded
- [ ] Comment lines still ignored
- [ ] A language with no ORM rows still gets the SQL DDL rows
- [ ] The curated entry missing a new field is a packaging error (raise), like other curated fields

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/registry/curated/conventions.toml` + language tomls | new cited rows |
| `src/easy_verifier/core/registry.py` | field names, shapes |
| `src/easy_verifier/dimensions/blast_radius.py`, `dimensions/data.py` | read from the registry |
| `tests/test_t057_migration_registry.py` | new |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| `core/score.py`, `core/structure.py`, `dimensions/requirement_fidelity.py`, `dimensions/api.py` | T078 runs in parallel and owns convention threading |
| `packs/*` | unrelated |

---

## Test Plan

Unit: registry fields load and validate; matcher parity table (each old regex alternative ↔ new data) on a fixed list of sample lines (positive and negative). Existing T055/T045 suites unchanged. Real-repo sha256.

---

## Completion Checklist

- [ ] Implementation done
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T057.md` Evidence (Hard-Stop Gate 5)
- [ ] Real-repo sha256 equality pasted in Demonstration
- [ ] Supervisor notified: task ready for Stage 4 review
