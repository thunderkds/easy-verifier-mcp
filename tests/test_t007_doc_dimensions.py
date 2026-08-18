"""T007 acceptance tests — shared doc-extraction helper + solution-fit,
requirement-fidelity, code-quality.

This repo (kit-aware) and the installed ``pytest`` package directory
(standalone) are the two fixtures, per Stage 1's "test fixtures are free"
decision — no synthetic repo needed for mode coverage.
"""

from __future__ import annotations

import ast
import dataclasses
import json
from pathlib import Path

import pytest

from easy_verifier.core.context import MODE_KIT_AWARE, MODE_STANDALONE
from easy_verifier.core.models import EvidencePack
from easy_verifier.core.pipeline import run_dimension
from easy_verifier.dimensions import (
    architecture,
    code_quality,
    requirement_fidelity,
    solution_fit,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DIMENSIONS_DIR = REPO_ROOT / "src" / "easy_verifier" / "dimensions"

DOC_SHAPED = (architecture, solution_fit, requirement_fidelity, code_quality)
DOC_SHAPED_NAMES = tuple(module.NAME for module in DOC_SHAPED)

STANDALONE_FIXTURE = Path(pytest.__file__).resolve().parent


# --------------------------------------------------------------------------
# 1. Both modes produce valid packs (Success Criteria 1, 2)
# --------------------------------------------------------------------------


@pytest.mark.parametrize("module", DOC_SHAPED, ids=DOC_SHAPED_NAMES)
def test_kit_aware_repo_produces_a_valid_pack(module) -> None:
    pack = run_dimension(module.DESCRIPTOR, REPO_ROOT)

    assert isinstance(pack, EvidencePack)
    assert pack.mode == MODE_KIT_AWARE
    for excerpt in pack.excerpts:
        assert (REPO_ROOT / excerpt.path).is_file()
        assert excerpt.start_line >= 1
        assert excerpt.end_line >= excerpt.start_line


@pytest.mark.parametrize("module", DOC_SHAPED, ids=DOC_SHAPED_NAMES)
def test_standalone_repo_produces_a_valid_pack_docs_over_code(module) -> None:
    pack = run_dimension(module.DESCRIPTOR, STANDALONE_FIXTURE)

    assert pack.mode == MODE_STANDALONE
    assert any("Limited context" in warning for warning in pack.warnings)
    assert pack.files_read
    assert pack.excerpts


@pytest.mark.parametrize("module", DOC_SHAPED, ids=DOC_SHAPED_NAMES)
def test_standalone_docs_prevent_code_fallback(tmp_path: Path, module) -> None:
    (tmp_path / "README.md").write_text(
        "A useful standalone document with no headings.\n", encoding="utf-8"
    )
    (tmp_path / "implementation.py").write_text(
        "def implementation():\n    return 'code fallback'\n", encoding="utf-8"
    )

    pack = run_dimension(module.DESCRIPTOR, tmp_path)

    assert pack.files_read == ("README.md",)
    assert {excerpt.path for excerpt in pack.excerpts} == {"README.md"}


def test_standalone_code_discovery_is_bounded(tmp_path: Path) -> None:
    from easy_verifier.core.context import detect_context

    for name in ("a.py", "b.py", "c.py"):
        (tmp_path / name).write_text("value = 1\n", encoding="utf-8")

    context = detect_context(tmp_path)

    assert tuple(context.iter_code_sources(limit=2)) == ("a.py", "b.py")


# --------------------------------------------------------------------------
# 2. Coverage differs across the four (AC #3, #7)
# --------------------------------------------------------------------------


def test_sources_sought_are_distinct_across_the_four_dimensions() -> None:
    sought_sets = {module.NAME: set(module.SOURCES_SOUGHT) for module in DOC_SHAPED}
    values = list(sought_sets.values())
    for i, left in enumerate(values):
        for right in values[i + 1 :]:
            assert left != right


def test_coverage_scores_differ_for_the_same_repo() -> None:
    scores = {
        module.NAME: run_dimension(module.DESCRIPTOR, REPO_ROOT).coverage_score
        for module in DOC_SHAPED
    }
    # Not every pair must differ, but they cannot all be identical — that
    # would mean the declared checklists are copy-pasted in effect.
    assert len(set(scores.values())) > 1


def test_files_read_differ_across_the_four_dimensions() -> None:
    files_read = {
        module.NAME: run_dimension(module.DESCRIPTOR, REPO_ROOT).files_read
        for module in DOC_SHAPED
    }
    values = list(files_read.values())
    assert len({v for v in values}) > 1


# --------------------------------------------------------------------------
# 3. Structural contract (AC #1, #4, #9)
# --------------------------------------------------------------------------


@pytest.mark.parametrize("module", (solution_fit, requirement_fidelity, code_quality))
def test_each_new_dimension_is_a_descriptor_plus_collect_no_base_class(module) -> None:
    assert hasattr(module, "NAME")
    assert hasattr(module, "PURPOSE")
    assert hasattr(module, "SOURCES_SOUGHT")
    assert hasattr(module, "DESCRIPTOR")
    assert callable(module.collect)
    # No class definitions at all in a dimension module — descriptor + data.
    source = (DIMENSIONS_DIR / f"{module.__name__.rsplit('.', 1)[-1]}.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)
    assert not [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]


@pytest.mark.parametrize("module", DOC_SHAPED, ids=DOC_SHAPED_NAMES)
def test_collect_result_is_an_iterator_not_a_list(module) -> None:
    from easy_verifier.core.context import RepoContext

    result = module.DESCRIPTOR.collect(
        RepoContext(repo_path=REPO_ROOT, mode="kit-aware", scope="project")
    )
    assert not isinstance(result, (list, tuple))
    assert iter(result) is result


def test_helper_is_imported_by_exactly_the_four_doc_shaped_dimensions() -> None:
    """AC #2 — keeps Constraint 8 from eroding as T008–T010 land beside it."""
    importers = set()
    for path in DIMENSIONS_DIR.glob("*.py"):
        if path.name in ("_doc_extract.py", "__init__.py"):
            continue
        if "_doc_extract" in path.read_text(encoding="utf-8"):
            importers.add(path.stem.replace("_", "-"))

    # architecture / solution_fit / requirement_fidelity / code_quality, named
    # with underscores on disk and hyphens as dimension names.
    expected_modules = (
        "architecture",
        "solution_fit",
        "requirement_fidelity",
        "code_quality",
    )
    assert importers == {m.replace("_", "-") for m in expected_modules}


def test_helper_contains_no_dimension_specific_branching() -> None:
    """AC #9 — divergence goes in the dimension, never in the helper.

    Checked structurally (no `if`/`elif` test compares against a dimension
    name), not by grepping the whole source — the docstring legitimately
    names all four callers in prose.
    """
    source = (DIMENSIONS_DIR / "_doc_extract.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    dimension_names = {
        "architecture",
        "solution-fit",
        "requirement-fidelity",
        "code-quality",
    }

    for node in ast.walk(tree):
        if isinstance(node, (ast.If, ast.IfExp)):
            test_source = ast.dump(node.test)
            assert not any(name in test_source for name in dimension_names)


# --------------------------------------------------------------------------
# 4. No verdict, ever (AC #6)
# --------------------------------------------------------------------------


FORBIDDEN_WORDS = ("verdict", "grade", "severity", "rating", "judgment", "judgement")


@pytest.mark.parametrize("module", DOC_SHAPED, ids=DOC_SHAPED_NAMES)
def test_no_dimension_emits_verdict_shaped_purpose_text(module) -> None:
    lowered = module.PURPOSE.lower()
    assert not any(word in lowered for word in FORBIDDEN_WORDS)


def test_code_quality_pack_has_no_score_field_beyond_coverage() -> None:
    pack = run_dimension(code_quality.DESCRIPTOR, REPO_ROOT)
    field_names = {f.name.lower() for f in dataclasses.fields(pack)}
    offenders = {n for n in field_names for w in FORBIDDEN_WORDS if w in n}
    assert offenders == set()
    assert "score" not in field_names - {"coverage_score"}


# --------------------------------------------------------------------------
# 5. Architecture refactor is behaviour-preserving (AC #8)
# --------------------------------------------------------------------------


def _snapshot_fixture(root: Path) -> None:
    (root / "PROJECT_SPEC.md").write_text(
        "# PROJECT_SPEC.md\n\n"
        "## Architecture Summary\n\n"
        "The system is a context packer.\n",
        encoding="utf-8",
    )
    (root / "BRAINSTORMING_LOG.md").write_text(
        "# BRAINSTORMING_LOG.md\n\n## Recommended Path\n\nOption D chosen.\n",
        encoding="utf-8",
    )
    (root / "README.md").write_text("# demo repo\n\nA small demo.\n", encoding="utf-8")


def test_architecture_pack_matches_pre_refactor_snapshot(tmp_path: Path) -> None:
    _snapshot_fixture(tmp_path)
    pack = run_dimension(architecture.DESCRIPTOR, tmp_path)

    snapshot_path = (
        Path(__file__).resolve().parent / "snapshots" / "architecture_pack.json"
    )
    expected = json.loads(snapshot_path.read_text(encoding="utf-8"))
    actual = json.loads(json.dumps(dataclasses.asdict(pack)))

    assert actual == expected


# --------------------------------------------------------------------------
# 6. Edge cases
# --------------------------------------------------------------------------


def test_source_found_with_no_matching_markers_counts_as_found_zero_excerpts(
    tmp_path: Path,
) -> None:
    (tmp_path / "PRD.md").write_text(
        "# PRD.md\n\n## Unrelated Section\n\nNothing about user stories here.\n",
        encoding="utf-8",
    )
    pack = run_dimension(solution_fit.DESCRIPTOR, tmp_path)

    assert "PRD.md" in pack.sources_found
    assert not [e for e in pack.excerpts if e.path == "PRD.md"]


@pytest.mark.parametrize(
    "heading_line",
    [
        "# Recommended Path",
        "## Recommended Path",
        "Recommended Path\n=================",
        "## 🚀 Recommended Path",
    ],
)
def test_heading_variants_are_all_detected(tmp_path: Path, heading_line: str) -> None:
    (tmp_path / "BRAINSTORMING_LOG.md").write_text(
        f"{heading_line}\n\nOption D chosen.\n", encoding="utf-8"
    )
    pack = run_dimension(solution_fit.DESCRIPTOR, tmp_path)

    assert any(
        "Option D chosen" in e.text
        for e in pack.excerpts
        if e.path == "BRAINSTORMING_LOG.md"
    )


def test_document_with_no_headings_yields_whole_file_excerpt(tmp_path: Path) -> None:
    (tmp_path / "PRD.md").write_text(
        "Just a paragraph of prose, no heading anywhere in this file at all.\n",
        encoding="utf-8",
    )
    pack = run_dimension(solution_fit.DESCRIPTOR, tmp_path)

    matching = [e for e in pack.excerpts if e.path == "PRD.md"]
    assert len(matching) == 1
    assert "Just a paragraph" in matching[0].text


def test_matching_parent_section_retains_nested_subsections(tmp_path: Path) -> None:
    (tmp_path / "PRD.md").write_text(
        "## Functional Requirements\n\n"
        "Intro.\n\n"
        "### Context loading\n\n"
        "| ID | Requirement |\n"
        "|---|---|\n"
        "| FR-001 | Load declared context. |\n\n"
        "## Out of Scope\n\n"
        "Unrelated boundary.\n",
        encoding="utf-8",
    )

    pack = run_dimension(requirement_fidelity.DESCRIPTOR, tmp_path)
    functional = next(
        excerpt
        for excerpt in pack.excerpts
        if "## Functional Requirements" in excerpt.text
    )

    assert "FR-001" in functional.text
    assert "Out of Scope" not in functional.text


def test_requirement_fidelity_collects_task_acceptance_criteria(
    tmp_path: Path,
) -> None:
    tasks = tmp_path / "tasks"
    tasks.mkdir()
    (tasks / "TASK_GUIDE_T123.md").write_text(
        "# Task T123\n\n"
        "## Acceptance Criteria\n\n"
        "- The feature returns citable evidence.\n",
        encoding="utf-8",
    )

    pack = run_dimension(requirement_fidelity.DESCRIPTOR, tmp_path)

    assert "tasks/TASK_GUIDE_*.md" in pack.sources_sought
    assert "tasks/TASK_GUIDE_*.md" in pack.sources_found
    assert "tasks/TASK_GUIDE_T123.md" in pack.files_read
    assert any(
        excerpt.path == "tasks/TASK_GUIDE_T123.md"
        and "returns citable evidence" in excerpt.text
        for excerpt in pack.excerpts
    )


def test_task_guide_glob_does_not_follow_outside_symlink(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "TASK_GUIDE_T999.md").write_text(
        "## Acceptance Criteria\n\nOutside content must not be read.\n",
        encoding="utf-8",
    )
    repo = tmp_path / "repo"
    tasks = repo / "tasks"
    tasks.mkdir(parents=True)
    (tasks / "TASK_GUIDE_T999.md").symlink_to(outside / "TASK_GUIDE_T999.md")

    pack = run_dimension(requirement_fidelity.DESCRIPTOR, repo)

    assert "tasks/TASK_GUIDE_T999.md" not in pack.files_read
    assert not any("Outside content" in excerpt.text for excerpt in pack.excerpts)


def test_code_quality_with_no_lint_config_has_zero_coverage_no_invention(
    tmp_path: Path,
) -> None:
    pack = run_dimension(code_quality.DESCRIPTOR, tmp_path)

    assert pack.coverage_score == 0.0
    assert pack.excerpts == ()
    assert set(m.source for m in pack.sources_missing) == set(
        code_quality.SOURCES_SOUGHT
    )


def test_non_markdown_config_is_bounded_whole_file_evidence(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        "# unrelated comment\n\n[tool.ruff]\nline-length = 88\n",
        encoding="utf-8",
    )

    pack = run_dimension(code_quality.DESCRIPTOR, tmp_path)

    config = next(
        excerpt for excerpt in pack.excerpts if excerpt.path == "pyproject.toml"
    )
    assert "[tool.ruff]" in config.text


def test_requirement_fidelity_standalone_with_no_frs_states_the_miss_plainly(
    tmp_path: Path,
) -> None:
    pack = run_dimension(requirement_fidelity.DESCRIPTOR, tmp_path)

    assert pack.mode == MODE_STANDALONE
    assert pack.coverage_score == 0.0
    for miss in pack.sources_missing:
        assert "not found" in miss.reason or "excluded" in miss.reason


def test_line_numbers_correct_with_crlf_line_endings(tmp_path: Path) -> None:
    content = "## Recommended Path\r\nOption D chosen.\r\nSecond line.\r\n"
    (tmp_path / "BRAINSTORMING_LOG.md").write_bytes(content.encode("utf-8"))

    pack = run_dimension(solution_fit.DESCRIPTOR, tmp_path)
    matching = [e for e in pack.excerpts if e.path == "BRAINSTORMING_LOG.md"]

    assert matching
    assert matching[0].start_line == 1
    assert matching[0].end_line == 3


def test_symlink_to_outside_the_repo_is_not_followed(tmp_path: Path) -> None:
    outside = tmp_path.parent / "t007_outside_target"
    outside.mkdir(exist_ok=True)
    (outside / "PRD.md").write_text("# secret outside content\n", encoding="utf-8")

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "PRD.md").symlink_to(outside / "PRD.md")

    pack = run_dimension(solution_fit.DESCRIPTOR, repo)

    assert "PRD.md" in {m.source for m in pack.sources_missing}
    assert not any("secret outside content" in e.text for e in pack.excerpts)


def test_same_file_read_independently_by_each_dimension(tmp_path: Path) -> None:
    """No cross-dimension cache leaks one dimension's budget into another."""
    (tmp_path / "PRD.md").write_text(
        "# PRD.md\n\n## User Stories\n\nAs a user, I want X.\n", encoding="utf-8"
    )
    first = run_dimension(solution_fit.DESCRIPTOR, tmp_path, budget_bytes=10)
    second = run_dimension(solution_fit.DESCRIPTOR, tmp_path, budget_bytes=100_000)

    assert first.truncated is True
    assert second.truncated is False
    assert second.excerpts


def test_large_document_is_bounded_and_lazy(tmp_path: Path) -> None:
    lines = "\n".join(f"line {i}" for i in range(1, 500))
    (tmp_path / "PRD.md").write_text(f"{lines}\n", encoding="utf-8")

    pack = run_dimension(solution_fit.DESCRIPTOR, tmp_path)
    matching = [e for e in pack.excerpts if e.path == "PRD.md"]
    assert matching
    assert matching[0].text.count("\n") < 250  # bounded well below the 499 lines


# --------------------------------------------------------------------------
# 7. AC #10 — DDR-0002, first genuine exercise against live code
# --------------------------------------------------------------------------


def _fake_secret() -> str:
    """Synthetic token, never a real vendor shape (no real prefix, spelled
    fake): assembled at runtime so no realistic-looking literal is committed.
    """
    return "FAKE" + "fake" + "9f2Ba7Qz1XcV8mNp4LrT6Ke0"


def test_secret_in_standalone_source_fallback_is_fingerprinted_and_env_excluded(
    tmp_path: Path,
) -> None:
    secret = _fake_secret()
    (tmp_path / "implementation.py").write_text(
        f'API_KEY = "{secret}"\n', encoding="utf-8"
    )
    (tmp_path / ".env").write_text(
        f"AWS_SECRET_ACCESS_KEY={secret}\n", encoding="utf-8"
    )

    pack = run_dimension(code_quality.DESCRIPTOR, tmp_path)
    pack_json = json.dumps(dataclasses.asdict(pack))

    assert secret not in pack_json
    assert pack.had_redactions
    source_excerpt = next(
        excerpt for excerpt in pack.excerpts if excerpt.path == "implementation.py"
    )
    assert pack.redactions
    assert pack.redactions[0].fingerprint in source_excerpt.text
    assert ".env" not in pack.files_read

    # The same pack-level fixture independently confirms that the co-located
    # .env is reported as excluded and its bytes never become readable.
    from easy_verifier.core.context import RepoContext

    ctx = RepoContext(repo_path=tmp_path, mode="standalone", scope="project")
    result = ctx.read_source(".env")
    assert result is None
    assert ctx.sources_missing[-1].source == ".env"
    assert ctx.sources_missing[-1].reason == "excluded: secret-bearing"
    assert ".env" not in ctx.files_read


def test_secret_bearing_patterns_cover_the_ddr_list(tmp_path: Path) -> None:
    from easy_verifier.core.context import RepoContext

    for name in (
        ".env",
        # Stage 4 regression: Constraint 4a's globs are `.env*` and
        # `credentials*`. The first implementation used `.env`/`.env.*` and
        # `credentials`/`credentials.*`, which read `.envrc` — a direnv file,
        # routinely full of exported credentials — and `credentialsfile`
        # straight into a pack. Both names stay pinned here.
        ".envrc",
        ".env.local",
        "credentialsfile",
        "id_rsa",
        "server.pem",
        "client.key",
        ".netrc",
        ".pgpass",
        "credentials",
        ".npmrc",
        ".pypirc",
        "secrets.yaml",
    ):
        (tmp_path / name).write_text("raw contents that must never be read\n")
        ctx = RepoContext(repo_path=tmp_path, mode="standalone", scope="project")
        assert ctx.read_source(name) is None
        assert ctx.sources_missing[-1].reason == "excluded: secret-bearing"


def test_absent_secret_bearing_path_is_reported_not_found(tmp_path: Path) -> None:
    from easy_verifier.core.context import RepoContext

    ctx = RepoContext(repo_path=tmp_path, mode="standalone", scope="project")

    assert ctx.read_source(".env") is None
    assert ctx.sources_missing[-1].reason == "not found in the target repository"


def test_secret_bearing_path_outside_repo_preserves_containment_reason(
    tmp_path: Path,
) -> None:
    from easy_verifier.core.context import RepoContext

    repo = tmp_path / "repo"
    repo.mkdir()
    outside = tmp_path / ".env"
    outside.write_text("must not be read\n", encoding="utf-8")
    ctx = RepoContext(repo_path=repo, mode="standalone", scope="project")

    assert ctx.read_source("../.env") is None
    assert ctx.sources_missing[-1].reason == (
        "resolves outside the repository; not followed"
    )


def test_secret_bearing_directory_preserves_regular_file_reason(tmp_path: Path) -> None:
    from easy_verifier.core.context import RepoContext

    (tmp_path / ".env").mkdir()
    ctx = RepoContext(repo_path=tmp_path, mode="standalone", scope="project")

    assert ctx.read_source(".env") is None
    assert ctx.sources_missing[-1].reason == "not a regular file"


def test_direct_safe_alias_to_secret_bearing_file_is_excluded(tmp_path: Path) -> None:
    from easy_verifier.core.context import RepoContext

    (tmp_path / ".env").write_text("raw secret bytes\n", encoding="utf-8")
    (tmp_path / "safe.txt").symlink_to(tmp_path / ".env")
    ctx = RepoContext(repo_path=tmp_path, mode="standalone", scope="project")

    assert ctx.read_source("safe.txt") is None
    assert ctx.sources_missing[-1].reason == "excluded: secret-bearing"
    assert "safe.txt" not in ctx.files_read


def test_discovered_doc_alias_to_secret_bearing_file_is_excluded(
    tmp_path: Path,
) -> None:
    (tmp_path / ".env").write_text("raw secret bytes\n", encoding="utf-8")
    (tmp_path / "README.md").symlink_to(tmp_path / ".env")

    pack = run_dimension(architecture.DESCRIPTOR, tmp_path)

    assert "README.md" not in pack.files_read
    assert not any("raw secret bytes" in excerpt.text for excerpt in pack.excerpts)
    assert any(
        miss.source == "README.md" and miss.reason == "excluded: secret-bearing"
        for miss in pack.sources_missing
    )


def test_task_guide_glob_alias_to_secret_bearing_file_is_excluded(
    tmp_path: Path,
) -> None:
    (tmp_path / ".env").write_text("raw secret bytes\n", encoding="utf-8")
    tasks = tmp_path / "tasks"
    tasks.mkdir()
    (tasks / "TASK_GUIDE_T123.md").symlink_to(tmp_path / ".env")

    pack = run_dimension(requirement_fidelity.DESCRIPTOR, tmp_path)

    assert "tasks/TASK_GUIDE_T123.md" not in pack.files_read
    assert not any("raw secret bytes" in excerpt.text for excerpt in pack.excerpts)
    assert any(
        miss.source == "tasks/TASK_GUIDE_*.md"
        and miss.reason == "matching files existed but none were readable"
        for miss in pack.sources_missing
    )
