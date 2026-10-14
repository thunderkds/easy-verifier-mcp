# TASK_REVIEW — T057: Migration knowledge into the registry

> Sibling of `tasks/TASK_GUIDE_T057.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t057_migration_registry.py` (63: 39-line parity table vs the old regex kept verbatim, `_is_migration` parity incl. `.down.`/`U2__`, comment/down skips, citations for 11 frameworks, AC 6 local `dbchanges`, curated-only refusal for local layer and `.easy-verifier.toml`, shape check, missing-field packaging error); sabotage run failed exactly the 4 targeted inputs. Supervisor re-run with T045 + T055 suites: `133 passed in 7.92s` |
| Verification command run | ☑ pass | `ruff check src tests` → `All checks passed!` (implementer) |
| Negative cases hold | ☑ pass | local `destructive_migration_apis` value refused ("curated-only"), never reaches the matcher; `.easy-verifier.toml` same; no T055 expectation edited; T045 identity assertion moved from deleted constants to `migration_patterns` (same intent, AC 1 consequence — accepted) |
| verify | ☑ pass | Supervisor 2026-10-08: fullstack-ts `--scope changes --ref 6198efe~1..6198efe` base 85d018a vs branch → both `156331796876d0967581a6e84ba6415c51de4271931e7f02d2cb85e3e39f97a2`; hit path: temp Rails repo migration with `drop_table`, `remove_column`, `DROP TABLE` → base and branch both `75af68e7…` (blast-radius `destructive_migration_ops` 3, data `destructive_migration_ops_observed` 3). Implementer: nest-api `07a08586…` and fullstack-ts `4559d8b5…` project-scope sha256 equal before/after — pass |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | reviewed `conventions.toml` rows, `core/registry.py` (`CONVENTION_FIELDS`, `_TOKEN_FIELDS`, `_REGEX_FIELDS`, `_CURATED_ONLY_FIELDS`, shape check), `blast_radius.migration_patterns/_is_migration/_destructive_ops/_read_diff`, `data.py` consumer, tests. AC 2 deviation (all three fields in `conventions.toml`, not language tomls) **accepted by Supervisor**: the matcher runs on every migration file regardless of language, and Liquibase XML has no language entry. Findings: P0 0 / P1 0 / **P2** `migration_patterns()` reads only curated + local layer, so after T078 a `.easy-verifier.toml` `migration_dirs` is not applied → follow-up T086 / P3 a local `conventions.toml` containing the curated-only field is dropped whole (existing malformed-entry rule) — documented. Security: regex field curated-only (no ReDoS path from a scanned repo or local layer); DDL tokens escaped by `token_regex` — clean |
| Full smoke suite still green (no regression) | ☑ pass | implementer: `2 failed, 2512 passed, 2 skipped in 384.48s` — the 2 known stale-image container tests only — pass |
| **UI: Visual regression (diff or verdict pasted)** | ☐ N/A | backend-only |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☐ N/A | backend-only |
| **UI: Responsiveness at target viewports** | ☐ N/A | backend-only |
| Repro loop | ☐ N/A | refactor task |
| Regression test | ☑ pass | T055/T045 suites unchanged and green; parity table pins old behaviour |
| Smoke suite | ☑ pass | real-repo sha256 equality (verify row) |
---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE** (captured 2026-10-08T04:44:59Z–04:45:46Z, worktree HEAD `85d018a`, no implementation change; runner `scratchpad/run.sh` = `PYTHONPATH=<worktree>/src <main>/.venv/bin/python -m easy_verifier.adapters.cli score --repo <repo> <args> </dev/null`, payload piped to `sha256sum`):

```
HEAD 85d018a
[2026-10-08T04:44:59Z] start nest-api-project: score --repo <real-repos>/nest-api --scope project
[2026-10-08T04:45:01Z] exit=0 07a085869ae70ac87c4f57078edca18151f4991a822fbda19d13021ee94373ce  nest-api-project
[2026-10-08T04:45:02Z] start fullstack-ts-project: score --repo <real-repos>/fullstack-ts --scope project
[2026-10-08T04:45:10Z] exit=0 4559d8b5c566e256f0e014f8214b909720afeb2a93836784f5dbf52aa0dd31d9  fullstack-ts-project
[2026-10-08T04:45:10Z] start fullstack-ts-changes: score --repo <real-repos>/fullstack-ts --scope changes --ref 6198efe~1..6198efe
[2026-10-08T04:45:12Z] exit=0 156331796876d0967581a6e84ba6415c51de4271931e7f02d2cb85e3e39f97a2  fullstack-ts-changes
DONE
```

Determinism re-run (same commit, second pass):

```
[2026-10-08T04:45:35Z] exit=0 07a085869ae70ac87c4f57078edca18151f4991a822fbda19d13021ee94373ce  nest-api-project
[2026-10-08T04:45:43Z] exit=0 4559d8b5c566e256f0e014f8214b909720afeb2a93836784f5dbf52aa0dd31d9  fullstack-ts-project
[2026-10-08T04:45:46Z] exit=0 156331796876d0967581a6e84ba6415c51de4271931e7f02d2cb85e3e39f97a2  fullstack-ts-changes
```

Verbatim constants as they exist before the change (`src/easy_verifier/dimensions/blast_radius.py:705-726`):

```python
MIGRATION_DIRS = frozenset(
    {"migrations", "migration", "migrate", "alembic", "changelog"}
)
"""Directory names (any case) that make a file a schema migration: Django,
Laravel, Prisma, Knex and golang-migrate ``migrations/``, Flyway
``db/migration/``, Rails ``db/migrate/``, Alembic ``alembic/``, Liquibase
``db/changelog/``."""

_DESTRUCTIVE = re.compile(
    r"\bdrop\s+(?:table|column|schema|database)\b"
    r"|\brename\s+(?:column|to)\b"
    r"|\b(?:drop|remove|delete|rename)_?(?:table|column|field|model)s?"
    r"(?:_?if_?exists)?\b"
    r"|\bdrop_?if_?exists\b",
    re.IGNORECASE,
)
"""SQL DDL (``DROP TABLE``/``COLUMN``, ``RENAME COLUMN``/``TO``) and the
migration APIs named after it: ``drop_table``/``remove_column`` (Rails,
Alembic), ``RemoveField``/``DeleteModel``/``RenameField`` (Django),
``dropColumn``/``renameColumn``/``dropIfExists`` (Knex, Laravel, Sequelize),
``DropColumn``/``RenameTable`` (EF Core)."""

```

**AFTER** (same runner, worktree HEAD `4f0fa82`, captured 2026-10-08T04:56:17Z–04:56:34Z):

```
HEAD 4f0fa82
[2026-10-08T04:56:17Z] start nest-api-project: score --repo <real-repos>/nest-api --scope project
[2026-10-08T04:56:20Z] exit=0 07a085869ae70ac87c4f57078edca18151f4991a822fbda19d13021ee94373ce  nest-api-project
[2026-10-08T04:56:20Z] start fullstack-ts-project: score --repo <real-repos>/fullstack-ts --scope project
[2026-10-08T04:56:31Z] exit=0 4559d8b5c566e256f0e014f8214b909720afeb2a93836784f5dbf52aa0dd31d9  fullstack-ts-project
[2026-10-08T04:56:31Z] start fullstack-ts-changes: score --repo <real-repos>/fullstack-ts --scope changes --ref 6198efe~1..6198efe
[2026-10-08T04:56:34Z] exit=0 156331796876d0967581a6e84ba6415c51de4271931e7f02d2cb85e3e39f97a2  fullstack-ts-changes
DONE
```

`cmp` of each BEFORE payload against its AFTER payload: `nest-api-project identical`, `fullstack-ts-project identical`, `fullstack-ts-changes identical`. The changes range `6198efe~1..6198efe` adds `apps/api/prisma/migrations/20260714120000_add_user_is_active_and_invite_revoked/migration.sql`, which is non-destructive, so on real repos the destructive count is 0 both times. A destructive hit is covered only by the synthetic parity table in `tests/test_t057_migration_registry.py`.

The engine constants were replaced by registry data in `src/easy_verifier/registry/curated/conventions.toml` (`migration_dirs` 9 cited rows, `destructive_migration_ddl` 5 cited rows, `destructive_migration_apis` 8 cited rows holding the former ORM alternation verbatim), read by `blast_radius.migration_patterns()`:

```python
def migration_patterns() -> tuple[frozenset[str], re.Pattern[str]]:
    entry, _warnings = layered_conventions()
    missing = [f for f in MIGRATION_FIELDS if not convention_values(entry, f)]
    if missing:
        raise ValueError(f"conventions.toml: missing {', '.join(missing)}")
    dirs = frozenset(v.lower() for v in convention_values(entry, "migration_dirs"))
    ddl = [
        token_regex(t) for t in convention_values(entry, "destructive_migration_ddl")
    ]
    apis = list(convention_values(entry, "destructive_migration_apis"))
    return dirs, re.compile("|".join(ddl + apis), re.IGNORECASE)
```

Sabotage check (implementer): in a copy of the HEAD sources, the `"rename to"` token and the `\bdrop_?if_?exists\b` value were removed and `_is_migration` was hard-wired to the old names. The new suite then failed exactly on `RENAME TO t2`, `Schema::dropIfExists`, `drop_if_exists` and `test_local_layer_adds_a_migration_directory` (4 failed, 59 passed). Unmodified HEAD: 63 passed.

**DELTA**: a user can add a migration directory name such as `dbchanges` through the local layer's `conventions.toml`, and every migration pattern a rule uses now carries a cited registry source. Scores and payloads on nest-api and fullstack-ts are byte-identical.

**WITNESS**: Supervisor, 2026-10-08 — re-ran focused suites, compared fullstack-ts changes-scope and a synthetic destructive-migration repo between base 85d018a and the branch (byte-identical); trace attributed via active_task (`memory/event-trace/T057.jsonl`).
