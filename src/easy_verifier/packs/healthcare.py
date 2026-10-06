"""The optional ``healthcare`` pack (T047, DDR-0008 §4, FR-052/053).

Area #9 (PHI minimization, retention, test-data safety): PHI-shaped values
(SSN, medical record number, birth date) in test data and in log statements
are counted, over whole files; the retention policy is a documentation rule.
Area #28 (vendor, BAA, data classification, residency): documentation rules
only. Which text counts as a PHI-shaped value, a documented placeholder, test
data or a log statement is the registry's data (``registry/packs/
healthcare.toml``), never this module's.

A matched value never leaves the engine: every excerpt this pack quotes has
it replaced by ``[PHI <kind> redacted]``, and derivations name only the path,
line and kind. No hash is kept, unlike a secret's fingerprint (core/redact.py):
an SSN has about 10**9 possible values, so even a truncated hash could be
reversed by enumeration.

The pack runs only when ``roles.active_packs`` names it.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass
from functools import lru_cache

from ..core.context import whole_file_excerpt
from ..core.judge import DOCUMENTATION_RULES
from ..core.metrics import PACK_METRICS
from ..core.models import (
    DimensionContext,
    DimensionDescriptor,
    Excerpt,
    SampledMetric,
    SourceMiss,
    SourceRole,
)
from ..core.redact import redact
from ..core.registry import load_pack
from ..core.roles import _matcher
from ..dimensions import _code_extract

NAME = "healthcare"

PURPOSE = (
    "Optional healthcare pack, active only when configured or picked: gather "
    "PHI-shaped values (SSN, medical record number, birth date) found in test "
    "data and log statements, values redacted, plus the retention, business "
    "associate agreement, data classification and residency documents; "
    "whether data is real patient data, or a contract is in force, cannot be "
    "verified from a repository and is not examined."
)

TEST_DATA = "test data files (the pack's test_data_paths)"
LOGS = "log statements in source files (the pack's log_calls)"

ROLES: tuple[SourceRole, ...] = (
    SourceRole(name=TEST_DATA, patterns=()),
    SourceRole(name=LOGS, patterns=()),
)
"""Pseudo-roles credited by the scan: test data read, a log statement found."""

SOURCES_SOUGHT: tuple[str, ...] = tuple(item.name for item in ROLES)

MAX_TEST_DATA_FILES = 200
"""Test-data files read, in path order; the rest are counted and disclosed."""

MAX_LISTED = 20
"""Sites named in one derivation; the rest are counted."""

CONTEXT_LINES = 1

TEST_DATA_METRIC, LOG_METRIC = PACK_METRICS[NAME]

_METHOD = (
    "matched textually against the pack's phi_values, documented "
    "phi_placeholders excluded; values are never shown, and a count is a "
    "place to look, not proof of real patient data"
)

UNRESOLVED_SCOPE_REASON = (
    "not examined: the {scope} scope could not be resolved "
    "(its required selector was not supplied)"
)


@dataclass(frozen=True)
class _Patterns:
    values: tuple[tuple[str, re.Pattern[str]], ...]
    placeholders: tuple[re.Pattern[str], ...]
    test_data_paths: tuple[str, ...]
    log_calls: tuple[re.Pattern[str], ...]


@lru_cache(maxsize=1)
def _patterns() -> _Patterns:
    fields = load_pack(NAME).fields

    def values(field: str) -> tuple[str, ...]:
        return tuple(value for cited in fields[field] for value in cited.value)

    kinds = tuple(item.split("=", 1) for item in values("phi_values"))
    return _Patterns(
        values=tuple((kind, re.compile(body)) for kind, body in kinds),
        placeholders=tuple(re.compile(item) for item in values("phi_placeholders")),
        test_data_paths=values("test_data_paths"),
        log_calls=tuple(re.compile(item) for item in values("log_calls")),
    )


def phi_spans(line: str) -> list[tuple[int, int, str]]:
    """``(start, end, kind)`` of each PHI-shaped, non-placeholder value."""
    patterns = _patterns()
    spans = []
    for kind, pattern in patterns.values:
        for match in pattern.finditer(line):
            group = "value" if "value" in pattern.groupindex else 0
            value = match.group(group)
            if not any(p.fullmatch(value) for p in patterns.placeholders):
                spans.append((match.start(group), match.end(group), kind))
    return sorted(spans)


def mask(line: str) -> str:
    """``line`` with every PHI-shaped value replaced by its kind."""
    for start, end, kind in reversed(phi_spans(line)):
        line = f"{line[:start]}[PHI {kind} redacted]{line[end:]}"
    return line


@dataclass
class _Scan:
    data_files: list[tuple[str, list[str]]]
    data_total: int
    sources: list[tuple[str, list[str]]]
    data_hits: list[tuple[str, int, str]]
    log_hits: list[tuple[str, int, str]]
    log_lines: int


def collect(context: DimensionContext) -> Iterator[Excerpt]:
    """Yield the masked lines around each hit, then the documents."""
    if context.resolved_scope is None and context.scope != "project":
        reason = UNRESOLVED_SCOPE_REASON.format(scope=context.scope)
        for source in SOURCES_SOUGHT:
            context.sources_missing.append(SourceMiss(source=source, reason=reason))
        return

    scan = getattr(context, "phi_scan", None)
    if scan is None:
        # Once per context, before the first yield: the budget may call
        # ``collect`` once per tier and stop pulling at any yield.
        scan = _scan(context)
        context.phi_scan = scan
        context.whole_file = _metrics(scan)
    documents = list(_documents(context))
    _record_roles(context, scan)

    for hits, files in (
        (scan.data_hits, scan.data_files),
        (scan.log_hits, scan.sources),
    ):
        texts = dict(files)
        for path in sorted({path for path, _line, _kind in hits}):
            lines = [mask(line) for line in texts[path]]
            yield from _windows(path, lines, [n for p, n, _k in hits if p == path])
    yield from documents


def _scan(context: DimensionContext) -> _Scan:
    patterns = _patterns()
    scope_files = tuple(getattr(context.resolved_scope, "files", ()) or ())
    is_data = _matcher(patterns.test_data_paths)
    candidates = sorted(p for p in scope_files if is_data(p))
    data_files = []
    for path in candidates[:MAX_TEST_DATA_FILES]:
        text = context.read_source(path)
        if text is not None:
            data_files.append((path, _lines(text)))
    sources = [
        (path, lines)
        for path, lines, _syntax in _code_extract._read(
            context,
            _code_extract.source_candidates(context, "healthcare log-statement checks"),
        )
    ]
    data_hits = [
        (path, number, kind)
        for path, lines in data_files
        for number, line in enumerate(lines, start=1)
        for _start, _end, kind in phi_spans(line)
    ]
    log_hits = []
    log_lines = 0
    for path, lines in sources:
        for number, line in enumerate(lines, start=1):
            if any(call.search(line) for call in patterns.log_calls):
                log_lines += 1
                log_hits.extend((path, number, kind) for *_s, kind in phi_spans(line))
    return _Scan(data_files, len(candidates), sources, data_hits, log_hits, log_lines)


def _metrics(scan: _Scan) -> tuple[SampledMetric, ...]:
    capped = (
        f"; the first {MAX_TEST_DATA_FILES} of {scan.data_total} test-data files "
        "in path order were read"
        if scan.data_total > MAX_TEST_DATA_FILES
        else ""
    )
    data = (
        _count(
            TEST_DATA_METRIC,
            scan.data_hits,
            [path for path, _lines in scan.data_files],
            f"in {len(scan.data_files)} test-data file(s){capped}",
        )
        if scan.data_files
        else _abstain(
            TEST_DATA_METRIC,
            "no in-scope test-data file (the pack's test_data_paths) could be "
            "read; that is not the same as test data free of PHI",
        )
    )
    if not scan.sources:
        logs = _abstain(
            LOG_METRIC,
            "no in-scope source file of a registry language was read, so no log "
            "statement was scanned",
        )
    elif not scan.log_lines:
        logs = _abstain(
            LOG_METRIC,
            f"no log statement (the pack's log_calls) was found in the "
            f"{len(scan.sources)} source file(s) scanned, so there is nothing to "
            "judge",
        )
    else:
        logs = _count(
            LOG_METRIC,
            scan.log_hits,
            [path for path, _lines in scan.sources],
            f"on {scan.log_lines} log-statement line(s) of {len(scan.sources)} "
            "source file(s)",
        )
    return (data, logs)


def _count(name, hits, scanned, where) -> SampledMetric:
    """Paths are cited and listed as the pack's ``files_read`` holds them:
    redacted (a file name can look like a secret, core/pipeline.py)."""
    sites = sorted(set(hits))
    listed = ", ".join(f"{redact(p)}:{n} ({k})" for p, n, k in sites[:MAX_LISTED])
    more = f" and {len(sites) - MAX_LISTED} more" if len(sites) > MAX_LISTED else ""
    cited = sorted({p for p, _n, _k in sites}) or sorted(set(scanned))
    cited = sorted({redact(p) for p in cited})
    return SampledMetric(
        name=name,
        value=len(sites),
        abstention=None,
        computed_from=tuple(cited),
        derivation=(
            f"{len(sites)} PHI-shaped value(s) {where}: {listed or 'none'}{more}; "
            + _METHOD
        ),
    )


def _abstain(name: str, reason: str) -> SampledMetric:
    return SampledMetric(
        name=name, value=None, abstention=reason, computed_from=(), derivation=""
    )


def _documents(context: DimensionContext) -> Iterator[Excerpt]:
    """The first readable in-scope match of each documentation rule, masked."""
    scope_files = tuple(getattr(context.resolved_scope, "files", ()) or ())
    for rule in DOCUMENTATION_RULES[NAME]:
        match = _matcher(rule.patterns)
        for path in sorted(p for p in scope_files if match(p)):
            text = context.read_source(path)
            if text is None:
                continue
            excerpt = whole_file_excerpt(path, "\n".join(map(mask, _lines(text))))
            if excerpt is not None:
                yield excerpt
            break


def _record_roles(context: DimensionContext, scan: _Scan) -> None:
    filled = {TEST_DATA: bool(scan.data_files), LOGS: bool(scan.log_lines)}
    reasons = {
        TEST_DATA: "not found: no readable in-scope file matches the pack's "
        "test_data_paths",
        LOGS: f"no log statement (the pack's log_calls) was found in the "
        f"{len(scan.sources)} source file(s) scanned",
    }
    recorded = {m.source for m in context.sources_missing}
    for source, found in filled.items():
        if found and source not in context.sources_found:
            context.sources_found.append(source)
        elif not found and source not in recorded:
            context.sources_missing.append(
                SourceMiss(source=source, reason=reasons[source])
            )


def _lines(text: str) -> list[str]:
    return [line.removesuffix("\r") for line in text.split("\n")]


def _windows(path: str, lines: list[str], hits: list[int]) -> Iterator[Excerpt]:
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
