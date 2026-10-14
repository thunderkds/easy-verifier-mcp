"""T057: migration knowledge lives in cited registry fields (DDR-0007).

Directory names and SQL DDL tokens are language-agnostic ``conventions``
fields; the ORM migration-API pattern is a curated-only cited regular
expression. ``blast_radius`` and ``data`` read them from the registry and
match exactly as the pre-T057 engine constants did.
"""

from __future__ import annotations

import re

import pytest

from easy_verifier.core import registry as reg
from easy_verifier.dimensions import blast_radius, data

# The engine constant before T057 (blast_radius.py:713), kept verbatim here as
# the parity oracle.
OLD_DESTRUCTIVE = re.compile(
    r"\bdrop\s+(?:table|column|schema|database)\b"
    r"|\brename\s+(?:column|to)\b"
    r"|\b(?:drop|remove|delete|rename)_?(?:table|column|field|model)s?"
    r"(?:_?if_?exists)?\b"
    r"|\bdrop_?if_?exists\b",
    re.IGNORECASE,
)
OLD_DIRS = frozenset({"migrations", "migration", "migrate", "alembic", "changelog"})

FIELDS = ("migration_dirs", "destructive_migration_ddl", "destructive_migration_apis")

SAMPLES = (
    # SQL DDL, any case
    "DROP TABLE users;",
    "drop table users;",
    "  ALTER TABLE t DROP COLUMN email;",
    "DROP SCHEMA legacy CASCADE;",
    "DROP DATABASE old;",
    "ALTER TABLE t RENAME COLUMN a TO b;",
    "ALTER TABLE t RENAME TO t2;",
    "drop\ttable x",
    "Drop   Column y",
    # ORM APIs (Rails, Alembic, Django, Knex, Laravel, Sequelize, EF Core)
    "    drop_table :users",
    "    remove_column :users, :email",
    "    op.drop_table('users')",
    "    op.drop_column('users', 'email')",
    "        migrations.RemoveField(model_name='user', name='email'),",
    "        migrations.DeleteModel(name='User'),",
    "        migrations.RenameField('user', 'a', 'b'),",
    "  table.dropColumn('email');",
    "  table.renameColumn('a', 'b');",
    "  knex.schema.dropTableIfExists('users');",
    "  Schema::dropIfExists('users');",
    "  await queryInterface.removeColumn('users', 'email');",
    "  await queryInterface.dropTable('users');",
    "  migrationBuilder.DropColumn(name: \"Email\", table: \"Users\");",
    "  migrationBuilder.RenameTable(name: \"A\", newName: \"B\");",
    # *_if_exists and plural variants
    "    drop_table_if_exists :users",
    "    drop_if_exists :users",
    "    remove_columns :users, :a, :b",
    "    DELETE_MODELS_IFEXISTS",
    "    renametables",
    # negatives
    "CREATE TABLE users (id int);",
    "ALTER TABLE t ADD COLUMN email text;",
    "    add_column :users, :email, :string",
    "    dropdown = 1",
    "    drop_tables_list = []",
    "    tabledrop()",
    "    migrations.AddField(model_name='user', name='email'),",
    "    removed_columns = 3",
    "    -- a comment line is the caller's concern, not the matcher's",
    "",
)


def _group(pattern: re.Pattern[str], line: str) -> str | None:
    hit = pattern.search(line)
    return hit.group(0) if hit else None


# ---------------------------------------------------------------------------
# AC 1 / AC 2: the values live in cited curated registry fields
# ---------------------------------------------------------------------------


def test_engine_constants_are_gone():
    for name in ("MIGRATION_DIRS", "_DESTRUCTIVE"):
        assert not hasattr(blast_radius, name), name
        assert not hasattr(data, name), name


def test_curated_conventions_carry_the_cited_migration_fields():
    entry, warnings = reg.load_conventions()
    assert warnings == ()
    for field in FIELDS:
        assert field in reg.CONVENTION_FIELDS
        rows = entry.fields[field]
        assert rows, field
        for cited in rows:
            assert cited.source_tag == reg.CURATED
            assert cited.citation_url.startswith("https://")
    urls = " ".join(
        cited.citation_url for field in FIELDS for cited in entry.fields[field]
    )
    for framework in (
        "djangoproject.com",  # Django
        "rubyonrails.org",  # Rails
        "alembic.sqlalchemy.org",  # Alembic
        "knexjs.org",  # Knex
        "laravel.com",  # Laravel
        "sequelize.org",  # Sequelize
        "learn.microsoft.com",  # EF Core
        "flyway",  # Flyway
        "liquibase",  # Liquibase
        "golang-migrate",  # golang-migrate
        "prisma.io",  # Prisma
    ):
        assert framework in urls, framework


def test_migration_dirs_are_the_same_lowercase_names():
    dirs, _pattern = blast_radius.migration_patterns()
    assert dirs == OLD_DIRS
    assert all(name == name.lower() for name in dirs)


def test_regex_field_is_a_regex_field_and_ddl_is_a_token_field():
    assert "destructive_migration_apis" in reg._REGEX_FIELDS
    assert "destructive_migration_ddl" in reg._TOKEN_FIELDS


# ---------------------------------------------------------------------------
# AC 3: matching semantics preserved (parity with the old constant)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("line", SAMPLES)
def test_destructive_matcher_parity(line):
    _dirs, pattern = blast_radius.migration_patterns()
    assert _group(pattern, line) == _group(OLD_DESTRUCTIVE, line)


def test_parity_table_has_both_positives_and_negatives():
    positives = [s for s in SAMPLES if OLD_DESTRUCTIVE.search(s)]
    negatives = [s for s in SAMPLES if not OLD_DESTRUCTIVE.search(s)]
    assert len(positives) >= 25 and len(negatives) >= 8


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("db/migrate/20240101_drop_users.rb", True),
        ("app/Migrations/0002_auto.py", True),
        ("src/ALEMBIC/versions/abc.py", True),
        ("db/changelog/db.changelog-1.0.xml", True),
        ("prisma/migrations/2024_x/migration.sql", True),
        ("db/migration/V2__drop.sql", True),
        ("db/migration/U2__undo.sql", False),  # Flyway undo
        ("migrations/0001.down.sql", False),  # golang-migrate down
        ("src/migrations.py", False),  # a file, not a directory
        ("src/models/user.py", False),
    ],
)
def test_is_migration_parity(path, expected):
    assert blast_radius._is_migration(path) is expected


def test_destructive_ops_still_skip_comments_and_down_sections():
    item = {
        "path": "db/migrate/1_x.rb",
        "status": "added",
        "lines": [
            ("+", 1, "def up", 0),
            ("+", 2, "  # drop_table :old", 0),
            ("+", 3, "  drop_table :users", 0),
            ("+", 4, "def down", 0),
            ("+", 5, "  drop_table :other", 0),
        ],
    }
    ops = blast_radius._destructive_ops(item)
    assert [(n, why) for _p, n, _t, why in ops] == [
        (3, "drop_table in a new migration file")
    ]


# ---------------------------------------------------------------------------
# AC 6: the local layer extends directory names; AC 7 / amendment: the regex
# field is curated-only
# ---------------------------------------------------------------------------


def _local(tmp_path, monkeypatch, body: str) -> None:
    (tmp_path / "conventions.toml").write_text(body, encoding="utf-8")
    monkeypatch.setenv(reg.SOT_ENV, str(tmp_path))


def test_local_layer_adds_a_migration_directory(tmp_path, monkeypatch):
    assert not blast_radius._is_migration("db/dbchanges/0001_init.sql")
    _local(
        tmp_path,
        monkeypatch,
        '[[migration_dirs]]\nvalue = ["dbchanges"]\n'
        'citation_url = "https://example.com/our-db-conventions"\n'
        'source_tag = "user-supplied"\n',
    )
    dirs, _pattern = blast_radius.migration_patterns()
    assert "dbchanges" in dirs and OLD_DIRS <= dirs
    assert blast_radius._is_migration("db/dbchanges/0001_init.sql")
    assert blast_radius._is_migration("db/DBChanges/0001_init.sql")


def test_local_layer_cannot_add_to_the_regex_field(tmp_path, monkeypatch):
    _local(
        tmp_path,
        monkeypatch,
        '[[destructive_migration_apis]]\nvalue = ["(a+)+$"]\n'
        'citation_url = "https://example.com/x"\n'
        'source_tag = "user-supplied"\n',
    )
    entry, warnings = reg.layered_conventions()
    assert any("curated-only" in w for w in warnings), warnings
    values = [v for c in entry.fields["destructive_migration_apis"] for v in c.value]
    assert "(a+)+$" not in values
    assert all(c.source_tag == reg.CURATED for c in entry.fields[
        "destructive_migration_apis"
    ])
    _dirs, pattern = blast_radius.migration_patterns()
    assert "(a+)+$" not in pattern.pattern


def test_repo_config_cannot_add_to_the_regex_field():
    problem = reg.convention_value_problem("destructive_migration_apis", r"\bx\b")
    assert problem and "curated-only" in problem
    assert reg.convention_value_problem("migration_dirs", "dbchanges") is None


@pytest.mark.parametrize("bad", ["db/migrate", "Migrations", "a b", "*"])
def test_migration_dir_shape_is_a_plain_lowercase_name(bad):
    assert reg.convention_value_problem("migration_dirs", bad)


def test_curated_entry_missing_a_field_is_a_packaging_error(monkeypatch):
    entry, _w = reg.load_conventions()
    fields = dict(entry.fields)
    del fields["migration_dirs"]
    broken = reg.RegistryEntry(
        name=entry.name, extends=None, manifests=(), roles={}, fields=fields
    )
    monkeypatch.setattr(
        blast_radius, "layered_conventions", lambda: (broken, ())
    )
    with pytest.raises(ValueError, match="migration_dirs"):
        blast_radius.migration_patterns()
