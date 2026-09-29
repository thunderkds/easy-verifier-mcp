"""The ``requirement-fidelity`` dimension (FR-010, doc-shaped).

Static descriptor data plus one ``collect`` generator, sharing extraction with
``architecture``, ``solution-fit`` and ``code-quality`` via ``_doc_extract``.
No base class, no registry, no subclassing.

Kit-aware mode adds acceptance-criteria trace evidence (T052, FR-043): every
row of a ``tasks/TASK_GUIDE_Txxx.md`` "Acceptance Criteria" table and every
``FR-xxx`` defined in a requirements document is quoted at its line, then one
bounded pass over the repository's code files quotes the lines that name a
criterion's identifiers. Traces are textual and cited, never inferred: a
criterion is traced when its task ID or an ``FR-xxx`` ID in its row appears
as a whole word in a code file. Whether
that file is code or a test is decided by the metric module's shared path
classification over the registry tables (``core/metric_tables.py``). Standalone
mode extracts nothing: there, criteria would have to be inferred.

Every mode records documentation source-of-truth facts (T055, area #27): the
files filling the requirements-doc role, and how many of the recent local
commits that changed code also changed a document (read-only git, bounded by
:data:`CO_CHANGE_WINDOW`).
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import PurePosixPath

from ..core.git import run_git_text
from ..core.metric_tables import curated_metric_tables
from ..core.metrics import code_kind, trace_key_pattern
from ..core.models import (
    AcceptanceCriterion,
    DimensionContext,
    DimensionDescriptor,
    DocHistory,
    Excerpt,
    SourceRole,
    TraceSearch,
)
from ..core.redact import redact
from ..core.roles import role
from . import _doc_extract

NAME = "requirement-fidelity"

PURPOSE = (
    "Gather the documents that state the declared functional and non-functional "
    "requirements and acceptance criteria, so the calling agent can judge "
    "whether the implementation is faithful to what was actually asked for."
)

ROLES: tuple[SourceRole, ...] = (
    role("requirements-doc"),
    role("spec-doc"),
    role("task-breakdown"),
)
"""Source roles (T026): filled by any matching file in any language."""

SOURCES_SOUGHT: tuple[str, ...] = tuple(item.name for item in ROLES)

MARKERS: tuple[str, ...] = (
    "functional requirement",
    "non-functional",
    "fr-0",
    "nfr-0",
    "acceptance criteri",
    "success criteri",
    "requirement",
    "out of scope",
)

TASK_GUIDE_GLOB = "tasks/TASK_GUIDE_*.md"
MAX_TASK_GUIDES = 500
"""Task guides read for acceptance criteria; more marks the search incomplete."""

MAX_TRACE_SCAN_FILES = 2000
"""Code files walked by the trace search; more marks the search incomplete."""

MAX_UNTRACED_LISTED = 20
"""Untraced criteria listed (and quoted) per kind; the rest are counted."""

MAX_TRACE_LINES_CITED = 30
"""Trace lines quoted per kind (code, test); the rest are counted. Keeps the
pack near its pre-T052 size (NFR-009): each quoted line costs JSON overhead."""

MAX_CRITERIA = 5000
"""Criteria extracted; more marks the search incomplete (keeps the pack and
the metric's work bounded on a hostile or enormous kit)."""

MAX_QUOTED_LINE_CHARS = 240
_LINE_CLIP = " …[line clipped]"

_TASK_ID = re.compile(r"TASK_GUIDE_(T\d{3})(?!\d)")
_FR_ID = re.compile(r"(?<![\w-])FR-\d{3}[a-z]?(?![\w-])")
_FR_DEFINITION = re.compile(r"^\s*(?:[|*#-]\s*)*(?:\*\*)?(FR-\d{3}[a-z]?)(?![\w-])")
_AC_HEADING = re.compile(r"^#{1,6}\s+.*acceptance criteri", re.IGNORECASE)
_HEADING = re.compile(r"^#{1,6}\s")
_SEPARATOR_ROW = re.compile(r"^\|[\s:|-]+$")

TRACE_WARNING = (
    "Acceptance-criteria tracing: {criteria} criteria ({rows} task-guide AC "
    "row(s) from {guides} guide(s), {frs} FR ID(s) defined in requirements "
    "documents); a criterion is traced when its task ID or an FR ID in its row "
    "appears as a whole word in a code file (textual, never inferred); "
    "{searched} code file(s) searched{incomplete}."
)

_Found = tuple[str, tuple[str, ...], Excerpt]


def collect(context: DimensionContext) -> Iterator[Excerpt]:
    """Yield AC trace evidence (kit-aware), then bounded requirement excerpts."""
    if context.resolved_scope is not None or context.scope == "project":
        _doc_history(context)
    if context.mode != "standalone":
        yield from _trace_evidence(context)
    yield from _doc_extract.iter_excerpts(context, SOURCES_SOUGHT, MARKERS)


def _trace_evidence(context: DimensionContext) -> tuple[Excerpt, ...]:
    """Extract criteria and search for traces once, before anything is yielded.

    The budget calls ``collect`` once per tier pass; the result is cached on the
    context so every pass yields the same excerpts without re-reading.
    """
    cached = getattr(context, "_trace_excerpts", None)
    if cached is not None:
        return cached

    rows, guides, guides_capped = _task_guide_rows(context)
    definitions = _fr_definitions(context)
    found = rows + definitions
    too_many = len(found) > MAX_CRITERIA
    found = found[:MAX_CRITERIA]
    traces, untraced, searched, scan_capped = _search_traces(
        context, [keys for _id, keys, _excerpt in found]
    )

    incomplete = None
    if too_many:
        incomplete = f"more than {MAX_CRITERIA} criteria; only the first were kept"
    elif guides_capped:
        incomplete = (
            f"more than {MAX_TASK_GUIDES} task guides; only the first were read"
        )
    elif scan_capped:
        incomplete = (
            f"the trace search stopped at its ceiling of {MAX_TRACE_SCAN_FILES} "
            "code files; files beyond it were never opened"
        )
    listed = {
        kind: sorted(untraced[kind])[:MAX_UNTRACED_LISTED] for kind in untraced
    }
    cited = [
        excerpt
        for kind in ("source", "test")
        for excerpt in [e for k, e in traces if k == kind][:MAX_TRACE_LINES_CITED]
    ]

    def entries(kind: str) -> tuple[AcceptanceCriterion, ...]:
        return tuple(
            AcceptanceCriterion(id=found[i][0], ref=_safe_ref(found[i][2]))
            for i in listed[kind]
        )

    context.trace_search = TraceSearch(
        criteria=len(found),
        traced_to_code=len(found) - len(untraced["source"]),
        traced_to_test=len(found) - len(untraced["test"]),
        trace_lines=len(cited),
        trace_lines_omitted=len(traces) - len(cited),
        untraced_code=entries("source"),
        untraced_code_omitted=len(untraced["source"]) - len(listed["source"]),
        untraced_test=entries("test"),
        untraced_test_omitted=len(untraced["test"]) - len(listed["test"]),
        files_searched=searched,
        incomplete=incomplete,
    )
    message = TRACE_WARNING.format(
        criteria=len(found),
        rows=len(rows),
        guides=guides,
        frs=len(definitions),
        searched=searched,
        incomplete=f"; incomplete: {incomplete}" if incomplete else "",
    )
    if message not in context.warnings:
        context.warnings = (*context.warnings, message)

    quoted = sorted(set(listed["source"]) | set(listed["test"]))
    evidence = (*(found[i][2] for i in quoted), *cited)
    context._trace_excerpts = evidence
    return evidence


def _task_guide_rows(context: DimensionContext) -> tuple[list[_Found], int, bool]:
    """Every AC-table row of every task guide, in sorted guide order."""
    found: list[_Found] = []
    guides = 0
    for path, text in context.read_sources(TASK_GUIDE_GLOB):
        task = _TASK_ID.search(PurePosixPath(path).name)
        if task is None:
            continue
        if guides >= MAX_TASK_GUIDES:
            return found, guides, True
        guides += 1
        found.extend(_ac_rows(path, text, task.group(1)))
    return found, guides, False


def _ac_rows(path: str, text: str, task: str) -> Iterator[_Found]:
    """Data rows of the tables under an "Acceptance Criteria" heading.

    The first table row is the column-title row and the ``|---|`` row is the
    separator; neither is a criterion. A row's label is its first cell when
    that is a number, else its position.
    """
    in_section = False
    header_seen = False
    ordinal = 0
    for number, line in enumerate(text.splitlines(), start=1):
        if _HEADING.match(line):
            in_section = bool(_AC_HEADING.match(line))
            header_seen = False
            continue
        stripped = line.strip()
        if not in_section or not stripped.startswith("|"):
            continue
        if not header_seen:
            header_seen = True
            continue
        if _SEPARATOR_ROW.match(stripped):
            continue
        ordinal += 1
        first = stripped.strip("|").split("|", 1)[0].strip()
        label = first if first.isdigit() else str(ordinal)
        yield f"{task}#{label}", _row_keys(task, stripped), _line_excerpt(
            path, number, line
        )


def _row_keys(task: str, row: str) -> tuple[str, ...]:
    return tuple(sorted({task, *_FR_ID.findall(row)}))


def _fr_definitions(context: DimensionContext) -> list[_Found]:
    """The first line defining each ``FR-xxx`` in the requirements documents."""
    seen: set[str] = set()
    found: list[_Found] = []
    for path in context.role_files.get("requirements-doc", ()):
        text = context.read_source(path)
        if text is None:
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            match = _FR_DEFINITION.match(line)
            if match is None or match.group(1) in seen:
                continue
            seen.add(match.group(1))
            found.append(
                (match.group(1), (match.group(1),), _line_excerpt(path, number, line))
            )
    return found


def _search_traces(
    context: DimensionContext, criteria: list[tuple[str, ...]]
) -> tuple[list[tuple[str, Excerpt]], dict[str, set[int]], int, bool]:
    """One bounded pass quoting the lines that first trace each criterion.

    A line is quoted only when it traces a criterion not yet traced in a file
    of the same kind (code or test), so the evidence is at most two lines per
    criterion. Files are walked in sorted order, so the result is
    deterministic (DDR-0005).
    """
    by_key: dict[str, set[int]] = {}
    untraced = {kind: set(range(len(criteria))) for kind in ("source", "test")}
    for index, keys in enumerate(criteria):
        for key in keys:
            by_key.setdefault(key, set()).add(index)
    if not by_key:
        return [], untraced, 0, False

    pattern = trace_key_pattern(by_key)
    tables = curated_metric_tables()
    traces: list[tuple[str, Excerpt]] = []
    searched = 0
    for walked, candidate in enumerate(
        context.iter_code_sources(limit=MAX_TRACE_SCAN_FILES + 1), start=1
    ):
        if not untraced["source"] and not untraced["test"]:
            break
        if walked > MAX_TRACE_SCAN_FILES:
            return traces, untraced, searched, True
        kind = code_kind(candidate, tables)
        if kind is None or not untraced[kind]:
            continue
        searched += 1
        text = context.read_source(candidate)
        if text is None:
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            matches = list(pattern.finditer(line))
            hits = {i for match in matches for i in by_key[match.group(0)]}
            if hits & untraced[kind]:
                untraced[kind] -= hits
                traces.append(
                    (kind, _line_excerpt(candidate, number, line, matches[0].start()))
                )
    return traces, untraced, searched, False


def _line_excerpt(path: str, number: int, line: str, hit: int = 0) -> Excerpt:
    """One quoted line, clipped so the identifier at ``hit`` stays visible."""
    stripped = line.rstrip()
    if len(stripped) > MAX_QUOTED_LINE_CHARS:
        start = max(0, hit - 40) if hit > MAX_QUOTED_LINE_CHARS - 60 else 0
        clipped = stripped[start : start + MAX_QUOTED_LINE_CHARS]
        stripped = ("…" if start else "") + clipped + _LINE_CLIP
    return Excerpt(path=path, start_line=number, end_line=number, text=stripped)


CO_CHANGE_WINDOW = 200
"""Most recent non-merge local commits read for #27 co-change (T055)."""

MAX_DOCS_CITED = 20
"""Requirements documents, and co-changed documents, read and cited (#27)."""

DOC_SUFFIXES = (".md", ".rst", ".adoc", ".txt")
DOC_DIRS = frozenset({"doc", "docs"})
_COMMIT_MARK = "\x1f"

CO_CHANGE_METHOD = (
    "Documentation co-change (#27): of the last {window} non-merge local "
    "commits, a commit changes code when it touches a file the registry "
    "classifies as source or test code, and changes documentation when it "
    "touches a {suffixes} file or a file under a doc/ or docs/ directory."
)


def _doc_history(context: DimensionContext) -> None:
    """Record the #27 facts once (the budget calls ``collect`` per tier pass).

    Every read happens here, before the first yield, so ``files_read`` holds
    each cited document whatever the byte budget later keeps.
    """
    if getattr(context, "doc_history", None) is not None:
        return
    docs = context.role_files.get("requirements-doc", ())
    listed = tuple(
        redact(path)
        for path in docs[:MAX_DOCS_CITED]
        if context.read_source(path) is not None
    )
    repo = context.repo_path
    unavailable = _history_unavailable(repo)
    if unavailable is not None:
        context.doc_history = DocHistory(
            requirements_docs=listed,
            requirements_docs_total=len(docs),
            window=CO_CHANGE_WINDOW,
            history_unavailable=unavailable,
        )
        return

    tables = curated_metric_tables()
    scanned = code = with_docs = 0
    co_changed: dict[str, None] = {}
    for names in _commit_file_sets(repo):
        scanned += 1
        if not any(code_kind(name, tables) for name in names):
            continue
        code += 1
        touched = sorted(name for name in names if _is_doc(name))
        if touched:
            with_docs += 1
            co_changed.update(dict.fromkeys(touched))
    cited = []
    for path in co_changed:
        if len(cited) >= MAX_DOCS_CITED:
            break
        if context.read_source(path) is not None:
            cited.append(redact(path))
    context.doc_history = DocHistory(
        requirements_docs=listed,
        requirements_docs_total=len(docs),
        commits_scanned=scanned,
        window=CO_CHANGE_WINDOW,
        code_commits=code,
        code_commits_with_docs=with_docs,
        docs_cited=tuple(cited),
    )
    message = CO_CHANGE_METHOD.format(
        window=CO_CHANGE_WINDOW, suffixes="/".join(DOC_SUFFIXES)
    )
    if message not in context.warnings:
        context.warnings = (*context.warnings, message)


def _is_doc(path: str) -> bool:
    pure = PurePosixPath(path)
    return pure.suffix.lower() in DOC_SUFFIXES or any(
        part.lower() in DOC_DIRS for part in pure.parts[:-1]
    )


def _history_unavailable(repo: object) -> str | None:
    """Why no co-change window can be read here, or ``None``."""
    ok, out, _ = run_git_text(repo, ["rev-parse", "--is-shallow-repository"])
    if not ok:
        return (
            "not examined: the target is not a git repository, so there is no "
            "local history to read documentation co-change from"
        )
    if out.strip() == "true":
        return (
            "not examined: this is a shallow clone, so local history is partial "
            "and a co-change share over it would describe only the commits "
            "fetched"
        )
    return None


def _commit_file_sets(repo: object) -> Iterator[frozenset[str]]:
    """The file set of each of the last :data:`CO_CHANGE_WINDOW` non-merge
    commits (a merge repeats its parents' changes, so it is not counted)."""
    ok, out, _ = run_git_text(
        repo,
        [
            "log",
            "--no-merges",
            "--name-only",
            f"--format={_COMMIT_MARK}%H",
            "-n",
            str(CO_CHANGE_WINDOW),
        ],
    )
    if not ok:
        return
    names: set[str] | None = None
    for line in out.splitlines():
        if line.startswith(_COMMIT_MARK):
            if names is not None:
                yield frozenset(names)
            names = set()
        elif line and names is not None:
            names.add(line)
    if names is not None:
        yield frozenset(names)


def _safe_ref(excerpt: Excerpt) -> str:
    """The ref this excerpt carries in the pack, after path redaction."""
    return f"{redact(excerpt.path)}:{excerpt.start_line}-{excerpt.end_line}"


DESCRIPTOR = DimensionDescriptor(
    name=NAME,
    purpose=PURPOSE,
    sources_sought=SOURCES_SOUGHT,
    collect=collect,
    roles=ROLES,
)
