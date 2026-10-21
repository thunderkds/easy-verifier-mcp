"""T098 -- the score payload discloses when a dimension's inputs were capped.

A role cap (``roles.MAX_ROLE_FILES``) and each dimension's own per-role cap
used to surface only as pack warning strings, so a rating computed from 50 of
197 manifests read as a whole-repository number. ``capped`` is the optional
structured disclosure: one ``{dimension, role, matched, read}`` entry per bound
hit, present only when non-empty.
"""

from __future__ import annotations

import io
import json
import subprocess
from pathlib import Path

import pytest

from easy_verifier.adapters import cli, mcp_server
from easy_verifier.core import roles
from easy_verifier.core.models import to_json_dict
from easy_verifier.core.pipeline import run_dimension
from easy_verifier.core.score import score_repository
from easy_verifier.dimensions import (
    DIMENSIONS,
    blast_radius,
    data,
    dimension_names,
    infrastructure,
    operations,
    supply_chain,
)

K8S = "k8s-manifest"


def _write(root: Path, files: dict[str, str]) -> Path:
    for relative, text in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


def _manifests(count: int) -> dict[str, str]:
    return {
        f"deploy/app-{index:03d}.yaml": (
            f"apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: app{index}\n"
        )
        for index in range(count)
    }


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        env={
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@example.com",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@example.com",
            "HOME": str(repo),
            "PATH": "/usr/bin:/bin",
        },
    )


@pytest.fixture(scope="module")
def capped_repo(tmp_path_factory) -> Path:
    root = tmp_path_factory.mktemp("capped")
    return _write(root, {"README.md": "# Infra\n", **_manifests(61)})


def _readers_of(role_name: str) -> list[str]:
    """Every dimension whose descriptor declares ``role_name``, canonical order."""
    return [
        name
        for name in dimension_names()
        if any(entry.name == role_name for entry in DIMENSIONS[name].roles)
    ]


# --- AC 1: role cap -----------------------------------------------------------


def test_resolution_keeps_the_true_match_count(capped_repo):
    resolution = roles.resolve(capped_repo, infrastructure.ROLES)
    assert resolution.truncated_roles == (K8S,)
    assert resolution.truncated_matched == {K8S: 61}
    assert len(resolution.files[K8S]) == roles.MAX_ROLE_FILES


def test_role_cap_appears_in_score_payload_for_every_reader(capped_repo):
    payload = score_repository(capped_repo, scope="project").to_dict()
    readers = _readers_of(K8S)
    assert readers  # pins the fixture: infrastructure reads the role
    assert payload["capped"] == [
        {"dimension": name, "role": K8S, "matched": 61, "read": 50}
        for name in readers
    ]


def test_role_cap_rides_on_the_pack_and_keeps_the_warning(capped_repo):
    pack = run_dimension(infrastructure.DESCRIPTOR, capped_repo, scope="project")
    assert [(c.role, c.matched, c.read) for c in pack.capped] == [(K8S, 61, 50)]
    assert to_json_dict(pack)["capped"] == (
        {"role": K8S, "matched": 61, "read": 50},
    )
    # The existing pack warning string is unchanged.
    assert (
        f"Source role '{K8S}' matched more than 50 files; only the first 50 in "
        "sorted path order were considered."
    ) in pack.warnings


# --- AC 2: no cap hit, no key -------------------------------------------------


def test_no_cap_means_no_capped_key_anywhere(tmp_path):
    repo = _write(tmp_path, {"README.md": "# Infra\n", **_manifests(50)})
    result = score_repository(repo, scope="project")
    assert "capped" not in result.to_dict()
    assert '"capped"' not in result.serialize()
    pack = run_dimension(infrastructure.DESCRIPTOR, repo, scope="project")
    assert pack.capped is None
    assert "capped" not in to_json_dict(pack)


# --- AC 3: dimension-level caps -----------------------------------------------


def test_infrastructure_dimension_cap_without_role_cap(tmp_path, monkeypatch):
    repo = _write(tmp_path, _manifests(5))
    monkeypatch.setattr(infrastructure, "MAX_FILES_PER_ROLE", 3)
    payload = score_repository(repo, scope="project").to_dict()
    assert payload["capped"] == [
        {"dimension": "infrastructure", "role": K8S, "matched": 5, "read": 3}
    ]


def test_dimension_cap_at_exactly_the_limit_is_not_capped(tmp_path, monkeypatch):
    repo = _write(tmp_path, _manifests(3))
    monkeypatch.setattr(infrastructure, "MAX_FILES_PER_ROLE", 3)
    pack = run_dimension(infrastructure.DESCRIPTOR, repo, scope="project")
    assert pack.capped is None


def test_supply_chain_dimension_cap(tmp_path, monkeypatch):
    repo = _write(
        tmp_path,
        {f"pkg{i}/package.json": f'{{"name": "p{i}"}}\n' for i in range(4)},
    )
    monkeypatch.setattr(supply_chain, "MAX_FILES_PER_ROLE", 2)
    pack = run_dimension(supply_chain.DESCRIPTOR, repo, scope="project")
    assert [(c.role, c.matched, c.read) for c in pack.capped] == [
        ("package-manifest", 4, 2)
    ]


def test_operations_dimension_cap(tmp_path, monkeypatch):
    repo = _write(
        tmp_path, {f"svc{i}/.tool-versions": "python 3.12\n" for i in range(3)}
    )
    monkeypatch.setattr(operations, "MAX_FILES_PER_ROLE", 1)
    pack = run_dimension(operations.DESCRIPTOR, repo, scope="project")
    assert [(c.role, c.matched, c.read) for c in pack.capped] == [
        ("tool-version-pin", 3, 1)
    ]


def test_data_migration_cap(tmp_path, monkeypatch):
    repo = _write(
        tmp_path,
        {
            f"migrations/000{i}_init.sql": f"CREATE TABLE t{i} (id int);\n"
            for i in range(4)
        },
    )
    monkeypatch.setattr(data, "MAX_MIGRATION_FILES", 2)
    pack = run_dimension(data.DESCRIPTOR, repo, scope="project")
    assert [(c.role, c.matched, c.read) for c in pack.capped] == [
        (data.MIGRATIONS, 4, 2)
    ]


def test_blast_radius_sweep_cap(tmp_path, monkeypatch):
    repo = _write(
        tmp_path, {f"app/m{i}.py": f"def f{i}():\n    return {i}\n" for i in range(5)}
    )
    _git(repo, "init", "-q")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "c0")
    _write(repo, {"app/m0.py": "def f0():\n    return 10\n"})
    _git(repo, "commit", "-qam", "c1")
    monkeypatch.setattr(blast_radius, "MAX_SCAN_FILES", 2)
    pack = run_dimension(
        blast_radius.DESCRIPTOR, repo, scope="changes", ref="HEAD~1", budget_bytes=10**6
    )
    assert pack.reach.sweep_capped is True
    assert [(c.role, c.matched, c.read) for c in pack.capped] == [
        (blast_radius.REFERENCES_SOURCE, 5, 2)
    ]


# --- AC 4: adapter parity -----------------------------------------------------


def test_cli_and_mcp_payloads_agree(capped_repo, capsys, monkeypatch):
    monkeypatch.setattr("sys.stdin", io.TextIOWrapper(io.BytesIO(b"")))
    mcp = mcp_server.score(repo=str(capped_repo), scope="project", detail="full")
    mcp.pop("needs_input", None)
    assert cli.main(["score", "--repo", str(capped_repo), "--scope", "project"]) == 0
    cli_payload = json.loads(capsys.readouterr().out)
    assert cli_payload == mcp
    assert cli_payload["capped"][0]["matched"] == 61
