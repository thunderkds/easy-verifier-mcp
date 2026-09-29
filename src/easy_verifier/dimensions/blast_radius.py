"""The bespoke ``blast-radius`` evidence dimension (FR-010).

*Code-dependency* reach: what else a change to the files in the active scope
could touch. This is **not** the kit's ``blast-radius`` skill, which analyses
data-breach impact.

Three cheap, honest evidence sources, none of which parses, imports or executes
anything from the target repository (NFR-007):

* **textual reference search** — each scope file's path, dotted module path and
  file stem searched across the repository's code files. It is not a resolved
  import graph, and :data:`METHOD_WARNING` says so on every pack: a same-named
  symbol in an unrelated module is reported (over-reporting) and an alias or a
  dynamically formed reference is not (under-reporting). A real resolver would
  be per-ecosystem, enormous, and would still miss the dynamic cases;
* **git co-change history** — files appearing in the same local commits as a
  scope file. Correlation in history, never a dependency claim. Read-only git
  only; no subcommand here contacts a remote (NFR-012);
* **entry-point declarations** — packaging manifests cited at the line that
  declares an executable entry, plus whatever the reference search turns up in
  entry-point-shaped files (``__init__.py``, ``cli.py``, route modules).

``collect`` yields per match and reads the next file only when the previous
one has been pulled, so the byte budget can stop the sweep (Critical
Constraint 3). One bound is not the budget's to enforce: ``core/budget.py``
runs a tier-1 pass first, and a tier-1 pass that never meets a misfit drains
its stream by construction — a referencing file is almost never itself a
changed file, so that pass usually admits nothing. :data:`MAX_SCAN_FILES` is
what keeps that drain bounded on a monorepo; the pass that does meet the
budget is abandoned as designed.

Nothing here rates, scores or grades anything (FR-013): the pack states what is
reachable and how it was discovered, and the calling agent judges the reach.
"""

from __future__ import annotations

import math
import re
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path, PurePosixPath

from ..core.context import _is_secret_bearing
from ..core.git import run_git_text
from ..core.metric_tables import curated_metric_tables
from ..core.metrics import code_kind
from ..core.models import (
    CompatFacts,
    DiffItem,
    DimensionContext,
    DimensionDescriptor,
    Excerpt,
    ReachFacts,
    SourceMiss,
    SourceRole,
)
from ..core.redact import redact
from ..core.roles import role
from ..core.scope import KIND_CHANGES, MAX_DIFF_CHARS
from ..core.tokens import MAX_LINE_CHARS

NAME = "blast-radius"

PURPOSE = (
    "Gather citable evidence about the reach of the files in the active scope: "
    "which files textually reference them, which files local git history shows "
    "changing alongside them, and which downstream entry points are declared — "
    "without resolving an import graph or rating the reach."
)

REFERENCES_SOURCE = "referencing files (textual reference search over repository code)"
CO_CHANGE_SOURCE = "git co-change history (local `git log --name-only`)"
HOTSPOT_SOURCE = "repository change hotspots (local git history)"

#: The role whose files are the packaging manifests that declare downstream
#: entry points. Probed in every scope, narrow ones included: an entry point
#: declared at the repository root is downstream of a change anywhere, so
#: restricting these to the scope's own file set would drop exactly the
#: evidence this dimension is asked for.
MANIFEST_ROLE = "package-manifest"

ROLES: tuple[SourceRole, ...] = (
    SourceRole(name=REFERENCES_SOURCE, patterns=()),
    SourceRole(name=CO_CHANGE_SOURCE, patterns=()),
    SourceRole(name=HOTSPOT_SOURCE, patterns=()),
    role(MANIFEST_ROLE),
)
"""Source roles (T026): three pseudo-roles this dimension credits itself, and
the package-manifest role filled by any ecosystem's manifest."""

SOURCES_SOUGHT: tuple[str, ...] = tuple(item.name for item in ROLES)

MAX_SCOPE_FILES = 50
"""Scope files expanded from. A worktree scope can name hundreds of files, and
every one of them widens the search pattern."""

MAX_SCAN_FILES = 400
"""Repository files opened while searching for references.

A ceiling, not the usual stopping point: the byte budget normally abandons the
generator long before this (Critical Constraint 3)."""

MAX_MATCHES_PER_FILE = 3
"""Citing lines quoted per referencing file, so one file cannot flood the pack."""

MAX_NAMED_FILES = 15
_HISTORY_COMMITS = "200"
_HOTSPOT_COMMITS = "400"
MIN_STEM_LENGTH = 3
MIN_CHURN_COMMITS = 20
"""Fewer local commits than this is too little history to rank churn on."""

METHOD_WARNING = (
    "Method: reference evidence in this pack comes from a textual search for "
    "each scope file's path, dotted module path and file stem across the "
    "repository's code files. It is not a resolved import graph — no target "
    "code was parsed, imported or run — so a same-named symbol in an unrelated "
    "module is reported (over-reporting) and an aliased or dynamically formed "
    "reference is not (under-reporting). Co-change evidence counts files "
    "appearing in the same local git commits as a scope file: correlation in "
    "history, not a dependency."
)

ENTRY_POINT_SEARCH_WARNING = (
    "Entry points were looked for in these packaging manifests: {manifests}; "
    "by these declaration markers: {markers}; and in entry-point-shaped files "
    "({shapes}) surfaced by the reference search. An unfilled package-manifest "
    "role is named in sources_missing."
)

CO_CHANGE_WARNING = (
    "Files that changed alongside the scope file(s) within the last {commits} "
    "local commits (number of commits they shared, not a dependency): {items}. "
    "History is not followed across renames, so a file renamed inside this "
    "window contributes only under its current name."
)

HOTSPOT_WARNING = (
    "Repository change hotspots from the last {commits} local commits (number "
    "of commits touching each file): {items}."
)

SHALLOW_CLONE_WARNING = (
    "This is a shallow clone: history-derived evidence covers only the commits "
    "present locally, so the counts above are partial rather than a total."
)

SCAN_CAP_WARNING = (
    "The reference sweep stopped at its ceiling of {cap} repository file(s); "
    "files beyond it were never opened, so an absence of referencing lines "
    "below is bounded by that ceiling rather than a repository-wide result."
)

SCOPE_TRUNCATION_WARNING = (
    "The resolved scope named {total} files; reference and history evidence "
    "was expanded from the first {kept} of them only."
)

UNRESOLVED_SCOPE_WARNING = (
    "The {scope} scope could not be resolved, most likely because its required "
    "selector was not supplied. No evidence was gathered; this pack is not "
    "whole-repository output."
)

UNRESOLVED_SCOPE_REASON = (
    "not examined: the {scope} scope could not be resolved "
    "(its required selector was not supplied)"
)

PROJECT_SCOPE_REASON = (
    "not examined in project scope: expanding every file against every other "
    "file is quadratic, so project scope reports repository-wide hotspots instead"
)

CHURN_WARNING = (
    "Churn ranking: the top 10% of the {ranked} tracked file(s) committed in the "
    "last {commits} local commit(s) is the first {top} by commit count (ties by "
    "path), whatever the scope; changed files in it: {hot}."
)

EMPTY_SCOPE_REASON = "examined: the resolved {kind} scope named no files"

#: Lines in a packaging manifest that declare an executable entry point.
_ENTRY_POINT_MARKERS: tuple[str, ...] = (
    "[project.scripts]",
    "[project.gui-scripts]",
    "[project.entry-points",
    "console_scripts",
    "entry_points",
    "[[bin]]",
    '"bin"',
    '"exports"',
    '"main"',
    "module ",
)

#: File shapes that usually *are* an entry point, named in the search warning so
#: the caller knows what a referencing hit in one of them means.
_ENTRY_POINT_SHAPES: tuple[str, ...] = (
    "__init__.py",
    "__main__.py",
    "main.*",
    "cli.*",
    "app.*",
    "server.*",
    "routes.*",
    "urls.py",
    "index.*",
)

_MANIFEST_MARKER = re.compile(
    "|".join(re.escape(marker) for marker in _ENTRY_POINT_MARKERS)
)

MAX_QUOTED_LINE_CHARS = 300
_LINE_CLIP = " …[line clipped]"

_COMMIT_MARK = "\x1f"
"""Prefix marking a commit header line in ``--name-only`` output.

A unit separator rather than a NUL: a NUL cannot be passed in an argv entry at
all (``ValueError: embedded null byte``), and no file path contains this byte."""


def collect(context: DimensionContext) -> Iterator[Excerpt]:
    """Yield reachability evidence for the active scope, lazily.

    Every non-yield side effect — warnings, misses, git history — happens
    *before* the first yield of the reference sweep. The byte budget abandons
    this generator at its first rejection, so bookkeeping recorded after a yield
    can silently never be recorded at all.
    """
    resolved_scope = context.resolved_scope
    scope_kind = getattr(resolved_scope, "kind", None)

    # A narrow scope that never resolved is a failure, not an invitation to read
    # the whole repository: `run_dimension` collapses `ScopeError` into
    # `resolved_scope = None`, so "unresolved" and "project" arrive here looking
    # alike, and only the requested scope name tells them apart.
    if resolved_scope is None and context.scope != "project":
        _warn(context, UNRESOLVED_SCOPE_WARNING.format(scope=context.scope))
        reason = UNRESOLVED_SCOPE_REASON.format(scope=context.scope)
        for source in SOURCES_SOUGHT:
            _miss(context, source, reason)
        return

    repo = Path(context.repo_path)
    _warn(context, METHOD_WARNING)
    _warn(
        context,
        ENTRY_POINT_SEARCH_WARNING.format(
            manifests=", ".join(context.role_files.get(MANIFEST_ROLE, ()))
            or "none matched the package-manifest role",
            markers=", ".join(_ENTRY_POINT_MARKERS),
            shapes=", ".join(_ENTRY_POINT_SHAPES),
        ),
    )

    whole_repo = resolved_scope is None or scope_kind == "project"
    if whole_repo:
        _project_history(context, repo)
        _miss(context, REFERENCES_SOURCE, PROJECT_SCOPE_REASON)
        _miss(context, CO_CHANGE_SOURCE, PROJECT_SCOPE_REASON)
        yield from _entry_point_excerpts(context)
        return

    all_scope_files = tuple(getattr(resolved_scope, "files", ()) or ())
    scope_files = all_scope_files[:MAX_SCOPE_FILES]
    if len(all_scope_files) > len(scope_files):
        _warn(
            context,
            SCOPE_TRUNCATION_WARNING.format(
                total=len(all_scope_files), kept=len(scope_files)
            ),
        )

    if not scope_files:
        empty = EMPTY_SCOPE_REASON.format(kind=scope_kind)
        _miss(context, REFERENCES_SOURCE, empty)
        _miss(context, CO_CHANGE_SOURCE, empty)
        yield from _entry_point_excerpts(context)
        return

    compat_excerpts = _compat_evidence(context, resolved_scope)
    _co_change_history(context, repo, scope_files)
    _churn_ranking(context, repo, scope_files)
    yield from compat_excerpts
    yield from _entry_point_excerpts(context)
    yield from _reference_excerpts(context, scope_files)


# --------------------------------------------------------------------------
# textual reference search
# --------------------------------------------------------------------------


def _reference_excerpts(
    context: DimensionContext, scope_files: tuple[str, ...]
) -> Iterator[Excerpt]:
    """Yield one excerpt per citing line, scanning the repository once.

    The naive shape of this dimension is O(scope files x repository files) and
    materialises everything before the budget sees any of it. One pattern over
    all scope files, one pass over the repository, and a yield per match keeps
    it O(repository files) *and* abandonable: when the budget stops pulling,
    the remaining files are never opened (AC #8).
    """
    pattern = _reference_pattern(scope_files)
    if pattern is None:
        _miss(
            context,
            REFERENCES_SOURCE,
            "examined: no searchable name could be derived from the scope files",
        )
        return

    in_scope = frozenset(scope_files)
    matched = False
    scanned = 0

    for candidate in context.iter_code_sources(limit=MAX_SCAN_FILES):
        scanned += 1
        text = context.read_source(candidate)
        if text is None:
            continue
        # Self-reference is excluded per *pair*, not per file: a scope file's
        # own name on its own line is not evidence, but one changed file
        # referencing another changed file is exactly the reach being asked
        # about, and dropping the whole file would lose it.
        own = _tokens_for(candidate) if candidate in in_scope else frozenset()
        for excerpt in _matching_lines(candidate, text, pattern, own):
            if not matched:
                # Recorded before the first yield: the budget may abandon this
                # generator immediately afterwards, and a source that produced
                # evidence must never also be reported as a miss.
                matched = True
                context.sources_found.append(REFERENCES_SOURCE)
            yield excerpt

    # The sweep is bounded by MAX_SCAN_FILES, and a sweep that hit that ceiling
    # did not finish. Reporting its emptiness as a plain "checked and found
    # nothing" would state a repository-wide absence the sweep never
    # established — the relevance-blind-cap defect class (T008 P1a), in the one
    # place this dimension is asked to be honest (AC #5: it may over-report,
    # but it may not go silent).
    capped = scanned >= MAX_SCAN_FILES
    reach = getattr(context, "reach", None)
    if reach is not None:
        context.reach = replace(reach, sweep_capped=capped)
    if capped:
        _warn(context, SCAN_CAP_WARNING.format(cap=MAX_SCAN_FILES))

    if not matched:
        # "Checked and found nothing" is a different statement from "not
        # checked" (AC #3), and both are different from "checked as far as the
        # ceiling allowed".
        bound = (
            f"examined: no referencing line was found in the {scanned} repository "
            f"file(s) scanned for the {len(scope_files)} scope file(s), and the "
            f"sweep stopped at its ceiling of {MAX_SCAN_FILES} file(s) — files "
            "beyond it were never opened"
            if capped
            else f"examined: no referencing line was found in the {scanned} "
            f"repository file(s) scanned for the {len(scope_files)} scope file(s)"
        )
        _miss(context, REFERENCES_SOURCE, bound)


def _tokens_for(path: str) -> frozenset[str]:
    """Every searchable name of one file: path, module path and bare stem.

    Deliberately blunt. A stem that is an ordinary English word over-matches,
    which :data:`METHOD_WARNING` states rather than silently narrowing away
    real references. Dunder stems (``__init__``) are excluded because they name
    every package in the tree rather than this file.
    """
    pure = PurePosixPath(path)
    without_suffix = path[: -len(pure.suffix)] if pure.suffix else path
    tokens = {path, without_suffix, without_suffix.replace("/", ".")}
    # A leading source root (`src/`, `lib/`) is not part of the import path any
    # language actually writes.
    head, _, tail = without_suffix.partition("/")
    if tail and head in {"src", "lib", "app"}:
        tokens.add(tail.replace("/", "."))
    if len(pure.stem) >= MIN_STEM_LENGTH and not pure.stem.startswith("__"):
        tokens.add(pure.stem)
    return frozenset(token for token in tokens if token)


def _reference_pattern(scope_files: tuple[str, ...]) -> re.Pattern[str] | None:
    """One alternation over the searchable names of every scope file.

    One pattern, not one per scope file: that is what turns the naive
    O(scope files x repository files) sweep into a single lazy pass.
    """
    tokens: set[str] = set()
    for path in scope_files:
        tokens |= _tokens_for(path)
    if not tokens:
        return None
    # Longest first, so a path match wins over its own stem inside the same
    # alternation and the quoted line is chosen by the most specific name.
    ordered = sorted(tokens, key=lambda token: (-len(token), token))
    return re.compile(r"\b(?:" + "|".join(re.escape(t) for t in ordered) + r")\b")


def _matching_lines(
    path: str,
    text: str,
    pattern: re.Pattern[str],
    own_tokens: frozenset[str],
) -> Iterator[Excerpt]:
    """Up to :data:`MAX_MATCHES_PER_FILE` citing lines, 1-indexed.

    A line whose only matches are the file's *own* names is not a reference to
    anything and is skipped.
    """
    found = 0
    for number, line in enumerate(text.splitlines(), start=1):
        hits = [match.group(0) for match in pattern.finditer(line)]
        if not hits or all(hit in own_tokens for hit in hits):
            continue
        yield Excerpt(
            path=path,
            start_line=number,
            end_line=number,
            text=_clip(line),
        )
        found += 1
        if found >= MAX_MATCHES_PER_FILE:
            return


def _clip(line: str) -> str:
    stripped = line.rstrip()
    if len(stripped) <= MAX_QUOTED_LINE_CHARS:
        return stripped
    return stripped[:MAX_QUOTED_LINE_CHARS] + _LINE_CLIP


# --------------------------------------------------------------------------
# entry points
# --------------------------------------------------------------------------


def _entry_point_excerpts(context: DimensionContext) -> Iterator[Excerpt]:
    """Cite the lines of each packaging manifest that declare an entry point.

    A manifest that exists but declares nothing still counts as read: the
    absence of a declaration is itself the answer, and ``files_read`` records
    that it was looked at.
    """
    for manifest in context.role_files.get(MANIFEST_ROLE, ()):
        text = context.read_source(manifest)
        if text is None:
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            if _MANIFEST_MARKER.search(line):
                yield Excerpt(
                    path=manifest,
                    start_line=number,
                    end_line=number,
                    text=_clip(line),
                )


# --------------------------------------------------------------------------
# git history — read-only, local only
# --------------------------------------------------------------------------


def _co_change_history(
    context: DimensionContext, repo: Path, scope_files: tuple[str, ...]
) -> None:
    """Count files committed alongside the scope files, in local history."""
    if not _is_git_repo(repo):
        _miss(
            context,
            CO_CHANGE_SOURCE,
            "not examined: the target is not a git repository, so there is no "
            "local history to derive co-change evidence from",
        )
        return

    own = frozenset(scope_files)
    counts: dict[str, int] = {}
    commits = 0
    for names in _commit_file_sets(repo, _HISTORY_COMMITS):
        commits += 1
        if not names & own:
            continue
        for name in names - own:
            counts[name] = counts.get(name, 0) + 1

    if not counts:
        reason = (
            f"examined: no other file appeared in the {commits} most recent local "
            "commit(s) alongside the scope file(s)"
            if commits
            else "examined: local history named no files (an empty or "
            "single-commit repository looks like this)"
        )
        _miss(context, CO_CHANGE_SOURCE, reason)
        return

    context.sources_found.append(CO_CHANGE_SOURCE)
    _warn(
        context,
        CO_CHANGE_WARNING.format(commits=_HISTORY_COMMITS, items=_rank(counts)),
    )
    _note_shallow(context, repo)


def _project_history(context: DimensionContext, repo: Path) -> None:
    """Repository-wide hotspots: the most frequently committed files (AC #7)."""
    if not _is_git_repo(repo):
        _miss(
            context,
            HOTSPOT_SOURCE,
            "not examined: the target is not a git repository, so there is no "
            "local history to derive hotspots from",
        )
        return

    counts: dict[str, int] = {}
    for names in _commit_file_sets(repo, _HOTSPOT_COMMITS):
        for name in names:
            counts[name] = counts.get(name, 0) + 1

    if not counts:
        _miss(
            context,
            HOTSPOT_SOURCE,
            "examined: local history named no files (an empty or single-commit "
            "repository looks like this)",
        )
        return

    context.sources_found.append(HOTSPOT_SOURCE)
    _warn(
        context,
        HOTSPOT_WARNING.format(commits=_HOTSPOT_COMMITS, items=_rank(counts)),
    )
    _note_shallow(context, repo)


def _churn_ranking(
    context: DimensionContext, repo: Path, scope_files: tuple[str, ...]
) -> None:
    """Place the scope files in the repository-wide churn ranking (T052).

    The ranking is over every tracked file, never the scope, so the share of
    changed files in the top 10% is a measurement rather than 10% by
    construction. Computed once per context: the budget calls ``collect`` once
    per tier pass, and the answer cannot change between passes.
    """
    if getattr(context, "reach", None) is not None:
        return
    changed = []
    for path in scope_files:
        if context.read_source(path) is not None:
            changed.append(redact(path))
    unavailable = _churn_unavailable(repo)
    if unavailable is not None:
        context.reach = ReachFacts(
            changed=tuple(changed), churn_unavailable=unavailable
        )
        _miss(context, HOTSPOT_SOURCE, unavailable)
        return

    counts: dict[str, int] = {}
    commits = 0
    for names in _commit_file_sets(repo, _HOTSPOT_COMMITS):
        commits += 1
        for name in names:
            counts[name] = counts.get(name, 0) + 1
    if commits < MIN_CHURN_COMMITS:
        reason = (
            f"examined: only {commits} local commit(s), fewer than the "
            f"{MIN_CHURN_COMMITS} a churn ranking needs, so no file is called a "
            "hotspot"
        )
        context.reach = ReachFacts(changed=tuple(changed), churn_unavailable=reason)
        _miss(context, HOTSPOT_SOURCE, reason)
        return

    ok, out, _ = _run_git(repo, ["ls-files"])
    tracked = set(out.splitlines()) if ok else set()
    ranked = sorted(
        (name for name in counts if name in tracked),
        key=lambda name: (-counts[name], name),
    )
    top = math.ceil(len(ranked) / 10)
    hot = {redact(name) for name in ranked[:top]}
    hot_changed = tuple(path for path in changed if path in hot)
    context.reach = ReachFacts(
        changed=tuple(changed),
        hotspots_changed=hot_changed,
        commits=commits,
        ranked_files=len(ranked),
        hotspot_count=top,
    )
    context.sources_found.append(HOTSPOT_SOURCE)
    _warn(
        context,
        CHURN_WARNING.format(
            ranked=len(ranked),
            commits=commits,
            top=top,
            hot=", ".join(hot_changed) or "none",
        ),
    )


def _churn_unavailable(repo: Path) -> str | None:
    """Why no churn ranking can be built here, or ``None``."""
    if not _is_git_repo(repo):
        return (
            "not examined: the target is not a git repository, so there is no "
            "local history to rank churn on"
        )
    ok, out, _ = _run_git(repo, ["rev-parse", "--is-shallow-repository"])
    if ok and out.strip() == "true":
        return (
            "not examined: this is a shallow clone, so local history is partial "
            "and a churn ranking over it would be a guess"
        )
    return None


def _commit_file_sets(repo: Path, limit: str) -> Iterator[frozenset[str]]:
    """Yield the file set of each of the last ``limit`` local commits.

    One ``git log`` for the whole window, rather than one per scope file: the
    co-occurrence counts and the hotspot counts are both derived from this same
    parse, and a per-file query with ``--follow`` cannot produce them at all —
    a pathspec filters the ``--name-only`` list down to the queried path, which
    is precisely the file that must be excluded from its own co-change count.
    The cost is that history is not followed across renames; that limitation is
    stated in :data:`CO_CHANGE_WARNING` rather than left for the caller to
    discover.
    """
    ok, out, _ = _run_git(
        repo, ["log", "--name-only", f"--format={_COMMIT_MARK}%H", "-n", limit]
    )
    if not ok:
        return

    names: set[str] = set()
    started = False
    for line in out.splitlines():
        if line.startswith(_COMMIT_MARK):
            if started:
                yield frozenset(names)
            names = set()
            started = True
            continue
        if line:
            names.add(line)
    if started:
        yield frozenset(names)


def _note_shallow(context: DimensionContext, repo: Path) -> None:
    ok, out, _ = _run_git(repo, ["rev-parse", "--is-shallow-repository"])
    if ok and out.strip() == "true":
        _warn(context, SHALLOW_CLONE_WARNING)


def _rank(counts: dict[str, int]) -> str:
    """The highest counts first, ties broken by path, as ``path (n)``."""
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    named = ordered[:MAX_NAMED_FILES]
    rendered = ", ".join(f"{redact(path)} ({count})" for path, count in named)
    if len(ordered) > len(named):
        rendered += f", and {len(ordered) - len(named)} more"
    return rendered


def _is_git_repo(repo: Path) -> bool:
    ok, _, _ = _run_git(repo, ["rev-parse", "--git-dir"])
    return ok


def _run_git(repo: Path, args: list[str]) -> tuple[bool, str, str]:
    """Run one read-only git subcommand against the target repository.

    Never ``shell=True``, always an explicit argument list, and only ``log``,
    ``ls-files`` and ``rev-parse`` are ever asked for — nothing here contacts a
    remote (NFR-012), and nothing from the target repository is executed
    (NFR-007) — the shared
    :func:`~easy_verifier.core.git.run_git_text` disarms repo-config programs.
    """
    return run_git_text(repo, args)


# --------------------------------------------------------------------------
# backward compatibility (T055, area #5) — read from the scope's diff
# --------------------------------------------------------------------------

MAX_COMPAT_LISTED = 20
"""#5 items quoted per kind; the rest are counted, not quoted (NFR-009)."""

MIGRATION_DIRS = frozenset(
    {"migrations", "migration", "migrate", "alembic", "changelog"}
)
"""Directory names (any case) that make a file a schema migration: Django,
Laravel, Prisma, Knex and golang-migrate ``migrations/``, Flyway
``db/migration/``, Rails ``db/migrate/``, Alembic ``alembic/``, Liquibase
``db/changelog/``."""

_DESTRUCTIVE = re.compile(
    r"\bdrop\s+(?:table|column|schema|database)\b"
    r"|\brename\s+(?:column|to)\b"
    r"|\b(?:drop|remove|delete|rename)_?(?:table|column|field|model)s?"
    r"(?:_?if_?exists)?\b"
    r"|\bdrop_?if_?exists\b",
    re.IGNORECASE,
)
"""SQL DDL (``DROP TABLE``/``COLUMN``, ``RENAME COLUMN``/``TO``) and the
migration APIs named after it: ``drop_table``/``remove_column`` (Rails,
Alembic), ``RemoveField``/``DeleteModel``/``RenameField`` (Django),
``dropColumn``/``renameColumn``/``dropIfExists`` (Knex, Laravel, Sequelize),
``DropColumn``/``RenameTable`` (EF Core)."""

_DOWN_START = re.compile(r"\b(?:down|downgrade)\b\s*(?:[=(:]|$)", re.IGNORECASE)
_UP_START = re.compile(r"\b(?:up|upgrade|change)\b\s*(?:[=(:]|$)", re.IGNORECASE)
_COMMENT_LINE = re.compile(r"^\s*(?:--|#|//|/\*|\*)")
_HUNK = re.compile(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@")
_IDENT = re.compile(r"[\w$]+")

COMPAT_METHOD = (
    "Backward-compatibility evidence (#5) is read from the diff of the changes "
    "scope, textually: a removed line of a non-test code file that starts with "
    "one of its language's registry public_declarations tokens is a removed "
    "public declaration unless a public declaration of the same name is added "
    "anywhere in the change (moved or re-signatured), and 'renamed' when its "
    "hunk adds a public declaration under a new name; renamed files are not "
    "counted. An added line of a migration file (a directory named "
    "migrations, migration, migrate, alembic or changelog) naming a destructive "
    "operation (DROP TABLE/COLUMN, RENAME COLUMN/TO, drop_table, remove_column, "
    "RemoveField, DeleteModel, RenameField, dropColumn, dropIfExists, ...) is a "
    "destructive migration operation, except in comment lines, in a "
    "down/downgrade section and in a *.down.* or Flyway undo file. A "
    "secret-bearing file (DDR-0002) is named, never parsed or quoted."
)


def _compat_evidence(context: DimensionContext, scope: object) -> tuple[Excerpt, ...]:
    """Read the #5 facts from the scope's diff once, and return their excerpts.

    Cached on the context: the budget calls ``collect`` once per tier pass.
    Only ``changes`` scope carries a diff; every other scope leaves
    ``context.compat`` unset and the metric names the scope.
    """
    cached = getattr(context, "_compat_excerpts", None)
    if cached is not None:
        return cached
    excerpts: tuple[Excerpt, ...] = ()
    if getattr(scope, "kind", None) == KIND_CHANGES:
        diff = getattr(scope, "diff", None)
        if diff is None:
            notes = "; ".join(getattr(scope, "notes", ()) or ()) or "git diff failed"
            context.compat = CompatFacts(
                unavailable=f"the changes scope carries no diff ({redact(notes)})"
            )
        else:
            clipped = any("clipped" in note for note in getattr(scope, "notes", ()))
            context.compat, excerpts = _read_diff(diff, clipped=clipped)
            _warn(context, COMPAT_METHOD)
    context._compat_excerpts = excerpts
    return excerpts


def _read_diff(
    diff: str, *, clipped: bool
) -> tuple[CompatFacts, tuple[Excerpt, ...]]:
    tables = curated_metric_tables()
    parsed = _diff_files(diff)
    secret = tuple(redact(item["path"]) for item in parsed if item["secret"])
    files = [item for item in parsed if not item["secret"]]
    added_names: set[str] = set()
    removed: list[tuple[str, int, str, str, int]] = []
    ops: list[tuple[str, int, str, str]] = []
    renamed: list[str] = []
    undeclared: list[str] = []
    for item in files:
        path = item["path"]
        kind = code_kind(path, tables)
        if item["renamed"] and kind is not None:
            renamed.append(redact(path))
        if kind == "source":
            pattern = tables.public_declarations.get(PurePosixPath(path).suffix)
            if pattern is None:
                if item["lines"]:
                    undeclared.append(redact(path))
                continue
            for sign, number, text, hunk in item["lines"]:
                name = _declared_name(pattern, text)
                if name is None:
                    continue
                if sign == "+":
                    added_names.add(name)
                elif sign == "-":
                    removed.append((item["old_path"], number, text, name, hunk))
        if _is_migration(path):
            ops.extend(_destructive_ops(item))

    hunks_adding: dict[int, set[str]] = {}
    for item in files:
        pattern = tables.public_declarations.get(PurePosixPath(item["path"]).suffix)
        for sign, _number, text, hunk in item["lines"] if pattern else ():
            if sign == "+" and (name := _declared_name(pattern, text)):
                hunks_adding.setdefault(hunk, set()).add(name)
    removed_names = {name for _p, _n, _t, name, _h in removed}
    gone = [entry for entry in removed if entry[3] not in added_names]
    symbol_items, symbol_excerpts = [], []
    for path, number, text, name, hunk in gone[:MAX_COMPAT_LISTED]:
        renamed_to = sorted(hunks_adding.get(hunk, set()) - removed_names)
        how = f"renamed (to {renamed_to[0]})" if renamed_to else "removed"
        excerpt = Excerpt(path, number, number, _clip("-" + text))
        symbol_excerpts.append(excerpt)
        symbol_items.append(
            DiffItem(ref=_safe_ref(excerpt), detail=redact(f"{name} {how}"))
        )
    op_items, op_excerpts = [], []
    for path, number, text, status in ops[:MAX_COMPAT_LISTED]:
        excerpt = Excerpt(path, number, number, _clip("+" + text))
        op_excerpts.append(excerpt)
        op_items.append(DiffItem(ref=_safe_ref(excerpt), detail=status))

    incomplete = None
    if clipped:
        incomplete = (
            f"the diff was clipped at its ceiling of {MAX_DIFF_CHARS} characters, "
            "so lines beyond it were never read"
        )
    elif undeclared:
        incomplete = (
            f"{len(undeclared)} changed code file(s) are in a language whose "
            "registry entry declares no public_declarations, so their removed "
            "declarations could not be recognised: " + ", ".join(undeclared[:5])
        )
    facts = CompatFacts(
        removed_symbols=tuple(symbol_items),
        removed_symbols_total=len(gone),
        destructive_ops=tuple(op_items),
        destructive_ops_total=len(ops),
        examined=tuple(redact(item["path"]) for item in files),
        renamed_code_files=tuple(renamed),
        secret_excluded=secret,
        incomplete=incomplete,
    )
    return facts, (*symbol_excerpts, *op_excerpts)


def _diff_files(diff: str) -> list[dict]:
    """Per file of a unified ``git diff``: paths, status and hunk lines.

    Each line is ``(sign, line number, text, hunk id)``: the old-side number
    for a removed line, the new-side number otherwise. ``---``/``+++`` are
    headers only before a file's first hunk: inside one, ``--- x`` is a
    removed ``-- x`` (an SQL comment).
    """
    files: list[dict] = []
    current: dict | None = None
    old = new = hunk = 0
    for line in diff.split("\n"):
        if line.startswith("diff --git "):
            a, _, b = line[len("diff --git ") :].partition(" b/")
            path = b.strip('"')
            old_path = a.strip('"').removeprefix("a/")
            current = {
                "path": path,
                "old_path": old_path,
                "status": "modified",
                "renamed": False,
                "lines": [],
                "in_hunk": False,
                # DDR-0002: a secret-bearing file's hunks are never read.
                "secret": _is_secret_bearing(path) or _is_secret_bearing(old_path),
            }
            files.append(current)
            continue
        if current is None:
            continue
        if not current["in_hunk"]:
            if line.startswith("new file mode"):
                current["status"] = "added"
            elif line.startswith("deleted file mode"):
                current["status"] = "deleted"
            elif line.startswith("rename from "):
                current["renamed"] = True
                current["old_path"] = line[len("rename from ") :]
                current["secret"] = current["secret"] or _is_secret_bearing(
                    current["old_path"]
                )
        match = _HUNK.match(line)
        if match:
            old, new = int(match[1]), int(match[2])
            hunk += 1
            current["in_hunk"] = True
            continue
        if current["secret"] or not current["in_hunk"] or line.startswith("\\"):
            continue
        if line.startswith("-"):
            current["lines"].append(("-", old, line[1:], hunk))
            old += 1
        elif line.startswith("+"):
            current["lines"].append(("+", new, line[1:], hunk))
            new += 1
        elif line.startswith(" "):
            current["lines"].append((" ", new, line[1:], hunk))
            old += 1
            new += 1
    return files


def _declared_name(pattern: re.Pattern[str], text: str) -> str | None:
    """The name a public-declaration token declares on ``text``, or ``None``.

    The identifier the token ends inside, else the next one after it; a token
    ending in ``(`` (``public * * (``) names the last identifier it matched.
    """
    if len(text) > MAX_LINE_CHARS:
        return None
    match = pattern.match(text)
    if match is None:
        return None
    matched, end = match.group(0), match.end()
    inside = _IDENT.findall(matched)
    if matched.endswith("("):
        return inside[-1] if inside else None
    if end < len(text) and _IDENT.match(text, end) and _IDENT.match(matched[-1:]):
        start = end
        while start > 0 and _IDENT.match(text[start - 1]):
            start -= 1
        return _IDENT.match(text, start).group(0)
    following = _IDENT.match(text[end:].lstrip())
    if following:
        return following.group(0)
    return inside[-1] if inside else None


def _is_migration(path: str) -> bool:
    pure = PurePosixPath(path)
    if ".down." in pure.name or re.match(r"U\d", pure.name):
        return False
    return any(part.lower() in MIGRATION_DIRS for part in pure.parts[:-1])


def _destructive_ops(item: dict) -> list[tuple[str, int, str, str]]:
    """Destructive operations on added lines, outside down sections."""
    status = (
        "in a new migration file"
        if item["status"] == "added"
        else "in an edited migration file (an existing migration was changed)"
    )
    found = []
    down = False
    for sign, number, text, _hunk in item["lines"]:
        if sign == "-":
            continue
        if _DOWN_START.search(text):
            down = True
        elif _UP_START.search(text):
            down = False
        if sign != "+" or down or _COMMENT_LINE.match(text):
            continue
        hit = _DESTRUCTIVE.search(text)
        if hit:
            found.append((item["path"], number, text, f"{hit.group(0)} {status}"))
    return found


def _safe_ref(excerpt: Excerpt) -> str:
    """The ref this excerpt carries in the pack, after path redaction."""
    return f"{redact(excerpt.path)}:{excerpt.start_line}-{excerpt.end_line}"


# --------------------------------------------------------------------------
# bookkeeping
# --------------------------------------------------------------------------


def _warn(context: DimensionContext, message: str) -> None:
    """Append a pack warning once, however many budget passes call ``collect``."""
    if message not in context.warnings:
        context.warnings = (*context.warnings, message)


def _miss(context: DimensionContext, source: str, reason: str) -> None:
    """Record a declared source that produced no evidence, once per source."""
    if any(miss.source == source for miss in context.sources_missing):
        return
    context.sources_missing.append(SourceMiss(source=source, reason=reason))


DESCRIPTOR = DimensionDescriptor(
    name=NAME,
    purpose=PURPOSE,
    sources_sought=SOURCES_SOUGHT,
    collect=collect,
    roles=ROLES,
)
