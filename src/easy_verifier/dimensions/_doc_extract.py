"""Shared extraction for the four **document-shaped** dimensions only.

``architecture``, ``solution-fit``, ``requirement-fidelity`` and ``code-quality``
each declare a checklist of source paths plus a set of marker keywords, and use
this module to turn "declared source found" into bounded, citable excerpts.
``security``, ``test-strategy`` and ``blast-radius`` stay bespoke (Constraint 8,
``BRAINSTORMING_LOG.md`` § Option A post-mortem) — widening this helper to fit
them is the mistake that sank Option A.

The helper is deliberately narrow: locate a declared document, find the
sections whose heading matches one of the dimension's markers, and yield
bounded excerpts with accurate line numbers. Everything dimension-specific —
*which* markers, *which* documents — stays as descriptor data in the caller.

No dimension-specific branching lives here (AC #9): every caller goes through
the same ``iter_excerpts`` regardless of which of the four it is.
"""

from __future__ import annotations

import re
from collections.abc import Iterator, Sequence
from pathlib import Path

from ..core.context import MAX_EXCERPT_LINES, MAX_LINE_CHARS
from ..core.models import DimensionContext, Excerpt

_ATX_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*$")
_SETEXT_UNDERLINE = re.compile(r"^(=+|-+)\s*$")

_LINE_TRUNCATION_MARK = " …[line truncated]"
_CLIP_MARK = "…[excerpt clipped: showing lines {start}–{end} of {total}]"
_MARKDOWN_EXTENSIONS = frozenset({".md", ".markdown"})


def iter_excerpts(
    context: DimensionContext, sources: Sequence[str], markers: Sequence[str]
) -> Iterator[Excerpt]:
    """Yield bounded excerpts from relevant kit or standalone sources.

    A source that is missing yields nothing (``read_source`` already records
    the miss). A source with no heading matching ``markers`` is still *found*
    — it simply contributes zero excerpts, because found and useful are not
    the same fact.

    ``markers`` empty is itself a declared choice, not an edge case: it means
    the dimension wants the whole (bounded) document, unfiltered, which is
    what a checklist-style dimension like ``architecture`` declares.
    """
    if context.mode == "standalone":
        found_doc_evidence = False
        examined: set[str] = set()
        for source in context.doc_sources:
            examined.add(source)
            text = context.read_source(source)
            if text is None:
                continue
            for excerpt in _excerpts_from_document(source, text, markers):
                found_doc_evidence = True
                yield excerpt

        # A dimension's declared document names remain legitimate standalone
        # candidates even when they are outside generic README/docs discovery.
        for declared in sources:
            if declared in examined:
                continue
            for concrete, text in context.read_sources(declared):
                if concrete in examined:
                    continue
                examined.add(concrete)
                for excerpt in _excerpts_from_document(concrete, text, markers):
                    found_doc_evidence = True
                    yield excerpt

        # Code is consulted only after every discovered document proved silent
        # for this dimension. Discovery and reading both remain lazy/bounded.
        if not found_doc_evidence:
            for source in context.iter_code_sources():
                text = context.read_source(source)
                if text is None:
                    continue
                yield from _excerpts_from_document(source, text, markers)
        return

    for source in sources:
        for concrete, text in context.read_sources(source):
            yield from _excerpts_from_document(concrete, text, markers)


def _excerpts_from_document(
    path: str, text: str, markers: Sequence[str]
) -> Iterator[Excerpt]:
    lines = text.splitlines()
    if not lines:
        return

    if Path(path).suffix.lower() not in _MARKDOWN_EXTENSIONS:
        excerpt = _bounded_excerpt(path, lines, 0, len(lines) - 1)
        if excerpt is not None:
            yield excerpt
        return

    sections = _sections(lines) if markers else []
    if not sections:
        # No markers declared, or no headings at all: the whole (bounded)
        # file is the unit, so it stands in rather than being silently
        # dropped for want of a heading to match against.
        excerpt = _bounded_excerpt(path, lines, 0, len(lines) - 1)
        if excerpt is not None:
            yield excerpt
        return

    covered_until = -1
    for start, end, heading in sections:
        if not _matches(heading, markers):
            continue
        if start <= covered_until:
            continue
        excerpt = _bounded_excerpt(path, lines, start, end)
        if excerpt is not None:
            covered_until = end
            yield excerpt


def _matches(heading: str, markers: Sequence[str]) -> bool:
    lowered = heading.lower()
    return any(marker.lower() in lowered for marker in markers)


def _sections(lines: list[str]) -> list[tuple[int, int, str]]:
    """Split ``lines`` into ``(start, end, heading_text)`` spans, 0-indexed.

    Recognises ATX (``#``/``##``, emoji-prefixed text survives untouched
    because it is captured verbatim) and setext (``===``/``---`` underline)
    headings. A document with no headings returns an empty list, handled by
    the caller as the whole-file case.
    """
    headings: list[tuple[int, int, str]] = []
    for index, line in enumerate(lines):
        atx = _ATX_HEADING.match(line)
        if atx is not None:
            headings.append((index, len(atx.group(1)), atx.group(2).strip()))
            continue
        if index > 0 and _SETEXT_UNDERLINE.match(line) and lines[index - 1].strip():
            start = index - 1
            if headings and headings[-1][0] == start:
                continue
            level = 1 if line.lstrip().startswith("=") else 2
            headings.append((start, level, lines[start].strip()))

    if not headings:
        return []

    # Track the nearest later heading at each Markdown level while walking
    # backwards. This preserves nested content in O(number-of-headings) time.
    next_at_level: list[int | None] = [None] * 7
    reversed_spans: list[tuple[int, int, str]] = []
    for start, level, heading in reversed(headings):
        boundaries = [
            candidate
            for candidate in next_at_level[1 : level + 1]
            if candidate is not None
        ]
        end = min(boundaries) - 1 if boundaries else len(lines) - 1
        reversed_spans.append((start, end, heading))
        next_at_level[level] = start
    return list(reversed(reversed_spans))


def _bounded_excerpt(
    path: str, lines: list[str], start: int, end: int
) -> Excerpt | None:
    """Build one bounded, 1-indexed excerpt from ``lines[start:end + 1]``.

    Mirrors ``core.context.whole_file_excerpt``'s bounding rules (line-count
    ceiling, per-line character ceiling) applied to a section rather than a
    whole file, so a giant section under a giant document still yields a
    bounded excerpt rather than the whole thing.
    """
    section = lines[start : end + 1]
    if not section:
        return None

    kept = section[:MAX_EXCERPT_LINES]
    bounded = [
        line
        if len(line) <= MAX_LINE_CHARS
        else line[:MAX_LINE_CHARS] + _LINE_TRUNCATION_MARK
        for line in kept
    ]
    if len(section) > len(kept):
        bounded.append(
            _CLIP_MARK.format(
                start=start + 1, end=start + len(kept), total=len(section)
            )
        )

    return Excerpt(
        path=path,
        start_line=start + 1,
        end_line=start + len(kept),
        text="\n".join(bounded),
    )
