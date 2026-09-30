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
from pathlib import PurePosixPath

from ..core.metric_tables import curated_metric_tables
from ..core.metrics import extends_targets, resolve_extends, type_config_sections
from ..core.models import (
    DimensionContext,
    DimensionDescriptor,
    Excerpt,
    SourceRole,
)
from ..core.roles import role
from . import _code_extract, _doc_extract

NAME = "code-quality"

PURPOSE = (
    "Gather the documents and configuration that declare this project's coding "
    "conventions, lint rules and contribution expectations, so the calling "
    "agent can judge conformance from cited evidence — nothing here computes "
    "or emits a quality assessment of its own."
)

ROLES: tuple[SourceRole, ...] = (
    role("contributing-guide"),
    role("lint-config"),
    role("format-config"),
)
"""Source roles (T026): filled by any matching file in any language."""

SOURCES_SOUGHT: tuple[str, ...] = tuple(item.name for item in ROLES)

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


MAX_TYPE_CONFIGS = 20
"""Type-checker configuration files read (T056), extended files included;
shallowest first, so a repository's root configuration is never the one cut."""

TYPE_CONFIG_CAP_WARNING = (
    "{count} in-scope type-checker configuration files exceed the cap of "
    "{cap}; the shallowest are read first, so strict_type_config_missing "
    "describes only the configurations quoted"
)


def collect(context: DimensionContext) -> Iterator[Excerpt]:
    """Yield bounded excerpts from sections matching convention markers, then
    the type checker's configuration (T056), then whole in-scope functions,
    most complex first (T050), as the last tier."""
    sources = _code_extract.source_candidates(context, "function excerpts")
    yield from _doc_extract.iter_excerpts(context, SOURCES_SOUGHT, MARKERS)
    yield from _type_config_excerpts(context)
    yield from _code_extract.function_excerpts(context, sources)


def _type_config_excerpts(context: DimensionContext) -> Iterator[Excerpt]:
    """Only the type checker's section of each in-scope registry
    ``type_config_files`` file (area #17), and the files each extends.

    Targeted excerpts, not a source role: the coverage denominator is
    unchanged (user, 2026-09-29). Reading goes through ``read_source``, so a
    secret-bearing file is refused unread (DDR-0002), and an extended path
    that leaves the repository is never formed (``resolve_extends``).
    """
    tables = curated_metric_tables()
    files = set(getattr(context.resolved_scope, "files", ()) or ())
    queue: list[tuple[str, str | None]] = [
        (path, None)
        for path in sorted(files, key=lambda item: (item.count("/"), item))
        if any(c.name.fullmatch(PurePosixPath(path).name) for c in tables.type_configs)
    ]
    if len(queue) > MAX_TYPE_CONFIGS:
        # Before the first yield: the budget may abandon this generator there.
        message = TYPE_CONFIG_CAP_WARNING.format(
            count=len(queue), cap=MAX_TYPE_CONFIGS
        )
        if message not in context.warnings:
            context.warnings = (*context.warnings, message)
    seen: set[str] = set()
    while queue and len(seen) < MAX_TYPE_CONFIGS:
        path, language = queue.pop(0)
        if path in seen:
            continue
        seen.add(path)
        text = context.read_source(path)
        if not text:
            continue
        lines = text.splitlines()
        sections = type_config_sections(path, "\n".join(lines), tables)
        spans = [(s.language, s.line, s.end_line) for s in sections]
        if language is not None and not spans:
            # An extended file that is not itself a declared type-checker
            # file keeps its extender's language, and is quoted whole.
            spans = [(language, 1, len(lines))]
        for owner, start, end in spans:
            excerpt = _code_extract._excerpt(path, lines, start - 1, end - 1)
            if excerpt is not None:
                yield excerpt
            token = tables.type_config_extends.get(owner)
            section = "\n".join(lines[start - 1 : end])
            for target in extends_targets(section, token) if token else ():
                known = [c for c in resolve_extends(path, target) if c in files]
                candidates = known or list(resolve_extends(path, target)[:1])
                queue.extend((candidate, owner) for candidate in candidates[:1])


DESCRIPTOR = DimensionDescriptor(
    name=NAME,
    purpose=PURPOSE,
    sources_sought=SOURCES_SOUGHT,
    collect=collect,
    roles=ROLES,
)
