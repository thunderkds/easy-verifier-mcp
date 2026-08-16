"""Repository access for dimensions.

A dimension never calls ``open()``. If it did, it would own symlink escape,
invalid UTF-8, permission errors and empty-file semantics — and Option D's whole
point is that a dimension cannot bypass a cross-cutting rule because it never
owns one. Reading through :meth:`RepoContext.read_source` also means
``files_read`` / ``sources_found`` / ``sources_missing`` are recorded as a *side
effect of actually reading*, so a dimension cannot claim it read something it
did not (FR-005, NFR-002).

T002 adds kit-aware/standalone detection on top: :func:`detect_context` probes
the kit artifact checklist, records what was sought and not found, and — in
standalone mode — attaches the limited-context warning to the context object
itself, so no caller can emit a response without it (FR-004).
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from .models import Excerpt, SourceMiss
from .redact import redact

MAX_EXCERPT_LINES = 200
"""Upper bound on lines in a single whole-file excerpt."""

MAX_LINE_CHARS = 500
"""Upper bound on a single line, so a minified file yields a bounded excerpt
rather than a multi-megabyte string."""

_LINE_TRUNCATION_MARK = " …[line truncated]"

_CLIP_MARK = "…[excerpt clipped: showing lines 1–{shown} of {total}]"
"""Appended after the quoted lines when a file was longer than
``MAX_EXCERPT_LINES``. It is a marker, not a quoted line: ``end_line`` still
reports the last *file* line quoted."""

MODE_KIT_AWARE = "kit-aware"
MODE_STANDALONE = "standalone"

DEFAULT_SCOPE = "project"
"""T003 owns real scope selection (task | changes | worktree | project)."""

KIT_ARTIFACTS = (
    "PROJECT_SPEC.md",
    "PRD.md",
    "PROJECT_KANBAN.md",
    "tasks/",
    "tasks/TASK_GUIDE_*.md",
    "memory/",
)
"""The checklist probed by :func:`detect_context` (FR-001).

``tasks/`` and ``tasks/TASK_GUIDE_*.md`` are separate entries on purpose: a
``tasks/`` directory holding no guides is a real state of a repo mid-Stage-2,
and collapsing the two would report it as either wholly present or wholly
absent. Both facts are recorded.
"""

LIMITED_CONTEXT_WARNING = (
    "Limited context: no kit artifacts (PROJECT_SPEC.md, PRD.md, PROJECT_KANBAN.md, "
    "tasks/TASK_GUIDE_*.md, memory/) were found in this repository. There is no "
    "declared ground truth to check against, so findings rest only on documents "
    "discovered in the repo and, where the documents are silent, on the code itself."
)

MAX_DOC_SOURCES = 200
"""Ceiling on discovered documents.

Discovery walks lazily and stops at this count, so a repository with a
thousands-of-files ``docs/`` tree is never traversed eagerly. Hitting the
ceiling is reported as a warning rather than silently swallowed.
"""

_DOC_BOUND_WARNING = (
    "Document discovery was bounded at {limit} files; this repository has more "
    "documents than were listed."
)

_DOC_EXTENSIONS = frozenset({".md", ".markdown", ".rst", ".txt", ".adoc", ".org"})

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

_ADR_DIR_NAMES = frozenset({"adr", "adrs", "decisions"})


class RepoPathError(ValueError):
    """The target repository path is unusable. Reported as a clear message, not
    a traceback."""


class RepoContext:
    """Read-only view of the target repository handed to ``collect``.

    Never writes, and never executes anything from the target repo (NFR-007).

    Build it with :func:`detect_context` rather than directly: that is what
    fills the artifact inventory. Constructing it by hand is still safe with
    respect to FR-004 — a standalone context always carries the limited-context
    warning, because ``__init__`` adds it rather than trusting the caller to.
    """

    def __init__(
        self,
        repo_path: Path,
        mode: str,
        scope: str,
        artifacts_found: tuple[str, ...] = (),
        artifacts_missing: tuple[SourceMiss, ...] = (),
        doc_sources: tuple[str, ...] = (),
        warnings: tuple[str, ...] = (),
    ) -> None:
        self.repo_path = repo_path
        self.mode = mode
        self.scope = scope
        self.artifacts_found = artifacts_found
        self.artifacts_missing = artifacts_missing
        self.doc_sources = doc_sources
        # FR-004 is enforced here, not at the call sites. Every tool response
        # and every report is built from a context, so making the warning a
        # property of the context in standalone mode is the only placement that
        # no caller can forget.
        if mode == MODE_STANDALONE and LIMITED_CONTEXT_WARNING not in warnings:
            warnings = (LIMITED_CONTEXT_WARNING, *warnings)
        self.warnings = warnings
        self.files_read: list[str] = []
        self.sources_found: list[str] = []
        self.sources_missing: list[SourceMiss] = []

    def read_source(self, relative_path: str) -> str | None:
        """Return the text of a declared source, or ``None`` if unusable.

        Records the source as found or missing either way. A missing source is
        reported as missing — never substituted with plausible content.
        Returning ``""`` (an existing but empty file) counts as **found** and
        simply contributes no excerpt.
        """
        candidate = self.repo_path / relative_path

        try:
            resolved = candidate.resolve()
        except OSError as exc:
            self._miss(relative_path, f"path could not be resolved: {exc.strerror}")
            return None

        # Symlinks pointing outside the repository are not followed.
        if not resolved.is_relative_to(self.repo_path):
            self._miss(relative_path, "resolves outside the repository; not followed")
            return None

        if not resolved.exists():
            self._miss(relative_path, "not found in the target repository")
            return None

        if not resolved.is_file():
            self._miss(relative_path, "not a regular file")
            return None

        try:
            raw = resolved.read_bytes()
        except OSError as exc:
            self._miss(relative_path, f"unreadable: {exc.strerror}")
            return None

        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            # Skipped rather than decoded with replacement characters, which
            # would put mojibake into a citation.
            self._miss(relative_path, "not valid UTF-8 text; skipped")
            return None

        self.sources_found.append(relative_path)
        self.files_read.append(relative_path)
        return text

    def _miss(self, relative_path: str, reason: str) -> None:
        """Record a source that produced no text. Returns nothing — call sites
        report the absence to their own caller with an explicit ``return None``."""
        self.sources_missing.append(SourceMiss(source=relative_path, reason=reason))


def detect_context(repo_path: str | Path, scope: str = DEFAULT_SCOPE) -> RepoContext:
    """Decide whether ``repo_path`` was built with the kit, and say what it saw.

    Detection is deliberately dumb and total: each probe is an existence and
    kind check, and its result is *data* — never a judgment about the repo's
    quality, and never a substitute for a file that is not there (FR-005).

    A repo with **any** kit artifact is ``kit-aware``, with the artifacts it
    lacks recorded in ``artifacts_missing``. Neither shortcut is taken: a
    partial kit is not downgraded to ``standalone``, and it is not assumed to
    be complete. Probing is rooted at ``repo_path`` and does not recurse — a kit
    artifact buried in a subdirectory belongs to that subproject, not this one.
    """
    repo = _resolved_repo(repo_path)

    found, missing = _probe_kit_artifacts(repo)
    mode = MODE_KIT_AWARE if found else MODE_STANDALONE

    # Document discovery is the *standalone* fallback (FR-003). In kit-aware
    # mode the kit artifacts are the ground truth (FR-002), so discovery is not
    # run — reporting a doc inventory nobody consults would be noise.
    doc_sources: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    if mode == MODE_STANDALONE:
        doc_sources, bounded = _discover_docs(repo)
        if bounded:
            warnings = (_DOC_BOUND_WARNING.format(limit=MAX_DOC_SOURCES),)

    return RepoContext(
        repo_path=repo,
        mode=mode,
        scope=scope,
        artifacts_found=found,
        artifacts_missing=missing,
        doc_sources=doc_sources,
        warnings=warnings,
    )


def _resolved_repo(repo_path: str | Path) -> Path:
    """Validate the target path. A file, or a path that is not there, is a clear
    message rather than a traceback from deep inside a probe."""
    repo = Path(repo_path).expanduser()
    # The path itself is content: a directory or file name can carry a secret,
    # and an exception message is one of the leak paths NFR-010 names. T004
    # redacted this message while the check lived in `run_dimension`; T002 moved
    # the check here, so the redaction moves with it. Restored at Stage 5 — the
    # merge of the two branches dropped it silently, because each branch's tests
    # passed on its own side.
    if not repo.exists():
        raise RepoPathError(
            f"target repository path does not exist: {redact(str(repo))}"
        )
    if not repo.is_dir():
        raise RepoPathError(
            f"target repository path is not a directory: {redact(str(repo))}"
        )
    return repo.resolve()


def _probe_kit_artifacts(repo: Path) -> tuple[tuple[str, ...], tuple[SourceMiss, ...]]:
    """Check every entry of ``KIT_ARTIFACTS``; return found and missing.

    The two partition ``KIT_ARTIFACTS`` exactly, so the inventory is auditable
    the same way ``sources_found``/``sources_missing`` are.
    """
    found: list[str] = []
    missing: list[SourceMiss] = []

    for artifact in KIT_ARTIFACTS:
        reason = _probe(repo, artifact)
        if reason is None:
            found.append(artifact)
        else:
            missing.append(SourceMiss(source=artifact, reason=reason))

    return tuple(found), tuple(missing)


def _probe(repo: Path, artifact: str) -> str | None:
    """Return ``None`` if the artifact is present and of the expected kind,
    otherwise the reason it does not count."""
    if artifact == "tasks/TASK_GUIDE_*.md":
        tasks = repo / "tasks"
        if not tasks.is_dir():
            return "no tasks/ directory in the target repository"
        if not any(tasks.glob("TASK_GUIDE_*.md")):
            return "tasks/ exists but contains no TASK_GUIDE_*.md files"
        return None

    candidate = repo / artifact.rstrip("/")
    expects_directory = artifact.endswith("/")

    # `is_symlink()` is checked before `exists()`, which follows the link: a
    # dangling link would otherwise be reported as a plain "not found" and hide
    # a broken repo layout.
    if candidate.is_symlink() and not candidate.exists():
        return "broken symlink; treated as missing"
    if not candidate.exists():
        return "not found in the target repository"
    if expects_directory and not candidate.is_dir():
        return "expected a directory; found something that is not a directory"
    if not expects_directory and not candidate.is_file():
        return "expected a file; found something that is not a regular file"
    return None


def _discover_docs(repo: Path) -> tuple[tuple[str, ...], bool]:
    """List the repo's documents in precedence order (FR-003).

    ``README*`` first, then ``docs/**``, then ``CONTRIBUTING*``, then
    ADR-shaped files elsewhere. Code is a deliberate non-member of this list:
    FR-003 consults code only where the documents are silent, and that decision
    belongs to the dimension that has a question to answer — not to detection,
    which would otherwise enumerate the entire source tree up front.

    Returns the paths and whether :data:`MAX_DOC_SOURCES` cut the walk short.
    """
    seen: list[str] = []
    known: set[str] = set()
    bounded = False

    for relative in _candidate_docs(repo):
        if relative in known:
            continue
        if len(seen) >= MAX_DOC_SOURCES:
            bounded = True
            break
        known.add(relative)
        seen.append(relative)

    return tuple(seen), bounded


def _candidate_docs(repo: Path) -> Iterator[str]:
    """Yield document paths lazily, in precedence order.

    Lazy so that ``_discover_docs`` can stop at the ceiling without the walk
    having already visited a huge ``docs/`` tree.
    """
    yield from _root_files_matching(repo, "readme")
    yield from _walk(repo / "docs", repo)
    yield from _root_files_matching(repo, "contributing")

    for entry in _sorted_entries(repo):
        if entry.is_dir() and entry.name.lower() in _ADR_DIR_NAMES:
            yield from _walk(entry, repo)
    yield from _root_files_matching(repo, "adr")


def _root_files_matching(repo: Path, prefix: str) -> Iterator[str]:
    """Root-level files whose name starts with ``prefix``, case-insensitively.

    Case-insensitive matching is what makes ``readme.md`` discoverable on a
    case-sensitive filesystem as well as on macOS, without probing a list of
    spellings.
    """
    for entry in _sorted_entries(repo):
        if entry.is_file() and entry.name.lower().startswith(prefix):
            yield entry.name


def _walk(directory: Path, repo: Path) -> Iterator[str]:
    """Yield document files under ``directory``, depth-first, sorted.

    A subdirectory that resolves outside the repository is not descended into.
    ``read_source`` refuses to read such a path anyway, so this is not what
    keeps outside content out — but without it, discovery would advertise paths
    it can never honor, and each would come back as a miss whose stated reason
    ("resolves outside the repository") describes a listing mistake rather than
    anything about the repo. The same containment test ``read_source`` uses is
    applied here so the two cannot disagree.

    An *in-repo* symlink loop is a different matter: it stays contained, so only
    :data:`MAX_DOC_SOURCES` terminates it. That ceiling is load-bearing for
    termination, not merely a performance guard.
    """
    # Checked on entry rather than at the recursive call, so it covers the roots
    # `_candidate_docs` passes in too: `docs/` itself can be the escaping link.
    if (
        not directory.is_dir()
        or directory.name in _EXCLUDED_DIRS
        or not _is_contained(directory, repo)
    ):
        return

    for entry in _sorted_entries(directory):
        if entry.is_dir():
            if entry.name not in _EXCLUDED_DIRS:
                yield from _walk(entry, repo)
        elif entry.is_file() and entry.suffix.lower() in _DOC_EXTENSIONS:
            yield entry.relative_to(repo).as_posix()


def _is_contained(candidate: Path, repo: Path) -> bool:
    """True if ``candidate`` resolves to somewhere inside ``repo``.

    An unresolvable path is treated as *not* contained: discovery declines to
    list what it cannot vouch for.
    """
    try:
        return candidate.resolve().is_relative_to(repo)
    except OSError:
        return False


def _sorted_entries(directory: Path) -> list[Path]:
    """Directory entries in a deterministic order, or none if unreadable.

    An unreadable directory yields nothing rather than raising: detection must
    survive an arbitrary repo with no prior setup (NFR-005).
    """
    try:
        return sorted(directory.iterdir(), key=lambda path: path.name)
    except OSError:
        return []


def whole_file_excerpt(relative_path: str, text: str) -> Excerpt | None:
    """Build one bounded, 1-indexed excerpt from a file's text.

    Returns ``None`` for an empty file: it counts as found, but there is nothing
    to cite.
    """
    lines = text.splitlines()
    if not lines:
        return None

    kept = lines[:MAX_EXCERPT_LINES]
    bounded = [
        line
        if len(line) <= MAX_LINE_CHARS
        else line[:MAX_LINE_CHARS] + _LINE_TRUNCATION_MARK
        for line in kept
    ]
    # Truncation is never silent (FR-011b). The pack-level `truncated` flag means
    # "the byte budget rejected an excerpt", so it does not cover a clip the
    # caller cannot otherwise see — this marker does, in the same visible way the
    # per-line clip above announces itself.
    if len(lines) > len(kept):
        bounded.append(_CLIP_MARK.format(shown=len(kept), total=len(lines)))

    return Excerpt(
        path=relative_path,
        start_line=1,
        end_line=len(kept),
        text="\n".join(bounded),
    )
