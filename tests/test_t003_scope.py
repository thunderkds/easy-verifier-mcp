"""T003 — task/changes/worktree/project scope resolution.

Uses this repo as the git fixture (real history, real diffs) and temp dirs for
the degenerate cases (no git, no kit, empty tree).
"""

from __future__ import annotations

import inspect
import re
import subprocess
from pathlib import Path

import pytest

from easy_verifier.core.context import detect_context
from easy_verifier.core.scope import (
    KIND_CHANGES,
    KIND_PROJECT,
    KIND_TASK,
    KIND_WORKTREE,
    Scope,
    ScopeError,
    resolve_scope,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


def _run(*args: str, cwd: Path) -> str:
    return subprocess.run(
        args, cwd=cwd, check=True, capture_output=True, text=True
    ).stdout


def _init_git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _run("git", "init", "-q", cwd=repo)
    _run("git", "config", "user.email", "test@example.com", cwd=repo)
    _run("git", "config", "user.name", "Test", cwd=repo)
    return repo


def _commit(repo: Path, name: str, text: str, message: str) -> None:
    (repo / name).write_text(text)
    _run("git", "add", name, cwd=repo)
    _run("git", "commit", "-q", "-m", message, cwd=repo)


# --------------------------------------------------------------------------
# AC #1 — every kind returns a Scope with the declared fields
# --------------------------------------------------------------------------


@pytest.mark.parametrize("kind", [KIND_PROJECT, KIND_WORKTREE])
def test_scope_shape_for_kinds_without_extra_args(kind: str) -> None:
    ctx = detect_context(REPO_ROOT)
    scope = resolve_scope(kind, REPO_ROOT, ctx)

    assert isinstance(scope, Scope)
    assert scope.kind == kind
    assert isinstance(scope.files, tuple)
    assert isinstance(scope.changed_files, tuple)
    assert isinstance(scope.notes, tuple)


def test_changes_scope_shape() -> None:
    ctx = detect_context(REPO_ROOT)
    scope = resolve_scope(KIND_CHANGES, REPO_ROOT, ctx, ref="HEAD~1..HEAD")

    assert scope.kind == KIND_CHANGES
    assert isinstance(scope.files, tuple)
    assert isinstance(scope.changed_files, tuple)
    assert isinstance(scope.diff, str)


def test_task_scope_shape() -> None:
    ctx = detect_context(REPO_ROOT)
    scope = resolve_scope(KIND_TASK, REPO_ROOT, ctx, task_id="T003")

    assert scope.kind == KIND_TASK
    assert scope.task_ref is not None


def test_unknown_kind_raises() -> None:
    ctx = detect_context(REPO_ROOT)
    with pytest.raises(ScopeError):
        resolve_scope("bogus", REPO_ROOT, ctx)


# --------------------------------------------------------------------------
# AC #2 — project scope
# --------------------------------------------------------------------------


def test_project_scope_excludes_git_and_vendored_dirs(tmp_path: Path) -> None:
    repo = _init_git_repo(tmp_path)
    _commit(repo, "app.py", "print(1)\n", "init")
    (repo / "node_modules").mkdir()
    (repo / "node_modules" / "pkg.js").write_text("noise")
    (repo / "build").mkdir()
    (repo / "build" / "out.txt").write_text("noise")

    scope = resolve_scope(KIND_PROJECT, repo, detect_context(repo))

    assert "app.py" in scope.files
    assert not any(f.startswith(".git") for f in scope.files)
    assert not any(f.startswith("node_modules") for f in scope.files)
    assert not any(f.startswith("build") for f in scope.files)


def test_project_scope_works_without_git(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("print(1)\n")

    scope = resolve_scope(KIND_PROJECT, tmp_path, detect_context(tmp_path))

    assert scope.files == ("main.py",)
    assert scope.notes == ()


def test_this_repo_project_scope_includes_a_known_file() -> None:
    ctx = detect_context(REPO_ROOT)
    scope = resolve_scope(KIND_PROJECT, REPO_ROOT, ctx)

    assert "PROJECT_SPEC.md" in scope.files
    assert not any(f == ".git" or f.startswith(".git/") for f in scope.files)


# --------------------------------------------------------------------------
# AC #3 — worktree scope
# --------------------------------------------------------------------------


def test_worktree_scope_is_empty_on_a_clean_tree(tmp_path: Path) -> None:
    repo = _init_git_repo(tmp_path)
    _commit(repo, "app.py", "print(1)\n", "init")

    scope = resolve_scope(KIND_WORKTREE, repo, detect_context(repo))

    assert scope.files == ()
    assert scope.changed_files == ()


def test_worktree_scope_includes_staged_unstaged_and_untracked(tmp_path: Path) -> None:
    repo = _init_git_repo(tmp_path)
    _commit(repo, "tracked.py", "a = 1\n", "init")
    (repo / "tracked.py").write_text("a = 2\n")  # unstaged
    (repo / "staged.py").write_text("b = 1\n")
    _run("git", "add", "staged.py", cwd=repo)
    (repo / "untracked.py").write_text("c = 1\n")  # untracked

    scope = resolve_scope(KIND_WORKTREE, repo, detect_context(repo))

    assert set(scope.files) == {"tracked.py", "staged.py", "untracked.py"}


def test_worktree_scope_without_git_is_structured_not_an_error(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("print(1)\n")

    scope = resolve_scope(KIND_WORKTREE, tmp_path, detect_context(tmp_path))

    assert scope.files == ()
    assert any("git" in note for note in scope.notes)


# --------------------------------------------------------------------------
# AC #4 / Success Criterion 1 — changes scope
# --------------------------------------------------------------------------


def test_changes_scope_over_last_two_commits_matches_git_diff(tmp_path: Path) -> None:
    repo = _init_git_repo(tmp_path)
    _commit(repo, "a.py", "a = 1\n", "first")
    _commit(repo, "a.py", "a = 2\n", "second")
    _commit(repo, "b.py", "b = 1\n", "third")

    scope = resolve_scope(KIND_CHANGES, repo, detect_context(repo), ref="HEAD~2..HEAD")

    expected = _run("git", "diff", "--name-only", "HEAD~2..HEAD", cwd=repo).splitlines()
    assert sorted(scope.changed_files) == sorted(expected)
    assert scope.diff is not None and "b.py" in scope.diff


def test_changes_scope_accepts_a_single_commit(tmp_path: Path) -> None:
    repo = _init_git_repo(tmp_path)
    _commit(repo, "a.py", "a = 1\n", "first")
    _commit(repo, "a.py", "a = 2\n", "second")

    scope = resolve_scope(KIND_CHANGES, repo, detect_context(repo), ref="HEAD")

    assert "a.py" in scope.changed_files


def test_changes_scope_accepts_a_branch_name(tmp_path: Path) -> None:
    repo = _init_git_repo(tmp_path)
    _commit(repo, "a.py", "a = 1\n", "first")
    _run("git", "branch", "feature", cwd=repo)

    scope = resolve_scope(KIND_CHANGES, repo, detect_context(repo), ref="feature")

    assert isinstance(scope.changed_files, tuple)


def test_changes_scope_handles_a_root_commit_with_no_parent(tmp_path: Path) -> None:
    repo = _init_git_repo(tmp_path)
    _commit(repo, "a.py", "a = 1\n", "root")

    scope = resolve_scope(KIND_CHANGES, repo, detect_context(repo), ref="HEAD")

    assert "a.py" in scope.changed_files


def test_changes_scope_with_an_invalid_ref_is_a_structured_error(
    tmp_path: Path,
) -> None:
    repo = _init_git_repo(tmp_path)
    _commit(repo, "a.py", "a = 1\n", "init")
    ctx = detect_context(repo)

    scope = resolve_scope(KIND_CHANGES, repo, ctx, ref="not-a-real-ref")

    assert scope.changed_files == ()
    assert scope.notes != ()


def test_changes_scope_without_git_is_structured_not_an_error(
    tmp_path: Path,
) -> None:
    (tmp_path / "main.py").write_text("print(1)\n")
    ctx = detect_context(tmp_path)

    scope = resolve_scope(KIND_CHANGES, tmp_path, ctx, ref="HEAD~1..HEAD")

    assert scope.changed_files == ()
    assert any("git" in note for note in scope.notes)


def test_changes_scope_requires_a_ref() -> None:
    ctx = detect_context(REPO_ROOT)
    with pytest.raises(ScopeError):
        resolve_scope(KIND_CHANGES, REPO_ROOT, ctx)


# --------------------------------------------------------------------------
# AC #5 / NFR-012 — no git invocation contacts a remote
# --------------------------------------------------------------------------


def test_no_remote_contacting_git_subcommand_appears_in_the_module() -> None:
    """Static check over the actual git subcommands the module invokes (the
    first argument of every ``_run_git(repo, [...])`` call) — not a raw
    substring scan of the source, which would also match the module's own
    docstrings naming the forbidden subcommands as a design constraint."""
    source = inspect.getsource(
        __import__("easy_verifier.core.scope", fromlist=["scope"])
    )
    invoked = set(re.findall(r'_run_git\(\s*\w+,\s*\[\s*"([a-z-]+)"', source))
    assert invoked, "expected to find at least one _run_git call to check"
    assert invoked.isdisjoint({"fetch", "pull", "ls-remote", "clone"})


# --------------------------------------------------------------------------
# AC #6 / Success Criterion 2 — task scope, kit-aware mode
# --------------------------------------------------------------------------


def test_task_scope_resolves_t007_to_its_guide_and_criteria() -> None:
    ctx = detect_context(REPO_ROOT)
    scope = resolve_scope(KIND_TASK, REPO_ROOT, ctx, task_id="T007")

    assert scope.task_ref is not None
    assert scope.task_ref.task_id == "T007"
    assert scope.task_ref.guide_path == "tasks/TASK_GUIDE_T007.md"
    assert len(scope.task_ref.acceptance_criteria) > 0
    assert scope.files == ("tasks/TASK_GUIDE_T007.md",)


@pytest.mark.parametrize("given", ["T007", "t007", "TASK_GUIDE_T007.md"])
def test_task_id_forms_are_normalized(given: str) -> None:
    ctx = detect_context(REPO_ROOT)
    scope = resolve_scope(KIND_TASK, REPO_ROOT, ctx, task_id=given)

    assert scope.task_ref is not None
    assert scope.task_ref.task_id == "T007"


def test_task_scope_for_a_nonexistent_id_lists_known_ids() -> None:
    ctx = detect_context(REPO_ROOT)
    scope = resolve_scope(KIND_TASK, REPO_ROOT, ctx, task_id="T999")

    assert scope.task_ref is None
    assert any("T999" in note for note in scope.notes)
    assert any("T007" in note for note in scope.notes)


def test_task_scope_two_guides_matching_one_id_is_a_deterministic_error(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    tasks = repo / "tasks"
    tasks.mkdir(parents=True)
    (repo / "PROJECT_SPEC.md").write_text("spec")
    (tasks / "TASK_GUIDE_T007.md").write_text("## Acceptance Criteria\n")
    (tasks / "TASK_GUIDE_t007.md").write_text("## Acceptance Criteria\n")

    ctx = detect_context(repo)
    scope = resolve_scope(KIND_TASK, repo, ctx, task_id="T007")

    assert scope.task_ref is None
    assert any("ambiguous" in note for note in scope.notes)


def test_task_scope_requires_a_task_id() -> None:
    ctx = detect_context(REPO_ROOT)
    with pytest.raises(ScopeError):
        resolve_scope(KIND_TASK, REPO_ROOT, ctx)


# --------------------------------------------------------------------------
# AC #7 / Success Criterion 4 — task scope, standalone mode: refuse, don't widen
# --------------------------------------------------------------------------


def test_task_scope_in_standalone_mode_is_a_structured_refusal(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("print(1)\n")
    ctx = detect_context(tmp_path)

    scope = resolve_scope(KIND_TASK, tmp_path, ctx, task_id="T001")

    assert ctx.mode == "standalone"
    assert scope.task_ref is None
    assert scope.files == ()
    assert any("standalone" in note for note in scope.notes)


def test_task_scope_standalone_refusal_does_not_fall_back_to_project_scope(
    tmp_path: Path,
) -> None:
    (tmp_path / "main.py").write_text("print(1)\n")
    (tmp_path / "other.py").write_text("print(2)\n")
    ctx = detect_context(tmp_path)

    scope = resolve_scope(KIND_TASK, tmp_path, ctx, task_id="T001")

    # A silent widening would put main.py / other.py into `files`.
    assert scope.files == ()


# --------------------------------------------------------------------------
# AC #8 / NFR-007 — every git call is read-only
# --------------------------------------------------------------------------


def test_worktree_and_changes_scope_do_not_mutate_the_repo(tmp_path: Path) -> None:
    repo = _init_git_repo(tmp_path)
    _commit(repo, "a.py", "a = 1\n", "first")
    _commit(repo, "a.py", "a = 2\n", "second")
    (repo / "untracked.py").write_text("x = 1\n")

    before_head = _run("git", "rev-parse", "HEAD", cwd=repo)
    before_status = _run("git", "status", "--porcelain", cwd=repo)

    resolve_scope(KIND_WORKTREE, repo, detect_context(repo))
    resolve_scope(KIND_CHANGES, repo, detect_context(repo), ref="HEAD~1..HEAD")

    after_head = _run("git", "rev-parse", "HEAD", cwd=repo)
    after_status = _run("git", "status", "--porcelain", cwd=repo)

    assert before_head == after_head
    assert before_status == after_status


# --------------------------------------------------------------------------
# AC #9 / Success Criterion 3 — no git repository at all
# --------------------------------------------------------------------------


def test_no_git_repo_project_works_changes_and_worktree_are_structured(
    tmp_path: Path,
) -> None:
    (tmp_path / "README.md").write_text("hello\n")
    ctx = detect_context(tmp_path)

    project_scope = resolve_scope(KIND_PROJECT, tmp_path, ctx)
    worktree_scope = resolve_scope(KIND_WORKTREE, tmp_path, ctx)
    changes_scope = resolve_scope(KIND_CHANGES, tmp_path, ctx, ref="HEAD~1..HEAD")

    assert project_scope.files == ("README.md",)
    assert worktree_scope.files == ()
    assert worktree_scope.notes != ()
    assert changes_scope.changed_files == ()
    assert changes_scope.notes != ()


# --- Stage 4 P1 regression: containment -------------------------------------


def test_project_scope_does_not_follow_a_symlinked_directory_out_of_the_repo(
    tmp_path,
):
    """Stage 4 P1 — a repeat of the defect T002 fixed in `context.py:_walk`.

    `project` scope produces the file set dimensions later read, so a path
    outside the target repository must never appear in it (NFR-007). A
    symlinked directory is an ordinary thing in a real checkout
    (`docs -> ../shared-docs`), which is why this is a containment rule rather
    than an attacker model.

    Before the fix this returned `('docs/outside.txt', 'real.txt')`.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "outside.txt").write_text("not part of the repo\n")
    (repo / "real.txt").write_text("in the repo\n")
    (repo / "docs").symlink_to(outside, target_is_directory=True)

    scope = resolve_scope("project", repo, None)

    assert scope.files == ("real.txt",), (
        f"escaped the repo via a symlinked directory: {scope.files}"
    )


def test_project_scope_does_not_follow_a_symlinked_file_out_of_the_repo(tmp_path):
    """The same escape one level down: the link is a file, not a directory."""
    repo = tmp_path / "repo"
    repo.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("not part of the repo\n")
    (repo / "real.txt").write_text("in the repo\n")
    (repo / "linked.txt").symlink_to(outside / "secret.txt")

    scope = resolve_scope("project", repo, None)

    assert scope.files == ("real.txt",), (
        f"escaped the repo via a symlinked file: {scope.files}"
    )
