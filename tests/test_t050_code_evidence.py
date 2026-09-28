"""T050: code-quality and architecture packs carry code evidence.

code-quality appends whole functions (most complex first) and architecture
appends import-statement lines, each as a trailing tier after the unchanged
doc/config evidence, so T033's CCN and import-cycle metrics compute at the
real ``score`` surface.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from easy_verifier.core.metric_tables import curated_metric_tables
from easy_verifier.core.metrics import compute_metrics
from easy_verifier.core.pipeline import run_dimension
from easy_verifier.dimensions import _code_extract, architecture, code_quality

REPO_ROOT = Path(__file__).resolve().parents[1]

ROUTE = """\
from app import beta


def route(kind, size, flag, mode, items):
    if kind == "a":
        return 1
    elif kind == "b":
        return 2
    elif kind == "c" and flag:
        return 3
    if size > 10 or mode:
        return 4
    for item in items:
        if item:
            return 5
    while size:
        size -= 1
    if mode == "x":
        return 6
    if not items:
        return 7
    return beta.helper()
"""
"""``route``: 11 decision points (if, elif, elif, and, if, or, for, if, while,
if, if), so approximate CCN 12."""

BETA = """\
from app import alpha


def helper():
    return 0


def uses():
    return alpha.route("a", 0, False, None, [])
"""

DOC = {"README.md": "# lib\n\nA document, so the standalone code fallback stays off.\n"}


def _write(root: Path, files: dict[str, str]) -> Path:
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
        cwd=root,
        check=True,
        capture_output=True,
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = _write(
        tmp_path / "repo",
        {
            "README.md": "# app\n\nTwo modules, alpha and beta.\n",
            "pyproject.toml": '[project]\nname = "app"\n\n[tool.ruff]\n',
            "src/app/__init__.py": "",
            "src/app/alpha.py": ROUTE,
            "src/app/beta.py": BETA,
            "tests/test_alpha.py": (
                "from app.alpha import route\n\n\ndef test_route():\n"
                '    assert route("a", 0, False, None, []) == 1\n'
            ),
        },
    )
    _git(root, "init", "-q")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "init")
    return root


def _metric(metrics, dimension: str, name: str):
    return next(m for m in metrics if m.dimension == dimension and m.name == name)


def _code_refs(pack) -> list[str]:
    return [e.ref for e in pack.excerpts if e.path.endswith(".py")]


def test_cli_score_computes_ccn_and_cycles_on_a_multi_file_repo(repo: Path) -> None:
    """Success criteria 1 and 2, at the real CLI surface."""
    completed = subprocess.run(
        [sys.executable, "-m", "easy_verifier.adapters.cli", "score"]
        + ["--repo", str(repo), "--scope", "project"],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(REPO_ROOT / "src")},
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    outcomes = {
        (m["dimension"], m["name"]): m["outcome"]
        for m in json.loads(completed.stdout)["metrics"]["metrics"]
    }
    assert outcomes[("code-quality", "max_function_ccn")]["value"] == 12
    share = outcomes[("code-quality", "functions_over_ccn_10_share")]["value"]
    assert share == pytest.approx(1 / 3)  # route, helper, uses
    assert outcomes[("architecture", "top_level_import_cycles")]["value"] == 1


@pytest.mark.parametrize("module", [code_quality, architecture], ids=["cq", "arch"])
def test_doc_evidence_is_unchanged_and_code_trails_it(
    repo: Path, module, monkeypatch
) -> None:
    pack = run_dimension(module.DESCRIPTOR, repo)
    with monkeypatch.context() as patch:
        patch.setattr(_code_extract, "source_candidates", lambda context, what: [])
        docs_only = run_dimension(module.DESCRIPTOR, repo)

    assert docs_only.excerpts
    assert pack.excerpts[: len(docs_only.excerpts)] == docs_only.excerpts
    trailing = pack.excerpts[len(docs_only.excerpts) :]
    assert trailing and all(e.path.startswith("src/app/") for e in trailing)


def test_functions_are_whole_and_most_complex_first(repo: Path) -> None:
    pack = run_dimension(code_quality.DESCRIPTOR, repo)

    assert _code_refs(pack) == [
        "src/app/alpha.py:4-22",  # route, CCN 12
        "src/app/beta.py:4-5",  # helper, CCN 1 (ties by path, then line)
        "src/app/beta.py:8-9",  # uses, CCN 1
    ]
    route = next(e for e in pack.excerpts if e.path == "src/app/alpha.py")
    assert route.text == "\n".join(ROUTE.splitlines()[3:22])


def test_a_nested_function_stays_inside_its_parent(tmp_path: Path) -> None:
    root = _write(
        tmp_path,
        {
            **DOC,
            "lib/outer.py": "def outer():\n    def inner(x):\n        if x:\n"
            "            return 1\n    return inner\n",
        },
    )
    pack = run_dimension(code_quality.DESCRIPTOR, root)
    assert _code_refs(pack) == ["lib/outer.py:1-5"]


def test_import_excerpts_quote_only_statement_lines(tmp_path: Path) -> None:
    root = _write(
        tmp_path,
        {
            **DOC,
            "lib/mod.py": (
                '"""import nothing here."""\n'
                "from x import (\n    a,\n    b,\n)\nimport os\n\n\n"
                "def f():\n    import json\n    return json\n"
            ),
        },
    )
    pack = run_dimension(architecture.DESCRIPTOR, root)

    by_ref = {e.ref: e.text for e in pack.excerpts if e.path == "lib/mod.py"}
    assert by_ref == {
        "lib/mod.py:2-6": "from x import (\n    a,\n    b,\n)\nimport os",
        "lib/mod.py:10-10": "    import json",
    }


def test_byte_budget_truncation_is_reported_and_keeps_the_most_complex(
    repo: Path,
) -> None:
    full = run_dimension(code_quality.DESCRIPTOR, repo)
    route_at = next(i for i, e in enumerate(full.excerpts) if "alpha.py" in e.path)
    limit = sum(len(e.text.encode()) for e in full.excerpts[: route_at + 1])

    pack = run_dimension(code_quality.DESCRIPTOR, repo, budget_bytes=limit)
    metrics = compute_metrics(pack, curated_metric_tables())

    assert pack.truncated and _code_refs(pack) == ["src/app/alpha.py:4-22"]
    assert _metric(metrics, "code-quality", "max_function_ccn").numeric_value == 12
    share = _metric(metrics, "code-quality", "functions_over_ccn_10_share")
    assert share.abstained and "truncated" in share.abstention.reason


def test_changes_scope_reads_only_changed_source(repo: Path) -> None:
    (repo / "src/app/beta.py").write_text(BETA + "\n\ndef extra():\n    return 1\n")

    pack = run_dimension(code_quality.DESCRIPTOR, repo, scope="worktree")

    assert {e.path for e in pack.excerpts if e.path.endswith(".py")} == {
        "src/app/beta.py"
    }
    assert "src/app/alpha.py" not in pack.files_read


def test_test_files_are_not_read_by_the_code_tier(repo: Path) -> None:
    for module in (code_quality, architecture):
        pack = run_dimension(module.DESCRIPTOR, repo)
        assert "tests/test_alpha.py" not in pack.files_read


def test_secret_bearing_source_is_never_read(repo: Path) -> None:
    _write(repo, {"src/app/secrets.py": "def token():\n    return 'x'\n"})

    for module in (code_quality, architecture):
        pack = run_dimension(module.DESCRIPTOR, repo)
        assert "src/app/secrets.py" not in pack.files_read
        assert not any(e.path == "src/app/secrets.py" for e in pack.excerpts)


def test_excerpts_pass_through_redaction(tmp_path: Path) -> None:
    secret = "ghp_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8"
    root = _write(
        tmp_path, {**DOC, "lib/cfg.py": f"def cfg():\n    return '{secret}'\n"}
    )

    pack = run_dimension(code_quality.DESCRIPTOR, root)

    assert pack.redactions
    assert _code_refs(pack) == ["lib/cfg.py:1-2"]
    assert secret not in pack.excerpts[-1].text


def test_above_the_cap_no_code_is_read_and_a_warning_says_so(
    repo: Path, monkeypatch
) -> None:
    monkeypatch.setattr(_code_extract, "MAX_CODE_SOURCES", 1)

    for module in (code_quality, architecture):
        pack = run_dimension(module.DESCRIPTOR, repo)
        assert _code_refs(pack) == []
        assert not any(p.startswith("src/") for p in pack.files_read)
        assert any("exceed the cap of 1" in w for w in pack.warnings)


def test_repo_with_docs_but_no_code_is_unchanged(tmp_path: Path, monkeypatch) -> None:
    root = _write(tmp_path, {"README.md": "# Docs\n\nOnly docs.\n"})
    for module in (code_quality, architecture):
        pack = run_dimension(module.DESCRIPTOR, root)
        with monkeypatch.context() as patch:
            patch.setattr(_code_extract, "source_candidates", lambda c, w: [])
            assert run_dimension(module.DESCRIPTOR, root) == pack


def test_selection_is_deterministic(repo: Path) -> None:
    for module in (code_quality, architecture):
        first = run_dimension(module.DESCRIPTOR, repo)
        assert run_dimension(module.DESCRIPTOR, repo).excerpts == first.excerpts
