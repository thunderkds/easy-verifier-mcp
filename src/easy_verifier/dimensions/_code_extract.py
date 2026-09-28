"""Trailing code-evidence tiers for ``code-quality`` and ``architecture`` (T050).

T033's structure metrics (approximate CCN, import cycles) read only what a pack
quotes, and these two packs quoted docs and config only, so the metrics always
abstained. Each dimension now appends one lowest-relevance tier after its
existing document evidence:

* ``function_excerpts`` -- whole functions, most complex first (code-quality);
* ``import_excerpts`` -- import-statement lines only (architecture).

Candidates are the in-scope files ``core.metrics`` itself classifies as source
of a registry language with structure syntax, so the pack carries exactly what
the metrics can read. Reading goes through ``context.read_source`` (secret-
bearing files are refused there, unread) and every excerpt passes the
pipeline's budget and redaction like any other. Selection is deterministic:
sorted paths, then a stable key.

All or none (the T031 pattern): above :data:`MAX_CODE_SOURCES` candidates the
tier is skipped with a warning, because a silently partial file set would make
a whole-set metric describe an arbitrary subset. The byte budget can still cut
the tier; that is reported as truncation and whole-set metrics abstain
(FR-027a).
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import PurePosixPath

from ..core.context import MAX_EXCERPT_LINES, MAX_LINE_CHARS
from ..core.metric_tables import curated_metric_tables
from ..core.metrics import _is_source_file
from ..core.models import DimensionContext, Excerpt
from ..core.tokens import LanguageSyntax, approximate_ccn, import_statements

MAX_CODE_SOURCES = 200
"""Upper bound on source files read for one code tier."""

UNREAD_CODE_WARNING = (
    "{count} in-scope source files exceed the cap of {cap} for {what}; none were "
    "read, so metrics over {what} abstain rather than describe an arbitrary subset"
)


_LINE_MARK = " …[line truncated]"
_CLIP_MARK = "…[excerpt clipped: showing lines {start}–{end}]"


def function_excerpts(
    context: DimensionContext, sources: list[str]
) -> Iterator[Excerpt]:
    """Whole outermost functions of ``sources``, highest CCN first.

    Ranking needs every candidate read before the first yield, which is what
    the cap bounds. Ties break on path then line. A nested function stays
    inside its parent's excerpt and ranks the parent by the higher CCN.
    """
    ranked: list[tuple[int, str, int, Excerpt]] = []
    for path, lines, syntax in _read(context, sources):
        outermost: list[list[int]] = []  # [start, end, highest ccn inside]
        for function in approximate_ccn("\n".join(lines), syntax):
            if outermost and function.line <= outermost[-1][1]:
                outermost[-1][2] = max(outermost[-1][2], function.ccn)
            else:
                outermost.append([function.line, function.end_line, function.ccn])
        for start, end, ccn in outermost:
            excerpt = _excerpt(path, lines, start - 1, end - 1)
            if excerpt is not None:
                ranked.append((-ccn, path, start, excerpt))
    for *_key, excerpt in sorted(ranked, key=lambda item: item[:3]):
        yield excerpt


def import_excerpts(context: DimensionContext, sources: list[str]) -> Iterator[Excerpt]:
    """Import-statement lines of ``sources``, in path order, lazily.

    Each excerpt is one run of consecutive statement lines (a multi-line
    statement whole), cited by its own path and line range.
    """
    for path, lines, syntax in _read(context, sources):
        spans: list[list[int]] = []
        for line, statement in import_statements("\n".join(lines), syntax):
            end = line + statement.count("\n")
            if spans and line <= spans[-1][1] + 1:
                spans[-1][1] = max(spans[-1][1], end)
            else:
                spans.append([line, end])
        for start, end in spans:
            excerpt = _excerpt(path, lines, start - 1, end - 1)
            if excerpt is not None:
                yield excerpt


def _read(
    context: DimensionContext, sources: list[str]
) -> Iterator[tuple[str, list[str], LanguageSyntax]]:
    """``(path, lines, syntax)`` per readable source, lazily.

    Lines split on ``\\n`` only, as ``core.tokens`` does, so a function's line
    numbers are the same in the file and in the excerpt cut from it.
    """
    for path in sources:
        text = context.read_source(path)
        if text:
            lines = [line.removesuffix("\r") for line in text.split("\n")]
            yield (
                path,
                lines,
                curated_metric_tables().syntax[PurePosixPath(path).suffix],
            )


def _excerpt(path: str, lines: list[str], start: int, end: int) -> Excerpt | None:
    """1-indexed excerpt of ``lines[start:end + 1]``, bounded like every other
    excerpt (line count, per-line characters); a clipped function says so."""
    kept = lines[start : min(end, start + MAX_EXCERPT_LINES - 1) + 1]
    if not kept:
        return None
    text = [
        line if len(line) <= MAX_LINE_CHARS else line[:MAX_LINE_CHARS] + _LINE_MARK
        for line in kept
    ]
    if end - start + 1 > len(kept):
        text.append(_CLIP_MARK.format(start=start + 1, end=start + len(kept)))
    return Excerpt(
        path=path,
        start_line=start + 1,
        end_line=start + len(kept),
        text="\n".join(text),
    )


def source_candidates(context: DimensionContext, what: str) -> list[str]:
    """In-scope source files with registry syntax, sorted; ``[]`` above the cap.

    Call before the dimension's first yield: the budget may abandon the
    generator at any yield, and the warning must not be lost with it.
    """
    tables = curated_metric_tables()
    files = getattr(context.resolved_scope, "files", ()) or ()
    sources = sorted(
        path
        for path in set(files)
        if PurePosixPath(path).suffix in tables.syntax and _is_source_file(path, tables)
    )
    if len(sources) > MAX_CODE_SOURCES:
        message = UNREAD_CODE_WARNING.format(
            count=len(sources), cap=MAX_CODE_SOURCES, what=what
        )
        if message not in context.warnings:
            context.warnings = (*context.warnings, message)
        return []
    return sources
