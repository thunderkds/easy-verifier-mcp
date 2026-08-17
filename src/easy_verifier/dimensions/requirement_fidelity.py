"""The ``requirement-fidelity`` dimension (FR-010, doc-shaped).

Static descriptor data plus one ``collect`` generator, sharing extraction with
``architecture``, ``solution-fit`` and ``code-quality`` via ``_doc_extract``.
No base class, no registry, no subclassing.
"""

from __future__ import annotations

from collections.abc import Iterator

from ..core.models import DimensionContext, DimensionDescriptor, Excerpt
from . import _doc_extract

NAME = "requirement-fidelity"

PURPOSE = (
    "Gather the documents that state the declared functional and non-functional "
    "requirements and acceptance criteria, so the calling agent can judge "
    "whether the implementation is faithful to what was actually asked for."
)

SOURCES_SOUGHT: tuple[str, ...] = (
    "PRD.md",
    "REQUIREMENT.md",
    "PROJECT_SPEC.md",
)

MARKERS: tuple[str, ...] = (
    "functional requirement",
    "non-functional",
    "fr-0",
    "nfr-0",
    "acceptance criteri",
    "requirement",
    "out of scope",
)


def collect(context: DimensionContext) -> Iterator[Excerpt]:
    """Yield bounded excerpts from sections matching requirement markers."""
    yield from _doc_extract.iter_excerpts(context, SOURCES_SOUGHT, MARKERS)


DESCRIPTOR = DimensionDescriptor(
    name=NAME,
    purpose=PURPOSE,
    sources_sought=SOURCES_SOUGHT,
    collect=collect,
)
