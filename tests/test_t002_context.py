"""T002 — kit detection, kit-aware/standalone modes.

The pivot of this suite is AC #3: a repository that has *some* kit artifacts is
kit-aware **and** carries the missing ones in `artifacts_missing`. Both tempting
shortcuts — "all five or it's standalone", "any one so assume the rest" —
silently corrupt every downstream coverage number, so they are each asserted
against directly.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from easy_verifier.core.context import (
    KIT_ARTIFACTS,
    LIMITED_CONTEXT_WARNING,
    MAX_DOC_SOURCES,
    MODE_KIT_AWARE,
    MODE_STANDALONE,
    RepoContext,
    RepoPathError,
    detect_context,
)
from easy_verifier.core.models import DimensionDescriptor
from easy_verifier.core.pipeline import run_dimension

REPO_ROOT = Path(__file__).resolve().parent.parent


def missing_names(context: RepoContext) -> set[str]:
    return {miss.source for miss in context.artifacts_missing}


# --------------------------------------------------------------------------
# AC #1 — shape of the returned context
# --------------------------------------------------------------------------


def test_detect_context_returns_the_declared_fields(tmp_path: Path) -> None:
    context = detect_context(tmp_path)

    assert isinstance(context, RepoContext)
    assert context.mode in {MODE_KIT_AWARE, MODE_STANDALONE}
    assert isinstance(context.artifacts_found, tuple)
    assert isinstance(context.artifacts_missing, tuple)
    assert isinstance(context.doc_sources, tuple)
    assert isinstance(context.warnings, tuple)


def test_found_and_missing_partition_the_artifact_checklist(tmp_path: Path) -> None:
    (tmp_path / "PRD.md").write_text("prd")

    context = detect_context(tmp_path)

    assert set(context.artifacts_found) | missing_names(context) == set(KIT_ARTIFACTS)
    assert set(context.artifacts_found) & missing_names(context) == set()


# --------------------------------------------------------------------------
# AC #2 / AC #3 — mode, and the partial-kit case that is the whole point
# --------------------------------------------------------------------------


@pytest.mark.parametrize("artifact", ["PROJECT_SPEC.md", "PRD.md", "PROJECT_KANBAN.md"])
def test_any_single_kit_artifact_makes_the_repo_kit_aware(
    tmp_path: Path, artifact: str
) -> None:
    (tmp_path / artifact).write_text("x")

    assert detect_context(tmp_path).mode == MODE_KIT_AWARE


def test_no_kit_artifact_is_standalone(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("print()\n")

    assert detect_context(tmp_path).mode == MODE_STANDALONE


def test_partial_kit_repo_is_kit_aware_with_the_rest_recorded_missing(
    tmp_path: Path,
) -> None:
    """AC #3 — the central case. `PROJECT_SPEC.md` only."""
    (tmp_path / "PROJECT_SPEC.md").write_text("spec")

    context = detect_context(tmp_path)

    assert context.mode == MODE_KIT_AWARE
    assert context.artifacts_found == ("PROJECT_SPEC.md",)
    assert missing_names(context) == set(KIT_ARTIFACTS) - {"PROJECT_SPEC.md"}
    assert all(miss.reason for miss in context.artifacts_missing)


def test_partial_kit_repo_is_not_silently_downgraded_to_standalone(
    tmp_path: Path,
) -> None:
    (tmp_path / "PROJECT_SPEC.md").write_text("spec")

    assert detect_context(tmp_path).mode != MODE_STANDALONE


def test_partial_kit_repo_is_not_assumed_complete(tmp_path: Path) -> None:
    (tmp_path / "PROJECT_SPEC.md").write_text("spec")

    assert detect_context(tmp_path).artifacts_missing != ()


# --------------------------------------------------------------------------
# AC #4 — the limited-context warning cannot be forgotten
# --------------------------------------------------------------------------


def test_standalone_context_carries_a_limited_context_warning(tmp_path: Path) -> None:
    context = detect_context(tmp_path)

    assert context.mode == MODE_STANDALONE
    assert LIMITED_CONTEXT_WARNING in context.warnings
    assert context.warnings[0].strip()


def test_kit_aware_context_carries_no_limited_context_warning(tmp_path: Path) -> None:
    (tmp_path / "PROJECT_SPEC.md").write_text("spec")

    assert detect_context(tmp_path).warnings == ()


def test_a_hand_built_standalone_context_still_gets_the_warning(tmp_path: Path) -> None:
    """A caller cannot opt out by constructing the context itself."""
    context = RepoContext(repo_path=tmp_path, mode=MODE_STANDALONE, scope="project")

    assert LIMITED_CONTEXT_WARNING in context.warnings


def test_every_standalone_evidence_pack_carries_the_warning(tmp_path: Path) -> None:
    """FR-004 structurally: the pack is the only way evidence leaves the engine."""
    (tmp_path / "main.py").write_text("print()\n")
    descriptor = DimensionDescriptor(
        name="probe", purpose="test", sources_sought=(), collect=lambda ctx: iter(())
    )

    pack = run_dimension(descriptor, tmp_path)

    assert pack.mode == MODE_STANDALONE
    assert LIMITED_CONTEXT_WARNING in pack.warnings


def test_kit_aware_evidence_pack_carries_no_warning() -> None:
    descriptor = DimensionDescriptor(
        name="probe", purpose="test", sources_sought=(), collect=lambda ctx: iter(())
    )

    pack = run_dimension(descriptor, REPO_ROOT)

    assert pack.mode == MODE_KIT_AWARE
    assert pack.warnings == ()


# --------------------------------------------------------------------------
# AC #5 — standalone document discovery
# --------------------------------------------------------------------------


def test_docs_are_discovered_in_precedence_order(tmp_path: Path) -> None:
    (tmp_path / "CONTRIBUTING.md").write_text("c")
    (tmp_path / "README.md").write_text("r")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "guide.md").write_text("g")
    (tmp_path / "adr").mkdir()
    (tmp_path / "adr" / "0001-choice.md").write_text("a")

    assert detect_context(tmp_path).doc_sources == (
        "README.md",
        "docs/guide.md",
        "CONTRIBUTING.md",
        "adr/0001-choice.md",
    )


def test_all_readme_variants_are_discovered_deterministically(tmp_path: Path) -> None:
    for name in ("README.txt", "README.md", "README.rst", "readme.org"):
        (tmp_path / name).write_text("r")

    assert detect_context(tmp_path).doc_sources == (
        "README.md",
        "README.rst",
        "README.txt",
        "readme.org",
    )


def test_lowercase_readme_is_found(tmp_path: Path) -> None:
    (tmp_path / "readme.md").write_text("r")

    assert detect_context(tmp_path).doc_sources == ("readme.md",)


def test_doc_discovery_skips_vendor_and_vcs_directories(tmp_path: Path) -> None:
    for noisy in (".git", "node_modules", ".venv", "__pycache__"):
        (tmp_path / "docs" / noisy).mkdir(parents=True)
        (tmp_path / "docs" / noisy / "README.md").write_text("noise")
    (tmp_path / "docs" / "real.md").write_text("real")

    assert detect_context(tmp_path).doc_sources == ("docs/real.md",)


def test_doc_discovery_does_not_follow_a_symlinked_directory_out_of_the_repo(
    tmp_path: Path,
) -> None:
    """A path discovery can never honor must never be advertised.

    `read_source` already refuses to read outside the repo, so nothing leaks.
    But listing an escaped path in `doc_sources` turns every one of those files
    into a guaranteed miss that reads as "unreadable" when the truth is "should
    never have been listed" — a depressed coverage score with a misleading
    reason, which is the exact failure this project exists to prevent.
    """
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret-plan.md").write_text("not part of the repo")

    repo = tmp_path / "repo"
    (repo / "docs").mkdir(parents=True)
    (repo / "docs" / "real.md").write_text("real")
    (repo / "docs" / "escape").symlink_to(outside, target_is_directory=True)

    context = detect_context(repo)

    assert context.doc_sources == ("docs/real.md",)
    assert not any("escape" in source for source in context.doc_sources)


def test_doc_discovery_skips_a_docs_directory_that_is_itself_an_escaping_symlink(
    tmp_path: Path,
) -> None:
    """The same escape, one level up: `docs/` itself is the link."""
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret-plan.md").write_text("not part of the repo")

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "docs").symlink_to(outside, target_is_directory=True)

    assert detect_context(repo).doc_sources == ()


def test_a_symlink_loop_in_docs_terminates(tmp_path: Path) -> None:
    """The containment check stops an out-of-repo escape; an *in-repo* loop is
    stopped by `MAX_DOC_SOURCES` alone, which is why the ceiling is
    load-bearing rather than merely a performance guard."""
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "page.md").write_text("d")
    (docs / "loop").symlink_to(docs, target_is_directory=True)

    context = detect_context(tmp_path)

    assert "docs/page.md" in context.doc_sources
    assert len(context.doc_sources) <= MAX_DOC_SOURCES


def test_doc_discovery_is_bounded_on_an_enormous_docs_tree(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    for index in range(MAX_DOC_SOURCES + 50):
        (docs / f"page-{index:04d}.md").write_text("d")

    context = detect_context(tmp_path)

    assert len(context.doc_sources) == MAX_DOC_SOURCES
    assert any("bounded" in warning for warning in context.warnings)


def test_empty_repo_discovers_no_docs_and_does_not_raise(tmp_path: Path) -> None:
    context = detect_context(tmp_path)

    assert context.mode == MODE_STANDALONE
    assert context.doc_sources == ()
    assert LIMITED_CONTEXT_WARNING in context.warnings


def test_kit_aware_repo_reports_no_standalone_doc_sources(tmp_path: Path) -> None:
    """Doc discovery is the standalone fallback; kit artifacts are the ground
    truth in kit-aware mode (FR-002/FR-003)."""
    (tmp_path / "PROJECT_SPEC.md").write_text("spec")
    (tmp_path / "README.md").write_text("r")

    assert detect_context(tmp_path).doc_sources == ()


# --------------------------------------------------------------------------
# AC #6 — nothing is populated from a file that is not on disk
# --------------------------------------------------------------------------


def test_a_directory_where_a_file_is_expected_is_missing_with_a_reason(
    tmp_path: Path,
) -> None:
    (tmp_path / "PROJECT_SPEC.md").mkdir()
    (tmp_path / "PRD.md").write_text("prd")

    context = detect_context(tmp_path)

    reasons = {miss.source: miss.reason for miss in context.artifacts_missing}
    assert "PROJECT_SPEC.md" not in context.artifacts_found
    assert "not a regular file" in reasons["PROJECT_SPEC.md"]


def test_a_file_where_a_directory_is_expected_is_missing_with_a_reason(
    tmp_path: Path,
) -> None:
    (tmp_path / "memory").write_text("not a directory")

    context = detect_context(tmp_path)

    reasons = {miss.source: miss.reason for miss in context.artifacts_missing}
    assert "not a directory" in reasons["memory/"]


def test_a_broken_symlink_artifact_is_missing_not_a_crash(tmp_path: Path) -> None:
    (tmp_path / "PROJECT_SPEC.md").symlink_to(tmp_path / "nowhere.md")

    context = detect_context(tmp_path)

    reasons = {miss.source: miss.reason for miss in context.artifacts_missing}
    assert "broken symlink" in reasons["PROJECT_SPEC.md"]
    assert context.mode == MODE_STANDALONE


def test_tasks_directory_without_guides_records_both_facts(tmp_path: Path) -> None:
    (tmp_path / "tasks").mkdir()
    (tmp_path / "tasks" / "notes.md").write_text("n")

    context = detect_context(tmp_path)

    reasons = {miss.source: miss.reason for miss in context.artifacts_missing}
    assert "tasks/" in context.artifacts_found
    assert "no TASK_GUIDE_*.md" in reasons["tasks/TASK_GUIDE_*.md"]
    assert context.mode == MODE_KIT_AWARE


def test_an_empty_memory_directory_is_found_because_it_exists(tmp_path: Path) -> None:
    (tmp_path / "memory").mkdir()

    context = detect_context(tmp_path)

    assert "memory/" in context.artifacts_found
    assert context.mode == MODE_KIT_AWARE


def test_a_kit_artifact_only_in_a_subdirectory_does_not_make_the_repo_kit_aware(
    tmp_path: Path,
) -> None:
    (tmp_path / "sub" / "project").mkdir(parents=True)
    (tmp_path / "sub" / "project" / "PROJECT_SPEC.md").write_text("spec")

    assert detect_context(tmp_path).mode == MODE_STANDALONE


# --------------------------------------------------------------------------
# AC #7 / AC #8 — read-only, and works on an arbitrary repo
# --------------------------------------------------------------------------


def test_detect_context_writes_nothing_to_the_target_repo(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("r")
    before = {path.name: path.stat().st_mtime_ns for path in tmp_path.rglob("*")}

    detect_context(tmp_path)

    after = {path.name: path.stat().st_mtime_ns for path in tmp_path.rglob("*")}
    assert after == before


def test_a_file_target_path_is_a_clear_error(tmp_path: Path) -> None:
    target = tmp_path / "README.md"
    target.write_text("r")

    with pytest.raises(RepoPathError, match="not a directory"):
        detect_context(target)


def test_a_nonexistent_target_path_is_a_clear_error(tmp_path: Path) -> None:
    with pytest.raises(RepoPathError, match="does not exist"):
        detect_context(tmp_path / "nowhere")


def test_this_repo_is_the_kit_aware_fixture() -> None:
    """Success Criterion 1 — the free kit-aware fixture."""
    context = detect_context(REPO_ROOT)

    assert context.mode == MODE_KIT_AWARE
    assert set(context.artifacts_found) == set(KIT_ARTIFACTS)
    assert context.artifacts_missing == ()
    assert context.warnings == ()


def test_an_installed_package_directory_is_the_standalone_fixture() -> None:
    """Success Criterion 2 — the free standalone fixture, no network needed."""
    context = detect_context(Path(pytest.__file__).resolve().parent)

    assert context.mode == MODE_STANDALONE
    assert LIMITED_CONTEXT_WARNING in context.warnings
