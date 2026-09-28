"""T020 -- declared ratings, coverage floors, and abstention."""

from __future__ import annotations

import ast
import json
from dataclasses import replace
from pathlib import Path

import pytest

from easy_verifier.core.judge import (
    COVERAGE_FLOORS,
    RATING_RULES,
    CoverageFloor,
    GatedRating,
    OverallRating,
    Rating,
    RatingAbstained,
    RatingAbstention,
    RatingInput,
    _serialize,
    rate,
    rate_overall,
)
from easy_verifier.core.metrics import (
    WHOLE_SET,
    Metric,
    MetricAbstention,
    MetricSet,
)
from easy_verifier.core.models import CoverageSummary, SourceMiss
from easy_verifier.dimensions import dimension_names

REPO_ROOT = Path(__file__).resolve().parents[1]
DIMENSIONS = tuple(COVERAGE_FLOORS)


def _metric(
    name: str,
    outcome: float | int | MetricAbstention,
    *,
    dimension: str,
) -> Metric:
    return Metric(
        name=name,
        family="fixture",
        kind=WHOLE_SET,
        dimension=dimension,
        outcome=outcome,
        computed_from=("src/app.py",)
        if not isinstance(outcome, MetricAbstention)
        else (),
        derivation="fixture derivation",
    )


def _numeric_metrics(
    dimension: str = "architecture",
    *,
    passing_names: set[str] | None = None,
) -> MetricSet:
    rules = RATING_RULES[dimension]
    passing_names = set(rules) if passing_names is None else passing_names
    items = []
    for name, rule in rules.items():
        passing = name in passing_names
        if rule.comparison == "at_least":
            value = rule.threshold if passing else rule.threshold - 1
        else:
            value = rule.threshold if passing else rule.threshold + 1
        items.append(_metric(name, value, dimension=dimension))
    return MetricSet(tuple(items))


def _coverage(
    dimension: str = "architecture",
    *,
    score: float | None = 0.88,
    missing: tuple[SourceMiss, ...] = (
        SourceMiss("ARCHITECTURE.md", "not found in target"),
    ),
) -> CoverageSummary:
    return CoverageSummary(
        per_dimension=((dimension, score),),
        combined=score,
        method="fixture coverage",
        misses=((dimension, missing),),
    )


def _rating_with_value(dimension: str, value: int) -> Rating | GatedRating:
    """A rules Rating of exactly ``value`` built through ``rate``, choosing
    which rule metrics pass and which abstain. solution-fit declares no rule
    (T035), so it can only contribute agent-rated at the evaluate gate."""
    rules = RATING_RULES[dimension]
    coverage = _coverage(dimension, score=max(COVERAGE_FLOORS[dimension].value, 0.88))
    if not rules:
        abstention = rate(_numeric_metrics(dimension), coverage)
        assert isinstance(abstention, RatingAbstention)
        return GatedRating(abstention, value, 1, ("PRD.md:1-2",))
    names = tuple(rules)
    for mask in range(1, 3 ** len(names)):
        states = [(mask // 3**index) % 3 for index in range(len(names))]
        available = [n for n, state in zip(names, states, strict=True) if state]
        if not available:
            continue
        earned = sum(
            rules[n].weight for n, st in zip(names, states, strict=True) if st == 2
        )
        total = sum(rules[n].weight for n in available)
        if round(100 * earned / total) != value:
            continue
        metrics = []
        for name, state in zip(names, states, strict=True):
            if state == 0:
                metrics.append(
                    _metric(name, MetricAbstention("unavailable"), dimension=dimension)
                )
                continue
            rule = rules[name]
            step = 0 if state == 2 else 1
            outcome = (
                rule.threshold - step
                if rule.comparison == "at_least"
                else rule.threshold + step
            )
            metrics.append(_metric(name, outcome, dimension=dimension))
        result = rate(MetricSet(tuple(metrics)), coverage)
        assert isinstance(result, Rating)
        assert result.value == value
        return result
    raise AssertionError(f"{dimension} cannot rate exactly {value}")


def test_floor_table_is_complete_static_data_and_matches_live_discovery():
    assert tuple(COVERAGE_FLOORS) == (
        "architecture",
        "solution-fit",
        "requirement-fidelity",
        "code-quality",
        "security",
        "test-strategy",
        "blast-radius",
    )
    assert set(COVERAGE_FLOORS) == set(dimension_names())
    assert {name: floor.value for name, floor in COVERAGE_FLOORS.items()} == {
        "architecture": 0.40,
        "solution-fit": 0.50,
        "requirement-fidelity": 0.50,
        "code-quality": 0.16,
        "security": 0.25,
        "test-strategy": 0.20,
        "blast-radius": 0.25,
    }
    assert all(floor.boundary == "inclusive" for floor in COVERAGE_FLOORS.values())


def test_rating_carries_inputs_citations_and_is_hand_recomputable():
    result = rate(_numeric_metrics(), _coverage())

    assert isinstance(result, Rating)
    expected = round(
        100
        * sum(item.earned_weight for item in result.inputs)
        / sum(item.weight for item in result.inputs)
    )
    assert result.value == expected == 100
    assert all(item.computed_from == ("src/app.py",) for item in result.inputs)
    assert "round once" in result.method


def test_below_floor_abstains_with_numeric_provenance_but_no_rating(monkeypatch):
    monkeypatch.setitem(
        COVERAGE_FLOORS, "architecture", CoverageFloor(0.60, "inclusive")
    )
    result = rate(_numeric_metrics(), _coverage(score=0.33))

    assert isinstance(result, RatingAbstention)
    assert result.reason_code == "below_coverage_floor"
    assert result.coverage_floor == 0.60
    assert result.achieved_coverage == 0.33
    assert result.sources_missing == (
        SourceMiss("ARCHITECTURE.md", "not found in target"),
    )
    assert not hasattr(result, "value")
    with pytest.raises(RatingAbstained):
        _ = result.numeric_value


def test_below_floor_rejects_an_empty_named_miss_list(monkeypatch):
    monkeypatch.setitem(
        COVERAGE_FLOORS, "architecture", CoverageFloor(0.60, "inclusive")
    )
    with pytest.raises(ValueError, match="sources_missing"):
        rate(_numeric_metrics(), _coverage(score=0.33, missing=()))


@pytest.mark.parametrize(
    "score", [float("nan"), float("inf"), float("-inf"), -0.01, 1.01]
)
def test_coverage_must_be_finite_and_in_the_closed_unit_interval(score: float):
    with pytest.raises(ValueError, match="coverage"):
        rate(_numeric_metrics(), _coverage(score=score))


@pytest.mark.parametrize("dimension", DIMENSIONS)
def test_every_floor_is_inclusive_and_extremes_change_the_result(
    dimension: str, monkeypatch
):
    declared = COVERAGE_FLOORS[dimension]
    exact = rate(
        _numeric_metrics(dimension), _coverage(dimension, score=declared.value)
    )
    if not RATING_RULES[dimension]:
        # T035: a dimension with no rule abstains whatever its coverage.
        assert isinstance(exact, RatingAbstention)
        assert exact.reason_code == "no_static_rule"
        return
    assert isinstance(exact, Rating)

    monkeypatch.setitem(COVERAGE_FLOORS, dimension, CoverageFloor(0.0, "inclusive"))
    low_floor = rate(_numeric_metrics(dimension), _coverage(dimension, score=0.33))
    monkeypatch.setitem(COVERAGE_FLOORS, dimension, CoverageFloor(1.0, "inclusive"))
    high_floor = rate(_numeric_metrics(dimension), _coverage(dimension, score=0.33))
    assert isinstance(low_floor, Rating)
    assert isinstance(high_floor, RatingAbstention)


@pytest.mark.parametrize(
    ("dimension", "metric_name"),
    [(dimension, name) for dimension, rules in RATING_RULES.items() for name in rules],
)
def test_every_rule_threshold_distinguishes_pass_from_fail(
    dimension: str, metric_name: str
):
    coverage = _coverage(dimension, score=1.0, missing=())
    passing = rate(_numeric_metrics(dimension, passing_names={metric_name}), coverage)
    failing = rate(_numeric_metrics(dimension, passing_names=set()), coverage)

    assert isinstance(passing, Rating)
    assert isinstance(failing, Rating)
    assert passing.value == RATING_RULES[dimension][metric_name].weight
    assert failing.value == 0


@pytest.mark.parametrize("outcome", [float("nan"), float("inf"), float("-inf")])
def test_numeric_metric_outcomes_must_be_finite(outcome: float):
    metrics = _numeric_metrics()
    poisoned = replace(metrics.metrics[0], outcome=outcome)
    with pytest.raises(ValueError, match="finite"):
        rate(MetricSet((poisoned,) + metrics.metrics[1:]), _coverage())


def test_none_coverage_and_failed_dimension_have_distinct_structured_reasons():
    no_sources = rate(_numeric_metrics(), _coverage(score=None, missing=()))
    failed_metrics = MetricSet(
        (), dimensions_without_pack=(("architecture", "collector exploded"),)
    )
    failed = rate(failed_metrics, _coverage(score=None))

    assert isinstance(no_sources, RatingAbstention)
    assert no_sources.reason_code == "coverage_not_applicable"
    assert no_sources.achieved_coverage is None
    assert isinstance(failed, RatingAbstention)
    assert failed.reason_code == "dimension_failed"
    assert failed.failure == "collector exploded"


def test_partial_metric_abstentions_are_disclosed_and_normalized_out():
    first_name = next(iter(RATING_RULES["architecture"]))
    metrics = []
    for name, rule in RATING_RULES["architecture"].items():
        outcome = (
            rule.threshold
            if name == first_name
            else MetricAbstention("whole-set metric unavailable")
        )
        metrics.append(_metric(name, outcome, dimension="architecture"))

    result = rate(MetricSet(tuple(metrics)), _coverage())

    assert isinstance(result, Rating)
    assert result.value == 100
    assert result.inputs[0].metric_name == first_name
    assert len(result.unavailable_metrics) == len(RATING_RULES["architecture"]) - 1
    assert all(
        reason == "whole-set metric unavailable"
        for _, reason in result.unavailable_metrics
    )


def test_all_metrics_abstained_but_legitimate_zero_does_not_collapse():
    all_abstained = MetricSet(
        tuple(
            _metric(
                name,
                MetricAbstention("whole-set metric unavailable"),
                dimension="architecture",
            )
            for name in RATING_RULES["architecture"]
        )
    )
    result = rate(all_abstained, _coverage())
    assert isinstance(result, RatingAbstention)
    assert result.reason_code == "all_metrics_abstained"

    values = _numeric_metrics(passing_names={"top_level_import_cycles"})
    zero = next(m for m in values if m.name == "top_level_import_cycles")
    assert zero.outcome == 0
    rated = rate(values, _coverage())
    assert isinstance(rated, Rating)
    assert rated.value == RATING_RULES["architecture"]["top_level_import_cycles"].weight


def test_missing_and_duplicate_rule_metrics_are_rejected():
    complete = _numeric_metrics()
    with pytest.raises(ValueError, match="missing declared rating metric"):
        rate(MetricSet(complete.metrics[:-1]), _coverage())
    with pytest.raises(ValueError, match="duplicate metric"):
        rate(MetricSet(complete.metrics + (complete.metrics[0],)), _coverage())


def test_rule_key_and_payload_name_cannot_drift(monkeypatch):
    rules = RATING_RULES["architecture"]
    key = next(iter(rules))
    monkeypatch.setitem(rules, key, replace(rules[key], metric_name="other"))
    with pytest.raises(ValueError, match="key.*metric_name"):
        rate(_numeric_metrics(), _coverage())


@pytest.mark.parametrize(
    "replacement, message",
    [
        ({"weight": 0}, "weight"),
        ({"threshold": float("nan")}, "threshold"),
        ({"comparison": "sideways"}, "comparison"),
    ],
)
def test_malformed_declared_rules_are_rejected(replacement, message, monkeypatch):
    rules = RATING_RULES["architecture"]
    key = "top_level_import_cycles"
    monkeypatch.setitem(rules, key, replace(rules[key], **replacement))
    with pytest.raises(ValueError, match=message):
        rate(_numeric_metrics(), _coverage())


@pytest.mark.parametrize(
    "floor",
    [
        CoverageFloor(float("nan"), "inclusive"),
        CoverageFloor(-0.01, "inclusive"),
        CoverageFloor(1.01, "inclusive"),
        CoverageFloor(0.5, "exclusive"),
    ],
)
def test_malformed_declared_floors_are_rejected(floor: CoverageFloor, monkeypatch):
    monkeypatch.setitem(COVERAGE_FLOORS, "architecture", floor)
    with pytest.raises(ValueError, match="coverage floor"):
        rate(_numeric_metrics(), _coverage())


def test_rate_rejects_cross_dimension_or_misaligned_coverage():
    foreign = replace(_numeric_metrics().metrics[0], dimension="security")
    mixed = MetricSet((foreign,) + _numeric_metrics().metrics[1:])
    with pytest.raises(ValueError, match="exactly one dimension"):
        rate(mixed, _coverage())
    with pytest.raises(ValueError, match="coverage"):
        rate(_numeric_metrics(), _coverage("security"))


def test_rate_rejects_extra_or_mismatched_coverage_dimensions():
    base = _coverage()
    invalid = (
        replace(
            base,
            per_dimension=base.per_dimension + (("security", 0.88),),
        ),
        replace(
            base,
            misses=base.misses + (("security", ()),),
        ),
        replace(base, misses=(("security", base.misses[0][1]),)),
    )
    for coverage in invalid:
        with pytest.raises(ValueError, match="single dimension|coverage"):
            rate(_numeric_metrics(), coverage)


def test_rate_rejects_combined_coverage_that_differs_from_sole_dimension():
    with pytest.raises(ValueError, match="combined"):
        rate(_numeric_metrics(), replace(_coverage(), combined=0.87))
    with pytest.raises(ValueError, match="combined"):
        rate(
            _numeric_metrics(),
            replace(_coverage(score=None, missing=()), combined=0.0),
        )


def test_abstaining_weak_dimension_raises_overall_and_disclosure_says_so():
    strong_names = DIMENSIONS[:6]
    weak_name = DIMENSIONS[6]
    strong = tuple(_rating_with_value(name, 50) for name in strong_names)
    weak_metrics = _numeric_metrics(weak_name, passing_names=set())
    floor = COVERAGE_FLOORS[weak_name].value
    weak_rating = rate(weak_metrics, _coverage(weak_name, score=floor))
    weak_abstention = rate(
        weak_metrics,
        _coverage(
            weak_name,
            score=floor - 0.001,
            missing=(SourceMiss("go.mod", "not found in target"),),
        ),
    )
    assert isinstance(weak_rating, Rating) and weak_rating.value == 0
    assert isinstance(weak_abstention, RatingAbstention)

    all_seven = rate_overall(strong + (weak_rating,))
    with_abstention = rate_overall(strong + (weak_abstention,))

    assert isinstance(all_seven, OverallRating) and all_seven.value == 43
    assert isinstance(with_abstention, OverallRating) and with_abstention.value == 50
    assert with_abstention.value > all_seven.value
    assert with_abstention.contributor_count == 6
    assert with_abstention.total_dimension_count == 7
    assert with_abstention.abstentions == (weak_abstention,)
    assert "6 of 7" in with_abstention.disclosure
    assert "abstention can raise the overall" in with_abstention.disclosure
    assert weak_name in with_abstention.disclosure
    assert "below_coverage_floor" in with_abstention.disclosure
    assert weak_abstention.sources_missing[0].source == "go.mod"


def test_overall_requires_exactly_the_seven_unique_known_dimensions():
    ratings = tuple(_rating_with_value(name, 50) for name in DIMENSIONS)
    with pytest.raises(ValueError, match="exactly the seven"):
        rate_overall(ratings[:-1])
    with pytest.raises(ValueError, match="duplicate"):
        rate_overall(ratings[:-1] + (ratings[0],))
    with pytest.raises(ValueError, match="unknown"):
        rate_overall(ratings[:-1] + (replace(ratings[-1], dimension="mystery"),))


def test_rating_value_is_an_integer_in_the_closed_rating_range():
    for invalid in (-1, 101, 99.5, True):
        with pytest.raises(ValueError, match="integer.*0.*100"):
            Rating(dimension="architecture", value=invalid, inputs=())

    forged = object.__new__(Rating)
    object.__setattr__(forged, "dimension", DIMENSIONS[-1])
    object.__setattr__(forged, "value", 999)
    valid = tuple(_rating_with_value(name, 50) for name in DIMENSIONS[:-1])
    with pytest.raises(ValueError, match="integer.*0.*100"):
        rate_overall(valid + (forged,))


def test_rating_input_rejects_incoherent_or_uncheckable_fields():
    rule = RATING_RULES["architecture"]["top_level_import_cycles"]
    valid = {
        "metric_name": "top_level_import_cycles",
        "metric_value": 0,
        "weight": 40,
        "threshold": 0,
        "comparison": "at_most",
        "passed": True,
        "earned_weight": 40,
        "computed_from": ("src/app.py",),
        "metric_citation": rule.metric_citation,
        "threshold_citation": rule.threshold_citation,
        "source_tag": rule.source_tag,
    }
    RatingInput(**valid)
    invalid_changes = (
        {"metric_name": ""},
        {"metric_name": 7},
        {"metric_name": "mystery"},
        {"weight": 0},
        {"weight": 1.5},
        {"threshold": float("inf")},
        {"comparison": "sideways"},
        {"passed": 1},
        {"passed": True, "earned_weight": 0},
        {"passed": False, "earned_weight": 5},
        {"earned_weight": 3},
        {"computed_from": ()},
        {"computed_from": ("",)},
        {"computed_from": (7,)},
        {"metric_citation": ()},
        {"threshold_citation": "project-default"},
        {"source_tag": "agent-researched (unreviewed)"},
    )
    for changes in invalid_changes:
        with pytest.raises(ValueError):
            RatingInput(**(valid | changes))


def test_rating_constructor_enforces_dimension_inputs_partition_and_arithmetic():
    valid = _rating_with_value("architecture", 50)
    with pytest.raises(ValueError):
        Rating("architecture", 75, inputs=())
    with pytest.raises(ValueError, match="unknown dimension"):
        replace(valid, dimension="mystery")
    with pytest.raises(ValueError, match="duplicate"):
        replace(valid, inputs=valid.inputs + (valid.inputs[0],))
    with pytest.raises(ValueError, match="overlap"):
        replace(
            valid,
            unavailable_metrics=((valid.inputs[0].metric_name, "unavailable"),),
        )
    with pytest.raises(ValueError, match="does not match.*arithmetic"):
        replace(valid, value=75)


def test_overall_rejects_unsupported_objects_before_reading_them():
    class Forged:
        def __init__(self, dimension: str):
            self.dimension = dimension
            self.value = 999

    forged = tuple(Forged(name) for name in DIMENSIONS[:-1])
    valid = _rating_with_value(DIMENSIONS[-1], 50)
    with pytest.raises(
        ValueError, match="exactly Rating, RatingAbstention or GatedRating"
    ):
        rate_overall(forged + (valid,))


def test_overall_constructor_enforces_counts_partition_and_arithmetic():
    with pytest.raises(ValueError):
        OverallRating(75, 99, 7, (), ())

    ratings = tuple(_rating_with_value(name, 50) for name in DIMENSIONS)
    valid = rate_overall(ratings)
    assert isinstance(valid, OverallRating)
    with pytest.raises(ValueError, match="contributor_count"):
        replace(valid, contributor_count=99)
    with pytest.raises(ValueError, match="total_dimension_count"):
        replace(valid, total_dimension_count=6)
    with pytest.raises(ValueError, match="contributors"):
        replace(valid, contributors=tuple(reversed(valid.contributors)))
    with pytest.raises(ValueError, match="does not match.*arithmetic"):
        replace(valid, value=75)


def test_overall_serializes_contributor_values_needed_to_recompute_it():
    ratings = tuple(_rating_with_value(name, 50) for name in DIMENSIONS)
    result = rate_overall(ratings)
    assert isinstance(result, OverallRating)
    payload = json.loads(result.serialize())
    values = payload["contributor_values"]
    assert values == [[name, 50] for name in DIMENSIONS]
    assert result.value == round(sum(value for _name, value in values) / len(values))


def test_unknown_abstention_reason_and_incoherent_payload_are_rejected():
    with pytest.raises(ValueError, match="reason_code"):
        RatingAbstention(dimension="architecture", reason_code="invented_reason")
    with pytest.raises(ValueError, match="sources_missing"):
        RatingAbstention(
            dimension="architecture",
            reason_code="below_coverage_floor",
            coverage_floor=0.40,
            achieved_coverage=0.33,
        )
    with pytest.raises(ValueError, match="failure"):
        RatingAbstention(dimension="architecture", reason_code="dimension_failed")
    with pytest.raises(ValueError, match="all seven abstentions"):
        RatingAbstention(
            dimension="overall",
            reason_code="no_dimension_rated",
            abstentions=(object(),) * 7,
        )


def test_abstention_rejects_unknown_dimensions_and_surplus_reason_fields():
    miss = SourceMiss("ARCHITECTURE.md", "not found in target")
    leaves = tuple(
        rate(_numeric_metrics(name), _coverage(name, score=0.0)) for name in DIMENSIONS
    )
    unavailable = tuple((name, "unavailable") for name in RATING_RULES["architecture"])
    valid = {
        "below": RatingAbstention(
            dimension="architecture",
            reason_code="below_coverage_floor",
            coverage_floor=0.40,
            achieved_coverage=0.33,
            sources_missing=(miss,),
        ),
        "not_applicable": RatingAbstention(
            dimension="architecture",
            reason_code="coverage_not_applicable",
            coverage_floor=0.40,
        ),
        "failed": RatingAbstention(
            dimension="architecture",
            reason_code="dimension_failed",
            sources_missing=(miss,),
            failure="collector exploded",
        ),
        "metrics": RatingAbstention(
            dimension="architecture",
            reason_code="all_metrics_abstained",
            coverage_floor=0.40,
            achieved_coverage=0.88,
            sources_missing=(miss,),
            unavailable_metrics=unavailable,
        ),
        "overall": RatingAbstention(
            dimension="overall",
            reason_code="no_dimension_rated",
            abstentions=leaves,
        ),
    }

    for name in ("below", "not_applicable", "failed", "metrics"):
        with pytest.raises(ValueError, match="dimension"):
            replace(valid[name], dimension="mystery")

    contradictory = (
        (valid["below"], {"dimension": "overall"}),
        (valid["below"], {"failure": "impossible"}),
        (valid["below"], {"unavailable_metrics": unavailable}),
        (valid["below"], {"abstentions": leaves}),
        (valid["not_applicable"], {"failure": "impossible"}),
        (valid["not_applicable"], {"unavailable_metrics": unavailable}),
        (valid["not_applicable"], {"abstentions": leaves}),
        (valid["failed"], {"coverage_floor": 0.40}),
        (valid["failed"], {"achieved_coverage": 0.20}),
        (valid["failed"], {"unavailable_metrics": unavailable}),
        (valid["failed"], {"abstentions": leaves}),
        (valid["metrics"], {"failure": "impossible"}),
        (valid["metrics"], {"abstentions": leaves}),
        (valid["overall"], {"coverage_floor": 0.40}),
        (valid["overall"], {"achieved_coverage": 0.20}),
        (valid["overall"], {"sources_missing": (miss,)}),
        (valid["overall"], {"failure": "impossible"}),
        (valid["overall"], {"unavailable_metrics": unavailable}),
    )
    for abstention, changes in contradictory:
        with pytest.raises(ValueError, match="requires|only|dimension"):
            replace(abstention, **changes)


def test_abstention_validates_source_miss_values_at_construction_and_revalidation():
    kwargs = {
        "dimension": DIMENSIONS[-1],
        "reason_code": "below_coverage_floor",
        "coverage_floor": COVERAGE_FLOORS[DIMENSIONS[-1]].value,
        "achieved_coverage": 0.20,
    }
    with pytest.raises(ValueError, match="SourceMiss"):
        RatingAbstention(**kwargs, sources_missing=(object(),))

    for field_name, field_value in (("source", ""), ("reason", object())):
        forged_miss = object.__new__(SourceMiss)
        object.__setattr__(forged_miss, "source", "go.mod")
        object.__setattr__(forged_miss, "reason", "not found in target")
        object.__setattr__(forged_miss, field_name, field_value)
        with pytest.raises(ValueError, match="SourceMiss"):
            RatingAbstention(**kwargs, sources_missing=(forged_miss,))

    valid = RatingAbstention(
        **kwargs,
        sources_missing=(SourceMiss("go.mod", "not found in target"),),
    )
    object.__setattr__(valid, "sources_missing", (object(),))
    ratings = tuple(_rating_with_value(name, 50) for name in DIMENSIONS[:-1])
    with pytest.raises(ValueError, match="SourceMiss|malformed RatingAbstention"):
        rate_overall(ratings + (valid,))


def test_leaf_abstention_floor_must_equal_its_current_declared_floor():
    all_unavailable = MetricSet(
        tuple(
            _metric(name, MetricAbstention("unavailable"), dimension="architecture")
            for name in RATING_RULES["architecture"]
        )
    )
    leaves = (
        rate(_numeric_metrics(), _coverage(score=0.33)),
        rate(_numeric_metrics(), _coverage(score=None, missing=())),
        rate(all_unavailable, _coverage()),
    )
    assert all(isinstance(item, RatingAbstention) for item in leaves)
    for abstention in leaves:
        assert isinstance(abstention, RatingAbstention)
        with pytest.raises(ValueError, match="declared floor"):
            replace(
                abstention,
                coverage_floor=COVERAGE_FLOORS[abstention.dimension].value + 0.01,
            )


def test_public_rating_methods_and_order_are_canonical():
    rating = _rating_with_value("architecture", 50)
    with pytest.raises(ValueError, match="method"):
        replace(rating, method="caller supplied arithmetic")
    with pytest.raises(ValueError, match="canonical"):
        replace(rating, inputs=tuple(reversed(rating.inputs)))

    first_name = next(iter(RATING_RULES["architecture"]))
    partial = rate(
        MetricSet(
            tuple(
                _metric(
                    name,
                    rule.threshold
                    if name == first_name
                    else MetricAbstention("unavailable"),
                    dimension="architecture",
                )
                for name, rule in RATING_RULES["architecture"].items()
            )
        ),
        _coverage(),
    )
    assert isinstance(partial, Rating)
    with pytest.raises(ValueError, match="canonical"):
        replace(
            partial,
            unavailable_metrics=tuple(reversed(partial.unavailable_metrics)),
        )

    outcomes = (_rating_with_value(DIMENSIONS[0], 50),) + tuple(
        rate(_numeric_metrics(name), _coverage(name, score=0.0))
        for name in DIMENSIONS[1:]
    )
    overall = rate_overall(outcomes)
    assert isinstance(overall, OverallRating)
    with pytest.raises(ValueError, match="method"):
        replace(overall, method="caller supplied arithmetic")
    with pytest.raises(ValueError, match="canonical"):
        replace(overall, abstentions=tuple(reversed(overall.abstentions)))

    all_abstained = rate_overall(
        outcomes[1:]
        + (rate(_numeric_metrics(DIMENSIONS[0]), _coverage(DIMENSIONS[0], score=0.0)),)
    )
    assert isinstance(all_abstained, RatingAbstention)
    with pytest.raises(ValueError, match="canonical"):
        replace(all_abstained, abstentions=tuple(reversed(all_abstained.abstentions)))


def test_overall_revalidates_bypassed_abstentions_and_parent_children():
    forged = object.__new__(RatingAbstention)
    object.__setattr__(forged, "dimension", DIMENSIONS[-1])
    object.__setattr__(forged, "reason_code", "invented_reason")
    valid_ratings = tuple(_rating_with_value(name, 50) for name in DIMENSIONS[:-1])
    with pytest.raises(ValueError, match="reason_code"):
        rate_overall(valid_ratings + (forged,))

    valid_abstentions = tuple(
        rate(_numeric_metrics(name), _coverage(name, score=0.0)) for name in DIMENSIONS
    )
    with pytest.raises(ValueError, match="reason_code"):
        RatingAbstention(
            dimension="overall",
            reason_code="no_dimension_rated",
            abstentions=valid_abstentions[:-1] + (forged,),
        )


def test_all_seven_abstaining_produces_overall_abstention():
    abstentions = tuple(
        rate(_numeric_metrics(name), _coverage(name, score=0.0)) for name in DIMENSIONS
    )
    result = rate_overall(abstentions)

    assert isinstance(result, RatingAbstention)
    assert result.dimension == "overall"
    assert result.reason_code == "no_dimension_rated"
    assert result.abstentions == abstentions
    assert not hasattr(result, "value")
    with pytest.raises(RatingAbstained):
        _ = result.numeric_value


def test_serialization_is_byte_deterministic_and_carries_disclosure():
    ratings = tuple(_rating_with_value(name, 50) for name in DIMENSIONS)
    first = rate_overall(ratings)
    second = rate_overall(tuple(reversed(ratings)))

    assert isinstance(first, OverallRating)
    assert first.serialize() == second.serialize()
    decoded = json.loads(first.serialize())
    assert decoded["contributors"] == list(DIMENSIONS)
    assert decoded["disclosure"] == first.disclosure
    assert first.serialize() == json.dumps(
        first.to_dict(), sort_keys=True, ensure_ascii=True, separators=(",", ":")
    )


@pytest.mark.parametrize("non_finite", [float("nan"), float("inf"), float("-inf")])
def test_serialization_rejects_non_finite_json_numbers(non_finite: float):
    with pytest.raises(ValueError):
        _serialize({"not_json": non_finite})
    with pytest.raises(ValueError, match="finite"):
        rule = RATING_RULES["architecture"]["top_level_import_cycles"]
        RatingInput(
            metric_name="top_level_import_cycles",
            metric_value=non_finite,
            weight=40,
            threshold=0,
            comparison="at_most",
            passed=False,
            earned_weight=0,
            computed_from=("src/app.py",),
            metric_citation=rule.metric_citation,
            threshold_citation=rule.threshold_citation,
            source_tag=rule.source_tag,
        )


def test_judge_is_structurally_arithmetic_only():
    source = (REPO_ROOT / "src/easy_verifier/core/judge.py").read_text()
    tree = ast.parse(source)
    imports: set[str] = set()
    called_attributes: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imports.add("." * node.level + (node.module or ""))
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            called_attributes.add(node.func.attr)

    assert imports == {
        "__future__",
        "json",
        "math",
        "collections.abc",
        "dataclasses",
        "decimal",
        ".metrics",
        ".models",
    }
    assert (
        not {
            "getenv",
            "environ",
            "open",
            "request",
            "urlopen",
            "connect",
            "send",
            "read_text",
            "read_bytes",
        }
        & called_attributes
    )
    assert not any(
        token in source.lower()
        for token in ("openai", "anthropic", "bedrock", "vertexai", "httpx")
    )
