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
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import PurePosixPath

from .models import CombinedPack, EvidencePack, Excerpt
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
        + (", ".join(sorted(unmatched)) or "(none)")
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
    "look, not a proven vulnerability; test-path hits are counted and tagged; "
    "a lower bound on the repository, since only these excerpts were read"
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
    hits: dict[tuple[str, int, str], tuple[str, str]] = {}
    for excerpt in scanned:
        for hit in sink_hits(excerpt.path, excerpt.text, view.tables):
            line = excerpt.start_line + hit.line - 1
            key = (excerpt.path, line, hit.cwe)
            hits.setdefault(key, (excerpt.ref, hit.citation_url))
    cited = sorted({ref for ref, _url in hits.values()}) or sorted(
        {e.ref for e in scanned}
    )
    listed = ", ".join(
        f"{path}:{line} {cwe} ({url})"
        + (" [test path]" if _is_test_file(path, view.tables) else "")
        for (path, line, cwe), (_ref, url) in sorted(hits.items())
    )
    return (
        len(hits),
        tuple(cited),
        f"{len(hits)} dangerous-sink hit(s) in {len(scanned)} excerpt(s): "
        + (listed or "none")
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
        + (", ".join(sorted(unmatched)) or "(none)")
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


_NOT_DERIVABLE = (
    "{what} is not derivable from a read-only evidence pack: {why}; no number "
    "is invented, so this rule's metric abstains"
)


def _not_derivable(what: str, why: str) -> Callable[[_PackView], _Computed]:
    def compute(_view: _PackView) -> _Computed:
        return MetricAbstention(reason=_NOT_DERIVABLE.format(what=what, why=why))

    return compute


_AC_TRACE_WHY = (
    "acceptance criteria are not extracted from requirement documents and no "
    "criterion-to-{target} trace exists in standalone mode (no task, ticket or "
    "trace matrix is read)"
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
    statements = _statements(view, source_only=False)
    if not statements:
        return _no_imports("code-file")
    fan_in: dict[str, list[Excerpt]] = {}
    for target in view.files:
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
    prefix = _common_directory(files)

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
        f"directory shared by the {len(files)} source file(s) quoted here (a file "
        "directly there is its own module); a cycle is a set of two or more "
        "modules each reaching the others, counted once; only the import "
        "statements quoted in this pack are seen; " + _IMPORT_METHOD,
    )


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


@dataclass(frozen=True)
class MetricDefinition:
    """Declared data, so T020's rules can name a metric without importing its
    implementation."""

    name: str
    family: str
    kind: str
    compute: Callable[[_PackView], _Computed]


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
        "max_fan_in_changed", FAMILY_CODE_SHAPE, WHOLE_SET, _max_fan_in_changed
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
        _role_presence("architecture-doc"),
    ),
    MetricDefinition(
        "decision_records_missing",
        FAMILY_EVIDENCE_COVERAGE,
        EVIDENCE_LOCAL,
        _role_presence("decision-record"),
    ),
    MetricDefinition(
        "acceptance_criteria_traced_to_code_share",
        FAMILY_EVIDENCE_COVERAGE,
        # never computed, so its own reason must show even on a truncated pack
        EVIDENCE_LOCAL,
        _not_derivable(
            "the share of acceptance criteria traced to code",
            _AC_TRACE_WHY.format(target="code"),
        ),
    ),
    MetricDefinition(
        "acceptance_criteria_traced_to_test_share",
        FAMILY_EVIDENCE_COVERAGE,
        # never computed, so its own reason must show even on a truncated pack
        EVIDENCE_LOCAL,
        _not_derivable(
            "the share of acceptance criteria traced to a test",
            _AC_TRACE_WHY.format(target="test"),
        ),
    ),
    MetricDefinition(
        "changed_files_in_churn_hotspots_share",
        FAMILY_CODE_SHAPE,
        # never computed, so its own reason must show even on a truncated pack
        EVIDENCE_LOCAL,
        _not_derivable(
            "the share of changed files in the top-10% churn hotspots",
            "the blast-radius pack gathers repository hotspots only at project "
            "scope, where every file is in scope so the share is 10% by "
            "construction, and co-change history (not a hotspot ranking) at "
            "narrower scopes",
        ),
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
        for definition in METRIC_DEFINITIONS:
            if definition.kind == WHOLE_SET and truncated:
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
        check_citations(metrics[-len(METRIC_DEFINITIONS) :], allowed)

    return MetricSet(metrics=tuple(metrics), dimensions_without_pack=without)


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
    in ``files_read``, and each excerpt's ``ref`` and ``path``."""
    refs = set(pack.files_read)
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
