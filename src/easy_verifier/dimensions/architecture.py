"""The ``architecture`` dimension (FR-010, 1 of 7).

Static descriptor data plus one ``collect`` generator. No base class, no
registry, no subclassing — and no redaction, budgeting, ordering or coverage
arithmetic, because the pipeline owns all of those.
"""

from __future__ import annotations

from typing import Iterator

from ..core.context import whole_file_excerpt
from ..core.models import DimensionContext, DimensionDescriptor, Excerpt

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


def collect(context: DimensionContext) -> Iterator[Excerpt]:
    """Yield one bounded excerpt per readable declared source.

    A generator, not a list: the pipeline stops pulling once its byte ceiling is
    reached, so sources after that point are never even opened.
    """
    for source in SOURCES_SOUGHT:
        text = context.read_source(source)
        if text is None:
            continue  # Recorded as missing by read_source. Never substituted.
        excerpt = whole_file_excerpt(source, text)
        if excerpt is not None:
            yield excerpt


DESCRIPTOR = DimensionDescriptor(
    name=NAME,
    purpose=PURPOSE,
    sources_sought=SOURCES_SOUGHT,
    collect=collect,
)
