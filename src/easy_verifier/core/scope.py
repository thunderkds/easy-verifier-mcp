"""Scope resolution — task | changes | worktree | project (T003).

``resolve_scope`` lets a caller ask a narrower question than "the whole repo".
It returns a :class:`Scope` naming the evaluated file set and, for ``changes``,
the diff. Everything here is read-only: git is invoked with an explicit
argument list (never ``shell=True``) and only read-only subcommands
(``rev-parse``, ``status``, ``diff``) ever appear — no ``fetch``, ``pull``,
``ls-remote`` or ``clone`` (FR-008, NFR-007, NFR-012).

Mirrors ``context.py``'s discipline: return a structured absence, never raise
for an ordinary "not available" case, and never silently widen a narrow scope
into a bigger one. A ``task`` scope that quietly becomes ``project`` scope
would produce a coverage score that looks fine and answers a question nobody
asked (see the guide) — so an unresolvable ``task`` scope is a loud, structured
refusal, not a fallback.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .redact import redact

KIND_TASK = "task"
KIND_CHANGES = "changes"
KIND_WORKTREE = "worktree"
KIND_PROJECT = "project"

VALID_KINDS = frozenset({KIND_TASK, KIND_CHANGES, KIND_WORKTREE, KIND_PROJECT})

MAX_DIFF_CHARS = 200_000
"""Upper bound on the diff text held in memory. `budget.py` (T005) owns real
relevance-ordered truncation downstream; this is only a hard ceiling so a huge
diff is never loaded unbounded (Edge Case Checklist)."""

_DIFF_CLIP_MARK = "\n…[diff clipped at {limit} characters]"

_EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
"""Git's well-known empty-tree object, used to diff a root commit that has no
parent to compare against (Edge Case Checklist)."""

_EXCLUDED_DIRS = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".tox",
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        "site-packages",
        "dist",
        "build",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
    }
)

_TASK_ID_PATTERN = re.compile(r"^(?:TASK_GUIDE_)?T(\d+)(?:\.md)?$", re.IGNORECASE)

_ACCEPTANCE_HEADING = re.compile(r"^##\s+Acceptance Criteria\s*$", re.MULTILINE)
_NEXT_HEADING = re.compile(r"^##\s+", re.MULTILINE)


@dataclass(frozen=True)
class TaskRef:
    """A resolved ``task`` scope target: the guide plus its parsed criteria."""

    task_id: str
    guide_path: str
    acceptance_criteria: tuple[str, ...]


@dataclass(frozen=True)
class Scope:
    """The evaluated file set (and, for ``changes``, the diff) a caller asked
    for. Never a verdict — same discipline as :class:`~.models.EvidencePack`."""

    kind: str
    files: tuple[str, ...] = ()
    changed_files: tuple[str, ...] = ()
    diff: str | None = None
    task_ref: TaskRef | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)


class ScopeError(ValueError):
    """The requested scope could not be resolved at all (bad ``kind``, or a bad
    ref that git itself rejects). Reserved for caller mistakes — an unusable
    *state* of the target repo (no git, no such task) is a structured
    :class:`Scope`, not this exception."""


def resolve_scope(kind: str, repo_path: str | Path, context, **args) -> Scope:
    """Resolve ``kind`` (``task`` | ``changes`` | ``worktree`` | ``project``)
    against ``repo_path`` into a :class:`Scope`.

    ``context`` is the :class:`~.context.RepoContext` already built for this
    run — ``task`` scope needs its ``mode`` to know whether kit artifacts exist
    at all before it can resolve anything.
    """
    if kind not in VALID_KINDS:
        raise ScopeError(
            f"unknown scope kind: {kind!r} (must be one of {sorted(VALID_KINDS)})"
        )

    repo = Path(repo_path)

    if kind == KIND_PROJECT:
        return _resolve_project(repo)
    if kind == KIND_WORKTREE:
        return _resolve_worktree(repo)
    if kind == KIND_CHANGES:
        return _resolve_changes(repo, ref=args.get("ref"))
    return _resolve_task(repo, context, task_id=args.get("task_id"))


# --------------------------------------------------------------------------
# project
# --------------------------------------------------------------------------


def _resolve_project(repo: Path) -> Scope:
    """The repo's relevant file set, ``.git``/vendored/build dirs excluded.

    A plain filesystem walk rather than ``git ls-files``, so this works
    identically whether or not ``repo`` is a git repository (Edge Case
    Checklist, AC #9).
    """
    files = sorted(_walk_files(repo, repo))
    return Scope(kind=KIND_PROJECT, files=tuple(files))


def _walk_files(directory: Path, repo: Path):
    # Containment is checked on *entry*, not only in the recursive branch.
    # `docs/` itself being a symlink out of the repo is the case a check
    # placed one level down misses — T002 hit exactly this in `context.py`
    # and the fix has to sit here to cover both roots.
    if not _is_contained(directory, repo):
        return
    try:
        entries = sorted(directory.iterdir(), key=lambda p: p.name)
    except OSError:
        return
    for entry in entries:
        if entry.name in _EXCLUDED_DIRS:
            # `.git` is a directory in an ordinary clone but a *file* in a git
            # worktree (it holds `gitdir: <path>`) — excluded by name either
            # way, not by type.
            continue
        if entry.is_symlink() and not entry.exists():
            continue
        if entry.is_dir():
            yield from _walk_files(entry, repo)
        elif entry.is_file():
            # A symlinked *file* pointing outside the repo is the same escape
            # one level down, so the resolved target is checked too.
            if not _is_contained(entry, repo):
                continue
            yield entry.relative_to(repo).as_posix()


def _is_contained(path: Path, repo: Path) -> bool:
    """True when ``path`` really lives inside ``repo`` once symlinks resolve.

    The engine must never enumerate — and therefore never hand a dimension —
    a path outside the target repository (NFR-007). A symlinked directory is
    an ordinary thing to find in a real checkout (`docs -> ../shared-docs`),
    so this is a containment rule, not an attacker model. Mirrors the test
    `context.py:read_source` already applies.
    """
    try:
        return path.resolve().is_relative_to(repo.resolve())
    except OSError:
        return False


# --------------------------------------------------------------------------
# worktree
# --------------------------------------------------------------------------


def _resolve_worktree(repo: Path) -> Scope:
    """Uncommitted modifications: staged + unstaged + untracked.

    A clean tree returns an empty set, not an error (AC #3). A non-git repo
    returns the structured "git required" result (AC #9).
    """
    if not _is_git_repo(repo):
        return _git_required_scope(KIND_WORKTREE)

    ok, stdout, error = _run_git(
        repo, ["status", "--porcelain=v1", "--untracked-files=all"]
    )
    if not ok:
        # Redacted like every other git stderr that reaches a note (see the
        # `git diff failed` path below) — stderr can echo a path or a line of
        # file content, and a note travels to the caller.
        return Scope(kind=KIND_WORKTREE, notes=(f"git status failed: {redact(error)}",))

    files = sorted(_parse_porcelain_paths(stdout))
    return Scope(kind=KIND_WORKTREE, files=tuple(files), changed_files=tuple(files))


def _parse_porcelain_paths(stdout: str):
    for line in stdout.splitlines():
        if not line:
            continue
        # `XY path` or, for a rename, `XY old -> new`.
        path_part = line[3:]
        if " -> " in path_part:
            path_part = path_part.split(" -> ", 1)[1]
        yield path_part.strip('"')


# --------------------------------------------------------------------------
# changes
# --------------------------------------------------------------------------


def _resolve_changes(repo: Path, ref: str | None) -> Scope:
    """Changed files + diff for a commit range, a single commit, or a branch
    name, derived from local git only (FR-008)."""
    if not _is_git_repo(repo):
        return _git_required_scope(KIND_CHANGES)

    if not ref:
        raise ScopeError(
            "changes scope requires a `ref` argument (range, commit, or branch)"
        )

    git_range = _normalize_range(repo, ref)
    if git_range is None:
        return Scope(
            kind=KIND_CHANGES,
            notes=(f"not a valid commit range, commit, or branch: {redact(ref)}",),
        )

    ok, names_out, error = _run_git(repo, ["diff", "--name-only", git_range])
    if not ok:
        return Scope(kind=KIND_CHANGES, notes=(f"git diff failed: {redact(error)}",))

    changed = tuple(sorted(line for line in names_out.splitlines() if line))

    ok, diff_out, error = _run_git(repo, ["diff", git_range])
    diff_text = diff_out if ok else None
    notes: tuple[str, ...] = ()
    if diff_text is not None and len(diff_text) > MAX_DIFF_CHARS:
        clip = _DIFF_CLIP_MARK.format(limit=MAX_DIFF_CHARS)
        diff_text = diff_text[:MAX_DIFF_CHARS] + clip
        notes = ("diff was clipped at the character ceiling",)

    return Scope(
        kind=KIND_CHANGES,
        files=changed,
        changed_files=changed,
        diff=diff_text,
        notes=notes,
    )


def _normalize_range(repo: Path, ref: str) -> str | None:
    """Turn a range, a single commit, or a branch name into a two-dot git
    diff range that ``git diff`` accepts.

    A ref already containing ``..`` is passed straight through — that is
    already a range. A bare single ref is normalized to "just this commit":
    diffed against its parent, or against git's empty-tree object when it has
    none (a root commit with no parent — Edge Case Checklist).
    """
    if ".." in ref:
        # Already a range (e.g. "HEAD~2..HEAD"). Passed straight through; an
        # invalid range is caught by the `git diff` call that follows, which
        # is a more reliable validity check than `rev-parse` across git
        # versions.
        return ref

    ok, _, _ = _run_git(repo, ["rev-parse", "--verify", f"{ref}^{{commit}}"])
    if not ok:
        return None

    parent_ok, _, _ = _run_git(repo, ["rev-parse", "--verify", f"{ref}^"])
    base = f"{ref}^" if parent_ok else _EMPTY_TREE
    return f"{base}..{ref}"


# --------------------------------------------------------------------------
# task
# --------------------------------------------------------------------------


def _resolve_task(repo: Path, context, task_id: str | None) -> Scope:
    """Resolve a task ID to its ``TASK_GUIDE_Txxx.md`` and carry its
    acceptance criteria forward as evidence (FR-007).

    Standalone mode is a structured refusal, never a silent widening to
    ``project`` scope (AC #7) — that is the acceptance criterion the guide
    calls out as mattering most.
    """
    if task_id is None:
        raise ScopeError("task scope requires a `task_id` argument")

    if getattr(context, "mode", None) != "kit-aware":
        return Scope(
            kind=KIND_TASK,
            notes=(
                "task scope is unavailable: this repository is standalone "
                "(no kit artifacts, so there is no TASK_GUIDE_*.md to resolve)",
            ),
        )

    normalized = _normalize_task_id(task_id)
    if normalized is None:
        return Scope(
            kind=KIND_TASK,
            notes=(f"not a recognizable task id: {redact(task_id)}",),
        )

    tasks_dir = repo / "tasks"
    if not tasks_dir.is_dir():
        note = "task scope is unavailable: no tasks/ directory in the target repository"
        return Scope(kind=KIND_TASK, notes=(note,))

    matches = sorted(
        p for p in tasks_dir.glob("*.md") if _normalize_task_id(p.stem) == normalized
    )

    if not matches:
        existing = sorted(
            {
                found
                for p in tasks_dir.glob("TASK_GUIDE_*.md")
                if (found := _normalize_task_id(p.stem)) is not None
            }
        )
        return Scope(
            kind=KIND_TASK,
            notes=(f"no guide found for {normalized}; known task ids: {existing}",),
        )

    if len(matches) > 1:
        names = [m.name for m in matches]
        return Scope(
            kind=KIND_TASK,
            notes=(f"ambiguous: multiple guides match {normalized}: {names}",),
        )

    guide = matches[0]
    text = guide.read_text(encoding="utf-8")
    criteria = _parse_acceptance_criteria(text)
    guide_relative = guide.relative_to(repo).as_posix()

    return Scope(
        kind=KIND_TASK,
        files=(guide_relative,),
        task_ref=TaskRef(
            task_id=normalized,
            guide_path=guide_relative,
            acceptance_criteria=criteria,
        ),
    )


def _normalize_task_id(raw: str) -> str | None:
    match = _TASK_ID_PATTERN.match(raw.strip())
    if not match:
        return None
    return f"T{match.group(1)}"


def _parse_acceptance_criteria(guide_text: str) -> tuple[str, ...]:
    """Pull the "Criterion" column out of the guide's Acceptance Criteria
    markdown table."""
    heading = _ACCEPTANCE_HEADING.search(guide_text)
    if heading is None:
        return ()

    rest = guide_text[heading.end() :]
    next_heading = _NEXT_HEADING.search(rest)
    section = rest[: next_heading.start()] if next_heading else rest

    criteria: list[str] = []
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) < 2:
            continue
        if cells[0] in {"#", "---"} or set(cells[0]) <= {"-"}:
            continue
        criteria.append(cells[1])
    return tuple(criteria)


# --------------------------------------------------------------------------
# git plumbing — read-only only
# --------------------------------------------------------------------------


def _is_git_repo(repo: Path) -> bool:
    ok, _, _ = _run_git(repo, ["rev-parse", "--git-dir"])
    return ok


def _git_required_scope(kind: str) -> Scope:
    note = "git is required for this scope but the target is not a git repository"
    return Scope(kind=kind, notes=(note,))


def _run_git(repo: Path, args: list[str]) -> tuple[bool, str, str]:
    """Run a read-only git subcommand. Never ``shell=True``; the caller passes
    an explicit argument list. Only read-only subcommands are ever invoked
    here — no ``fetch``, ``pull``, ``ls-remote`` or ``clone`` (NFR-012)."""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return False, "", "git binary not found on PATH"
    return result.returncode == 0, result.stdout, result.stderr.strip()
