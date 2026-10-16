"""T067 — evidence floor (DDR-0010, FR-058, FR-059, FR-036 amended).

A dimension shows a number only when at least half of its declared rule
weight was measured. An abstention for missing evidence is a warning and an
improvement-plan line; it is never offered to, nor accepted at, the evaluate
gate. Only ``no_static_rule`` (solution-fit) and borderline inputs are gated.

Ratings are built through the real ``rate()`` so every number is the declared
arithmetic.
"""

from __future__ import annotations

import dataclasses
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

import easy_verifier.core.judge as judge
from easy_verifier.core.findings import ValidationError
from easy_verifier.core.gate import apply_gate_evaluations, detect_evaluate_gates
from easy_verifier.core.improve import FIX_HINTS, improvement_plan
from easy_verifier.core.judge import (
    COVERAGE_FLOORS,
    DOCUMENTATION_RULES,
    EVIDENCE_LACK_REASONS,
    MEASURED_WEIGHT_FLOOR,
    RATING_RULES,
    GatedRating,
    Rating,
    RatingAbstention,
    rate_overall,
)
from easy_verifier.core.metrics import WHOLE_SET, Metric, MetricAbstention, MetricSet
from easy_verifier.core.models import CoverageSummary, SourceMiss
from easy_verifier.core.report import _Ctx, _render_unknowns
from easy_verifier.core.roles import documentation_present
from easy_verifier.core.score import ScoreResult
from easy_verifier.dimensions import dimension_names

# T108: change-risk added
DIMENSIONS = tuple(n for n in dimension_names() if n != "change-risk")
REF = "README.md:1-3"
GONE = MetricAbstention("no function was read: the source cap was exceeded")


def _docs(dimension: str) -> tuple:
    return tuple(
        documentation_present(rule, ())
        for rule in DOCUMENTATION_RULES.get(dimension, ())
    )


def _passing(dimension: str, name: str) -> float:
    """Met and outside the borderline band."""
    rule = RATING_RULES[dimension][name]
    return rule.threshold + 10 if rule.comparison == "at_least" else rule.threshold / 2


def _rating(dimension: str, values: dict[str, object] | None = None):
    """Every rule passes unless ``values`` overrides it."""
    values = values or {}
    metrics = tuple(
        Metric(
            name=name,
            family="fixture",
            kind=WHOLE_SET,
            dimension=dimension,
            outcome=values.get(name, _passing(dimension, name)),
            computed_from=()
            if isinstance(values.get(name), MetricAbstention)
            else ("src/app.py",),
            derivation="fixture",
        )
        for name in RATING_RULES[dimension]
    )
    coverage = CoverageSummary(
        per_dimension=((dimension, 1.0),),
        combined=1.0,
        method="fixture",
        misses=((dimension, ()),),
    )
    return judge.rate(MetricSet(metrics), coverage, documentation=_docs(dimension))


def _measured_only(dimension: str, *measured: str):
    """Only ``measured`` rules have a value; every other rule abstained."""
    return _rating(
        dimension,
        {name: GONE for name in RATING_RULES[dimension] if name not in measured},
    )


def _monorepo_code_quality() -> RatingAbstention:
    """node-monorepo 2026-10-03: lint + format config measured (20 of 100)."""
    return _measured_only(
        "code-quality", "lint_config_missing", "format_config_missing"
    )


def _far(dimension: str, name: str) -> float:
    rule = RATING_RULES[dimension][name]
    return rule.threshold + 10 if rule.comparison == "at_least" else rule.threshold + 5


def _rated_far(dimension: str) -> Rating:
    return _rating(dimension, {n: _far(dimension, n) for n in RATING_RULES[dimension]})


def _below_floor(dimension: str) -> RatingAbstention:
    return RatingAbstention(
        dimension=dimension,
        reason_code="below_coverage_floor",
        coverage_floor=COVERAGE_FLOORS[dimension].value,
        achieved_coverage=0.0,
        sources_missing=(SourceMiss("REQUIREMENTS.md", "not found in target"),),
        documentation=_docs(dimension),
    )


def _not_applicable(dimension: str) -> RatingAbstention:
    return RatingAbstention(
        dimension=dimension,
        reason_code="coverage_not_applicable",
        coverage_floor=COVERAGE_FLOORS[dimension].value,
        documentation=_docs(dimension),
    )


def _failed(dimension: str) -> RatingAbstention:
    return RatingAbstention(
        dimension=dimension, reason_code="dimension_failed", failure="boom"
    )


def _all_abstained(dimension: str) -> RatingAbstention:
    result = _measured_only(dimension)
    assert result.reason_code == "all_metrics_abstained"
    return result


def _solution_fit() -> RatingAbstention:
    result = _rating("solution-fit")
    assert result.reason_code == "no_static_rule"
    return result


def _packs() -> dict:
    pack = SimpleNamespace(excerpts=(SimpleNamespace(ref=REF),), truncated=False)
    return {name: pack for name in DIMENSIONS}


def _ev() -> dict:
    return {"score": 88, "confidence": 0.6, "evidence_refs": [REF]}


def _every_kind() -> tuple:
    """One of each evidence-lack reason, one no_static_rule, one borderline."""
    borderline = _rating("blast-radius", {"max_fan_in_changed": 21})
    assert type(borderline) is Rating
    by_name = {
        "architecture": _below_floor("architecture"),
        "solution-fit": _solution_fit(),
        "requirement-fidelity": _not_applicable("requirement-fidelity"),
        "code-quality": _monorepo_code_quality(),
        "security": _failed("security"),
        "test-strategy": _all_abstained("test-strategy"),
        "blast-radius": borderline,
        # T043: an ordinary rules rating, far from every threshold.
        "reliability": _rated_far("reliability"),
        # T041: likewise.
        "supply-chain": _rated_far("supply-chain"),
        # T044: likewise.
        "api": _rated_far("api"),
        # T045: likewise.
        "data": _rated_far("data"),
        # T046: likewise.
        "operations": _rated_far("operations"),
        # T042: likewise.
        "infrastructure": _rated_far("infrastructure"),
    }
    return tuple(by_name[name] for name in DIMENSIONS)


# ---------------------------------------------------------------------------
# AC1 — the floor is declared data and drives rate()
# ---------------------------------------------------------------------------


def test_floor_is_declared_decimal_half() -> None:
    assert MEASURED_WEIGHT_FLOOR == Decimal("0.50")
    assert type(MEASURED_WEIGHT_FLOOR) is Decimal


def test_twenty_of_hundred_abstains_with_share_and_unmeasured_rules() -> None:
    result = _monorepo_code_quality()
    assert type(result) is RatingAbstention
    assert result.reason_code == "insufficient_measured_weight"
    assert result.measured_share == Decimal("0.20")
    unmeasured = [name for name, _ in result.unavailable_metrics]
    assert unmeasured == [
        "functions_over_ccn_10_share",
        "max_function_ccn",
        "type_escapes_per_kloc",
        "todo_without_ticket_share",
        "strict_type_config_missing",
    ]
    assert all(reason == GONE.reason for _, reason in result.unavailable_metrics)
    with pytest.raises(judge.RatingAbstained):
        _ = result.numeric_value


def test_exactly_half_is_rated() -> None:
    # 25 + 15 + 10 = 50 of 100
    result = _measured_only(
        "code-quality",
        "functions_over_ccn_10_share",
        "max_function_ccn",
        "lint_config_missing",
    )
    assert type(result) is Rating
    assert result.value == 100


def test_just_below_half_abstains() -> None:
    # 25 + 10 + 10 = 45 of 100 (declared weights are multiples of 5)
    result = _measured_only(
        "code-quality",
        "functions_over_ccn_10_share",
        "lint_config_missing",
        "format_config_missing",
    )
    assert result.reason_code == "insufficient_measured_weight"
    assert result.measured_share == Decimal("0.45")


def test_floor_is_read_from_the_declared_constant(monkeypatch) -> None:
    """Tuning is a value change: at 0.51 the 50/100 boundary abstains."""
    monkeypatch.setattr(judge, "MEASURED_WEIGHT_FLOOR", Decimal("0.51"))
    result = _measured_only(
        "code-quality",
        "functions_over_ccn_10_share",
        "max_function_ccn",
        "lint_config_missing",
    )
    assert result.reason_code == "insufficient_measured_weight"
    assert result.measured_share == Decimal("0.50")


def test_solution_fit_still_no_static_rule() -> None:
    assert _solution_fit().reason_code == "no_static_rule"


# ---------------------------------------------------------------------------
# AC2 — serialization and validation round-trip
# ---------------------------------------------------------------------------


def test_to_dict_carries_share_floor_and_unmeasured() -> None:
    payload = _monorepo_code_quality().to_dict()
    assert payload["reason_code"] == "insufficient_measured_weight"
    assert payload["measured_share"] == "0.20"
    assert payload["measured_weight_floor"] == "0.50"
    assert [name for name, _ in payload["unavailable_metrics"]][0] == (
        "functions_over_ccn_10_share"
    )
    assert "measured" in payload["reason"]


def test_other_abstentions_do_not_gain_share_keys() -> None:
    payload = _below_floor("architecture").to_dict()
    assert "measured_share" not in payload
    assert "measured_weight_floor" not in payload


def test_abstention_round_trips_through_its_fields() -> None:
    original = _monorepo_code_quality()
    rebuilt = RatingAbstention(
        **{f.name: getattr(original, f.name) for f in dataclasses.fields(original)}
    )
    assert rebuilt == original
    assert rebuilt.serialize() == original.serialize()


def test_forged_abstention_at_or_above_floor_is_rejected() -> None:
    original = _monorepo_code_quality()
    with pytest.raises(ValueError, match="insufficient_measured_weight"):
        dataclasses.replace(
            original, unavailable_metrics=original.unavailable_metrics[:1]
        )  # 75 of 100 measured


def test_forged_abstention_without_unmeasured_rules_is_rejected() -> None:
    with pytest.raises(ValueError, match="insufficient_measured_weight"):
        dataclasses.replace(_monorepo_code_quality(), unavailable_metrics=())


def test_forged_rating_below_floor_is_rejected() -> None:
    """A Rating cannot be built from less than the floor (the node-monorepo 100)."""
    rated = _rating("code-quality")
    measured = tuple(
        item
        for item in rated.inputs
        if item.metric_name in ("lint_config_missing", "format_config_missing")
    )
    unavailable = tuple(
        (name, GONE.reason)
        for name in RATING_RULES["code-quality"]
        if name not in ("lint_config_missing", "format_config_missing")
    )
    with pytest.raises(ValueError, match="measured"):
        Rating(
            dimension="code-quality",
            value=100,
            inputs=measured,
            unavailable_metrics=unavailable,
        )


# ---------------------------------------------------------------------------
# AC3 — gate only no_static_rule and borderline
# ---------------------------------------------------------------------------


def test_evidence_lack_reasons_are_exactly_the_ddr_list() -> None:
    assert EVIDENCE_LACK_REASONS == frozenset(
        {
            "insufficient_measured_weight",
            "below_coverage_floor",
            "coverage_not_applicable",
            "all_metrics_abstained",
            "dimension_failed",
        }
    )


def test_gates_are_solution_fit_and_borderline_only() -> None:
    assert detect_evaluate_gates(_every_kind()) == {
        "solution-fit": "abstained",
        "blast-radius": "borderline: max_fan_in_changed",
    }


# ---------------------------------------------------------------------------
# AC4 — an evaluation for an evidence-lack dimension is an explicit error
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "dimension",
    [
        "architecture",
        "requirement-fidelity",
        "code-quality",
        "security",
        "test-strategy",
    ],
)
def test_evaluation_for_evidence_lack_dimension_is_rejected(dimension) -> None:
    ratings = _every_kind()
    reason = next(r for r in ratings if r.dimension == dimension).reason_code
    with pytest.raises(ValidationError) as caught:
        apply_gate_evaluations({dimension: _ev()}, ratings, _packs())
    message = str(caught.value)
    assert f"gate_evaluations.{dimension}" in message
    assert reason in message
    assert "missing evidence" in message


def test_replayed_old_input_is_rejected_not_dropped() -> None:
    """An old stored agent input carrying an evaluation for a dimension that
    is now an evidence-lack abstention fails loudly, alongside a valid one."""
    with pytest.raises(ValidationError) as caught:
        apply_gate_evaluations(
            {"solution-fit": _ev(), "requirement-fidelity": _ev()},
            _every_kind(),
            _packs(),
        )
    assert "gate_evaluations.requirement-fidelity" in str(caught.value)
    assert "gate_evaluations.solution-fit" not in str(caught.value)


def test_solution_fit_and_borderline_are_still_accepted() -> None:
    applied = apply_gate_evaluations(
        {"solution-fit": _ev(), "blast-radius": _ev()}, _every_kind(), _packs()
    )
    kinds = {item.dimension: type(item) for item in applied}
    assert kinds["solution-fit"] is GatedRating
    assert kinds["blast-radius"] is GatedRating
    assert kinds["code-quality"] is RatingAbstention


@pytest.mark.parametrize(
    "build",
    [
        lambda: _below_floor("architecture"),
        lambda: _not_applicable("requirement-fidelity"),
        _monorepo_code_quality,
        lambda: _failed("security"),
        lambda: _all_abstained("test-strategy"),
    ],
)
def test_gated_rating_cannot_wrap_evidence_lack(build) -> None:
    with pytest.raises(ValueError, match="missing evidence"):
        GatedRating(build(), 80, 1, (REF,))


# ---------------------------------------------------------------------------
# AC5 — warnings in the payload and the report
# ---------------------------------------------------------------------------


def _score(ratings) -> ScoreResult:
    return ScoreResult(
        ratings=ratings,
        overall=rate_overall(ratings),
        metrics=MetricSet(()),
        provenance=tuple((name, "fixture") for name in DIMENSIONS),
    )


def test_payload_carries_one_warning_per_evidence_lack_abstention() -> None:
    warnings = _score(_every_kind()).to_dict()["warnings"]
    assert [w["dimension"] for w in warnings] == [
        name
        for name in DIMENSIONS
        if name in {
            "architecture",
            "requirement-fidelity",
            "code-quality",
            "security",
            "test-strategy",
        }
    ]
    code_quality = next(w for w in warnings if w["dimension"] == "code-quality")
    assert code_quality["reason_code"] == "insufficient_measured_weight"
    assert code_quality["measured_share"] == "0.20"
    assert len(code_quality["unmeasured_rules"]) == 5
    assert code_quality["unmeasured_rules"][0] == {
        "metric_name": "functions_over_ccn_10_share",
        "reason": GONE.reason,
    }
    architecture = next(w for w in warnings if w["dimension"] == "architecture")
    assert architecture["sources_missing"] == [
        {"source": "REQUIREMENTS.md", "reason": "not found in target"}
    ]
    assert "no number" in code_quality["message"]


def test_no_warning_for_solution_fit_or_rated() -> None:
    ratings = tuple(
        _solution_fit() if name == "solution-fit" else _rated_far(name)
        for name in DIMENSIONS
    )
    assert _score(ratings).to_dict()["warnings"] == []


def test_report_renders_warning_block_with_dimension_and_rules() -> None:
    html = _render_unknowns(_Ctx(Path("/repo")), [], _score(_every_kind()))
    assert html.startswith('<section class="warning-banner unknowns">')
    assert "code-quality" in html
    assert "insufficient_measured_weight" in html
    assert "20%" in html
    assert "<code>functions_over_ccn_10_share</code>" in html
    assert "solution-fit" not in html


def test_report_renders_nothing_without_warnings() -> None:
    ratings = tuple(
        _solution_fit() if name == "solution-fit" else _rated_far(name)
        for name in DIMENSIONS
    )
    assert _render_unknowns(_Ctx(Path("/repo")), [], _score(ratings)) == ""


# ---------------------------------------------------------------------------
# AC6 — improvement plan lists what is missing
# ---------------------------------------------------------------------------


def test_plan_abstained_line_lists_unmeasured_rules_with_fix() -> None:
    ratings = _every_kind()
    plan = improvement_plan(ratings, rate_overall(ratings)).to_dict()
    line = next(a for a in plan["abstained"] if a["dimension"] == "code-quality")
    assert line["reason_code"] == "insufficient_measured_weight"
    assert [u["metric_name"] for u in line["unmeasured"]] == [
        name for name, _ in _monorepo_code_quality().unavailable_metrics
    ]
    first = line["unmeasured"][0]
    assert first["reason"] == GONE.reason
    assert first["fix"] == FIX_HINTS["functions_over_ccn_10_share"]
    # an abstention with no unmeasured rule keeps its three-key line
    architecture = next(
        a for a in plan["abstained"] if a["dimension"] == "architecture"
    )
    assert set(architecture) == {"dimension", "reason_code", "reason"}


def test_plan_totals_with_fewer_contributors() -> None:
    ratings = _every_kind()
    overall = rate_overall(ratings)
    contributors = (
        "blast-radius", "reliability", "supply-chain", "api", "data", "operations",
        "infrastructure",
    )
    assert overall.contributors == contributors
    plan = improvement_plan(ratings, overall)
    assert {item.dimension for item in plan.items} <= set(contributors)


# ---------------------------------------------------------------------------
# edge — the floor can remove every contributor
# ---------------------------------------------------------------------------


def test_overall_abstains_cleanly_when_floor_removes_every_contributor() -> None:
    ratings = tuple(
        _solution_fit()
        if name == "solution-fit"
        else _measured_only(name, next(iter(RATING_RULES[name])))
        for name in DIMENSIONS
    )
    assert all(type(item) is RatingAbstention for item in ratings)
    overall = rate_overall(ratings)
    assert overall.reason_code == "no_dimension_rated"
    plan = improvement_plan(ratings, overall)
    assert plan.items == ()
