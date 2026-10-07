# TASK_REVIEW — T045: New dimension: data (#4 data model, constraints, migrations)

> Sibling of `tasks/TASK_GUIDE_T045.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☒ pass / ☐ fail | `tests/test_t045_data.py` (18 tests): AC1 discovery + roles (`test_dimension_is_discoverable_with_purpose_and_three_roles`), role globs never match source (`test_schema_role_matches_schema_files_never_source_code`, `test_source_files_named_like_migrations_are_not_migrations`: `src/models/schema.ts`, `src/database/migration.service.ts`, `MigrationRunner.java`); AC2 four cited rules on area #4 weigh 100 + floor 0.25 (`test_four_rules_are_cited_on_area_4_and_weigh_100`); AC3 patterns in registry/generic layer, none in the module, migration knowledge shared with blast-radius by identity (`test_patterns_come_from_the_registry_and_generic_layer`); AC5 every rule met rates 100 / no roles abstains `below_coverage_floor` naming all three misses / library never 0; sabotage pairs per predicate; down-section and comment drops; golang-migrate + Flyway undo pairs, Django, Alembic env.py; Prisma without down; narrow-scope presence abstains; run-time CREATE TABLE; data script in migrations/ disclosed. `18 passed in 4.31s`. Sabotage (backend-developer): constraint predicate forced true -> 1 failed; rollback predicate forced true -> 2 failed; destructive predicate forced false -> 1 failed. |
| Verification command run | ☒ pass / ☐ fail | `COMPOSE_FILE=compose.yaml:<scratchpad>/compose.t045.yaml PYTHONPATH=src <main>/.venv/bin/python -m pytest -q` -> `2281 passed, 2 skipped in 340.05s (0:05:40)` (exit 0, after the t045 image build); `ruff check src tests` -> `All checks passed!` |
| Negative cases hold | ☒ pass / ☐ fail | none of the roles -> `below_coverage_floor` with `sources_missing` = migration files, schema-file, data models in source files; library -> all four metrics abstain (never 0); narrow scope -> `migrations_missing` abstains ("judged only under project scope"); sabotage pairs flip exactly one metric each |
| verify | ☐ pass / ☐ fail / ☐ N/A | [Supervisor / user: `verify` is user-invocation-only. Implementer drove CLI `score --scope project` on four real repos (table below) and `scripts/verify_container.sh` against `easy-verifier-mcp:t045`: `PASS: uid=10001, tools=12, ...` (the `tools=12` text is a stale hard-coded label; the exact 15-tool set check above it passed). Harness sabotage: same script against `easy-verifier-mcp:t044` -> `FAIL: tools/list did not return the expected tool set (missing=['data'], unexpected=[])`.] |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☐ pass / ☐ fail | [Supervisor. Affected set: new `dimensions/data.py`; `core/{judge,metrics,metric_tables,registry,roles,improve,report}.py` additive entries; nine curated TOMLs (new optional fields; `roles.schema-file` in ruby.toml only); docs/count pins; T068 snapshot (no existing rating or overall changed: overall 61 -> 61, only `data` added).] |
| Full smoke suite still green (no regression) | ☒ pass / ☐ fail | `2281 passed, 2 skipped` incl. `tests/integration/test_adapter_parity.py` + `test_redaction_proof.py` against the t045 image (`9 passed in 27.59s`) |
| **UI: Visual regression (diff or verdict pasted)** | ☐ pass / ☐ fail / ☒ N/A | pure backend task, no UI component |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☐ pass / ☐ fail / ☒ N/A | pure backend task, no UI component |
| **UI: Responsiveness at target viewports** | ☐ pass / ☐ fail / ☒ N/A | pure backend task, no UI component |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE** (captured by backend-developer at tip `e54712c`, before any T045 implementation commit; output abridged to dimension names):

```
$ date -u; PYTHONPATH=src .venv/bin/python -m easy_verifier.adapters.cli list-dimensions   # names only
Wed Oct  7 09:30:53 AM UTC 2026
api
architecture
blast-radius
code-quality
reliability
requirement-fidelity
security
solution-fit
supply-chain
test-strategy
```

Ten dimensions, no `data` entry.

**AFTER** (backend-developer, commit `ae9fb15`, same command, names only plus the data roles):

```
$ date -u; PYTHONPATH=src .venv/bin/python -m easy_verifier.adapters.cli list-dimensions   # names only
Wed Oct  7 10:16:55 AM UTC 2026
api
architecture
blast-radius
code-quality
data | migration files, schema-file, data models in source files
reliability
requirement-fidelity
security
solution-fit
supply-chain
test-strategy
```

**DELTA**: A user can now get a cited area-#4 rating (migrations present beside a schema, a rollback per migration, declared NOT NULL/unique/foreign-key constraints, destructive operations in up migrations) for any repository with migrations, schema files or data models, and an abstention naming every missing role for one without.

### Real repositories (CLI `score --repo <r> --scope project < /dev/null`, before = main checkout src at `e54712c`, after = worktree src)

| Repo | Roles found (coverage vs floor 0.25) | migrations_missing | without_rollback_share | constraints_missing | destructive_ops | data | Overall before -> after |
|---|---|---|---|---|---|---|---|
| coffee-shop-api | migration files, data models (0.67) | 0 (3 MikroORM migrations) | 0.0 (0 of 3) | 0 (8 of 9 files) | 0 | **100** | 77 -> 80 |
| kitchd | migration files, schema-file (0.67) | 0 (16 Prisma migration.sql) | 1.0 (16 of 16; Prisma Migrate writes no down) | 0 (15 of 17) | 0 | **70** | 55 -> 56 |
| ai-training | data models (0.33): `CREATE TABLE` in `src/core/rate_limit/postgres_store.py` | 1 | abstains (no migration) | 0 | abstains (no migration) | **40** (50% measured) | 66 -> 62 |
| bryony | data models (0.33): 55 mongoose schema files | 1 (4 `migrations/migrate-*.js` disclosed as not counted: one-off data scripts, no up section) | abstains | 0 (14 of 55) | abstains | **40** (50% measured) | 62 -> 59 |

First run abstained on ai-training (below floor) although it creates a table at run time: fixed in Stage 3 by counting SQL `CREATE TABLE` in source as data-model evidence (generic layer, cited). bryony's first derivation said "no migration file was found" while four files sat in `migrations/` directories: fixed by disclosing them as not counted.

### Known limitations

- Migration filenames with long digit runs are masked by redaction in `computed_from`/derivations (`src/migrations/Migr…****:6a429a46c56b.ts` on coffee). This is `core/redact.py`'s entropy detector (T029 territory); not changed here.
- The migration-directory definition is blast-radius's (`MIGRATION_DIRS`, T057 will move it): a source module in a directory named `migration/` (e.g. a NestJS `src/migration/` module) is a candidate, counted only if it has an up section.
- Django migrations are credited as reversible by `migrations.Migration`; a `RunPython` without `reverse_code` is not detected. Rails `def change` is credited the same way.
- `schema_constraints_missing` is repository-level (any constraint in any schema/migration/model file), not per table.
- `destructive_migration_ops_observed` counts every DROP/RENAME in up sections of all in-scope migrations, so the final contract step of a correct expand/contract also fails the rule; the lines are quoted for the calling agent.
- Prisma Migrate has no down migrations, so every Prisma repository fails the rollback rule (kitchd); that is the checklist's verdict, not a detection gap.
- `CREATE TABLE` is matched in raw source text, so prose containing the phrase in a source file would count as a data model.

**WITNESS**: [who ran it and when — derived from `memory/event-trace/T045.jsonl`, never the
implementing agent alone]
