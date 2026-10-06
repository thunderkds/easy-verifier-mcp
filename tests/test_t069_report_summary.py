"""T069 — the report opens with a short summary (FR-063, FR-064, US-019).

The engine summary is templated from the score only: overall, how many
dimensions were rated, the top three P0/P1 plan items with their gain and
cited standard, and one line per evidence-lack warning. The calling agent may
add one paragraph, labelled agent. Every detail section follows unchanged.

Synthetic scores reuse T067's builders, so every number is the real
``rate()`` arithmetic.
"""

from __future__ import annotations

import asyncio
import dataclasses
import importlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest
from test_t067_evidence_floor import (
    REF,
    _all_abstained,
    _below_floor,
    _bryony_code_quality,
    _failed,
    _not_applicable,
    _rating,
    _score,
    _solution_fit,
)

import easy_verifier.core.report as report
from easy_verifier.core.findings import ValidationError
from easy_verifier.core.judge import RATING_RULES, GatedRating
from easy_verifier.core.models import SourceMiss
from easy_verifier.core.report import _Ctx, _render_summary, write_report
from easy_verifier.core.roles import RoleInputError, validate_agent_input
from easy_verifier.core.synthesis import combined_pack
from easy_verifier.dimensions import dimension_names

REPO_ROOT = Path(__file__).resolve().parents[1]
DIMENSIONS = dimension_names()
CTX = _Ctx(Path("/repo"))

# Assembled at runtime: never commit a whole credential-shaped literal.
SECRET = "FAKEfake" + "9Qx7Lm2Vt8Rk4Wz6Np3Jh5"


def _passing_all(dimension: str):
    return _rating(dimension)


def _by_name(**overrides):
    """Every dimension rated and passing, solution-fit no_static_rule, then
    ``overrides``."""
    ratings = {
        name: _solution_fit() if name == "solution-fit" else _passing_all(name)
        for name in DIMENSIONS
    }
    ratings.update(overrides)
    return tuple(ratings[name] for name in DIMENSIONS)


def _security_three_failures():
    # three clear failures, cookie flags met: 15/100
    return _rating(
        "security",
        {"redaction_hits_observed": 3, "sink_hits_observed": 2, "lockfile_missing": 1},
    )


def _architecture_missing_roles():
    """Below the floor with two declared roles not found."""
    return dataclasses.replace(
        _below_floor("architecture"),
        sources_missing=(
            SourceMiss("architecture-doc", "not found in target"),
            SourceMiss("decision-record", "not found in target"),
        ),
    )


def _two_rated_four_warnings():
    """Success criterion 1: security + blast-radius rated, 3 P1 items, four
    evidence-lack warnings, solution-fit without a static rule."""
    return _by_name(
        architecture=_architecture_missing_roles(),
        **{"requirement-fidelity": _not_applicable("requirement-fidelity")},
        **{"code-quality": _bryony_code_quality()},
        security=_security_three_failures(),
        **{"test-strategy": _all_abstained("test-strategy")},
    )


def _summary(score, agent_summary=None, scopes=None) -> str:
    return _render_summary(
        CTX, score, score.improvement_plan, agent_summary, scopes or {}
    )


def _block(html: str, cls: str) -> str:
    start = html.index(f'class="{cls}"')
    tag = html.rindex("<", 0, start)
    name = html[tag + 1 : start].strip()
    return html[tag : html.index(f"</{name}>", start)]


def _items(html: str, cls: str) -> list[str]:
    return re.findall(r"<li>(.*?)</li>", _block(html, cls))


# ---------------------------------------------------------------------------
# AC2 / AC3 / AC4 — content
# ---------------------------------------------------------------------------


def test_two_rated_three_focus_items_four_warnings() -> None:
    score = _score(_two_rated_four_warnings())
    html = _summary(score)
    assert html.startswith('<section class="summary"><h2>Summary</h2>')

    overall = _block(html, "summary-overall")
    assert f"Overall <strong>{score.overall.value}/100</strong>" in overall
    # T043: reliability is rated and passing by default (_by_name).
    assert "3 of 8 dimensions rated" in overall
    assert "reliability 100" in overall
    assert "security 15" in overall
    assert "blast-radius 100" in overall

    focus = _items(html, "summary-focus")
    plan = [i for i in score.improvement_plan.items if i.group in ("P0", "P1")]
    assert len(plan) == 3 and len(focus) == 3
    for line, item in zip(focus, plan, strict=True):
        assert f"<strong>{item.dimension}</strong>" in line
        assert report._METRIC_TEXT[item.metric_name] in line
        assert f"now {item.metric_value}, rule at most 0" in line
        assert f"{item.overall_gain:+d} overall" in line
        assert "<code>" not in line  # no metric-name tag
        rule = RATING_RULES[item.dimension][item.metric_name]
        first, *others = rule.metric_citation
        assert f'href="{first.url}"' in line
        assert first.label.split(" (")[0] in line
        for citation in others:  # only the first metric citation
            assert f'href="{citation.url}"' not in line

    missing = _items(html, "summary-missing")
    assert [re.search(r"<strong>(.*?)</strong>", m).group(1) for m in missing] == [
        w["dimension"] for w in score.warnings
    ]
    assert len(missing) == 4
    assert all("<code>" not in m for m in missing)
    code_quality = next(m for m in missing if "code-quality" in m)
    assert code_quality == "<strong>code-quality</strong>: 5 rules not measured"
    architecture = next(m for m in missing if "<strong>architecture" in m)
    assert architecture == (
        "<strong>architecture</strong>: no architecture doc or decision records"
    )
    # solution-fit is neither rated nor a warning: it is named once, shortly
    assert (
        "<p>Not rated: solution-fit — rated only by the calling agent "
        "(MCP evaluate gate).</p>"
    ) in html
    assert "agent" not in html.replace("calling agent", "").replace(
        "agent evaluation", ""
    )


def test_only_the_top_three_p0_p1_items_are_shown_in_plan_order() -> None:
    # blast-radius near miss (P0) + four test-strategy failures (P1)
    score = _score(
        _by_name(
            **{
                "blast-radius": _rating("blast-radius", {"max_fan_in_changed": 21}),
                "test-strategy": _rating(
                    "test-strategy",
                    {
                        "source_files_without_covering_test_share": 0.9,
                        "assertion_density_per_test": 0.1,
                        "tests_without_assertions_share": 0.9,
                        "skipped_test_share": 0.9,
                    },
                ),
            }
        )
    )
    plan = [i for i in score.improvement_plan.items if i.group in ("P0", "P1")]
    assert len(plan) == 5 and plan[0].group == "P0"
    focus = _items(_summary(score), "summary-focus")
    assert len(focus) == 3
    for line, item in zip(focus, plan[:3], strict=True):
        assert report._METRIC_TEXT[item.metric_name] in line
    for item in plan[3:]:
        assert report._METRIC_TEXT[item.metric_name] not in _summary(score)


def test_project_default_threshold_is_not_shown() -> None:
    security = _rating("security", {"cookie_flags_missing_observed": 2})
    score = _score(_by_name(security=security))
    (line,) = _items(_summary(score), "summary-focus")
    assert "threshold" not in line and "project default" not in line
    assert line.count("<a ") == 1  # the metric's standard only


def test_a_distinct_threshold_citation_is_shown() -> None:
    code_quality = _rating("code-quality", {"max_function_ccn": 30})
    (line,) = _items(
        _summary(_score(_by_name(**{"code-quality": code_quality}))), "summary-focus"
    )
    rule = RATING_RULES["code-quality"]["max_function_ccn"]
    assert f'; threshold: <a href="{rule.threshold_citation.url}"' in line
    assert line.count("<a ") == 2


def test_threshold_citation_shared_with_the_metric_is_not_repeated() -> None:
    score = _score(_by_name(security=_rating("security", {"lockfile_missing": 1})))
    (line,) = _items(_summary(score), "summary-focus")
    assert "threshold:" not in line
    assert line.count("<a ") == 1


# ---------------------------------------------------------------------------
# AC5 — the plain cases
# ---------------------------------------------------------------------------


def test_no_gaps_and_no_warnings_says_so_plainly() -> None:
    score = _score(_by_name())
    html = _summary(score)
    assert score.improvement_plan.items == () and score.warnings == []
    assert '<p class="no-gaps">No gaps: every measured rule is met.</p>' in html
    assert "summary-focus" not in html and "summary-missing" not in html
    assert "7 of 8 dimensions rated" in html


def test_overall_abstained_says_no_dimension_could_be_rated() -> None:
    ratings = (
        _below_floor("architecture"),
        _solution_fit(),
        _not_applicable("requirement-fidelity"),
        _bryony_code_quality(),
        _failed("security"),
        _all_abstained("test-strategy"),
        _below_floor("blast-radius"),
        _below_floor("reliability"),
    )
    html = _summary(_score(ratings))
    assert "Overall: no number — none of the 8 dimensions could be rated." in html
    assert "/100" not in html
    assert len(_items(html, "summary-missing")) == 7


def test_unmeasured_only_gaps_point_to_the_plan() -> None:
    from test_t067_evidence_floor import GONE

    score = _score(
        _by_name(
            **{"code-quality": _rating("code-quality", {"max_function_ccn": GONE})}
        )
    )
    html = _summary(score)
    assert "No measured rule fails; 1 rule could not be measured" in html
    assert "summary-focus" not in html


def test_requirement_and_ci_roles_get_plain_names() -> None:
    requirement = dataclasses.replace(
        _below_floor("requirement-fidelity"),
        sources_missing=(
            SourceMiss("requirements-doc", "not found in target"),
            SourceMiss("task-breakdown", "not found in target"),
        ),
    )
    tests = dataclasses.replace(
        _below_floor("test-strategy"),
        sources_missing=(
            SourceMiss("ci-workflow", "not found in target"),
            SourceMiss(
                "source-to-test correspondence for files in the active scope",
                "no source file in scope",
            ),
        ),
    )
    html = _summary(
        _score(
            _by_name(**{"requirement-fidelity": requirement, "test-strategy": tests})
        )
    )
    lines = _items(html, "summary-missing")
    assert lines[0] == (
        "<strong>requirement-fidelity</strong>: no requirements doc; "
        "1 other source not found"
    )
    # the derived correspondence miss is not something to add: not named
    assert lines[1] == "<strong>test-strategy</strong>: no CI workflow"


def test_an_undeclared_source_is_counted_never_quoted() -> None:
    html = _summary(_score(_by_name(architecture=_below_floor("architecture"))))
    (line,) = _items(html, "summary-missing")
    assert "REQUIREMENTS.md" not in html
    assert line == "<strong>architecture</strong>: 1 other source not found"


def test_blast_radius_at_project_scope_says_to_run_on_a_change() -> None:
    blast = _all_abstained("blast-radius")
    score = _score(_by_name(**{"blast-radius": blast}))
    project = _summary(score, scopes={"blast-radius": "project"})
    (line,) = _items(project, "summary-missing")
    assert line == (
        "<strong>blast-radius</strong>: measured only on a change: run with "
        "--scope changes (a commit, range or branch)"
    )
    changes = _summary(score, scopes={"blast-radius": "changes"})
    (line,) = _items(changes, "summary-missing")
    assert "rules not measured" in line and "--scope" not in line


def test_failed_dimension_line_uses_its_reason() -> None:
    html = _summary(_score(_by_name(security=_failed("security"))))
    (line,) = _items(html, "summary-missing")
    assert line.startswith("<strong>security</strong>: ")
    assert "dimension" in line and "not measured" not in line


# ---------------------------------------------------------------------------
# Edge cases — gated, sampled, no score
# ---------------------------------------------------------------------------


def test_agent_rated_solution_fit_counts_as_rated_and_is_labelled() -> None:
    gated = GatedRating(_solution_fit(), 80, 1, (REF,))
    html = _summary(_score(_by_name(**{"solution-fit": gated})))
    assert "8 of 8 dimensions rated" in html
    assert "solution-fit 80 (agent-rated)" in html
    assert "Not rated" not in html


def test_blended_dimension_is_labelled_blended() -> None:
    near_miss = _rating("blast-radius", {"max_fan_in_changed": 21})
    gated = GatedRating(near_miss, 80, 1, (REF,))
    html = _summary(_score(_by_name(**{"blast-radius": gated})))
    assert f"blast-radius {gated.value} (blended with an agent evaluation)" in html


def test_sampled_dimension_shows_its_sample() -> None:
    score = dataclasses.replace(
        _score(_by_name()),
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
    assert "code-quality 100 (sample: 200 of 1,178 files)" in _summary(score)


def test_no_score_is_one_line() -> None:
    html = _render_summary(CTX, None, None, None, {})
    assert html == (
        '<section class="summary"><h2>Summary</h2><p class="summary-overall">'
        "No score in this report: it does not cover every declared dimension."
        "</p></section>"
    )


def test_summary_is_a_pure_function_of_the_score() -> None:
    assert _summary(_score(_two_rated_four_warnings())) == _summary(
        _score(_two_rated_four_warnings())
    )


# ---------------------------------------------------------------------------
# AC1 / AC6 / AC7 — through write_report on a real directory
# ---------------------------------------------------------------------------

SCOPE = "project"


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


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    return _repo(tmp_path / "target")


def _write(repo: Path, agent_input=None, dimensions=None) -> str:
    packs = combined_pack(dimensions or DIMENSIONS, repo_path=repo, scope=SCOPE)
    result = write_report([], packs, repo, agent_input=agent_input)
    return (repo / result.path).read_text(encoding="utf-8")


def _strip_summary(document: str) -> str:
    start = document.index('<section class="summary">')
    end = document.index("</section>", start) + len("</section>\n")
    return document[:start] + document[end:]


def test_summary_is_the_first_section_after_header_and_advisory(repo: Path) -> None:
    document = _write(repo)
    headings = re.findall(r"<h2>([^<]*)</h2>", document)
    assert headings[:2] == ["Before you share this report", "Summary"]
    assert "Quality score" in headings[2:] and "Dimensions" in headings[2:]
    assert document.index("</header>") < document.index('<section class="summary">')


class _FrozenClock:
    """Both documents carry the same generated-at text and filename stamp."""

    @staticmethod
    def now(_tz=None):
        from datetime import UTC, datetime

        return datetime(2026, 10, 4, tzinfo=UTC)


def test_detail_sections_are_unchanged_by_the_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC6: removing the summary section leaves exactly the document the
    renderer produces with no summary at all."""
    monkeypatch.setattr(report, "datetime", _FrozenClock)
    with_summary = _write(
        _repo(tmp_path / "a" / "target"), {"summary": "Focus on formatting first."}
    )
    monkeypatch.setattr(report, "_render_summary", lambda *a, **k: "")
    without = _write(_repo(tmp_path / "b" / "target"))
    assert '<section class="summary">' not in without
    assert _strip_summary(with_summary) == without.replace("\n\n", "\n", 1)


def test_agent_summary_is_redacted_escaped_and_labelled_agent(repo: Path) -> None:
    text = f"Hey, rotate api_key={SECRET} then <script>alert(1)</script> & go"
    document = _write(repo, {"summary": f"  {text}  "})
    assert SECRET not in document
    assert "<script>alert(1)</script>" not in document
    summary = _block(document, "summary")
    agent = _block(summary, "summary-agent")
    assert "&lt;script&gt;alert(1)&lt;/script&gt; &amp; go" in agent
    assert "Hey, rotate api_" in agent  # redaction, not suppression
    assert '<span class="fix-source fix-source-agent">agent</span>' in agent


def test_no_agent_summary_means_no_agent_paragraph(repo: Path) -> None:
    assert 'class="summary-agent"' not in _write(repo)


@pytest.mark.parametrize(
    ("value", "reason"),
    [
        ("", "must not be empty"),
        ("   \n\t", "must not be empty"),
        ("x" * 2001, "must be at most 2000 characters, got 2001"),
        (123, "must be a string"),
        (None, "must be a string"),
        (["a"], "must be a string"),
    ],
)
def test_invalid_agent_summary_is_rejected_before_anything_is_written(
    repo: Path, value, reason
) -> None:
    with pytest.raises(ValidationError) as raised:
        _write(repo, {"summary": value})
    assert f"summary: {reason}" in str(raised.value)
    assert not (repo / "reports").exists()


def test_agent_summary_at_the_limit_is_accepted(repo: Path) -> None:
    document = _write(repo, {"summary": " " + "x" * 2000 + " "})
    assert "x" * 2000 in _block(document, "summary-agent")


def test_agent_summary_renders_without_a_score(repo: Path) -> None:
    document = _write(repo, {"summary": "Partial run."}, dimensions=("security",))
    summary = _block(document, "summary")
    assert "No score in this report" in summary
    assert "Partial run." in summary


def test_agent_input_accepts_summary_and_shape_checks_it(repo: Path) -> None:
    assert validate_agent_input({"summary": "ok"}, repo) == {}
    with pytest.raises(RoleInputError) as raised:
        validate_agent_input({"summary": 5}, repo)
    assert "summary: must be a string" in str(raised.value)
    with pytest.raises(RoleInputError) as raised:
        validate_agent_input({"nope": 1}, repo)
    assert "improvements, batches and summary are accepted" in str(raised.value)


def test_cli_and_mcp_write_the_same_summary(tmp_path: Path) -> None:
    agent_input = {"summary": f"Two areas rated; key={SECRET}"}
    cli_repo = _repo(tmp_path / "cli")
    mcp_repo = _repo(tmp_path / "mcp")
    input_path = tmp_path / "agent_input.json"
    input_path.write_text(json.dumps(agent_input), encoding="utf-8")
    findings_path = tmp_path / "findings.json"
    findings_path.write_text("[]", encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "easy_verifier.adapters.cli",
            "write-report",
            "--repo",
            str(cli_repo),
            "--scope",
            SCOPE,
            "--findings",
            str(findings_path),
            "--agent-input",
            str(input_path),
        ],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        env={"PYTHONPATH": str(REPO_ROOT / "src"), "PATH": "/usr/bin:/bin"},
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    cli_document = (cli_repo / json.loads(completed.stdout)["path"]).read_text(
        encoding="utf-8"
    )

    server = importlib.import_module("easy_verifier.adapters.mcp_server")
    _content, structured = asyncio.run(
        server.mcp.call_tool(
            "write_report",
            {
                "findings": [],
                "repo": str(mcp_repo),
                "scope": SCOPE,
                "agent_input": agent_input,
            },
        )
    )
    mcp_document = (mcp_repo / structured["path"]).read_text(encoding="utf-8")

    assert SECRET not in cli_document and SECRET not in mcp_document
    assert ">agent<" in _block(cli_document, "summary")
    assert _block(cli_document, "summary") == _block(mcp_document, "summary")


def test_every_declared_source_has_a_plain_name_or_is_marked_derived() -> None:
    from easy_verifier.dimensions import list_dimensions
    from easy_verifier.packs import PACKS

    declared = {s for item in list_dimensions() for s in item.sources_sought}
    declared |= {s for item in PACKS.values() for s in item.sources_sought}
    assert set(report._SOURCE_TEXT) == declared


def test_every_rule_metric_has_a_plain_description() -> None:
    names = {name for rules in RATING_RULES.values() for name in rules}
    assert set(report._METRIC_TEXT) == names


def test_mcp_write_report_description_mentions_summary() -> None:
    server = importlib.import_module("easy_verifier.adapters.mcp_server")
    tools = asyncio.run(server.mcp.list_tools())
    description = next(t.description for t in tools if t.name == "write_report")
    assert '"summary"' in description
