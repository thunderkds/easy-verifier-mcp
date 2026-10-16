"""The bespoke ``data`` evidence dimension (T045, FR-050..052).

Area #4 data model, constraints, migrations. It reads the in-scope migration
files and committed schema files, scans the in-scope source files of registry
languages once for data models, and quotes them; it never judges. Its four rule
metrics are computed over whole files and stored on ``pack.whole_file`` (the
T075/T076 path), so the byte budget never makes them abstain.

What makes a file a migration (its directory, its down/up sections, which
operations are destructive) is the blast-radius dimension's knowledge, read
from there so there is one copy until T057 moves it to the registry. Which code
declares a data model, a constraint or a reversible migration is the
registry's data (``orm_model_markers``, ``schema_constraint_markers``,
``migration_rollback_markers``); SQL/Prisma/Liquibase constraint syntax, rollback
sections, rollback file pairs and migration suffixes are the generic layer's
(``core/roles.py``). None of it lives here. Whether the live database matches
the schema cannot be verified offline and is not examined.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import PurePosixPath

from ..core.context import whole_file_excerpt
from ..core.metric_tables import curated_metric_tables
from ..core.models import (
    DimensionContext,
    DimensionDescriptor,
    Excerpt,
    SampledMetric,
    SourceMiss,
    SourceRole,
)
from ..core.redact import redact
from ..core.roles import (
    GENERIC_DATA_FACTS,
    note_context_roles,
    role,
    role_files_in_scope,
)
from ..core.structure import context_conventions
from ..core.tokens import strip
from . import _code_extract
from .blast_radius import (
    _COMMENT_LINE,
    _DOWN_START,
    _UP_START,
    _is_migration,
    migration_patterns,
)

NAME = "data"

PURPOSE = (
    "Gather citable evidence about the data model, its constraints and its "
    "migrations from migration files, committed schema files (SQL, Prisma, "
    "Rails schema; Alembic, Flyway and Liquibase migrations) and data models "
    "declared in source files, without judging them; whether a live database "
    "matches the schema cannot be verified offline and is not examined."
)

MIGRATIONS = "migration files"
SCHEMA = "schema-file"
MODELS = "data models in source files"

ROLES: tuple[SourceRole, ...] = (
    SourceRole(name=MIGRATIONS, patterns=()),
    role(SCHEMA),
    SourceRole(name=MODELS, patterns=()),
)
"""Two pseudo-roles: migration files are the in-scope files in a directory
the registry's ``migration_dirs`` convention names (any case;
``blast_radius.migration_patterns``, T057), and data models are filled when
the scan finds a registry ``orm_model_markers`` token (DDR-0011)."""

SOURCES_SOUGHT: tuple[str, ...] = tuple(item.name for item in ROLES)

MAX_MIGRATION_FILES = 200
"""Migration files read, newest path first; the rest are counted and warned
about (NFR-009)."""

MAX_QUOTED = 20
"""Schema files, migrations, destructive lines and model lines quoted, each."""

MAX_EXAMPLES = 5
"""Sites named in a derivation."""

CAP_WARNING = (
    "{count} migration files exceed the cap of {cap}; the newest are read, so "
    "the migration metrics describe only those"
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


def _patterns(key: str) -> tuple[re.Pattern[str], ...]:
    return tuple(re.compile(v) for item in GENERIC_DATA_FACTS[key] for v in item.value)


_CONSTRAINTS = _patterns("schema_constraints")
_ROLLBACK = _patterns("rollback_markers")
_DDL = _patterns("schema_ddl")
_PAIRS = tuple(
    (re.compile(item.value[0]), item.value[1])
    for item in GENERIC_DATA_FACTS["rollback_file_pairs"]
)
_DATA_SUFFIXES = frozenset(
    v for item in GENERIC_DATA_FACTS["migration_data_suffixes"] for v in item.value
)
_PRESENCE = frozenset({"migrations_missing", "schema_constraints_missing"})


def collect(context: DimensionContext) -> Iterator[Excerpt]:
    """Yield schema files, the newest migrations, destructive lines and model
    lines, lazily; the metrics are stored before the first yield."""
    resolved_scope = context.resolved_scope
    if resolved_scope is None and context.scope != "project":
        message = UNRESOLVED_SCOPE_WARNING.format(scope=context.scope)
        if message not in context.warnings:
            context.warnings = (*context.warnings, message)
        reason = UNRESOLVED_SCOPE_REASON.format(scope=context.scope)
        for source in SOURCES_SOUGHT:
            context.sources_missing.append(SourceMiss(source=source, reason=reason))
        return

    facts = getattr(context, "data_facts", None)
    if facts is None:
        facts = _facts(context)
        context.data_facts = facts
    for path, text in facts["schemas"][:MAX_QUOTED]:
        excerpt = whole_file_excerpt(path, text)
        if excerpt is not None:
            yield excerpt
    for path, text in facts["units"][:MAX_QUOTED]:
        excerpt = whole_file_excerpt(path, text)
        if excerpt is not None:
            yield excerpt
    for key in ("destructive", "models"):
        for path, lines, number in facts[key][:MAX_QUOTED]:
            excerpt = _code_extract._excerpt(path, lines, number - 1, number - 1)
            if excerpt is not None:
                yield excerpt


def _in_scope(context: DimensionContext, source: str, scope_set, whole_repo):
    paths = context.role_files.get(source, ())
    in_bounds = list(role_files_in_scope(source, paths, scope_set, whole_repo))
    if paths and not in_bounds:
        context.sources_missing.append(
            SourceMiss(source=source, reason="not in the resolved scope")
        )
    return in_bounds


def _facts(context: DimensionContext) -> dict:
    """Read every input once and store the four metrics on
    ``context.whole_file``; idempotent across the budget's tier passes."""
    scope = context.resolved_scope
    scope_files = tuple(getattr(scope, "files", ()) or ())
    whole_repo = scope is None or getattr(scope, "kind", None) == "project"
    scope_set = frozenset(scope_files)
    note_context_roles(
        context, SOURCES_SOUGHT, scope_set, getattr(scope, "kind", None), whole_repo
    )
    tables = curated_metric_tables()
    dirs, destructive_pattern = migration_patterns(context_conventions(context))

    schemas = []
    for path in sorted(
        _in_scope(context, SCHEMA, scope_set, whole_repo),
        key=lambda p: (p.count("/"), p),
    ):
        text = context.read_source(path)
        if text is not None:
            schemas.append((path, text))

    candidates = [
        p
        for p in scope_files
        if any(part.lower() in dirs for part in PurePosixPath(p).parts[:-1])
        and not PurePosixPath(p).name.startswith(".")
        and (
            PurePosixPath(p).suffix in _DATA_SUFFIXES
            or PurePosixPath(p).suffix in tables.syntax
        )
    ]
    candidates.sort(reverse=True)  # timestamped names: newest first
    cap_note = ""
    if len(candidates) > MAX_MIGRATION_FILES:
        message = CAP_WARNING.format(count=len(candidates), cap=MAX_MIGRATION_FILES)
        context.capped[MIGRATIONS] = (len(candidates), MAX_MIGRATION_FILES)
        if message not in context.warnings:
            context.warnings = (*context.warnings, message)
        cap_note = (
            f"; the newest {MAX_MIGRATION_FILES} of {len(candidates)} migration "
            "files were read"
        )
    downs: set[str] = set()
    units: list[tuple[str, str]] = []
    others: list[str] = []
    for path in candidates[:MAX_MIGRATION_FILES]:
        text = context.read_source(path)
        if not text or not text.strip():
            continue
        if not _is_migration(path, dirs):
            downs.add(path)  # a *.down.* or Flyway undo file: a rollback
            continue
        suffix = PurePosixPath(path).suffix
        if (
            suffix in _DATA_SUFFIXES
            or _UP_START.search(text)
            or _token(tables.migration_rollback_markers, suffix, text)
        ):
            units.append((path, text))
        else:
            others.append(path)  # support code or a one-off data script

    _found(
        context, MIGRATIONS, bool(units or downs),
        f"not found: no migration file (SQL, changelog, or code with an up "
        f"section) in an in-scope directory named "
        f"{', '.join(sorted(dirs))}" + _not_counted(others),
    )
    sources = _code_extract.source_candidates(context, "data-model evidence")
    models: list[tuple[str, list[str], int]] = []
    model_texts: list[tuple[str, str]] = []
    unit_paths = {p for p, _t in units}
    for path, lines, syntax in _code_extract._read(context, sources):
        if path in unit_paths:
            continue
        pattern = tables.orm_model_markers.get(PurePosixPath(path).suffix)
        hits = [
            n for n, line in enumerate(lines, 1) if any(p.search(line) for p in _DDL)
        ]
        if pattern is not None:
            code_lines = strip("\n".join(lines), syntax).split("\n")
            hits += [n for n, code in enumerate(code_lines, 1) if pattern.search(code)]
        hits.sort()
        if hits:
            models.append((path, lines, hits[0]))
            model_texts.append((path, "\n".join(lines)))
    _found(
        context, MODELS, bool(models),
        "not found: no data-model token (the registry's orm_model_markers) and "
        f"no CREATE TABLE in the {len(sources)} in-scope source file(s) scanned",
    )

    destructive = _destructive(units, destructive_pattern)
    context.whole_file = (
        _presence_metric(
            units, downs, schemas, models, cap_note + _not_counted(others), dirs
        ),
        _rollback_metric(units, downs, tables, cap_note),
        _constraint_metric(schemas + units + model_texts, tables),
        _destructive_metric(units, destructive, cap_note),
    )
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
    return {
        "schemas": schemas,
        "units": units,
        "destructive": destructive,
        "models": models,
    }


def _found(context: DimensionContext, source: str, found: bool, reason: str) -> None:
    if found:
        if source not in context.sources_found:
            context.sources_found.append(source)
    elif not any(m.source == source for m in context.sources_missing):
        context.sources_missing.append(SourceMiss(source=source, reason=reason))


def _not_counted(others: list[str]) -> str:
    if not others:
        return ""
    return (
        f"; {len(others)} file(s) in a migration directory were not counted as "
        "migrations, having no up section, SQL or changelog form (support code or "
        f"a one-off data script: {_paths([(p,) for p in others])})"
    )


def _token(table, suffix: str, text: str) -> bool:
    pattern = table.get(suffix)
    return pattern is not None and pattern.search(text) is not None


def _has_rollback(path: str, text: str, downs: set[str], tables) -> bool:
    if _DOWN_START.search(text) or any(p.search(text) for p in _ROLLBACK):
        return True
    if _token(tables.migration_rollback_markers, PurePosixPath(path).suffix, text):
        return True
    for down in downs:
        pure = PurePosixPath(down)
        for pattern, replacement in _PAIRS:
            up = pattern.sub(replacement, pure.name, count=1)
            if up != pure.name and str(pure.with_name(up)) == path:
                return True
    return False


def _destructive(units, pattern) -> list[tuple[str, list[str], int]]:
    """Destructive operations outside down sections and comment lines, with
    the blast-radius dimension's patterns."""
    found = []
    for path, text in units:
        lines = text.split("\n")
        down = False
        for number, line in enumerate(lines, 1):
            if _DOWN_START.search(line):
                down = True
            elif _UP_START.search(line):
                down = False
            if down or _COMMENT_LINE.match(line):
                continue
            if pattern.search(line):
                found.append((path, lines, number))
    return found


def _sites(items) -> str:
    shown = ", ".join(f"{redact(p)}:{n}" for p, *_rest, n in items[:MAX_EXAMPLES])
    more = len(items) - MAX_EXAMPLES
    return shown + (f", and {more} more" if more > 0 else "")


def _paths(items) -> str:
    shown = ", ".join(redact(p) for p, *_rest in items[:MAX_EXAMPLES])
    more = len(items) - MAX_EXAMPLES
    return shown + (f", and {more} more" if more > 0 else "")


def _presence_metric(units, downs, schemas, models, cap_note, dirs) -> SampledMetric:
    name = "migrations_missing"
    if units or downs:
        return _metric(
            name, 0, [p for p, _t in units] or downs,
            f"{len(units)} migration file(s) ({_paths(units)}) in a directory "
            f"named {', '.join(sorted(dirs))}; 0 when any exists, "
            "else 1" + cap_note,
        )
    if not schemas and not models:
        return _metric(
            name,
            abstention="no migration file, schema file or data model was found, "
            "so there is no schema whose migrations could be missing (a "
            "repository without a database is not rated)",
        )
    evidence = [(p, 1) for p, _t in schemas] + [
        (p, n) for p, _l, n in models
    ]
    return _metric(
        name, 1, {p for p, _n in evidence},
        f"a schema exists ({_sites(evidence)}: schema files, data models (the "
        "registry's orm_model_markers) or CREATE TABLE in source) but no "
        "migration file was found; 1 (missing)" + cap_note,
    )


def _rollback_metric(units, downs, tables, cap_note) -> SampledMetric:
    name = "migrations_without_rollback_share"
    if not units:
        return _metric(
            name,
            abstention="no migration file with an up section, SQL or changelog "
            "was found, so no migration could lack a rollback",
        )
    missing = [(p, t) for p, t in units if not _has_rollback(p, t, downs, tables)]
    return _metric(
        name, round(len(missing) / len(units), 4), [p for p, _t in units],
        f"{len(missing)} of {len(units)} migration file(s) have no rollback"
        + (f" ({_paths(missing)})" if missing else "")
        + "; a rollback is a down/downgrade section, a Liquibase rollback, a "
        "*.down.* or Flyway undo sibling file, or a form the framework reverses "
        "(the registry's migration_rollback_markers)" + cap_note,
    )


def _constraint_metric(files, tables) -> SampledMetric:
    name = "schema_constraints_missing"
    if not files:
        return _metric(
            name,
            abstention="no schema file, migration or data model was found, so no "
            "constraint could be declared",
        )
    hits = []
    for path, text in files:
        pattern = tables.schema_constraint_markers.get(PurePosixPath(path).suffix)
        for number, line in enumerate(text.split("\n"), 1):
            if any(p.search(line) for p in _CONSTRAINTS) or (
                pattern is not None and pattern.search(line)
            ):
                hits.append((path, number))
                break
    if hits:
        return _metric(
            name, 0, {p for p, _n in hits},
            f"{len(hits)} of {len(files)} schema, migration or model file(s) "
            f"declare a NOT NULL, unique or foreign-key constraint ({_sites(hits)}; "
            "SQL/Prisma/Liquibase syntax from the generic layer, the registry's "
            "schema_constraint_markers); 0 when any does, else 1",
        )
    return _metric(
        name, 1, {p for p, _t in files},
        f"none of {len(files)} schema, migration or model file(s) "
        f"({_paths(files)}) declares a NOT NULL, unique or foreign-key "
        "constraint; 1 (missing)",
    )


def _destructive_metric(units, destructive, cap_note) -> SampledMetric:
    name = "destructive_migration_ops_observed"
    if not units:
        return _metric(
            name,
            abstention="no migration file with an up section, SQL or changelog "
            "was found, so no destructive operation could be observed",
        )
    return _metric(
        name, len(destructive), [p for p, _t in units],
        f"{len(destructive)} destructive operation(s) (DROP TABLE/COLUMN, "
        "RENAME COLUMN/TO, drop_table, remove_column, RemoveField, dropColumn, "
        "...) outside down sections and comment lines of "
        f"{len(units)} migration file(s)"
        + (f": {_sites(destructive)}" if destructive else "")
        + "; quoted for the calling agent, since a final expand/contract step "
        "is deliberate" + cap_note,
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
