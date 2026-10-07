"""T045: the ``data`` dimension (area #4 data model, constraints, migrations).

Each AC has a positive and a negative test; each rule predicate is flipped
alone (sabotage pairs), so a metric that cannot fail would be caught.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from easy_verifier.core.judge import (
    AREAS,
    COVERAGE_FLOORS,
    RATING_RULES,
    Citation,
    CoverageFloor,
)
from easy_verifier.core.metric_tables import DATA_FIELDS, curated_metric_tables
from easy_verifier.core.roles import GENERIC_DATA_FACTS, _matcher, role
from easy_verifier.core.score import score_repository
from easy_verifier.dimensions import DIMENSIONS, data, list_dimensions

ROLES = ("migration files", "schema-file", "data models in source files")
METRICS = (
    "migrations_missing",
    "migrations_without_rollback_share",
    "schema_constraints_missing",
    "destructive_migration_ops_observed",
)

MIGRATION = """import { Migration } from '@mikro-orm/migrations';

export class Migration20260101 extends Migration {
  async up(): Promise<void> {
    this.addSql('create table "user" ("id" serial primary key, '
      + '"email" varchar(255) not null);');
    this.addSql('alter table "user" add constraint "user_email_unique" '
      + 'unique ("email");');
  }

  async down(): Promise<void> {
    this.addSql('drop table if exists "user" cascade;');
  }
}
"""

ENTITY = """import { Entity, PrimaryKey, Property } from '@mikro-orm/core';

@Entity()
export class User {
  @PrimaryKey() id!: number;
  @Property() email!: string;
}
"""

GOOD = {
    "src/migrations/Migration20260101.ts": MIGRATION,
    "src/user.entity.ts": ENTITY,
    "package.json": '{"name": "shop"}\n',
}


def _repo(tmp_path: Path, files: dict[str, str]) -> Path:
    for relative, text in files.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return tmp_path


def _result(repo: Path, **kwargs) -> dict:
    scope = kwargs.pop("scope", "project")
    payload = json.loads(score_repository(repo, scope=scope, **kwargs).serialize())
    rating = next(r for r in payload["ratings"] if r["dimension"] == "data")
    metrics = {
        m["name"]: m for m in payload["metrics"]["metrics"] if m["dimension"] == "data"
    }
    return {"rating": rating, "metrics": metrics}


def _values(result: dict) -> dict:
    return {
        name: m["outcome"]["value"]
        if not m["outcome"].get("abstained")
        else m["outcome"]
        for name, m in result["metrics"].items()
    }


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.email=t@example.invalid", "-c", "user.name=t", *args],
        cwd=repo, check=True, capture_output=True,
    )


# ---------------------------------------------------------------------------
# AC 1 - discoverable, purpose and three source roles
# ---------------------------------------------------------------------------


def test_dimension_is_discoverable_with_purpose_and_three_roles() -> None:
    item = next(d for d in list_dimensions() if d.name == "data")
    assert item.purpose.endswith(".")
    assert "cannot be verified offline" in item.purpose
    for word in ("SQL", "Prisma", "Alembic", "Flyway", "Liquibase", "Rails"):
        assert word in item.purpose, word
    assert tuple(r.name for r in item.roles) == ROLES
    assert item.sources_sought == ROLES
    assert DIMENSIONS["data"] is data.DESCRIPTOR
    assert item.roles[1].patterns  # the schema role is a file role


def test_schema_role_matches_schema_files_never_source_code() -> None:
    match = _matcher(role("schema-file").patterns)
    for path in ("db/schema.sql", "prisma/schema.prisma", "sql/shop.schema.sql"):
        assert match(path), path
    for path in ("src/models/schema.ts", "src/schema/user.schema.ts",
                 "src/database/migration.service.ts", "app/schema.py",
                 "src/main/java/com/acme/MigrationRunner.java"):
        assert not match(path), path


def test_source_files_named_like_migrations_are_not_migrations(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path, {
        "src/database/migration.service.ts": "export class MigrationService {}\n",
        "src/main/java/com/acme/MigrationRunner.java": "class MigrationRunner {}\n",
        "src/models/schema.ts": "export const schema = {};\n",
    })
    rating = _result(repo)["rating"]
    assert rating["reason_code"] == "below_coverage_floor"
    assert [m["source"] for m in rating["sources_missing"]] == list(ROLES)


# ---------------------------------------------------------------------------
# AC 2 - four cited rules on area #4; floor 0.25 inclusive (user 2026-10-07)
# ---------------------------------------------------------------------------


def test_four_rules_are_cited_on_area_4_and_weigh_100() -> None:
    rules = RATING_RULES["data"]
    assert tuple(rules) == METRICS
    assert sum(rule.weight for rule in rules.values()) == 100
    assert {rule.area for rule in rules.values()} == {AREAS[3]}
    assert AREAS[3] == "Data model, constraints, migrations"
    for rule in rules.values():
        assert isinstance(rule.threshold_citation, Citation)
        assert rule.threshold_citation.url.startswith("https://")
        assert all(c.url.startswith("https://") for c in rule.metric_citation)
    assert "5055" in rules["schema_constraints_missing"].metric_citation[0].label
    assert COVERAGE_FLOORS["data"] == CoverageFloor(0.25, "inclusive")


# ---------------------------------------------------------------------------
# AC 5 - every rule met rates 100; none of the roles abstains with misses
# ---------------------------------------------------------------------------


def test_fixture_where_every_rule_is_met_rates_100(tmp_path: Path) -> None:
    result = _result(_repo(tmp_path, GOOD))
    rating = result["rating"]
    assert rating["kind"] != "rating_abstention", rating
    assert rating["value"] == 100
    inputs = {item["metric_name"]: item for item in rating["inputs"]}
    assert set(inputs) == set(METRICS)
    assert all(item["passed"] for item in inputs.values())
    values = _values(result)
    assert {name: values[name] for name in METRICS} == dict.fromkeys(METRICS, 0)


def test_repository_with_none_of_the_roles_abstains_naming_every_miss(
    tmp_path: Path,
) -> None:
    result = _result(_repo(tmp_path, {"notes.txt": "nothing relevant\n"}))
    rating = result["rating"]
    assert rating["kind"] == "rating_abstention"
    assert rating["reason_code"] == "below_coverage_floor"
    assert "value" not in rating
    assert [m["source"] for m in rating["sources_missing"]] == list(ROLES)


def test_library_without_a_database_is_never_rated_zero(tmp_path: Path) -> None:
    repo = _repo(tmp_path, {"src/util.ts": "export const add = (a: number) => a;\n"})
    values = _values(_result(repo))
    for name in METRICS:
        assert values[name].get("abstained"), name


# ---------------------------------------------------------------------------
# Sabotage pairs: each predicate flipped alone flips exactly its metric
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("files", "metric", "value"),
    [
        # ORM-managed schema without migration files (edge case).
        ({"src/user.entity.ts": ENTITY}, "migrations_missing", 1),
        (
            {**GOOD, "src/migrations/Migration20260101.ts": MIGRATION.split(
                "  async down()")[0] + "}\n"},
            "migrations_without_rollback_share", 1.0,
        ),
        (
            {**GOOD, "src/migrations/Migration20260101.ts": MIGRATION.replace(
                " not null", "").replace("'unique (", "'check (")},
            "schema_constraints_missing", 1,
        ),
        (
            {**GOOD, "src/migrations/Migration20260101.ts": MIGRATION.replace(
                "    this.addSql('alter", "    this.addSql('alter table \"user\" "
                "drop column \"name\";');\n    this.addSql('alter")},
            "destructive_migration_ops_observed", 1,
        ),
    ],
)
def test_each_predicate_flips_exactly_its_metric(
    tmp_path: Path, files: dict, metric: str, value: float
) -> None:
    values = _values(_result(_repo(tmp_path, files)))
    assert values[metric] == value
    good = _values(_result(_repo(tmp_path / "good", GOOD)))
    assert good[metric] == 0


def test_drop_in_a_down_section_or_comment_is_not_destructive(tmp_path: Path) -> None:
    head = "async up(): Promise<void> {"
    text = MIGRATION.replace(head, head + "\n    // drop table legacy later")
    files = {**GOOD, "src/migrations/Migration20260101.ts": text}
    values = _values(_result(_repo(tmp_path, files)))
    assert values["destructive_migration_ops_observed"] == 0


def test_rollback_sibling_files_and_framework_reversible_forms(tmp_path: Path) -> None:
    repo = _repo(tmp_path, {
        # golang-migrate pair
        "db/migrations/1_init.up.sql": "CREATE TABLE a (id int NOT NULL);\n",
        "db/migrations/1_init.down.sql": "DROP TABLE a;\n",
        # Flyway versioned + undo
        "db/migration/V2__b.sql": "CREATE TABLE b (id int UNIQUE);\n",
        "db/migration/U2__b.sql": "DROP TABLE b;\n",
        # Django: reversible by default; empty __init__.py is not a migration
        "shop/migrations/0001_initial.py": (
            "from django.db import migrations, models\n\n"
            "class Migration(migrations.Migration):\n    operations = []\n"
        ),
        "shop/migrations/__init__.py": "",
        # Alembic env.py is support code, not a migration
        "alembic/env.py": "from alembic import context\ncontext.run_migrations()\n",
        "alembic/versions/abc_add.py": (
            "def upgrade():\n    op.add_column('t', sa.Column('x', sa.Integer(), "
            "nullable=False))\n\ndef downgrade():\n    op.drop_column('t', 'x')\n"
        ),
        "pyproject.toml": "[project]\nname='x'\n",
    })
    result = _result(repo)
    metric = result["metrics"]["migrations_without_rollback_share"]
    assert metric["outcome"]["value"] == 0, metric
    assert "0 of 4 migration file(s)" in metric["derivation"]
    # The drop in Alembic's downgrade and the down/undo files are not counted.
    assert _values(result)["destructive_migration_ops_observed"] == 0


def test_prisma_migration_without_down_counts_as_missing_rollback(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path, {
        "prisma/schema.prisma": (
            "model User {\n  id Int @id\n  email String @unique\n}\n"
        ),
        "prisma/migrations/20260101_init/migration.sql": (
            'CREATE TABLE "User" ("id" INTEGER NOT NULL);\n'
        ),
        "prisma/migrations/migration_lock.toml": 'provider = "postgresql"\n',
    })
    values = _values(_result(repo))
    assert values["migrations_missing"] == 0
    assert values["migrations_without_rollback_share"] == 1.0
    assert values["schema_constraints_missing"] == 0


def test_a_narrow_scope_never_reports_presence_as_missing(tmp_path: Path) -> None:
    repo = _repo(tmp_path, GOOD)
    _git(repo, "init", "-q")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "base")
    (repo / "src/user.entity.ts").write_text(ENTITY + "// touched\n", encoding="utf-8")
    _git(repo, "commit", "-qam", "touch entity")
    values = _values(_result(repo, scope="changes", ref="HEAD~1..HEAD"))
    missing = values["migrations_missing"]
    assert missing.get("abstained") and "project scope" in missing["reason"]


# ---------------------------------------------------------------------------
# AC 3 - language/tool patterns live in the registry and generic layer
# ---------------------------------------------------------------------------


def test_patterns_come_from_the_registry_and_generic_layer() -> None:
    tables = curated_metric_tables()
    assert tables.orm_model_markers[".ts"].search("@Entity()")
    assert tables.orm_model_markers[".py"].search("class A(models.Model):")
    assert tables.schema_constraint_markers[".rb"].search("t.string :x, null: false")
    assert tables.migration_rollback_markers[".rb"].search("  def change")
    assert set(DATA_FIELDS) == {
        "orm_model_markers", "schema_constraint_markers", "migration_rollback_markers"
    }
    for facts in GENERIC_DATA_FACTS.values():
        assert all(item.citation_url.startswith("https://") for item in facts)
    source = Path(data.__file__).read_text(encoding="utf-8")
    for literal in ("@Entity", "models.Model", "nullable", "def change",
                    "migrations.Migration", "schema.prisma", "rollback:",
                    "U(?=", "DROP\\s", "notNullable"):
        assert literal not in source, literal
    # One source of truth: the migration knowledge is blast-radius's (T057).
    from easy_verifier.dimensions import blast_radius

    assert data._DESTRUCTIVE is blast_radius._DESTRUCTIVE
    assert data.MIGRATION_DIRS is blast_radius.MIGRATION_DIRS


# ---------------------------------------------------------------------------
# Real-repo shapes (T045 Stage 3): run-time DDL; one-off data scripts
# ---------------------------------------------------------------------------

STORE = '''_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS usage (
    user_id TEXT NOT NULL,
    PRIMARY KEY (user_id)
)
"""
'''


def test_a_table_created_in_source_is_a_schema_without_migrations(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path, {"src/store.py": STORE, "pyproject.toml": "[project]\n"})
    result = _result(repo)
    values = _values(result)
    assert values["migrations_missing"] == 1
    assert values["schema_constraints_missing"] == 0
    assert "CREATE TABLE" in result["metrics"]["migrations_missing"]["derivation"]
    assert result["rating"]["value"] == 40  # 20 of 50 measured weight


def test_a_data_script_in_a_migrations_directory_is_disclosed_not_counted(
    tmp_path: Path,
) -> None:
    repo = _repo(tmp_path, {
        "scripts/migrations/migrate-users.js": "for (const u of users) save(u);\n",
        "src/user.entity.ts": ENTITY,
        "package.json": "{}\n",
    })
    metric = _result(repo)["metrics"]["migrations_missing"]
    assert metric["outcome"]["value"] == 1
    assert "not counted as migrations" in metric["derivation"]
    assert "migrate-users.js" in metric["derivation"]
