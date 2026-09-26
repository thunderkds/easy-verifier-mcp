"""Declared arithmetic rating rules and typed abstention (FR-028/DDR-0003).

This module consumes metrics and coverage already computed by the core. It
does not gather evidence, read configuration, contact a model, or infer a
verdict. Every floor, threshold, comparison, and weight is inspectable static
data below.

A numeric metric earns its rule's full weight when it meets the threshold and
zero otherwise. Metrics that explicitly abstained are disclosed and excluded
from numerator and denominator. The dimension rating is rounded exactly once
to the nearest integer; if no metric is available, the rating abstains.
"""

from __future__ import annotations

import json
import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from .metrics import Metric, MetricAbstention, MetricSet
from .models import CoverageSummary, SourceMiss


@dataclass(frozen=True)
class CoverageFloor:
    """One inclusive minimum coverage value, declared as data."""

    value: float
    boundary: str


# The sole rating-floor table. Its key set is checked against live dimension
# discovery in tests, so adding a dimension cannot silently omit its floor.
# The checklists contain ecosystem alternatives and pseudo-sources, which is
# why these calibrated minima differ rather than applying a uniform majority.
COVERAGE_FLOORS: dict[str, CoverageFloor] = {
    "architecture": CoverageFloor(0.40, "inclusive"),
    "solution-fit": CoverageFloor(0.50, "inclusive"),
    "requirement-fidelity": CoverageFloor(0.50, "inclusive"),
    "code-quality": CoverageFloor(0.16, "inclusive"),
    "security": CoverageFloor(0.25, "inclusive"),
    "test-strategy": CoverageFloor(0.20, "inclusive"),
    "blast-radius": CoverageFloor(0.25, "inclusive"),
}


@dataclass(frozen=True)
class RatingRule:
    """A binary threshold rule over one existing metric."""

    metric_name: str
    weight: int
    threshold: float
    comparison: str


# Meeting a rule earns its weight; missing it earns zero. Direct test and
# security indicators carry most weight, while evidence-volume indicators
# carry little. The declared weights total 100 when every metric is available.
RATING_RULES: dict[str, RatingRule] = {
    "test_to_source_ratio": RatingRule("test_to_source_ratio", 15, 1.0, "at_least"),
    "source_files_without_covering_test": RatingRule(
        "source_files_without_covering_test", 15, 0.0, "at_most"
    ),
    "assertion_density_per_test": RatingRule(
        "assertion_density_per_test", 10, 1.0, "at_least"
    ),
    "assertions_observed": RatingRule("assertions_observed", 5, 1.0, "at_least"),
    "redaction_hits_observed": RatingRule(
        "redaction_hits_observed", 10, 0.0, "at_most"
    ),
    "redacted_file_share": RatingRule("redacted_file_share", 10, 0.0, "at_most"),
    "excerpts_observed": RatingRule("excerpts_observed", 5, 1.0, "at_least"),
    "declared_source_coverage": RatingRule(
        "declared_source_coverage", 10, 0.60, "at_least"
    ),
    "evidence_lines_observed": RatingRule(
        "evidence_lines_observed", 5, 1.0, "at_least"
    ),
    "mean_excerpt_lines": RatingRule("mean_excerpt_lines", 5, 1.0, "at_least"),
    "source_file_share": RatingRule("source_file_share", 10, 0.10, "at_least"),
}


# Hard gate — evaluate (FR-036, DDR-0006): a rule input whose metric value lies
# within this fraction of its threshold, inclusive, puts its dimension at a
# gate. A threshold of 0 has no relative band, so only exact equality counts.
# Tuning the band is a value change here, never a code change (FR-028).
BORDERLINE_BAND = Decimal("0.10")

# Capped blend (FR-038): w = AGENT_WEIGHT_CAP x confidence, so a gate
# evaluation can move a rules rating at most half of the gap.
AGENT_WEIGHT_CAP = Decimal("0.5")


class RatingAbstained(LookupError):
    """Raised when a consumer asks an abstention for a numeric rating."""


_ABSTENTION_REASONS = {
    "below_coverage_floor": "achieved coverage is below the declared floor",
    "coverage_not_applicable": "the dimension sought no declared source",
    "dimension_failed": "the dimension failed and produced no evidence pack",
    "all_metrics_abstained": "all declared rating metrics abstained",
    "no_dimension_rated": "none of the seven dimensions produced a rating",
}

_RATING_METHOD = (
    "round once to the nearest integer using Python round (ties to even): "
    "100 * sum(earned_weight) / sum(weight) over numeric available rule "
    "metrics; a met threshold earns its full declared weight and an unmet "
    "threshold earns zero"
)

_OVERALL_RATING_METHOD = (
    "round once to the nearest integer using Python round (ties to even): "
    "sum(dimension rating values) / contributor count; abstentions are "
    "excluded from the average"
)


@dataclass(frozen=True)
class RatingInput:
    """One hand-checkable contribution to a dimension rating."""

    metric_name: str
    metric_value: float | int
    weight: int
    threshold: float
    comparison: str
    passed: bool
    earned_weight: int
    computed_from: tuple[str, ...]

    def __post_init__(self) -> None:
        _validate_rating_input(self)

    def to_dict(self) -> dict:
        return {
            "metric_name": self.metric_name,
            "metric_value": self.metric_value,
            "weight": self.weight,
            "threshold": self.threshold,
            "comparison": self.comparison,
            "passed": self.passed,
            "earned_weight": self.earned_weight,
            "computed_from": list(self.computed_from),
        }


@dataclass(frozen=True)
class Rating:
    """A numeric per-dimension rating with every arithmetic input."""

    dimension: str
    value: int
    inputs: tuple[RatingInput, ...]
    unavailable_metrics: tuple[tuple[str, str], ...] = field(default=())
    method: str = _RATING_METHOD

    def __post_init__(self) -> None:
        _validate_rating(self)

    @property
    def numeric_value(self) -> int:
        return self.value

    def to_dict(self) -> dict:
        return {
            "kind": "rating",
            "dimension": self.dimension,
            "value": self.value,
            "inputs": [item.to_dict() for item in self.inputs],
            "unavailable_metrics": [list(item) for item in self.unavailable_metrics],
            "method": self.method,
        }

    def serialize(self) -> str:
        return _serialize(self.to_dict())


@dataclass(frozen=True)
class RatingAbstention:
    """A structured absence of rating; deliberately has no ``value`` field."""

    dimension: str
    reason_code: str
    coverage_floor: float | None = None
    achieved_coverage: float | None = None
    sources_missing: tuple[SourceMiss, ...] = field(default=())
    failure: str | None = None
    unavailable_metrics: tuple[tuple[str, str], ...] = field(default=())
    abstentions: tuple[RatingAbstention, ...] = field(default=())

    def __post_init__(self) -> None:
        _validate_abstention(self)

    @property
    def numeric_value(self) -> int:
        raise RatingAbstained(
            f"rating for {self.dimension!r} abstained: {self.reason_code}"
        )

    @property
    def reason(self) -> str:
        return _ABSTENTION_REASONS[self.reason_code]

    def to_dict(self) -> dict:
        return {
            "kind": "rating_abstention",
            "dimension": self.dimension,
            "reason_code": self.reason_code,
            "reason": self.reason,
            "coverage_floor": self.coverage_floor,
            "achieved_coverage": self.achieved_coverage,
            "sources_missing": [
                {"source": miss.source, "reason": miss.reason}
                for miss in self.sources_missing
            ],
            "failure": self.failure,
            "unavailable_metrics": [list(item) for item in self.unavailable_metrics],
            "abstentions": [item.to_dict() for item in self.abstentions],
        }

    def serialize(self) -> str:
        return _serialize(self.to_dict())


@dataclass(frozen=True)
class GatedRating:
    """A dimension the calling agent contributed to at a hard gate (FR-038).

    Holds the rules result unchanged beside the agent's validated score and
    confidence, so the parts are never separable from the number: blended
    when the rules rated, agent-rated when they abstained. The agent's
    rationale is never stored (FR-039).
    """

    rules: Rating | RatingAbstention
    agent_score: int | float
    confidence: int | float
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        _validate_gated_rating(self)

    @property
    def dimension(self) -> str:
        return self.rules.dimension

    @property
    def is_agent_rated(self) -> bool:
        return type(self.rules) is RatingAbstention

    @property
    def weight(self) -> Decimal:
        return AGENT_WEIGHT_CAP * _decimal(self.confidence)

    @property
    def value(self) -> int:
        if self.is_agent_rated:
            return _round_half_up(_decimal(self.agent_score))
        return blend(self.rules.value, self.agent_score, self.confidence)[0]

    @property
    def numeric_value(self) -> int:
        return self.value

    @property
    def rated_by(self) -> str:
        if self.is_agent_rated:
            return "agent-rated"
        return f"blended (w {_decimal_text(self.weight)})"

    @property
    def parts(self) -> str:
        agent = str(_decimal(self.agent_score))
        if self.is_agent_rated:
            return (
                f"{self.value} = agent {agent} (confidence "
                f"{_decimal(self.confidence)}; rules abstained: "
                f"{self.rules.reason_code})"
            )
        return (
            f"{self.value} = rules {self.rules.value} + agent {agent} "
            f"(w {_decimal_text(self.weight)})"
        )

    def to_dict(self) -> dict:
        return {
            "kind": "agent_rated" if self.is_agent_rated else "blended_rating",
            "dimension": self.dimension,
            "value": self.value,
            "parts": self.parts,
            "rated_by": self.rated_by,
            "agent": {
                "score": self.agent_score,
                "confidence": self.confidence,
                # no weight is applied where the rules abstained: final = A
                "weight": None
                if self.is_agent_rated
                else _decimal_text(self.weight),
                "evidence_refs": list(self.evidence_refs),
            },
            "rules": self.rules.to_dict(),
        }

    def serialize(self) -> str:
        return _serialize(self.to_dict())


@dataclass(frozen=True)
class OverallRating:
    """The contributor-only mean together with its complete boundary."""

    value: int
    contributor_count: int
    total_dimension_count: int
    contributors: tuple[str, ...]
    abstentions: tuple[RatingAbstention, ...]
    contributor_values: tuple[tuple[str, int], ...] = field(default=())
    method: str = _OVERALL_RATING_METHOD
    rated_by: tuple[tuple[str, str], ...] = field(default=())
    """Per contributor: ``rules``, ``blended (w …)`` or ``agent-rated``."""

    def __post_init__(self) -> None:
        _validate_overall_rating(self)

    @property
    def numeric_value(self) -> int:
        return self.value

    @property
    def disclosure(self) -> str:
        abstained = ", ".join(
            f"{item.dimension} ({item.reason_code}: {item.reason})"
            for item in self.abstentions
        )
        suffix = f"; abstained: {abstained}" if abstained else "; none abstained"
        labels = [label for _name, label in self.rated_by]
        rules = labels.count("rules")
        agent = labels.count("agent-rated")
        blended = len(labels) - rules - agent
        return (
            f"{self.contributor_count} of {self.total_dimension_count} dimensions "
            f"contributed ({rules} rule-rated, {blended} blended, {agent} "
            "agent-rated); ratings average contributors only, so abstention can "
            f"raise the overall{suffix}"
        )

    def to_dict(self) -> dict:
        return {
            "kind": "overall_rating",
            "value": self.value,
            "contributor_count": self.contributor_count,
            "total_dimension_count": self.total_dimension_count,
            "contributors": list(self.contributors),
            "contributor_values": [list(item) for item in self.contributor_values],
            "rated_by": [list(item) for item in self.rated_by],
            "abstentions": [item.to_dict() for item in self.abstentions],
            "method": self.method,
            "disclosure": self.disclosure,
        }

    def serialize(self) -> str:
        return _serialize(self.to_dict())


def rate(metrics: MetricSet, coverage: CoverageSummary) -> Rating | RatingAbstention:
    """Rate exactly one dimension represented by ``metrics`` and ``coverage``."""
    _validate_declared_data()
    dimension = _dimension_of(metrics, coverage)
    _validate_single_dimension_coverage(coverage, dimension)
    misses = _misses_for(coverage, dimension)
    failures = tuple(
        error for name, error in metrics.dimensions_without_pack if name == dimension
    )
    if len(failures) > 1:
        raise ValueError(f"duplicate failure entries for dimension {dimension!r}")
    if failures:
        return RatingAbstention(
            dimension=dimension,
            reason_code="dimension_failed",
            sources_missing=misses,
            failure=failures[0],
        )

    floor = COVERAGE_FLOORS.get(dimension)
    if floor is None:
        raise ValueError(f"no coverage floor declared for dimension {dimension!r}")
    achieved = _coverage_for(coverage, dimension)
    if achieved is None:
        return RatingAbstention(
            dimension=dimension,
            reason_code="coverage_not_applicable",
            coverage_floor=floor.value,
            achieved_coverage=None,
            sources_missing=misses,
        )
    _validate_coverage(achieved)
    if achieved < 1.0 and not misses:
        raise ValueError(
            f"coverage for {dimension!r} is below 1.0 but sources_missing is empty"
        )
    if achieved == 1.0 and misses:
        raise ValueError(
            f"coverage for {dimension!r} is 1.0 but sources_missing is not empty"
        )
    if not _meets_floor(achieved, floor):
        return RatingAbstention(
            dimension=dimension,
            reason_code="below_coverage_floor",
            coverage_floor=floor.value,
            achieved_coverage=achieved,
            sources_missing=misses,
        )

    by_name: dict[str, Metric] = {}
    for item in metrics:
        if item.name not in RATING_RULES:
            continue
        if item.name in by_name:
            raise ValueError(
                f"duplicate metric {item.name!r} for dimension {dimension!r}"
            )
        by_name[item.name] = item
    missing = tuple(name for name in RATING_RULES if name not in by_name)
    if missing:
        raise ValueError(
            f"missing declared rating metric(s) for {dimension!r}: {', '.join(missing)}"
        )

    inputs: list[RatingInput] = []
    unavailable: list[tuple[str, str]] = []
    for name, rule in RATING_RULES.items():
        item = by_name[name]
        if isinstance(item.outcome, MetricAbstention):
            unavailable.append((name, item.outcome.reason))
            continue
        _validate_finite_number(item.outcome, f"metric {name!r} outcome")
        passed = _passes(item.outcome, rule)
        inputs.append(
            RatingInput(
                metric_name=name,
                metric_value=item.outcome,
                weight=rule.weight,
                threshold=rule.threshold,
                comparison=rule.comparison,
                passed=passed,
                earned_weight=rule.weight if passed else 0,
                computed_from=item.computed_from,
            )
        )

    if not inputs:
        return RatingAbstention(
            dimension=dimension,
            reason_code="all_metrics_abstained",
            coverage_floor=floor.value,
            achieved_coverage=achieved,
            sources_missing=misses,
            unavailable_metrics=tuple(unavailable),
        )

    earned = sum(item.earned_weight for item in inputs)
    available = sum(item.weight for item in inputs)
    return Rating(
        dimension=dimension,
        value=round(100 * earned / available),
        inputs=tuple(inputs),
        unavailable_metrics=tuple(unavailable),
    )


def within_band(value: float | int, threshold: float | int) -> bool:
    """True if ``value`` lies within ``BORDERLINE_BAND`` of ``threshold``,
    inclusive (FR-036). Decimal over the shortest float text, so ``1.1`` is
    exactly 10% from ``1.0`` rather than a binary hair beyond it."""
    gap = abs(_decimal(value) - _decimal(threshold))
    return gap <= BORDERLINE_BAND * abs(_decimal(threshold))


def blend(
    rules: int, agent: int | float, confidence: int | float
) -> tuple[int, Decimal]:
    """Capped blend (FR-038): ``(final, w)`` with ``w = 0.5 x confidence`` and
    ``final = R(1-w) + Aw`` rounded half up once and clamped to 0-100."""
    weight = AGENT_WEIGHT_CAP * _decimal(confidence)
    final = _decimal(rules) * (1 - weight) + _decimal(agent) * weight
    return _round_half_up(final), weight


def _decimal(value: float | int) -> Decimal:
    return Decimal(str(value))


def _round_half_up(value: Decimal) -> int:
    return min(100, max(0, int(value.quantize(Decimal(1), rounding=ROUND_HALF_UP))))


def _decimal_text(value: Decimal) -> str:
    """Two places for the common case (``0.30``), exact digits otherwise, so a
    displayed weight is never a rounded stand-in for the one applied."""
    hundredths = value.quantize(Decimal("0.01"))
    return format(hundredths if hundredths == value else value.normalize(), "f")


def _validate_gated_rating(value: GatedRating) -> None:
    if type(value.rules) is Rating:
        _revalidate_rating(value.rules)
    elif type(value.rules) is RatingAbstention:
        _revalidate_abstention(value.rules)
        if value.rules.reason_code == "no_dimension_rated":
            raise ValueError("a gated rating cannot wrap the overall abstention")
    else:
        raise ValueError("gated rating rules must be a Rating or RatingAbstention")
    _validate_finite_number(value.agent_score, "gated rating agent_score")
    if not 0 <= value.agent_score <= 100:
        raise ValueError("gated rating agent_score must be between 0 and 100")
    _validate_unit_number(value.confidence, "gated rating confidence")
    if (
        type(value.evidence_refs) is not tuple
        or not value.evidence_refs
        or any(type(ref) is not str or not ref for ref in value.evidence_refs)
    ):
        raise ValueError("gated rating evidence_refs must be non-empty strings")


def _rated_by(item: Rating | GatedRating) -> str:
    return item.rated_by if type(item) is GatedRating else "rules"


def rate_overall(
    ratings: Sequence[Rating | RatingAbstention | GatedRating],
) -> OverallRating | RatingAbstention:
    """Average exactly seven unique dimension results, raters only.

    A :class:`GatedRating` contributes its blended or agent-rated value; the
    disclosure counts each kind (FR-038)."""
    _validate_declared_data()
    expected = tuple(COVERAGE_FLOORS)
    if len(ratings) != len(expected):
        raise ValueError("rate_overall requires exactly the seven known dimensions")

    invalid_types = tuple(
        index
        for index, item in enumerate(ratings)
        if type(item) not in (Rating, RatingAbstention, GatedRating)
    )
    if invalid_types:
        raise ValueError(
            "rate_overall accepts exactly Rating, RatingAbstention or GatedRating "
            f"values; invalid item index(es): {', '.join(map(str, invalid_types))}"
        )

    for item in ratings:
        if type(item) is Rating:
            _revalidate_rating(item)
        elif type(item) is GatedRating:
            _validate_gated_rating(item)
        else:
            _revalidate_abstention(item)

    names = tuple(item.dimension for item in ratings)
    unknown = tuple(name for name in names if name not in COVERAGE_FLOORS)
    if unknown:
        raise ValueError(f"unknown rating dimension(s): {', '.join(unknown)}")
    duplicates = tuple(name for name in expected if names.count(name) > 1)
    if duplicates:
        raise ValueError(f"duplicate rating dimension(s): {', '.join(duplicates)}")
    if set(names) != set(expected):
        raise ValueError("rate_overall requires exactly the seven known dimensions")

    by_dimension = {item.dimension: item for item in ratings}
    ordered = tuple(by_dimension[name] for name in expected)
    contributors = tuple(
        item for item in ordered if type(item) in (Rating, GatedRating)
    )
    abstentions = tuple(item for item in ordered if type(item) is RatingAbstention)
    if not contributors:
        return RatingAbstention(
            dimension="overall",
            reason_code="no_dimension_rated",
            abstentions=abstentions,
        )

    return OverallRating(
        value=round(sum(item.value for item in contributors) / len(contributors)),
        contributor_count=len(contributors),
        total_dimension_count=len(expected),
        contributors=tuple(item.dimension for item in contributors),
        abstentions=abstentions,
        contributor_values=tuple((item.dimension, item.value) for item in contributors),
        rated_by=tuple((item.dimension, _rated_by(item)) for item in contributors),
    )


def _dimension_of(metrics: MetricSet, coverage: CoverageSummary) -> str:
    names = {item.dimension for item in metrics}
    names.update(name for name, _error in metrics.dimensions_without_pack)
    if not names:
        names.update(name for name, _score in coverage.per_dimension)
    if len(names) != 1:
        raise ValueError("rate requires metrics for exactly one dimension")
    return names.pop()


def _coverage_for(coverage: CoverageSummary, dimension: str) -> float | None:
    matches = tuple(
        score for name, score in coverage.per_dimension if name == dimension
    )
    if len(matches) != 1:
        raise ValueError(f"coverage must contain exactly one entry for {dimension!r}")
    return matches[0]


def _validate_single_dimension_coverage(
    coverage: CoverageSummary, dimension: str
) -> None:
    if len(coverage.per_dimension) != 1 or len(coverage.misses) != 1:
        raise ValueError("coverage must describe exactly one single dimension")
    coverage_dimension, achieved = coverage.per_dimension[0]
    misses_dimension, _misses = coverage.misses[0]
    if coverage_dimension != dimension or misses_dimension != dimension:
        raise ValueError(
            f"coverage entries must both name rated dimension {dimension!r}"
        )
    if coverage.combined != achieved:
        raise ValueError(
            "combined coverage must equal the sole per-dimension coverage value"
        )


def _misses_for(coverage: CoverageSummary, dimension: str) -> tuple[SourceMiss, ...]:
    matches = tuple(misses for name, misses in coverage.misses if name == dimension)
    if len(matches) != 1:
        raise ValueError(
            f"coverage must contain exactly one miss list for {dimension!r}"
        )
    return matches[0]


def _meets_floor(achieved: float, floor: CoverageFloor) -> bool:
    if floor.boundary == "inclusive":
        return achieved >= floor.value
    raise ValueError(f"unknown coverage-floor boundary {floor.boundary!r}")


def _passes(value: float | int, rule: RatingRule) -> bool:
    if rule.comparison == "at_least":
        return value >= rule.threshold
    if rule.comparison == "at_most":
        return value <= rule.threshold
    raise ValueError(f"unknown rating comparison {rule.comparison!r}")


def _validate_declared_data() -> None:
    for name, floor in COVERAGE_FLOORS.items():
        if type(floor) is not CoverageFloor:
            raise ValueError(f"coverage floor for {name!r} is not CoverageFloor data")
        _validate_unit_number(floor.value, f"coverage floor for {name!r}")
        if floor.boundary != "inclusive":
            raise ValueError(
                f"coverage floor for {name!r} has unsupported boundary "
                f"{floor.boundary!r}"
            )

    for key, rule in RATING_RULES.items():
        if type(rule) is not RatingRule:
            raise ValueError(f"rating rule {key!r} is not RatingRule data")
        if key != rule.metric_name:
            raise ValueError(
                f"rating rule key {key!r} does not equal metric_name "
                f"{rule.metric_name!r}"
            )
        if type(rule.weight) is not int or rule.weight <= 0:
            raise ValueError(f"rating rule {key!r} weight must be a positive integer")
        _validate_finite_number(rule.threshold, f"rating rule {key!r} threshold")
        if rule.comparison not in {"at_least", "at_most"}:
            raise ValueError(
                f"rating rule {key!r} comparison must be at_least or at_most"
            )


def _validate_abstention(value: RatingAbstention) -> None:
    if value.reason_code not in _ABSTENTION_REASONS:
        raise ValueError(f"unknown rating abstention reason_code {value.reason_code!r}")

    if value.reason_code != "no_dimension_rated":
        _validate_leaf_abstention_dimension(value)
    _validate_source_misses(value.sources_missing)
    unavailable_names = _validate_unavailable_metrics(
        value.unavailable_metrics, "abstention"
    )
    if type(value.abstentions) is not tuple:
        raise ValueError("rating abstention abstentions must be a tuple")
    if value.failure is not None and (
        type(value.failure) is not str or not value.failure.strip()
    ):
        raise ValueError("rating abstention failure must be a non-empty string")
    if value.coverage_floor is not None:
        _validate_unit_number(value.coverage_floor, "abstention coverage_floor")
        if value.reason_code != "no_dimension_rated":
            declared_floor = COVERAGE_FLOORS[value.dimension].value
            if value.coverage_floor != declared_floor:
                raise ValueError(
                    "abstention coverage_floor must equal declared floor "
                    f"{declared_floor} for dimension {value.dimension!r}"
                )
    if value.achieved_coverage is not None:
        _validate_unit_number(value.achieved_coverage, "abstention achieved_coverage")

    if value.reason_code == "below_coverage_floor":
        if value.coverage_floor is None or value.achieved_coverage is None:
            raise ValueError(
                "below_coverage_floor requires coverage_floor and achieved_coverage"
            )
        if value.achieved_coverage >= value.coverage_floor:
            raise ValueError(
                "below_coverage_floor requires achieved_coverage below coverage_floor"
            )
        if not value.sources_missing:
            raise ValueError("below_coverage_floor requires non-empty sources_missing")
        if value.failure is not None or unavailable_names or value.abstentions:
            raise ValueError(
                "below_coverage_floor only carries coverage provenance and misses"
            )
    elif value.reason_code == "coverage_not_applicable":
        if (
            value.coverage_floor is None
            or value.achieved_coverage is not None
            or value.sources_missing
            or value.failure is not None
            or unavailable_names
            or value.abstentions
        ):
            raise ValueError(
                "coverage_not_applicable requires a floor, no achieved coverage, "
                "and no other provenance fields"
            )
    elif value.reason_code == "dimension_failed":
        if (
            value.failure is None
            or value.coverage_floor is not None
            or value.achieved_coverage is not None
            or unavailable_names
            or value.abstentions
        ):
            raise ValueError(
                "dimension_failed requires a failure and only permits named misses"
            )
    elif value.reason_code == "all_metrics_abstained":
        if (
            value.coverage_floor is None
            or value.achieved_coverage is None
            or value.achieved_coverage < value.coverage_floor
            or unavailable_names != tuple(RATING_RULES)
            or value.failure is not None
            or value.abstentions
        ):
            raise ValueError(
                "all_metrics_abstained requires coverage provenance and "
                "all unavailable metrics, with no failure or nested abstentions"
            )
        _validate_miss_coverage_coherence(value)
    else:
        nested_are_abstentions = True
        for item in value.abstentions:
            if (
                type(item) is not RatingAbstention
                or getattr(item, "reason_code", None) == "no_dimension_rated"
            ):
                nested_are_abstentions = False
                break
            _revalidate_abstention(item)
        nested_names = (
            tuple(item.dimension for item in value.abstentions)
            if nested_are_abstentions
            else ()
        )
        complete = (
            value.dimension == "overall"
            and len(value.abstentions) == len(COVERAGE_FLOORS)
            and nested_are_abstentions
            and nested_names == tuple(COVERAGE_FLOORS)
            and value.coverage_floor is None
            and value.achieved_coverage is None
            and not value.sources_missing
            and value.failure is None
            and not unavailable_names
        )
        if not complete:
            raise ValueError(
                "no_dimension_rated requires dimension 'overall' and all seven "
                "abstentions in canonical order, with no leaf provenance fields"
            )


def _validate_leaf_abstention_dimension(value: RatingAbstention) -> None:
    if value.dimension not in COVERAGE_FLOORS:
        raise ValueError(
            f"unknown dimension for rating abstention: {value.dimension!r}"
        )


def _validate_source_misses(value: object) -> None:
    if type(value) is not tuple:
        raise ValueError("rating abstention sources_missing must be a tuple")
    for miss in value:
        if (
            type(miss) is not SourceMiss
            or type(miss.source) is not str
            or not miss.source.strip()
            or type(miss.reason) is not str
            or not miss.reason.strip()
        ):
            raise ValueError(
                "rating abstention sources_missing must contain SourceMiss values "
                "with non-empty source and reason strings"
            )


def _validate_unavailable_metrics(value: object, label: str) -> tuple[str, ...]:
    if type(value) is not tuple:
        raise ValueError(f"{label} unavailable_metrics must be a tuple")
    names: list[str] = []
    for entry in value:
        if (
            type(entry) is not tuple
            or len(entry) != 2
            or type(entry[0]) is not str
            or not entry[0].strip()
            or type(entry[1]) is not str
            or not entry[1].strip()
        ):
            raise ValueError(
                f"{label} unavailable_metrics entries must be metric/reason "
                "string pairs"
            )
        names.append(entry[0])
    if len(set(names)) != len(names):
        raise ValueError(f"{label} unavailable_metrics contain duplicate metric names")
    known_order = tuple(name for name in RATING_RULES if name in names)
    if tuple(names) != known_order:
        raise ValueError(
            f"{label} unavailable_metrics are not in canonical declared-rule order"
        )
    return tuple(names)


def _validate_miss_coverage_coherence(value: RatingAbstention) -> None:
    assert value.achieved_coverage is not None
    if value.achieved_coverage < 1.0 and not value.sources_missing:
        raise ValueError(
            f"{value.reason_code} coverage below 1.0 requires sources_missing"
        )
    if value.achieved_coverage == 1.0 and value.sources_missing:
        raise ValueError(
            f"{value.reason_code} coverage 1.0 requires no sources_missing"
        )


def _validate_rating_input(value: RatingInput) -> None:
    if type(value.metric_name) is not str or not value.metric_name.strip():
        raise ValueError("rating input metric_name must be a non-empty string")
    rule = RATING_RULES.get(value.metric_name)
    if rule is None:
        raise ValueError(f"rating input names unknown metric {value.metric_name!r}")
    _validate_finite_number(value.metric_value, "rating input metric_value")
    if type(value.weight) is not int or value.weight <= 0:
        raise ValueError("rating input weight must be a positive integer")
    _validate_finite_number(value.threshold, "rating input threshold")
    if value.comparison not in {"at_least", "at_most"}:
        raise ValueError("rating input comparison must be at_least or at_most")
    if (
        value.weight != rule.weight
        or value.threshold != rule.threshold
        or value.comparison != rule.comparison
    ):
        raise ValueError(
            f"rating input for {value.metric_name!r} does not match its declared rule"
        )
    if type(value.passed) is not bool:
        raise ValueError("rating input passed must be a boolean")
    expected_earned = value.weight if value.passed else 0
    if type(value.earned_weight) is not int or value.earned_weight != expected_earned:
        raise ValueError(
            "rating input earned_weight must equal weight when passed, else zero"
        )
    expected_passed = (
        value.metric_value >= value.threshold
        if value.comparison == "at_least"
        else value.metric_value <= value.threshold
    )
    if value.passed is not expected_passed:
        raise ValueError("rating input passed does not match its declared comparison")
    if (
        type(value.computed_from) is not tuple
        or not value.computed_from
        or any(type(ref) is not str or not ref.strip() for ref in value.computed_from)
    ):
        raise ValueError(
            "rating input computed_from must contain non-empty reference strings"
        )


def _validate_rating(value: Rating) -> None:
    _validate_declared_data()
    _validate_rating_value(value.value, "rating value")
    if value.dimension not in COVERAGE_FLOORS:
        raise ValueError(f"unknown dimension for rating: {value.dimension!r}")
    if value.method != _RATING_METHOD:
        raise ValueError("rating method must equal the declared arithmetic method")
    if type(value.inputs) is not tuple or not value.inputs:
        raise ValueError("rating inputs must be a non-empty tuple")
    if any(type(item) is not RatingInput for item in value.inputs):
        raise ValueError("rating inputs must contain exactly RatingInput values")

    input_names = tuple(item.metric_name for item in value.inputs)
    if len(set(input_names)) != len(input_names):
        raise ValueError("rating inputs contain duplicate metric names")
    expected_input_order = tuple(name for name in RATING_RULES if name in input_names)
    if input_names != expected_input_order:
        raise ValueError("rating inputs are not in canonical declared-rule order")
    for item in value.inputs:
        _validate_rating_input(item)
        rule = RATING_RULES.get(item.metric_name)
        if rule is None:
            raise ValueError(f"rating input names unknown metric {item.metric_name!r}")
        if (
            item.weight != rule.weight
            or item.threshold != rule.threshold
            or item.comparison != rule.comparison
        ):
            raise ValueError(
                f"rating input for {item.metric_name!r} does not match its "
                "declared rule"
            )

    unavailable_names = _validate_unavailable_metrics(
        value.unavailable_metrics, "rating"
    )
    overlap = set(input_names) & set(unavailable_names)
    if overlap:
        raise ValueError(
            "rating input and unavailable metric names overlap: "
            f"{', '.join(sorted(overlap))}"
        )
    partition = set(input_names) | set(unavailable_names)
    if partition != set(RATING_RULES):
        raise ValueError(
            "rating inputs and unavailable metrics must partition all rules"
        )

    expected = round(
        100
        * sum(item.earned_weight for item in value.inputs)
        / sum(item.weight for item in value.inputs)
    )
    if value.value != expected:
        raise ValueError(
            f"rating value {value.value} does not match declared arithmetic {expected}"
        )


def _validate_overall_rating(value: OverallRating) -> None:
    _validate_declared_data()
    _validate_rating_value(value.value, "overall rating value")
    if value.method != _OVERALL_RATING_METHOD:
        raise ValueError(
            "overall rating method must equal the declared arithmetic method"
        )
    if type(value.contributor_count) is not int or value.contributor_count != len(
        value.contributor_values
    ):
        raise ValueError("overall contributor_count does not match contributor_values")
    if type(
        value.total_dimension_count
    ) is not int or value.total_dimension_count != len(COVERAGE_FLOORS):
        raise ValueError("overall total_dimension_count must equal known dimensions")
    if type(value.contributors) is not tuple or not value.contributors:
        raise ValueError("overall contributors must be a non-empty tuple")
    if type(value.contributor_values) is not tuple or any(
        type(entry) is not tuple
        or len(entry) != 2
        or type(entry[0]) is not str
        or type(entry[1]) is not int
        or not 0 <= entry[1] <= 100
        for entry in value.contributor_values
    ):
        raise ValueError("overall contributor_values must be dimension/integer pairs")
    value_names = tuple(name for name, _rating in value.contributor_values)
    if value.contributors != value_names:
        raise ValueError("overall contributors do not match contributor_values")
    if (
        type(value.rated_by) is not tuple
        or tuple(entry[0] for entry in value.rated_by) != value_names
        or any(
            type(label) is not str
            or not (
                label in ("rules", "agent-rated") or label.startswith("blended (w ")
            )
            for _name, label in value.rated_by
        )
    ):
        raise ValueError(
            "overall rated_by must label every contributor rules, blended, "
            "or agent-rated"
        )
    if type(value.abstentions) is not tuple:
        raise ValueError("overall abstentions must be a tuple")
    for item in value.abstentions:
        if type(item) is not RatingAbstention:
            raise ValueError("overall abstentions must contain RatingAbstention values")
        _revalidate_abstention(item)
        if item.reason_code == "no_dimension_rated":
            raise ValueError("an OverallRating cannot contain an overall abstention")

    abstained_names = tuple(item.dimension for item in value.abstentions)
    names = value_names + abstained_names
    if len(set(names)) != len(names) or set(names) != set(COVERAGE_FLOORS):
        raise ValueError(
            "overall contributors and abstentions must partition known dimensions"
        )
    expected_order = tuple(name for name in COVERAGE_FLOORS if name in value_names)
    if value_names != expected_order:
        raise ValueError("overall contributors are not in canonical dimension order")
    expected_abstention_order = tuple(
        name for name in COVERAGE_FLOORS if name in abstained_names
    )
    if abstained_names != expected_abstention_order:
        raise ValueError("overall abstentions are not in canonical dimension order")
    expected = round(
        sum(rating for _name, rating in value.contributor_values)
        / len(value.contributor_values)
    )
    if value.value != expected:
        raise ValueError(
            f"overall value {value.value} does not match contributor "
            f"arithmetic {expected}"
        )


def _revalidate_rating(value: Rating) -> None:
    try:
        _validate_rating(value)
    except (AttributeError, TypeError) as exc:
        raise ValueError("malformed Rating value") from exc


def _revalidate_abstention(value: RatingAbstention) -> None:
    try:
        _validate_abstention(value)
    except (AttributeError, TypeError, KeyError) as exc:
        raise ValueError("malformed RatingAbstention value") from exc


def _validate_rating_value(value: object, label: str) -> None:
    if type(value) is not int or not 0 <= value <= 100:
        raise ValueError(f"{label} must be an integer from 0 through 100")


def _validate_finite_number(value: object, label: str) -> None:
    if type(value) is int:
        return
    if type(value) is not float or not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number")


def _validate_unit_number(value: object, label: str) -> None:
    _validate_finite_number(value, label)
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{label} must be between 0.0 and 1.0 inclusive")


def _validate_coverage(value: object) -> None:
    _validate_unit_number(value, "coverage")


def _serialize(value: dict) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=True,
        separators=(",", ":"),
        allow_nan=False,
    )
