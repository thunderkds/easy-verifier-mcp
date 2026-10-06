"""The optional ``finance`` pack (T048, DDR-0008 §4, FR-053).

Area #3 (financial integrity & historical reconstruction), three counts:

* money-named fields declared or typed as a binary float (``price: number``,
  ``amount: float``, ``costPerUnit Float``, ``"fee" double precision``);
* ledger, transaction or payment tables and models with no audit column
  (``created_at`` / ``created_by`` or similar) in their declaration;
* UPDATE / DELETE statements and ORM update / delete calls aimed at a
  ledger declared in the same repository (append-only evidence).

The two ledger counts abstain when no ledger is declared: nothing to judge,
never 0. Whether a ledger is *correct* is judgment: its declarations and the
calls that change it are quoted for the calling agent and feed no rule. Which
text counts as a money name, a float type, a ledger or an audit column is the
registry's data (``registry/packs/finance.toml``), never this module's.

The pack runs only when ``roles.active_packs`` names it.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass
from functools import lru_cache

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

NAME = "finance"

PURPOSE = (
    "Optional finance pack, active only when configured or picked: gather "
    "money-named fields declared as binary floating point, ledger, "
    "transaction and payment tables with their audit columns, and the "
    "statements that update or delete their rows; whether a ledger balances "
    "or is correct is judgment, quoted for the agent and not rated."
)

MONEY = "money-named field declarations (the pack's money_declarations)"
LEDGERS = "ledger, transaction or payment tables (the pack's ledger_declarations)"

ROLES: tuple[SourceRole, ...] = (
    SourceRole(name=MONEY, patterns=()),
    SourceRole(name=LEDGERS, patterns=()),
)
"""Pseudo-roles credited by the scan: a money field found, a ledger found."""

SOURCES_SOUGHT: tuple[str, ...] = tuple(item.name for item in ROLES)

MAX_SCHEMA_FILES = 200
"""Schema files (the pack's schema_paths) read, in path order."""

MAX_LISTED = 20
"""Sites named in one derivation; the rest are counted."""

MAX_BODY_LINES = 300
"""Lines a ledger declaration's body may span."""

MAX_QUOTED_LINES = 40
"""Lines of one ledger declaration quoted for the agent."""

MARKER_LINES = 5
"""Lines above a class searched for its entity annotation."""

CONTEXT_LINES = 1

FLOAT_METRIC, AUDIT_METRIC, MUTATION_METRIC = PACK_METRICS[NAME]

UNRESOLVED_SCOPE_REASON = (
    "not examined: the {scope} scope could not be resolved "
    "(its required selector was not supplied)"
)

_WORDS = re.compile(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|\d+")
_OPEN, _CLOSE = "({[", ")}]"


@dataclass(frozen=True)
class _Patterns:
    money_names: frozenset[str]
    money_excluded: frozenset[str]
    declarations: tuple[re.Pattern[str], ...]
    float_types: tuple[re.Pattern[str], ...]
    schema_paths: tuple[str, ...]
    ledger_names: frozenset[str]
    non_ledger_heads: frozenset[str]
    suffixes: frozenset[str]
    ledgers: tuple[re.Pattern[str], ...]
    entity_classes: tuple[re.Pattern[str], ...]
    entity_markers: tuple[re.Pattern[str], ...]
    audit: tuple[re.Pattern[str], ...]
    mutations: tuple[re.Pattern[str], ...]


@lru_cache(maxsize=1)
def _patterns() -> _Patterns:
    fields = load_pack(NAME).fields

    def values(field: str) -> tuple[str, ...]:
        return tuple(value for cited in fields[field] for value in cited.value)

    def regexes(field: str) -> tuple[re.Pattern[str], ...]:
        return tuple(re.compile(item, re.MULTILINE) for item in values(field))

    return _Patterns(
        money_names=frozenset(values("money_names")),
        money_excluded=frozenset(values("money_excluded_words")),
        declarations=regexes("money_declarations"),
        float_types=regexes("float_types"),
        schema_paths=values("schema_paths"),
        ledger_names=frozenset(values("ledger_names")),
        non_ledger_heads=frozenset(values("non_ledger_heads")),
        suffixes=frozenset(values("name_suffixes")),
        ledgers=regexes("ledger_declarations"),
        entity_classes=regexes("entity_classes"),
        entity_markers=regexes("entity_markers"),
        audit=regexes("audit_columns"),
        mutations=regexes("ledger_mutations"),
    )


def words(name: str) -> list[str]:
    """``costPerUnit`` -> ``["cost", "per", "unit"]``."""
    return [word.lower() for word in _WORDS.findall(name)]


def is_money_name(name: str) -> bool:
    found = set(words(name))
    patterns = _patterns()
    return bool(found & patterns.money_names) and not found & patterns.money_excluded


def _singular(word: str) -> str:
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    if word.endswith("s") and not word.endswith("ss") and len(word) > 3:
        return word[:-1]
    return word


def entity_key(name: str) -> str:
    """The name a ledger is matched by: words, trailing repository / model
    suffixes dropped, plurals folded (``paymentRepository`` -> ``payment``,
    ``ledger_entries`` -> ``ledger_entry``)."""
    return "_".join(_singular(part) for part in _entity_words(name))


def _entity_words(name: str) -> list[str]:
    parts = words(name)
    while len(parts) > 1 and parts[-1] in _patterns().suffixes:
        parts.pop()
    return parts


def is_ledger_name(name: str) -> bool:
    patterns = _patterns()
    parts = _entity_words(name)
    return (
        bool({_singular(part) for part in parts} & patterns.ledger_names)
        and not {parts[-1], _singular(parts[-1])} & patterns.non_ledger_heads
    )


@dataclass(frozen=True)
class _Ledger:
    path: str
    line: int
    end: int
    name: str
    audited: bool


@dataclass
class _Scan:
    files: list[tuple[str, list[str]]]
    money: list[tuple[str, int, str, str]]
    floats: list[tuple[str, int, str, str]]
    ledgers: list[_Ledger]
    mutations: list[tuple[str, int, str]]


def collect(context: DimensionContext) -> Iterator[Excerpt]:
    """Yield the lines around each float money field, each ledger
    declaration and each ledger mutation, for the agent."""
    if context.resolved_scope is None and context.scope != "project":
        reason = UNRESOLVED_SCOPE_REASON.format(scope=context.scope)
        for source in SOURCES_SOUGHT:
            context.sources_missing.append(SourceMiss(source=source, reason=reason))
        return

    scan = getattr(context, "finance_scan", None)
    if scan is None:
        # Once per context, before the first yield: the budget may call
        # ``collect`` once per tier and stop pulling at any yield.
        scan = _scan(context)
        context.finance_scan = scan
        context.whole_file = _metrics(scan)
    _record_roles(context, scan)

    texts = dict(scan.files)
    for ledger in scan.ledgers:
        lines = texts[ledger.path]
        end = min(ledger.end, ledger.line + MAX_QUOTED_LINES - 1)
        excerpt = _code_extract._excerpt(ledger.path, lines, ledger.line - 1, end - 1)
        if excerpt is not None:
            yield excerpt
    sites = [(p, n) for p, n, _name in scan.mutations]
    sites += [(p, n) for p, n, _name, _type in scan.floats]
    for path in sorted({path for path, _line in sites}):
        yield from _windows(path, texts[path], [n for p, n in sites if p == path])


def _scan(context: DimensionContext) -> _Scan:
    patterns = _patterns()
    sources = [
        (path, lines)
        for path, lines, _syntax in _code_extract._read(
            context,
            _code_extract.source_candidates(context, "finance money and ledger checks"),
        )
    ]
    read = {path for path, _lines in sources}
    scope_files = tuple(getattr(context.resolved_scope, "files", ()) or ())
    is_schema = _matcher(patterns.schema_paths)
    schemas = sorted(p for p in scope_files if is_schema(p) and p not in read)
    files = list(sources)
    for path in schemas[:MAX_SCHEMA_FILES]:
        text = context.read_source(path)
        if text:
            files.append((path, _lines(text)))

    money = sorted(
        {
            (path, number, match["name"], match["type"])
            for path, lines in files
            for number, line in enumerate(lines, start=1)
            for pattern in patterns.declarations
            for match in pattern.finditer(line)
            if is_money_name(match["name"])
        }
    )
    floats, seen = [], set()
    for path, number, name, kind in money:
        if (path, number, name) not in seen and any(
            pattern.search(kind) for pattern in patterns.float_types
        ):
            seen.add((path, number, name))
            floats.append((path, number, name, kind))

    ledgers = sorted(
        {ledger for path, lines in files for ledger in _ledgers(path, lines)},
        key=lambda item: (item.path, item.line),
    )
    keys = {entity_key(ledger.name) for ledger in ledgers}
    mutations = sorted(
        {
            (path, number, match["name"])
            for path, lines in files
            for number, line in enumerate(lines, start=1)
            for pattern in patterns.mutations
            for match in pattern.finditer(line)
            if entity_key(match["name"]) in keys
        }
    )
    return _Scan(files, money, floats, ledgers, mutations)


def _ledgers(path: str, lines: list[str]) -> Iterator[_Ledger]:
    patterns = _patterns()
    for index, line in enumerate(lines):
        matches = [m for p in patterns.ledgers for m in p.finditer(line)]
        above = "\n".join(lines[max(0, index - MARKER_LINES) : index])
        if any(marker.search(above) for marker in patterns.entity_markers):
            matches += [m for p in patterns.entity_classes for m in p.finditer(line)]
        for match in matches:
            if not is_ledger_name(match["name"]):
                continue
            end = _body_end(lines, index, match.start())
            body = "\n".join([line[match.start() :], *lines[index + 1 : end]])
            yield _Ledger(
                path=path,
                line=index + 1,
                end=end,
                name=match["name"],
                audited=any(p.search(body) for p in patterns.audit),
            )


def _body_end(lines: list[str], index: int, start: int) -> int:
    """One past the last line of the declaration starting at ``lines[index]``
    column ``start``: to where its brackets close, else while indented
    deeper than its first line (a Python class, a one-line SQL string)."""
    depth = _depth(lines[index][start:])
    end = index + 1
    limit = min(len(lines), index + MAX_BODY_LINES)
    if depth > 0:
        while end < limit and depth > 0:
            depth += _depth(lines[end])
            end += 1
        return end
    indent = _indent(lines[index])
    while end < limit and (not lines[end].strip() or _indent(lines[end]) > indent):
        end += 1
    return end


def _depth(text: str) -> int:
    return sum(text.count(c) for c in _OPEN) - sum(text.count(c) for c in _CLOSE)


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def _metrics(scan: _Scan) -> tuple[SampledMetric, ...]:
    where = f"in {len(scan.files)} source and schema file(s)"
    if not scan.files:
        floats = _abstain(
            FLOAT_METRIC,
            "no in-scope source file of a registry language or schema file (the "
            "pack's schema_paths) was read, so no money field was looked for",
        )
    elif not scan.money:
        floats = _abstain(
            FLOAT_METRIC,
            f"no money-named field declaration (the pack's money_names in "
            f"money_declarations) was found {where}, so there is nothing to judge",
        )
    else:
        floats = _count(
            FLOAT_METRIC,
            [(p, n, f"{name}: {kind}") for p, n, name, kind in scan.floats],
            f"money-named field(s) of a binary floating-point type, of "
            f"{len({(p, n, nm) for p, n, nm, _k in scan.money})} money-named "
            f"declaration(s) {where}",
            "a money value held in binary floating point cannot represent most "
            "decimal amounts exactly; integer minor units and decimal types count "
            "as exact; matched textually against the pack's money_declarations "
            "and float_types, so a count is a place to look",
            [p for p, _n, _name, _kind in scan.money],
        )
    if not scan.ledgers:
        reason = (
            f"no ledger, transaction or payment table or model (the pack's "
            f"ledger_declarations and ledger_names) was found {where}, so there "
            "is no ledger to judge"
        )
        return (
            floats,
            _abstain(AUDIT_METRIC, reason),
            _abstain(MUTATION_METRIC, reason),
        )
    declared = [(item.path, item.line, item.name) for item in scan.ledgers]
    audit = _count(
        AUDIT_METRIC,
        [(i.path, i.line, i.name) for i in scan.ledgers if not i.audited],
        f"ledger declaration(s) with no audit column, of {len(declared)} found {where}",
        "an audit column (when and by whom a row was recorded, the pack's "
        "audit_columns) is looked for in the declaration's own body; one that "
        "inherits from a base, audit or timestamp class is never counted",
        [p for p, _n, _name in declared],
    )
    mutations = _count(
        MUTATION_METRIC,
        scan.mutations,
        f"update or delete site(s) aimed at the {len(declared)} ledger "
        f"declaration(s) {where}",
        "matched textually against the pack's ledger_mutations; a ledger is "
        "corrected by a new reversing entry, so each site is a place to look, "
        "not proof that history is lost",
        [p for p, _n, _name in declared],
    )
    return (floats, audit, mutations)


def _count(name, sites, what, method, scanned) -> SampledMetric:
    """Paths are cited and listed as the pack's ``files_read`` holds them:
    redacted (a file name can look like a secret, core/pipeline.py)."""
    sites = sorted(set(sites))
    listed = ", ".join(
        f"{redact(p)}:{n} ({label})" for p, n, label in sites[:MAX_LISTED]
    )
    more = f" and {len(sites) - MAX_LISTED} more" if len(sites) > MAX_LISTED else ""
    cited = sorted({redact(p) for p in ({p for p, _n, _l in sites} or set(scanned))})
    return SampledMetric(
        name=name,
        value=len(sites),
        abstention=None,
        computed_from=tuple(cited),
        derivation=f"{len(sites)} {what}: {listed or 'none'}{more}; {method}",
    )


def _abstain(name: str, reason: str) -> SampledMetric:
    return SampledMetric(
        name=name, value=None, abstention=reason, computed_from=(), derivation=""
    )


def _record_roles(context: DimensionContext, scan: _Scan) -> None:
    filled = {MONEY: bool(scan.money), LEDGERS: bool(scan.ledgers)}
    reasons = {
        MONEY: f"no money-named field declaration was found in the "
        f"{len(scan.files)} source and schema file(s) read",
        LEDGERS: f"no ledger, transaction or payment table or model was found in "
        f"the {len(scan.files)} source and schema file(s) read",
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
