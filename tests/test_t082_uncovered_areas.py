"""T082 -- the score names the evaluation areas it measured and those no rule covers."""

from __future__ import annotations

import html
from pathlib import Path

from easy_verifier.core import judge
from easy_verifier.core.judge import (
    AREAS,
    DOCUMENTATION_RULES,
    RATING_RULES,
    Citation,
    DocumentationRule,
    GatedRating,
    OverallRating,
    Rating,
    RatingAbstention,
    RatingRule,
    areas_measured,
    areas_without_rule,
    rate,
)
from easy_verifier.core.metrics import WHOLE_SET, Metric, MetricAbstention, MetricSet
from easy_verifier.core.models import (
    CombinedPack,
    CoverageSummary,
    DimensionSlot,
    EvidencePack,
    Excerpt,
    SourceMiss,
)
from easy_verifier.core.report import write_report
from easy_verifier.core.roles import documentation_present
from easy_verifier.core.score import score_packs
from easy_verifier.dimensions import dimension_names

FIXTURE_CITATION = Citation("fixture", "https://example.org/fixture")


def _metrics(dimension: str, abstained: tuple[str, ...] = ()) -> MetricSet:
    return MetricSet(
        tuple(
            Metric(
                name=name,
                family="fixture",
                kind=WHOLE_SET,
                dimension=dimension,
                outcome=MetricAbstention("fixture: not measured")
                if name in abstained
                else rule.threshold,
                computed_from=("src/app.py",),
                derivation="fixture",
            )
            for name, rule in RATING_RULES[dimension].items()
        )
    )


def _coverage(dimension: str, score: float = 1.0) -> CoverageSummary:
    misses = () if score == 1.0 else (SourceMiss("x", "not found"),)
    return CoverageSummary(
        per_dimension=((dimension, score),),
        combined=score,
        method="fixture",
        misses=((dimension, misses),),
    )


def _docs(dimension: str, files: tuple[str, ...]):
    return tuple(
        documentation_present(rule, files)
        for rule in DOCUMENTATION_RULES.get(dimension, ())
    )


def _pack(target: Path, *, abstaining: frozenset[str]) -> CombinedPack:
    """All declared dimensions; those in ``abstaining`` read nothing they sought."""
    app_path = (target / "src/app.py").as_posix()
    test_path = (target / "tests/test_app.py").as_posix()
    slots, scores, misses = [], [], []
    for dimension in dimension_names():
        abstains = dimension in abstaining
        dimension_misses = (
            (SourceMiss("README.md", "not found in the target repository"),)
            if abstains
            else ()
        )
        score = 0.0 if abstains else 1.0
        pack = EvidencePack(
            dimension=dimension,
            mode="standalone",
            scope="project",
            files_read=(app_path, test_path),
            excerpts=(
                Excerpt(app_path, 1, 2, "def app():\n    return 1\n"),
                Excerpt(test_path, 1, 2, "def test_app():\n    assert app() == 1\n"),
            ),
            sources_sought=("README.md",),
            sources_found=() if abstains else ("README.md",),
            sources_missing=dimension_misses,
            coverage_score=score,
            truncated=False,
            omitted_count=0,
        )
        slots.append(DimensionSlot(dimension, pack, None))
        scores.append((dimension, score))
        misses.append((dimension, dimension_misses))
    return CombinedPack(
        slots=tuple(slots),
        coverage=CoverageSummary(
            per_dimension=tuple(scores),
            combined=sum(score for _name, score in scores) / len(scores),
            method="fixture coverage",
            misses=tuple(misses),
        ),
        budget_model="per-dimension",
    )


def _target(path: Path) -> Path:
    (path / "src").mkdir(parents=True)
    (path / "tests").mkdir()
    (path / "src/app.py").write_text("def app():\n    return 1\n", encoding="utf-8")
    (path / "tests/test_app.py").write_text(
        "def test_app():\n    assert app() == 1\n", encoding="utf-8"
    )
    return path


# --- AC 1/2: areas without a rule come from the live tables -----------------


def test_areas_without_rule_are_the_not_yet_rows_of_the_area_doc():
    # tests/ is on sys.path under pytest's default prepend import mode.
    from test_t072_area_coverage_doc import _rows

    not_yet = tuple(
        row["area"] for _n, row in sorted(_rows().items()) if row["status"] == "Not yet"
    )
    assert len(not_yet) == 21
    assert areas_without_rule() == not_yet


def test_adding_a_documentation_rule_removes_its_area(monkeypatch):
    financial = AREAS[2]
    assert financial in areas_without_rule()
    rule = DocumentationRule(financial, ("**/ledger*.md",), (FIXTURE_CITATION,))
    monkeypatch.setitem(DOCUMENTATION_RULES, "solution-fit", (rule,))
    assert financial not in areas_without_rule()
    assert len(areas_without_rule()) == 20


def test_adding_a_rating_rule_removes_its_area(monkeypatch):
    idempotency = AREAS[5]
    assert idempotency in areas_without_rule()
    extra = RatingRule(
        metric_name="fixture_metric",
        weight=1,
        threshold=0,
        comparison="<=",
        metric_citation=(FIXTURE_CITATION,),
        threshold_citation=judge.PROJECT_DEFAULT,
        area=idempotency,
    )
    rules = dict(RATING_RULES["code-quality"], fixture_metric=extra)
    monkeypatch.setitem(RATING_RULES, "code-quality", rules)
    assert idempotency not in areas_without_rule()


# --- AC 1: areas measured --------------------------------------------------


def test_abstained_metric_does_not_count_its_area():
    # todo_without_ticket_share is the only area-31 rule; 85% weight still rated.
    rating = rate(
        _metrics("code-quality", abstained=("todo_without_ticket_share",)),
        _coverage("code-quality"),
    )
    assert type(rating) is Rating
    assert areas_measured((rating,)) == (AREAS[16], AREAS[17])


def test_code_quality_only_measures_only_its_measured_areas():
    rated = rate(_metrics("code-quality"), _coverage("code-quality"))
    failed = RatingAbstention(
        dimension="architecture", reason_code="dimension_failed", failure="boom"
    )
    assert areas_measured((rated, failed)) == (AREAS[16], AREAS[17], AREAS[30])


def test_abstained_dimension_rule_areas_are_not_measured_but_its_doc_result_is():
    security = rate(
        _metrics("security"),
        _coverage("security", 0.0),
        documentation=_docs("security", ("src/app.py",)),
    )
    assert type(security) is RatingAbstention
    assert security.documentation, "security declares an offboarding doc rule"
    # rule areas 10 and 20 abstained; area 8 is measured only by its doc check
    assert areas_measured((security,)) == (AREAS[7],)


def test_blended_counts_rule_areas_and_agent_rated_counts_none():
    rated = rate(_metrics("code-quality"), _coverage("code-quality"))
    blended = GatedRating(rated, 50, 0.5, ("src/app.py:1-2",))
    assert areas_measured((blended,)) == areas_measured((rated,))
    no_rule = rate(MetricSet(()), _coverage("solution-fit"))
    agent = GatedRating(no_rule, 80, 1.0, ("src/app.py:1-2",))
    assert areas_measured((agent,)) == ()


def test_areas_measured_are_in_areas_order_without_duplicates():
    cq = rate(_metrics("code-quality"), _coverage("code-quality"))
    ts = rate(_metrics("test-strategy"), _coverage("test-strategy"))
    measured = areas_measured((cq, ts, cq))
    assert len(measured) == len(set(measured))
    assert measured == tuple(area for area in AREAS if area in measured)


# --- AC 3: disclosure; payload ---------------------------------------------


def test_overall_disclosure_states_the_measured_area_count(tmp_path):
    result = score_packs(_pack(_target(tmp_path / "t"), abstaining=frozenset()))
    assert type(result.overall) is OverallRating
    count = len(result.areas_measured)
    assert 0 < count < 32
    assert f"measured {count} of 32 evaluation areas" in result.overall.disclosure
    payload = result.to_dict()
    assert payload["areas_measured"] == list(result.areas_measured)
    assert payload["areas_without_rule"] == list(areas_without_rule())
    assert payload["overall"]["disclosure"] == result.overall.disclosure
    assert result.areas_measured == areas_measured(result.ratings)


def test_withheld_overall_still_carries_both_lists(tmp_path):
    result = score_packs(
        _pack(_target(tmp_path / "t"), abstaining=frozenset(dimension_names()))
    )
    assert type(result.overall) is RatingAbstention
    payload = result.to_dict()
    assert payload["areas_without_rule"] == list(areas_without_rule())
    assert "areas_measured" in payload
    assert payload["areas_measured"] == list(result.areas_measured)


def test_forged_overall_area_list_is_rejected():
    import pytest

    rated = rate(_metrics("code-quality"), _coverage("code-quality"))
    names = tuple(judge.COVERAGE_FLOORS)
    others = tuple(
        RatingAbstention(dimension=name, reason_code="dimension_failed", failure="x")
        for name in names
        if name != "code-quality"
    )
    base = dict(
        value=rated.value,
        contributor_count=1,
        total_dimension_count=len(names),
        contributors=("code-quality",),
        abstentions=others,
        contributor_values=(("code-quality", rated.value),),
        rated_by=(("code-quality", "rules"),),
    )
    OverallRating(**base, areas_measured=(AREAS[16], AREAS[17]))
    with pytest.raises(ValueError, match="areas_measured"):
        OverallRating(**base, areas_measured=("Not an area",))
    with pytest.raises(ValueError, match="areas_measured"):
        OverallRating(**base, areas_measured=(AREAS[17], AREAS[16]))


# --- AC 4/5: HTML report ---------------------------------------------------


def _document(tmp_path: Path, abstaining: frozenset[str]) -> str:
    target = _target(tmp_path / "t")
    result = write_report([], _pack(target, abstaining=abstaining), target)
    return (target / result.path).read_text(encoding="utf-8")


def test_report_panel_shows_count_and_folded_uncovered_list(tmp_path):
    document = _document(tmp_path, frozenset())
    missing = areas_without_rule()
    assert f"Areas no rule covers yet ({len(missing)})" in document
    assert "of 32 evaluation areas" in document
    for area in missing:
        assert html.escape(area, quote=True) in document
    # names carrying '&' are escaped like all other report text
    assert "Data model, constraints, migrations" in document
    assert "Vendor, BAA, data classification, residency" in document
    assert "Error handling &amp; safe degradation" in document
    assert "Error handling & safe degradation" not in document
    assert '<details class="areas-without-rule">' in document


def test_report_shows_area_lists_when_overall_is_withheld(tmp_path):
    document = _document(tmp_path, frozenset(dimension_names()))
    assert "Overall rating withheld" in document
    assert f"Areas no rule covers yet ({len(areas_without_rule())})" in document
    assert "of 32 evaluation areas" in document
