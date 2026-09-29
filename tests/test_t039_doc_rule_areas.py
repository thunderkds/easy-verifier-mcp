"""T039 -- area labels on rules, the documentation rule, N-dimension overall."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from easy_verifier.core import judge
from easy_verifier.core.judge import (
    AREAS,
    COVERAGE_FLOORS,
    DOCUMENTATION_RULES,
    RATING_RULES,
    Citation,
    CoverageFloor,
    DocumentationResult,
    DocumentationRule,
    Rating,
    RatingAbstained,
    RatingAbstention,
    RatingInput,
    RatingRule,
    rate,
    rate_overall,
)
from easy_verifier.core.metrics import WHOLE_SET, Metric, MetricSet
from easy_verifier.core.models import CoverageSummary, SourceMiss
from easy_verifier.core.report import _Ctx, _render_score_card
from easy_verifier.core.roles import documentation_present

INCIDENT = "Incident response, change mgmt, access review"
NIST_61 = Citation(
    "NIST SP 800-61 (incident handling)",
    "https://csrc.nist.gov/pubs/sp/800/61/r2/final",
)
RUNBOOK_RULE = DocumentationRule(
    area=INCIDENT,
    patterns=("**/runbook*.md", "**/incident*.md"),
    citation=(NIST_61,),
)


def _docs(dimension: str, files: tuple[str, ...]) -> tuple[DocumentationResult, ...]:
    return tuple(
        documentation_present(rule, files)
        for rule in DOCUMENTATION_RULES.get(dimension, ())
    )


def _numbers(value: object) -> list[object]:
    """Every int/float anywhere inside a to_dict payload (bools excluded)."""
    if isinstance(value, bool):
        return []
    if isinstance(value, (int, float)):
        return [value]
    if isinstance(value, dict):
        return [n for item in value.values() for n in _numbers(item)]
    if isinstance(value, (list, tuple)):
        return [n for item in value for n in _numbers(item)]
    return []


def _metrics(dimension: str) -> MetricSet:
    return MetricSet(
        tuple(
            Metric(
                name=name,
                family="fixture",
                kind=WHOLE_SET,
                dimension=dimension,
                outcome=rule.threshold,
                computed_from=("src/app.py",),
                derivation="fixture",
            )
            for name, rule in RATING_RULES[dimension].items()
        )
    )


def _coverage(dimension: str, score: float | None = 1.0) -> CoverageSummary:
    misses = () if score in (None, 1.0) else (SourceMiss("x", "not found"),)
    return CoverageSummary(
        per_dimension=((dimension, score),),
        combined=score,
        method="fixture",
        misses=((dimension, misses),),
    )


# --- AC 1: area labels -------------------------------------------------------


def test_areas_are_the_users_32_names_in_table_order():
    assert len(AREAS) == 32
    assert len(set(AREAS)) == 32
    assert AREAS[0] == "Architecture & dependency direction"
    assert AREAS[24] == INCIDENT
    assert AREAS[31] == "Business continuity & degraded modes"


def test_every_declared_rule_carries_one_of_the_32_areas():
    for rules in RATING_RULES.values():
        for rule in rules.values():
            assert rule.area in AREAS, rule.metric_name


def test_rule_with_unknown_area_is_rejected(monkeypatch):
    rules = dict(RATING_RULES["architecture"])
    name = next(iter(rules))
    rules[name] = replace(rules[name], area="Vibes")
    monkeypatch.setitem(RATING_RULES, "architecture", rules)
    with pytest.raises(ValueError, match="area"):
        rate(_metrics("architecture"), _coverage("architecture"))


def test_rating_inputs_carry_their_rule_area_in_score_output():
    result = rate(_metrics("code-quality"), _coverage("code-quality"))
    assert isinstance(result, Rating)
    areas = {item.metric_name: item.area for item in result.inputs}
    assert areas == {
        name: rule.area for name, rule in RATING_RULES["code-quality"].items()
    }
    for item in result.to_dict()["inputs"]:
        assert item["area"] == areas[item["metric_name"]]


def test_forged_input_area_is_rejected():
    result = rate(_metrics("architecture"), _coverage("architecture"))
    with pytest.raises(ValueError, match="declared rule"):
        replace(result.inputs[0], area=AREAS[5])


def test_existing_output_shape_only_gains_area_labels():
    """AC 4: without documentation rules a Rating's payload keys are the
    pre-T039 keys, and each input gains exactly one key: ``area``."""
    result = rate(_metrics("architecture"), _coverage("architecture"))
    payload = result.to_dict()
    assert set(payload) == {
        "kind", "dimension", "value", "inputs", "unavailable_metrics", "method"
    }
    assert set(payload["inputs"][0]) == {
        "metric_name", "metric_value", "weight", "threshold", "comparison",
        "passed", "earned_weight", "computed_from", "metric_citation",
        "threshold_citation", "source_tag", "area",
    }
    abstention = rate(_metrics("solution-fit"), _coverage("solution-fit"))
    assert abstention.reason_code == "no_static_rule"
    assert "documentation" not in abstention.to_dict()


# --- AC 2: documentation_present --------------------------------------------


def test_runbook_present_cites_file_and_carries_no_number():
    result = documentation_present(
        RUNBOOK_RULE, ("README.md", "docs/runbook.md", "src/app.py")
    )
    assert result.status == "present"
    assert result.file == "docs/runbook.md"
    assert result.area == INCIDENT
    payload = result.to_dict()
    assert payload["kind"] == "documentation"
    assert payload["status"] == "present"
    assert payload["file"] == "docs/runbook.md"
    assert _numbers(payload) == []
    assert not hasattr(result, "value")
    assert not hasattr(result, "weight")
    assert not hasattr(result, "numeric_value")


def test_runbook_missing_says_what_bounded_the_search():
    result = documentation_present(RUNBOOK_RULE, ("README.md", "src/app.py"))
    assert result.status == "missing"
    assert result.file is None
    assert "read" in result.reason
    assert _numbers(result.to_dict()) == []


def test_present_picks_the_first_match_in_sorted_order():
    result = documentation_present(
        RUNBOOK_RULE, ("ops/runbook.md", "docs/incident-response.md")
    )
    assert result.file == "docs/incident-response.md"


def test_documentation_result_rejects_incoherent_states():
    with pytest.raises(ValueError):
        DocumentationResult(INCIDENT, "present", None, (NIST_61,), "")
    with pytest.raises(ValueError):
        DocumentationResult(INCIDENT, "missing", "docs/runbook.md", (NIST_61,), "x")
    with pytest.raises(ValueError):
        DocumentationResult(INCIDENT, "partial", None, (NIST_61,), "x")
    with pytest.raises(ValueError):
        DocumentationResult("Vibes", "missing", None, (NIST_61,), "x")
    with pytest.raises(ValueError):
        DocumentationRule(area=INCIDENT, patterns=(), citation=(NIST_61,))


def test_documentation_rule_adds_zero_weight_to_a_rating(monkeypatch):
    plain = rate(
        _metrics("architecture"),
        _coverage("architecture"),
        documentation=_docs("architecture", ("x.md",)),
    )
    monkeypatch.setitem(DOCUMENTATION_RULES, "architecture", (RUNBOOK_RULE,))
    with_doc = rate(
        _metrics("architecture"),
        _coverage("architecture"),
        documentation=_docs("architecture", ("docs/runbook.md",)),
    )
    assert isinstance(with_doc, Rating)
    assert with_doc.value == plain.value
    assert with_doc.inputs == plain.inputs
    assert [d.status for d in with_doc.documentation] == ["present"]
    assert with_doc.to_dict()["documentation"][0]["file"] == "docs/runbook.md"


def test_dimension_with_only_documentation_rules_abstains_explicitly(monkeypatch):
    monkeypatch.setitem(DOCUMENTATION_RULES, "solution-fit", (RUNBOOK_RULE,))
    result = rate(
        _metrics("solution-fit"),
        _coverage("solution-fit"),
        documentation=_docs("solution-fit", ("docs/runbook.md",)),
    )
    assert isinstance(result, RatingAbstention)
    assert result.reason_code == "documentation_only"
    assert "documentation" in result.reason
    assert "never" in result.reason
    assert [d.status for d in result.documentation] == ["present"]
    with pytest.raises(RatingAbstained):
        _ = result.numeric_value
    assert "value" not in result.to_dict()


def test_no_static_rule_is_not_used_when_documentation_rules_exist(monkeypatch):
    """Two causes, two codes: never let one sentinel mean both."""
    monkeypatch.setitem(DOCUMENTATION_RULES, "solution-fit", (RUNBOOK_RULE,))
    with pytest.raises(ValueError):
        RatingAbstention(
            "solution-fit", "no_static_rule", coverage_floor=0.5
        )
    monkeypatch.setitem(DOCUMENTATION_RULES, "solution-fit", ())
    with pytest.raises(ValueError):
        RatingAbstention(
            "solution-fit", "documentation_only", coverage_floor=0.5
        )


def test_failed_dimension_reports_no_documentation_result(monkeypatch):
    """No pack means nothing was read: a 'missing' would be invented."""
    monkeypatch.setitem(DOCUMENTATION_RULES, "architecture", (RUNBOOK_RULE,))
    failed = MetricSet((), dimensions_without_pack=(("architecture", "boom"),))
    result = rate(failed, _coverage("architecture", None))
    assert result.reason_code == "dimension_failed"
    assert result.documentation == ()


def test_rate_requires_results_when_documentation_rules_are_declared(monkeypatch):
    monkeypatch.setitem(DOCUMENTATION_RULES, "architecture", (RUNBOOK_RULE,))
    with pytest.raises(ValueError, match="documentation"):
        rate(_metrics("architecture"), _coverage("architecture"))


def test_documentation_results_must_match_declared_rules(monkeypatch):
    monkeypatch.setitem(DOCUMENTATION_RULES, "architecture", (RUNBOOK_RULE,))
    result = rate(
        _metrics("architecture"),
        _coverage("architecture"),
        documentation=_docs("architecture", ()),
    )
    with pytest.raises(ValueError, match="documentation"):
        replace(result, documentation=())


def test_score_packs_feeds_files_read_to_documentation_rules(monkeypatch, tmp_path):
    # tests/ is on sys.path under pytest's default prepend import mode.
    from test_score_operation import _complete_pack_with_architecture_abstaining

    from easy_verifier.core.score import score_packs

    target = tmp_path / "target"
    target.mkdir()
    packs = _complete_pack_with_architecture_abstaining(target)
    monkeypatch.setitem(DOCUMENTATION_RULES, "test-strategy", (RUNBOOK_RULE,))
    result = score_packs(packs)
    by_dimension = {item.dimension: item for item in result.ratings}
    docs = by_dimension["test-strategy"].documentation
    assert [d.status for d in docs] == ["missing"]


# --- AC 3: N declared dimensions --------------------------------------------


@pytest.fixture
def eight_dimensions(monkeypatch):
    citation = Citation("fixture", "https://example.org/fixture")
    floors = {f"d{i}": CoverageFloor(0.5, "inclusive") for i in range(1, 9)}
    rules = {
        f"d{i}": (
            {
                f"m{i}": RatingRule(
                    f"m{i}", 100, 0, "at_most", (citation,), citation,
                    area=AREAS[0],
                )
            }
            if i <= 4
            else {}
        )
        for i in range(1, 9)
    }
    monkeypatch.setattr(judge, "COVERAGE_FLOORS", floors)
    monkeypatch.setattr(judge, "RATING_RULES", rules)
    monkeypatch.setattr(judge, "DOCUMENTATION_RULES", {})
    return citation


def _fake_rating(i: int, metric_value: int, citation: Citation) -> Rating:
    passed = metric_value == 0
    return Rating(
        f"d{i}",
        100 if passed else 0,
        (
            RatingInput(
                f"m{i}", metric_value, 100, 0, "at_most", passed,
                100 if passed else 0, ("a.py",), (citation,), citation,
                "curated", area=AREAS[0],
            ),
        ),
    )


def test_overall_averages_raters_over_eight_declared_dimensions(eight_dimensions):
    ratings = [
        _fake_rating(1, 0, eight_dimensions),
        _fake_rating(2, 0, eight_dimensions),
        _fake_rating(3, 0, eight_dimensions),
        _fake_rating(4, 5, eight_dimensions),
    ] + [
        RatingAbstention(f"d{i}", "no_static_rule", coverage_floor=0.5)
        for i in range(5, 9)
    ]
    overall = rate_overall(ratings)
    assert overall.value == 75
    assert overall.total_dimension_count == 8
    assert overall.contributor_count == 4
    assert overall.disclosure.startswith("4 of 8 dimensions contributed")


def test_overall_rejects_a_missing_declared_dimension(eight_dimensions):
    ratings = [_fake_rating(i, 0, eight_dimensions) for i in range(1, 5)] + [
        RatingAbstention(f"d{i}", "no_static_rule", coverage_floor=0.5)
        for i in range(5, 8)
    ]
    with pytest.raises(ValueError, match="declared dimensions"):
        rate_overall(ratings)


def test_all_abstain_reason_does_not_claim_seven(eight_dimensions):
    overall = rate_overall(
        [
            RatingAbstention(f"d{i}", "coverage_not_applicable", coverage_floor=0.5)
            for i in range(1, 5)
        ]
        + [
            RatingAbstention(f"d{i}", "no_static_rule", coverage_floor=0.5)
            for i in range(5, 9)
        ]
    )
    assert overall.reason_code == "no_dimension_rated"
    assert "seven" not in overall.reason
    assert len(overall.abstentions) == 8


def test_documentation_only_dimension_is_excluded_from_overall(monkeypatch):
    monkeypatch.setitem(DOCUMENTATION_RULES, "solution-fit", (RUNBOOK_RULE,))
    ratings = [
        rate(
            _metrics(name),
            _coverage(name),
            documentation=_docs(name, ("docs/runbook.md",)),
        )
        for name in COVERAGE_FLOORS
    ]
    overall = rate_overall(ratings)
    assert "solution-fit" not in overall.contributors
    assert "solution-fit (documentation_only" in overall.disclosure


# --- report: grouped by area inside each dimension card ---------------------


def test_report_card_groups_inputs_by_area_and_shows_documentation(monkeypatch):
    monkeypatch.setitem(DOCUMENTATION_RULES, "code-quality", (RUNBOOK_RULE,))
    result = rate(
        _metrics("code-quality"),
        _coverage("code-quality"),
        documentation=_docs("code-quality", ("docs/runbook.md",)),
    )
    card = _render_score_card(_Ctx(Path("/repo")), result, None, None)
    areas = [rule.area for rule in RATING_RULES["code-quality"].values()]
    for area in dict.fromkeys(areas):
        escaped = area.replace("&", "&amp;")
        assert card.count(f'<h4 class="rating-area">{escaped}</h4>') == 1
    assert '<h4 class="rating-area">Incident response' in card
    assert "Documentation present" in card
    assert "docs/runbook.md" in card
    assert "not scored" in card


def test_report_card_renders_missing_documentation_on_abstention(monkeypatch):
    monkeypatch.setitem(DOCUMENTATION_RULES, "solution-fit", (RUNBOOK_RULE,))
    result = rate(
        _metrics("solution-fit"),
        _coverage("solution-fit"),
        documentation=_docs("solution-fit", ()),
    )
    card = _render_score_card(_Ctx(Path("/repo")), result, None, None)
    assert "documentation_only" in card
    assert "Documentation missing" in card
    assert "/100" not in card
