"""T065 -- improvement plan: unmet rules grouped P0/P1/P2 with recomputed gain.

Every oracle number below is hand-computed from the declared arithmetic:
dimension = round(100 * earned / available), overall = round(mean of
contributors), Python round (ties to even), each rounded once.
"""

from __future__ import annotations

import json
from pathlib import Path

from easy_verifier.core.improve import FIX_HINTS, improvement_plan
from easy_verifier.core.judge import (
    DOCUMENTATION_RULES,
    RATING_RULES,
    GatedRating,
    Rating,
    RatingAbstention,
    rate_overall,
)
from easy_verifier.core.judge import rate as _rate
from easy_verifier.core.metrics import WHOLE_SET, Metric, MetricAbstention, MetricSet
from easy_verifier.core.models import CoverageSummary, SourceMiss
from easy_verifier.core.report import write_report
from easy_verifier.core.roles import documentation_present
from easy_verifier.core.score import score_repository
from easy_verifier.core.synthesis import combined_pack
from easy_verifier.dimensions import dimension_names

DIMENSIONS = dimension_names()
UNAVAILABLE = MetricAbstention("not measurable in this fixture")


# ---------------------------------------------------------------------------
# fixtures built through the real rating arithmetic
# ---------------------------------------------------------------------------


def _docs(dimension):
    return tuple(
        documentation_present(rule, ())
        for rule in DOCUMENTATION_RULES.get(dimension, ())
    )


def _passing(dimension: str, name: str) -> float:
    return RATING_RULES[dimension][name].threshold


def _rating(dimension: str, values: dict[str, object] | None = None):
    """Rated through ``judge.rate``; every metric passes unless overridden."""
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
    return _rate(MetricSet(metrics), coverage, documentation=_docs(dimension))


def _abstention(dimension: str) -> RatingAbstention:
    from easy_verifier.core.judge import COVERAGE_FLOORS

    return RatingAbstention(
        dimension=dimension,
        reason_code="below_coverage_floor",
        coverage_floor=COVERAGE_FLOORS[dimension].value,
        achieved_coverage=0.0,
        sources_missing=(SourceMiss("ARCHITECTURE.md", "not found in target"),),
        documentation=_docs(dimension),
    )


def _ratings(**rated) -> tuple:
    """All declared dimensions in canonical order; unnamed ones abstain."""
    return tuple(
        rated.get(name.replace("-", "_")) or _abstention(name) for name in DIMENSIONS
    )


def _plan(ratings):
    return improvement_plan(ratings, rate_overall(ratings)).to_dict()


def _item(plan, metric_name):
    found = [
        item
        for group in plan["groups"].values()
        for item in group
        if item["metric_name"] == metric_name
    ]
    assert len(found) == 1, metric_name
    return found[0]


def _requirement_fidelity_30() -> Rating:
    """30 = (15 + 15) / 100: code share 0.75 vs at_least 0.80 (gap 0.05,
    inside the 0.08 band -> P0), test share 0.5 (gap 0.30 -> P1)."""
    rating = _rating(
        "requirement-fidelity",
        {
            "acceptance_criteria_traced_to_code_share": 0.75,
            "acceptance_criteria_traced_to_test_share": 0.5,
        },
    )
    assert type(rating) is Rating and rating.value == 30
    return rating


# ---------------------------------------------------------------------------
# AC1, AC2, AC3: shape, grouping, recomputed gain
# ---------------------------------------------------------------------------


def test_plan_shape_and_every_item_field() -> None:
    plan = _plan(_ratings(requirement_fidelity=_requirement_fidelity_30()))
    assert list(plan["groups"]) == ["P0", "P1", "P2"]
    item = _item(plan, "acceptance_criteria_traced_to_code_share")
    assert item == {
        "group": "P0",
        "dimension": "requirement-fidelity",
        "area": RATING_RULES["requirement-fidelity"][
            "acceptance_criteria_traced_to_code_share"
        ].area,
        "metric_name": "acceptance_criteria_traced_to_code_share",
        "metric_value": 0.75,
        "unavailable_reason": None,
        "comparison": "at_least",
        "threshold": 0.8,
        "weight": 35,
        "computed_from": ["src/app.py"],
        # 30 -> 65; sole contributor, so the overall moves 30 -> 65 too
        "dimension_gain": 35,
        "overall_gain": 35,
        "gain_basis": "final",
        "fix": {
            "text": FIX_HINTS["acceptance_criteria_traced_to_code_share"],
            "source": "engine",
        },
    }


def test_near_miss_is_p0_and_far_failure_is_p1() -> None:
    plan = _plan(_ratings(requirement_fidelity=_requirement_fidelity_30()))
    names = {
        group: [item["metric_name"] for item in items]
        for group, items in plan["groups"].items()
    }
    assert names == {
        "P0": ["acceptance_criteria_traced_to_code_share"],
        "P1": ["acceptance_criteria_traced_to_test_share"],
        "P2": [],
    }


def test_threshold_zero_is_never_p0() -> None:
    # decision_records_missing = 0.05 fails at_most 0 by a hair; a zero
    # threshold has a zero-width band, so it is still a clear failure.
    rating = _rating("architecture", {"decision_records_missing": 0.05})
    plan = _plan(_ratings(architecture=rating))
    assert _item(plan, "decision_records_missing")["group"] == "P1"


def test_at_most_near_miss_respects_direction() -> None:
    # max_function_ccn at_most 15: 16 fails, |16-15| = 1 <= 1.5 -> P0;
    # 17 fails by 2 > 1.5 -> P1.
    near = _plan(_ratings(code_quality=_rating("code-quality", {"max_function_ccn": 16})))
    far = _plan(_ratings(code_quality=_rating("code-quality", {"max_function_ccn": 17})))
    assert _item(near, "max_function_ccn")["group"] == "P0"
    assert _item(far, "max_function_ccn")["group"] == "P1"


# ---------------------------------------------------------------------------
# AC5: recomputed, never weight share
# ---------------------------------------------------------------------------


def test_rounding_tie_uses_recomputed_gain_not_weight_share() -> None:
    # requirement-fidelity 30 + security 100 -> overall round(130/2) = 65.
    # Fixing the code share: 30 -> 65; overall round(165/2) = round(82.5)
    # = 82 (ties to even) -> gain 17. A weight share would say
    # round(35 / 2) = round(17.5) = 18.
    ratings = _ratings(
        requirement_fidelity=_requirement_fidelity_30(),
        security=_rating("security"),
    )
    assert rate_overall(ratings).value == 65
    item = _item(_plan(ratings), "acceptance_criteria_traced_to_code_share")
    assert item["dimension_gain"] == 35
    assert item["overall_gain"] == 17
    assert item["overall_gain"] != round(35 / 2)


# ---------------------------------------------------------------------------
# AC4: abstained metric -> P2 range, negative low kept
# ---------------------------------------------------------------------------


def test_abstained_metric_is_p2_with_a_range_and_negative_low() -> None:
    # architecture: description met (30), decision records unmet (30),
    # import cycles abstained -> 30/60 = 50; sole contributor -> overall 50.
    # Cycles measured and failing: 30/100 = 30 -> [-20]; passing: 70 -> [+20].
    rating = _rating(
        "architecture",
        {"decision_records_missing": 1, "top_level_import_cycles": UNAVAILABLE},
    )
    assert rating.value == 50
    plan = _plan(_ratings(architecture=rating))
    item = _item(plan, "top_level_import_cycles")
    assert item["group"] == "P2"
    assert item["dimension_gain"] == [-20, 20]
    assert item["overall_gain"] == [-20, 20]
    assert item["metric_value"] is None
    assert item["unavailable_reason"] == UNAVAILABLE.reason
    assert item["computed_from"] == []
    # the unmet measured rule: 50 -> 100
    decision = _item(plan, "decision_records_missing")
    assert (decision["group"], decision["overall_gain"]) == ("P1", 50)


# ---------------------------------------------------------------------------
# AC6: deterministic order
# ---------------------------------------------------------------------------


def test_order_is_gain_desc_then_dimension_then_metric() -> None:
    # architecture 50 (decision records unmet, w30 of 60) and security
    # 30 (redaction 35 + sink 35 unmet; lockfile 15 + cookie 15 met).
    # overall round(80/2) = 40.
    architecture = _rating(
        "architecture",
        {"decision_records_missing": 1, "top_level_import_cycles": UNAVAILABLE},
    )
    security = _rating(
        "security", {"redaction_hits_observed": 3, "sink_hits_observed": 3}
    )
    plan = _plan(_ratings(architecture=architecture, security=security))
    p1 = [(i["overall_gain"], i["dimension"], i["metric_name"]) for i in plan["groups"]["P1"]]
    # architecture fix: 100 -> round(130/2) = 65 -> +25
    # each security fix: 65 -> round(115/2) = round(57.5) = 58 -> +18
    assert p1 == [
        (25, "architecture", "decision_records_missing"),
        (18, "security", "redaction_hits_observed"),
        (18, "security", "sink_hits_observed"),
    ]
    # determinism: same input, same bytes
    assert json.dumps(plan) == json.dumps(
        _plan(_ratings(architecture=architecture, security=security))
    )


def test_p2_orders_by_high_end() -> None:
    # code-quality with only lint/format measured (both met, 20 of 20 = 100);
    # five metrics abstained. Sole contributor.
    values = {
        name: UNAVAILABLE
        for name in RATING_RULES["code-quality"]
        if name not in {"lint_config_missing", "format_config_missing"}
    }
    plan = _plan(_ratings(code_quality=_rating("code-quality", values)))
    p2 = plan["groups"]["P2"]
    highs = [item["overall_gain"][1] for item in p2]
    assert highs == sorted(highs, reverse=True)
    # pass keeps 100 -> high 0 for every one; fail of the w25 rule:
    # 20/45 = 44 -> low -56. Ties broken by metric name.
    assert all(high == 0 for high in highs)
    assert [item["metric_name"] for item in p2] == sorted(values)
    assert _item(plan, "functions_over_ccn_10_share")["overall_gain"] == [-56, 0]


# ---------------------------------------------------------------------------
# AC7: gated basis
# ---------------------------------------------------------------------------


def test_gated_dimension_gain_is_rules_part_and_labelled() -> None:
    rules = _rating(
        "architecture",
        {"decision_records_missing": 1, "top_level_import_cycles": UNAVAILABLE},
    )
    gated = GatedRating(rules, 90, 1, ("README.md:1-3",))
    assert gated.value == 70  # 50 x 0.5 + 90 x 0.5
    plan = _plan(_ratings(architecture=gated, security=_rating("security")))
    item = _item(plan, "decision_records_missing")
    assert item["gain_basis"] == "rules"
    # rules part 50 -> 100; overall on the rules basis round(150/2) = 75
    # -> round(200/2) = 100: +25. Never the blended 70.
    assert item["dimension_gain"] == 50
    assert item["overall_gain"] == 25
    assert _item(plan, "top_level_import_cycles")["gain_basis"] == "rules"


def test_non_gated_items_carry_final_basis() -> None:
    plan = _plan(_ratings(requirement_fidelity=_requirement_fidelity_30()))
    assert {
        item["gain_basis"] for items in plan["groups"].values() for item in items
    } == {"final"}


# ---------------------------------------------------------------------------
# AC8, AC9: abstained dimensions, no gaps
# ---------------------------------------------------------------------------


def test_abstained_dimension_yields_reason_line_and_no_items() -> None:
    plan = _plan(_ratings(security=_rating("security")))
    abstained = {item["dimension"]: item for item in plan["abstained"]}
    assert abstained["requirement-fidelity"] == {
        "dimension": "requirement-fidelity",
        "reason_code": "below_coverage_floor",
        "reason": "achieved coverage is below the declared floor",
    }
    assert set(abstained) == set(DIMENSIONS) - {"security"}
    for items in plan["groups"].values():
        assert all(item["dimension"] == "security" for item in items)


def test_agent_rated_dimension_reports_its_rules_abstention() -> None:
    gated = GatedRating(_abstention("architecture"), 80, 1, ("README.md:1-3",))
    plan = _plan(_ratings(architecture=gated))
    assert {"dimension": "architecture", "reason_code": "below_coverage_floor",
            "reason": "achieved coverage is below the declared floor"} in plan["abstained"]


def test_all_met_gives_empty_groups() -> None:
    ratings = tuple(
        _rating(name) if RATING_RULES[name] else _abstention(name)
        for name in DIMENSIONS
    )
    plan = _plan(ratings)
    assert plan["groups"] == {"P0": [], "P1": [], "P2": []}


def test_overall_abstention_gives_no_items() -> None:
    ratings = _ratings()
    plan = _plan(ratings)
    assert plan["groups"] == {"P0": [], "P1": [], "P2": []}
    assert len(plan["abstained"]) == len(DIMENSIONS)


# ---------------------------------------------------------------------------
# AC10: every rule has a fix line
# ---------------------------------------------------------------------------


def test_every_rating_rule_has_exactly_one_fix_hint() -> None:
    declared = {name for rules in RATING_RULES.values() for name in rules}
    assert set(FIX_HINTS) == declared
    assert all(isinstance(text, str) and text.strip() for text in FIX_HINTS.values())


# ---------------------------------------------------------------------------
# AC1, AC11 (shared path), AC12: score payload and report
# ---------------------------------------------------------------------------


def _repo(root: Path) -> Path:
    files = {
        "README.md": "# Demo\n\nA tiny service.\n",
        "src/app.py": "def add(a, b):\n    return a + b\n",
        "tests/test_app.py": "from app import add\n\n"
        "def test_add():\n    assert add(1, 2) == 3\n",
        "pyproject.toml": "[project]\nname = 'demo'\n",
    }
    for relative, text in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


def test_score_payload_carries_the_plan_of_its_own_ratings(tmp_path: Path) -> None:
    result = score_repository(_repo(tmp_path), scope="worktree")
    payload = result.to_dict()
    assert payload["improvement_plan"] == improvement_plan(
        result.ratings, result.overall
    ).to_dict()
    assert json.loads(result.serialize())["improvement_plan"] == payload[
        "improvement_plan"
    ]


def test_report_renders_plan_in_group_order_with_engine_label(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    packs = combined_pack(DIMENSIONS, repo_path=repo, scope="worktree")
    result = write_report([], packs, repo)
    document = (repo / result.path).read_text(encoding="utf-8")
    plan = score_repository(repo, scope="worktree").to_dict()["improvement_plan"]
    assert '<section class="improvement-plan">' in document
    assert "<h2>Improvement plan</h2>" in document
    positions = [document.index(f"<h3>{group}") for group in ("P0", "P1", "P2")]
    assert positions == sorted(positions)
    items = [item for group in plan["groups"].values() for item in group]
    assert items, "fixture repo should have at least one gap"
    for item in items:
        assert f"<code>{item['metric_name']}</code>" in document
    assert document.count('class="fix-source">engine<') == len(items)
    for line in plan["abstained"]:
        assert line["reason_code"] in document


def test_report_says_no_gaps_when_every_group_is_empty() -> None:
    from easy_verifier.core.improve import ImprovementPlan
    from easy_verifier.core.report import _Ctx, _render_improvement_plan

    html = _render_improvement_plan(
        _Ctx(Path("/repo")), ImprovementPlan(items=(), abstained=())
    )
    assert "No gaps" in html
