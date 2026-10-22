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

import json
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from fnmatch import fnmatchcase
from functools import lru_cache
from importlib import resources
from pathlib import Path, PurePosixPath

from .context import _EXCLUDED_DIRS, _is_report_artifact, git_ignore_filter
from .git import run_git_text
from .models import ThirdPartyExclusion
from .redact import redact
from .roles import (
    MAX_CONFIG_BYTES,
    _config_glob_problem,
    _config_matcher,
    load_repo_excludes,
)

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

# `_EXCLUDED_DIRS` (build, cache and tool directories) is `context.py`'s: one
# set for both walks (T087). Third-party code is not in it; that is decided by
# `third_party_filter` and disclosed, never dropped silently.

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
    excluded: tuple[ThirdPartyExclusion, ...] = ()
    """Third-party roots left out of ``files`` (T087, FR-074), one per root,
    sorted by path."""


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
        resolved = _resolve_worktree(repo)
    elif kind == KIND_CHANGES:
        resolved = _resolve_changes(repo, ref=args.get("ref"))
    else:
        resolved = _resolve_task(repo, context, task_id=args.get("task_id"))
    return _without_third_party(repo, resolved)


def _without_third_party(repo: Path, scope: Scope) -> Scope:
    """A narrow scope's file lists and diff minus third-party files (T087):
    the same predicate the project walk applies."""
    if not scope.files and not scope.changed_files:
        return scope
    is_third_party = third_party_filter(repo)
    excluded: dict[str, ThirdPartyExclusion] = {}

    def keep(paths: tuple[str, ...]) -> tuple[str, ...]:
        kept = []
        for path in paths:
            hit = is_third_party(path)
            if hit is None:
                kept.append(path)
            else:
                excluded.setdefault(hit.path, hit)
        return tuple(kept)

    files, changed = keep(scope.files), keep(scope.changed_files)
    if not excluded:
        return scope
    dropped = (set(scope.files) | set(scope.changed_files)) - set(files) - set(changed)
    diff = _drop_diff_sections(scope.diff, dropped) if scope.diff else scope.diff
    return Scope(
        kind=scope.kind,
        files=files,
        changed_files=changed,
        diff=diff,
        task_ref=scope.task_ref,
        notes=scope.notes,
        excluded=tuple(sorted(excluded.values(), key=lambda item: item.path)),
    )


def _drop_diff_sections(diff: str, paths: set[str]) -> str:
    """Remove each ``diff --git`` section whose new path is excluded."""
    sections = re.split(r"(?m)^(?=diff --git )", diff)
    return "".join(
        section
        for section in sections
        if not (
            section.startswith("diff --git ")
            and any(section.split("\n", 1)[0].endswith(f" b/{path}") for path in paths)
        )
    )


# --------------------------------------------------------------------------
# project
# --------------------------------------------------------------------------


def _resolve_project(repo: Path) -> Scope:
    """The repo's relevant file set, ``.git``/vendored/build dirs excluded.

    A plain filesystem walk rather than ``git ls-files``, so this works
    identically whether or not ``repo`` is a git repository (Edge Case
    Checklist, AC #9). Where git is available, files it ignores are dropped
    (T051) — decided once here, see :func:`context.git_ignore_filter`.
    """
    skip = git_ignore_filter(repo)
    is_third_party = third_party_filter(repo)
    files: list[str] = []
    excluded: dict[str, ThirdPartyExclusion] = {}
    for path in sorted(_walk_files(repo, repo)):
        if skip(path):
            continue
        hit = is_third_party(path)
        if hit is None:
            files.append(path)
        else:
            excluded.setdefault(hit.path, hit)
    return Scope(
        kind=KIND_PROJECT,
        files=tuple(files),
        excluded=tuple(sorted(excluded.values(), key=lambda item: item.path)),
    )


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
            relative = entry.relative_to(repo).as_posix()
            if not _is_report_artifact(relative):
                yield relative


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
# third-party exclusion (T087, FR-074, DDR-0012 §5)
# --------------------------------------------------------------------------

REASON_LINGUIST = "linguist-pattern"
REASON_GITATTRIBUTES = "gitattributes"
REASON_DECLARED = "declared"
REASON_NESTED = "nested-project"

_LICENCE_FILES = ("LICENSE*", "COPYING*")
_PROJECT_FILES = ("NOTICE*", "AUTHORS*", "CONTRIBUTORS*")
"""A nested third-party root holds a licence file **and** one of these
(AC 4). Deliberately conservative: a monorepo package with only its own
``LICENSE`` is the team's code. Case-sensitive, as written."""

_ATTRS = ("linguist-vendored", "linguist-generated")


@lru_cache(maxsize=1)
def _linguist_vendor_patterns() -> tuple[tuple[str, re.Pattern[str]], ...]:
    """The kept third-party regexes of the vendored, filtered Linguist
    ``vendor.yml`` snapshot (``registry/vendored/linguist_vendor.json``)."""
    path = resources.files("easy_verifier") / "registry" / "vendored"
    data = json.loads((path / "linguist_vendor.json").read_text(encoding="utf-8"))
    return tuple(
        (pattern, re.compile(pattern))
        for item in data["kept"]
        for pattern in item["patterns"]
    )


def third_party_filter(
    repo: Path,
) -> Callable[[str], ThirdPartyExclusion | None]:
    """Return ``exclusion(relative_file_path)``: the third-party root a file
    belongs to, or ``None`` for the team's own code (T087, FR-074).

    Built once per walk, like :func:`context.git_ignore_filter`; per-directory
    answers are cached. Four reasons, every match outermost-root first so a
    root nested in another excluded root is disclosed once:

    * ``declared`` -- an ``exclude`` glob in ``.easy-verifier.toml`` (validated
      there; an invalid glob raises ``RoleInputError``);
    * ``gitattributes`` -- ``linguist-vendored`` / ``linguist-generated`` set
      on the path, git semantics (a ``.gitattributes`` applies below its own
      directory, the last matching line wins, a deeper file overrides). An
      explicit ``-linguist-vendored`` (or ``=false``) re-includes a path the
      two defaults below would exclude;
    * ``nested-project`` -- a directory below the root holding its own licence
      file and a NOTICE/AUTHORS/CONTRIBUTORS file;
    * ``linguist-pattern`` -- a kept Linguist ``vendor.yml`` regex.

    Reads names and ``.gitattributes`` text only, never file contents, and
    nothing that resolves outside the repository.
    """
    root = repo.resolve()
    declared = load_repo_excludes(repo)
    declared_match = _config_matcher(declared) if declared else None
    nested_cache: dict[str, str | None] = {}
    attrs_cache: dict[str, tuple[tuple[str, str, str, bool | None], ...]] = {}
    linguist_dir_cache: dict[str, str | None] = {}

    def contained_dir(directory: str) -> Path | None:
        path = repo / directory if directory else repo
        try:
            resolved = path.resolve()
        except OSError:
            return None
        if not resolved.is_relative_to(root) or not resolved.is_dir():
            return None
        return path

    def nested_rule(directory: str) -> str | None:
        if directory not in nested_cache:
            nested_cache[directory] = _nested_project_rule(contained_dir(directory))
        return nested_cache[directory]

    def attribute_rules(directory: str):
        if directory not in attrs_cache:
            attrs_cache[directory] = _gitattributes_rules(
                contained_dir(directory), root
            )
        return attrs_cache[directory]

    def linguist_dir_rule(directory: str) -> str | None:
        if directory not in linguist_dir_cache:
            linguist_dir_cache[directory] = next(
                (
                    source
                    for source, regex in _linguist_vendor_patterns()
                    if regex.search(directory + "/")
                ),
                None,
            )
        return linguist_dir_cache[directory]

    def exclusion(relative: str) -> ThirdPartyExclusion | None:
        parts = PurePosixPath(relative).parts
        dirs = ["/".join(parts[:depth]) for depth in range(1, len(parts))]
        candidates: list[ThirdPartyExclusion] = []

        if declared_match is not None and declared_match(relative):
            glob = next(g for g in declared if _config_matcher((g,))(relative))
            candidates.append(
                ThirdPartyExclusion(
                    _glob_root(glob, "", dirs, relative),
                    REASON_DECLARED,
                    f".easy-verifier.toml exclude: {glob}",
                )
            )

        states: dict[str, tuple[bool | None, str, str]] = {}
        for directory in ["", *dirs]:
            rules = attribute_rules(directory)
            if not rules:
                continue
            below = relative[len(directory) + 1 :] if directory else relative
            for pattern, attr, token, state in rules:
                if _config_matcher((pattern,))(below):
                    states[attr] = (state, directory, f"{pattern} {token}")
        for attr in _ATTRS:
            state, directory, line = states.get(attr, (None, "", ""))
            if state is True:
                pattern = line.split(" ", 1)[0]
                where = f"{directory}/.gitattributes" if directory else ".gitattributes"
                candidates.append(
                    ThirdPartyExclusion(
                        _glob_root(pattern, directory, dirs, relative),
                        REASON_GITATTRIBUTES,
                        f"{where}: {line}",
                    )
                )

        if states.get("linguist-vendored", (None,))[0] is not False:
            nested = next(
                ((d, rule) for d in dirs if (rule := nested_rule(d)) is not None),
                None,
            )
            if nested is not None:
                candidates.append(
                    ThirdPartyExclusion(nested[0] + "/", REASON_NESTED, nested[1])
                )
            linguist = next(
                ((d, rule) for d in dirs if (rule := linguist_dir_rule(d)) is not None),
                None,
            )
            if linguist is not None:
                candidates.append(
                    ThirdPartyExclusion(
                        linguist[0] + "/",
                        REASON_LINGUIST,
                        f"linguist vendor.yml: {linguist[1]}",
                    )
                )
            else:
                source = next(
                    (
                        src
                        for src, regex in _linguist_vendor_patterns()
                        if regex.search(relative)
                    ),
                    None,
                )
                if source is not None:
                    candidates.append(
                        ThirdPartyExclusion(
                            relative, REASON_LINGUIST, f"linguist vendor.yml: {source}"
                        )
                    )

        if not candidates:
            return None
        # Outermost root wins; on a tie, the earlier reason (declared first).
        return min(candidates, key=lambda item: item.path.rstrip("/").count("/"))

    return exclusion


def _glob_root(glob: str, base: str, dirs: list[str], relative: str) -> str:
    """The disclosed root for a glob match: the directory a ``…/**`` glob
    covers (the outermost one it names), otherwise the file itself."""
    if glob.endswith("/**"):
        prefix = _config_matcher((glob[:-3],))
        for directory in dirs:
            if base and not directory.startswith(base + "/"):
                continue
            below = directory[len(base) + 1 :] if base else directory
            if prefix(below):
                return directory + "/"
    return relative


def _nested_project_rule(directory: Path | None) -> str | None:
    """``"LICENSE + NOTICE"`` (the matched names) when ``directory`` holds its
    own licence file and a NOTICE/AUTHORS/CONTRIBUTORS file, else ``None``."""
    if directory is None:
        return None
    try:
        names = sorted(e.name for e in directory.iterdir() if e.is_file())
    except OSError:
        return None
    licence = next(
        (n for n in names if any(fnmatchcase(n, p) for p in _LICENCE_FILES)), None
    )
    project = next(
        (n for n in names if any(fnmatchcase(n, p) for p in _PROJECT_FILES)), None
    )
    if licence is None or project is None:
        return None
    return f"{licence} + {project}"


def _gitattributes_rules(
    directory: Path | None, root: Path
) -> tuple[tuple[str, str, str, bool | None], ...]:
    """``(glob relative to the directory, attribute, token, state)`` for each
    ``linguist-vendored`` / ``linguist-generated`` token of the directory's
    own ``.gitattributes``, in file order. ``state``: ``True`` set, ``False``
    unset (``-attr`` or ``attr=false``), ``None`` unspecified (``!attr``).

    The file is untrusted input: read only when it is a regular file inside
    the repository and within the config size bound; a line that is quoted,
    a directory-only pattern (it never matches a file in git), or a glob past
    the role-glob bounds is skipped -- it can only leave code *in*.
    """
    if directory is None:
        return ()
    path = directory / ".gitattributes"
    try:
        resolved = path.resolve()
        if not resolved.is_relative_to(root) or not resolved.is_file():
            return ()
        raw = resolved.read_bytes()
    except OSError:
        return ()
    if len(raw) > MAX_CONFIG_BYTES:
        return ()
    rules = []
    for line in raw.decode("utf-8", "replace").splitlines():
        fields = line.split()
        if not fields or fields[0].startswith(("#", '"', "!")):
            continue
        pattern = fields[0]
        if pattern.endswith("/"):
            continue
        if "/" in pattern:
            pattern = pattern.lstrip("/")
        else:
            pattern = "**/" + pattern
        if _config_glob_problem(pattern):
            continue
        for token in fields[1:]:
            name, _, value = token.lstrip("-!").partition("=")
            if name not in _ATTRS:
                continue
            if token.startswith("!"):
                state = None
            elif token.startswith("-") or value == "false":
                state = False
            else:
                state = True
            rules.append((pattern, name, token, state))
    return tuple(rules)


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
    here — no ``fetch``, ``pull``, ``ls-remote`` or ``clone`` (NFR-012). Goes
    through :func:`.git.run_git_text`, which disarms repo-config-driven
    execution (NFR-007)."""
    return run_git_text(repo, args)
