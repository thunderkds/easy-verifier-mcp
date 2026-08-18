"""The ``architecture`` dimension (FR-010, 1 of 7).

Static descriptor data plus one ``collect`` generator. No base class, no
registry, no subclassing — and no redaction, budgeting, ordering or coverage
arithmetic, because the pipeline owns all of those.
"""

from __future__ import annotations

from collections.abc import Iterator

from ..core.models import DimensionContext, DimensionDescriptor, Excerpt
from . import _doc_extract

NAME = "architecture"

PURPOSE = (
    "Gather the documents that state how the system is structured and why, "
    "so the calling agent can judge the architecture from cited evidence."
)

SOURCES_SOUGHT: tuple[str, ...] = (
    "PROJECT_SPEC.md",
    "BRAINSTORMING_LOG.md",
    "ARCHITECTURE.md",
    "docs/architecture.md",
    "README.md",
)

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
    """
    yield from _doc_extract.iter_excerpts(context, SOURCES_SOUGHT, MARKERS)


DESCRIPTOR = DimensionDescriptor(
    name=NAME,
    purpose=PURPOSE,
    sources_sought=SOURCES_SOUGHT,
    collect=collect,
)
