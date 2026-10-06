"""The bespoke ``reliability`` evidence dimension (T043, FR-050..052).

Areas #12 error handling, #13 retries and deadlines, #15 performance (queries
in loops only), #32 business continuity (its document only) and #6
transactions, concurrency and idempotency, which needs judgment and is quoted
as evidence for the calling agent, never scored.

It reads the in-scope source files of registry languages once, through the
code tier's priority batches (``_code_extract``), so its rule metrics are
computed over whole files (``SAMPLED_METRICS``); then it quotes the lines
around each finding, the transaction and idempotency lines, the continuity
document and the README. Which code counts as a swallowed error, an outbound
call, a deadline, a retry, a backoff, a query, a loop or a transaction is the
registry's data (``registry/curated``, ``core/metrics.reliability_findings``),
never this module's. Live behaviour (real timeouts, outages, load) cannot be
verified offline and is not examined.
"""

from __future__ import annotations

from collections.abc import Iterator

from ..core.context import whole_file_excerpt
from ..core.judge import DOCUMENTATION_RULES
from ..core.metric_tables import curated_metric_tables
from ..core.metrics import reliability_findings
from ..core.models import (
    DimensionContext,
    DimensionDescriptor,
    Excerpt,
    SourceMiss,
    SourceRole,
)
from ..core.roles import _matcher, role
from . import _code_extract

NAME = "reliability"

PURPOSE = (
    "Gather citable evidence about error handling, outbound-call deadlines, "
    "retry backoff, database queries inside loops, and transaction or "
    "idempotency code from source files, plus the business-continuity "
    "document, without judging them; live behaviour under load or outage "
    "cannot be verified offline and is not examined."
)

SOURCE = "source files of a registry language"
HTTP = "outbound HTTP client calls in source files"
DATABASE = "database access calls in source files"

ROLES: tuple[SourceRole, ...] = (
    SourceRole(name=SOURCE, patterns=()),
    SourceRole(name=HTTP, patterns=()),
    SourceRole(name=DATABASE, patterns=()),
    role("readme"),
)
"""Code evidence counts toward coverage (DDR-0011): the three pseudo-roles are
filled when the scan reads source code, finds an outbound call (or a
client-wide deadline), and finds a database query call."""

SOURCES_SOUGHT: tuple[str, ...] = tuple(item.name for item in ROLES)

CONTEXT_LINES = 2
"""Lines quoted above and below each finding, so the handler or call reads
whole in the common case."""

UNRESOLVED_SCOPE_WARNING = (
    "The {scope} scope could not be resolved, most likely because its required "
    "selector was not supplied. No evidence was gathered; this pack is not "
    "whole-repository output."
)

UNRESOLVED_SCOPE_REASON = (
    "not examined: the {scope} scope could not be resolved "
    "(its required selector was not supplied)"
)


def collect(context: DimensionContext) -> Iterator[Excerpt]:
    """Yield the finding excerpts, then transaction evidence, then the
    continuity document and the README, lazily and in relevance order."""
    resolved_scope = context.resolved_scope
    if resolved_scope is None and context.scope != "project":
        message = UNRESOLVED_SCOPE_WARNING.format(scope=context.scope)
        if message not in context.warnings:
            context.warnings = (*context.warnings, message)
        reason = UNRESOLVED_SCOPE_REASON.format(scope=context.scope)
        for source in SOURCES_SOUGHT:
            context.sources_missing.append(SourceMiss(source=source, reason=reason))
        return

    sources = _code_extract.source_candidates(context, "reliability findings")
    _code_extract.record_sample(context, NAME, sources)
    # Documents are read before the first yield: the budget may stop pulling
    # at any yield, and the documentation rule and the README role count only
    # what was read.
    documents = list(_documents(context))

    findings = getattr(context, "reliability_scan", None)
    if findings is None:
        # Once per context: the budget may call ``collect`` once per tier.
        tables = curated_metric_tables()
        findings = []
        for path, lines, _syntax in _code_extract._read(context, sources):
            found = reliability_findings(path, "\n".join(lines), tables)
            if found is not None:
                findings.append((path, lines, found))
        context.reliability_scan = findings
    _record_roles(context, sources, findings)

    for path, lines, found in findings:
        hits = (
            *found.swallowed,
            *found.unbounded_calls,
            *found.unbacked_retries,
            *found.queries_in_loops,
        )
        yield from _windows(path, lines, hits)
    for path, lines, found in findings:
        yield from _windows(path, lines, found.transactions)
    yield from documents


def _documents(context: DimensionContext) -> Iterator[Excerpt]:
    """The first readable in-scope match of each documentation rule, then
    the README role's files."""
    scope = context.resolved_scope
    scope_files = tuple(getattr(scope, "files", ()) or ())
    whole_repo = scope is None or getattr(scope, "kind", None) == "project"
    for rule in DOCUMENTATION_RULES.get(NAME, ()):
        match = _matcher(rule.patterns)
        for path in sorted(p for p in scope_files if match(p)):
            text = context.read_source(path)
            if text is None:
                continue
            excerpt = whole_file_excerpt(path, text)
            if excerpt is not None:
                yield excerpt
            break
    readmes = context.role_files.get("readme", ())
    in_bounds = readmes if whole_repo else [p for p in readmes if p in scope_files]
    if readmes and not in_bounds:
        context.sources_missing.append(
            SourceMiss(source="readme", reason="not in the resolved scope")
        )
    for path in sorted(in_bounds, key=lambda p: (p.count("/"), p))[:1]:
        text = context.read_source(path)
        excerpt = whole_file_excerpt(path, text) if text else None
        if excerpt is not None:
            yield excerpt


def _record_roles(context: DimensionContext, sources, findings) -> None:
    """Fill or name each pseudo-role from what the scan read and found;
    idempotent, since the budget may call ``collect`` once per tier."""
    read = len(findings)
    filled = {
        SOURCE: read > 0,
        HTTP: any(f.calls for _p, _l, f in findings),
        DATABASE: any(f.queries for _p, _l, f in findings),
    }
    reasons = {
        SOURCE: "not found: no in-scope source file of a registry language "
        "with structure syntax"
        if not sources
        else f"none of the {len(sources)} in-scope source file(s) could be read",
        HTTP: f"no outbound call (the registry's outbound_calls tokens) was found "
        f"in the {read} source file(s) scanned",
        DATABASE: f"no database query call (the registry's query_calls tokens) "
        f"was found in the {read} source file(s) scanned",
    }
    recorded = {m.source for m in context.sources_missing}
    for source, found in filled.items():
        if found and source not in context.sources_found:
            context.sources_found.append(source)
        elif not found and source not in recorded:
            context.sources_missing.append(
                SourceMiss(source=source, reason=reasons[source])
            )


def _windows(path: str, lines: list[str], hits) -> Iterator[Excerpt]:
    """One excerpt per run of overlapping ``CONTEXT_LINES`` windows."""
    spans: list[list[int]] = []
    for line in sorted(set(hits)):
        start = max(1, line - CONTEXT_LINES)
        end = min(len(lines), line + CONTEXT_LINES)
        if spans and start <= spans[-1][1] + 1:
            spans[-1][1] = max(spans[-1][1], end)
        else:
            spans.append([start, end])
    for start, end in spans:
        excerpt = _code_extract._excerpt(path, lines, start - 1, end - 1)
        if excerpt is not None:
            yield excerpt


DESCRIPTOR = DimensionDescriptor(
    name=NAME,
    purpose=PURPOSE,
    sources_sought=SOURCES_SOUGHT,
    collect=collect,
    roles=ROLES,
)
