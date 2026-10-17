"""Measured, citable facts computed over an evidence pack (FR-027, FR-027a).

A **metric** is one measured fact about the target, derived *exclusively* from
an :class:`~easy_verifier.core.models.EvidencePack` that a dimension already
produced, and carrying the file references it was computed from. Four things
this module deliberately does **not** do:

* **read anything.** There is no ``open``, no ``Path.read_*``, no
  ``RepoContext`` import, and nothing here reaches the filesystem, a
  subprocess or the network. That is structural, not a convention: the module
  imports only :mod:`dataclasses`, :mod:`json`, :mod:`re`,
  :mod:`pathlib.PurePosixPath` (a pure string type that touches no disk),
  this package's own plain-data models and its pure tokenizer
  (:mod:`~easy_verifier.core.tokens`, string work only). A metric that
  could read a file could cite evidence the pack never gathered, which is
  the whole point of FR-027.
  Language knowledge (which suffixes are code, how tests are named, declared
  and assert) is the reference registry's (DDR-0007, FR-041), and arrives as a
  :class:`LanguageTables` argument the caller built from the already-loaded
  registry (``core/metric_tables.py``) -- this module holds no copy of it;
* **rate, threshold, weight or judge anything.** A metric is a fact, never an
  opinion. Rules over these metrics are T020's job (``core/judge.py``);
* **invent a metric for a dimension that failed.** A
  :class:`~easy_verifier.core.models.DimensionSlot` with no pack contributes no
  metrics, and is named in :attr:`MetricSet.dimensions_without_pack` so the
  omission is visible to any reader holding only the metric set;
* **report a whole-set figure over a truncated pack.** See below.

**Whole-set-dependent vs. evidence-local** (FR-027a). A ratio, density or
aggregate share describes the *set* it was computed over. Over a pack the byte
budget truncated, that set is "what survived the budget", not the repository —
so every :data:`WHOLE_SET` metric **abstains** when the pack reports
truncation, naming the omitted count as a lower bound. An
:data:`EVIDENCE_LOCAL` metric still computes there, because its truth does not
depend on what else was read: a redaction hit that was observed was observed,
whatever the budget dropped afterwards.

That rule is applied by :func:`compute_metrics` *before* a definition's
``compute`` ever runs, so a metric author cannot forget it.

**Abstention is a state, never a value** (Critical Constraint 1b, DDR-0003).
:class:`MetricAbstention` is a distinct type carrying its own reason, held in
the same field a number would occupy. It defines no ``__float__``, ``__int__``
or ``__index__``, so a consumer cannot get arithmetic out of an abstaining
metric by accident — only by asking :attr:`Metric.numeric_value`, which raises,
or by checking :attr:`Metric.abstained` first.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import PurePosixPath

from .models import CombinedPack, EvidencePack, Excerpt, SampledMetric
from .tokens import (
    MAX_LINE_CHARS,
    LanguageSyntax,
    approximate_ccn,
    import_statements,
    strip,
)

WHOLE_SET = "whole_set"
"""A ratio, density or aggregate share: it describes the whole set it was
computed over, so it abstains on a truncated pack (FR-027a)."""

EVIDENCE_LOCAL = "evidence_local"
"""An observation over the evidence actually present: still true whatever the
byte budget dropped, so it computes over a truncated pack (FR-027a)."""

FAMILY_TEST_STRENGTH = "test_strength"
FAMILY_SECURITY_SURFACE = "security_surface"
FAMILY_EVIDENCE_COVERAGE = "evidence_coverage"
FAMILY_CODE_SHAPE = "code_shape"

FAMILIES = (
    FAMILY_TEST_STRENGTH,
    FAMILY_SECURITY_SURFACE,
    FAMILY_EVIDENCE_COVERAGE,
    FAMILY_CODE_SHAPE,
)

_CLASSIFIED_BY = (
    "source vs. test is classified by path convention, never by reading or "
    "parsing the file: the deepest directory segment naming a source root "
    "(src/, lib/, pkg/, ...) or a test root (tests/, spec/, ...) decides, and "
    "only a file under neither is decided by its basename"
)

_TRUNCATED_ABSTENTION = (
    "whole-set-dependent: the byte budget truncated this pack, so any ratio, "
    "density or share computed here describes what survived the budget, not "
    "the repository (at least {omitted} item(s) omitted -- a lower bound, "
    "never an exact count)"
)


class MetricAbstained(LookupError):
    """Raised by :attr:`Metric.numeric_value` on an abstaining metric."""


class MetricCitationError(ValueError):
    """A metric cited a reference the pack never read (FR-027, AC #7)."""


@dataclass(frozen=True)
class MetricAbstention:
    """Why a metric emitted no number. Deliberately not a number.

    The reason lives *inside* the value object (DDR-0004's lesson) so a
    consumer cannot reach the slot where a number would be without also
    reaching why it is absent.
    """

    reason: str

    omitted_lower_bound: int | None = None
    """Items the byte budget is *known* to have rejected, when truncation is
    the cause. A **lower bound**, never a total: the pipeline stops pulling at
    the first rejection and never drains the remainder to count it."""


@dataclass(frozen=True)
class Metric:
    """One measured fact, or one abstention, with its evidence."""

    name: str
    family: str
    kind: str
    """:data:`WHOLE_SET` or :data:`EVIDENCE_LOCAL`."""

    dimension: str
    """The dimension whose pack this was computed from. Kept beside ``name``
    rather than folded into it, so T020's rules can reference a metric by its
    stable name across dimensions."""

    outcome: float | int | MetricAbstention
    """The measured value, **or** a :class:`MetricAbstention`. One field, two
    types on purpose: there is no separate ``value`` attribute a consumer could
    read past an abstention."""

    computed_from: tuple[str, ...]
    """Evidence references this was derived from: repository-relative paths
    from ``pack.files_read`` and/or ``Excerpt.ref`` strings from
    ``pack.excerpts``. Non-empty for every non-abstaining metric, and validated
    against the pack by :func:`check_citations`."""

    derivation: str
    """How to recompute this by hand from the evidence beside it
    (Critical Constraint 1a)."""

    @property
    def abstained(self) -> bool:
        return isinstance(self.outcome, MetricAbstention)

    @property
    def abstention(self) -> MetricAbstention | None:
        return self.outcome if isinstance(self.outcome, MetricAbstention) else None

    @property
    def numeric_value(self) -> float | int:
        """The measured number, or :class:`MetricAbstained` if there is none."""
        if isinstance(self.outcome, MetricAbstention):
            raise MetricAbstained(
                f"metric {self.name!r} ({self.dimension}) abstained: "
                f"{self.outcome.reason}"
            )
        return self.outcome


@dataclass(frozen=True)
class MetricSet:
    """Every metric computed for one call, in a deterministic order."""

    metrics: tuple[Metric, ...]

    dimensions_without_pack: tuple[tuple[str, str], ...] = field(default=())
    """``(dimension, error)`` for each requested dimension that produced no
    pack. No metric is invented for these; naming them here is what stops a
    reader holding only this set from reading their absence as "measured and
    found nothing"."""

    def __iter__(self) -> Iterator[Metric]:
        return iter(self.metrics)

    def __len__(self) -> int:
        return len(self.metrics)

    def by_name(self, name: str) -> tuple[Metric, ...]:
        """Every metric with this name, across dimensions, in set order."""
        return tuple(metric for metric in self.metrics if metric.name == name)

    def serialize(self) -> str:
        """A deterministic JSON rendering (FR-022, AC #9).

        Field order is fixed by this function, never by dict iteration order,
        and the metric order is :data:`METRIC_DEFINITIONS` order within
        dimension order -- so two runs over the same pack, in two processes,
        produce byte-identical output.
        """
        return json.dumps(
            {
                "metrics": [_serializable(metric) for metric in self.metrics],
                "dimensions_without_pack": [
                    [name, error] for name, error in self.dimensions_without_pack
                ],
            },
            sort_keys=True,
            ensure_ascii=True,
            separators=(",", ":"),
        )


def _serializable(metric: Metric) -> dict:
    if isinstance(metric.outcome, MetricAbstention):
        outcome = {
            "abstained": True,
            "reason": metric.outcome.reason,
            "omitted_lower_bound": metric.outcome.omitted_lower_bound,
        }
    else:
        outcome = {"abstained": False, "value": metric.outcome}
    return {
        "name": metric.name,
        "family": metric.family,
        "kind": metric.kind,
        "dimension": metric.dimension,
        "outcome": outcome,
        "computed_from": list(metric.computed_from),
        "derivation": metric.derivation,
    }


LAYER_PATHS_CURATED_NOTE = (
    "curated layer_paths only: no local-layer or .easy-verifier.toml layer "
    "paths were declared"
)
"""T078: the layer rule's source note when no repository extra applies."""


@dataclass(frozen=True)
class LanguageTables:
    """The registry's language knowledge, as plain compiled data (T031).

    Built by ``core/metric_tables.py`` from the loaded reference registry and
    handed to :func:`compute_metrics`; never loaded here, so this module still
    reads nothing. Treat it as immutable.
    """

    source_suffixes: frozenset[str]
    """File suffixes (dot included) of files that are code."""

    test_name_patterns: tuple[re.Pattern[str], ...]
    """Full-match patterns over a base name that make it a test file."""

    colocated_test_patterns: tuple[re.Pattern[str], ...]
    """Full-match patterns over a base name that make it a test file even
    under a source-root directory (T052); a subset of test names."""

    test_candidates: Mapping[str, tuple[str, ...]]
    """Source suffix -> test base-name templates with ``{stem}``/``{ext}``. A
    template starting ``./`` only matches a test in the source's directory."""

    test_declarations: tuple[re.Pattern[str], ...]
    """Each counts test declarations independently (``findall``)."""

    assertions: re.Pattern[str]
    """One alternation; its non-overlapping matches are the assertions."""

    syntax: Mapping[str, LanguageSyntax] = field(default_factory=dict)
    """Source suffix -> the language's structure tokens (T033); a suffix
    absent here gets no CCN or import evidence."""

    sinks: Mapping[str, tuple[SinkPattern, ...]] = field(default_factory=dict)
    """Source suffix -> the language's dangerous-sink tokens (T034); matched
    only where ``syntax`` can blank that language's comments and strings."""

    skip_markers: Mapping[str, re.Pattern[str]] = field(default_factory=dict)
    network_calls: Mapping[str, re.Pattern[str]] = field(default_factory=dict)
    type_escapes: Mapping[str, re.Pattern[str]] = field(default_factory=dict)
    """Source suffix -> the language's T040 area tokens (FR-051), present
    only where ``syntax`` is: skip markers and network calls are matched in
    test code, type escapes in source code with its comments kept."""

    type_stub_patterns: tuple[re.Pattern[str], ...] = ()
    """Full-match base-name patterns of generated type stubs (``*.d.ts``)."""

    public_declarations: Mapping[str, re.Pattern[str]] = field(default_factory=dict)
    """Source suffix -> the language's public-declaration tokens (T055),
    anchored at a line start; read by the blast-radius dimension, never here."""

    cookie_calls: Mapping[str, re.Pattern[str]] = field(default_factory=dict)
    cookie_flags: Mapping[str, Mapping[str, re.Pattern[str]]] = field(
        default_factory=dict
    )
    """Source suffix -> the language's cookie tokens (T056, area #8): a
    statement that sets a cookie, and per flag of :data:`COOKIE_FLAGS` the
    language declares, the tokens that set it inside that statement."""

    layer_of: Callable[[str], str | None] | None = field(default=None, compare=False)
    layer_evidence: Callable[..., object] | None = field(default=None, compare=False)
    """``(path, text, imported names) -> structure.LayerEvidence`` (T088,
    DDR-0012): what a file's code does (route, DB/ORM call), bound by the
    builder; ``None`` observes nothing, so only the path hints classify."""
    layer_paths_note: str = field(default=LAYER_PATHS_CURATED_NOTE, compare=False)
    """Which layer_paths sources ``layer_of`` applies (T078), for the
    derivation: curated only, or plus the local layer / .easy-verifier.toml."""
    """Path -> ``api``/``service``/``data``/``shared`` or ``None`` (T074): the
    declared ``layer_paths`` conventions, bound by the builder
    (``metric_tables``); ``None`` classifies nothing."""
    purpose_rank: Callable[[str], int] | None = field(default=None, compare=False)
    """``core.batches.purpose_rank`` (T113), bound by the builder: 0/1 is
    application source, 2+ tooling/config/generated. ``None``: all count."""
    package_manifests: tuple[str, ...] = field(default=(), compare=False)
    """Repository paths of the ``package-manifest`` role (T093), from the role
    resolution's whole-repository walk, bound by the dimension: where the layer
    rule's backend units are. Empty: every file sits in the root's unit."""

    auth_markers: Mapping[str, re.Pattern[str]] = field(default_factory=dict)
    """Source suffix -> the language's authentication/session tokens (T056):
    the gate the cookie metric computes behind, never scored itself."""

    type_configs: tuple[TypeConfigFile, ...] = ()
    type_strict: Mapping[str, re.Pattern[str]] = field(default_factory=dict)
    type_strict_off: Mapping[str, re.Pattern[str]] = field(default_factory=dict)
    type_config_extends: Mapping[str, re.Pattern[str]] = field(default_factory=dict)
    """Language name -> its type-checker configuration tokens (T056, area
    #17); only languages with a type checker declare them."""

    swallowed_errors: Mapping[str, re.Pattern[str]] = field(default_factory=dict)
    outbound_calls: Mapping[str, re.Pattern[str]] = field(default_factory=dict)
    call_timeouts: Mapping[str, re.Pattern[str]] = field(default_factory=dict)
    client_timeouts: Mapping[str, re.Pattern[str]] = field(default_factory=dict)
    retry_calls: Mapping[str, re.Pattern[str]] = field(default_factory=dict)
    retry_backoff: Mapping[str, re.Pattern[str]] = field(default_factory=dict)
    query_calls: Mapping[str, re.Pattern[str]] = field(default_factory=dict)
    loop_keywords: Mapping[str, re.Pattern[str]] = field(default_factory=dict)
    transaction_markers: Mapping[str, re.Pattern[str]] = field(default_factory=dict)
    """Source suffix -> the language's T043 reliability tokens (areas #6, #12,
    #13, #15), present only where ``syntax`` is and the language declares the
    field; read through :func:`reliability_findings`."""
    request_validation: Mapping[str, re.Pattern[str]] = field(default_factory=dict)
    api_spec_generators: Mapping[str, re.Pattern[str]] = field(default_factory=dict)
    api_version_markers: Mapping[str, re.Pattern[str]] = field(default_factory=dict)
    """Source suffix -> the language's T044 api tokens (area #7); read by the
    ``api`` dimension over whole files."""
    orm_model_markers: Mapping[str, re.Pattern[str]] = field(default_factory=dict)
    logging_markers: Mapping[str, re.Pattern[str]] = field(default_factory=dict)
    """Source suffix -> the language's T046 logging/tracing tokens (area #14);
    read by the ``operations`` dimension over whole files."""
    schema_constraint_markers: Mapping[str, re.Pattern[str]] = field(
        default_factory=dict
    )
    migration_rollback_markers: Mapping[str, re.Pattern[str]] = field(
        default_factory=dict
    )
    """Source suffix -> the language's T045 data tokens (area #4); read by the
    ``data`` dimension over whole files."""
    ci_files: Callable[[str], bool] | None = None
    release_files: Callable[[str], bool] | None = None
    """Path matchers for the ``ci-workflow`` and ``release-config`` roles
    (T041): which excerpts of a supply-chain pack are CI or release files."""

    lockfile_install: re.Pattern[str] | None = None
    """The registry's ``lockfile_install`` tokens, all languages, as one
    alternation; ``None`` when no language declares any."""

    action_reference: re.Pattern[str] | None = None
    """Generic layer: an external step reference, group 1 being the reference
    (``uses: actions/checkout@v4`` -> ``actions/checkout@v4``)."""

    pinned_reference: tuple[re.Pattern[str], ...] = ()
    local_reference: tuple[str, ...] = ()
    """Generic layer: a reference is pinned when a pattern matches it, and is
    not an external dependency when it starts with a local prefix."""

    provenance_steps: re.Pattern[str] | None = None
    """Generic layer: tokens showing an SBOM, signing or provenance step,
    matched case-insensitively."""


@dataclass(frozen=True)
class TypeConfigFile:
    """One registry ``type_config_files`` value, compiled (T056)."""

    language: str
    name: re.Pattern[str]
    """Full-match pattern over a base name."""
    header: str | None
    """The section header holding the type checker's settings in a shared
    file (``[tool.mypy]``); ``None`` when the whole file is its."""


@dataclass(frozen=True)
class SinkPattern:
    """One registry ``security_sinks`` token, compiled (T034)."""

    cwe: str
    token: str
    citation_url: str
    regex: re.Pattern[str]


@dataclass(frozen=True)
class SinkHit:
    """One sink match: 1-indexed lines within the text it was found in."""

    line: int
    end_line: int
    cwe: str
    citation_url: str


def sink_hits(path: str, text: str, tables: LanguageTables) -> tuple[SinkHit, ...]:
    """Every registry sink token matching ``text`` (the contents of ``path``).

    Tokens match code only: comments and strings are blanked first
    (``core/tokens.py``), so a sink named in a comment or a string is no hit;
    a string that interpolates leaves one mark, which ``<INTERP>`` matches.
    A match starting on a line longer than ``MAX_LINE_CHARS`` (generated or
    minified code) is ignored. One hit per starting line and CWE, by line.
    """
    suffix = PurePosixPath(path).suffix
    syntax = tables.syntax.get(suffix)
    patterns = tables.sinks.get(suffix, ())
    if syntax is None or not patterns:
        return ()
    code = strip(text, syntax, mark_interpolation=True)
    lines = code.split("\n")
    found: dict[tuple[int, str], SinkHit] = {}
    for pattern in patterns:
        for match in pattern.regex.finditer(code):
            line = code.count("\n", 0, match.start()) + 1
            if len(lines[line - 1]) > MAX_LINE_CHARS:
                continue
            end = line + code.count("\n", match.start(), match.end())
            hit = SinkHit(line, end, pattern.cwe, pattern.citation_url)
            found.setdefault((line, pattern.cwe), hit)
    return tuple(found[key] for key in sorted(found))


COOKIE_FLAGS = ("secure", "httponly", "samesite")
"""The cookie attributes OWASP ASVS 5.0.0 V3.3.1, V3.3.4 and V3.3.2 require."""

_CHAINED = re.compile(r"[ \t\r\n]*\.")


@dataclass(frozen=True)
class CookieSite:
    """One cookie-setting statement (T056): its line span in the text read,
    and the declared flags it does not set -- ``None`` when the statement runs
    past the end of that text, so its flags cannot be judged."""

    line: int
    end_line: int
    missing: tuple[str, ...] | None


def cookie_sites(
    path: str, text: str, tables: LanguageTables
) -> tuple[CookieSite, ...]:
    """Every registry ``cookie_calls`` statement in ``text`` (the contents of
    ``path``), one per starting line, by line.

    The call token matches code with comments and strings blanked; the
    statement runs to a ``;`` or a line end outside brackets (a next line
    starting with ``.`` continues it), or to a closing bracket it did not
    open; a flag token matches inside it with comments blanked and strings
    kept. A call starting on a line longer than ``MAX_LINE_CHARS`` is skipped.
    """
    suffix = PurePosixPath(path).suffix
    syntax = tables.syntax.get(suffix)
    calls = tables.cookie_calls.get(suffix)
    if syntax is None or calls is None:
        return ()
    flags = tables.cookie_flags.get(suffix, {})
    code = strip(text, syntax)
    kept = strip(text, syntax, keep_strings=True)
    lines = code.split("\n")
    found: dict[int, CookieSite] = {}
    for match in calls.finditer(code):
        line = _line_of(code, match.start())
        if line in found or len(lines[line - 1]) > MAX_LINE_CHARS:
            continue
        end = _statement_end(code, match.start())
        if end is None:
            found[line] = CookieSite(line, len(lines), None)
            continue
        statement = kept[match.start() : end]
        missing = tuple(
            name
            for name in COOKIE_FLAGS
            if name in flags and not flags[name].search(statement)
        )
        end_line = _line_of(code, end) if end < len(code) else len(lines)
        found[line] = CookieSite(line, end_line, missing)
    return tuple(found[key] for key in sorted(found))


def _statement_end(code: str, start: int) -> int | None:
    """The offset ending the statement that starts at ``start``, or ``None``
    when brackets are still open at the end of ``code``."""
    depth = 0
    for index in range(start, len(code)):
        char = code[index]
        if char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
            if depth < 0:
                return index
        elif depth == 0 and (
            char == ";" or (char == "\n" and not _CHAINED.match(code, index + 1))
        ):
            return index
    return len(code) if depth == 0 else None


def auth_lines(path: str, text: str, tables: LanguageTables) -> tuple[int, ...]:
    """Lines of ``text`` (the contents of ``path``) holding a registry
    ``auth_markers`` token, matched after comments and strings are blanked;
    a line longer than ``MAX_LINE_CHARS`` is skipped (it is never quoted)."""
    suffix = PurePosixPath(path).suffix
    syntax = tables.syntax.get(suffix)
    markers = tables.auth_markers.get(suffix)
    if syntax is None or markers is None:
        return ()
    code = strip(text, syntax)
    lines = code.split("\n")
    found = {_line_of(code, match.start()) for match in markers.finditer(code)}
    return tuple(
        sorted(line for line in found if len(lines[line - 1]) <= MAX_LINE_CHARS)
    )


@dataclass(frozen=True)
class TypeConfigSection:
    """The type checker's settings in one configuration text (T056): a
    1-indexed inclusive line span, whole file or one section."""

    language: str
    line: int
    end_line: int
    header: str | None


def type_config_sections(
    path: str, text: str, tables: LanguageTables
) -> tuple[TypeConfigSection, ...]:
    """The type-checker sections of ``text`` (the contents of ``path``).

    A declared header opens its section only as a whole line of its own; the
    section runs to the line before the next line starting with ``[`` (the
    next INI/TOML header, a TOML sub-table included), else to the end.
    """
    name = PurePosixPath(path).name
    lines = text.split("\n")
    found: list[TypeConfigSection] = []
    for config in tables.type_configs:
        if not config.name.fullmatch(name):
            continue
        if config.header is None:
            found.append(TypeConfigSection(config.language, 1, len(lines), None))
            continue
        for index, line in enumerate(lines):
            if line.strip() != config.header:
                continue
            end = next(
                (j for j in range(index + 1, len(lines)) if lines[j].startswith("[")),
                len(lines),
            )
            found.append(
                TypeConfigSection(config.language, index + 1, end, config.header)
            )
    return tuple(found)


_STRING = re.compile(r'"((?:[^"\\\n]|\\.)*)"')


def extends_targets(text: str, token: re.Pattern[str]) -> tuple[str, ...]:
    """The string, or ``[...]`` list of strings, right after each ``token``
    match in ``text``, in order."""
    targets: list[str] = []
    for match in token.finditer(text):
        rest = text[match.end() :].lstrip(" \t")
        if rest.startswith("["):
            close = rest.find("]")
            rest = rest[: close if close >= 0 else len(rest)]
            targets.extend(_STRING.findall(rest))
        else:
            string = _STRING.match(rest)
            if string:
                targets.append(string[1])
    return tuple(targets)


def resolve_extends(path: str, target: str) -> tuple[str, ...]:
    """Repository paths ``target`` (named by ``path``'s ``extends``) may be,
    in order: as written, then with ``.json`` appended. ``()`` when it is
    absolute or leaves the repository; a package name resolves to a path
    no pack holds (``node_modules`` is never read), so it stays unresolved."""
    if not target or target.startswith("/") or "\\" in target:
        return ()
    parts: list[str] = []
    for part in (PurePosixPath(path).parent / target).parts:
        if part == "..":
            if not parts:
                return ()
            parts.pop()
        elif part != ".":
            parts.append(part)
    joined = "/".join(parts)
    if not joined:
        return ()
    return (joined,) if joined.endswith(".json") else (joined, joined + ".json")


# ---------------------------------------------------------------------------
# The pack view a metric computation is handed. Plain data derived from the
# pack -- no I/O, no lazy callables, nothing that could reach outside it.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _PackView:
    pack: EvidencePack
    files: tuple[str, ...]
    """``files_read``, order-preserving deduplicated. ``files_read`` is known
    to repeat each path 2x on a default invocation (T009/T010 residue), so a
    metric that counted it raw would silently double every count."""

    source_files: tuple[str, ...]
    test_files: tuple[str, ...]
    test_excerpts: tuple[Excerpt, ...]
    tables: LanguageTables
    reliability: dict[str, ReliabilityFindings | None] = field(
        default_factory=dict, compare=False, repr=False
    )
    """Excerpt ref -> its :func:`reliability_findings`, filled on first use:
    the four reliability metrics scan each excerpt once, not four times."""


def _view(pack: EvidencePack, tables: LanguageTables) -> _PackView:
    files = _dedup(pack.files_read)
    return _PackView(
        pack=pack,
        files=files,
        source_files=tuple(path for path in files if _is_source_file(path, tables)),
        test_files=tuple(path for path in files if _is_test_file(path, tables)),
        test_excerpts=tuple(
            excerpt for excerpt in pack.excerpts if _is_test_file(excerpt.path, tables)
        ),
        tables=tables,
    )


MAX_LISTED_PATHS = 20
"""Paths a derivation lists by name (T113): the first N in order, then
``(+K more)``; the count beside the list is always the full one."""


def _listed(paths: Sequence[str], limit: int = MAX_LISTED_PATHS) -> str:
    shown = ", ".join(paths[:limit])
    return shown + (f" (+{len(paths) - limit} more)" if len(paths) > limit else "")


def _dedup(paths: Sequence[str]) -> tuple[str, ...]:
    seen: dict[str, None] = {}
    for path in paths:
        seen.setdefault(path, None)
    return tuple(seen)


# ---------------------------------------------------------------------------
# Metric computations. Each returns either (value, refs, derivation) or a
# MetricAbstention. None of them looks at truncation: compute_metrics applies
# the FR-027a rule to every whole_set metric before calling them.
# ---------------------------------------------------------------------------

_Computed = tuple[float | int, tuple[str, ...], str] | MetricAbstention


def _no_files() -> MetricAbstention:
    return MetricAbstention(
        reason=(
            "no file appears in this pack's files_read, so there is no "
            "evidence this could be computed from or cite"
        )
    )


def _test_to_source_ratio(view: _PackView) -> _Computed:
    if not view.source_files:
        return MetricAbstention(
            reason=(
                "no file in this pack classifies as source, so the ratio has "
                "a zero denominator; that is not the same as a ratio of 0. "
                + _CLASSIFIED_BY
            )
        )
    refs = tuple(sorted(set(view.source_files) | set(view.test_files)))
    return (
        len(view.test_files) / len(view.source_files),
        refs,
        f"{len(view.test_files)} test file(s) / {len(view.source_files)} "
        "source file(s), over the deduplicated files_read listed here; "
        + _CLASSIFIED_BY,
    )


def _sources_without_covering_test(view: _PackView) -> _Computed:
    if not view.source_files:
        return MetricAbstention(
            reason=(
                "no file in this pack classifies as source, so there is "
                "nothing whose test correspondence could be checked. " + _CLASSIFIED_BY
            )
        )
    _matched, unmatched = _correspondence(view.files, view.test_files, view.tables)
    return (
        len(unmatched),
        tuple(sorted(view.source_files)),
        f"{len(unmatched)} of {len(view.source_files)} source file(s) have no "
        "conventionally named test file in the same project inside this pack: "
        + (_listed(sorted(unmatched)) or "(none)")
        + "; "
        + _CLASSIFIED_BY,
    )


def _assertion_density_per_test(view: _PackView) -> _Computed:
    if not view.test_excerpts:
        return MetricAbstention(
            reason=(
                "no excerpt from a file classifying as a test is present in "
                "the evidence, so there is no test body to measure "
                "assertions in. " + _CLASSIFIED_BY
            )
        )
    tests = sum(_count_test_functions(e.text, view.tables) for e in view.test_excerpts)
    if not tests:
        return MetricAbstention(
            reason=(
                "the test-file excerpts in this pack contain no recognised "
                "test function declaration, so the density has a zero "
                "denominator; that is not the same as a density of 0"
            )
        )
    assertions = sum(_count_assertions(e.text, view.tables) for e in view.test_excerpts)
    return (
        assertions / tests,
        tuple(sorted(e.ref for e in view.test_excerpts)),
        f"{assertions} assertion(s) / {tests} test function(s), counted "
        "textually in the test-file excerpts listed here; " + _CLASSIFIED_BY,
    )


def _assertions_observed(view: _PackView) -> _Computed:
    if not view.test_excerpts:
        return MetricAbstention(
            reason=(
                "no excerpt from a file classifying as a test is present in "
                "the evidence, so there is nothing to have observed an "
                "assertion in. " + _CLASSIFIED_BY
            )
        )
    assertions = sum(_count_assertions(e.text, view.tables) for e in view.test_excerpts)
    return (
        assertions,
        tuple(sorted(e.ref for e in view.test_excerpts)),
        f"{assertions} assertion(s) counted textually in the test-file "
        "excerpts listed here; a lower bound on the repository, since it "
        "counts only what this pack contains; " + _CLASSIFIED_BY,
    )


def _redaction_hits_observed(view: _PackView) -> _Computed:
    if not view.files:
        return _no_files()
    hits = view.pack.redactions
    return (
        len(hits),
        tuple(sorted(view.files)),
        f"{len(hits)} secret redaction(s) recorded while building this pack "
        f"from the {len(view.files)} file(s) listed here; a lower bound on the "
        "repository, since only these files were read",
    )


def _redacted_file_share(view: _PackView) -> _Computed:
    if not view.files:
        return _no_files()
    hit_files = {hit.path for hit in view.pack.redactions if hit.path is not None}
    matched = tuple(sorted(path for path in view.files if path in hit_files))
    return (
        len(matched) / len(view.files),
        tuple(sorted(view.files)),
        f"{len(matched)} file(s) with at least one redaction "
        f"({', '.join(matched) or 'none'}) / {len(view.files)} file(s) read",
    )


def _declared_source_coverage(view: _PackView) -> _Computed:
    score = view.pack.coverage_score
    if score is None:
        return MetricAbstention(
            reason=(
                "this dimension sought no declared source, so there is no "
                "found/sought ratio to report; that is not the same as "
                "seeking sources and finding none, which is 0.0"
            )
        )
    if not view.files:
        return _no_files()
    return (
        score,
        tuple(sorted(view.files)),
        f"{len(view.pack.sources_found)} of "
        f"{len(view.pack.sources_sought)} declared source(s) found "
        "(the pack's own coverage_score), evidenced by the files listed here",
    )


def _excerpts_observed(view: _PackView) -> _Computed:
    if not view.pack.excerpts:
        return MetricAbstention(
            reason="this pack contains no excerpt, so none was observed"
        )
    return (
        len(view.pack.excerpts),
        tuple(sorted(e.ref for e in view.pack.excerpts)),
        f"{len(view.pack.excerpts)} excerpt(s) present in this pack, listed "
        "here; a lower bound on the repository",
    )


def _evidence_lines_observed(view: _PackView) -> _Computed:
    if not view.pack.excerpts:
        return MetricAbstention(
            reason="this pack contains no excerpt, so no line was observed"
        )
    lines = sum(_excerpt_lines(e) for e in view.pack.excerpts)
    return (
        lines,
        tuple(sorted(e.ref for e in view.pack.excerpts)),
        f"{lines} line(s) summed over the excerpts listed here, each counted "
        "as end_line - start_line + 1 (1-indexed, inclusive)",
    )


def _mean_excerpt_lines(view: _PackView) -> _Computed:
    if not view.pack.excerpts:
        return MetricAbstention(
            reason=(
                "this pack contains no excerpt, so the mean has a zero "
                "denominator; that is not the same as a mean of 0"
            )
        )
    lines = sum(_excerpt_lines(e) for e in view.pack.excerpts)
    return (
        lines / len(view.pack.excerpts),
        tuple(sorted(e.ref for e in view.pack.excerpts)),
        f"{lines} line(s) / {len(view.pack.excerpts)} excerpt(s) listed here",
    )


def _source_file_share(view: _PackView) -> _Computed:
    if not view.files:
        return _no_files()
    return (
        len(view.source_files) / len(view.files),
        tuple(sorted(view.files)),
        f"{len(view.source_files)} of {len(view.files)} deduplicated file(s) "
        "read classify as source and are listed here"
        + (
            " -- none did, so this share is 0.0 by the rule below, not because "
            "the repository has no source"
            if not view.source_files
            else ""
        )
        + "; "
        + _CLASSIFIED_BY,
    )


_SINK_METHOD = (
    "dangerous sinks are the registry's security_sinks tokens (each citing "
    "its CWE page), matched textually after the registry's comment and string "
    "delimiters are blanked (a string that interpolates keeps one mark at its "
    "start) -- no data flow is traced, so a hit is a place to "
    "look, not a proven vulnerability; test-path hits are listed, cited and "
    "tagged but not counted; a lower bound on the repository, since only "
    "these excerpts were read"
)


def _sink_hits_observed(view: _PackView) -> _Computed:
    scanned = [
        excerpt
        for excerpt in view.pack.excerpts
        if view.tables.sinks.get(PurePosixPath(excerpt.path).suffix)
        and PurePosixPath(excerpt.path).suffix in view.tables.syntax
    ]
    if not scanned:
        return MetricAbstention(
            reason=(
                "no excerpt in this pack is from a registry language with sink "
                "patterns, so no code was scanned; that is not the same as code "
                "without sinks. " + _SINK_METHOD
            )
        )
    if all(_is_test_file(excerpt.path, view.tables) for excerpt in scanned):
        return MetricAbstention(
            reason=(
                "only test files were scanned for sinks, so no production code "
                "was observed; that is not the same as production code without "
                "sinks. " + _SINK_METHOD
            )
        )
    hits: dict[tuple[str, int, str], tuple[str, str]] = {}
    for excerpt in scanned:
        for hit in sink_hits(excerpt.path, excerpt.text, view.tables):
            line = excerpt.start_line + hit.line - 1
            key = (excerpt.path, line, hit.cwe)
            hits.setdefault(key, (excerpt.ref, hit.citation_url))
    test_hits = {key for key in hits if _is_test_file(key[0], view.tables)}
    counted = len(hits) - len(test_hits)
    cited = sorted({ref for ref, _url in hits.values()}) or sorted(
        {e.ref for e in scanned}
    )
    listed = ", ".join(
        f"{path}:{line} {cwe} ({url})"
        + (" [test path]" if (path, line, cwe) in test_hits else "")
        for (path, line, cwe), (_ref, url) in sorted(hits.items())
    )
    return (
        counted,
        tuple(cited),
        f"{counted} dangerous-sink hit(s) in non-test files, from "
        f"{len(scanned)} excerpt(s): "
        + (listed or "none")
        + (
            f"; {len(test_hits)} test-path hit(s) are listed and not counted"
            if test_hits
            else ""
        )
        + "; "
        + _SINK_METHOD,
    )


def _source_files_without_covering_test_share(view: _PackView) -> _Computed:
    if not view.source_files:
        return MetricAbstention(
            reason=(
                "no file in this pack classifies as source, so the share has a "
                "zero denominator; that is not the same as a share of 0. "
                + _CLASSIFIED_BY
            )
        )
    _matched, unmatched = _correspondence(view.files, view.test_files, view.tables)
    return (
        len(unmatched) / len(view.source_files),
        tuple(sorted(view.source_files)),
        f"{len(unmatched)} of {len(view.source_files)} source file(s) have no "
        "conventionally named test file in the same project inside this pack: "
        + (_listed(sorted(unmatched)) or "(none)")
        + "; "
        + _CLASSIFIED_BY,
    )


# ---------------------------------------------------------------------------
# Role-missing metrics (T035): a source role this dimension declares is
# filled only when one of its files was actually read (core/pipeline.py), so
# a filled role is a fact. An unfilled role on a truncated pack may be a file
# the budget never read, so there it abstains instead of reporting 1. The
# metric counts the missing role (1) against an at-most-0 rule rather than
# presence against at-least-1: a threshold of 0 is never borderline (FR-036),
# so a filled role does not put its dimension at the evaluate gate.
# ---------------------------------------------------------------------------


ARCHITECTURE_HEADING = re.compile(r"^\s{0,3}#{1,6}[^\n]*\barchitecture\b", re.I | re.M)
"""A Markdown heading naming the architecture (T074, FR-068)."""


MIN_DESCRIBED_ENTRIES = 3
"""An architecture description names at least this many real repository
paths, each followed by at least :data:`MIN_DESCRIPTION_WORDS` words of
description (user sign-off 2026-10-12, G5). Two entries read as an aside
("see ``src/`` and ``tests/``"); three is the smallest map of a structure."""

MIN_DESCRIPTION_WORDS = 2

MIN_REQUIREMENT_LIST_ITEMS = 3
"""List items a heading naming requirements must head (T089 AC 12)."""


DOCUMENT_SHAPES = {
    "architecture-doc": (
        f"describes at least {MIN_DESCRIBED_ENTRIES} real repository paths "
        f"(a list item, table row or tree line naming a path that exists, "
        f"followed by at least {MIN_DESCRIPTION_WORDS} words)"
    ),
    "decision-record": (
        "has a decision structure (a Decision / Decision Outcome / Recommended "
        "Path / Recommendation / Chosen / Selected / Approved direction heading "
        "or field plus a Context, Consequences, Status, Alternatives or Options "
        "one; or a dated entry with a decision verb and a rationale)"
    ),
    "requirements-doc": (
        "has a requirement item under the declared requirement_item_patterns, "
        "or a heading naming requirements (Requirements, User Stories, "
        f"Acceptance Criteria, Use Cases) over at least "
        f"{MIN_REQUIREMENT_LIST_ITEMS} list items"
    ),
}
"""What content fills each document role (T089); the miss reason names it."""


def _document_rule(role: str) -> Callable[[_PackView], _Computed]:
    """Document role by content or declaration (T089, FR-076, DDR-0012 §3):
    0 when ``pack.documents`` records a document with the role's shape (or a
    declaration) for ``role``, 1 when every candidate document was scanned
    and none has it, an abstention when the scan was cut short. A file name
    alone never fills the role (``core/documents.py``)."""
    presence = _role_presence(role)

    def compute(view: _PackView) -> _Computed:
        if role not in view.pack.sources_sought:
            return presence(view)
        evidence = next(
            (item for item in view.pack.documents or () if item.role == role), None
        )
        if evidence is None:
            return MetricAbstention(
                reason=(
                    f"no document scan was recorded for the {role!r} role in this "
                    f"{view.pack.dimension!r} pack, so its content was never checked"
                )
            )
        if evidence.kind is not None:
            cited = "; ".join(evidence.cited)
            return (
                0,
                (evidence.path,),
                f"source role {role!r} is filled by {evidence.path} "
                f"({evidence.kind}"
                + (f": {cited}" if cited else ": named by the project")
                + "); 0 when a document "
                + DOCUMENT_SHAPES[role]
                + " or the project declares one, else 1; a file name alone "
                "never fills the role",
            )
        if evidence.bounded is not None:
            return MetricAbstention(
                reason=(
                    f"no document read for the {role!r} role "
                    f"{DOCUMENT_SHAPES[role]}, but {evidence.bounded}; that is "
                    "not the same as absent"
                )
            )
        if not view.files:
            return _no_files()
        return (
            1,
            tuple(sorted(view.files)),
            f"source role {role!r} is not filled: {evidence.scanned} documents "
            f"read; none {DOCUMENT_SHAPES[role]}, and none is declared, so the "
            "document is missing (1)",
        )

    return compute


def _role_presence(*roles: str) -> Callable[[_PackView], _Computed]:
    named = " or ".join(repr(role) for role in roles)

    def compute(view: _PackView) -> _Computed:
        sought = [role for role in roles if role in view.pack.sources_sought]
        if not sought:
            return MetricAbstention(
                reason=(
                    f"this {view.pack.dimension!r} pack does not declare the "
                    f"{named} source role, so its presence was never sought here"
                )
            )
        filled = [role for role in sought if role in view.pack.sources_found]
        if not filled and view.pack.truncated:
            return MetricAbstention(
                reason=(
                    f"no {named} role file was read, but the byte budget "
                    "truncated this pack, so the role file may be one the "
                    "budget never read; that is not the same as absent"
                )
            )
        if not view.files:
            return _no_files()
        return (
            0 if filled else 1,
            tuple(sorted(view.files)),
            f"source role {named} is "
            + (f"filled ({', '.join(filled)})" if filled else "not filled")
            + " in this pack's sources_found: 0 when a file matching the role "
            "was read, else 1 (missing); role matching is by the registry's "
            "glob patterns (list-dimensions prints them), over the files listed "
            "here",
        )

    return compute


# ---------------------------------------------------------------------------
# Acceptance-criteria trace shares (T052, FR-043). The requirement-fidelity
# pack quotes each criterion's line and the code lines naming its
# identifiers; ``pack.trace_search`` says what the search put in, so a
# criterion or trace line the byte budget dropped is noticed instead of
# reading as "untraced". These are shares over the *criteria* set, which is
# verified complete here, so they do not abstain merely because a later
# requirement-doc excerpt did not fit (they are EVIDENCE_LOCAL for that
# reason, and check their own completeness below).
# ---------------------------------------------------------------------------

REQUIREMENT_FIDELITY = "requirement-fidelity"

_TRACE_METHOD = (
    "criteria are the data rows of each tasks/TASK_GUIDE_Txxx.md 'Acceptance "
    "Criteria' table (id Txxx#row) and each FR-xxx defined in a requirements "
    "document; a criterion is traced when one of its keys (its task ID or an "
    "FR-xxx ID in its row) appears as a whole word in a quoted line of a code "
    "file; " + _CLASSIFIED_BY + "; documents never count"
)


def trace_key_pattern(keys: Iterable[str]) -> re.Pattern[str]:
    """Whole-word alternation over trace keys; ``-`` counts as a word char, so
    ``FR-027`` does not match inside ``FR-027a``. Shared with the dimension so
    both sides match identically."""
    ordered = sorted(set(keys), key=lambda key: (-len(key), key))
    return re.compile(
        r"(?<![\w-])(?:" + "|".join(re.escape(k) for k in ordered) + r")(?![\w-])"
    )


def code_kind(path: str, tables: LanguageTables) -> str | None:
    """``"test"``, ``"source"`` or ``None`` (not code), by path convention."""
    if _is_test_file(path, tables):
        return "test"
    if _is_source_file(path, tables):
        return "source"
    return None


def _ac_traced_share(kind: str) -> Callable[[_PackView], _Computed]:
    target = "code" if kind == "source" else "a test"

    def compute(view: _PackView) -> _Computed:
        search = view.pack.trace_search
        if search is None:
            if view.pack.dimension != REQUIREMENT_FIDELITY:
                why = (
                    f"only the requirement-fidelity pack extracts acceptance "
                    f"criteria, and this is the {view.pack.dimension!r} pack"
                )
            else:
                why = (
                    "no acceptance-criteria search was run for this pack: only "
                    "kit-aware mode reads task guides and requirements documents "
                    f"as ground truth (this pack is {view.pack.mode}), and "
                    "criteria are never inferred, so there is no criterion to trace"
                )
            return MetricAbstention(reason=why)
        if search.incomplete:
            return MetricAbstention(
                reason="the acceptance-criteria search is incomplete: "
                + search.incomplete
            )
        if not search.criteria:
            return MetricAbstention(
                reason=(
                    "no acceptance criterion was found: no task guide has an "
                    "'Acceptance Criteria' table row and no requirements document "
                    "defines an FR-xxx ID"
                )
            )
        if kind == "source":
            traced, listed, omitted = (
                search.traced_to_code,
                search.untraced_code,
                search.untraced_code_omitted,
            )
        else:
            traced, listed, omitted = (
                search.traced_to_test,
                search.untraced_test,
                search.untraced_test_omitted,
            )
        present = {e.ref for e in view.pack.excerpts}
        lines = [
            e for e in view.pack.excerpts if code_kind(e.path, view.tables) is not None
        ]
        missing = [c.ref for c in listed if c.ref not in present]
        missing_lines = max(0, search.trace_lines - len(lines))
        if missing or missing_lines:
            dropped = len(missing) + missing_lines
            return MetricAbstention(
                reason=(
                    f"{dropped} cited criterion or trace line(s) the search found "
                    "are not in this pack (the byte budget dropped them), so the "
                    "share could not be shown with its evidence"
                ),
                omitted_lower_bound=dropped,
            )
        refs = {e.ref for e in lines if code_kind(e.path, view.tables) == kind}
        refs |= {c.ref for c in listed}
        untraced = search.criteria - traced
        return (
            traced / search.criteria,
            tuple(sorted(refs)),
            f"{traced} of {search.criteria} acceptance criteria are traced to "
            f"{target} (searched {search.files_searched} code file(s)); "
            f"{untraced} untraced: "
            + (", ".join(c.id for c in listed[:15]) or "none")
            + (f", and {untraced - min(15, len(listed))} more" if untraced > 15 else "")
            + f" (the first {len(listed)} are cited, {omitted} counted only); "
            + f"{search.trace_lines} trace line(s) quoted, "
            + f"{search.trace_lines_omitted} more found and counted only; "
            + _TRACE_METHOD,
        )

    return compute


# ---------------------------------------------------------------------------
# Churn hotspot share (T052): the ranking is local git history, which no
# file excerpt can carry, so the blast-radius dimension records it in
# ``pack.reach``; the share is over the changed files the pack read.
# ---------------------------------------------------------------------------


def _changed_files_in_churn_hotspots_share(view: _PackView) -> _Computed:
    reach = view.pack.reach
    if reach is None or view.pack.dimension != BLAST_RADIUS:
        return MetricAbstention(
            reason=(
                "a churn-hotspot share needs the changed files of a narrow scope "
                "and a repository-wide ranking; only the blast-radius pack at "
                "changes, worktree or task scope gathers them (at project scope "
                "every file is in scope, so the share would be 10% by "
                f"construction), and this is the {view.pack.dimension!r} pack "
                f"at {view.pack.scope!r} scope"
            )
        )
    if reach.churn_unavailable:
        return MetricAbstention(reason=reach.churn_unavailable)
    allowed = set(view.pack.files_read)
    changed = [path for path in reach.changed if path in allowed]
    if not changed:
        return MetricAbstention(
            reason="no changed file of this scope could be read, so there is no "
            "changed file to place in the churn ranking"
        )
    hot = [path for path in changed if path in reach.hotspots_changed]
    return (
        len(hot) / len(changed),
        tuple(sorted(changed)),
        f"{len(hot)} of {len(changed)} changed file(s) are in the repository's "
        f"top 10% by churn: " + (", ".join(hot) or "none") + f". Churn = number "
        f"of the last {reach.commits} local commits touching a file; the top 10% "
        f"is the first {reach.hotspot_count} of the {reach.ranked_files} tracked "
        "file(s) with any commit in that window, ordered by churn then path, "
        "whatever the scope (Tornhill, hotspots by change frequency)",
    )


_SWEEP_CAPPED = (
    "the reference sweep stopped at its file ceiling before reaching every "
    "repository file, so files importing a changed file may never have been "
    "opened; the fan-in would be a lower bound, not the value"
)


# ---------------------------------------------------------------------------
# Structure metrics (T033): registry-driven tokens over the pack's excerpts,
# never over a file the pack did not quote (core/tokens.py).
# ---------------------------------------------------------------------------

CCN_THRESHOLD = 10
"""``functions_over_ccn_10_share`` counts functions with CCN above this."""

BLAST_RADIUS = "blast-radius"

_CCN_METHOD = (
    "approximate CCN (lizard-style), McCabe 1976: 1 + the registry's branch "
    "keywords per function, counted after the registry's comment and string "
    "delimiters are blanked; a function starts at a registry function-start "
    "token and ends before the next non-blank line indented no deeper, and a "
    "function whose excerpt ends first counts only the lines quoted; only "
    "source-file excerpts of registry languages are read"
)

_IMPORT_METHOD = (
    "import statements are the registry's import tokens, found textually in "
    "excerpts of registry-language files; a statement names a file when it "
    "contains the file's stem (a package's __init__-style file: its "
    "directory) as a whole word -- a textual match, not a resolved import"
)


def _observed_functions(view: _PackView) -> list[tuple[Excerpt, int, int]]:
    """``(excerpt, absolute line, ccn)`` per function, one per start line."""
    best: dict[tuple[str, int], tuple[Excerpt, int, int]] = {}
    for excerpt in view.pack.excerpts:
        syntax = view.tables.syntax.get(PurePosixPath(excerpt.path).suffix)
        if syntax is None or not _is_source_file(excerpt.path, view.tables):
            continue
        for function in approximate_ccn(excerpt.text, syntax):
            line = excerpt.start_line + function.line - 1
            key = (excerpt.path, line)
            if key not in best or function.ccn > best[key][2]:
                best[key] = (excerpt, line, function.ccn)
    return [best[key] for key in sorted(best)]


def _no_functions() -> MetricAbstention:
    return MetricAbstention(
        reason=(
            "no source-file excerpt in this pack contains a function start the "
            "registry recognises, so no function was observed; that is not the "
            "same as functions of low complexity. " + _CCN_METHOD
        )
    )


def _functions_over_ccn_10_share(view: _PackView) -> _Computed:
    functions = _observed_functions(view)
    if not functions:
        return _no_functions()
    over = [(e.path, line, ccn) for e, line, ccn in functions if ccn > CCN_THRESHOLD]
    return (
        len(over) / len(functions),
        tuple(sorted({e.ref for e, _line, _ccn in functions})),
        f"{len(over)} of {len(functions)} observed function(s) have approximate "
        f"CCN > {CCN_THRESHOLD}: "
        + (", ".join(f"{path}:{line} ({ccn})" for path, line, ccn in over) or "none")
        + "; "
        + _CCN_METHOD,
    )


def _max_function_ccn(view: _PackView) -> _Computed:
    functions = _observed_functions(view)
    if not functions:
        return _no_functions()
    top = max(ccn for _e, _line, ccn in functions)
    at = [(e, line) for e, line, ccn in functions if ccn == top]
    return (
        top,
        tuple(sorted({e.ref for e, _line in at})),
        f"the highest approximate CCN among {len(functions)} observed "
        f"function(s) is {top}, at "
        + ", ".join(f"{e.path}:{line}" for e, line in at)
        + "; a lower bound on the repository; "
        + _CCN_METHOD,
    )


def _statements(
    view: _PackView, *, source_only: bool
) -> list[tuple[Excerpt, str]]:
    found = []
    for excerpt in view.pack.excerpts:
        syntax = view.tables.syntax.get(PurePosixPath(excerpt.path).suffix)
        if syntax is None:
            continue
        if source_only and not _is_source_file(excerpt.path, view.tables):
            continue
        for _line, text in import_statements(excerpt.text, syntax):
            found.append((excerpt, text))
    return found


def _no_imports(what: str) -> MetricAbstention:
    return MetricAbstention(
        reason=(
            f"no import statement was found in this pack's {what} excerpts, so "
            "there is no import graph to measure; that is not the same as a "
            "graph without edges. " + _IMPORT_METHOD
        )
    )


def _names_pattern(names: Sequence[str]) -> re.Pattern[str]:
    ordered = sorted(set(names), key=lambda name: (-len(name), name))
    return re.compile(r"\b(?:" + "|".join(re.escape(n) for n in ordered) + r")\b")


def _file_name(path: str) -> str:
    pure = PurePosixPath(path)
    return pure.parent.name if pure.stem.startswith("__") else pure.stem


def _max_fan_in_changed(view: _PackView) -> _Computed:
    if view.pack.dimension != BLAST_RADIUS:
        return MetricAbstention(
            reason=(
                "only the blast-radius pack says which files changed: its "
                "reference search quotes only lines naming in-scope files, and "
                f"this is the {view.pack.dimension!r} pack"
            )
        )
    reach = view.pack.reach
    if reach is not None and reach.sweep_capped:
        return MetricAbstention(reason=_SWEEP_CAPPED)
    statements = _statements(view, source_only=False)
    if not statements:
        return _no_imports("code-file")
    fan_in: dict[str, list[Excerpt]] = {}
    targets = reach.changed if reach is not None and reach.changed else view.files
    for target in targets:
        name = _file_name(target)
        if PurePosixPath(target).suffix not in view.tables.syntax or not name:
            continue
        pattern = _names_pattern([name])
        importers: dict[str, Excerpt] = {}
        for excerpt, text in statements:
            if excerpt.path != target and pattern.search(text):
                importers.setdefault(excerpt.path, excerpt)
        if importers:
            fan_in[target] = list(importers.values())
    if not fan_in:
        return (
            0,
            tuple(sorted({e.ref for e, _text in statements})),
            f"none of the {len(statements)} import statement(s) quoted here "
            "names a file read by this pack; " + _IMPORT_METHOD,
        )
    top = max(len(importers) for importers in fan_in.values())
    targets = sorted(path for path, found in fan_in.items() if len(found) == top)
    refs = {e.ref for path in targets for e in fan_in[path]} | set(targets)
    return (
        top,
        tuple(sorted(refs)),
        f"{', '.join(targets)} is named by import statements in {top} distinct "
        "file(s); the files counted are those named by the import statements "
        "this pack's reference search quoted, which quotes only lines naming "
        "in-scope (changed) files; a lower bound, since the search is capped; "
        + _IMPORT_METHOD,
    )


def _top_level_import_cycles(view: _PackView) -> _Computed:
    statements = _statements(view, source_only=True)
    if not statements:
        return _no_imports("source-file")
    files = sorted(
        {
            e.path
            for e in view.pack.excerpts
            if _is_source_file(e.path, view.tables)
            and PurePosixPath(e.path).suffix in view.tables.syntax
        }
    )
    # T113: the root is shared by the application source only, so a root
    # tooling/config file (``commitlint.config.js``, purpose class of
    # ``core.batches``) cannot collapse every module into one; files outside
    # that root are not modules and their statements are not edges.
    rank = view.tables.purpose_rank
    application = [p for p in files if rank is None or rank(p) <= 1] or files
    prefix = _common_directory(application)
    files = [
        path for path in files if PurePosixPath(path).parts[: len(prefix)] == prefix
    ]
    statements = [
        (excerpt, text)
        for excerpt, text in statements
        if PurePosixPath(excerpt.path).parts[: len(prefix)] == prefix
    ]

    def module_of(path: str) -> str:
        parts = PurePosixPath(path).parts[len(prefix) :]
        return parts[0] if len(parts) > 1 else PurePosixPath(path).stem

    modules = sorted({module_of(path) for path in files})
    patterns = {module: _names_pattern([module]) for module in modules}
    edges: dict[str, set[str]] = {module: set() for module in modules}
    edge_refs: dict[tuple[str, str], set[str]] = {}
    for excerpt, text in statements:
        source = module_of(excerpt.path)
        for module in modules:
            if module != source and patterns[module].search(text):
                edges[source].add(module)
                edge_refs.setdefault((source, module), set()).add(excerpt.ref)

    cycles = _cycles(edges)
    refs = {
        ref
        for cycle in cycles
        for (a, b), found in edge_refs.items()
        if a in cycle and b in cycle
        for ref in found
    } or {e.ref for e, _text in statements}
    where = "/".join(prefix) or "the repository root"
    return (
        len(cycles),
        tuple(sorted(refs)),
        f"{len(cycles)} import cycle(s) among {len(modules)} top-level module(s) "
        f"under {where}: "
        + ("; ".join(" <-> ".join(cycle) for cycle in cycles) or "none")
        + f". A top-level module is the first directory under the deepest "
        f"directory shared by the application source file(s) quoted here "
        f"({len(files)} under it; a file directly there is its own module; "
        "tooling, config and generated files neither move it nor count); "
        "a cycle is a set of two or more "
        "modules each reaching the others, counted once; only the import "
        "statements quoted in this pack are seen; " + _IMPORT_METHOD,
    )


LAYER_RANK = {"data": 0, "service": 1, "api": 2}
"""Lower to higher (T074, DDR-0011); ``shared`` has no rank and never counts."""

MIN_CLASSIFIED_SHARE = 0.50
"""Below this share of non-shared source files in a layer, the layer rule
abstains (user, DDR-0011)."""


MAX_LAYER_EXAMPLES = 5
"""Violating import statements quoted by file:line in the derivation."""


def _source_statements(view: _PackView):
    """The quoted source files, and each of their import statements as
    ``(excerpt, line, text)``: the edges both layer metrics walk."""
    files = sorted(
        {
            e.path
            for e in view.pack.excerpts
            if _is_source_file(e.path, view.tables)
            and PurePosixPath(e.path).suffix in view.tables.syntax
        }
    )
    statements = []
    for excerpt in view.pack.excerpts:
        syntax = view.tables.syntax.get(PurePosixPath(excerpt.path).suffix)
        if syntax is None or excerpt.path not in files:
            continue
        for line, text in import_statements(excerpt.text, syntax):
            statements.append((excerpt, excerpt.start_line + line - 1, text))
    return files, statements


_ROOT = "the repository root"


def _unit_of(path: str, homes: Sequence[str]) -> str:
    """The deepest of ``homes`` (manifest directories, ``""`` = the root) at or
    above ``path``; the root when none is."""
    return max(
        (home for home in homes if not home or path.startswith(home + "/")),
        key=len,
        default="",
    )


def _backend_units(
    manifests: Sequence[str], behaviour: Mapping[str, str]
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """``(manifest directories, backend units)`` (T093): a backend unit is the
    deepest manifest directory at or above an api file (by behaviour). No api
    file, no unit: the share then stays over the whole repository."""
    parents = {str(PurePosixPath(manifest).parent) for manifest in manifests}
    homes = tuple(sorted("" if d == "." else d for d in parents))
    units = sorted(
        {_unit_of(path, homes) for path, layer in behaviour.items() if layer == "api"}
    )
    return homes, tuple(units)


def _in_backend_unit(path: str, homes: Sequence[str], units: Sequence[str]) -> bool:
    """Whether ``path`` counts in the classified share: no unit counts every
    file; else the file's own (deepest) manifest directory must be a unit."""
    return not units or _unit_of(path, homes) in units


def _import_unit(path: str, homes: Sequence[str]) -> str:
    """The manifest unit an import's target must share with its importer
    (T093, AC 12); with no manifests, the whole repository."""
    return _unit_of(path, homes)


def _is_violation_end(path: str, behaviour: Mapping[str, str]) -> bool:
    """Whether ``path`` may be either end of a violation (T093, AC 11): only
    a layer from behaviour evidence; a hint-only layer never decides one."""
    return path in behaviour


def _layer_direction_violations(view: _PackView) -> _Computed:
    files, statements = _source_statements(view)
    if not statements:
        return _no_imports("source-file")
    layer_of = view.tables.layer_of or (lambda _path: None)
    hints = {path: layer_of(path) for path in files}
    behaviour, cited, linked, _graph = _behaviour_layers(view, files, statements)
    layers = {path: behaviour.get(path) or hints[path] for path in files}
    considered = [path for path in files if layers[path] != "shared"]
    classified = {p: layers[p] for p in considered if layers[p] in LAYER_RANK}
    homes, units = _backend_units(view.tables.package_manifests, behaviour)
    counted = [p for p in considered if _in_backend_unit(p, homes, units)]
    outside = [p for p in considered if p not in set(counted)]
    in_share = [p for p in counted if p in classified]
    by_behaviour = sum(1 for p in in_share if p in behaviour)
    disagreements = [
        f"{path} (hint {hints[path]}, behaviour {behaviour[path]} at {cited[path]})"
        for path in files
        if path in behaviour and hints[path] and hints[path] != behaviour[path]
    ]
    where = (
        "in backend unit(s) (" + ", ".join(u or _ROOT for u in units) + ")"
        if units
        else "quoted here"
    )
    share = (
        f"{len(in_share)} of {len(counted)} non-shared source file(s) {where} "
        f"classify into a layer (api, service, data): {by_behaviour} by "
        "behaviour ("
        + _behaviour_counts({p: behaviour[p] for p in in_share if p in behaviour})
        + f"), {len(in_share) - by_behaviour} by the layer_paths hints only"
    )
    if outside:
        groups = sorted({_unit_of(p, homes) or _ROOT for p in outside})
        share += (
            f"; {len(outside)} non-shared source file(s) outside backend units ("
            + ", ".join(groups[:MAX_LAYER_EXAMPLES])
            + (", ..." if len(groups) > MAX_LAYER_EXAMPLES else "")
            + ") are not counted in this share: a backend unit is the deepest "
            "directory holding a package manifest at or above a file that "
            "registers a route, and a file belongs to the deepest such directory "
            "above it; violations are not limited to backend units"
        )
    disagreed = (
        f"; {len(disagreements)} disagreement(s) with the layer_paths hints, "
        "behaviour wins"
        + (": " if disagreements else "")
        + "; ".join(disagreements[:MAX_LAYER_EXAMPLES])
    )
    if linked:
        disagreed += (
            f"; {len(linked)} prefix edge(s) from dynamic imports with a literal "
            "directory prefix, each linking every source file directly in that "
            "directory: " + "; ".join(linked[:MAX_LAYER_EXAMPLES])
        )
    if not counted or len(in_share) / len(counted) < MIN_CLASSIFIED_SHARE:
        if not any(layer in ("api", "data") for layer in behaviour.values()):
            return MetricAbstention(
                reason=(
                    "framework_not_recognized: no source file quoted here "
                    "registers a route or calls a recognised DB/ORM API (the "
                    "registry's route_tokens and data_tokens), and the "
                    f"layer_paths hints classify {len(classified)} of "
                    f"{len(considered)} non-shared source file(s), below the "
                    f"declared minimum share of {MIN_CLASSIFIED_SHARE:.2f}; "
                    + view.tables.layer_paths_note
                )
            )
        return MetricAbstention(
            reason=(
                f"{share}, below the declared minimum share of "
                f"{MIN_CLASSIFIED_SHARE:.2f}, so the layer direction of this "
                "code is not measurable"
                + ("" if "api" in behaviour.values() else
                   "; no route registration was found here")
                + disagreed + "; " + view.tables.layer_paths_note
            )
        )
    # Only files classified by behaviour are violation ends (T093, AC 11).
    ends = {p: lay for p, lay in classified.items() if _is_violation_end(p, behaviour)}
    # A stem shared by files of different layers names no layer: skipped.
    # A target resolves only within the importer's own unit (T093, AC 12).
    by_name: dict[tuple[str, str], set[str]] = {}
    for path, layer in ends.items():
        key = (_import_unit(path, homes), _file_name(path))
        by_name.setdefault(key, set()).add(layer)
    targets = {
        key: found.pop() for key, found in by_name.items() if len(found) == 1 and key[1]
    }
    patterns = {key: _names_pattern([key[1]]) for key in targets}
    violations: list[tuple[Excerpt, int, str, str]] = []
    for excerpt, line, text in statements:
        source = ends.get(excerpt.path)
        if source is None:
            continue
        unit = _import_unit(excerpt.path, homes)
        higher = sorted(
            {
                target
                for (in_unit, name), target in targets.items()
                if in_unit == unit
                and LAYER_RANK[target] > LAYER_RANK[source]
                and name != _file_name(excerpt.path)
                and patterns[(in_unit, name)].search(text)
            },
            key=LAYER_RANK.get,
        )
        if higher:
            violations.append((excerpt, line, source, higher[-1]))
    refs = {e.ref for e, *_rest in violations} or {e.ref for e, _l, _t in statements}
    examples = "; ".join(
        f"{e.path}:{line} ({source} -> {target})"
        for e, line, source, target in violations[:MAX_LAYER_EXAMPLES]
    )
    return (
        len(violations),
        tuple(sorted(refs)),
        f"{len(violations)} import statement(s) from a lower to a higher layer "
        "(data -> service, service -> api, data -> api)"
        + (f", e.g. {examples}" if examples else "")
        + f". {share} ({view.tables.layer_paths_note}){disagreed}. "
        + _BEHAVIOUR_METHOD
        + "; a violation needs a layer from behaviour at both ends: the "
        f"{len(classified) - len(ends)} file(s) classified by the layer_paths "
        "hints only count in the share but are never a violation end; an "
        "import's target is matched only among files of the importer's own "
        "manifest unit (the deepest directory holding a package manifest "
        "above it); "
        "shared and unclassified files "
        "never count, and a file "
        "stem shared by files of different layers names none; only the import "
        "statements quoted in this pack are seen; " + _IMPORT_METHOD,
    )


MAX_REQUEST_PATHS_LISTED = 20
"""Routes quoted in the ``request_paths`` derivation (T090); the rest are
counted and the cap is stated, since every cited hop adds payload."""


def _request_paths(view: _PackView) -> _Computed:
    """Per route, the shortest in-repo import path from its file to a file
    that calls a DB/ORM API (T090). Reported, never scored: no rating rule
    reads it. Walks the edges T088's behaviour layers already built."""
    files, statements = _source_statements(view)
    behaviour, _cited, linked, graph = _behaviour_layers(view, files, statements)
    if graph is None:
        return MetricAbstention(
            reason="no behaviour evidence is registered for this language set, so "
            "no route can be recognised"
        )
    found, edges, lines = graph
    api = {}
    for path in sorted(found):
        for excerpt, ev in found[path]:
            if ev.routes:
                api.setdefault(path, []).append((excerpt, ev))
    if not api:
        return MetricAbstention(
            reason="no source file quoted here registers a route (the registry's "
            "route_tokens), so there is no request path to report"
        )

    def boundary(path: str):
        for excerpt, ev in found.get(path, ()):
            if ev.data_line:
                return excerpt, ev.data_line
        return None

    def hops(start: str) -> list[str] | None:
        previous = {start: None}
        queue = [start]
        for node in queue:
            if node != start and boundary(node):
                chain = [node]
                while previous[chain[-1]] is not None:
                    chain.append(previous[chain[-1]])
                return chain[::-1]
            for target in sorted(edges.get(node, ())):
                if target not in previous:
                    previous[target] = node
                    queue.append(target)
        return None

    routes = []
    for path, items in api.items():
        chain = [path] if boundary(path) else hops(path)
        for excerpt, ev in items:
            for route in ev.routes:
                routes.append((path, excerpt.start_line + route.line - 1, route, chain))
    direct = sum(1 for _p, _l, _r, chain in routes if chain and len(chain) == 1)
    via = sum(1 for _p, _l, _r, chain in routes if chain and len(chain) > 1)
    none = len(routes) - direct - via
    ranked = sorted(
        routes,
        key=lambda r: (
            0 if r[3] and len(r[3]) > 1 else 1 if r[3] else 2,
            r[0],
            r[1],
        ),
    )
    shown = ranked[:MAX_REQUEST_PATHS_LISTED]
    refs: set[str] = set()
    out = []
    for path, line, route, chain in shown:
        where = route.path or "(path is not a literal)"
        head = f"{route.method} {where}: {path}:{line}"
        if chain is None:
            out.append(head + " -> reaches no file that calls a DB/ORM API")
            refs.update(e.ref for e, _ev in api[path])
            continue
        parts = [head]
        for node, nxt in zip(chain, chain[1:], strict=False):
            if node != path:
                parts.append(f"{node}:{lines[(node, nxt)]}")
        hit = boundary(chain[-1])
        excerpt, at = hit
        call = excerpt.text.split("\n")[at - 1].strip()[:60]
        end = excerpt.start_line + at - 1
        parts.append(
            f"{chain[-1]}:{end} ({call})" if chain[-1] != path
            else f"DB/ORM call at line {end} ({call})"
        )
        out.append(" -> ".join(parts))
        for node in chain:
            refs.update(e.ref for e, _ev in found.get(node, ()))
    cap = (
        f"; the first {MAX_REQUEST_PATHS_LISTED} of {len(routes)} routes are "
        "listed (cap), ordered by paths through modules, then direct, then none"
        if len(routes) > MAX_REQUEST_PATHS_LISTED
        else ""
    )
    summary = (
        f"{len(routes)} route(s) found in {len(api)} file(s): {direct} reach a "
        f"DB/ORM call in their own file, {via} through at least one other "
        f"in-repo module, {none} reach none by the import edges seen{cap}. "
        "Reported only: no rule, rating or overall reads it; the database "
        "belongs to another service (user). "
        + (
            f"{len(linked)} dynamic import(s) with a literal directory prefix "
            "link every file directly in that directory, so a path through one "
            "names the first such file, not necessarily the one called. "
            if linked
            else ""
        )
        + _BEHAVIOUR_METHOD
        + "; only the import statements quoted in this pack are seen; "
        + _IMPORT_METHOD
    )
    return (
        len(routes),
        tuple(sorted(refs or {e.ref for _p, items in api.items() for e, _v in items})),
        # The summary is the last line: a whole-file note is appended to the end.
        "\n".join([*out, summary]),
    )


_BEHAVIOUR_METHOD = (
    "A file's layer is what its code does (DDR-0012): api registers a route "
    "(route_tokens) or is the module of a dotted route handler; data calls a "
    "data_tokens DB/ORM method on a client or model name it imports from a "
    "DB/ORM package or an in-repo file binding one; service is a file on an "
    "import path from an api file to a data file; a file with route and DB "
    "calls is api, and its DB access is never scored; a file the behaviour "
    "does not classify takes its layer_paths hint"
)


def _behaviour_counts(behaviour: Mapping[str, str]) -> str:
    return ", ".join(
        f"{sum(1 for v in behaviour.values() if v == layer)} {layer}"
        for layer in ("api", "service", "data")
    )


def _behaviour_layers(
    view: _PackView, files: Sequence[str], statements
) -> tuple[dict[str, str], dict[str, str]]:
    """Behaviour layers over the layer rule's own import edges (T088): an
    import statement names a file when it holds the file's stem (an ``index``
    file: also its directory) and no other file quoted here has that name."""
    evidence_of = view.tables.layer_evidence
    if evidence_of is None:
        return {}, {}, [], None
    texts: dict[str, list[Excerpt]] = {}
    for excerpt in view.pack.excerpts:
        if excerpt.path in files:
            texts.setdefault(excerpt.path, []).append(excerpt)
    unique = _name_owners(files)
    patterns = {name: _names_pattern([name]) for name in unique}
    targets: dict[tuple[str, int], set[str]] = {}
    for excerpt, line, text in statements:
        targets[(excerpt.path, line)] = {
            unique[name]
            for name in unique
            if unique[name] != excerpt.path and patterns[name].search(text)
        }

    def observe(imported: Mapping[str, frozenset[str]], previous=None, before=None):
        found = {}
        for path, excerpts in texts.items():
            if previous is not None and imported.get(path) == before.get(path):
                found[path] = previous[path]
                continue
            for excerpt in excerpts:
                ev = evidence_of(path, excerpt.text, imported.get(path, frozenset()))
                found.setdefault(path, []).append((excerpt, ev))
        return found

    def bound(found) -> dict[str, frozenset[str]]:
        imported: dict[str, set[str]] = {}
        for path, items in found.items():
            for excerpt, ev in items:
                for line, names in ev.imports:
                    at = (path, excerpt.start_line + line - 1)
                    for target in targets.get(at, ()):
                        for _e, tev in found.get(target, ()):
                            exported = "exports" in tev.defines
                            take = names if exported else names & tev.defines
                            imported.setdefault(path, set()).update(take)
        return {path: frozenset(names) for path, names in imported.items()}

    found = observe({})
    linked: list[str] = []
    for path, items in found.items():
        for excerpt, ev in items:
            for line, prefix in ev.prefixes:
                at = excerpt.start_line + line - 1
                loaded = _prefix_targets(path, prefix, files)
                if loaded:
                    targets.setdefault((path, at), set()).update(loaded)
                    linked.append(
                        f"{path}:{at} -> {prefix!r} ({len(loaded)} file(s))"
                    )
    imported: dict[str, frozenset[str]] = {}
    for _round in range(3):
        again = bound(found)
        if again == imported:
            break
        found = observe(again, found, imported)
        imported = again
    behaviour: dict[str, str] = {}
    cited: dict[str, str] = {}
    handled: dict[str, str] = {}
    for path, items in found.items():
        for excerpt, ev in items:
            if ev.layer is None or behaviour.get(path) == "api":
                continue
            if ev.layer == "api" or path not in behaviour:
                behaviour[path] = ev.layer
                cited[path] = f"{path}:{excerpt.start_line + ev.line - 1}"
            if ev.layer == "api":
                for line, names in ev.imports:
                    at = (path, excerpt.start_line + line - 1)
                    if names & ev.handlers:
                        for target in targets.get(at, ()):
                            handled.setdefault(target, cited[path])
    for target, at in handled.items():
        if behaviour.get(target) != "api":
            behaviour[target] = "api"
            cited[target] = f"route handler module, routed at {at}"
    edges: dict[str, set[str]] = {}
    lines: dict[tuple[str, str], int] = {}
    for (path, line), found_targets in targets.items():
        for target in found_targets:
            edges.setdefault(path, set()).add(target)
            lines.setdefault((path, target), line)
    reverse: dict[str, set[str]] = {}
    for path, found_targets in edges.items():
        for target in found_targets:
            reverse.setdefault(target, set()).add(path)

    def reach(start: str, graph) -> set[str]:
        seen: set[str] = set()
        roots = [path for path, layer in behaviour.items() if layer == start]
        queue = [node for root in roots for node in graph.get(root, ())]
        while queue:
            node = queue.pop()
            if node in seen or node in behaviour:
                continue
            seen.add(node)
            queue.extend(graph.get(node, ()))
        return seen

    below = reach("data", reverse)
    for path in sorted(reach("api", edges) & below):
        behaviour[path] = "service"
        toward = sorted(
            lines[(path, t)]
            for t in edges.get(path, ())
            if t in below or behaviour.get(t) == "data"
        )
        cited[path] = f"{path}:{toward[0]}" if toward else path
    return behaviour, cited, linked, (found, edges, lines)


def _name_owners(files: Sequence[str]) -> dict[str, str]:
    """The architecture resolver's names (T088): a file is named by its stem
    (an ``index`` file: also by its directory), and a name two files share
    names neither."""
    owners: dict[str, set[str]] = {}
    for path in files:
        pure = PurePosixPath(path)
        barrel = {pure.parent.name} if pure.stem == "index" else set()
        for name in {_file_name(path)} | barrel:
            if name:
                owners.setdefault(name, set()).add(path)
    return {name: found.pop() for name, found in owners.items() if len(found) == 1}


_LITERAL = re.compile(r"(['\"`])((?:(?!\1)[^\n])*)\1")
_DOTTED = re.compile(r"[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*")


def _named_modules(text: str, suffixes: frozenset[str]) -> set[str]:
    """The module names one import statement names (T114). A statement with
    a string literal names its path specifiers' last segments, a registry
    source suffix dropped (``'../dtos'``, ``'./user.controller'``,
    ``'./util.js'``); one without names the last segment of each dotted name
    (``from src.core.config import settings`` -> ``config``, ``settings``)."""
    literals = [value for _quote, value in _LITERAL.findall(text)]
    if literals:
        names = set()
        for value in literals:
            if "${" in value or not value:
                continue
            last = value.rstrip("/").rsplit("/", 1)[-1]
            suffix = PurePosixPath(last).suffix
            names.add(last[: -len(suffix)] if suffix in suffixes else last)
        return names
    return {token.rsplit(".", 1)[-1] for token in _DOTTED.findall(text)}


def import_fan_in(
    files: Sequence[str],
    statements: Iterable[tuple[str, str]],
    prefixes: Iterable[tuple[str, str]] = (),
    suffixes: Iterable[str] = (),
) -> dict[str, frozenset[str]]:
    """The importing files of each of ``files`` (T114), over the names of the
    architecture resolver (:func:`_name_owners`: a file's stem, an index
    file's directory, a name two files share names neither) and its literal
    dynamic-import prefix edges (``(path, prefix)``: every file directly in
    the directory). A statement (``(path, text)``) names a file only by the
    *last* segment of a specifier or dotted module name
    (:func:`_named_modules`), not by any whole word in it: over a whole
    repository a directory segment (``'./auth/guards/x'``) or a hyphenated
    piece (``base-mongodb-service``) would otherwise make a file look
    imported by every statement that passes through its name."""
    unique = _name_owners(files)
    known = frozenset(suffixes)
    importers: dict[str, set[str]] = {}
    for path, text in statements:
        for name in _named_modules(text, known):
            target = unique.get(name)
            if target is not None and target != path:
                importers.setdefault(target, set()).add(path)
    for path, prefix in prefixes:
        for target in _prefix_targets(path, prefix, files):
            importers.setdefault(target, set()).add(path)
    return {target: frozenset(found) for target, found in importers.items()}


HIGH_REACH_PERCENT = 10
"""High-reach files are the top 10 % of source files by fan-in (T114)."""
MIN_HIGH_REACH_FAN_IN = 3
"""... and are imported by at least this many in-repo files (T114)."""


def high_reach_files(fan_in: Mapping[str, int], source_count: int) -> list[str]:
    """The top :data:`HIGH_REACH_PERCENT` % of ``source_count`` source files by
    fan-in, at least one, ties at the cut included, each with a fan-in of at
    least :data:`MIN_HIGH_REACH_FAN_IN`; highest first, then by path."""
    ranked = sorted(
        (path for path, count in fan_in.items() if count >= MIN_HIGH_REACH_FAN_IN),
        key=lambda path: (-fan_in[path], path),
    )
    if not ranked:
        return []
    top = max(1, -(-source_count * HIGH_REACH_PERCENT // 100))
    cut = fan_in[ranked[min(top, len(ranked)) - 1]]
    return [path for path in ranked if fan_in[path] >= cut]


def _prefix_targets(path: str, prefix: str, files: Sequence[str]) -> set[str]:
    """The in-scope files directly in the directory a literal dynamic-import
    prefix names (T088 AC 11), non-recursive: ``./controllers/`` relative to
    ``path``'s directory, or dotted ``pkg.mod.`` as a directory ``pkg/mod``
    at any depth."""
    if prefix.startswith("."):
        parts: list[str] = []
        for part in (*PurePosixPath(path).parent.parts, *prefix.split("/")):
            if part == "..":
                if parts:
                    parts.pop()
            elif part not in (".", ""):
                parts.append(part)
        base = "/".join(parts)
        return {f for f in files if f != path and _parent(f) == base}
    folder = prefix.rstrip(".").replace(".", "/")
    return {
        f
        for f in files
        if f != path
        and (_parent(f) == folder or _parent(f).endswith("/" + folder))
    }


def _parent(path: str) -> str:
    parent = str(PurePosixPath(path).parent)
    return "" if parent == "." else parent


def _common_directory(files: Sequence[str]) -> tuple[str, ...]:
    parents = [PurePosixPath(path).parent.parts for path in files]
    common: list[str] = []
    for parts in zip(*parents, strict=False):
        if len(set(parts)) != 1:
            break
        common.append(parts[0])
    return tuple(common)


def _cycles(edges: Mapping[str, set[str]]) -> list[list[str]]:
    def reach(start: str) -> set[str]:
        seen: set[str] = set()
        stack = list(edges[start])
        while stack:
            node = stack.pop()
            if node not in seen:
                seen.add(node)
                stack.extend(edges[node])
        return seen

    reachable = {node: reach(node) for node in edges}
    cycles: list[list[str]] = []
    assigned: set[str] = set()
    for node in sorted(edges):
        if node in assigned:
            continue
        component = {node} | {m for m in reachable[node] if node in reachable[m]}
        assigned |= component
        if len(component) > 1:
            cycles.append(sorted(component))
    return cycles


# ---------------------------------------------------------------------------
# Area rule-group metrics (T040, FR-051): #16 false confidence and isolation,
# #17 type escapes, #31 debt markers. Language tokens are the registry's;
# every match runs over code with comments and strings blanked (type escapes
# keep comments, TODO scanning reads only comments), so a marker quoted in a
# string is never counted. Each derivation says which excerpts bounded it.
# ---------------------------------------------------------------------------

_ISOLATION_SEGMENTS = frozenset({"integration", "e2e", "end-to-end", "functional"})

_TEST_AREA_METHOD = (
    "tests are the registry's test declarations in test-file excerpts; a test "
    "runs from its declaration to the next one (or the excerpt end); markers "
    "and assertions are the registry's tokens, matched after comments and "
    "strings are blanked; only excerpts of registry languages are read, so "
    "this describes the quoted tests, not the repository"
)


def _line_of(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _code_test_excerpts(view: _PackView) -> list[tuple[Excerpt, LanguageSyntax]]:
    found = []
    for excerpt in view.test_excerpts:
        syntax = view.tables.syntax.get(PurePosixPath(excerpt.path).suffix)
        if syntax is not None:
            found.append((excerpt, syntax))
    return found


def _declarations(text: str, tables: LanguageTables) -> list[int]:
    """Offsets of each test declaration's first non-blank character: the
    registry patterns start with ``^\\s*``, which can reach back over blank
    lines, so ``match.start()`` alone would name the line before."""
    starts = {
        m.start() + len(m.group()) - len(m.group().lstrip())
        for p in tables.test_declarations
        for m in p.finditer(text)
    }
    return sorted(starts)


_CLIPPED = re.compile(r"\n…\[excerpt clipped: showing lines [^\n]*\]\Z")


def excerpt_clipped(text: str) -> bool:
    """Whether an excerpt ends in the line-cap clip marker that
    ``context.whole_file_excerpt`` and ``_code_extract`` append: its last
    quoted line is not the end of what it quotes. The marker text is pinned
    against both producers by a test, since this module may not import them."""
    return _CLIPPED.search(text) is not None


def _no_tests(what: str) -> MetricAbstention:
    return MetricAbstention(
        reason=(
            "no test declaration the registry recognises was found in a "
            "test-file excerpt of a registry language, so there is no test "
            f"to {what}; that is a zero denominator, not a share of 0. "
            + _TEST_AREA_METHOD
        )
    )


def _tests_without_assertions_share(view: _PackView) -> _Computed:
    tests = 0
    cut = 0
    empty: list[str] = []
    refs: set[str] = set()
    for excerpt, syntax in _code_test_excerpts(view):
        starts = _declarations(excerpt.text, view.tables)
        code = strip(excerpt.text, syntax)
        clipped = excerpt_clipped(excerpt.text)
        for index, start in enumerate(starts):
            last = index + 1 == len(starts)
            if last and clipped:
                # its body runs past the excerpt line limit: not fully quoted
                cut += 1
                continue
            end = len(code) if last else starts[index + 1]
            tests += 1
            refs.add(excerpt.ref)
            if not view.tables.assertions.search(code, start, end):
                line = excerpt.start_line + _line_of(excerpt.text, start) - 1
                empty.append(f"{excerpt.path}:{line}")
    if not tests and cut:
        return MetricAbstention(
            reason=(
                f"the only {cut} observed test(s) are cut by the excerpt line "
                "limit (the last test of a clipped excerpt is not fully quoted), "
                "so no test could be judged; that is not a share of 0. "
                + _TEST_AREA_METHOD
            )
        )
    if not tests:
        return _no_tests("check for assertions")
    return (
        len(empty) / tests,
        tuple(sorted(refs)),
        f"{len(empty)} of {tests} observed test(s) contain no assertion: "
        + (", ".join(empty) or "none")
        + (
            f"; {cut} test(s) cut by the excerpt line limit were not judged "
            "(the last test of a clipped excerpt is not fully quoted)"
            if cut
            else ""
        )
        + "; "
        + _TEST_AREA_METHOD,
    )


def _skipped_test_share(view: _PackView) -> _Computed:
    tests = 0
    hits: list[tuple[str, bool]] = []
    refs: set[str] = set()
    for excerpt, syntax in _code_test_excerpts(view):
        text = excerpt.text
        declared = [_line_of(text, start) for start in _declarations(text, view.tables)]
        tests += len(declared)
        if declared:
            refs.add(excerpt.ref)
        pattern = view.tables.skip_markers.get(PurePosixPath(excerpt.path).suffix)
        if pattern is None:
            continue
        raw_lines = text.split("\n")
        code = strip(text, syntax)
        code_lines = code.split("\n")
        kept_lines = strip(text, syntax, keep_strings=True).split("\n")
        for match in pattern.finditer(code):
            number = _line_of(code, match.start())
            if _skip_declares_a_test(number, declared, raw_lines):
                tests += 1
            # a reason is a string literal on the marker's own line
            reason = kept_lines[number - 1] != code_lines[number - 1]
            line = excerpt.start_line + number - 1
            hits.append((f"{excerpt.path}:{line}", reason))
            refs.add(excerpt.ref)
    if not tests:
        return _no_tests("compare skip markers against")
    with_reason = sum(1 for _where, reason in hits if reason)
    return (
        len(hits) / tests,
        tuple(sorted(refs)),
        f"{len(hits)} unconditional skip/disable marker(s) against {tests} "
        f"observed test(s) ({with_reason} with a reason, "
        f"{len(hits) - with_reason} without): "
        + (
            ", ".join(
                where + (" (reason)" if reason else " (no reason)")
                for where, reason in hits
            )
            or "none"
        )
        + "; conditional skips (skipif) are not markers; a marker annotates "
        "the test declared on its line, or below it across lines of the same "
        "attribute syntax (@..., #[...], [...]), or skips from inside the body "
        "of a test declared less indented above it; any other marker declares "
        "a skipped test itself (it.skip, xit) and is counted as one; "
        + _TEST_AREA_METHOD,
    )


def _skip_declares_a_test(number: int, declared: list[int], lines: list[str]) -> bool:
    """Whether the skip marker on line ``number`` is a test of its own."""
    if number in declared:
        return False
    marker = lines[number - 1].strip()
    below = [line for line in declared if line > number]
    if below and marker[:1] and not _word_char(marker[0]):
        between = [lines[i - 1].strip() for i in range(number + 1, below[0])]
        if all(item[:1] == marker[0] for item in between):
            return False
    above = [line for line in declared if line < number]
    if not above:
        return True
    return _indent_of(lines[number - 1]) <= _indent_of(lines[above[-1] - 1])


def _word_char(char: str) -> bool:
    return char.isalnum() or char == "_"


def _indent_of(line: str) -> int:
    return len(line) - len(line.lstrip())


def _network_calls_in_unit_tests_observed(view: _PackView) -> _Computed:
    scanned = []
    for excerpt, syntax in _code_test_excerpts(view):
        segments = set(PurePosixPath(excerpt.path).parent.parts)
        pattern = view.tables.network_calls.get(PurePosixPath(excerpt.path).suffix)
        if pattern is not None and not segments & _ISOLATION_SEGMENTS:
            scanned.append((excerpt, syntax, pattern))
    if not scanned:
        return MetricAbstention(
            reason=(
                "no unit-test excerpt of a registry language with network-call "
                "tokens is in this pack (tests under an integration, e2e, "
                "end-to-end or functional directory are not unit tests), so no "
                "unit test was scanned; that is not the same as isolated tests"
            )
        )
    hits: dict[tuple[str, int], str] = {}
    for excerpt, syntax, pattern in scanned:
        code = strip(excerpt.text, syntax)
        for match in pattern.finditer(code):
            line = excerpt.start_line + _line_of(code, match.start()) - 1
            hits.setdefault((excerpt.path, line), excerpt.ref)
    cited = sorted(set(hits.values())) or sorted({e.ref for e, _s, _p in scanned})
    return (
        len(hits),
        tuple(cited),
        f"{len(hits)} line(s) calling the network in {len(scanned)} unit-test "
        "excerpt(s): "
        + (", ".join(f"{path}:{line}" for path, line in sorted(hits)) or "none")
        + "; network calls are the registry's network_calls tokens matched "
        "after comments and strings are blanked; tests under integration, "
        "e2e, end-to-end or functional directories are excluded; a lower "
        "bound on the repository, since only these excerpts were read",
    )


_TYPE_ESCAPE_METHOD = (
    "type escapes are the registry's type_escapes tokens (Any, type: ignore, "
    "@ts-ignore, ...), matched in source-file excerpts of registry languages "
    "after string literals are blanked (comments are kept, since most "
    "escapes are comments); generated type stubs (the registry's "
    "type_stub_names) are not read; per 1000 quoted source lines"
)


def _type_escapes_per_kloc(view: _PackView) -> _Computed:
    lines = 0
    hits: list[str] = []
    refs: set[str] = set()
    for excerpt in view.pack.excerpts:
        path = PurePosixPath(excerpt.path)
        pattern = view.tables.type_escapes.get(path.suffix)
        syntax = view.tables.syntax.get(path.suffix)
        if (
            pattern is None
            or syntax is None
            or not _is_source_file(excerpt.path, view.tables)
            or any(p.fullmatch(path.name) for p in view.tables.type_stub_patterns)
        ):
            continue
        lines += _excerpt_lines(excerpt)
        refs.add(excerpt.ref)
        text = _strings_blanked(excerpt.text, syntax)
        for match in pattern.finditer(text):
            line = excerpt.start_line + _line_of(text, match.start()) - 1
            hits.append(f"{excerpt.path}:{line}")
    if not lines:
        return MetricAbstention(
            reason=(
                "no source-file excerpt of a registry language with type-escape "
                "tokens is in this pack, so no code was scanned; that is not the "
                "same as code without escapes. " + _TYPE_ESCAPE_METHOD
            )
        )
    return (
        len(hits) / lines * 1000,
        tuple(sorted(refs)),
        f"{len(hits)} type escape(s) in {lines} quoted source line(s): "
        + (", ".join(hits) or "none")
        + "; "
        + _TYPE_ESCAPE_METHOD,
    )


def _strings_blanked(text: str, syntax: LanguageSyntax) -> str:
    """``text`` with string literals blanked and comments kept."""
    code = strip(text, syntax)
    without_comments = strip(text, syntax, keep_strings=True)
    return "".join(
        raw if kept != raw else blank
        for raw, kept, blank in zip(text, without_comments, code, strict=True)
    )


_DEBT_MARKER = re.compile(r"\b(?:TODO|FIXME|XXX|HACK)\b")
_TICKET_REF = re.compile(r"\b[A-Z][A-Z0-9]+-\d+\b|#\d+\b|https?://\S+")

_TODO_METHOD = (
    "debt markers are TODO, FIXME, XXX or HACK as whole words inside comments "
    "(the registry's comment delimiters; a marker in a string is not a "
    "comment); a marker has a ticket when its comment names a KEY-123 issue "
    "key, a #123 reference or a URL; only source-file excerpts of registry "
    "languages are read, so this describes the quoted code, not the repository"
)


def _todo_without_ticket_share(view: _PackView) -> _Computed:
    markers: list[tuple[str, bool]] = []
    refs: set[str] = set()
    scanned = 0
    for excerpt in view.pack.excerpts:
        syntax = view.tables.syntax.get(PurePosixPath(excerpt.path).suffix)
        if syntax is None or not _is_source_file(excerpt.path, view.tables):
            continue
        scanned += 1
        kept = strip(excerpt.text, syntax, keep_strings=True)
        comments = "".join(
            raw if raw != other or raw == "\n" else " "
            for raw, other in zip(excerpt.text, kept, strict=True)
        )
        for number, line in enumerate(comments.split("\n"), start=1):
            if _DEBT_MARKER.search(line):
                where = f"{excerpt.path}:{excerpt.start_line + number - 1}"
                markers.append((where, bool(_TICKET_REF.search(line))))
                refs.add(excerpt.ref)
    if not markers:
        return MetricAbstention(
            reason=(
                f"no debt marker was found in the comments of {scanned} "
                "source-file excerpt(s), so the share has a zero denominator; "
                "that is not a share of 0. " + _TODO_METHOD
            )
        )
    without = [where for where, ticket in markers if not ticket]
    return (
        len(without) / len(markers),
        tuple(sorted(refs)),
        f"{len(without)} of {len(markers)} debt marker(s) name no ticket: "
        + (", ".join(without) or "none")
        + "; "
        + _TODO_METHOD,
    )


# ---------------------------------------------------------------------------
# Reliability (T043): #12 swallowed errors, #13 calls without a deadline and
# retries without backoff, #15 queries in loops, #6 transaction evidence.
# Every token is the registry's; matching is textual, so a count is a place
# to look and a lower bound, never a proven defect.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReliabilityFindings:
    """1-indexed lines of one text holding each reliability fact (T043)."""

    swallowed: tuple[int, ...]
    calls: tuple[int, ...]
    unbounded_calls: tuple[int, ...]
    retries: tuple[int, ...]
    unbacked_retries: tuple[int, ...]
    queries: tuple[int, ...]
    queries_in_loops: tuple[int, ...]
    transactions: tuple[int, ...]


def reliability_findings(
    path: str, text: str, tables: LanguageTables
) -> ReliabilityFindings | None:
    """The reliability facts of ``text`` (the contents of ``path``), or
    ``None`` when its language has no structure syntax.

    Tokens match with strings and comments blanked, except
    ``swallowed_errors``, which keeps comments: a handler holding a comment,
    or followed by one on its last line (``pass  # why``), is a documented
    choice and is not counted. A call or retry statement runs like a
    cookie statement; one whose brackets never close is counted as a call
    but never judged. A ``client_timeouts`` token anywhere in the text
    bounds every call in it (a wrapper's deadline). Lines longer than
    ``MAX_LINE_CHARS`` (generated or minified code) are skipped.
    """
    suffix = PurePosixPath(path).suffix
    syntax = tables.syntax.get(suffix)
    if syntax is None:
        return None
    code = strip(text, syntax)
    lines = code.split("\n")
    # Whole files can be large: count newlines forward from the last match,
    # never from the start (each pass visits matches in offset order).
    position = [0, 1]

    def line_of(offset: int) -> int:
        if offset < position[0]:
            position[:] = [0, 1]
        position[1] += code.count("\n", position[0], offset)
        position[0] = offset
        return position[1]

    def lines_of(pattern: re.Pattern[str] | None, source: str) -> tuple[int, ...]:
        if pattern is None:
            return ()
        found = {line_of(m.start()) for m in pattern.finditer(source)}
        return tuple(sorted(n for n in found if len(lines[n - 1]) <= MAX_LINE_CHARS))

    def statements(
        calls: re.Pattern[str] | None, flags: re.Pattern[str] | None
    ) -> tuple[tuple[int, ...], tuple[int, ...]]:
        """(every statement line, those without a flag inside)."""
        found: dict[int, bool] = {}
        for match in calls.finditer(code) if calls is not None else ():
            line = line_of(match.start())
            if line in found or len(lines[line - 1]) > MAX_LINE_CHARS:
                continue
            end = _statement_end(code, match.start())
            flagged = end is None or (
                flags is not None and flags.search(code, match.start(), end) is not None
            )
            found[line] = not flagged
        ordered = sorted(found)
        return tuple(ordered), tuple(n for n in ordered if found[n])

    calls, unbounded = statements(
        tables.outbound_calls.get(suffix), tables.call_timeouts.get(suffix)
    )
    wrapper = tables.client_timeouts.get(suffix)
    if wrapper is not None and wrapper.search(code):
        unbounded = ()
    retries, unbacked = statements(
        tables.retry_calls.get(suffix), tables.retry_backoff.get(suffix)
    )
    queries = lines_of(tables.query_calls.get(suffix), code)
    loops = tables.loop_keywords.get(suffix)
    in_loops = tuple(
        line
        for line in queries
        if loops is not None
        and _in_loop(lines, line, tables.query_calls[suffix], loops, syntax)
    )
    return ReliabilityFindings(
        swallowed=_undocumented(
            tables.swallowed_errors.get(suffix),
            _strings_blanked(text, syntax),
            code,
            line_of,
        ),
        calls=calls,
        unbounded_calls=unbounded,
        retries=retries,
        unbacked_retries=unbacked,
        queries=queries,
        queries_in_loops=in_loops,
        transactions=lines_of(tables.transaction_markers.get(suffix), code),
    )


def _undocumented(
    pattern: re.Pattern[str] | None,
    source: str,
    code: str,
    line_of: Callable[[int], int],
) -> tuple[int, ...]:
    """Lines of ``pattern`` matches in ``source`` (comments kept) whose span,
    through the end of its last line, holds no comment: ``code`` (comments
    blanked) differs from ``source`` exactly where a comment is."""
    found: set[int] = set()
    for match in pattern.finditer(source) if pattern is not None else ():
        begin = source.rfind("\n", 0, match.start()) + 1
        first_end = source.find("\n", match.start())
        end = source.find("\n", match.end())
        first_end, end = (len(source) if i < 0 else i for i in (first_end, end))
        if (
            first_end - begin <= MAX_LINE_CHARS
            and source[match.start() : end] == code[match.start() : end]
        ):
            found.add(line_of(match.start()))
    return tuple(sorted(found))


def _in_loop(
    lines: list[str],
    line: int,
    query: re.Pattern[str],
    loops: re.Pattern[str],
    syntax: LanguageSyntax,
) -> bool:
    """Whether the query on ``line`` runs once per iteration of a loop.

    On its own line only a ``.``-method loop token before the query counts
    (``ids.map((id) => find(id))``): a keyword there is the loop's header,
    which runs the query once. Above it, each less-indented line encloses it;
    the first holding a loop token puts it in a loop, and the first holding
    a function start ends the search (a loop around a function definition
    does not run its body).
    """
    current = lines[line - 1]
    first = query.search(current)
    start = first.start() if first is not None else len(current)
    if any(
        m.group().startswith(".") and m.end() <= start for m in loops.finditer(current)
    ):
        return True
    threshold = _indent_of(current)
    for index in range(line - 2, -1, -1):
        if threshold == 0:
            break
        candidate = lines[index]
        if not candidate.strip() or len(candidate) > MAX_LINE_CHARS:
            continue
        indent = _indent_of(candidate)
        if indent >= threshold:
            continue
        if loops.search(candidate):
            return True
        if syntax.function_start.search(candidate):
            return False
        threshold = indent
    return False


MAX_RELIABILITY_LISTED = 20
"""Sites named in one reliability derivation; the rest are counted."""


@dataclass(frozen=True)
class _ReliabilityRule:
    fields: tuple[str, ...]
    """LanguageTables fields a language must declare to be scanned."""
    hits: str
    total: str | None
    """The findings attribute counting all candidates; ``None`` when a count
    over the scanned code is meaningful without any (no handler swallowed)."""
    what: str
    candidates: str


_RELIABILITY_RULES = {
    "swallowed_errors_observed": _ReliabilityRule(
        ("swallowed_errors",),
        "swallowed",
        None,
        "error handler(s) doing nothing (the registry's swallowed_errors tokens, "
        "matched with comments kept, so a handler holding a comment is not "
        "counted)",
        "",
    ),
    "outbound_calls_without_timeout_observed": _ReliabilityRule(
        ("outbound_calls",),
        "unbounded_calls",
        "calls",
        "outbound call(s) with no deadline (an outbound_calls statement holding "
        "no call_timeouts token, in a file holding no client_timeouts token)",
        "outbound call",
    ),
    "retries_without_backoff_observed": _ReliabilityRule(
        ("retry_calls",),
        "unbacked_retries",
        "retries",
        "retry statement(s) with no delay or backoff (a retry_calls statement "
        "holding no retry_backoff token)",
        "retry statement",
    ),
    "queries_in_loops_observed": _ReliabilityRule(
        ("query_calls", "loop_keywords"),
        "queries_in_loops",
        "queries",
        "database query call(s) inside a loop body (a query_calls token on a "
        "line enclosed, by indentation up to its function, by a loop_keywords "
        "line, or after a .method loop token on its own line)",
        "database query call",
    ),
}

_RELIABILITY_METHOD = (
    "matched textually in source-file (not test) excerpts of registry "
    "languages declaring these tokens, after strings and comments are "
    "blanked; a lower bound on the repository, since only these excerpts "
    "were read"
)


def _reliability_count(name: str) -> Callable[[_PackView], _Computed]:
    rule = _RELIABILITY_RULES[name]

    def compute(view: _PackView) -> _Computed:
        scanned: list[tuple[Excerpt, ReliabilityFindings]] = []
        for excerpt in view.pack.excerpts:
            suffix = PurePosixPath(excerpt.path).suffix
            if not _is_source_file(excerpt.path, view.tables) or not all(
                suffix in getattr(view.tables, item) for item in rule.fields
            ):
                continue
            if excerpt.ref not in view.reliability:
                view.reliability[excerpt.ref] = reliability_findings(
                    excerpt.path, excerpt.text, view.tables
                )
            found = view.reliability[excerpt.ref]
            if found is not None:
                scanned.append((excerpt, found))
        if not scanned:
            return MetricAbstention(
                reason=(
                    "no source-file excerpt of a registry language declaring "
                    f"{' and '.join(rule.fields)} is in this pack, so no code was "
                    "scanned; that is not the same as code without "
                    + rule.what.split(" (", 1)[0]
                )
            )
        if rule.total is not None and not any(
            getattr(found, rule.total) for _excerpt, found in scanned
        ):
            return MetricAbstention(
                reason=(
                    f"no {rule.candidates} was found in the {len(scanned)} "
                    "source-file excerpt(s) scanned, so there is nothing to "
                    f"judge; that is not the same as every {rule.candidates} "
                    "being sound. " + _RELIABILITY_METHOD
                )
            )
        sites = {
            (excerpt.path, excerpt.start_line + line - 1): excerpt.ref
            for excerpt, found in scanned
            for line in getattr(found, rule.hits)
        }
        cited = sorted(set(sites.values())) or sorted({e.ref for e, _f in scanned})
        ordered = sorted(sites)
        listed = ", ".join(
            f"{path}:{line}" for path, line in ordered[:MAX_RELIABILITY_LISTED]
        )
        more = len(ordered) - MAX_RELIABILITY_LISTED
        total = (
            f" of {sum(len(getattr(f, rule.total)) for _e, f in scanned)}"
            if rule.total is not None
            else ""
        )
        return (
            len(sites),
            tuple(cited),
            f"{len(sites)}{total} {rule.what} in {len(scanned)} source-file "
            "excerpt(s): "
            + (listed or "none")
            + (f" and {more} more" if more > 0 else "")
            + "; "
            + _RELIABILITY_METHOD,
        )

    return compute


# ---------------------------------------------------------------------------
# Backward compatibility (T055, area #5): read by the blast-radius dimension
# from the diff of a changes scope into ``pack.compat``; each listed item is
# a pack excerpt, so a count is shown only with all of its listed evidence.
# ---------------------------------------------------------------------------


def _compat_count(kind: str) -> Callable[[_PackView], _Computed]:
    what = (
        "removed or renamed public declaration(s)"
        if kind == "symbols"
        else "destructive migration operation(s)"
    )

    def compute(view: _PackView) -> _Computed:
        pack = view.pack
        facts = pack.compat
        if pack.dimension != BLAST_RADIUS:
            return MetricAbstention(
                reason=(
                    "only the blast-radius pack reads the diff of a change, and "
                    f"this is the {pack.dimension!r} pack"
                )
            )
        if facts is None:
            why = (
                "the changes scope could not be resolved (its ref was not "
                "supplied), so there is no diff to read"
                if pack.scope == "changes"
                else f"this pack is at {pack.scope!r} scope, which carries no "
                "diff; backward compatibility is read only from the diff of a "
                "'changes' scope (a commit, range or branch)"
            )
            return MetricAbstention(reason=why)
        if facts.unavailable:
            return MetricAbstention(reason=facts.unavailable)
        if facts.incomplete:
            return MetricAbstention(
                reason="the diff could not be read completely: " + facts.incomplete
            )
        items, total = (
            (facts.removed_symbols, facts.removed_symbols_total)
            if kind == "symbols"
            else (facts.destructive_ops, facts.destructive_ops_total)
        )
        present = {e.ref for e in pack.excerpts}
        dropped = [item.ref for item in items if item.ref not in present]
        if dropped:
            return MetricAbstention(
                reason=(
                    f"{len(dropped)} quoted diff line(s) the count rests on are not "
                    "in this pack (the byte budget dropped them), so the count "
                    "could not be shown with its evidence"
                ),
                omitted_lower_bound=len(dropped),
            )
        # The quoted lines when there are any; a count of 0 cites the changed
        # files that were read, since it is a statement about them.
        refs = {item.ref for item in items} or {
            path for path in facts.examined if path in set(pack.files_read)
        }
        if not refs:
            return MetricAbstention(
                reason="no changed file of this diff could be read or quoted, so "
                "there is no evidence to cite"
            )
        listed = ", ".join(f"{item.ref} {item.detail}" for item in items) or "none"
        more = total - len(items)
        renamed = (
            f"; {len(facts.renamed_code_files)} code file(s) renamed, not counted "
            "(whether a file path is public API depends on the language): "
            + ", ".join(facts.renamed_code_files[:5])
            if kind == "symbols" and facts.renamed_code_files
            else ""
        )
        secret = (
            f"; {len(facts.secret_excluded)} secret-bearing file(s) excluded: "
            + ", ".join(facts.secret_excluded[:5])
            + " (existence only; contents withheld and never parsed, DDR-0002)"
            if facts.secret_excluded
            else ""
        )
        return (
            total,
            tuple(sorted(refs)),
            f"{total} {what} in the diff of {len(facts.examined)} changed "
            f"file(s): {listed}"
            + (f", and {more} more counted, not quoted" if more > 0 else "")
            + renamed
            + secret
            + ". Method: "
            + _COMPAT_METHOD,
        )

    return compute


_COMPAT_METHOD = (
    "textual, over the changes scope's diff (see the pack warning): removed "
    "lines of non-test code starting with a registry public_declarations "
    "token, unless the same name is declared again in the change; added "
    "destructive operations in migration files outside down sections"
)


# ---------------------------------------------------------------------------
# Documentation source of truth (T055, area #27): recorded by the
# requirement-fidelity dimension in ``pack.doc_history``.
# ---------------------------------------------------------------------------


def _no_doc_history(view: _PackView) -> MetricAbstention | None:
    pack = view.pack
    if pack.dimension != REQUIREMENT_FIDELITY:
        return MetricAbstention(
            reason=(
                "only the requirement-fidelity pack records documentation "
                f"source-of-truth facts, and this is the {pack.dimension!r} pack"
            )
        )
    if pack.doc_history is None:
        return MetricAbstention(
            reason=(
                f"the {pack.scope} scope could not be resolved, so no "
                "documentation facts were gathered"
            )
        )
    return None


def _requirements_docs_count(view: _PackView) -> _Computed:
    absent = _no_doc_history(view)
    if absent is not None:
        return absent
    facts = view.pack.doc_history
    refs = [path for path in facts.requirements_docs if path in view.files]
    if not facts.requirements_docs_total or not refs:
        return MetricAbstention(
            reason=(
                "no readable file fills the requirements-doc role, so there is no "
                "requirements source to count; the role's miss is in this pack's "
                "sources_missing"
            )
        )
    more = facts.requirements_docs_total - len(facts.requirements_docs)
    return (
        facts.requirements_docs_total,
        tuple(sorted(refs)),
        f"{facts.requirements_docs_total} file(s) fill the requirements-doc role "
        "(PRD*.md or a document named for requirements, anywhere): "
        + ", ".join(facts.requirements_docs)
        + (f", and {more} more" if more > 0 else "")
        + "; more than one is several competing requirements sources rather than "
        "one canonical document",
    )


def _code_commits_with_docs_share(view: _PackView) -> _Computed:
    absent = _no_doc_history(view)
    if absent is not None:
        return absent
    facts = view.pack.doc_history
    if facts.history_unavailable:
        return MetricAbstention(reason=facts.history_unavailable)
    if not facts.code_commits:
        return MetricAbstention(
            reason=(
                f"none of the {facts.commits_scanned} non-merge local commit(s) "
                f"read (window {facts.window}) changed a code file, so the share "
                "has a zero denominator; that is not a share of 0"
            )
        )
    cited = {*facts.docs_cited, *facts.requirements_docs}
    refs = sorted(path for path in cited if path in view.files)
    if not refs:
        # A missing document fails the rule, never abstains (T075, FR-067):
        # the share is still read from history, cited by the code files read.
        refs = [path for path in view.files if code_kind(path, view.tables)][
            :MAX_CODE_FILES_CITED
        ]
    if not refs:
        return MetricAbstention(
            reason="no document or code file of this pack was read, so there is "
            "no evidence to cite beside the share"
        )
    return (
        facts.code_commits_with_docs / facts.code_commits,
        tuple(refs),
        f"{facts.code_commits_with_docs} of {facts.code_commits} code-changing "
        f"commit(s) also changed documentation, among the last "
        f"{facts.commits_scanned} non-merge local commit(s) read (window "
        f"{facts.window}); co-changed documents cited: "
        + (", ".join(facts.docs_cited) or "none")
        + "; code = a file the registry classifies as source or test code; "
        "documentation = a .md/.rst/.adoc/.txt file or a file under doc/ or "
        "docs/",
    )


MAX_CODE_FILES_CITED = 20
"""Code files cited by a history share when no document can be (T075)."""


def _code_fact(view: _PackView) -> MetricAbstention:
    """The T075 code metrics are computed by the requirement-fidelity
    dimension over whole files and stored on ``pack.whole_file``; reaching
    this function means they were not."""
    pack = view.pack
    if pack.dimension != REQUIREMENT_FIDELITY:
        return MetricAbstention(
            reason=(
                "only the requirement-fidelity pack records route, commit and "
                f"requirement-item facts, and this is the {pack.dimension!r} pack"
            )
        )
    return MetricAbstention(
        reason=(
            f"the {pack.scope} scope could not be resolved, so no route, commit "
            "or requirement-item facts were gathered"
        )
    )


_COOKIE_METHOD = (
    "a cookie-setting statement is the registry's cookie_calls token (e.g. "
    ".set_cookie(, res.cookie(, http.Cookie{) matched after comments and "
    "strings are blanked, through the end of its statement; a flag counts as "
    "set only when the language's cookie_secure / cookie_httponly / "
    "cookie_samesite token (a literal true; SameSite with any value) occurs "
    "inside that statement, so a flag set elsewhere (a later assignment, "
    "framework configuration or a framework default) is not visible here and "
    "counts as not set; only source-file excerpts of registry languages are "
    "read, so this is a lower bound on the repository"
)


def _cookie_flags_missing_observed(view: _PackView) -> _Computed:
    scanned = 0
    sites: dict[tuple[str, int], tuple[tuple[str, ...] | None, str]] = {}
    auth: dict[tuple[str, int], str] = {}
    for excerpt in view.pack.excerpts:
        suffix = PurePosixPath(excerpt.path).suffix
        if suffix not in view.tables.cookie_calls or not _is_source_file(
            excerpt.path, view.tables
        ):
            continue
        scanned += 1
        for line in auth_lines(excerpt.path, excerpt.text, view.tables):
            auth.setdefault((excerpt.path, excerpt.start_line + line - 1), excerpt.ref)
        for site in cookie_sites(excerpt.path, excerpt.text, view.tables):
            key = (excerpt.path, excerpt.start_line + site.line - 1)
            if sites.get(key, (None, ""))[0] is None:
                sites[key] = (site.missing, excerpt.ref)
    if not auth:
        # The gate (user, 2026-09-29): cookie flags are judged only where
        # authentication or session code was read, so a CLI or a library is
        # never scored on cookies it has no reason to set.
        return MetricAbstention(
            reason=(
                "no authentication or session code (a registry auth_markers "
                f"token) was found in {scanned} source-file excerpt(s) of "
                "registry languages with cookie tokens, so no cookie flag is "
                "judged: this gate is never scored, and a repository without "
                "such code (a CLI, a library) is not rated on cookies; "
                + (
                    f"{len(sites)} cookie-setting statement(s) were found "
                    f"({_bounded_sites(sites)})"
                    if sites
                    else "no cookie-setting statement was found"
                )
                + "; auth tokens are matched after comments and strings are "
                "blanked, in source files only (not tests). "
                + _COOKIE_METHOD
            )
        )
    gate = f"authentication or session code was read at {_bounded_sites(auth)}"
    judged = {key: value for key, value in sites.items() if value[0] is not None}
    cut = len(sites) - len(judged)
    if not judged:
        return MetricAbstention(
            reason=(
                f"no cookie-setting statement could be judged in {scanned} "
                "source-file excerpt(s) of registry languages with cookie tokens"
                + (
                    f" ({cut} ran past the end of its excerpt)"
                    if cut
                    else ""
                )
                + ", so no cookie flag was checked; a cookie a framework sets "
                "itself (a session middleware's default cookie) is not visible "
                "in code; that is not the same as cookies with every flag set; "
                + gate
                + ". "
                + _COOKIE_METHOD
            )
        )
    lacking = {key: value for key, value in judged.items() if value[0]}
    cited = lacking or judged
    return (
        len(lacking),
        tuple(
            sorted(
                {ref for _missing, ref in cited.values()} | {auth[min(auth)]}
            )
        ),
        f"{len(lacking)} of {len(judged)} cookie-setting statement(s) leave a "
        "flag unset: "
        + (
            ", ".join(
                f"{path}:{line} (no {', '.join(missing or ())})"
                for (path, line), (missing, _ref) in sorted(lacking.items())
            )
            or "none"
        )
        + (
            f"; {cut} statement(s) ran past their excerpt and were not judged"
            if cut
            else ""
        )
        + "; "
        + gate
        + "; "
        + _COOKIE_METHOD,
    )


_MAX_LISTED = 5


def _bounded_sites(sites: Mapping[tuple[str, int], object]) -> str:
    """``path:line`` of the first :data:`_MAX_LISTED` sites, the rest counted."""
    ordered = sorted(sites)
    listed = ", ".join(f"{path}:{line}" for path, line in ordered[:_MAX_LISTED])
    more = len(ordered) - _MAX_LISTED
    return listed + (f" and {more} more" if more > 0 else "")


_STRICT_METHOD = (
    "a type-checker configuration is a registry type_config_files file (the "
    "whole file, or in a shared file only its declared section, e.g. "
    "pyproject.toml [tool.mypy]); strict mode counts as enabled when a "
    "type_strict token (e.g. strict = true, \"strict\": true) occurs there, "
    "outside comment lines, after the last type_strict_off token, else "
    "through the files it extends (the last listed wins); a language counts "
    "as strict when any of its configurations read is; strictness passed "
    "as command-line flags (mypy --strict, tsc --strict) is not visible in "
    "any file, so a repository without such a file abstains rather than "
    "being rated; only "
    "configuration files quoted in this pack are read"
)

_STATE_ORDER = ("strict", "off", "unset", "unseen")

def _last_match(pattern: re.Pattern[str] | None, text: str) -> int:
    """Offset of ``pattern``'s last match in ``text``; -1 for none."""
    if pattern is None:
        return -1
    return max((match.start() for match in pattern.finditer(text)), default=-1)


_CONFIG_COMMENTS = ("#", ";", "//", "/*", "*")
"""Line-comment openers of the configuration formats type checkers read
(INI, TOML, JSON with comments): format syntax, not a language's."""


def _uncommented(text: str) -> str:
    """``text`` with every comment line blanked, line count kept."""
    return "\n".join(
        "" if line.lstrip().startswith(_CONFIG_COMMENTS) else line
        for line in text.split("\n")
    )


def _strict_type_config_missing(view: _PackView) -> _Computed:
    tables = view.tables
    by_path: dict[str, list[Excerpt]] = {}
    for excerpt in view.pack.excerpts:
        by_path.setdefault(excerpt.path, []).append(excerpt)

    def decide(
        language: str, texts: list[tuple[str, bool]]
    ) -> tuple[str, tuple[str, ...]]:
        """The merged strict state of one configuration's quoted texts, and
        the files it extends."""
        states = []
        targets: tuple[str, ...] = ()
        on = tables.type_strict.get(language)
        off = tables.type_strict_off.get(language)
        extends = tables.type_config_extends.get(language)
        for quoted, clipped in texts:
            text = _uncommented(quoted)
            last_on = _last_match(on, text)
            last_off = _last_match(off, text)
            if last_on > last_off:
                states.append("strict")
            elif clipped:
                states.append("unseen")
            else:
                states.append("off" if last_off >= 0 else "unset")
            if extends is not None and not targets:
                targets = extends_targets(text, extends)
        return min(states, key=_STATE_ORDER.index), targets

    unresolved: list[str] = []

    def resolved(path: str, language: str, state: str, targets, seen) -> str:
        if state != "unset":
            return state
        for target in reversed(targets):
            base = next(
                (c for c in resolve_extends(path, target) if c in by_path), None
            )
            if base is None or base in seen:
                unresolved.append(f"{path} extends {target!r}")
                return "unseen"
            texts = [(e.text, excerpt_clipped(e.text)) for e in by_path[base]]
            state, targets = decide(language, texts)
            inherited = resolved(base, language, state, targets, seen | {base})
            if inherited != "unset":
                return inherited
        return "unset"

    # (language, path, header) -> (state, refs, cited span)
    roots: dict[tuple[str, str, str | None], tuple[str, set[str], str]] = {}
    extended: set[str] = set()
    for path in sorted(by_path):
        found: dict[tuple[str, str | None], list[tuple[str, bool, str, str]]] = {}
        for excerpt in by_path[path]:
            lines = excerpt.text.split("\n")
            clipped = excerpt_clipped(excerpt.text)
            for section in type_config_sections(path, excerpt.text, tables):
                text = "\n".join(lines[section.line - 1 : section.end_line])
                start = excerpt.start_line + section.line - 1
                end = min(excerpt.end_line, excerpt.start_line + section.end_line - 1)
                span = f"{path}:{start}-{end}" + (
                    f" {section.header}" if section.header else ""
                )
                cut = clipped and section.end_line == len(lines)
                found.setdefault((section.language, section.header), []).append(
                    (text, cut, excerpt.ref, span)
                )
        for (language, header), parts in found.items():
            state, targets = decide(language, [(t, c) for t, c, _r, _s in parts])
            extended.update(
                c for target in targets for c in resolve_extends(path, target)
            )
            state = resolved(path, language, state, targets, frozenset({path}))
            roots[(language, path, header)] = (
                state,
                {ref for _t, _c, ref, _s in parts},
                parts[0][3],
            )

    # A configuration another one extends is a base, not a project of its
    # own: it counts only through its extenders (tsconfig.base.json).
    read = sorted({path for _language, path, _header in roots})
    roots = {key: value for key, value in roots.items() if key[1] not in extended}
    if read and not roots:
        return MetricAbstention(
            reason=(
                "every type-checker configuration read ("
                + ", ".join(read[:_MAX_LISTED])
                + ") is extended by another, a cycle no type checker accepts, "
                "so strict mode cannot be judged. " + _STRICT_METHOD
            )
        )
    languages: dict[str, str] = {}
    for (language, _path, _header), (state, _refs, _span) in roots.items():
        current = languages.get(language)
        rank = {"strict": 0, "unseen": 1, "off": 2, "unset": 2}
        if current is None or rank[state] < rank[current]:
            languages[language] = state
    judged = {lang: s for lang, s in languages.items() if s != "unseen"}
    unseen = sorted(set(languages) - set(judged))
    if not judged:
        if not roots:
            return MetricAbstention(
                reason=(
                    "no type-checker configuration was read, so strict mode "
                    "cannot be judged: strictness may be set by command-line "
                    "flags that no file shows, and a language without a type "
                    "checker declares no configuration; that is not the same "
                    "as a configuration without strict mode. " + _STRICT_METHOD
                )
            )
        return MetricAbstention(
            reason=(
                "the type-checker configuration read for "
                + ", ".join(unseen)
                + " could not be judged: "
                + (
                    "; ".join(sorted(set(unresolved))[:_MAX_LISTED])
                    + " (not read: a package, or a file outside this pack)"
                    if unresolved
                    else "its section runs past the end of its clipped excerpt"
                )
                + ". "
                + _STRICT_METHOD
            )
        )
    lacking = sorted(lang for lang, state in judged.items() if state != "strict")
    cited = [
        (key, value)
        for key, value in sorted(
            roots.items(), key=lambda item: (*item[0][:2], item[0][2] or "")
        )
        if key[0] in (lacking or judged)
    ]

    def spans(language: str) -> str:
        return ", ".join(
            f"{span} ({state})"
            for (lang, _p, _h), (state, _r, span) in cited
            if lang == language
        )

    return (
        len(lacking),
        tuple(sorted({ref for _key, (_s, refs, _span) in cited for ref in refs})),
        f"{len(lacking)} of {len(judged)} language(s) with a type-checker "
        "configuration read enable no strict mode: "
        + ("; ".join(f"{lang}: {spans(lang)}" for lang in lacking) or "none")
        + (
            "; strict: " + ", ".join(sorted(set(judged) - set(lacking)))
            if set(judged) - set(lacking)
            else ""
        )
        + ("; not judged: " + ", ".join(unseen) if unseen else "")
        + "; "
        + _STRICT_METHOD,
    )


# ---------------------------------------------------------------------------
# Supply-chain CI evidence (T041, areas #20-#22). Computed only over the
# supply-chain pack; every token and pattern is the registry's or the generic
# layer's (core/roles.py GENERIC_CI_FACTS), never this module's.
# ---------------------------------------------------------------------------

SUPPLY_CHAIN = "supply-chain"

_SUPPLY_CHAIN_ONLY = (
    "only the supply-chain pack quotes CI and release configuration, and this "
    "is the {dimension!r} pack"
)


def _ci_lines(
    view: _PackView, match: Callable[[str], bool] | None
) -> tuple[list[tuple[str, int, str]], list[str], list[str]]:
    """``(lines, files, clipped)`` over the excerpts whose path ``match``
    accepts: each non-comment line with its path and line number (a trailing
    `` #`` comment removed), the distinct paths, and the paths whose excerpt
    ends in the line-cap clip marker."""
    lines: list[tuple[str, int, str]] = []
    files: dict[str, None] = {}
    clipped: dict[str, None] = {}
    for excerpt in view.pack.excerpts if match is not None else ():
        if not match(excerpt.path):
            continue
        files.setdefault(excerpt.path)
        if excerpt_clipped(excerpt.text):
            clipped.setdefault(excerpt.path)
        for offset, line in enumerate(excerpt.text.splitlines()):
            code = line.split(" #", 1)[0]
            if code.lstrip().startswith("#"):
                continue
            lines.append((excerpt.path, excerpt.start_line + offset, code))
    return lines, list(files), list(clipped)


def _ci_abstention(view: _PackView) -> MetricAbstention | None:
    if view.pack.dimension != SUPPLY_CHAIN:
        return MetricAbstention(
            reason=_SUPPLY_CHAIN_ONLY.format(dimension=view.pack.dimension)
        )
    return None


def _no_ci_file(what: str) -> MetricAbstention:
    return MetricAbstention(
        reason=(
            f"no CI workflow file was quoted in this pack, so there is no {what} "
            "to examine; that is not the same as a pipeline without one "
            "(the ci-workflow role's miss is in sources_missing)"
        )
    )


def _ci_actions_unpinned_share(view: _PackView) -> _Computed:
    absent = _ci_abstention(view)
    if absent is not None:
        return absent
    tables = view.tables
    lines, files, clipped = _ci_lines(view, tables.ci_files)
    if not files:
        return _no_ci_file("action reference")
    if clipped:
        return MetricAbstention(
            reason=(
                "a CI workflow excerpt was clipped at the line cap ("
                + ", ".join(clipped)
                + "), so references beyond it were never read"
            )
        )
    if tables.action_reference is None:
        return MetricAbstention(reason="no action-reference token is declared")
    external: list[tuple[str, int, str]] = []
    for path, number, line in lines:
        found = tables.action_reference.search(line)
        if found and not found[1].startswith(tables.local_reference):
            external.append((path, number, found[1]))
    if not external:
        return MetricAbstention(
            reason=(
                "no external action reference (uses: owner/repo@ref, or a step "
                "or service image:) appears in "
                "the quoted CI workflows, so there is nothing to pin; that is a "
                "zero denominator, not a share of 0"
            )
        )
    unpinned = [
        item
        for item in external
        if not any(pattern.search(item[2]) for pattern in tables.pinned_reference)
    ]
    return (
        len(unpinned) / len(external),
        tuple(sorted({path for path, _n, _r in external})),
        f"{len(unpinned)} of {len(external)} external action reference(s) in "
        f"{len(files)} CI workflow file(s) are not pinned to a full commit SHA "
        "or image digest: "
        + (", ".join(f"{p}:{n} {r}" for p, n, r in unpinned[:5]) or "none")
        + (f", and {len(unpinned) - 5} more" if len(unpinned) > 5 else "")
        + "; a reference is any `uses:` or `image:` value outside the "
        "repository (not starting ./), pinned when it matches the generic "
        "layer's pinned-reference patterns (a full commit SHA, or an image "
        "@sha256 digest)",
    )


def _ci_lockfile_install_missing(view: _PackView) -> _Computed:
    absent = _ci_abstention(view)
    if absent is not None:
        return absent
    tables = view.tables
    lines, files, clipped = _ci_lines(view, tables.ci_files)
    if not files:
        return _no_ci_file("install command")
    if tables.lockfile_install is None:
        return MetricAbstention(reason="no lockfile-install token is declared")
    hits = [
        (path, number)
        for path, number, line in lines
        if tables.lockfile_install.search(line)
    ]
    if not hits and clipped:
        return MetricAbstention(
            reason=(
                "no lockfile-faithful install command was found, but a CI "
                "workflow excerpt was clipped at the line cap ("
                + ", ".join(clipped)
                + "), so it may sit beyond what was read"
            )
        )
    cited = sorted({path for path, _n in hits}) or sorted(files)
    return (
        0 if hits else 1,
        tuple(cited),
        (
            f"{len(hits)} CI line(s) run a lockfile-faithful install: "
            + ", ".join(f"{p}:{n}" for p, n in hits[:5])
            if hits
            else f"no line of {len(files)} quoted CI workflow file(s) runs a "
            "lockfile-faithful install"
        )
        + "; 0 when any does, else 1 (missing); the commands are the "
        "registry's lockfile_install tokens (per language) matched in "
        "non-comment CI lines",
    )


def _ci_provenance_step_missing(view: _PackView) -> _Computed:
    absent = _ci_abstention(view)
    if absent is not None:
        return absent
    tables = view.tables
    ci_lines, ci_files, ci_clipped = _ci_lines(view, tables.ci_files)
    rel_lines, rel_files, rel_clipped = _ci_lines(view, tables.release_files)
    files = [*ci_files, *(f for f in rel_files if f not in ci_files)]
    if not files:
        return MetricAbstention(
            reason=(
                "no CI workflow or release configuration file was quoted in "
                "this pack, so there is nothing to look for an SBOM, signing or "
                "provenance step in (the roles' misses are in sources_missing)"
            )
        )
    if tables.provenance_steps is None:
        return MetricAbstention(reason="no provenance-step token is declared")
    hits = [
        (path, number)
        for path, number, line in (*ci_lines, *rel_lines)
        if tables.provenance_steps.search(line)
    ]
    clipped = [*ci_clipped, *rel_clipped]
    if not hits and clipped:
        return MetricAbstention(
            reason=(
                "no SBOM, signing or provenance step was found, but an excerpt "
                "was clipped at the line cap (" + ", ".join(clipped) + "), so "
                "it may sit beyond what was read"
            )
        )
    cited = sorted({path for path, _n in hits}) or sorted(files)
    return (
        0 if hits else 1,
        tuple(cited),
        (
            f"{len(hits)} line(s) show an SBOM, signing or provenance step: "
            + ", ".join(f"{p}:{n}" for p, n in hits[:5])
            if hits
            else f"no line of {len(files)} quoted CI or release file(s) shows one"
        )
        + "; 0 when any does, else 1 (missing); the tokens are the generic "
        "layer's (slsa, provenance, attest, sbom, cyclonedx, spdx, cosign, "
        "sigstore, syft), matched case-insensitively in non-comment lines",
    )


API = "api"

API_METRICS = (
    "api_spec_missing",
    "api_version_missing",
    "request_validation_missing",
    "breaking_api_changes_observed",
)
"""The T044 api rule metrics (area #7), computed by the ``api`` dimension over
whole files and the changes-scope diff and stored on ``pack.whole_file``."""


def _api_fact(view: _PackView) -> MetricAbstention:
    """Reaching this function means the api dimension did not store the
    metric: another pack, or an unresolved scope."""
    pack = view.pack
    if pack.dimension != API:
        return MetricAbstention(
            reason=(
                "only the api pack records API specification, route, validation "
                f"and versioning facts, and this is the {pack.dimension!r} pack"
            )
        )
    return MetricAbstention(
        reason=(
            f"the {pack.scope} scope could not be resolved, so no API facts "
            "were gathered"
        )
    )


DATA = "data"

DATA_METRICS = (
    "migrations_missing",
    "migrations_without_rollback_share",
    "schema_constraints_missing",
    "destructive_migration_ops_observed",
)
"""The T045 data rule metrics (area #4), computed by the ``data`` dimension
over whole files and stored on ``pack.whole_file``."""


def _data_fact(view: _PackView) -> MetricAbstention:
    """Reaching this function means the data dimension did not store the
    metric: another pack, or an unresolved scope."""
    pack = view.pack
    if pack.dimension != DATA:
        return MetricAbstention(
            reason=(
                "only the data pack records migration, schema and constraint "
                f"facts, and this is the {pack.dimension!r} pack"
            )
        )
    return MetricAbstention(
        reason=(
            f"the {pack.scope} scope could not be resolved, so no data facts "
            "were gathered"
        )
    )


OPERATIONS = "operations"

OPERATIONS_METRICS = (
    "logging_library_missing",
    "audit_log_writes_missing",
    "codeowners_missing",
    "agent_guardrails_missing",
    "agent_config_secrets_observed",
    "tool_version_pin_missing",
    "dev_environment_missing",
)
"""The T046 operations rule metrics (areas #14, #26, #29, #30), computed by
the ``operations`` dimension over whole files and stored on
``pack.whole_file``."""


def _operations_fact(view: _PackView) -> MetricAbstention:
    """Reaching this function means the operations dimension did not store
    the metric: another pack, or an unresolved scope."""
    pack = view.pack
    if pack.dimension != OPERATIONS:
        return MetricAbstention(
            reason=(
                "only the operations pack records ownership, observability, "
                f"agent and setup facts, and this is the {pack.dimension!r} pack"
            )
        )
    return MetricAbstention(
        reason=(
            f"the {pack.scope} scope could not be resolved, so no operations "
            "facts were gathered"
        )
    )


INFRASTRUCTURE = "infrastructure"

INFRASTRUCTURE_METRICS = (
    "iac_wildcard_iam_observed",
    "iac_open_ingress_observed",
    "iac_unencrypted_storage_observed",
    "terraform_locked_remote_state_missing",
    "terraform_environment_separation_missing",
    "database_backup_unconfigured",
    "database_ha_unconfigured",
)
"""The T042 infrastructure rule metrics (areas #11, #23, #24), computed by
the ``infrastructure`` dimension over whole files and stored on
``pack.whole_file``."""


def _infrastructure_fact(view: _PackView) -> MetricAbstention:
    """Reaching this function means the infrastructure dimension did not store
    the metric: another pack, or an unresolved scope."""
    pack = view.pack
    if pack.dimension != INFRASTRUCTURE:
        return MetricAbstention(
            reason=(
                "only the infrastructure pack records IaC facts, and this is "
                f"the {pack.dimension!r} pack"
            )
        )
    return MetricAbstention(
        reason=(
            f"the {pack.scope} scope could not be resolved, so no "
            "infrastructure facts were gathered"
        )
    )


@dataclass(frozen=True)
class MetricDefinition:
    """Declared data, so T020's rules can name a metric without importing its
    implementation."""

    name: str
    family: str
    kind: str
    compute: Callable[[_PackView], _Computed]


PACK_METRICS: dict[str, tuple[str, ...]] = {
    "healthcare": (
        "phi_values_in_test_data_observed",
        "phi_values_in_log_statements_observed",
    ),
    "finance": (
        "float_money_observed",
        "ledger_tables_without_audit_columns_observed",
        "ledger_rows_mutated_observed",
    ),
    "frontend-a11y": (
        "images_without_alt_observed",
        "form_controls_without_label_observed",
        "aria_hidden_focusable_observed",
        "viewport_missing_or_zoom_disabled_observed",
        "browser_support_declaration_missing",
    ),
    # T108: the change-risk dimension owns its metric the same way, so no
    # other dimension's metric list (and no project payload) gains it.
    "change-risk": (
        "bugfix_without_regression_test",
        "new_code_without_test_share",
        "refactor_tests_deleted",
        "refactor_uncovered_share",
    ),
}
"""Metrics of an optional pack (T047), or of the change-risk dimension (T108).
A pack's evidence computes only these, and no other dimension computes them, so
a repository that does not enable the pack serializes exactly as before. The
pack computes them over whole files (``EvidencePack.whole_file``)."""

_PACK_METRIC_NAMES = frozenset(
    name for names in PACK_METRICS.values() for name in names
)


SCOPE_METRICS: dict[str, tuple[str, ...]] = {
    "blast-radius": (
        "high_reach_files_without_test_share",
        "high_reach_churn_hotspot_share",
    ),
}
"""Metrics only their dimension computes, and only at project scope, over the
repository import graph (T114): a pack without the result does not list them,
so a narrow-scope pack serializes exactly as before."""

_SCOPE_METRIC_NAMES = frozenset(
    name for names in SCOPE_METRICS.values() for name in names
)


def _project_scope_only(_view: _PackView) -> _Computed:
    return MetricAbstention(
        reason="computed only by its dimension at project scope, and this pack "
        "holds no such result"
    )


def _pack_only(_view: _PackView) -> _Computed:
    return MetricAbstention(
        reason="computed only by its pack over whole files, and this pack holds "
        "no such result"
    )


METRIC_DEFINITIONS: tuple[MetricDefinition, ...] = (
    MetricDefinition(
        "test_to_source_ratio", FAMILY_TEST_STRENGTH, WHOLE_SET, _test_to_source_ratio
    ),
    MetricDefinition(
        "source_files_without_covering_test",
        FAMILY_TEST_STRENGTH,
        WHOLE_SET,
        _sources_without_covering_test,
    ),
    MetricDefinition(
        "assertion_density_per_test",
        FAMILY_TEST_STRENGTH,
        WHOLE_SET,
        _assertion_density_per_test,
    ),
    MetricDefinition(
        "assertions_observed",
        FAMILY_TEST_STRENGTH,
        EVIDENCE_LOCAL,
        _assertions_observed,
    ),
    MetricDefinition(
        "redaction_hits_observed",
        FAMILY_SECURITY_SURFACE,
        EVIDENCE_LOCAL,
        _redaction_hits_observed,
    ),
    MetricDefinition(
        "redacted_file_share",
        FAMILY_SECURITY_SURFACE,
        WHOLE_SET,
        _redacted_file_share,
    ),
    MetricDefinition(
        "excerpts_observed",
        FAMILY_EVIDENCE_COVERAGE,
        EVIDENCE_LOCAL,
        _excerpts_observed,
    ),
    MetricDefinition(
        "declared_source_coverage",
        FAMILY_EVIDENCE_COVERAGE,
        WHOLE_SET,
        _declared_source_coverage,
    ),
    MetricDefinition(
        "evidence_lines_observed",
        FAMILY_CODE_SHAPE,
        EVIDENCE_LOCAL,
        _evidence_lines_observed,
    ),
    MetricDefinition(
        "mean_excerpt_lines", FAMILY_CODE_SHAPE, WHOLE_SET, _mean_excerpt_lines
    ),
    MetricDefinition(
        "source_file_share", FAMILY_CODE_SHAPE, WHOLE_SET, _source_file_share
    ),
    MetricDefinition(
        "functions_over_ccn_10_share",
        FAMILY_CODE_SHAPE,
        WHOLE_SET,
        _functions_over_ccn_10_share,
    ),
    MetricDefinition(
        "max_function_ccn", FAMILY_CODE_SHAPE, EVIDENCE_LOCAL, _max_function_ccn
    ),
    MetricDefinition(
        "top_level_import_cycles",
        FAMILY_CODE_SHAPE,
        WHOLE_SET,
        _top_level_import_cycles,
    ),
    MetricDefinition(
        "layer_direction_violations",
        FAMILY_CODE_SHAPE,
        WHOLE_SET,
        _layer_direction_violations,
    ),
    MetricDefinition(
        "request_paths", FAMILY_CODE_SHAPE, WHOLE_SET, _request_paths
    ),
    MetricDefinition(
        "max_fan_in_changed", FAMILY_CODE_SHAPE, WHOLE_SET, _max_fan_in_changed
    ),
    MetricDefinition(
        "high_reach_files_without_test_share",
        FAMILY_CODE_SHAPE,
        WHOLE_SET,
        _project_scope_only,
    ),
    MetricDefinition(
        "high_reach_churn_hotspot_share",
        FAMILY_CODE_SHAPE,
        WHOLE_SET,
        _project_scope_only,
    ),
    MetricDefinition(
        "sink_hits_observed",
        FAMILY_SECURITY_SURFACE,
        EVIDENCE_LOCAL,
        _sink_hits_observed,
    ),
    MetricDefinition(
        "source_files_without_covering_test_share",
        FAMILY_TEST_STRENGTH,
        WHOLE_SET,
        _source_files_without_covering_test_share,
    ),
    MetricDefinition(
        "lint_config_missing",
        FAMILY_EVIDENCE_COVERAGE,
        EVIDENCE_LOCAL,
        _role_presence("lint-config"),
    ),
    MetricDefinition(
        "format_config_missing",
        FAMILY_EVIDENCE_COVERAGE,
        EVIDENCE_LOCAL,
        _role_presence("format-config"),
    ),
    MetricDefinition(
        "lockfile_missing",
        FAMILY_EVIDENCE_COVERAGE,
        EVIDENCE_LOCAL,
        _role_presence("lockfile"),
    ),
    MetricDefinition(
        "test_config_and_ci_missing",
        FAMILY_EVIDENCE_COVERAGE,
        EVIDENCE_LOCAL,
        _role_presence("test-config", "ci-workflow"),
    ),
    MetricDefinition(
        "architecture_description_missing",
        FAMILY_EVIDENCE_COVERAGE,
        EVIDENCE_LOCAL,
        _document_rule("architecture-doc"),
    ),
    MetricDefinition(
        "decision_records_missing",
        FAMILY_EVIDENCE_COVERAGE,
        EVIDENCE_LOCAL,
        _document_rule("decision-record"),
    ),
    MetricDefinition(
        "acceptance_criteria_traced_to_code_share",
        FAMILY_EVIDENCE_COVERAGE,
        # checks its own evidence is complete (see its compute function)
        EVIDENCE_LOCAL,
        _ac_traced_share("source"),
    ),
    MetricDefinition(
        "acceptance_criteria_traced_to_test_share",
        FAMILY_EVIDENCE_COVERAGE,
        # checks its own evidence is complete (see its compute function)
        EVIDENCE_LOCAL,
        _ac_traced_share("test"),
    ),
    MetricDefinition(
        "changed_files_in_churn_hotspots_share",
        FAMILY_CODE_SHAPE,
        # checks its own evidence is complete (see its compute function)
        EVIDENCE_LOCAL,
        _changed_files_in_churn_hotspots_share,
    ),
    MetricDefinition(
        "tests_without_assertions_share",
        FAMILY_TEST_STRENGTH,
        WHOLE_SET,
        _tests_without_assertions_share,
    ),
    MetricDefinition(
        "skipped_test_share", FAMILY_TEST_STRENGTH, WHOLE_SET, _skipped_test_share
    ),
    MetricDefinition(
        "network_calls_in_unit_tests_observed",
        FAMILY_TEST_STRENGTH,
        EVIDENCE_LOCAL,
        _network_calls_in_unit_tests_observed,
    ),
    MetricDefinition(
        "type_escapes_per_kloc", FAMILY_CODE_SHAPE, WHOLE_SET, _type_escapes_per_kloc
    ),
    MetricDefinition(
        "todo_without_ticket_share",
        FAMILY_CODE_SHAPE,
        WHOLE_SET,
        _todo_without_ticket_share,
    ),
    # T055: each checks its own evidence is complete (see its compute function)
    MetricDefinition(
        "public_symbols_removed",
        FAMILY_CODE_SHAPE,
        EVIDENCE_LOCAL,
        _compat_count("symbols"),
    ),
    MetricDefinition(
        "destructive_migration_ops",
        FAMILY_CODE_SHAPE,
        EVIDENCE_LOCAL,
        _compat_count("ops"),
    ),
    MetricDefinition(
        "requirements_doc_missing",
        FAMILY_EVIDENCE_COVERAGE,
        EVIDENCE_LOCAL,
        _document_rule("requirements-doc"),
    ),
    MetricDefinition(
        "requirements_docs_count",
        FAMILY_EVIDENCE_COVERAGE,
        EVIDENCE_LOCAL,
        _requirements_docs_count,
    ),
    MetricDefinition(
        "code_commits_with_docs_share",
        FAMILY_EVIDENCE_COVERAGE,
        EVIDENCE_LOCAL,
        _code_commits_with_docs_share,
    ),
    # T075: computed by the requirement-fidelity dimension (whole files)
    MetricDefinition(
        "routes_without_test_share",
        FAMILY_TEST_STRENGTH,
        EVIDENCE_LOCAL,
        _code_fact,
    ),
    MetricDefinition(
        "commits_with_issue_reference_share",
        FAMILY_EVIDENCE_COVERAGE,
        EVIDENCE_LOCAL,
        _code_fact,
    ),
    MetricDefinition(
        "requirement_items_traced_share",
        FAMILY_EVIDENCE_COVERAGE,
        EVIDENCE_LOCAL,
        _code_fact,
    ),
    MetricDefinition(
        "cookie_flags_missing_observed",
        FAMILY_SECURITY_SURFACE,
        EVIDENCE_LOCAL,
        _cookie_flags_missing_observed,
    ),
    MetricDefinition(
        "strict_type_config_missing",
        FAMILY_EVIDENCE_COVERAGE,
        EVIDENCE_LOCAL,
        _strict_type_config_missing,
    ),
    # T043: reliability; computed over whole files by the reliability pack
    *(
        MetricDefinition(
            name, FAMILY_CODE_SHAPE, EVIDENCE_LOCAL, _reliability_count(name)
        )
        for name in _RELIABILITY_RULES
    ),
    # T047: optional packs; computed over whole files by the pack itself
    *(
        MetricDefinition(
            name,
            FAMILY_TEST_STRENGTH if pack == "change-risk" else FAMILY_SECURITY_SURFACE,
            EVIDENCE_LOCAL,
            _pack_only,
        )
        for pack, names in PACK_METRICS.items()
        for name in names
    ),
    MetricDefinition(
        "licence_file_missing",
        FAMILY_EVIDENCE_COVERAGE,
        EVIDENCE_LOCAL,
        _role_presence("licence-file"),
    ),
    MetricDefinition(
        "ci_actions_unpinned_share",
        FAMILY_SECURITY_SURFACE,
        WHOLE_SET,
        _ci_actions_unpinned_share,
    ),
    MetricDefinition(
        "ci_lockfile_install_missing",
        FAMILY_EVIDENCE_COVERAGE,
        WHOLE_SET,
        _ci_lockfile_install_missing,
    ),
    MetricDefinition(
        "ci_provenance_step_missing",
        FAMILY_EVIDENCE_COVERAGE,
        WHOLE_SET,
        _ci_provenance_step_missing,
    ),
    # T044: api; computed over whole files by the api pack itself
    *(
        MetricDefinition(name, FAMILY_EVIDENCE_COVERAGE, EVIDENCE_LOCAL, _api_fact)
        for name in API_METRICS
    ),
    # T045: data; computed over whole files by the data pack itself
    *(
        MetricDefinition(name, FAMILY_EVIDENCE_COVERAGE, EVIDENCE_LOCAL, _data_fact)
        for name in DATA_METRICS
    ),
    # T046: operations; computed over whole files by the operations pack itself
    *(
        MetricDefinition(
            name, FAMILY_EVIDENCE_COVERAGE, EVIDENCE_LOCAL, _operations_fact
        )
        for name in OPERATIONS_METRICS
    ),
    # T042: infrastructure; computed over whole files by its own pack
    *(
        MetricDefinition(
            name, FAMILY_EVIDENCE_COVERAGE, EVIDENCE_LOCAL, _infrastructure_fact
        )
        for name in INFRASTRUCTURE_METRICS
    ),
)

METRIC_NAMES: tuple[str, ...] = tuple(d.name for d in METRIC_DEFINITIONS)


def compute_metrics(
    pack: EvidencePack | CombinedPack, tables: LanguageTables
) -> MetricSet:
    """Compute every declared metric over ``pack``.

    ``tables`` is the registry's language knowledge (:class:`LanguageTables`),
    built by the caller; see ``core/metric_tables.py``.

    Accepts a single :class:`~easy_verifier.core.models.EvidencePack` or the
    :class:`~easy_verifier.core.models.CombinedPack` T012 produces; a combined
    pack yields the same metric names once per dimension that produced a pack,
    in :attr:`CombinedPack.slots` order.

    Raises :class:`MetricCitationError` if any metric cites a reference the
    pack never read -- a bug in this module, never something a caller can
    trigger, and checked rather than trusted because "a metric may never cite
    what the pack did not gather" is FR-027's whole point.
    """
    packs, without = _packs_of(pack)

    metrics: list[Metric] = []
    for dimension, evidence in packs:
        view = _view(evidence, tables)
        truncated, omitted = _truncation_of(evidence)
        allowed = allowed_refs(evidence)
        sample = evidence.sample
        stored = {item.name: item for item in sample.metrics} if sample else {}
        stored |= {item.name: item for item in evidence.whole_file or ()}
        own = PACK_METRICS.get(dimension)
        first = len(metrics)
        for definition in METRIC_DEFINITIONS:
            if (
                definition.name not in own
                if own is not None
                else definition.name in _PACK_METRIC_NAMES
            ):
                continue  # a pack's metrics stay in that pack (T047)
            if definition.name in _SCOPE_METRIC_NAMES and (
                definition.name not in SCOPE_METRICS.get(dimension, ())
                or definition.name not in stored
            ):
                continue  # project-scope only, listed only when computed (T114)
            if definition.name in stored:
                # Computed by the dimension over the whole text of the
                # sample's files (T068) or of every source file at or under
                # the cap (T076), not over the budgeted excerpts, so
                # the FR-027a truncation rule does not describe it.
                computed = _stored(stored[definition.name])
            elif definition.kind == WHOLE_SET and truncated:
                computed: _Computed = MetricAbstention(
                    reason=_TRUNCATED_ABSTENTION.format(omitted=omitted),
                    omitted_lower_bound=omitted,
                )
            else:
                computed = definition.compute(view)

            if isinstance(computed, MetricAbstention):
                outcome: float | int | MetricAbstention = computed
                refs: tuple[str, ...] = ()
                derivation = "no value: " + computed.reason
            else:
                outcome, refs, derivation = computed
            # A whole-file result (T076, the T113 code index) is not a sample.
            whole = {item.name for item in evidence.whole_file or ()}
            if (
                sample is not None
                and definition.name in SAMPLE_METRICS.get(dimension, ())
                and definition.name not in whole
            ):
                derivation += "; " + sample_note(
                    sample, whole_text=definition.name in stored
                )

            metrics.append(
                Metric(
                    name=definition.name,
                    family=definition.family,
                    kind=definition.kind,
                    dimension=dimension,
                    outcome=outcome,
                    computed_from=refs,
                    derivation=derivation,
                )
            )
        check_citations(metrics[first:], allowed)

    return MetricSet(metrics=tuple(metrics), dimensions_without_pack=without)


SAMPLED_METRICS: dict[str, tuple[str, ...]] = {
    "code-quality": (
        "functions_over_ccn_10_share",
        "max_function_ccn",
        "type_escapes_per_kloc",
        "todo_without_ticket_share",
    ),
    "architecture": (
        "top_level_import_cycles",
        "layer_direction_violations",
        "request_paths",
    ),
    "reliability": tuple(_RELIABILITY_RULES),
}
"""Metrics a code tier computes over the whole text of its priority-batch
sample (T068) when it has more sources than its cap: the byte budget would
otherwise truncate the excerpts they read and every whole-set one abstain."""

SAMPLE_METRICS: dict[str, tuple[str, ...]] = {
    "code-quality": (*SAMPLED_METRICS["code-quality"], "source_file_share"),
    "architecture": (*SAMPLED_METRICS["architecture"], "source_file_share"),
    "reliability": (*SAMPLED_METRICS["reliability"], "source_file_share"),
    "test-strategy": (
        "test_to_source_ratio",
        "source_files_without_covering_test",
        "source_files_without_covering_test_share",
        "source_file_share",
    ),
}
"""Metrics whose value depends on which source files a sampled pack read, so
their derivation states the sample (FR-060)."""


def sample_note(sample, *, whole_text: bool = False) -> str:
    """``sample: batches N of M, X of Y files`` (FR-060, AC3)."""
    note = (
        f"sample: batches {sample.batches_done} of {sample.batches_total}, "
        f"{sample.files_read} of {sample.files_in_scope} files"
    )
    if whole_text:
        note += (
            " -- computed over the whole text of those files, not only the "
            "excerpts quoted in this pack"
        )
    return note


def compute_sampled_metrics(
    dimension: str,
    units: Sequence[Excerpt],
    tables: LanguageTables,
    *,
    names: Sequence[str] | None = None,
    files: Sequence[str] = (),
) -> tuple[SampledMetric, ...]:
    """Run this dimension's :data:`SAMPLED_METRICS` over whole-file ``units``.

    Pure, like every function here: the caller (a dimension) read the files
    and passes their text as whole-file excerpts; nothing is kept but the
    result. Refs are mapped from each unit's ``ref`` to its path, which is
    what the pack's ``files_read`` holds. ``names`` replaces the dimension's
    :data:`SAMPLED_METRICS` (the code index's set, T113); ``files`` are extra
    text-less paths in the view (package manifests: project boundaries).
    """
    wanted = SAMPLED_METRICS.get(dimension, ()) if names is None else names
    pack = EvidencePack(
        dimension=dimension,
        mode="",
        scope="",
        files_read=(*(unit.path for unit in units), *files),
        excerpts=tuple(units),
        sources_sought=(),
        sources_found=(),
        sources_missing=(),
        coverage_score=None,
        truncated=False,
    )
    view = _view(pack, tables)
    paths = {unit.ref: unit.path for unit in units}
    results = []
    for definition in METRIC_DEFINITIONS:
        if definition.name not in wanted:
            continue
        computed = definition.compute(view)
        if isinstance(computed, MetricAbstention):
            results.append(
                SampledMetric(definition.name, None, computed.reason, (), "")
            )
        else:
            value, refs, derivation = computed
            cited = tuple(sorted({paths.get(ref, ref) for ref in refs}))
            results.append(
                SampledMetric(definition.name, value, None, cited, derivation)
            )
    return tuple(results)


def _stored(item: SampledMetric) -> _Computed:
    if item.abstention is not None:
        return MetricAbstention(reason=item.abstention)
    return item.value, item.computed_from, item.derivation


def check_citations(metrics: Sequence[Metric], allowed_refs: frozenset[str]) -> None:
    """Enforce AC #7 over already-built metrics.

    Every non-abstaining metric must cite at least one reference, and every
    reference it cites must be a path in ``files_read`` or an
    :attr:`~easy_verifier.core.models.Excerpt.ref` (or path) of an excerpt on
    the same pack. Exposed rather than inlined so the guard can be driven
    directly by a fabricated metric in the test suite -- a guard nothing can
    fail is not a guard.
    """
    for metric in metrics:
        if metric.abstained:
            continue
        if not metric.computed_from:
            raise MetricCitationError(
                f"metric {metric.name!r} ({metric.dimension}) reports a value "
                "but cites no evidence"
            )
        unknown = tuple(ref for ref in metric.computed_from if ref not in allowed_refs)
        if unknown:
            raise MetricCitationError(
                f"metric {metric.name!r} ({metric.dimension}) cites "
                f"{', '.join(unknown)}, which the pack never read"
            )


def allowed_refs(pack: EvidencePack) -> frozenset[str]:
    """Every reference a metric over ``pack`` may legitimately cite: each path
    in ``files_read`` or ``code_index_files`` (T113), and each excerpt's
    ``ref`` and ``path``."""
    refs = set(pack.files_read) | set(pack.code_index_files or ())
    for excerpt in pack.excerpts:
        refs.add(excerpt.ref)
        refs.add(excerpt.path)
    return frozenset(refs)


def _packs_of(
    pack: EvidencePack | CombinedPack,
) -> tuple[tuple[tuple[str, EvidencePack], ...], tuple[tuple[str, str], ...]]:
    if isinstance(pack, CombinedPack):
        packs = tuple(
            (slot.dimension, slot.pack) for slot in pack.slots if slot.pack is not None
        )
        without = tuple(
            (slot.dimension, slot.error or "the dimension produced no pack")
            for slot in pack.slots
            if slot.pack is None
        )
        return packs, without
    return (((pack.dimension, pack),), ())


def _truncation_of(pack: EvidencePack) -> tuple[bool, int]:
    """Whether the byte budget rejected anything, and the lower-bound count.

    Both the flat fields (T001's contract) and the structured
    :class:`~easy_verifier.core.models.TruncationRecord` (T005/FR-011b) are
    consulted, and *either* saying "truncated" is believed. A pack built by a
    caller that predates T005 carries ``truncation=None`` and only the flat
    flag; trusting one field alone would let a truncated pack produce
    whole-set figures.
    """
    record = pack.truncation
    truncated = bool(pack.truncated) or bool(record is not None and record.truncated)
    omitted = max(pack.omitted_count, record.omitted_count if record else 0)
    return truncated, omitted


def _excerpt_lines(excerpt: Excerpt) -> int:
    return max(0, excerpt.end_line - excerpt.start_line + 1)


# ---------------------------------------------------------------------------
# Path classification and source<->test correspondence.
#
# PORTED VERBATIM from `dimensions/test_strategy.py` (T009), which hardened
# all of it: per-ecosystem name conventions, the tests/ directory fallback,
# and -- the part that matters most here -- the project boundary, without
# which `svc_b/tests/test_payments.py` counts as a test of
# `svc_a/src/payments.py` and this module reports a monorepo as covered.
#
# It is duplicated rather than imported because AC #2 forbids this module from
# importing anything that reads the filesystem, and `test_strategy` imports
# `core.context` transitively; and this task's guide forbids editing
# `dimensions/*.py`, so the shared pure helper these two now want cannot be
# extracted here. That is real duplication and it can drift -- recorded as
# residue on T019, to be closed by lifting these predicates into a pure module
# both import.
#
# Since T031 the language tables it used (source suffixes, test names, test
# candidates, the Go same-directory rule) come from the reference registry via
# LanguageTables; the algorithm -- deepest directory segment wins, project
# boundaries -- is unchanged.
#
# Everything below is string work over PurePosixPath. No path is resolved, no
# file is opened, and nothing here touches the filesystem.
# ---------------------------------------------------------------------------

_TEST_DIR_SEGMENTS = frozenset({"test", "tests", "__tests__", "spec", "specs"})

#: Directory segments that mark a **source** root. Not in `test_strategy.py`:
#: added here after Stage 5 `verify` found that name evidence alone classified
#: `src/easy_verifier/dimensions/test_strategy.py` -- production code -- as a
#: test, because its basename matches `test_*.py`. On the real pack that made
#: `source_file_share` publish 0.0 where the truth was 1/17, and made two other
#: metrics abstain claiming "no source file appears in the evidence" while the
#: file sat in `files_read`.
#:
#: The rule: **directory evidence beats name evidence**, and the *deepest*
#: directory segment wins, because it is the most specific statement about the
#: file. `src/pkg/test_helpers.py` is source; `src/pkg/tests/test_real.py` is a
#: test; a file under neither kind of directory falls back to its basename.
#: Nothing here special-cases a literal path.
_SOURCE_DIR_SEGMENTS = frozenset(
    {"app", "cmd", "internal", "lib", "pkg", "source", "sources", "src"}
)

_MANIFEST_NAMES = frozenset(
    {
        "build.gradle",
        "build.gradle.kts",
        "cargo.toml",
        "composer.json",
        "gemfile",
        "go.mod",
        "package.json",
        "pom.xml",
        "pyproject.toml",
        "setup.cfg",
        "setup.py",
    }
)

_LAYOUT_SEGMENTS = frozenset(
    {
        "__tests__",
        "app",
        "cmd",
        "internal",
        "lib",
        "pkg",
        "source",
        "sources",
        "spec",
        "specs",
        "src",
        "test",
        "tests",
    }
)


def _parent(path: str) -> str:
    return PurePosixPath(path).parent.as_posix()


def _is_test_file(path: str, tables: LanguageTables) -> bool:
    """True when ``path`` is a test file under :data:`_CLASSIFIED_BY`'s rule.

    Directory evidence first and deepest-wins, name evidence only as a
    fallback -- see :data:`_SOURCE_DIR_SEGMENTS` for why the order matters.
    Only files with a source suffix can be tests either way, so a fixture
    ``tests/data/sample.json`` is neither test nor source.
    """
    name = PurePosixPath(path).name
    if PurePosixPath(name).suffix not in tables.source_suffixes:
        return False

    # An unambiguous colocated test name (``app.spec.ts``, ``x_test.go``) is a
    # test wherever it sits (T052); only ambiguous names defer to directories.
    if any(pattern.match(name) for pattern in tables.colocated_test_patterns):
        return True

    directory = _directory_evidence(path)
    if directory is not None:
        return directory

    return any(pattern.match(name) for pattern in tables.test_name_patterns)


def _directory_evidence(path: str) -> bool | None:
    """``True`` test / ``False`` source / ``None`` when the path says neither.

    The deepest matching segment wins: it is the most specific claim about the
    file, so ``src/pkg/tests/test_a.py`` is a test and ``tests/fixtures/src/
    thing.py`` is source, without either rule needing to know about the other.
    """
    for part in reversed(PurePosixPath(path).parts[:-1]):
        lowered = part.lower()
        if lowered in _TEST_DIR_SEGMENTS:
            return True
        if lowered in _SOURCE_DIR_SEGMENTS:
            return False
    return None


def _is_source_file(path: str, tables: LanguageTables) -> bool:
    """A file the correspondence rule can be asked about: code, not a test."""
    return PurePosixPath(path).suffix in tables.source_suffixes and not _is_test_file(
        path, tables
    )


def _correspondence(
    files: tuple[str, ...], tests: tuple[str, ...], tables: LanguageTables
) -> tuple[dict[str, tuple[str, ...]], tuple[str, ...]]:
    """Map each source file to its conventionally named, project-local tests."""
    by_name: dict[str, list[str]] = {}
    for test in tests:
        by_name.setdefault(PurePosixPath(test).name, []).append(test)

    boundaries = _manifest_dirs(files)

    matched: dict[str, tuple[str, ...]] = {}
    unmatched: list[str] = []
    for source in files:
        if not _is_source_file(source, tables):
            continue
        source_project = _project_boundary(source, boundaries)
        hits: list[str] = []
        for name, same_directory in expected_test_names(source, tables):
            for test in by_name.get(name, ()):
                if _project_boundary(test, boundaries) != source_project:
                    continue
                if same_directory and _parent(test) != _parent(source):
                    continue
                hits.append(test)
        if hits:
            matched[source] = tuple(sorted(set(hits)))
        else:
            unmatched.append(source)
    return matched, tuple(unmatched)


def _manifest_dirs(files: tuple[str, ...]) -> frozenset[str]:
    return frozenset(
        _parent(path).strip(".")
        for path in files
        if PurePosixPath(path).name.lower() in _MANIFEST_NAMES
    )


def _project_boundary(path: str, manifest_dirs: frozenset[str]) -> str:
    directory = _parent(path).strip(".")
    parts = PurePosixPath(directory).parts if directory else ()

    layout = "/".join(parts)
    for index, part in enumerate(parts):
        if part.lower() in _LAYOUT_SEGMENTS:
            layout = "/".join(parts[:index])
            break

    manifest = ""
    for candidate in manifest_dirs:
        if not _is_ancestor(candidate, directory):
            continue
        if len(candidate) > len(manifest):
            manifest = candidate

    return layout if len(layout) > len(manifest) else manifest


def _is_ancestor(candidate: str, directory: str) -> bool:
    if candidate == "":
        return True
    return directory == candidate or directory.startswith(f"{candidate}/")


def expected_test_names(
    source: str, tables: LanguageTables
) -> tuple[tuple[str, bool], ...]:
    """``(test base name, must share the source's directory)`` per template."""
    name = PurePosixPath(source).name
    stem = PurePosixPath(name).stem
    suffix = PurePosixPath(name).suffix
    values = {"stem": stem, "ext": suffix}
    return tuple(
        (
            _PLACEHOLDER.sub(
                lambda match: values[match[1]], template.removeprefix("./")
            ),
            template.startswith("./"),
        )
        for template in tables.test_candidates.get(suffix, ())
    )


_PLACEHOLDER = re.compile(r"\{(stem|ext)\}")


# ---------------------------------------------------------------------------
# Textual assertion / test-declaration counting.
#
# Textual on purpose: nothing here parses or executes target code (NFR-007).
# The recognised forms are the registry's, listed explicitly per language, so a
# repository using a shape not listed is *under*-counted rather than guessed at
# -- and both metrics that use these say so in their derivation.
# ---------------------------------------------------------------------------


def _count_assertions(text: str, tables: LanguageTables) -> int:
    return len(tables.assertions.findall(text))


def _count_test_functions(text: str, tables: LanguageTables) -> int:
    return sum(len(pattern.findall(text)) for pattern in tables.test_declarations)
