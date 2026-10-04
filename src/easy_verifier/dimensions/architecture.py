"""The ``architecture`` dimension (FR-010, 1 of 7).

Static descriptor data plus one ``collect`` generator. No base class, no
registry, no subclassing — and no redaction, budgeting, ordering or coverage
arithmetic, because the pipeline owns all of those.
"""

from __future__ import annotations

from collections.abc import Iterator

from ..core.models import (
    DimensionContext,
    DimensionDescriptor,
    Excerpt,
    SourceMiss,
    SourceRole,
)
from ..core.roles import role
from . import _code_extract, _doc_extract

NAME = "architecture"

PURPOSE = (
    "Gather the documents that state how the system is structured and why, "
    "so the calling agent can judge the architecture from cited evidence."
)

IMPORTS_SOURCE = "source files with import statements"
"""Code evidence counts toward coverage (T074, DDR-0011): a pseudo-source,
found when the import tier quotes at least one statement."""

ROLES: tuple[SourceRole, ...] = (
    role("architecture-doc"),
    role("decision-record"),
    role("readme"),
    SourceRole(name=IMPORTS_SOURCE, patterns=()),
)
"""Source roles (T026): filled by any matching file in any language."""

SOURCES_SOUGHT: tuple[str, ...] = tuple(item.name for item in ROLES)

MARKERS: tuple[str, ...] = ()
"""Empty on purpose (behaviour-preserving refactor, AC #8): the pre-T007
``architecture`` dimension always yielded the whole bounded document for every
found source — no section filtering. ``_doc_extract`` treats an empty marker
set as exactly that request, so this refactor changes nothing observable."""


def collect(context: DimensionContext) -> Iterator[Excerpt]:
    """Yield bounded excerpts from each readable declared source.

    A generator, not a list: the pipeline stops pulling once its byte ceiling is
    reached, so sources after that point are never even opened. Extraction is
    shared with the other three document-shaped dimensions via ``_doc_extract``
    — this module supplies only the declared sources and markers.

    Import-statement lines of in-scope source files follow as the last tier
    (T050), so the import graph is measurable from this pack.
    """
    sources = _code_extract.source_candidates(context, "import excerpts")
    _code_extract.record_sample(context, NAME)
    yield from _doc_extract.iter_excerpts(context, SOURCES_SOUGHT, MARKERS)
    found = IMPORTS_SOURCE in context.sources_found
    for excerpt in _code_extract.import_excerpts(context, sources):
        if not found:
            context.sources_found.append(IMPORTS_SOURCE)
            found = True
        yield excerpt
    recorded = any(m.source == IMPORTS_SOURCE for m in context.sources_missing)
    if not found and not recorded:
        context.sources_missing.append(
            SourceMiss(
                source=IMPORTS_SOURCE,
                reason=(
                    f"no import statement was found in the {len(sources)} "
                    "in-scope source file(s) of a registry language read for "
                    "the import tier"
                    if sources
                    else "not found: no in-scope source file of a registry "
                    "language with import syntax"
                ),
            )
        )


DESCRIPTOR = DimensionDescriptor(
    name=NAME,
    purpose=PURPOSE,
    sources_sought=SOURCES_SOUGHT,
    collect=collect,
    roles=ROLES,
)
