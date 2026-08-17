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

from ..core.context import MAX_EXCERPT_LINES, MAX_LINE_CHARS
from ..core.models import DimensionContext, Excerpt

_ATX_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*$")
_SETEXT_UNDERLINE = re.compile(r"^(=+|-+)\s*$")

_LINE_TRUNCATION_MARK = " …[line truncated]"
_CLIP_MARK = "…[excerpt clipped: showing lines {start}–{end} of {total}]"


def iter_excerpts(
    context: DimensionContext, sources: Sequence[str], markers: Sequence[str]
) -> Iterator[Excerpt]:
    """Yield bounded excerpts from each declared, readable source in ``sources``.

    A source that is missing yields nothing (``read_source`` already records
    the miss). A source with no heading matching ``markers`` is still *found*
    — it simply contributes zero excerpts, because found and useful are not
    the same fact.

    ``markers`` empty is itself a declared choice, not an edge case: it means
    the dimension wants the whole (bounded) document, unfiltered, which is
    what a checklist-style dimension like ``architecture`` declares.
    """
    for source in sources:
        text = context.read_source(source)
        if text is None:
            continue
        yield from _excerpts_from_document(source, text, markers)


def _excerpts_from_document(
    path: str, text: str, markers: Sequence[str]
) -> Iterator[Excerpt]:
    lines = text.splitlines()
    if not lines:
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

    for start, end, heading in sections:
        if not _matches(heading, markers):
            continue
        excerpt = _bounded_excerpt(path, lines, start, end)
        if excerpt is not None:
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
    headings: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        atx = _ATX_HEADING.match(line)
        if atx is not None:
            headings.append((index, atx.group(2).strip()))
            continue
        if index > 0 and _SETEXT_UNDERLINE.match(line) and lines[index - 1].strip():
            # The previous line is the heading text; guard against also
            # having matched it as an ATX heading (it would have `continue`d
            # already, so no duplicate is possible here).
            headings.append((index - 1, lines[index - 1].strip()))

    if not headings:
        return []

    spans: list[tuple[int, int, str]] = []
    for position, (start, heading) in enumerate(headings):
        has_next = position + 1 < len(headings)
        end = headings[position + 1][0] - 1 if has_next else len(lines) - 1
        spans.append((start, end, heading))
    return spans


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
