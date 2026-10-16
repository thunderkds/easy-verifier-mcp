"""The bespoke ``operations`` evidence dimension (T046, FR-050..052).

Areas #14 observability, auditing, SLOs; #25 incident response and change
management; #26 configuration ownership and operational readiness; #29
AI-assisted-development safety; #30 developer experience and deterministic
local setup. It quotes the files of five file roles (CODEOWNERS, observability
configuration, agent configuration, tool-version pins, development
environment), the first document matching each documentation rule, and the
source lines that show a logging library or an audit write; it never judges.
Its eight rule metrics are computed over whole files and stored on
``pack.whole_file`` (the T045 path), so the byte budget never makes them
abstain.

Which files fill a role, which tokens show a logging library, an audit write or
an agent guardrail are the registry's (``logging_markers``,
``roles.tool-version-pin``) and the generic layer's (``core/roles.py``), never
this module's. A secret in agent configuration is found by the evidence layer's
exact-pattern redaction detectors (``core/redact.py``) and only counted:
the value is never quoted. The lockfile part of #30 is the supply-chain dimension's
``lockfile_missing``. Whether incidents are handled, SLOs met or access reviewed
cannot be verified offline: only the documents are checked.
"""

from __future__ import annotations

import re
from collections.abc import Iterator

from ..core.context import MAX_LINE_CHARS, whole_file_excerpt
from ..core.judge import DOCUMENTATION_RULES
from ..core.metric_tables import curated_metric_tables
from ..core.models import (
    DimensionContext,
    DimensionDescriptor,
    Excerpt,
    SampledMetric,
    SourceMiss,
    SourceRole,
)
from ..core.redact import _DETECTORS, redact, scan
from ..core.roles import (
    GENERIC_OPERATIONS_FACTS,
    GENERIC_PATTERNS,
    _matcher,
    _registry,
    note_context_roles,
    role,
    role_files_in_scope,
)
from ..core.tokens import strip
from . import _code_extract

NAME = "operations"

PURPOSE = (
    "Gather citable evidence about ownership, observability, AI coding-agent "
    "safety and reproducible local setup from CODEOWNERS, observability "
    "configuration, logging and audit calls in source files, agent "
    "instruction and settings files, tool-version pins and development "
    "environment files, and whether runbook, incident and SLO documents exist, "
    "without judging them; whether incidents are handled, SLOs met or access "
    "reviewed cannot be verified offline and is not examined."
)

CODEOWNERS = "codeowners"
OBSERVABILITY = "observability-config"
AGENT = "agent-config"
PIN = "tool-version-pin"
DEV_ENV = "dev-environment"
DOCS = "runbook, incident or SLO documents"
LOGGING = "logging or tracing in source files"

ROLES: tuple[SourceRole, ...] = (
    role(CODEOWNERS),
    SourceRole(name=DOCS, patterns=()),
    role(OBSERVABILITY),
    SourceRole(name=LOGGING, patterns=()),
    role(AGENT),
    role(PIN),
    role(DEV_ENV),
)
"""Five file roles and two pseudo-roles: the documents are those of this
dimension's documentation rules (``core/judge.py``, one copy of the
patterns), and logging is filled when the source scan finds a registry
``logging_markers`` token (DDR-0011)."""

SOURCES_SOUGHT: tuple[str, ...] = tuple(item.name for item in ROLES)

_FILE_ROLES = (CODEOWNERS, AGENT, PIN, DEV_ENV, OBSERVABILITY)

MAX_FILES_PER_ROLE = 20
"""Files read per file role, shallowest path first, so a monorepo's root files
are never the ones cut; the rest are warned about (NFR-009)."""

PROOF_LINES = 20
"""Lines quoted from each role file: proof it exists and what it says."""

MAX_QUOTED = 10
"""Logging and audit lines quoted, each."""

MAX_EXAMPLES = 5
"""Paths named in a derivation."""

CAP_WARNING = (
    "{count} {role} files exceed the cap of {cap}; the shallowest are read, so "
    "metrics over this role describe only those"
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


def _facts_of(key: str) -> tuple[str, ...]:
    return tuple(v for item in GENERIC_OPERATIONS_FACTS[key] for v in item.value)


_AUDIT = re.compile("|".join(_facts_of("audit_write")))
_GUARDRAIL = re.compile("|".join(_facts_of("agent_guardrails")))
_GUARDRAIL_PATH = _matcher(_facts_of("agent_guardrail_paths"))
_EXACT_DETECTORS = frozenset(name for name, _pattern in _DETECTORS)
"""The redaction scanner's exact-pattern detectors (PEM keys, AWS keys, JWTs,
credential assignments). Its heuristic detectors (high entropy, key-material
segments) fire on ordinary agent-instruction prose such as a hyphenated
document path, so they are not counted here (Supervisor, 2026-10-07)."""
_PRESENCE = frozenset(
    {
        "codeowners_missing",
        "agent_guardrails_missing",
        "tool_version_pin_missing",
        "dev_environment_missing",
        "logging_library_missing",
        "audit_log_writes_missing",
    }
)


def collect(context: DimensionContext) -> Iterator[Excerpt]:
    """Yield role files, documents and logging/audit lines, lazily; the
    metrics are stored before the first yield."""
    resolved_scope = context.resolved_scope
    if resolved_scope is None and context.scope != "project":
        message = UNRESOLVED_SCOPE_WARNING.format(scope=context.scope)
        if message not in context.warnings:
            context.warnings = (*context.warnings, message)
        reason = UNRESOLVED_SCOPE_REASON.format(scope=context.scope)
        for source in SOURCES_SOUGHT:
            context.sources_missing.append(SourceMiss(source=source, reason=reason))
        return

    facts = getattr(context, "operations_facts", None)
    if facts is None:
        facts = _facts(context)
        context.operations_facts = facts
    for path, text in facts["docs"] + [
        item for name in _FILE_ROLES for item in facts["files"][name]
    ]:
        excerpt = whole_file_excerpt(path, "\n".join(text.splitlines()[:PROOF_LINES]))
        if excerpt is not None:
            yield excerpt
    for key in ("logging", "audit"):
        for path, lines, number in facts[key][:MAX_QUOTED]:
            excerpt = _code_extract._excerpt(path, lines, number - 1, number - 1)
            if excerpt is not None:
                yield excerpt


def _facts(context: DimensionContext) -> dict:
    """Read every input once and store the eight metrics on
    ``context.whole_file``; idempotent across the budget's tier passes."""
    scope = context.resolved_scope
    scope_files = tuple(getattr(scope, "files", ()) or ())
    kind = getattr(scope, "kind", None)
    whole_repo = scope is None or kind == "project"
    scope_set = frozenset(scope_files)
    tables = curated_metric_tables()

    files: dict[str, list[tuple[str, str]]] = {}
    note_context_roles(context, _FILE_ROLES, scope_set, kind, whole_repo)
    for name in _FILE_ROLES:
        paths = context.role_files.get(name, ())
        in_bounds = role_files_in_scope(name, paths, scope_set, whole_repo)
        if paths and not in_bounds:
            context.sources_missing.append(
                SourceMiss(source=name, reason=f"not in the resolved {kind} scope")
            )
        ranked = sorted(in_bounds, key=lambda p: (p.count("/"), p))
        if len(ranked) > MAX_FILES_PER_ROLE:
            message = CAP_WARNING.format(
                count=len(ranked), role=name, cap=MAX_FILES_PER_ROLE
            )
            context.capped[name] = (len(ranked), MAX_FILES_PER_ROLE)
            if message not in context.warnings:
                context.warnings = (*context.warnings, message)
        files[name] = []
        for path in ranked[:MAX_FILES_PER_ROLE]:
            text = context.read_source(path)
            if text is not None:
                files[name].append((path, text))

    # Documentation rules are checked against the files this pack read, so the
    # first readable in-scope match of each is read here (T041 precedent).
    docs: list[tuple[str, str]] = []
    for rule in DOCUMENTATION_RULES.get(NAME, ()):
        match = _matcher(rule.patterns)
        for path in sorted(p for p in scope_files if match(p)):
            if path in context.files_read:
                break  # already quoted (an agent instruction file)
            text = context.read_source(path)
            if text is not None:
                docs.append((path, text))
                break
    _found(
        context, DOCS, bool(docs),
        "not found: no runbook, incident, change-management or SLO document "
        "in scope (the operations documentation rules' patterns)",
    )

    # A logging library declared as a dependency is in use even when the
    # sampled source files never import it (node-monorepo, T046): the same registry
    # tokens are matched in the in-scope package manifests.
    # Registry manifest names are bare (``package.json``); a monorepo
    # service's own manifest (``backend/package.json``) counts too.
    manifest = _matcher(
        GENERIC_PATTERNS["package-manifest"]
        + tuple(
            v if "/" in v else f"**/{v}"
            for entry in _registry().languages.values()
            for item in entry.manifests
            for v in item.value
        )
    )
    patterns = set(tables.logging_markers.values())
    declared: list[str] = []
    for path in sorted(
        (p for p in scope_files if manifest(p)), key=lambda p: (p.count("/"), p)
    )[:MAX_FILES_PER_ROLE]:
        text = context.read_source(path)
        if text and any(p.search(text) for p in patterns):
            declared.append(path)

    sources = _code_extract.source_candidates(context, "logging and audit evidence")
    logging: list[tuple[str, list[str], int]] = []
    audit: list[tuple[str, list[str], int]] = []
    scanned = 0
    for path, lines, syntax in _code_extract._read(context, sources):
        scanned += 1
        suffix = path.rsplit(".", 1)[-1]
        pattern = tables.logging_markers.get("." + suffix)
        if pattern is not None:
            hit = next((n for n, ln in enumerate(lines, 1) if pattern.search(ln)), 0)
            if hit:
                logging.append((path, lines, hit))
        code = strip("\n".join(lines), syntax).split("\n")
        # Searched within the excerpt line cap: a minified line longer than
        # that is never quoted whole, and bounding it keeps the search linear.
        hit = next(
            (n for n, ln in enumerate(code, 1) if _AUDIT.search(ln, 0, MAX_LINE_CHARS)),
            0,
        )
        if hit:
            audit.append((path, lines, hit))
    _found(
        context, LOGGING, bool(logging),
        "not found: no logging or tracing token (the registry's "
        f"logging_markers) in the {scanned} in-scope source file(s) scanned",
    )

    context.whole_file = (
        _logging_metric(logging, declared, files[OBSERVABILITY], scanned),
        _audit_metric(audit, scanned),
        _role_metric("codeowners_missing", files[CODEOWNERS], "a CODEOWNERS file"),
        _guardrails_metric(files[AGENT]),
        _secrets_metric(files[AGENT]),
        _role_metric(
            "tool_version_pin_missing", files[PIN], "a tool-version pin file"
        ),
        _role_metric(
            "dev_environment_missing", files[DEV_ENV],
            "a devcontainer, Nix/Devbox environment or one-command setup file",
        ),
    )
    # An absence is cited by the files this pack did read (FR-027: a value
    # never cites nothing); with none read there is nothing to cite.
    read = tuple(dict.fromkeys(context.files_read))
    context.whole_file = tuple(
        m
        if m.value is None or m.computed_from
        else _metric(
            m.name, m.value, read, m.derivation + "; bounded by the files this "
            f"pack read ({len(read)})",
        )
        if read
        else _metric(
            m.name,
            abstention="this pack read no file, so the absence has nothing to "
            "be cited by",
        )
        for m in context.whole_file
    )
    if not whole_repo:
        # Presence is a repository property: a narrow scope can show it, but
        # its absence among the scope's files is not the repository's.
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
    return {"files": files, "docs": docs, "logging": logging, "audit": audit}


def _found(context: DimensionContext, source: str, found: bool, reason: str) -> None:
    if found:
        if source not in context.sources_found:
            context.sources_found.append(source)
    elif not any(m.source == source for m in context.sources_missing):
        context.sources_missing.append(SourceMiss(source=source, reason=reason))


def _paths(paths) -> str:
    paths = list(paths)
    shown = ", ".join(paths[:MAX_EXAMPLES])
    extra = len(paths) - MAX_EXAMPLES
    return shown + (f" and {extra} more" if extra > 0 else "")


def _role_metric(name: str, items, what: str) -> SampledMetric:
    paths = [p for p, _t in items]
    return _metric(
        name,
        0 if paths else 1,
        paths,
        (f"{what} was read: {_paths(paths)}" if paths else f"not found: {what}")
        + " (presence only; its content is quoted for the calling agent)",
    )


def _logging_metric(logging, declared, configs, scanned: int) -> SampledMetric:
    paths = [p for p, _l, _n in logging] + declared + [p for p, _t in configs]
    if not paths and not scanned:
        return _metric(
            "logging_library_missing",
            abstention="no source file and no observability configuration in "
            "scope, so there is no code whose logging could be examined",
        )
    return _metric(
        "logging_library_missing",
        0 if paths else 1,
        paths,
        f"{len(logging)} of {scanned} source file(s) scanned use a logging or "
        f"tracing library (the registry's logging_markers), {len(declared)} "
        f"package manifest(s) declare one and {len(configs)} observability "
        "configuration file(s) were read"
        + (f": {_paths(paths)}" if paths else ""),
    )


def _audit_metric(audit, scanned: int) -> SampledMetric:
    if not scanned:
        return _metric(
            "audit_log_writes_missing",
            abstention="no source file in scope, so there is no code whose "
            "audit writes could be examined",
        )
    paths = [p for p, _l, _n in audit]
    return _metric(
        "audit_log_writes_missing",
        0 if paths else 1,
        paths,
        f"{len(paths)} of {scanned} source file(s) scanned call through an "
        "identifier naming audit (comments and strings blanked)"
        + (f": {_paths(paths)}" if paths else "")
        + "; textual, so the calling agent judges what the trail records",
    )


def _no_agent(name: str) -> SampledMetric:
    return _metric(
        name,
        abstention="no agent configuration file was found, so there is no "
        "agent setup to examine (the #29 documentation rule reports whether "
        "instruction files exist)",
    )


def _guardrails_metric(agent) -> SampledMetric:
    if not agent:
        return _no_agent("agent_guardrails_missing")
    paths = [p for p, t in agent if _GUARDRAIL_PATH(p) or _GUARDRAIL.search(t)]
    return _metric(
        "agent_guardrails_missing",
        0 if paths else 1,
        paths or [p for p, _t in agent],
        (
            f"guardrails (a hook script, a hooks or deny key, or a Codex "
            f"approval policy or sandbox mode) in: {_paths(paths)}"
            if paths
            else f"no hook, deny list, approval policy or sandbox mode in the "
            f"{len(agent)} agent configuration file(s) read"
        ),
    )


def _secrets_metric(agent) -> SampledMetric:
    if not agent:
        return _no_agent("agent_config_secrets_observed")
    hits = [
        (p, sum(h.detector in _EXACT_DETECTORS for h in scan(t).hits))
        for p, t in agent
    ]
    flagged = [p for p, count in hits if count]
    total = sum(count for _p, count in hits)
    return _metric(
        "agent_config_secrets_observed",
        total,
        [p for p, _t in agent],
        f"{total} secret value(s) found by the evidence layer's exact-pattern "
        f"redaction detectors ({', '.join(sorted(_EXACT_DETECTORS))}) in "
        f"{len(agent)} agent configuration file(s)"
        + (f", in {_paths(flagged)}" if flagged else "")
        + "; values are never quoted",
    )


def _metric(name, value=None, refs=(), derivation="", abstention=None) -> SampledMetric:
    return SampledMetric(
        name=name,
        value=value,
        abstention=None if abstention is None else redact(abstention),
        computed_from=tuple(sorted({redact(path) for path in refs})),
        derivation=redact(derivation),
    )


DESCRIPTOR = DimensionDescriptor(
    name=NAME,
    purpose=PURPOSE,
    sources_sought=SOURCES_SOUGHT,
    collect=collect,
    roles=ROLES,
)
