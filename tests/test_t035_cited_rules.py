"""T035 -- per-dimension cited rating rules (FR-043, FR-048 curated half).

The rule table is pinned to the approved table (B5) in
``BRAINSTORMING_LOG_reference-registry.md``; every sabotage pair below varies
only the one predicate it pins.
"""

from __future__ import annotations

import asyncio
import json
import re
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from easy_verifier.adapters import mcp_server
from easy_verifier.core import report as report_module
from easy_verifier.core.gate import detect_evaluate_gates
from easy_verifier.core.judge import (
    COVERAGE_FLOORS,
    CURATED,
    PROJECT_DEFAULT,
    RATING_RULES,
    Citation,
    Rating,
    RatingAbstention,
    rate,
)
from easy_verifier.core.metric_tables import curated_metric_tables
from easy_verifier.core.metrics import MetricSet, compute_metrics
from easy_verifier.core.models import (
    CoverageSummary,
    EvidencePack,
    Excerpt,
    SourceMiss,
    TruncationRecord,
)
from easy_verifier.core.score import score_repository

REPO_ROOT = Path(__file__).resolve().parents[1]
VENDORED = REPO_ROOT / "src/easy_verifier/registry/vendored"
_ASVS = "OWASP ASVS 5.0.0"

# The approved table (B5): dimension -> (metric, weight, comparison, threshold,
# metric-citation labels, threshold citation label or project-default).
APPROVED = {
    "architecture": [
        ("architecture_description_missing", 30, "at_most", 0, ("42010",), "42010"),
        ("decision_records_missing", 30, "at_most", 0, ("42010",), "42010"),
        ("top_level_import_cycles", 40, "at_most", 0, ("Martin",), "Martin"),
    ],
    "solution-fit": [],
    "requirement-fidelity": [
        ("acceptance_criteria_traced_to_code_share", 50, "at_least", 0.80,
         ("29148",), PROJECT_DEFAULT),
        ("acceptance_criteria_traced_to_test_share", 50, "at_least", 0.80,
         ("29148",), PROJECT_DEFAULT),
    ],
    "code-quality": [
        ("functions_over_ccn_10_share", 40, "at_most", 0.10,
         ("McCabe", "5055"), "NIST SP 500-235"),
        ("max_function_ccn", 20, "at_most", 15,
         ("McCabe", "NIST SP 500-235"), "NIST SP 500-235 (15"),
        ("lint_config_missing", 20, "at_most", 0, ("5055",), PROJECT_DEFAULT),
        ("format_config_missing", 20, "at_most", 0, ("5055",), PROJECT_DEFAULT),
    ],
    "security": [
        ("redaction_hits_observed", 40, "at_most", 0,
         ("CWE-798", f"{_ASVS} V13.3.1"), f"{_ASVS} V13.3.1"),
        ("sink_hits_observed", 40, "at_most", 0, ("CWE Top 25",), "CWE Top 25"),
        ("lockfile_missing", 20, "at_most", 0,
         (f"{_ASVS} V15.1.2",), f"{_ASVS} V15.1.2"),
    ],
    "test-strategy": [
        ("source_files_without_covering_test_share", 35, "at_most", 0.20,
         ("29119",), PROJECT_DEFAULT),
        ("assertion_density_per_test", 35, "at_least", 1.0,
         ("Kudrjavets",), PROJECT_DEFAULT),
        ("test_config_and_ci_missing", 30, "at_most", 0,
         ("29119",), PROJECT_DEFAULT),
    ],
    "blast-radius": [
        ("max_fan_in_changed", 50, "at_most", 20, ("Henry & Kafura",),
         PROJECT_DEFAULT),
        ("changed_files_in_churn_hotspots_share", 50, "at_most", 0.20,
         ("Nagappan & Ball",), PROJECT_DEFAULT),
    ],
}


# ---------------------------------------------------------------------------
# AC1 -- the rule table is the approved table, as data
# ---------------------------------------------------------------------------


def test_rule_table_equals_the_approved_table():
    assert list(RATING_RULES) == list(COVERAGE_FLOORS)
    for dimension, rows in APPROVED.items():
        rules = RATING_RULES[dimension]
        assert list(rules) == [row[0] for row in rows], dimension
        for name, weight, comparison, threshold, metric_cites, threshold_cite in rows:
            rule = rules[name]
            assert (rule.weight, rule.comparison, rule.threshold) == (
                weight,
                comparison,
                threshold,
            ), name
            assert len(rule.metric_citation) == len(metric_cites), name
            pairs = zip(rule.metric_citation, metric_cites, strict=True)
            for citation, expected in pairs:
                assert expected in citation.label, (name, citation)
            if threshold_cite == PROJECT_DEFAULT:
                assert rule.threshold_citation == PROJECT_DEFAULT, name
            else:
                assert threshold_cite in rule.threshold_citation.label, name
            assert rule.source_tag == CURATED


def test_weights_sum_to_100_per_dimension_and_solution_fit_has_none():
    for dimension, rules in RATING_RULES.items():
        if dimension == "solution-fit":
            assert rules == {}
        else:
            assert sum(rule.weight for rule in rules.values()) == 100, dimension


def test_every_rule_metric_is_a_computed_metric():
    from easy_verifier.core.metrics import METRIC_NAMES

    for rules in RATING_RULES.values():
        assert set(rules) <= set(METRIC_NAMES)


def test_asvs_and_cwe_citations_match_the_vendored_snapshots():
    asvs = json.loads((VENDORED / "asvs.json").read_text())["requirements"]
    urls = {item["id"]: item["url"] for item in asvs}
    cwe = {
        item["id"]: item["url"]
        for item in json.loads((VENDORED / "cwe.json").read_text())["weaknesses"]
    }
    security = RATING_RULES["security"]
    cited = [*security["redaction_hits_observed"].metric_citation,
             *security["lockfile_missing"].metric_citation]
    for citation in cited:
        if citation.label.startswith(_ASVS):
            requirement = re.search(r"V\d+\.\d+\.\d+", citation.label).group(0)
            assert citation.url == urls[requirement], citation
        else:
            assert citation.url == cwe["798"]


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"weight": 31}, "sum to 100"),
        ({"metric_citation": ()}, "metric_citation"),
        ({"metric_citation": (Citation("ISO", "http://iso.org/x"),)}, "https"),
        ({"metric_citation": (Citation("", "https://iso.org/x"),)}, "label"),
        ({"threshold_citation": "our-default"}, "threshold_citation"),
        ({"source_tag": "agent-researched (unreviewed)"}, "source_tag"),
    ],
)
def test_declared_data_validation_rejects_each_broken_field(
    change, message, monkeypatch
):
    rules = RATING_RULES["architecture"]
    name = "architecture_description_missing"
    metrics, coverage = _architecture_inputs()
    assert isinstance(rate(metrics, coverage), Rating)  # intact table rates
    monkeypatch.setitem(rules, name, replace(rules[name], **change))
    with pytest.raises(ValueError, match=message):
        rate(metrics, coverage)


# ---------------------------------------------------------------------------
# AC2 -- every RatingInput carries its citations and source tag
# ---------------------------------------------------------------------------


def test_every_score_input_carries_metric_threshold_citation_and_source_tag():
    payload = score_repository(REPO_ROOT, scope="project").to_dict()
    inputs = [
        (rating["dimension"], item)
        for rating in payload["ratings"]
        if rating["kind"] == "rating"
        for item in rating["inputs"]
    ]
    assert inputs, "this repository rates at least one dimension"
    for dimension, item in inputs:
        rule = RATING_RULES[dimension][item["metric_name"]]
        assert item["metric_citation"] == [c.to_dict() for c in rule.metric_citation]
        assert item["threshold_citation"] == (
            PROJECT_DEFAULT
            if rule.threshold_citation == PROJECT_DEFAULT
            else rule.threshold_citation.to_dict()
        )
        assert item["source_tag"] == "curated"
        for citation in item["metric_citation"]:
            assert citation["url"].startswith("https://")


# ---------------------------------------------------------------------------
# AC3 -- solution-fit abstains by design and reaches the evaluate gate
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("score", [1.0, 0.5, 0.0, None])
def test_solution_fit_always_abstains_no_static_rule(score):
    missing = () if score in (1.0, None) else (SourceMiss("PRD.md", "not found"),)
    coverage = CoverageSummary(
        per_dimension=(("solution-fit", score),),
        combined=score,
        method="fixture",
        misses=(("solution-fit", missing),),
    )
    result = rate(MetricSet(()), coverage)
    assert isinstance(result, RatingAbstention)
    assert result.reason_code == "no_static_rule"
    assert result.coverage_floor == COVERAGE_FLOORS["solution-fit"].value
    assert result.achieved_coverage == score
    assert detect_evaluate_gates([result]) == {"solution-fit": "abstained"}


def test_no_static_rule_is_rejected_for_a_dimension_that_has_rules():
    with pytest.raises(ValueError, match="no_static_rule"):
        RatingAbstention(
            dimension="architecture",
            reason_code="no_static_rule",
            coverage_floor=COVERAGE_FLOORS["architecture"].value,
        )


# ---------------------------------------------------------------------------
# Success criterion 2 -- 30% of functions over CCN 10 fails the 40-weight rule
# ---------------------------------------------------------------------------

_SIMPLE = "def simple_{n}(x):\n    return x\n"
_COMPLEX = "def complex_{n}(x):\n" + "".join(
    f"    if x == {i}:\n        return {i}\n" for i in range(10)
) + "    return x\n"  # 10 ifs -> approximate CCN 11


def _code_quality_rating(over: int) -> Rating:
    body = "".join(
        (_COMPLEX if n < over else _SIMPLE).format(n=n) for n in range(10)
    )
    pack = _pack(
        "code-quality",
        {"src/app.py": body},
        sought=("lint-config",),
        found=("lint-config",),
    )
    metrics = compute_metrics(pack, curated_metric_tables())
    result = rate(metrics, _full_coverage("code-quality"))
    assert isinstance(result, Rating)
    return result


def test_thirty_percent_of_functions_over_ccn_10_earns_0_of_40():
    unmet = _code_quality_rating(over=3)
    met = _code_quality_rating(over=1)  # sabotage pair: only the share varies
    by_name = {item.metric_name: item for item in unmet.inputs}
    share = by_name["functions_over_ccn_10_share"]
    assert share.metric_value == 0.3
    assert (share.weight, share.earned_weight, share.passed) == (40, 0, False)
    met_share = {i.metric_name: i for i in met.inputs}["functions_over_ccn_10_share"]
    assert met_share.metric_value == 0.1
    assert (met_share.earned_weight, met_share.passed) == (40, True)


# ---------------------------------------------------------------------------
# Role-missing metrics -- only sources_found varies
# ---------------------------------------------------------------------------


def _missing_metric(found: tuple[str, ...], *, truncated: bool = False):
    pack = _pack(
        "code-quality",
        {"README.md": "# x\n"},
        sought=("lint-config", "format-config"),
        found=found,
        truncated=truncated,
    )
    metrics = compute_metrics(pack, curated_metric_tables())
    return next(m for m in metrics if m.name == "lint_config_missing")


def test_role_missing_metric_is_0_when_filled_1_when_not_and_abstains_truncated():
    assert _missing_metric(("lint-config",)).outcome == 0
    assert _missing_metric(()).outcome == 1
    assert _missing_metric((), truncated=True).abstained
    assert _missing_metric(("lint-config",), truncated=True).outcome == 0


def test_role_missing_metric_abstains_where_the_role_is_not_declared():
    pack = _pack("architecture", {"README.md": "# x\n"}, sought=("readme",))
    metrics = compute_metrics(pack, curated_metric_tables())
    lint = next(m for m in metrics if m.name == "lint_config_missing")
    assert lint.abstained
    assert "does not declare" in lint.abstention.reason


def test_ac_trace_metrics_abstain_with_a_stated_reason_without_a_trace_search():
    # T052: the shares compute from a kit-aware pack's trace search; a pack
    # without one (standalone mode) still abstains, saying why.
    pack = _pack("requirement-fidelity", {"PRD.md": "- AC1\n"}, sought=("x",))
    metrics = compute_metrics(pack, curated_metric_tables())
    result = rate(metrics, _full_coverage("requirement-fidelity"))
    assert isinstance(result, RatingAbstention)
    assert result.reason_code == "all_metrics_abstained"
    assert all("never inferred" in reason for _n, reason in result.unavailable_metrics)


# ---------------------------------------------------------------------------
# AC4 -- report renders citations as links; CLI/MCP parity with inputs
# ---------------------------------------------------------------------------


def test_report_renders_each_citation_as_a_link_and_project_default_as_text(
    tmp_path: Path,
):
    metrics, coverage = _architecture_inputs()
    rating = rate(metrics, coverage)
    ctx = report_module._Ctx(tmp_path)
    html = "".join(report_module._render_rating_input(ctx, i) for i in rating.inputs)
    assert '<a href="https://www.iso.org/standard/74393.html" rel="noreferrer">' in html
    assert "source: curated" in html

    rendered = report_module._render_citation(ctx, PROJECT_DEFAULT)
    assert rendered == "project-default" and "<a" not in rendered
    hostile = Citation('<b>"x"</b>', 'https://example.org/"onmouseover=')
    escaped = report_module._render_citation(ctx, hostile)
    assert "<b>" not in escaped and '"onmouseover' not in escaped


def test_cli_and_mcp_payloads_match_with_cited_inputs(tmp_path: Path):
    target = tmp_path / "target"
    (target / "docs/adr").mkdir(parents=True)
    (target / "src").mkdir()
    (target / "README.md").write_text("# Target\n", encoding="utf-8")
    (target / "PROJECT_SPEC.md").write_text("# Architecture\n", encoding="utf-8")
    (target / "docs/adr/0001-use-python.md").write_text("# ADR\n", encoding="utf-8")
    (target / "src/app.py").write_text("import os\n\n\ndef main():\n    return os\n")
    completed = subprocess.run(
        [sys.executable, "-m", "easy_verifier.adapters.cli", "score",
         "--repo", str(target), "--scope", "project"],
        capture_output=True, text=True, stdin=subprocess.DEVNULL, check=False,
        env={"PYTHONPATH": str(REPO_ROOT / "src"), "PATH": "/usr/bin:/bin"},
    )
    assert completed.returncode == 0, completed.stderr
    _content, mcp_payload = asyncio.run(
        mcp_server.mcp.call_tool("score", {"repo": str(target), "scope": "project"})
    )
    mcp_payload.pop("needs_input", None)
    cli_payload = json.loads(completed.stdout)
    assert cli_payload == mcp_payload
    architecture = next(
        r for r in cli_payload["ratings"] if r["dimension"] == "architecture"
    )
    assert architecture["kind"] == "rating"
    assert all(item["metric_citation"] for item in architecture["inputs"])


# ---------------------------------------------------------------------------
# README -- the documented table is the declared table (doc-truth)
# ---------------------------------------------------------------------------


def test_readme_rating_table_matches_declared_rules():
    text = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    block = text.split("<!-- rating-rules:start -->")[1].split(
        "<!-- rating-rules:end -->"
    )[0]
    rows = [line for line in block.splitlines() if line.startswith("| `")]
    documented = {}
    for row in rows:
        cells = [cell.strip() for cell in row.strip("|").split("|")]
        if cells[2] == "—":
            documented.setdefault(cells[0].strip("`"), [])
            continue
        documented.setdefault(cells[0].strip("`"), []).append(
            (cells[1].strip("`"), cells[2], int(cells[3]), cells[4], cells[5])
        )
    symbol = {"at_most": "≤", "at_least": "≥"}
    for dimension, rules in RATING_RULES.items():
        def cite(c):
            return c if c == PROJECT_DEFAULT else f"[{c.label}]({c.url})"

        expected = [
            (
                rule.metric_name,
                f"{symbol[rule.comparison]} {rule.threshold:g}",
                rule.weight,
                "; ".join(f"[{c.label}]({c.url})" for c in rule.metric_citation),
                cite(rule.threshold_citation),
            )
            for rule in rules.values()
        ]
        assert documented[dimension] == expected, dimension


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _pack(
    dimension: str,
    files: dict[str, str],
    *,
    sought: tuple[str, ...],
    found: tuple[str, ...] | None = None,
    truncated: bool = False,
) -> EvidencePack:
    found = sought if found is None else found
    return EvidencePack(
        dimension=dimension,
        mode="kit-aware",
        scope="project",
        files_read=tuple(files),
        excerpts=tuple(
            Excerpt(path, 1, len(text.splitlines()), text)
            for path, text in files.items()
        ),
        sources_sought=sought,
        sources_found=found,
        sources_missing=tuple(
            SourceMiss(role, "not found") for role in sought if role not in found
        ),
        coverage_score=len(found) / len(sought),
        truncated=truncated,
        omitted_count=1 if truncated else 0,
        truncation=TruncationRecord(
            truncated=truncated, omitted_count=1 if truncated else 0
        ),
    )


def _full_coverage(dimension: str) -> CoverageSummary:
    return CoverageSummary(
        per_dimension=((dimension, 1.0),),
        combined=1.0,
        method="fixture",
        misses=((dimension, ()),),
    )


def _architecture_inputs() -> tuple[MetricSet, CoverageSummary]:
    pack = _pack(
        "architecture",
        {"src/a/x.py": "import os\n", "src/b/y.py": "import sys\n"},
        sought=("architecture-doc", "decision-record"),
    )
    return compute_metrics(pack, curated_metric_tables()), _full_coverage(
        "architecture"
    )
