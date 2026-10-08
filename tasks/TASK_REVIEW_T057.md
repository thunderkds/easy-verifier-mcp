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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☐ pass / ☐ fail | [test file path(s) — required before Done] |
| Verification command run | ☐ pass / ☐ fail | [paste actual output] |
| Negative cases hold | ☐ pass / ☐ fail | |
| verify | ☐ pass / ☐ fail / ☐ N/A | [what was observed — must literally state "pass" or "fail" here too, e.g. "skill run, feature confirmed working — pass": the merge gate scans this Notes column for the word "pass", not just the Result column] |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☐ pass / ☐ fail | [what was reviewed vs. skipped, and why] |
| Full smoke suite still green (no regression) | ☐ pass / ☐ fail | |
| **UI: Visual regression (diff or verdict pasted)** | ☐ pass / ☐ fail / ☐ N/A | [screenshot path or LLM verdict — required for UI tasks, Hard-Stop Gate 6] |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☐ pass / ☐ fail / ☐ N/A | [method used + output] |
| **UI: Responsiveness at target viewports** | ☐ pass / ☐ fail / ☐ N/A | [viewports tested, any overflow findings] |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE** (captured 2026-10-08T04:44:59Z–04:45:46Z, worktree HEAD `85d018a`, no implementation change; runner `scratchpad/run.sh` = `PYTHONPATH=<worktree>/src <main>/.venv/bin/python -m easy_verifier.adapters.cli score --repo <repo> <args> </dev/null`, payload piped to `sha256sum`):

```
HEAD 85d018a
[2026-10-08T04:44:59Z] start coffee-project: score --repo /home/hungnguyenhuu/workspace/training/tien.nguyen/nestjs-training/coffee-shop-api --scope project
[2026-10-08T04:45:01Z] exit=0 07a085869ae70ac87c4f57078edca18151f4991a822fbda19d13021ee94373ce  coffee-project
[2026-10-08T04:45:02Z] start kitchd-project: score --repo /home/hungnguyenhuu/workspace/pets/hungnguyen111/kitchd --scope project
[2026-10-08T04:45:10Z] exit=0 4559d8b5c566e256f0e014f8214b909720afeb2a93836784f5dbf52aa0dd31d9  kitchd-project
[2026-10-08T04:45:10Z] start kitchd-changes: score --repo /home/hungnguyenhuu/workspace/pets/hungnguyen111/kitchd --scope changes --ref 6198efe~1..6198efe
[2026-10-08T04:45:12Z] exit=0 156331796876d0967581a6e84ba6415c51de4271931e7f02d2cb85e3e39f97a2  kitchd-changes
DONE
```

Determinism re-run (same commit, second pass):

```
[2026-10-08T04:45:35Z] exit=0 07a085869ae70ac87c4f57078edca18151f4991a822fbda19d13021ee94373ce  coffee-project
[2026-10-08T04:45:43Z] exit=0 4559d8b5c566e256f0e014f8214b909720afeb2a93836784f5dbf52aa0dd31d9  kitchd-project
[2026-10-08T04:45:46Z] exit=0 156331796876d0967581a6e84ba6415c51de4271931e7f02d2cb85e3e39f97a2  kitchd-changes
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
[2026-10-08T04:56:17Z] start coffee-project: score --repo /home/hungnguyenhuu/workspace/training/tien.nguyen/nestjs-training/coffee-shop-api --scope project
[2026-10-08T04:56:20Z] exit=0 07a085869ae70ac87c4f57078edca18151f4991a822fbda19d13021ee94373ce  coffee-project
[2026-10-08T04:56:20Z] start kitchd-project: score --repo /home/hungnguyenhuu/workspace/pets/hungnguyen111/kitchd --scope project
[2026-10-08T04:56:31Z] exit=0 4559d8b5c566e256f0e014f8214b909720afeb2a93836784f5dbf52aa0dd31d9  kitchd-project
[2026-10-08T04:56:31Z] start kitchd-changes: score --repo /home/hungnguyenhuu/workspace/pets/hungnguyen111/kitchd --scope changes --ref 6198efe~1..6198efe
[2026-10-08T04:56:34Z] exit=0 156331796876d0967581a6e84ba6415c51de4271931e7f02d2cb85e3e39f97a2  kitchd-changes
DONE
```

`cmp` of each BEFORE payload against its AFTER payload: `coffee-project identical`, `kitchd-project identical`, `kitchd-changes identical`. The changes range `6198efe~1..6198efe` adds `apps/api/prisma/migrations/20260714120000_add_user_is_active_and_invite_revoked/migration.sql`, which is non-destructive, so on real repos the destructive count is 0 both times. A destructive hit is covered only by the synthetic parity table in `tests/test_t057_migration_registry.py`.

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

**DELTA**: a user can add a migration directory name such as `dbchanges` through the local layer's `conventions.toml`, and every migration pattern a rule uses now carries a cited registry source. Scores and payloads on coffee-shop-api and kitchd are byte-identical.

**WITNESS**: [who ran it and when — derived from `memory/event-trace/Txxx.jsonl`, never the
implementing agent alone]
