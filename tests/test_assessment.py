"""T021 acceptance tests for finding assessments and divergence."""

from __future__ import annotations

import ast
from dataclasses import replace
from pathlib import Path

import pytest

from easy_verifier.core.assessment import (
    ASSESSMENT_METHOD,
    CONFIDENCE_MULTIPLIERS,
    DEFAULT_SEVERITY,
    SEVERITY_PENALTIES,
    Assessment,
    AssessmentAbsence,
    Divergence,
    DivergenceAbsence,
    assess,
    compare,
)
from easy_verifier.core.findings import MAX_FINDINGS, Finding
from easy_verifier.core.judge import (
    COVERAGE_FLOORS,
    RATING_RULES,
    Rating,
    RatingAbstention,
    RatingInput,
)

DIMENSIONS = tuple(COVERAGE_FLOORS)


def finding(
    dimension: str = "security",
    *,
    title: str = "Finding",
    confidence: str = "high",
    severity: str | None = "medium",
) -> Finding:
    return Finding(
        dimension=dimension,
        title=title,
        detail=f"Detail for {title}",
        evidence_ref=f"{dimension}.py:1-1",
        confidence=confidence,
        severity=severity,
    )


def rating(dimension: str, value: int = 100) -> Rating:
    passed_count = round(value * len(RATING_RULES) / 100)
    inputs = []
    for index, (name, rule) in enumerate(RATING_RULES.items()):
        passed = index < passed_count
        metric_value = (
            rule.threshold
            if passed
            else (
                rule.threshold - 1
                if rule.comparison == "at_least"
                else rule.threshold + 1
            )
        )
        inputs.append(
            RatingInput(
                metric_name=name,
                metric_value=metric_value,
                weight=rule.weight,
                threshold=rule.threshold,
                comparison=rule.comparison,
                passed=passed,
                earned_weight=rule.weight if passed else 0,
                computed_from=(f"{dimension}.py:1-1",),
            )
        )
    computed = round(
        100
        * sum(item.earned_weight for item in inputs)
        / sum(item.weight for item in inputs)
    )
    return Rating(dimension=dimension, value=computed, inputs=tuple(inputs))


def ratings(*, abstain: str | None = None):
    return tuple(
        RatingAbstention(
            dimension=name,
            reason_code="dimension_failed",
            failure="collector failed",
        )
        if name == abstain
        else rating(name)
        for name in DIMENSIONS
    )


def test_assessment_is_recomputable_from_declared_weights():
    findings = (
        finding(title="High", severity="high", confidence="high"),
        finding(title="Low high confidence", severity="low", confidence="high"),
        finding(title="Low low confidence", severity="low", confidence="low"),
    )
    outcome = assess({"security": findings}).for_dimension("security")
    assert isinstance(outcome, Assessment)
    numerator = sum(item.penalty_numerator for item in outcome.inputs)
    assert outcome.value == max(0, 100 - round(numerator / 100))
    assert outcome.method == ASSESSMENT_METHOD
    assert outcome.inputs[0].severity_penalty == SEVERITY_PENALTIES["high"]
    assert outcome.inputs[0].confidence_multiplier == CONFIDENCE_MULTIPLIERS["high"]
    assert outcome.inputs[0].detail == "Detail for High"
    assert outcome.inputs[0].evidence_ref == "security.py:1-1"


def test_missing_severity_uses_declared_default_and_discloses_it():
    outcome = assess({"security": (finding(severity=None),)}).for_dimension("security")
    assert isinstance(outcome, Assessment)
    (item,) = outcome.inputs
    assert item.supplied_severity is None
    assert item.effective_severity == DEFAULT_SEVERITY
    assert item.severity_defaulted is True
    assert outcome.defaulted_severity_count == 1
    assert DEFAULT_SEVERITY in outcome.provenance


def test_no_findings_is_a_distinct_absence_not_zero_or_perfect():
    outcome = assess({}).for_dimension("architecture")
    assert isinstance(outcome, AssessmentAbsence)
    assert outcome.reason_code == "no_findings"
    assert not hasattr(outcome, "value")


def test_all_known_dimensions_are_returned_in_declared_order():
    result = assess({"security": (finding(),)})
    assert tuple(item.dimension for item in result.outcomes) == DIMENSIONS
    assert len(result.outcomes) == 7


def test_findings_are_canonicalized_for_byte_identical_output():
    first = finding(title="A", severity="high")
    second = finding(title="B", severity="low")
    left = assess({"security": (second, first)}).serialize()
    right = assess({"security": (first, second)}).serialize()
    assert left == right


def test_weight_tables_are_pinned_by_behavior(monkeypatch):
    baseline = assess({"security": (finding(severity="high"),)}).for_dimension(
        "security"
    )
    monkeypatch.setitem(SEVERITY_PENALTIES, "high", 1)
    changed = assess({"security": (finding(severity="high"),)}).for_dimension(
        "security"
    )
    assert isinstance(baseline, Assessment)
    assert isinstance(changed, Assessment)
    assert baseline.value != changed.value


def test_confidence_weight_and_clamp_are_pinned_by_behavior():
    high = assess(
        {"security": (finding(severity="medium", confidence="high"),)}
    ).for_dimension("security")
    low = assess(
        {"security": (finding(severity="medium", confidence="low"),)}
    ).for_dimension("security")
    floor = assess(
        {"security": (finding(severity="high"),) * MAX_FINDINGS}
    ).for_dimension("security")
    assert isinstance(high, Assessment)
    assert isinstance(low, Assessment)
    assert isinstance(floor, Assessment)
    assert high.value < low.value
    assert floor.value == 0


def test_assess_rejects_unknown_dimensions_mismatches_and_too_many_findings():
    with pytest.raises(ValueError, match="unknown dimension"):
        assess({"mystery": (finding(),)})
    with pytest.raises(ValueError, match="does not match"):
        assess({"architecture": (finding("security"),)})
    with pytest.raises(ValueError, match="limit"):
        assess({"security": (finding(),) * (MAX_FINDINGS + 1)})


def test_assess_revalidates_directly_constructed_finding_domains():
    with pytest.raises(ValueError, match="confidence"):
        assess({"security": (replace(finding(), confidence="certain"),)})
    with pytest.raises(ValueError, match="severity"):
        assess({"security": (replace(finding(), severity="critical"),)})


def test_rating_and_assessment_divergence_carries_both_inputs_and_direction():
    assessment_set = assess({"security": (finding(severity="high"),)})
    result = compare(ratings(), assessment_set).for_dimension("security")
    assert isinstance(result.divergence, Divergence)
    assert result.divergence.rating_value == result.rating.value
    assert result.divergence.assessment_value == result.assessment.value
    assert result.divergence.signed_gap == result.assessment.value - result.rating.value
    assert result.divergence.absolute_gap == abs(result.divergence.signed_gap)
    assert result.divergence.direction == "agent_harsher"


def test_assessment_survives_rating_abstention_with_reason_intact():
    result = compare(
        ratings(abstain="security"),
        assess({"security": (finding(severity="high"),)}),
    ).for_dimension("security")
    assert isinstance(result.assessment, Assessment)
    assert isinstance(result.rating, RatingAbstention)
    assert isinstance(result.divergence, DivergenceAbsence)
    assert result.divergence.reason_code == "rating_abstained"
    assert result.divergence.rating_abstention is result.rating


def test_missing_assessment_and_both_absent_have_explicit_reasons():
    with_rating = compare(ratings(), assess({})).for_dimension("security")
    both_absent = compare(ratings(abstain="security"), assess({})).for_dimension(
        "security"
    )
    assert with_rating.divergence.reason_code == "assessment_absent"
    assert both_absent.divergence.reason_code == "both_absent"


def test_no_blended_quality_number_exists_structurally():
    module = ast.parse(
        Path("src/easy_verifier/core/assessment.py").read_text(encoding="utf-8")
    )
    names = {node.id for node in ast.walk(module) if isinstance(node, ast.Name)}
    assert {"blended", "merged_rating", "reconciled"}.isdisjoint(names)
    comparison = compare(ratings(), assess({"security": (finding(),)}))
    payload = comparison.to_dict()
    assert "value" not in payload


def test_assessment_module_has_no_egress_or_model_capability():
    module = ast.parse(
        Path("src/easy_verifier/core/assessment.py").read_text(encoding="utf-8")
    )
    imports = {
        alias.name.split(".")[0]
        for node in ast.walk(module)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imports.update(
        (node.module or "").split(".")[0]
        for node in ast.walk(module)
        if isinstance(node, ast.ImportFrom) and node.level == 0
    )
    assert imports <= {"__future__", "json", "collections", "dataclasses"}
    attributes = {
        node.attr for node in ast.walk(module) if isinstance(node, ast.Attribute)
    }
    assert {"open", "connect", "request", "run", "Popen", "getenv"}.isdisjoint(
        attributes
    )


def test_public_assessment_rejects_forged_arithmetic():
    valid = assess({"security": (finding(),)}).for_dimension("security")
    assert isinstance(valid, Assessment)
    with pytest.raises(ValueError, match="arithmetic"):
        replace(valid, value=valid.value - 1)

    with pytest.raises(ValueError, match="count"):
        replace(valid, defaulted_severity_count=True)


def test_compare_rejects_a_forged_rating_constructor_bypass():
    forged = object.__new__(Rating)
    object.__setattr__(forged, "dimension", "architecture")
    invalid_ratings = (forged,) + ratings()[1:]
    with pytest.raises(ValueError, match="malformed rating"):
        compare(invalid_ratings, assess({}))


def test_comparison_rejects_a_divergence_from_different_inputs():
    result = compare(ratings(), assess({"security": (finding(),)}))
    comparison = result.for_dimension("security")
    mismatched = Divergence(
        dimension="security",
        rating_value=50,
        assessment_value=60,
        signed_gap=10,
        absolute_gap=10,
        direction="rules_harsher",
    )
    with pytest.raises(ValueError, match="does not match"):
        replace(comparison, divergence=mismatched)


def test_divergence_rejects_non_integer_gap_fields():
    with pytest.raises(ValueError, match="integers"):
        Divergence(
            dimension="security",
            rating_value=50,
            assessment_value=60,
            signed_gap=10.0,
            absolute_gap=10,
            direction="rules_harsher",
        )
