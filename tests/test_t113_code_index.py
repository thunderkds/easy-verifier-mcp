"""T113: one repository code index per run; code metrics over whole files.

Synthetic repositories only (AC10). The byte budget is set low so the packs
truncate, which is exactly when the old whole-set metrics abstained.
"""

from __future__ import annotations

import subprocess
from collections import Counter
from pathlib import Path

import pytest

from easy_verifier.core import index as index_module
from easy_verifier.core.score import score_repository
from easy_verifier.core.synthesis import combined_pack

SMALL_BUDGET = 30_000

INDEX_DIMENSIONS = ("test-strategy", "code-quality", "architecture")
"""Dimensions whose whole-set code metrics read the index (AC2)."""

INDEX_METRIC_NAMES = {
    "test-strategy": (
        "source_files_without_covering_test_share",
        "assertion_density_per_test",
        "tests_without_assertions_share",
        "skipped_test_share",
    ),
    "code-quality": (
        "functions_over_ccn_10_share",
        "type_escapes_per_kloc",
        "todo_without_ticket_share",
    ),
    "architecture": ("top_level_import_cycles", "layer_direction_violations"),
}

TRUNCATED = "the byte budget truncated this pack"


def _make_repo(root: Path, count: int = 30) -> Path:
    (root / "src" / "app").mkdir(parents=True)
    (root / "tests").mkdir()
    (root / "pyproject.toml").write_text("[project]\nname = 'demo'\n")
    body = "".join(
        f"\n\ndef helper_{j}(value):\n    if value > {j}:\n        return value - {j}\n"
        "    return value  # TODO tidy\n"
        for j in range(20)
    )
    tests = "".join(
        f"\n\ndef test_helper_{j}():\n    assert helper_{j}({j + 1}) == 1\n"
        for j in range(70)
    )
    for i in range(count):
        (root / "src" / "app" / f"mod{i}.py").write_text(
            f"from app import mod{(i + 1) % count}\n" + body
        )
        (root / "tests" / f"test_mod{i}.py").write_text(
            f"from app.mod{i} import *  # noqa\n" + tests
        )
    return root


def _metrics(result, dimension):
    return {m.name: m for m in result.metrics if m.dimension == dimension}


def _code_files(repo: Path) -> list[str]:
    return sorted(
        p.relative_to(repo).as_posix() for p in repo.rglob("*.py") if p.is_file()
    )


# AC1 -------------------------------------------------------------------------


def test_each_code_file_is_opened_at_most_once_per_score_call(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path / "repo")
    opened: Counter[str] = Counter()
    original = Path.read_bytes

    def counting(self):
        try:
            opened[self.resolve().relative_to(repo.resolve()).as_posix()] += 1
        except ValueError:
            pass
        return original(self)

    monkeypatch.setattr(Path, "read_bytes", counting)
    score_repository(repo, scope="project", budget_bytes=SMALL_BUDGET)

    code = _code_files(repo)
    assert code and all(opened[path] == 1 for path in code), {
        path: opened[path] for path in code if opened[path] != 1
    }


# AC2 -------------------------------------------------------------------------


def test_whole_set_code_metrics_never_abstain_on_budget_truncation(tmp_path):
    repo = _make_repo(tmp_path / "repo")
    result = score_repository(repo, scope="project", budget_bytes=SMALL_BUDGET)
    packs = combined_pack(
        INDEX_DIMENSIONS, repo, scope="project", budget_bytes=SMALL_BUDGET
    )
    # The precondition that made the old metrics abstain: truncated packs.
    assert all(slot.pack.truncated for slot in packs.slots)

    for dimension, names in INDEX_METRIC_NAMES.items():
        metrics = _metrics(result, dimension)
        for name in names:
            reason = metrics[name].abstention.reason if metrics[name].abstained else ""
            assert TRUNCATED not in reason, (dimension, name, reason)
    ts = _metrics(result, "test-strategy")
    # Over all 30 sources and 30 tests, not what survived the budget.
    assert ts["source_files_without_covering_test_share"].numeric_value == 0.0
    assert "all 60 code files" in ts["assertion_density_per_test"].derivation
    assert ts["tests_without_assertions_share"].numeric_value == 0.0
    rating = next(r for r in result.ratings if r.dimension == "test-strategy")
    assert getattr(rating, "value", None) is not None


def test_evidence_local_metrics_keep_their_kind(tmp_path):
    repo = _make_repo(tmp_path / "repo", count=5)
    result = score_repository(repo, scope="project", budget_bytes=SMALL_BUDGET)
    cq = _metrics(result, "code-quality")
    assert cq["max_function_ccn"].kind == "evidence_local"
    assert cq["functions_over_ccn_10_share"].kind == "whole_set"


# AC3 -------------------------------------------------------------------------


def test_index_file_cap_is_disclosed_and_deterministic(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path / "repo", count=10)
    monkeypatch.setattr(index_module, "MAX_INDEX_FILES", 7)
    first = score_repository(repo, scope="project", budget_bytes=SMALL_BUDGET)
    second = score_repository(repo, scope="project", budget_bytes=SMALL_BUDGET)

    caps = [item for item in first.capped if item["dimension"] == "index"]
    assert caps == [{"dimension": "index", "role": "code", "matched": 20, "read": 7}]
    assert first.serialize() == second.serialize()
    ts = _metrics(first, "test-strategy")
    assert "7 of 20 code files" in ts["assertion_density_per_test"].derivation


def test_byte_caps_skip_large_files_and_stop_at_the_total(tmp_path, monkeypatch):
    repo = _make_repo(tmp_path / "repo", count=3)
    (repo / "src" / "app" / "huge.py").write_text("x = 1\n" * 200_000)
    files = tuple(_code_files(repo))
    built = index_module.build_index(repo, files)
    assert "src/app/huge.py" not in built.texts
    assert (built.matched, built.read) == (7, 6)

    monkeypatch.setattr(index_module, "MAX_INDEX_BYTES", 1)
    assert index_module.build_index(repo, files).read == 0


def test_unreadable_and_non_utf8_files_are_skipped_and_counted(tmp_path):
    repo = _make_repo(tmp_path / "repo", count=2)
    (repo / "src" / "app" / "bad.py").write_bytes(b"x = '\xff\xfe'\n")
    built = index_module.build_index(repo, tuple(_code_files(repo)))
    assert "src/app/bad.py" not in built.texts
    assert (built.matched, built.read) == (5, 4)


def test_no_cap_entry_when_the_index_is_complete(tmp_path):
    repo = _make_repo(tmp_path / "repo", count=3)
    result = score_repository(repo, scope="project", budget_bytes=SMALL_BUDGET)
    assert not [item for item in result.capped if item["dimension"] == "index"]


# AC4 -------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def test_narrow_scope_measures_only_the_scope_files(tmp_path):
    repo = _make_repo(tmp_path / "repo", count=4)
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "t")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "init")
    (repo / "src" / "app" / "mod1.py").write_text("def changed():\n    return 1\n")
    (repo / "tests" / "test_mod1.py").write_text(
        "def test_changed():\n    assert True\n"
    )
    result = score_repository(repo, scope="worktree", budget_bytes=SMALL_BUDGET)
    ts = _metrics(result, "test-strategy")
    metric = ts["source_files_without_covering_test_share"]
    assert not metric.abstained
    assert set(metric.computed_from) <= {"src/app/mod1.py", "tests/test_mod1.py"}


# AC5 -------------------------------------------------------------------------


def test_excerpts_still_respect_the_byte_budget(tmp_path):
    repo = _make_repo(tmp_path / "repo")
    packs = combined_pack(
        INDEX_DIMENSIONS, repo, scope="project", budget_bytes=SMALL_BUDGET
    )
    for slot in packs.slots:
        used = sum(len(e.text.encode("utf-8")) for e in slot.pack.excerpts)
        assert used <= SMALL_BUDGET, (slot.dimension, used)


# AC6 -------------------------------------------------------------------------


def test_secret_classified_files_never_enter_the_index(tmp_path):
    repo = _make_repo(tmp_path / "repo", count=2)
    value = "FAKE" + "fake" * 6 + "9Q"
    (repo / ".env").write_text(f"API_TOKEN={value}\n")
    (repo / "src" / "app" / "settings.py").symlink_to(repo / ".env")
    built = index_module.build_index(repo, tuple(_code_files(repo)))
    assert "src/app/settings.py" not in built.texts
    assert all(value not in text for text in built.texts.values())

    result = score_repository(repo, scope="project", budget_bytes=SMALL_BUDGET)
    assert value not in result.serialize()


@pytest.mark.parametrize("dimension", INDEX_DIMENSIONS)
def test_index_metrics_cite_only_files_the_pack_read(tmp_path, dimension):
    repo = _make_repo(tmp_path / "repo", count=4)
    packs = combined_pack((dimension,), repo, scope="project")
    pack = packs.slots[0].pack
    for item in pack.whole_file or ():
        assert set(item.computed_from) <= set(pack.code_index_files)
