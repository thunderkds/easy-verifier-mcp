"""T070 — report readability: order, plan cards, merged unknowns, folding
(FR-065, US-020).

Presentation only: every number, citation and warning the report carried
before stays in the document; it is reordered and folded into ``<details>``.
Synthetic scores reuse T067/T069 builders, so every number is the real
``rate()`` arithmetic.
"""

from __future__ import annotations

import dataclasses
import html
import re
from pathlib import Path

from test_t067_evidence_floor import (
    GONE,
    REF,
    _all_abstained,
    _below_floor,
    _not_applicable,
    _rating,
    _score,
    _solution_fit,
)
from test_t069_report_summary import (
    SECRET,
    _by_name,
    _repo,
    _security_three_failures,
)

from easy_verifier.core.judge import (
    DOCUMENTATION_RULES,
    RATING_RULES,
    GatedRating,
    _measured_share,
)
from easy_verifier.core.report import (
    SENSITIVITY_ADVISORY,
    _Ctx,
    _render_document,
    _render_improvement_plan,
    _render_score_panel,
    _render_summary,
    _render_unknowns,
)
from easy_verifier.core.synthesis import combined_pack
from easy_verifier.dimensions import dimension_names

DIMENSIONS = dimension_names()
CTX = _Ctx(Path("/repo"))
ORDER = [
    "Before you share this report",
    "Summary",
    "Improvement plan",
    "What we couldn't measure",
    "Quality score",
    "Checklist coverage",
    "Dimensions",
]
CONTEXT_WARNINGS = [
    "Limited context: no requirements document was found. Requirement claims "
    "below are unanchored."
]


def _code_quality_p1_two_p2():
    # one clear failure, two abstained rules (still above the weight floor)
    names = list(RATING_RULES["code-quality"])
    return _rating(
        "code-quality",
        {"lint_config_missing": 1, names[-1]: GONE, names[-2]: GONE},
    )


def _criterion_one():
    """Success criterion 1: P0, P1x4, P2x2, three evidence warnings."""
    return _score(
        _by_name(
            **{"blast-radius": _rating("blast-radius", {"max_fan_in_changed": 21})},
            security=_security_three_failures(),
            **{"code-quality": _code_quality_p1_two_p2()},
            architecture=_below_floor("architecture"),
            **{"requirement-fidelity": _not_applicable("requirement-fidelity")},
            **{"test-strategy": _all_abstained("test-strategy")},
        )
    )


def _all_abstained_score():
    return _score(
        tuple(
            _solution_fit() if name == "solution-fit" else _below_floor(name)
            for name in DIMENSIONS
        )
    )


def _document(tmp_path: Path, score, improvements=None, agent_summary=None) -> str:
    repo = _repo(tmp_path / "target")
    packs = combined_pack(DIMENSIONS, repo_path=repo, scope="project")
    packs = dataclasses.replace(
        packs,
        slots=tuple(
            dataclasses.replace(
                slot,
                pack=dataclasses.replace(slot.pack, warnings=tuple(CONTEXT_WARNINGS)),
            )
            if index == 0
            else slot
            for index, slot in enumerate(packs.slots)
        ),
    )
    return _render_document(
        _Ctx(repo),
        {},
        packs,
        score,
        score.improvement_plan,
        improvements or {},
        agent_summary,
        first_write=True,
    )


def _section(document: str, cls: str) -> str:
    start = document.index(f'<section class="{cls}')
    return document[start : _close(document, start, "section")]


def _close(document: str, start: int, tag: str) -> int:
    """Index after the matching close tag (nesting-aware)."""
    depth, pos = 0, start
    pattern = re.compile(rf"<(/?){tag}\b")
    for match in pattern.finditer(document, start):
        depth += -1 if match.group(1) else 1
        if depth == 0:
            pos = match.end()
            break
    return document.index(">", pos) + 1


def _cards(plan_html: str) -> list[str]:
    starts = [m.start() for m in re.finditer(r'<article class="plan-card', plan_html)]
    return [plan_html[s : _close(plan_html, s, "article")] for s in starts]


# ---------------------------------------------------------------------------
# AC1 — order; AC1 share notice
# ---------------------------------------------------------------------------


def test_fixture_has_p0_four_p1_two_p2_three_warnings() -> None:
    score = _criterion_one()
    groups = [item.group for item in score.improvement_plan.items]
    assert groups.count("P0") == 1
    assert groups.count("P1") == 4
    assert groups.count("P2") == 2
    assert len(score.warnings) == 3


def test_sections_follow_the_fr065_order(tmp_path: Path) -> None:
    document = _document(tmp_path, _criterion_one())
    assert re.findall(r"<h2>([^<]*)</h2>", document) == ORDER
    assert document.index("</header>") < document.index('<section class="advisory">')


def test_share_notice_is_one_visible_line_with_full_text_folded(
    tmp_path: Path,
) -> None:
    advisory = _section(_document(tmp_path, _criterion_one()), "advisory")
    summary = re.search(r"<details><summary>(.*?)</summary>", advisory)
    assert summary is not None and "<" not in summary.group(1)
    folded = advisory[advisory.index("<details>") :]
    assert html.escape(SENSITIVITY_ADVISORY, quote=True) in folded


# ---------------------------------------------------------------------------
# AC2 — evidence-status line; no quality adjective
# ---------------------------------------------------------------------------


def test_summary_has_a_factual_evidence_status_line() -> None:
    score = _criterion_one()
    summary = _render_summary(CTX, score, score.improvement_plan, None, {})
    names = list(RATING_RULES["code-quality"])
    share = _measured_share(
        "code-quality", ((names[-1], "x"), (names[-2], "x"))
    )
    line = re.search(r'<p class="summary-evidence">(.*?)</p>', summary).group(1)
    assert line == (
        "Evidence: 4 of 8 dimensions rated; lowest measured rule weight "
        f"{share * 100:.0f}% (code-quality); 3 warnings — see What we "
        "couldn&#x27;t measure."
    )


def test_status_line_counts_context_warnings_too() -> None:
    score = _criterion_one()
    summary = _render_summary(
        CTX, score, score.improvement_plan, None, {}, context_warning_count=2
    )
    assert "; 5 warnings — see" in summary


def test_engine_text_carries_no_quality_adjective(tmp_path: Path) -> None:
    document = _document(tmp_path, _criterion_one())
    body = re.sub(r"<[^>]+>", " ", document.split("</style>", 1)[1]).lower()
    words = set(re.findall(r"[a-z]+", body))
    assert not words & {"good", "poor", "bad", "excellent", "healthy", "weak"}


# ---------------------------------------------------------------------------
# AC3 — plan cards
# ---------------------------------------------------------------------------


def test_plan_renders_cards_p2_closed_three_highlighted() -> None:
    score = _criterion_one()
    plan = _render_improvement_plan(CTX, score.improvement_plan)
    assert "<table" not in plan
    cards = _cards(plan)
    assert len(cards) == 7
    top = [i for i, card in enumerate(cards) if " plan-top\"" in card[:80]]
    assert top == [0, 1, 2]
    p2 = plan[plan.index("<h3>P2") - len('<details class="plan-group"><summary>') :]
    assert p2.startswith('<details class="plan-group"><summary>')
    p0_p1 = plan[: plan.index('<details class="plan-group">')]
    assert 'class="plan-group"' not in p0_p1
    assert "<details open" not in plan
    for card in cards:
        assert 'class="plan-gain"' in card
        assert "Now → rule" in card
        assert "<details><summary>" in card  # cited files or why not measured


def test_card_gain_badge_reads_overall_then_dimension() -> None:
    score = _criterion_one()
    item = score.improvement_plan.items[0]
    card = _cards(_render_improvement_plan(CTX, score.improvement_plan))[0]
    badge = re.search(r'<span class="plan-gain">(.*?)</span>', card).group(1)
    assert badge == (
        f"Gain {item.overall_gain:+d} overall / {item.dimension_gain:+d} "
        f"{item.dimension}"
    )


def test_agent_fix_sits_above_engine_fix_redacted_and_escaped() -> None:
    score = _criterion_one()
    item = score.improvement_plan.items[0]
    text = f"Rotate api_key={SECRET} <b>now</b>"
    plan = _render_improvement_plan(
        CTX, score.improvement_plan, {(item.dimension, item.metric_name): text}
    )
    card = _cards(plan)[0]
    assert SECRET not in card
    assert "&lt;b&gt;now&lt;/b&gt;" in card
    assert card.index(">agent<") < card.index(">engine<")
    assert plan.count(">agent<") == 1


# ---------------------------------------------------------------------------
# AC4 — merged unknowns
# ---------------------------------------------------------------------------


def test_unknowns_merge_context_and_evidence_warnings_one_line_each() -> None:
    score = _criterion_one()
    section = _render_unknowns(CTX, CONTEXT_WARNINGS, score)
    assert section.startswith(
        '<section class="warning-banner unknowns"><h2>What we couldn\'t measure</h2>'
    )
    items = re.findall(r'<li class="unknown">', section)
    assert len(items) == len(CONTEXT_WARNINGS) + len(score.warnings)
    assert section.count('<li class="unknown"><details><summary>') == len(items)
    for warning in score.warnings:
        assert html.escape(warning["message"], quote=True) in section
    assert html.escape(CONTEXT_WARNINGS[0], quote=True) in section


def test_unknowns_render_nothing_when_nothing_is_unknown() -> None:
    score = _score(_by_name())
    assert _render_unknowns(CTX, [], score) == ""


# ---------------------------------------------------------------------------
# AC5 — compact score rows
# ---------------------------------------------------------------------------


def test_score_rows_are_compact_with_detail_folded() -> None:
    score = _criterion_one()
    names = list(RATING_RULES["code-quality"])
    score = dataclasses.replace(
        score,
        samples=(
            {
                "dimension": "code-quality",
                "batches_done": 1,
                "batches_total": 6,
                "files_read": 200,
                "files_in_scope": 1178,
                "order": "purpose, churn, path",
            },
        ),
    )
    panel = _render_score_panel(CTX, score)
    starts = [m.start() for m in re.finditer(r'<article class="score-card', panel)]
    cards = [panel[s : _close(panel, s, "article")] for s in starts]
    assert len(cards) == len(DIMENSIONS)
    for card in cards:
        row = card[: card.index("<details")]
        assert '<p class="score-row">' in row
        assert "rating-inputs" not in row and "<a href" not in row
        assert re.search(r"<details><summary>", card)
    by_dim = {re.search(r"<h3>([^<]*)</h3>", c).group(1): c for c in cards}
    quality = by_dim["code-quality"]
    row = quality[: quality.index("<details")]
    met = len(names) - 3  # one failure, two abstained
    assert f"rules met {met}/{len(names)}" in row
    assert "Sample: batches 1 of 6" in row
    architecture = by_dim["architecture"]
    row = architecture[: architecture.index("<details")]
    assert "no number — below_coverage_floor" in row


def test_gated_row_shows_its_blend_parts() -> None:
    gated = GatedRating(
        rules=_solution_fit(), agent_score=80, confidence=0.6, evidence_refs=(REF,)
    )
    score = _score(_by_name(**{"solution-fit": gated}))
    panel = _render_score_panel(CTX, score)
    card = panel[panel.index("<h3>solution-fit</h3>") :]
    row = card[: card.index("<details")]
    assert html.escape(gated.parts, quote=True) in row


# ---------------------------------------------------------------------------
# AC6 — coverage and dimensions folded
# ---------------------------------------------------------------------------


def test_coverage_and_dimensions_are_closed_details_with_counts(
    tmp_path: Path,
) -> None:
    document = _document(tmp_path, _criterion_one())
    for cls, pattern in (
        ("coverage", r"\d+ dimensions; \d+ sources? missing"),
        ("dimensions", r"\d+ dimensions; \d+ findings?; \d+ files? read"),
    ):
        section = _section(document, cls)
        summary = re.search(r"<details><summary>(.*?)</summary>", section)
        assert summary is not None, cls
        assert re.fullmatch(pattern, summary.group(1)), summary.group(1)
        assert "<details open" not in section


# ---------------------------------------------------------------------------
# AC7 / AC8 — content preserved; self-contained
# ---------------------------------------------------------------------------


def test_every_plan_and_rule_number_and_citation_is_in_the_document(
    tmp_path: Path,
) -> None:
    score = _criterion_one()
    document = _document(tmp_path, score)
    data = score.improvement_plan.to_dict()
    for items in data["groups"].values():
        for item in items:
            assert f"<code>{item['metric_name']}</code>" in document
            for key in ("threshold", "weight", "comparison"):
                assert html.escape(str(item[key])) in document
            assert html.escape(item["fix"]["text"], quote=True) in document
    for rating in score.ratings:
        rules = getattr(rating, "rules", rating)
        for row in getattr(rules, "inputs", ()):
            assert f"earned {row.earned_weight}" in document
            for citation in row.metric_citation:
                if not isinstance(citation, str):
                    assert f'href="{html.escape(citation.url, quote=True)}"' in document
    for warning in score.warnings:
        assert html.escape(warning["message"], quote=True) in document


def test_no_script_and_only_citation_links(tmp_path: Path) -> None:
    document = _document(tmp_path, _criterion_one())
    assert "<script" not in document.lower()
    assert " src=" not in document
    urls = {
        citation.url
        for rules in RATING_RULES.values()
        for rule in rules.values()
        for citation in (*rule.metric_citation, rule.threshold_citation)
        if not isinstance(citation, str)
    } | {  # T043: documentation rules cite their standard too
        citation.url
        for rules in DOCUMENTATION_RULES.values()
        for rule in rules
        for citation in rule.citation
    }
    hrefs = set(re.findall(r'href="([^"]*)"', document))
    assert hrefs <= {html.escape(u, quote=True) for u in urls}


# ---------------------------------------------------------------------------
# AC9 — intentional empty states
# ---------------------------------------------------------------------------


def test_no_gaps_is_a_styled_block() -> None:
    score = _score(_by_name())
    plan = _render_improvement_plan(CTX, score.improvement_plan)
    assert '<p class="notice no-gaps">No gaps' in plan


def test_all_abstained_renders_a_no_number_block_and_lists_unknowns(
    tmp_path: Path,
) -> None:
    score = _all_abstained_score()
    document = _document(tmp_path, score)
    plan = _section(document, "improvement-plan")
    assert '<p class="notice notice-abstain">No number for any dimension' in plan
    assert "No gaps" not in plan
    summary = _section(document, "summary")
    assert '<p class="summary-overall notice notice-abstain">' in summary
    unknowns = _section(document, "warning-banner unknowns")
    evidence = '<li class="unknown"><details><summary><strong>'
    assert unknowns.count(evidence) == len(score.warnings)
    assert unknowns.count('<li class="unknown">') > len(score.warnings)
