"""The bespoke ``supply-chain`` evidence dimension (T041, FR-050..052).

Areas #20 dependencies and licences, #21 CI reproducibility, #22 provenance,
SBOM and signing. It quotes the files of five source roles (manifest,
lockfile, CI workflow, licence file, release configuration) and, for the
rollback documentation rule, the first matching document; it never judges.
Which patterns fill a role, which commands count as a lockfile-faithful
install and which tokens show an SBOM or signing step are the registry's and
the generic layer's data (``core/roles.py``, ``registry/curated``), never this
module's. Live vulnerability status (CVE feeds) is not verifiable offline and
is not examined.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import PurePosixPath

from ..core.context import whole_file_excerpt
from ..core.judge import DOCUMENTATION_RULES
from ..core.models import (
    DimensionContext,
    DimensionDescriptor,
    Excerpt,
    SourceMiss,
    SourceRole,
)
from ..core.roles import _matcher, note_context_roles, role, role_files_in_scope

NAME = "supply-chain"

PURPOSE = (
    "Gather citable evidence about dependency pinning and licensing, CI "
    "reproducibility, and artifact provenance, SBOM and signing steps from "
    "manifests, lockfiles, CI workflows, licence files and release "
    "configuration, without judging them; live vulnerability status cannot be "
    "verified offline and is not examined."
)

ROLES: tuple[SourceRole, ...] = (
    role("package-manifest"),
    role("lockfile"),
    role("ci-workflow"),
    role("licence-file"),
    role("release-config"),
)
"""Source roles (T026): filled by any matching file in any language."""

SOURCES_SOUGHT: tuple[str, ...] = tuple(item.name for item in ROLES)

MAX_FILES_PER_ROLE = 20
"""Files quoted per role, shallowest path first, so a monorepo's root files
are never the ones cut; the rest are warned about (NFR-009)."""

PROOF_LINES = 5
"""Lines quoted from a lockfile or licence file: proof it exists and what it
is, without spending the byte budget on a machine-written file."""

CAP_WARNING = (
    "{count} {role} files exceed the cap of {cap}; the shallowest are quoted, "
    "so metrics over this role describe only those"
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

_PROOF_ROLES = frozenset({"lockfile", "licence-file"})

_READ_ORDER: tuple[str, ...] = (
    "ci-workflow",
    "release-config",
    "licence-file",
    "lockfile",
    "package-manifest",
)
"""Most relevant first, cheapest proof before the largest file."""


def collect(context: DimensionContext) -> Iterator[Excerpt]:
    """Yield bounded excerpts of each role's files, then the rollback
    document, lazily and in relevance order."""
    resolved_scope = context.resolved_scope
    if resolved_scope is None and context.scope != "project":
        message = UNRESOLVED_SCOPE_WARNING.format(scope=context.scope)
        if message not in context.warnings:
            context.warnings = (*context.warnings, message)
        reason = UNRESOLVED_SCOPE_REASON.format(scope=context.scope)
        for source in SOURCES_SOUGHT:
            context.sources_missing.append(SourceMiss(source=source, reason=reason))
        return

    scope_files = tuple(getattr(resolved_scope, "files", ()) or ())
    scope_kind = getattr(resolved_scope, "kind", None)
    whole_repo = resolved_scope is None or scope_kind == "project"
    scope_set = frozenset(scope_files)
    note_context_roles(context, _READ_ORDER, scope_set, scope_kind, whole_repo)

    for source in _READ_ORDER:
        paths = context.role_files.get(source, ())
        in_bounds = role_files_in_scope(source, paths, scope_set, whole_repo)
        if paths and not in_bounds:
            context.sources_missing.append(
                SourceMiss(
                    source=source, reason=f"not in the resolved {scope_kind} scope"
                )
            )
            continue
        ranked = sorted(in_bounds, key=lambda p: (p.count("/"), p))
        if len(ranked) > MAX_FILES_PER_ROLE:
            message = CAP_WARNING.format(
                count=len(ranked), role=source, cap=MAX_FILES_PER_ROLE
            )
            context.capped[source] = (len(ranked), MAX_FILES_PER_ROLE)
            # Before the first yield: the budget may abandon this generator.
            if message not in context.warnings:
                context.warnings = (*context.warnings, message)
        for path in ranked[:MAX_FILES_PER_ROLE]:
            text = context.read_source(path)
            if text is None:
                continue
            if source in _PROOF_ROLES:
                text = "\n".join(text.splitlines()[:PROOF_LINES])
            excerpt = whole_file_excerpt(path, text)
            if excerpt is not None:
                yield excerpt

    if resolved_scope is None:
        return
    # Documentation rules are checked against the files this pack read, so the
    # first readable in-scope match of each is read here (T056 precedent).
    for rule in DOCUMENTATION_RULES.get(NAME, ()):
        match = _matcher(rule.patterns)
        for path in sorted(p for p in scope_files if match(p)):
            text = context.read_source(path)
            if text is None:
                continue
            excerpt = whole_file_excerpt(PurePosixPath(path).as_posix(), text)
            if excerpt is not None:
                yield excerpt
            break


DESCRIPTOR = DimensionDescriptor(
    name=NAME,
    purpose=PURPOSE,
    sources_sought=SOURCES_SOUGHT,
    collect=collect,
    roles=ROLES,
)
