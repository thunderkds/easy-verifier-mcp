"""T086: `.easy-verifier.toml` migration conventions reach blast-radius #5 and
data #4 through the call's resolved conventions, and replay byte-equal."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from test_t078_repo_conventions import cli, metric

from easy_verifier.core import registry as reg
from easy_verifier.core.roles import _registry
from easy_verifier.core.score import score_repository
from easy_verifier.core.structure import repo_conventions
from easy_verifier.dimensions import blast_radius
from easy_verifier.dimensions.blast_radius import migration_patterns


@pytest.fixture
def sot(tmp_path, monkeypatch) -> Path:
    root = tmp_path / "machine-a" / "sot"
    monkeypatch.setenv("EASY_VERIFIER_SOT", str(root))
    _registry.cache_clear()
    return root


DIRS_ITEM = {
    "language": "conventions",
    "field": "migration_dirs",
    "value": ["dbchanges"],
    "citation_url": ".easy-verifier.toml",
    "source_tag": "user-supplied",
}


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.email=t@example.org", "-c", "user.name=t", *args],
        cwd=repo,
        check=True,
        capture_output=True,
    )


def migration_repo(root: Path, *, toml: str | None) -> Path:
    """Two commits; the second adds a destructive DDL line under dbchanges/.
    The toml is git-ignored, so it is never evidence."""
    (root / "dbchanges").mkdir(parents=True)
    (root / "src").mkdir()
    _git(root, "init", "-q")
    (root / "src/a.py").write_text("def f():\n    return 1\n")
    (root / ".gitignore").write_text(".easy-verifier.toml\n")
    if toml is not None:
        (root / ".easy-verifier.toml").write_text(toml)
    (root / "dbchanges/001.sql").write_text("CREATE TABLE t (id int);\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "one")
    (root / "dbchanges/002.sql").write_text("ALTER TABLE t DROP COLUMN id;\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "two")
    return root


TOML = '[conventions]\nmigration_dirs = ["dbchanges"]\n'


def changes(repo: Path, agent_input: dict | None = None) -> dict:
    return score_repository(
        repo, scope="changes", ref="HEAD~1..HEAD", agent_input=agent_input,
        batches="all",
    ).to_dict()


def counts(payload: dict) -> tuple[str, str]:
    ops = metric(payload, "blast-radius", "destructive_migration_ops")
    observed = metric(payload, "data", "destructive_migration_ops_observed")
    return ops["derivation"], json.dumps(observed["outcome"])


def test_migration_patterns_takes_the_entry(tmp_path, sot):
    repo = migration_repo(tmp_path / "r", toml=TOML)
    default_dirs, _ = migration_patterns()
    dirs, _ = migration_patterns(repo_conventions(repo))
    assert "dbchanges" not in default_dirs
    assert dirs == default_dirs | {"dbchanges"}  # lowercase like curated


def test_toml_migration_dir_is_counted_by_both_dimensions(tmp_path, sot):
    payload = changes(migration_repo(tmp_path / "r", toml=TOML))
    derivation, observed = counts(payload)
    assert "1 destructive migration operation(s)" in derivation
    assert "abstained" not in observed or '"abstained": false' in observed
    assert [i["field"] for i in payload["registry_entries"]] == ["migration_dirs"]
    assert payload["registry_entries"] == [DIRS_ITEM]


def test_without_the_toml_the_dir_is_not_counted(tmp_path, sot):
    derivation, _ = counts(changes(migration_repo(tmp_path / "r", toml=None)))
    assert "0 destructive migration operation(s)" in derivation


def test_toml_ddl_extra_applies(tmp_path, sot):
    repo = migration_repo(
        tmp_path / "r",
        toml='[conventions]\nmigration_dirs = ["dbchanges"]\n'
        'destructive_migration_ddl = ["TRUNCATE TABLE"]\n',
    )
    (repo / "dbchanges/003.sql").write_text("TRUNCATE TABLE t;\n")
    _git(repo, "add", "-A")  # gitignore keeps the toml out
    _git(repo, "commit", "-qm", "three")
    payload = score_repository(
        repo, scope="changes", ref="HEAD~1..HEAD", batches="all"
    ).to_dict()
    ops = metric(payload, "blast-radius", "destructive_migration_ops")
    assert "1 destructive migration operation(s)" in ops["derivation"]


def test_replay_without_the_toml_is_byte_equal(tmp_path):
    a, b = tmp_path / "a-sot", tmp_path / "b-sot"
    repo = migration_repo(tmp_path / "r", toml=TOML)
    common = (
        "--repo", str(repo), "--scope", "changes", "--ref", "HEAD~1..HEAD", "--all",
    )
    original = cli("score", *common, sot_dir=a)
    assert original.returncode == 0, original.stderr
    entries = json.loads(original.stdout)["registry_entries"]
    assert entries == [DIRS_ITEM]

    (repo / ".easy-verifier.toml").unlink()
    bare = cli("score", *common, sot_dir=b)
    assert bare.stdout != original.stdout
    replay = tmp_path / "replay.json"
    replay.write_text(json.dumps({"registry_entries": entries}))
    replayed = cli("score", *common, "--agent-input", str(replay), sot_dir=b)
    assert replayed.returncode == 0, replayed.stderr
    assert replayed.stdout == original.stdout


def test_toml_cannot_add_destructive_migration_apis(tmp_path, sot):
    repo = migration_repo(
        tmp_path / "r", toml='[conventions]\ndestructive_migration_apis = ["foo"]\n'
    )
    result = cli("score", "--repo", str(repo), "--scope", "project", sot_dir=sot)
    assert result.returncode != 0
    assert b"curated-only field" in result.stderr + result.stdout


def test_two_repos_in_one_process_do_not_leak_dirs(tmp_path, sot):
    with_toml = migration_repo(tmp_path / "a", toml=TOML)
    without = migration_repo(tmp_path / "b", toml=None)
    first = counts(changes(with_toml))
    second = counts(changes(without))
    third = counts(changes(with_toml))
    assert "1 destructive" in first[0] and "0 destructive" in second[0]
    assert third == first
    assert "dbchanges" not in migration_patterns()[0]


def test_curated_field_missing_still_raises(monkeypatch):
    empty = reg.RegistryEntry(
        name="conventions", extends=None, manifests=(), roles={}, fields={}
    )
    with pytest.raises(ValueError, match="missing"):
        migration_patterns(empty)
    assert blast_radius.migration_patterns is migration_patterns
