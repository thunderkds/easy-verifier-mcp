"""T009 acceptance tests for the bespoke ``test-strategy`` dimension."""

from __future__ import annotations

import ast
import dataclasses
import inspect
import json
import re
import subprocess
import sys
from pathlib import Path

from easy_verifier.adapters.cli import main as cli_main
from easy_verifier.core.context import MODE_STANDALONE, detect_context
from easy_verifier.core.models import EvidencePack
from easy_verifier.core.pipeline import run_dimension
from easy_verifier.dimensions import test_strategy

REPO_ROOT = Path(__file__).resolve().parent.parent


def _reasons(pack: EvidencePack) -> dict[str, str]:
    return {miss.source: miss.reason for miss in pack.sources_missing}


def _correspondence_reason(pack: EvidencePack) -> str:
    return _reasons(pack)[test_strategy.CORRESPONDENCE_SOURCE]


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
            "PATH": "/usr/bin:/bin",
            "HOME": str(repo),
        },
    )


# ---------------------------------------------------------------------------
# Success Criterion 1 — this repo's own test surface
# ---------------------------------------------------------------------------


def test_this_repo_cites_its_test_tree_and_pytest_config_with_real_lines() -> None:
    pack = run_dimension(test_strategy.DESCRIPTOR, REPO_ROOT, scope="project")

    paths = [excerpt.path for excerpt in pack.excerpts]
    assert "pyproject.toml" in pack.sources_found
    assert any(path.startswith("tests/") for path in paths)

    config = next(item for item in pack.excerpts if item.path == "pyproject.toml")
    lines = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8").splitlines()
    # Real line numbers, 1-indexed and inclusive: the cited text must be
    # exactly what those lines of the file say.
    assert config.start_line >= 1
    assert config.end_line >= config.start_line
    assert config.text.splitlines()[0] == lines[config.start_line - 1]
    assert "pytest" in config.text.lower()


# ---------------------------------------------------------------------------
# Success Criterion 2 — correspondence established
# ---------------------------------------------------------------------------


def test_conventional_source_to_test_correspondence_is_established_and_cited(
    tmp_path: Path,
) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "src" / "foo.py").write_text("def foo(): ...\n", encoding="utf-8")
    (tmp_path / "tests" / "test_foo.py").write_text(
        "def test_foo(): assert True\n", encoding="utf-8"
    )

    pack = run_dimension(test_strategy.DESCRIPTOR, tmp_path, scope="project")

    reason = _correspondence_reason(pack)
    assert "src/foo.py -> tests/test_foo.py" in reason
    assert "no test discovered" not in reason
    assert "tests/test_foo.py" in [excerpt.path for excerpt in pack.excerpts]


def test_colocated_multiple_and_cross_ecosystem_conventions(tmp_path: Path) -> None:
    """Co-located tests, several tests for one source, and per-ecosystem names.

    Also pins the honest gaps: a Rust source has no single-file convention, and
    a Go test in a different directory is a different package — neither may be
    reported as a correspondence.
    """
    (tmp_path / "pkg").mkdir()
    (tmp_path / "other").mkdir()
    files = {
        # co-located, no tests/ tree
        "pkg/alpha.py": "def alpha(): ...\n",
        "pkg/alpha_test.py": "def test_alpha(): ...\n",
        # two tests for one source
        "pkg/beta.py": "def beta(): ...\n",
        "pkg/test_beta.py": "def test_beta(): ...\n",
        "pkg/beta_test.py": "def test_beta_again(): ...\n",
        # js / go / ruby / java conventions
        "pkg/widget.ts": "export const widget = 1;\n",
        "pkg/widget.spec.ts": "it('widget', () => {});\n",
        "pkg/server.go": "package pkg\n",
        "pkg/server_test.go": "package pkg\n",
        "pkg/model.rb": "class Model; end\n",
        "pkg/model_spec.rb": "describe Model do; end\n",
        "pkg/Order.java": "class Order {}\n",
        "pkg/OrderTest.java": "class OrderTest {}\n",
        # honest gaps
        "pkg/engine.rs": "pub fn engine() {}\n",
        "pkg/lonely.go": "package pkg\n",
        "other/lonely_test.go": "package other\n",
    }
    for relative, body in files.items():
        (tmp_path / relative).write_text(body, encoding="utf-8")

    pack = run_dimension(test_strategy.DESCRIPTOR, tmp_path, scope="project")
    reason = _correspondence_reason(pack)

    assert "pkg/alpha.py -> pkg/alpha_test.py" in reason
    assert "pkg/beta.py -> pkg/beta_test.py, pkg/test_beta.py" in reason
    assert "pkg/widget.ts -> pkg/widget.spec.ts" in reason
    assert "pkg/server.go -> pkg/server_test.go" in reason
    assert "pkg/model.rb -> pkg/model_spec.rb" in reason
    assert "pkg/Order.java -> pkg/OrderTest.java" in reason

    gap = reason.split("no test discovered")[1]
    assert "pkg/engine.rs" in gap
    assert "pkg/lonely.go" in gap
    assert "pkg/lonely.go ->" not in reason


# ---------------------------------------------------------------------------
# Success Criterion 3 / AC #3 / AC #7 — admitted gaps, never an estimate
# ---------------------------------------------------------------------------


def test_repo_with_no_tests_names_the_scope_file_and_scores_zero(
    tmp_path: Path,
) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "foo.py").write_text("def foo(): ...\n", encoding="utf-8")

    pack = run_dimension(test_strategy.DESCRIPTOR, tmp_path, scope="project")
    payload = dataclasses.asdict(pack)
    serialized = json.dumps(payload)

    assert pack.sources_found == ()
    assert pack.coverage_score == 0.0
    assert {miss.source for miss in pack.sources_missing} == set(
        test_strategy.SOURCES_SOUGHT
    )
    assert "no test discovered for 1 file(s): src/foo.py" in _correspondence_reason(
        pack
    )
    # Nothing anywhere in the pack estimates a figure it did not measure.
    assert not re.search(r"\d+(\.\d+)?\s?%", serialized)
    assert "estimated" not in serialized.lower()


def test_empty_tests_tree_is_a_valid_pack_with_no_fabricated_correspondence(
    tmp_path: Path,
) -> None:
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "foo.py").write_text("def foo(): ...\n", encoding="utf-8")

    pack = run_dimension(test_strategy.DESCRIPTOR, tmp_path, scope="project")

    assert isinstance(pack, EvidencePack)
    assert "no test discovered for 1 file(s): src/foo.py" in _correspondence_reason(
        pack
    )
    # `tests/__init__.py` is a test-tree file, so it is read as evidence — but
    # it is empty, so it yields no excerpt and no correspondence.
    assert "tests/__init__.py" in pack.files_read
    assert pack.excerpts == ()


# ---------------------------------------------------------------------------
# Success Criterion 4 / AC #4 — kit-aware task scope
# ---------------------------------------------------------------------------


def test_kit_aware_task_scope_includes_this_guides_acceptance_criteria() -> None:
    pack = run_dimension(
        test_strategy.DESCRIPTOR, REPO_ROOT, scope="task", task_id="T009"
    )

    guide = "tasks/TASK_GUIDE_T009.md"
    excerpt = next(item for item in pack.excerpts if item.path == guide)
    lines = (REPO_ROOT / guide).read_text(encoding="utf-8").splitlines()

    assert pack.mode == "kit-aware"
    assert pack.scope == "task"
    assert lines[excerpt.start_line - 1].strip() == "## Acceptance Criteria"
    assert "does not import `_doc_extract`" in excerpt.text
    assert "no coverage percentage" in excerpt.text


# ---------------------------------------------------------------------------
# AC #2 — framework/config evidence, including a three-way config split
# ---------------------------------------------------------------------------


def test_framework_config_split_across_three_files_is_cited_from_each(
    tmp_path: Path,
) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "x"\n\n[tool.pytest.ini_options]\ntestpaths = ["tests"]\n',
        encoding="utf-8",
    )
    (tmp_path / "pytest.ini").write_text("[pytest]\naddopts = -q\n", encoding="utf-8")
    (tmp_path / "setup.cfg").write_text(
        "[metadata]\nname = x\n\n[tool:pytest]\npython_files = check_*.py\n",
        encoding="utf-8",
    )
    (tmp_path / "tox.ini").write_text(
        "[tox]\nenvlist = py312\n\n[testenv]\ncommands = pytest\n", encoding="utf-8"
    )
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "ci.yml").write_text(
        "jobs:\n  build:\n    steps:\n      - run: python -m pytest -q\n",
        encoding="utf-8",
    )

    pack = run_dimension(test_strategy.DESCRIPTOR, tmp_path, scope="project")
    cited = {excerpt.path: excerpt for excerpt in pack.excerpts}

    for path in ("pyproject.toml", "pytest.ini", "setup.cfg", "tox.ini"):
        assert path in cited, path
        assert path in pack.sources_found or path == "tox.ini"

    # The shared manifest is cited from its test section, not from line 1.
    assert cited["pyproject.toml"].start_line == 4
    assert "testpaths" in cited["pyproject.toml"].text
    assert cited["setup.cfg"].start_line == 4
    assert "python_files" in cited["setup.cfg"].text
    assert "pytest" in cited[".github/workflows/ci.yml"].text


def test_conftest_is_cited_as_text_and_never_imported(tmp_path: Path) -> None:
    (tmp_path / "conftest.py").write_text(
        "MARKER = 'conftest evidence'\n", encoding="utf-8"
    )

    pack = run_dimension(test_strategy.DESCRIPTOR, tmp_path, scope="project")
    excerpt = next(item for item in pack.excerpts if item.path == "conftest.py")

    assert "conftest evidence" in excerpt.text
    # Read as text, never executed: no module anywhere in the interpreter was
    # loaded from the target repo's conftest (the module has no import
    # machinery at all — asserted in full by the bespoke-and-inert test below).
    loaded = {
        getattr(module, "__file__", None) for module in list(sys.modules.values())
    }
    assert str(tmp_path / "conftest.py") not in loaded
    assert "conftest.py" in pack.files_read


# ---------------------------------------------------------------------------
# AC #5 / AC #1 / AC #8 — bespoke, lazy, and structurally inert
# ---------------------------------------------------------------------------


def test_module_is_bespoke_lazy_and_cannot_execute_target_code(
    tmp_path: Path,
) -> None:
    source = Path(test_strategy.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {
        node.names[0].name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
    }
    imported.update(
        (node.module or "").split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    )

    assert "_doc_extract" not in source
    assert imported.isdisjoint(
        {"http", "importlib", "requests", "runpy", "socket", "subprocess", "urllib"}
    )
    # Called names, not source substrings: the module's own prose says it never
    # subprocesses the target, and a substring check would trip over that.
    called = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert called.isdisjoint({"eval", "exec", "compile", "__import__", "open"})
    assert inspect.isgenerator(test_strategy.collect(detect_context(tmp_path)))


# ---------------------------------------------------------------------------
# AC #6 — no coverage figure, no adequacy judgment, no verdict
# ---------------------------------------------------------------------------


def test_committed_coverage_artifacts_are_named_but_never_read_or_quoted(
    tmp_path: Path,
) -> None:
    (tmp_path / "coverage.xml").write_text(
        '<coverage line-rate="0.87"></coverage>\n', encoding="utf-8"
    )
    (tmp_path / ".coverage").write_text("SECRETNUMBER 87\n", encoding="utf-8")
    htmlcov = tmp_path / "htmlcov"
    htmlcov.mkdir()
    (htmlcov / "index.html").write_text("<p>91%</p>\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_a.py").write_text("def test_a(): ...\n", "utf-8")

    pack = run_dimension(test_strategy.DESCRIPTOR, tmp_path, scope="project")
    payload = dataclasses.asdict(pack)
    serialized = json.dumps(payload)

    warning = next(text for text in pack.warnings if "Coverage artifacts exist" in text)
    assert "coverage.xml" in warning and ".coverage" in warning
    assert "coverage.xml" not in pack.files_read
    assert ".coverage" not in pack.files_read
    assert "htmlcov/index.html" not in pack.files_read
    assert "0.87" not in serialized
    assert "SECRETNUMBER" not in serialized
    assert "91%" not in serialized

    assert {"verdict", "grade", "severity", "coverage_percent"}.isdisjoint(payload)
    lowered = serialized.lower()
    for word in (
        "adequate",
        "inadequate",
        "insufficient",
        "sufficient",
        "well-tested",
        "poorly tested",
        "untested",
        "grade",
        "verdict",
    ):
        assert word not in lowered, word
    # `coverage_score` is this engine's own found/sought checklist ratio and is
    # allowed; a *test* coverage percentage is not.
    assert not re.search(r"\d+(\.\d+)?\s?%", serialized)


# ---------------------------------------------------------------------------
# Bounded reads, ranked before the cap
# ---------------------------------------------------------------------------


def test_corresponding_test_outranks_alphabetically_earlier_filler(
    tmp_path: Path,
) -> None:
    """The read cap must be spent on relevance, not on arrival order.

    The fixture has a right answer and a wrong answer: ``tests/test_zebra.py``
    is the only test corresponding to a scope file and sorts *after* far more
    filler tests than the cap allows, so an alphabetical cap drops it.
    """
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "src" / "zebra.py").write_text("def zebra(): ...\n", encoding="utf-8")
    (tmp_path / "tests" / "test_zebra.py").write_text(
        "def test_zebra(): ...\n", encoding="utf-8"
    )
    for index in range(test_strategy.MAX_TEST_SOURCES + 20):
        (tmp_path / "tests" / f"test_aaa_{index:04}.py").write_text(
            f"def test_filler_{index}(): ...\n", encoding="utf-8"
        )

    pack = run_dimension(
        test_strategy.DESCRIPTOR, tmp_path, scope="project", budget_bytes=5_000_000
    )
    paths = [excerpt.path for excerpt in pack.excerpts]

    assert len(set(pack.files_read)) <= test_strategy.MAX_TEST_SOURCES
    assert paths[0] == "tests/test_zebra.py"
    assert "tests/test_aaa_0219.py" not in paths


def test_large_fixture_data_is_bounded_and_undecodable_files_are_skipped(
    tmp_path: Path,
) -> None:
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_big.py").write_text(
        "\n".join(f"# line {index}" for index in range(500)) + "\n", encoding="utf-8"
    )
    (tmp_path / "tests" / "fixture.bin").write_bytes(b"\x00\xff" * 100)

    pack = run_dimension(test_strategy.DESCRIPTOR, tmp_path, scope="project")
    excerpt = next(item for item in pack.excerpts if item.path == "tests/test_big.py")

    assert excerpt.end_line == 200
    assert "excerpt clipped" in excerpt.text
    assert "tests/fixture.bin" not in pack.files_read


# ---------------------------------------------------------------------------
# Scope behaviour: changes, deletion visibility, and no silent widening
# ---------------------------------------------------------------------------


def test_changes_scope_with_only_test_edits_and_a_deleted_test(
    tmp_path: Path,
) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "src" / "foo.py").write_text("def foo(): ...\n", encoding="utf-8")
    (tmp_path / "tests" / "test_foo.py").write_text(
        "def test_foo(): ...\n", encoding="utf-8"
    )
    (tmp_path / "tests" / "test_gone.py").write_text(
        "def test_gone(): ...\n", encoding="utf-8"
    )
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "base")

    (tmp_path / "tests" / "test_foo.py").write_text(
        "def test_foo(): assert foo() is None\n", encoding="utf-8"
    )
    (tmp_path / "tests" / "test_gone.py").unlink()
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "test edits")

    pack = run_dimension(
        test_strategy.DESCRIPTOR, tmp_path, scope="changes", ref="HEAD"
    )

    assert pack.scope == "changes"
    assert "tests/test_foo.py" in [excerpt.path for excerpt in pack.excerpts]
    deleted = next(
        text for text in pack.warnings if "could not be read from the worktree" in text
    )
    assert "tests/test_gone.py" in deleted
    # Discovery limited to the diff is stated, not silently presented as absence.
    assert any("Test discovery was limited" in text for text in pack.warnings)
    assert _reasons(pack)["pytest.ini"] == "not in the resolved changes scope"


def test_missing_and_bogus_selectors_never_widen_to_the_whole_repository(
    tmp_path: Path,
) -> None:
    """Absent input and bad input are different failures — both are checked.

    A narrow scope whose selector is *missing* collapses to
    ``resolved_scope = None`` in ``run_dimension``; a *bogus* one resolves to
    an empty ``Scope``. Neither may read repository-root files.
    """
    (tmp_path / "tests").mkdir()
    (tmp_path / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    (tmp_path / "tests" / "test_a.py").write_text("def test_a(): ...\n", "utf-8")
    # A real git repo, so `changes` reaches its own selector check rather than
    # stopping at "this is not a git repository".
    _git(tmp_path, "init", "-q")

    for scope in ("task", "changes"):
        pack = run_dimension(test_strategy.DESCRIPTOR, tmp_path, scope=scope)
        assert pack.files_read == (), scope
        assert pack.excerpts == (), scope
        assert pack.coverage_score == 0.0, scope
        assert any("could not be resolved" in text for text in pack.warnings), scope
        assert all(
            "could not be resolved" in miss.reason for miss in pack.sources_missing
        ), scope

    bogus = run_dimension(
        test_strategy.DESCRIPTOR, tmp_path, scope="task", task_id="T999"
    )
    assert bogus.files_read == ()
    assert bogus.excerpts == ()
    assert _reasons(bogus)["pytest.ini"] == "not in the resolved task scope"


def test_declared_sources_are_probed_so_every_miss_reason_is_truthful(
    tmp_path: Path,
) -> None:
    """Each declared source must carry a reason a real probe recorded.

    Regression guard for the failure mode T008 shipped: a dimension that only
    walks the scope never probes its own declared list, so every declared name
    falls through to the pipeline's ``not examined`` default — a claim the
    engine never checked.
    """
    (tmp_path / "pytest.ini").write_text("[pytest]\naddopts = -q\n", encoding="utf-8")
    (tmp_path / "package.json").mkdir()  # exists, but is not a regular file

    pack = run_dimension(test_strategy.DESCRIPTOR, tmp_path, scope="project")
    reasons = _reasons(pack)

    assert pack.sources_found == ("pytest.ini",)
    assert reasons["tox.ini"] == "not found in the target repository"
    assert reasons["pyproject.toml"] == "not found in the target repository"
    assert reasons["conftest.py"] == "not found in the target repository"
    assert reasons[".github/workflows/ci.yml"] == "not found in the target repository"
    assert reasons["package.json"] == "not a regular file"
    assert "not examined" not in reasons[test_strategy.CORRESPONDENCE_SOURCE]
    assert not any("byte budget" in reason for reason in reasons.values())


def test_nested_declared_source_is_never_both_cited_and_declared_missing(
    tmp_path: Path,
) -> None:
    """A declared bare name found and cited from a subdirectory must not also
    land in ``sources_missing`` — the contradiction T009's Stage 5 `verify`
    found on this repo's own ``tests/conftest.py``.

    ``pytest.ini``/``tox.ini``/``setup.cfg``/``pyproject.toml``/``package.json``/
    ``jest.config.js`` share the same bare-name declaration as ``conftest.py``,
    so this fixture nests one of the others too, to cover the same fix.
    """
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "conftest.py").write_text("import pytest\n", encoding="utf-8")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "pyproject.toml").write_text(
        "[tool.pytest.ini_options]\ntestpaths = ['tests']\n", encoding="utf-8"
    )

    pack = run_dimension(test_strategy.DESCRIPTOR, tmp_path, scope="project")
    reasons = _reasons(pack)

    assert "tests/conftest.py" in pack.files_read
    assert "conftest.py" not in reasons
    assert "sub/pyproject.toml" in pack.files_read
    assert "pyproject.toml" not in reasons

    sought = len(test_strategy.SOURCES_SOUGHT)
    found = len(pack.sources_found)
    assert pack.coverage_score == found / sought


def test_standalone_mode_carries_the_limited_context_warning(tmp_path: Path) -> None:
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_a.py").write_text("def test_a(): ...\n", "utf-8")

    pack = run_dimension(test_strategy.DESCRIPTOR, tmp_path, scope="project")

    assert pack.mode == MODE_STANDALONE
    assert any("limited" in text.lower() for text in pack.warnings)
    assert "tests/test_a.py" in pack.files_read


def test_cli_exposes_the_dimension_end_to_end(tmp_path, capsys) -> None:
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_a.py").write_text("def test_a(): ...\n", "utf-8")

    assert cli_main(["test-strategy", "--repo", str(tmp_path)]) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["dimension"] == "test-strategy"
    assert payload["scope"] == "project"
    assert payload["files_read"] == ["tests/test_a.py"]


def test_monorepo_subprojects_do_not_borrow_each_others_tests(tmp_path: Path) -> None:
    """A same-named test in a *different* subproject is not a correspondence.

    Stage 4 P1: correspondence indexed test basenames across the whole
    repository, so ``svc_b``'s ``test_payments.py`` was reported as covering
    ``svc_a``'s ``payments.py`` — a confident claim about a file nothing tests.
    The Go rule already refused this across directories; every other ecosystem
    took the fabricated match.

    The fixture pins both directions at once: the cross-subproject match must
    disappear, and the two layouts that legitimately span directories — a
    project-root ``src/`` + ``tests/`` split and a co-located pair — must keep
    matching, so the fix cannot trade one defect for the other.
    """
    files = {
        # independent subprojects: same basename, different service
        "svc_a/src/payments.py": "def charge(): ...\n",
        "svc_a/src/orders.py": "def order(): ...\n",
        "svc_b/tests/test_payments.py": "def test_payments(): ...\n",
        "svc_b/tests/test_ordering_helpers.py": "def test_helpers(): ...\n",
        # co-located pair, same directory
        "colo/widget.py": "def widget(): ...\n",
        "colo/widget_test.py": "def test_widget(): ...\n",
    }
    for relative, body in files.items():
        (tmp_path / relative).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / relative).write_text(body, encoding="utf-8")

    pack = run_dimension(test_strategy.DESCRIPTOR, tmp_path, scope="project")
    reason = _correspondence_reason(pack)

    assert "svc_a/src/payments.py ->" not in reason
    assert "svc_b" not in reason.split("no test discovered")[0]
    gap = reason.split("no test discovered")[1]
    assert "svc_a/src/payments.py" in gap
    assert "svc_a/src/orders.py" in gap
    # The layouts that must survive the boundary rule.
    assert "colo/widget.py -> colo/widget_test.py" in reason


def test_project_root_src_and_tests_split_still_matches(tmp_path: Path) -> None:
    """The commonest Python layout of all spans two directories, and a nested
    package under ``src/`` must still reach a flat ``tests/`` tree. Pinned
    separately so the monorepo boundary rule can never quietly kill it."""
    files = {
        "pyproject.toml": '[tool.pytest.ini_options]\ntestpaths = ["tests"]\n',
        "src/foo.py": "def foo(): ...\n",
        "src/deep/pkg/bar.py": "def bar(): ...\n",
        "tests/test_foo.py": "def test_foo(): ...\n",
        "tests/unit/test_bar.py": "def test_bar(): ...\n",
    }
    for relative, body in files.items():
        (tmp_path / relative).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / relative).write_text(body, encoding="utf-8")

    pack = run_dimension(test_strategy.DESCRIPTOR, tmp_path, scope="project")
    reason = _correspondence_reason(pack)

    assert "src/foo.py -> tests/test_foo.py" in reason
    assert "src/deep/pkg/bar.py -> tests/unit/test_bar.py" in reason
    assert "no test discovered" not in reason
