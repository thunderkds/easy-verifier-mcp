"""The ``solution-fit`` dimension (FR-010, doc-shaped).

Static descriptor data plus one ``collect`` generator, sharing extraction with
``architecture``, ``requirement-fidelity`` and ``code-quality`` via
``_doc_extract``. No base class, no registry, no subclassing.
"""

from __future__ import annotations

from collections.abc import Iterator

from ..core.models import DimensionContext, DimensionDescriptor, Excerpt
from . import _doc_extract

NAME = "solution-fit"

PURPOSE = (
    "Gather the documents that state which solution was chosen and why, so the "
    "calling agent can judge whether the implementation still fits the intent "
    "behind that choice."
)

SOURCES_SOUGHT: tuple[str, ...] = (
    "PRD.md",
    "BRAINSTORMING_LOG.md",
)

MARKERS: tuple[str, ...] = (
    "user stor",
    "persona",
    "user need",
    "recommended path",
    "conclusion",
    "option",
    "selected",
)


def collect(context: DimensionContext) -> Iterator[Excerpt]:
    """Yield bounded excerpts from sections matching solution-fit markers."""
    yield from _doc_extract.iter_excerpts(context, SOURCES_SOUGHT, MARKERS)


DESCRIPTOR = DimensionDescriptor(
    name=NAME,
    purpose=PURPOSE,
    sources_sought=SOURCES_SOUGHT,
    collect=collect,
)
