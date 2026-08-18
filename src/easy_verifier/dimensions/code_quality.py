"""The ``code-quality`` dimension (FR-010, doc-shaped).

Static descriptor data plus one ``collect`` generator, sharing extraction with
``architecture``, ``solution-fit`` and ``requirement-fidelity`` via
``_doc_extract``. No base class, no registry, no subclassing.

This is the first doc-shaped dimension whose declared sources are project
*configuration* — lint/format config and contribution conventions — rather
than pure documentation. It returns evidence about declared conventions,
never a quality judgment (FR-013): there is no lint runner here, no score, no
grade.

Because these sources can themselves be plain text (not headings-shaped), and
because a stray credential can end up in project config, this is the first
dimension to genuinely exercise DDR-0002: ``context.read_source`` refuses to
read a secret-bearing file outright (reported as ``excluded: secret-bearing``,
contents never touched), and whatever *is* read still passes through the
pipeline's redaction seam like any other excerpt.
"""

from __future__ import annotations

from collections.abc import Iterator

from ..core.models import DimensionContext, DimensionDescriptor, Excerpt
from . import _doc_extract

NAME = "code-quality"

PURPOSE = (
    "Gather the documents and configuration that declare this project's coding "
    "conventions, lint rules and contribution expectations, so the calling "
    "agent can judge conformance from cited evidence — nothing here computes "
    "or emits a quality assessment of its own."
)

SOURCES_SOUGHT: tuple[str, ...] = (
    "CONTRIBUTING.md",
    "pyproject.toml",
    "ruff.toml",
    ".flake8",
    "setup.cfg",
    ".editorconfig",
)

MARKERS: tuple[str, ...] = (
    "convention",
    "style",
    "lint",
    "format",
    "naming",
    "ruff",
    "flake8",
    "pylint",
    "black",
    "pre-commit",
)


def collect(context: DimensionContext) -> Iterator[Excerpt]:
    """Yield bounded excerpts from sections matching convention markers."""
    yield from _doc_extract.iter_excerpts(context, SOURCES_SOUGHT, MARKERS)


DESCRIPTOR = DimensionDescriptor(
    name=NAME,
    purpose=PURPOSE,
    sources_sought=SOURCES_SOUGHT,
    collect=collect,
)
