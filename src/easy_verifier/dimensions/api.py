"""The bespoke ``api`` evidence dimension (T044, FR-050..052).

Area #7 API contracts, validation, versioning. It quotes committed API
specification files (OpenAPI, GraphQL SDL, protobuf), reads the in-scope source
files of registry languages once to find route handlers, request validation,
generated specifications and versioning, and under ``changes`` scope reads the
diff for removed endpoints and specification fields. Its four rule metrics are
computed over whole files and stored on ``pack.whole_file`` (the T075/T076
path), so the byte budget never makes them abstain.

Which code is a route, a validation, a spec generator or a versioning switch
is the registry's data (``registry/curated``: ``route_tokens``,
``request_validation``, ``api_spec_generators``, ``api_version_markers``);
which files are specifications, what a version segment looks like and what a
specification definition line looks like is the generic layer's
(``core/roles.py``). None of it lives here. Whether a running service honours
its contract cannot be verified offline and is not examined.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import PurePosixPath

from ..core.context import whole_file_excerpt
from ..core.metric_tables import curated_metric_tables
from ..core.metrics import code_kind
from ..core.models import (
    DimensionContext,
    DimensionDescriptor,
    Excerpt,
    SampledMetric,
    SourceMiss,
    SourceRole,
)
from ..core.redact import redact
from ..core.roles import GENERIC_API_FACTS, _matcher, role
from ..core.scope import KIND_CHANGES
from ..core.structure import _curated as _curated_conventions
from ..core.structure import context_conventions, find_routes
from ..core.tokens import strip
from . import _code_extract
from .blast_radius import _diff_files
from .requirement_fidelity import _suffix_tokens, _tokens_for

NAME = "api"

PURPOSE = (
    "Gather citable evidence about API contracts, request validation and "
    "versioning from specification files (OpenAPI, GraphQL, protobuf), route "
    "definitions and validation code in source files, and, for a change, the "
    "endpoints and specification fields it removes, without judging them; "
    "whether a running service honours its contract cannot be verified "
    "offline and is not examined."
)

SPEC = "api-spec"
ROUTES = "route definitions in source files"
VALIDATION = "request validation in source files"

ROLES: tuple[SourceRole, ...] = (
    role(SPEC),
    SourceRole(name=ROUTES, patterns=()),
    SourceRole(name=VALIDATION, patterns=()),
)
"""Code evidence counts toward coverage (DDR-0011): the two pseudo-roles are
filled when the scan finds a route handler and a request-validation token."""

SOURCES_SOUGHT: tuple[str, ...] = tuple(item.name for item in ROLES)

MAX_SPEC_FILES = 20
"""Specification files quoted, shallowest first; the rest are warned about."""

MAX_EXAMPLES = 5
"""Sites named in a derivation."""

MAX_QUOTED = 20
"""Route and validation lines quoted as evidence, each."""

CAP_WARNING = (
    "{count} api-spec files exceed the cap of {cap}; the shallowest are "
    "quoted, so the breaking-change and version checks over specifications "
    "describe only those"
)

UNRESOLVED_SCOPE_WARNING = (
    "The {scope} scope could not be resolved, most likely because its required "
    "selector was not supplied. No evidence was gathered; this pack is not "
    "whole-repository output."
)

UNRESOLVED_SCOPE_REASON = (
    "not examined: the {scope} scope could not be resolved "
    "(its required selector was not supplied)"
)

_DOTTED = tuple(
    v for item in GENERIC_API_FACTS["dotted_package_suffixes"] for v in item.value
)
_PRESENCE = frozenset(
    {"api_spec_missing", "api_version_missing", "request_validation_missing"}
)
_LITERAL = re.compile(r"([\"'`])([^\"'`\n]{1,200})\1")
_VERSION = tuple(
    re.compile(v) for item in GENERIC_API_FACTS["version_segment"] for v in item.value
)
_SPEC_LINES = tuple(
    re.compile(v) for item in GENERIC_API_FACTS["spec_definition"] for v in item.value
)


def collect(context: DimensionContext) -> Iterator[Excerpt]:
    """Yield the specification files, then the route and validation lines,
    lazily; the metrics are stored before the first yield."""
    resolved_scope = context.resolved_scope
    if resolved_scope is None and context.scope != "project":
        message = UNRESOLVED_SCOPE_WARNING.format(scope=context.scope)
        if message not in context.warnings:
            context.warnings = (*context.warnings, message)
        reason = UNRESOLVED_SCOPE_REASON.format(scope=context.scope)
        for source in SOURCES_SOUGHT:
            context.sources_missing.append(SourceMiss(source=source, reason=reason))
        return

    facts = getattr(context, "api_facts", None)
    if facts is None:
        facts = _facts(context)
        context.api_facts = facts
    specs, scan = facts
    for path, text in specs:
        excerpt = whole_file_excerpt(path, text)
        if excerpt is not None:
            yield excerpt
    for kind in ("routes", "validation"):
        for path, lines, number in scan[kind][:MAX_QUOTED]:
            excerpt = _code_extract._excerpt(path, lines, number - 1, number - 1)
            if excerpt is not None:
                yield excerpt


def _facts(context: DimensionContext):
    """Read every input once and store the four metrics on
    ``context.whole_file``; idempotent across the budget's tier passes."""
    scope = context.resolved_scope
    scope_files = tuple(getattr(scope, "files", ()) or ())
    whole_repo = scope is None or getattr(scope, "kind", None) == "project"
    specs = _read_specs(context, scope_files, whole_repo)
    sources = _code_extract.source_candidates(context, "API evidence")
    scan = _scan(context, sources)
    plan = getattr(context, "batch_plan", None)
    # What bounded the search is said wherever an absence is reported.
    note = (
        f"; sample: batches {plan.batches_done} of {plan.batches_total}, "
        f"{len(plan.selected)} of {len(plan.ordered)} source files -- the rest "
        "were not scanned (--batches)"
        if plan is not None
        else ""
    )
    _found(context, ROUTES, bool(scan["routes"]),
           f"not found: no route handler (the registry's route_tokens) in the "
           f"{scan['read']} in-scope source file(s) scanned{note}")
    _found(context, VALIDATION, bool(scan["validation"]),
           f"not found: no request-validation token (the registry's "
           f"request_validation) in the {scan['read']} in-scope source file(s) "
           f"scanned{note}")
    context.whole_file = tuple(
        _with_note(metric, note)
        for metric in (
            _spec_metric(specs, scan),
            _version_metric(specs, scan),
            _validation_metric(scan),
        )
    ) + (_breaking_metric(scope, {p for p, _t in specs} | scan["paths"]),)
    if not whole_repo:
        # Presence is a repository property: a narrow scope can show it, but
        # its absence among the scope's files is not the repository's.
        kind = getattr(scope, "kind", None)
        context.whole_file = tuple(
            _metric(
                m.name,
                abstention=f"not found among the {len(scope_files)} file(s) of the "
                f"{kind} scope; whether the repository has it is judged only under "
                "project scope",
            )
            if m.value == 1 and m.name in _PRESENCE
            else m
            for m in context.whole_file
        )
    return specs, scan


def _read_specs(context, scope_files, whole_repo) -> list[tuple[str, str]]:
    paths = context.role_files.get(SPEC, ())
    in_bounds = paths if whole_repo else [p for p in paths if p in set(scope_files)]
    if paths and not in_bounds:
        context.sources_missing.append(
            SourceMiss(source=SPEC, reason="not in the resolved scope")
        )
    ranked = sorted(in_bounds, key=lambda p: (p.count("/"), p))
    if len(ranked) > MAX_SPEC_FILES:
        message = CAP_WARNING.format(count=len(ranked), cap=MAX_SPEC_FILES)
        if message not in context.warnings:
            context.warnings = (*context.warnings, message)
    specs = []
    for path in ranked[:MAX_SPEC_FILES]:
        text = context.read_source(path)
        if text is not None:
            specs.append((path, text))
    return specs


def _scan(context: DimensionContext, sources: list[str]) -> dict:
    """Routes, validation, spec-generator, versioning-marker and version-path
    sites over the whole text of ``sources``."""
    tables = curated_metric_tables()
    by_suffix = _suffix_tokens(context_conventions(context))
    scan: dict = {
        "read": 0, "routes": [], "validation": [], "generators": [],
        "markers": [], "versioned": [], "route_languages": set(),
        "validating_languages": set(), "paths": set(),
    }
    for path, lines, syntax in _code_extract._read(context, sources):
        scan["read"] += 1
        scan["paths"].add(path)
        suffix = PurePosixPath(path).suffix
        text = "\n".join(lines)
        routes = find_routes(text, _tokens_for(by_suffix, path), syntax)
        for route in routes:
            scan["routes"].append((path, lines, route.line))
            if route.path and _versioned(route.path):
                scan["versioned"].append((path, route.line, route.path))
        if routes:
            scan["route_languages"].add(suffix)
            if suffix in tables.request_validation:
                scan["validating_languages"].add(suffix)
        code_lines = strip(text, syntax).split("\n")
        for field, key in (
            ("request_validation", "validation"),
            ("api_spec_generators", "generators"),
            ("api_version_markers", "markers"),
        ):
            pattern = getattr(tables, field).get(suffix)
            if pattern is None:
                continue
            for number, code in enumerate(code_lines, 1):
                if pattern.search(code):
                    scan[key].append((path, lines, number))
        # Path literals count only in files that declare routes: elsewhere a
        # versioned path is usually an outbound client URL (T044 real-repo
        # finding), not this API's own version.
        for number, (line, code) in enumerate(
            zip(lines, code_lines, strict=False) if routes else (), 1
        ):
            if syntax.imports is not None and syntax.imports.search(code):
                continue
            for literal in _LITERAL.finditer(line):
                value = literal[2]
                if "://" not in value and "/" in value and _versioned(value):
                    scan["versioned"].append((path, number, value))
                    break
    return scan


def _versioned(value: str, separators: str = "/") -> bool:
    segments = re.split(f"[{re.escape(separators)}]", value.split("?", 1)[0])
    return any(p.match(s) for s in segments for p in _VERSION)


def _sites(items) -> str:
    shown = ", ".join(f"{redact(p)}:{n}" for p, *_rest, n in items[:MAX_EXAMPLES])
    more = len(items) - MAX_EXAMPLES
    return shown + (f", and {more} more" if more > 0 else "")


def _spec_metric(specs, scan) -> SampledMetric:
    name = "api_spec_missing"
    generators = scan["generators"]
    if specs:
        return _metric(
            name, 0, [p for p, _t in specs],
            f"{len(specs)} committed API specification file(s) (the api-spec "
            "role: OpenAPI/Swagger JSON or YAML, GraphQL SDL, protobuf): "
            + ", ".join(redact(p) for p, _t in specs[:MAX_EXAMPLES])
            + "; 0 when one exists, else 1 (missing)",
        )
    if generators:
        return _metric(
            name, 0, {p for p, _l, _n in generators},
            "no specification file is committed, but code generates one at "
            f"build or run time ({_sites(generators)}; the registry's "
            "api_spec_generators tokens); 0 when a specification exists, else 1",
        )
    if not scan["routes"]:
        return _metric(
            name,
            abstention="no API specification file and no route handler were "
            f"found in the {scan['read']} source file(s) scanned, so there is "
            "no API whose contract could be missing (a library is not rated)",
        )
    return _metric(
        name, 1, {p for p, _l, _n in scan["routes"]},
        f"{len(scan['routes'])} route handler(s) ({_sites(scan['routes'])}) "
        "but no committed specification file (api-spec role) and no "
        "specification generator (the registry's api_spec_generators tokens); "
        "1 (missing)",
    )


def _version_metric(specs, scan) -> SampledMetric:
    name = "api_version_missing"
    spec_hits = []
    for path, text in specs:
        dotted = path.endswith(_DOTTED)
        for number, line in enumerate(text.splitlines(), 1):
            for token in line.replace(";", " ").split():
                if ("://" not in token and ("/" in token or dotted)
                        and _versioned(token, "/." if dotted else "/")):
                    spec_hits.append((path, number))
                    break
    hits = [(p, n) for p, n, _v in scan["versioned"]] + spec_hits
    markers = [(p, n) for p, _l, n in scan["markers"]]
    if hits or markers:
        found = hits + markers
        return _metric(
            name, 0, {p for p, _n in found},
            f"{len(found)} versioning site(s): {_sites(found)}; a route path, "
            "a non-import string literal path or a specification path/package "
            "with a whole version segment (the generic layer's ^v[0-9]+$, "
            "AIP-185), or a framework versioning switch (the registry's "
            "api_version_markers); 0 when any exists, else 1 (missing)",
        )
    if not scan["routes"] and not specs:
        return _metric(
            name,
            abstention="no route handler and no API specification were found, "
            "so there is no API whose version could be missing",
        )
    cited = {p for p, _l, _n in scan["routes"]} | {p for p, _t in specs}
    return _metric(
        name, 1, cited,
        f"no version segment in {len(scan['routes'])} route path(s), the "
        "string literal paths of the scanned source or "
        f"{len(specs)} specification file(s), and no framework versioning "
        "switch; 1 (missing)",
    )


def _validation_metric(scan) -> SampledMetric:
    name = "request_validation_missing"
    routes, validation = scan["routes"], scan["validation"]
    if not routes:
        return _metric(
            name,
            abstention=f"no route handler was found in the {scan['read']} source "
            "file(s) scanned, so there is no entry point whose input could go "
            "unvalidated",
        )
    if validation:
        return _metric(
            name, 0, {p for p, _l, _n in validation},
            f"{len(validation)} request-validation site(s) ({_sites(validation)}) "
            f"beside {len(routes)} route handler(s); the registry's "
            "request_validation tokens, matched in code; 0 when any exists, "
            "else 1 (missing). Repository level: it does not show that every "
            "route validates",
        )
    if not scan["validating_languages"]:
        return _metric(
            name,
            abstention="no language of the files declaring routes declares "
            "request_validation tokens in the registry, so a validation library "
            "could not be recognised; that is not the same as none",
        )
    return _metric(
        name, 1, {p for p, _l, _n in routes},
        f"{len(routes)} route handler(s) ({_sites(routes)}) and no "
        "request-validation token (the registry's request_validation) in "
        f"{scan['read']} source file(s); 1 (missing)",
    )


def _breaking_metric(scope, read: set[str]) -> SampledMetric:
    """Removed endpoints and specification fields in the diff; cites only
    the changed files this pack read (FR-027)."""
    name = "breaking_api_changes_observed"
    kind = getattr(scope, "kind", None)
    if kind != KIND_CHANGES:
        return _metric(
            name,
            abstention="only a changes-scope diff shows removed endpoints or "
            f"specification fields, and this is {kind or 'project'} scope",
        )
    diff = getattr(scope, "diff", None)
    if diff is None:
        return _metric(
            name, abstention="the changes scope carries no diff (git diff failed)"
        )
    tables = curated_metric_tables()
    by_suffix = _suffix_tokens(_curated_conventions())
    is_spec = _matcher(role(SPEC).patterns)
    gone: list[tuple[str, int, str]] = []
    cited: set[str] = set()
    for item in (f for f in _diff_files(diff) if not f["secret"]):
        path, old = item["path"], item["old_path"]
        suffix = PurePosixPath(path).suffix
        if is_spec(path) or is_spec(old):
            keys = {"+": set(), "-": []}
            for sign, number, text, _h in item["lines"]:
                key = _spec_key(text)
                if key is None or sign not in keys:
                    continue
                if sign == "+":
                    keys["+"].add(key)
                else:
                    keys["-"].append((number, key))
            removed = [(old, n, k[-1]) for n, k in keys["-"] if k not in keys["+"]]
        elif code_kind(path, tables) == "source" and suffix in tables.syntax:
            tokens = _tokens_for(by_suffix, path)
            seen = {"+": set(), "-": []}
            for sign, number, text, _h in item["lines"]:
                if sign not in seen:
                    continue
                for route in find_routes(text, tokens, tables.syntax[suffix]):
                    key = (route.method, route.path)
                    if sign == "+":
                        seen["+"].add(key)
                    else:
                        seen["-"].append((number, key))
            removed = [
                (old, n, f"{k[0]} {k[1] or '(no path)'}")
                for n, k in seen["-"]
                if k not in seen["+"]
            ]
        else:
            continue
        if path in read:
            cited.add(path)
        gone.extend(removed)
    if not cited:
        return _metric(
            name,
            abstention="no API specification or route source file in this diff "
            "was read" + (
                f", so the {len(gone)} removed endpoint(s) or field(s) found in "
                "it cannot be cited" if gone else ""
            ),
        )
    return _metric(
        name, len(gone), cited,
        f"{len(gone)} endpoint(s) or specification field(s) removed and not "
        "re-added in the diff"
        + (": " + ", ".join(f"{redact(p)}:{n} {redact(k)}" for p, n, k in
                            gone[:MAX_EXAMPLES]) if gone else "")
        + "; a removed route is a route handler (registry route_tokens) whose "
        "method and path no added line declares, a removed field a "
        "specification definition line (generic layer: YAML/JSON/GraphQL key "
        "at its indentation, protobuf field or rpc) no added line restores",
    )


def _spec_key(text: str):
    for pattern in _SPEC_LINES:
        match = pattern.match(text)
        if match is None:
            continue
        groups = match.groupdict()
        if groups.get("key"):
            return (len(groups.get("indent") or ""), groups["key"])
        return (0, groups.get("rpc") or groups.get("field"))
    return None


def _found(context: DimensionContext, source: str, found: bool, reason: str) -> None:
    if found:
        if source not in context.sources_found:
            context.sources_found.append(source)
    elif not any(m.source == source for m in context.sources_missing):
        context.sources_missing.append(SourceMiss(source=source, reason=reason))


def _metric(
    name, value=None, refs=(), derivation="", abstention=None
) -> SampledMetric:
    return SampledMetric(
        name=name,
        value=value,
        abstention=None if abstention is None else redact(abstention),
        computed_from=tuple(sorted({redact(path) for path in refs})),
        derivation=redact(derivation),
    )


def _with_note(metric: SampledMetric, note: str) -> SampledMetric:
    if not note:
        return metric
    if metric.abstention is not None:
        return _metric(metric.name, abstention=metric.abstention + note)
    return SampledMetric(
        name=metric.name,
        value=metric.value,
        abstention=None,
        computed_from=metric.computed_from,
        derivation=metric.derivation + note,
    )


DESCRIPTOR = DimensionDescriptor(
    name=NAME,
    purpose=PURPOSE,
    sources_sought=SOURCES_SOUGHT,
    collect=collect,
    roles=ROLES,
)
