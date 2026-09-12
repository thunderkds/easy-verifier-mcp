"""Declared finding rollup and rating/assessment divergence (FR-029/029a).

The calling agent supplies every judgment in the findings. This module only
performs declared arithmetic. It never blends, reconciles, or adjudicates a
rating and an assessment; disagreement remains a separate divergence signal.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

from .findings import CONFIDENCE_DOMAIN, MAX_FINDINGS, SEVERITY_DOMAIN, Finding
from .judge import COVERAGE_FLOORS, Rating, RatingAbstention

SEVERITY_PENALTIES: dict[str, int] = {"low": 5, "medium": 15, "high": 30}
"""Maximum quality-point deduction contributed by one finding."""

CONFIDENCE_MULTIPLIERS: dict[str, int] = {"low": 25, "medium": 60, "high": 100}
"""Percentage of the severity penalty applied for stated confidence."""

DEFAULT_SEVERITY = "medium"
"""Applied only when a finding omitted severity; the use is always disclosed."""

ASSESSMENT_METHOD = (
    "start at 100; subtract round(sum(severity penalty * confidence percentage) "
    "/ 100) once using Python round (ties to even); clamp the result at zero"
)

_ASSESSMENT_ABSENCE_REASONS = {"no_findings": "no findings were submitted"}
_DIVERGENCE_ABSENCE_REASONS = {
    "rating_abstained": "assessment exists but the rating abstained",
    "assessment_absent": "rating exists but no assessment was produced",
    "both_absent": "the rating abstained and no assessment was produced",
}


@dataclass(frozen=True)
class AssessmentInput:
    """One caller finding and its complete declared arithmetic contribution."""

    title: str
    detail: str
    evidence_ref: str
    confidence: str
    suggestion: str | None
    supplied_severity: str | None
    effective_severity: str
    severity_defaulted: bool
    severity_penalty: int
    confidence_multiplier: int
    penalty_numerator: int

    def __post_init__(self) -> None:
        _validate_input(self)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "detail": self.detail,
            "evidence_ref": self.evidence_ref,
            "confidence": self.confidence,
            "suggestion": self.suggestion,
            "supplied_severity": self.supplied_severity,
            "effective_severity": self.effective_severity,
            "severity_defaulted": self.severity_defaulted,
            "severity_penalty": self.severity_penalty,
            "confidence_multiplier": self.confidence_multiplier,
            "penalty_numerator": self.penalty_numerator,
        }


@dataclass(frozen=True)
class Assessment:
    """A 0-100 finding assessment with hand-recomputable provenance."""

    dimension: str
    value: int
    inputs: tuple[AssessmentInput, ...]
    defaulted_severity_count: int
    method: str = ASSESSMENT_METHOD

    def __post_init__(self) -> None:
        _validate_assessment(self)

    @property
    def provenance(self) -> str:
        if not self.defaulted_severity_count:
            return "every finding supplied severity"
        noun = "finding" if self.defaulted_severity_count == 1 else "findings"
        return (
            f"declared default severity {DEFAULT_SEVERITY!r} applied to "
            f"{self.defaulted_severity_count} {noun} that omitted severity"
        )

    def to_dict(self) -> dict:
        return {
            "kind": "assessment",
            "dimension": self.dimension,
            "value": self.value,
            "inputs": [item.to_dict() for item in self.inputs],
            "defaulted_severity_count": self.defaulted_severity_count,
            "provenance": self.provenance,
            "method": self.method,
        }


@dataclass(frozen=True)
class AssessmentAbsence:
    """Distinct absence of assessment; deliberately has no numeric value."""

    dimension: str
    reason_code: str = "no_findings"

    def __post_init__(self) -> None:
        if self.dimension not in COVERAGE_FLOORS:
            raise ValueError(f"unknown assessment dimension {self.dimension!r}")
        if self.reason_code not in _ASSESSMENT_ABSENCE_REASONS:
            raise ValueError(f"unknown assessment absence reason {self.reason_code!r}")

    @property
    def reason(self) -> str:
        return _ASSESSMENT_ABSENCE_REASONS[self.reason_code]

    def to_dict(self) -> dict:
        return {
            "kind": "assessment_absence",
            "dimension": self.dimension,
            "reason_code": self.reason_code,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class AssessmentSet:
    """Exactly one assessment outcome for every declared dimension."""

    outcomes: tuple[Assessment | AssessmentAbsence, ...]

    def __post_init__(self) -> None:
        expected = tuple(COVERAGE_FLOORS)
        if type(self.outcomes) is not tuple or len(self.outcomes) != len(expected):
            raise ValueError("assessment set requires exactly the known dimensions")
        if any(
            type(item) not in (Assessment, AssessmentAbsence) for item in self.outcomes
        ):
            raise ValueError("assessment set contains an invalid outcome type")
        if tuple(item.dimension for item in self.outcomes) != expected:
            raise ValueError("assessment set must use canonical dimension order")
        for item in self.outcomes:
            try:
                replace(item)
            except (AttributeError, TypeError, ValueError) as exc:
                raise ValueError("assessment set contains a malformed outcome") from exc

    def for_dimension(self, dimension: str) -> Assessment | AssessmentAbsence:
        for item in self.outcomes:
            if item.dimension == dimension:
                return item
        raise KeyError(dimension)

    def to_dict(self) -> dict:
        return {"assessments": [item.to_dict() for item in self.outcomes]}

    def serialize(self) -> str:
        return _serialize(self.to_dict())


@dataclass(frozen=True)
class Divergence:
    """Difference with both independent inputs and an explicit direction."""

    dimension: str
    rating_value: int
    assessment_value: int
    signed_gap: int
    absolute_gap: int
    direction: str

    def __post_init__(self) -> None:
        if self.dimension not in COVERAGE_FLOORS:
            raise ValueError(f"unknown divergence dimension {self.dimension!r}")
        _validate_quality_value(self.rating_value, "divergence rating")
        _validate_quality_value(self.assessment_value, "divergence assessment")
        if type(self.signed_gap) is not int or type(self.absolute_gap) is not int:
            raise ValueError("divergence gaps must be integers")
        expected = self.assessment_value - self.rating_value
        if self.signed_gap != expected or self.absolute_gap != abs(expected):
            raise ValueError("divergence gap does not match its two inputs")
        direction = (
            "agent_harsher"
            if expected < 0
            else "rules_harsher"
            if expected > 0
            else "aligned"
        )
        if self.direction != direction:
            raise ValueError("divergence direction does not match its signed gap")

    def to_dict(self) -> dict:
        return {
            "kind": "divergence",
            "dimension": self.dimension,
            "rating_value": self.rating_value,
            "assessment_value": self.assessment_value,
            "signed_gap": self.signed_gap,
            "absolute_gap": self.absolute_gap,
            "direction": self.direction,
            "direction_meaning": "negative means the calling agent is harsher",
        }


@dataclass(frozen=True)
class DivergenceAbsence:
    """Why rating/assessment divergence cannot be computed."""

    dimension: str
    reason_code: str
    rating_abstention: RatingAbstention | None = None
    assessment_absence: AssessmentAbsence | None = None

    def __post_init__(self) -> None:
        if self.dimension not in COVERAGE_FLOORS:
            raise ValueError(f"unknown divergence dimension {self.dimension!r}")
        if self.reason_code not in _DIVERGENCE_ABSENCE_REASONS:
            raise ValueError(f"unknown divergence absence reason {self.reason_code!r}")
        has_rating_absence = type(self.rating_abstention) is RatingAbstention
        has_assessment_absence = type(self.assessment_absence) is AssessmentAbsence
        expected = {
            "rating_abstained": (True, False),
            "assessment_absent": (False, True),
            "both_absent": (True, True),
        }[self.reason_code]
        if (has_rating_absence, has_assessment_absence) != expected:
            raise ValueError("divergence absence provenance contradicts its reason")
        for item in (self.rating_abstention, self.assessment_absence):
            if item is not None and item.dimension != self.dimension:
                raise ValueError("divergence absence dimensions do not match")
            if item is not None:
                replace(item)

    @property
    def reason(self) -> str:
        return _DIVERGENCE_ABSENCE_REASONS[self.reason_code]

    def to_dict(self) -> dict:
        return {
            "kind": "divergence_absence",
            "dimension": self.dimension,
            "reason_code": self.reason_code,
            "reason": self.reason,
            "rating_abstention": (
                self.rating_abstention.to_dict() if self.rating_abstention else None
            ),
            "assessment_absence": (
                self.assessment_absence.to_dict() if self.assessment_absence else None
            ),
        }


@dataclass(frozen=True)
class DimensionComparison:
    """Side-by-side values; never a merged quality number."""

    dimension: str
    rating: Rating | RatingAbstention
    assessment: Assessment | AssessmentAbsence
    divergence: Divergence | DivergenceAbsence

    def __post_init__(self) -> None:
        if type(self.rating) not in (Rating, RatingAbstention):
            raise ValueError("comparison rating has an invalid type")
        if type(self.assessment) not in (Assessment, AssessmentAbsence):
            raise ValueError("comparison assessment has an invalid type")
        if type(self.divergence) not in (Divergence, DivergenceAbsence):
            raise ValueError("comparison divergence has an invalid type")
        for item in (self.rating, self.assessment, self.divergence):
            replace(item)
        if any(
            item.dimension != self.dimension
            for item in (self.rating, self.assessment, self.divergence)
        ):
            raise ValueError("comparison values must name one dimension")
        _validate_comparison(self)

    def to_dict(self) -> dict:
        return {
            "dimension": self.dimension,
            "rating": self.rating.to_dict(),
            "assessment": self.assessment.to_dict(),
            "divergence": self.divergence.to_dict(),
        }


@dataclass(frozen=True)
class ComparisonSet:
    """Canonical seven-dimension side-by-side comparison."""

    comparisons: tuple[DimensionComparison, ...]

    def __post_init__(self) -> None:
        if type(self.comparisons) is not tuple or any(
            type(item) is not DimensionComparison for item in self.comparisons
        ):
            raise ValueError("comparison set must contain DimensionComparison values")
        if tuple(item.dimension for item in self.comparisons) != tuple(COVERAGE_FLOORS):
            raise ValueError(
                "comparison set must use every dimension in canonical order"
            )
        for item in self.comparisons:
            try:
                replace(item)
            except (AttributeError, TypeError, ValueError) as exc:
                raise ValueError(
                    "comparison set contains a malformed comparison"
                ) from exc

    def for_dimension(self, dimension: str) -> DimensionComparison:
        for item in self.comparisons:
            if item.dimension == dimension:
                return item
        raise KeyError(dimension)

    def to_dict(self) -> dict:
        return {"comparisons": [item.to_dict() for item in self.comparisons]}

    def serialize(self) -> str:
        return _serialize(self.to_dict())


def assess(findings_by_dimension: Mapping[str, Sequence[Finding]]) -> AssessmentSet:
    """Compute assessments only from caller judgments, never from ratings."""
    _validate_declared_data()
    if not isinstance(findings_by_dimension, Mapping):
        raise ValueError("findings_by_dimension must be a mapping")
    unknown = set(findings_by_dimension) - set(COVERAGE_FLOORS)
    if unknown:
        raise ValueError(f"unknown dimension(s): {', '.join(sorted(unknown))}")

    outcomes: list[Assessment | AssessmentAbsence] = []
    for dimension in COVERAGE_FLOORS:
        findings = tuple(findings_by_dimension.get(dimension, ()))
        if len(findings) > MAX_FINDINGS:
            raise ValueError(f"{dimension!r} findings exceed the {MAX_FINDINGS} limit")
        if not findings:
            outcomes.append(AssessmentAbsence(dimension))
            continue
        for item in findings:
            _validate_finding(item, dimension)
        ordered = tuple(sorted(findings, key=_finding_key))
        inputs = tuple(_assessment_input(item) for item in ordered)
        deduction = round(sum(item.penalty_numerator for item in inputs) / 100)
        outcomes.append(
            Assessment(
                dimension=dimension,
                value=max(0, 100 - deduction),
                inputs=inputs,
                defaulted_severity_count=sum(
                    item.severity_defaulted for item in inputs
                ),
            )
        )
    return AssessmentSet(tuple(outcomes))


def compare(
    ratings: Sequence[Rating | RatingAbstention], assessments: AssessmentSet
) -> ComparisonSet:
    """Place rating and assessment side by side; never produce a blended value."""
    if len(ratings) != len(COVERAGE_FLOORS):
        raise ValueError("comparison requires exactly the seven rating outcomes")
    if type(assessments) is not AssessmentSet:
        raise ValueError("comparison requires an AssessmentSet")
    by_dimension: dict[str, Rating | RatingAbstention] = {}
    for item in ratings:
        if type(item) not in (Rating, RatingAbstention):
            raise ValueError("comparison accepts only rating outcome types")
        if item.dimension in by_dimension:
            raise ValueError(f"duplicate rating dimension {item.dimension!r}")
        try:
            replace(item)
        except (AttributeError, TypeError, ValueError) as exc:
            raise ValueError("comparison received a malformed rating outcome") from exc
        by_dimension[item.dimension] = item
    if set(by_dimension) != set(COVERAGE_FLOORS):
        raise ValueError("comparison requires exactly the known rating dimensions")

    comparisons = []
    for dimension in COVERAGE_FLOORS:
        rating_outcome = by_dimension[dimension]
        assessment_outcome = assessments.for_dimension(dimension)
        if type(rating_outcome) is Rating and type(assessment_outcome) is Assessment:
            signed = assessment_outcome.value - rating_outcome.value
            divergence: Divergence | DivergenceAbsence = Divergence(
                dimension=dimension,
                rating_value=rating_outcome.value,
                assessment_value=assessment_outcome.value,
                signed_gap=signed,
                absolute_gap=abs(signed),
                direction=(
                    "agent_harsher"
                    if signed < 0
                    else "rules_harsher"
                    if signed > 0
                    else "aligned"
                ),
            )
        elif (
            type(rating_outcome) is RatingAbstention
            and type(assessment_outcome) is Assessment
        ):
            divergence = DivergenceAbsence(
                dimension,
                "rating_abstained",
                rating_abstention=rating_outcome,
            )
        elif (
            type(rating_outcome) is Rating
            and type(assessment_outcome) is AssessmentAbsence
        ):
            divergence = DivergenceAbsence(
                dimension,
                "assessment_absent",
                assessment_absence=assessment_outcome,
            )
        else:
            divergence = DivergenceAbsence(
                dimension,
                "both_absent",
                rating_abstention=rating_outcome,
                assessment_absence=assessment_outcome,
            )
        comparisons.append(
            DimensionComparison(
                dimension, rating_outcome, assessment_outcome, divergence
            )
        )
    return ComparisonSet(tuple(comparisons))


def _assessment_input(finding: Finding) -> AssessmentInput:
    effective = finding.severity or DEFAULT_SEVERITY
    severity_penalty = SEVERITY_PENALTIES[effective]
    confidence_multiplier = CONFIDENCE_MULTIPLIERS[finding.confidence]
    return AssessmentInput(
        title=finding.title,
        detail=finding.detail,
        evidence_ref=finding.evidence_ref,
        confidence=finding.confidence,
        suggestion=finding.suggestion,
        supplied_severity=finding.severity,
        effective_severity=effective,
        severity_defaulted=finding.severity is None,
        severity_penalty=severity_penalty,
        confidence_multiplier=confidence_multiplier,
        penalty_numerator=severity_penalty * confidence_multiplier,
    )


def _finding_key(finding: Finding) -> tuple:
    return (
        finding.title,
        finding.evidence_ref,
        finding.detail,
        finding.confidence,
        finding.severity or "",
        finding.suggestion or "",
    )


def _validate_declared_data() -> None:
    if tuple(SEVERITY_PENALTIES) != SEVERITY_DOMAIN:
        raise ValueError("severity penalty table must match the severity domain")
    if tuple(CONFIDENCE_MULTIPLIERS) != CONFIDENCE_DOMAIN:
        raise ValueError("confidence multiplier table must match the confidence domain")
    if DEFAULT_SEVERITY not in SEVERITY_DOMAIN:
        raise ValueError("default severity must belong to the severity domain")
    if any(
        type(value) is not int or value <= 0 for value in SEVERITY_PENALTIES.values()
    ):
        raise ValueError("severity penalties must be positive integers")
    if any(
        type(value) is not int or not 0 < value <= 100
        for value in CONFIDENCE_MULTIPLIERS.values()
    ):
        raise ValueError("confidence multipliers must be integer percentages")


def _validate_finding(value: object, dimension: str) -> None:
    if type(value) is not Finding:
        raise ValueError("assessment inputs must contain Finding values")
    if value.dimension != dimension:
        raise ValueError(
            f"finding dimension {value.dimension!r} does not match mapping key "
            f"{dimension!r}"
        )
    for field_name in ("title", "detail", "evidence_ref"):
        field_value = getattr(value, field_name)
        if type(field_value) is not str or not field_value:
            raise ValueError(f"finding {field_name} must be a non-empty string")
    if value.confidence not in CONFIDENCE_DOMAIN:
        raise ValueError(f"finding confidence {value.confidence!r} is invalid")
    if value.severity is not None and value.severity not in SEVERITY_DOMAIN:
        raise ValueError(f"finding severity {value.severity!r} is invalid")


def _validate_input(value: AssessmentInput) -> None:
    _validate_declared_data()
    if type(value.title) is not str or not value.title:
        raise ValueError("assessment input title must be non-empty")
    if type(value.detail) is not str or not value.detail:
        raise ValueError("assessment input detail must be non-empty")
    if type(value.evidence_ref) is not str or not value.evidence_ref:
        raise ValueError("assessment input evidence_ref must be non-empty")
    if value.suggestion is not None and type(value.suggestion) is not str:
        raise ValueError("assessment input suggestion must be text when present")
    if value.confidence not in CONFIDENCE_DOMAIN:
        raise ValueError("assessment input confidence is invalid")
    if (
        value.supplied_severity is not None
        and value.supplied_severity not in SEVERITY_DOMAIN
    ):
        raise ValueError("assessment input supplied severity is invalid")
    expected_effective = value.supplied_severity or DEFAULT_SEVERITY
    if value.effective_severity != expected_effective:
        raise ValueError("assessment input effective severity contradicts provenance")
    if value.severity_defaulted is not (value.supplied_severity is None):
        raise ValueError("assessment input default flag contradicts supplied severity")
    if value.severity_penalty != SEVERITY_PENALTIES[expected_effective]:
        raise ValueError("assessment input severity penalty differs from declared data")
    if value.confidence_multiplier != CONFIDENCE_MULTIPLIERS[value.confidence]:
        raise ValueError(
            "assessment input confidence multiplier differs from declared data"
        )
    if value.penalty_numerator != value.severity_penalty * value.confidence_multiplier:
        raise ValueError("assessment input penalty arithmetic is inconsistent")


def _validate_assessment(value: Assessment) -> None:
    _validate_declared_data()
    if value.dimension not in COVERAGE_FLOORS:
        raise ValueError(f"unknown assessment dimension {value.dimension!r}")
    _validate_quality_value(value.value, "assessment value")
    if value.method != ASSESSMENT_METHOD:
        raise ValueError("assessment method must equal the declared arithmetic method")
    if type(value.inputs) is not tuple or not value.inputs:
        raise ValueError("assessment inputs must be a non-empty tuple")
    if any(type(item) is not AssessmentInput for item in value.inputs):
        raise ValueError("assessment inputs must contain AssessmentInput values")
    if tuple(value.inputs) != tuple(sorted(value.inputs, key=_input_key)):
        raise ValueError("assessment inputs must be in canonical order")
    for item in value.inputs:
        _validate_input(item)
    expected_defaulted = sum(item.severity_defaulted for item in value.inputs)
    if (
        type(value.defaulted_severity_count) is not int
        or value.defaulted_severity_count != expected_defaulted
    ):
        raise ValueError("assessment defaulted severity count is inconsistent")
    expected = max(
        0, 100 - round(sum(item.penalty_numerator for item in value.inputs) / 100)
    )
    if value.value != expected:
        raise ValueError("assessment value does not match declared arithmetic")


def _input_key(value: AssessmentInput) -> tuple:
    return (
        value.title,
        value.evidence_ref,
        value.detail,
        value.confidence,
        value.supplied_severity or "",
        value.suggestion or "",
    )


def _validate_comparison(value: DimensionComparison) -> None:
    rating_is_numeric = type(value.rating) is Rating
    assessment_is_numeric = type(value.assessment) is Assessment
    if rating_is_numeric and assessment_is_numeric:
        if type(value.divergence) is not Divergence:
            raise ValueError("numeric rating and assessment require a divergence")
        if (
            value.divergence.rating_value != value.rating.value
            or value.divergence.assessment_value != value.assessment.value
        ):
            raise ValueError("comparison divergence does not match its values")
        return

    if type(value.divergence) is not DivergenceAbsence:
        raise ValueError("an absent input requires a divergence absence")
    if not rating_is_numeric and assessment_is_numeric:
        expected_reason = "rating_abstained"
    elif rating_is_numeric and not assessment_is_numeric:
        expected_reason = "assessment_absent"
    else:
        expected_reason = "both_absent"
    if value.divergence.reason_code != expected_reason:
        raise ValueError("comparison divergence absence reason is inconsistent")
    if value.divergence.rating_abstention != (
        None if rating_is_numeric else value.rating
    ):
        raise ValueError("comparison rating abstention provenance is inconsistent")
    if value.divergence.assessment_absence != (
        None if assessment_is_numeric else value.assessment
    ):
        raise ValueError("comparison assessment absence provenance is inconsistent")


def _validate_quality_value(value: object, label: str) -> None:
    if type(value) is not int or not 0 <= value <= 100:
        raise ValueError(f"{label} must be an integer from 0 to 100")


def _serialize(value: dict) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
