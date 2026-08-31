"""Measured, citable facts computed over an evidence pack (FR-027, FR-027a).

A **metric** is one measured fact about the target, derived *exclusively* from
an :class:`~easy_verifier.core.models.EvidencePack` that a dimension already
produced, and carrying the file references it was computed from. Four things
this module deliberately does **not** do:

* **read anything.** There is no ``open``, no ``Path.read_*``, no
  ``RepoContext`` import, and nothing here reaches the filesystem, a
  subprocess or the network. That is structural, not a convention: the module
  imports only :mod:`dataclasses`, :mod:`json`, :mod:`re`,
  :mod:`pathlib.PurePosixPath` (a pure string type that touches no disk) and
  this package's own plain-data models. A metric that could read a file could
  cite evidence the pack never gathered, which is the whole point of FR-027;
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
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass, field
from pathlib import PurePosixPath

from .models import CombinedPack, EvidencePack, Excerpt

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


def _view(pack: EvidencePack) -> _PackView:
    files = _dedup(pack.files_read)
    return _PackView(
        pack=pack,
        files=files,
        source_files=tuple(path for path in files if _is_source_file(path)),
        test_files=tuple(path for path in files if _is_test_file(path)),
        test_excerpts=tuple(
            excerpt for excerpt in pack.excerpts if _is_test_file(excerpt.path)
        ),
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
                "no source file appears in the evidence, so the ratio has a "
                "zero denominator; that is not the same as a ratio of 0"
            )
        )
    refs = tuple(sorted(set(view.source_files) | set(view.test_files)))
    return (
        len(view.test_files) / len(view.source_files),
        refs,
        f"{len(view.test_files)} test file(s) / {len(view.source_files)} "
        "source file(s), over the deduplicated files_read listed here",
    )


def _sources_without_covering_test(view: _PackView) -> _Computed:
    if not view.source_files:
        return MetricAbstention(
            reason=(
                "no source file appears in the evidence, so there is nothing "
                "whose test correspondence could be checked"
            )
        )
    _matched, unmatched = _correspondence(view.files, view.test_files)
    return (
        len(unmatched),
        tuple(sorted(view.source_files)),
        f"{len(unmatched)} of {len(view.source_files)} source file(s) have no "
        "conventionally named test file in the same project inside this pack: "
        + (", ".join(sorted(unmatched)) or "(none)"),
    )


def _assertion_density_per_test(view: _PackView) -> _Computed:
    if not view.test_excerpts:
        return MetricAbstention(
            reason=(
                "no excerpt from a test file is present in the evidence, so "
                "there is no test body to measure assertions in"
            )
        )
    tests = sum(_count_test_functions(e.text) for e in view.test_excerpts)
    if not tests:
        return MetricAbstention(
            reason=(
                "the test-file excerpts in this pack contain no recognised "
                "test function declaration, so the density has a zero "
                "denominator; that is not the same as a density of 0"
            )
        )
    assertions = sum(_count_assertions(e.text) for e in view.test_excerpts)
    return (
        assertions / tests,
        tuple(sorted(e.ref for e in view.test_excerpts)),
        f"{assertions} assertion(s) / {tests} test function(s), counted "
        "textually in the test-file excerpts listed here",
    )


def _assertions_observed(view: _PackView) -> _Computed:
    if not view.test_excerpts:
        return MetricAbstention(
            reason=(
                "no excerpt from a test file is present in the evidence, so "
                "there is nothing to have observed an assertion in"
            )
        )
    assertions = sum(_count_assertions(e.text) for e in view.test_excerpts)
    return (
        assertions,
        tuple(sorted(e.ref for e in view.test_excerpts)),
        f"{assertions} assertion(s) counted textually in the test-file "
        "excerpts listed here; a lower bound on the repository, since it "
        "counts only what this pack contains",
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
        f"{len(view.source_files)} source file(s) / {len(view.files)} "
        "deduplicated file(s) read, listed here",
    )


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
)

METRIC_NAMES: tuple[str, ...] = tuple(d.name for d in METRIC_DEFINITIONS)


def compute_metrics(pack: EvidencePack | CombinedPack) -> MetricSet:
    """Compute every declared metric over ``pack``.

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
        view = _view(evidence)
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
# Everything below is string work over PurePosixPath. No path is resolved, no
# file is opened, and nothing here touches the filesystem.
# ---------------------------------------------------------------------------

_TEST_DIR_SEGMENTS = frozenset({"test", "tests", "__tests__", "spec", "specs"})

_TEST_NAME_PATTERNS = (
    re.compile(r"^test_.+\.py$"),
    re.compile(r"^.+_test\.py$"),
    re.compile(r"^.+_test\.go$"),
    re.compile(r"^.+_test\.rs$"),
    re.compile(r"^.+_spec\.rb$"),
    re.compile(r"^test_.+\.rb$"),
    re.compile(r"^.+\.(test|spec)\.[cm]?[jt]sx?$"),
    re.compile(r"^.+Test\.java$"),
    re.compile(r"^Test.+\.java$"),
    re.compile(r"^.+Tests?\.cs$"),
)

_SOURCE_SUFFIXES = frozenset(
    {
        ".cs",
        ".go",
        ".java",
        ".js",
        ".jsx",
        ".kt",
        ".php",
        ".py",
        ".rb",
        ".rs",
        ".ts",
        ".tsx",
    }
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


def _is_test_file(path: str) -> bool:
    name = PurePosixPath(path).name
    if any(pattern.match(name) for pattern in _TEST_NAME_PATTERNS):
        return True
    parts = PurePosixPath(path).parts[:-1]
    return any(part.lower() in _TEST_DIR_SEGMENTS for part in parts) and (
        PurePosixPath(name).suffix in _SOURCE_SUFFIXES
    )


def _is_source_file(path: str) -> bool:
    """A file the correspondence rule can be asked about: code, not a test."""
    return PurePosixPath(path).suffix in _SOURCE_SUFFIXES and not _is_test_file(path)


def _correspondence(
    files: tuple[str, ...], tests: tuple[str, ...]
) -> tuple[dict[str, tuple[str, ...]], tuple[str, ...]]:
    """Map each source file to its conventionally named, project-local tests."""
    by_name: dict[str, list[str]] = {}
    for test in tests:
        by_name.setdefault(PurePosixPath(test).name, []).append(test)

    boundaries = _manifest_dirs(files)

    matched: dict[str, tuple[str, ...]] = {}
    unmatched: list[str] = []
    for source in files:
        if not _is_source_file(source):
            continue
        source_project = _project_boundary(source, boundaries)
        hits: list[str] = []
        for name in _expected_test_names(source):
            for test in by_name.get(name, ()):
                if _project_boundary(test, boundaries) != source_project:
                    continue
                if source.endswith(".go") and _parent(test) != _parent(source):
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


def _expected_test_names(source: str) -> tuple[str, ...]:
    name = PurePosixPath(source).name
    stem = PurePosixPath(name).stem
    suffix = PurePosixPath(name).suffix

    if suffix == ".py":
        return (f"test_{stem}.py", f"{stem}_test.py")
    if suffix == ".go":
        return (f"{stem}_test.go",)
    if suffix in {".js", ".jsx", ".ts", ".tsx"}:
        return (
            f"{stem}.test{suffix}",
            f"{stem}.spec{suffix}",
            f"{stem}_test{suffix}",
        )
    if suffix == ".rb":
        return (f"{stem}_spec.rb", f"test_{stem}.rb")
    if suffix == ".java":
        return (f"{stem}Test.java", f"Test{stem}.java")
    if suffix == ".cs":
        return (f"{stem}Test.cs", f"{stem}Tests.cs")
    return ()


# ---------------------------------------------------------------------------
# Textual assertion / test-declaration counting.
#
# Textual on purpose: nothing here parses or executes target code (NFR-007).
# The recognised forms are listed explicitly, so a repository using a shape not
# listed is *under*-counted rather than guessed at -- and both metrics that use
# these say so in their derivation.
# ---------------------------------------------------------------------------

_ASSERTION_PATTERN = re.compile(
    r"(?:\bassert\b"  # python, java, js, rust (assert!)
    r"|\bassert!"
    r"|\bassert_[a-z_]+\b"  # rust assert_eq!, python unittest assert_called
    r"|\bassert[A-Z]\w*"  # junit/xunit assertEquals, assertTrue
    r"|\bexpect\s*\("  # jest, chai
    r"|\.should\b"  # rspec, chai
    r"|\bAssert\.\w+"  # xunit / nunit
    r")"
)

_TEST_DECLARATION_PATTERNS = (
    re.compile(r"^\s*(?:async\s+)?def\s+test\w*\s*\(", re.MULTILINE),
    re.compile(r"^\s*func\s+Test\w*\s*\(", re.MULTILINE),
    re.compile(r"^\s*(?:it|test)\s*\(\s*[\"'`]", re.MULTILINE),
    re.compile(r"^\s*@Test\b", re.MULTILINE),
    re.compile(r"^\s*#\[test\]", re.MULTILINE),
)


def _count_assertions(text: str) -> int:
    return len(_ASSERTION_PATTERN.findall(text))


def _count_test_functions(text: str) -> int:
    return sum(len(pattern.findall(text)) for pattern in _TEST_DECLARATION_PATTERNS)
