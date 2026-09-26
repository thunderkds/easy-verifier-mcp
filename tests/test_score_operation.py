"""T022 acceptance tests for the shared score operation and both adapters."""

from __future__ import annotations

import ast
import asyncio
import json
import os
import subprocess
import sys
from dataclasses import replace
from html.parser import HTMLParser
from pathlib import Path

from easy_verifier.adapters import mcp_server
from easy_verifier.core.models import (
    CombinedPack,
    CoverageSummary,
    DimensionSlot,
    EvidencePack,
    Excerpt,
    SourceMiss,
)
from easy_verifier.core.report import write_report
from easy_verifier.core.score import score_repository
from easy_verifier.dimensions import dimension_names

REPO_ROOT = Path(__file__).resolve().parents[1]
CLI_PATH = REPO_ROOT / "src/easy_verifier/adapters/cli.py"
MCP_PATH = REPO_ROOT / "src/easy_verifier/adapters/mcp_server.py"
MODULE_COMMAND = [sys.executable, "-m", "easy_verifier.adapters.cli"]


def _env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    return env


def _run(*args: str, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [*MODULE_COMMAND, *args],
        input=input_text,
        capture_output=True,
        text=True,
        env=_env(),
        check=False,
    )


def _target(path: Path) -> Path:
    path.mkdir()
    (path / "README.md").write_text("# Target\n", encoding="utf-8")
    return path


def _mcp_score(arguments: dict) -> dict:
    _content, structured = asyncio.run(mcp_server.mcp.call_tool("score", arguments))
    return structured.get("result", structured)


def test_cli_score_needs_no_findings_and_returns_disclosed_ratings(
    tmp_path: Path,
) -> None:
    target = _target(tmp_path / "target")

    completed = _run("score", "--repo", str(target), "--scope", "project")

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert tuple(item["dimension"] for item in payload["ratings"]) == dimension_names()
    # T026 (FR-039, AC #10) adds per-dimension source provenance to the payload.
    assert set(payload) == {"ratings", "overall", "metrics", "provenance"}
    assert [item["dimension"] for item in payload["provenance"]] == list(
        dimension_names()
    )
    assert payload["overall"]["kind"] in {"overall_rating", "rating_abstention"}
    if payload["overall"]["kind"] == "overall_rating":
        assert payload["overall"]["disclosure"]
    else:
        assert payload["overall"]["reason_code"] == "no_dimension_rated"
    assert all(
        item["kind"] == "rating_abstention" and "value" not in item
        for item in payload["ratings"]
    )


def test_cli_and_mcp_score_payloads_match(tmp_path: Path) -> None:
    target = _target(tmp_path / "target")
    completed = _run("score", "--repo", str(target), "--scope", "project")

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == _mcp_score(
        {"repo": str(target), "scope": "project"}
    )


def test_optional_findings_add_assessments_and_divergences(tmp_path: Path) -> None:
    target = _target(tmp_path / "target")
    baseline = score_repository(target, scope="project").to_dict()
    evidence_ref = next(
        ref
        for metric in baseline["metrics"]["metrics"]
        for ref in metric["computed_from"]
        if ":" in ref and "-" in ref.rpartition(":")[2]
    )
    findings = json.dumps(
        [
            {
                "dimension": "architecture",
                "title": "Architecture concern",
                "detail": "The declared structure needs attention.",
                "evidence_ref": evidence_ref,
                "confidence": "high",
                "severity": "high",
            }
        ]
    )

    completed = _run(
        "score", "--repo", str(target), "--scope", "project", input_text=findings
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    # T026 (FR-039, AC #10) adds per-dimension source provenance to the payload.
    assert set(payload) == {
        "ratings",
        "overall",
        "metrics",
        "provenance",
        "assessments",
        "divergences",
    }
    assessment = next(
        item for item in payload["assessments"] if item["dimension"] == "architecture"
    )
    divergence = next(
        item for item in payload["divergences"] if item["dimension"] == "architecture"
    )
    assert assessment["kind"] == "assessment"
    assert divergence["kind"] in {"divergence", "divergence_absence"}


def test_findings_file_matches_stdin_for_score(tmp_path: Path) -> None:
    target = _target(tmp_path / "target")
    findings_file = tmp_path / "findings.json"
    findings_file.write_text("[]", encoding="utf-8")

    from_file = _run("score", "--repo", str(target), "--findings", str(findings_file))
    from_stdin = _run("score", "--repo", str(target), input_text="[]")

    assert from_file.returncode == from_stdin.returncode == 0
    assert json.loads(from_file.stdout) == json.loads(from_stdin.stdout)


def test_score_report_panel_is_self_contained_and_scrubs_repo_path(
    tmp_path: Path,
) -> None:
    target = _target(tmp_path / "target")
    completed = _run("write-report", "--repo", str(target), input_text="[]")

    assert completed.returncode == 0, completed.stderr
    report_path = target / json.loads(completed.stdout)["path"]
    document = report_path.read_text(encoding="utf-8")
    parser = _ReferenceScanner()
    parser.feed(document)
    assert "Quality score" in document
    assert "Overall" in document
    assert "Rating withheld" in document
    assert str(target) not in document
    assert parser.urls == []
    assert parser.scripts == []


def test_report_renders_numeric_overall_assessment_and_distinct_abstention(
    tmp_path: Path,
) -> None:
    target = _target(tmp_path / "target")
    packs = _complete_pack_with_architecture_abstaining(target)
    absolute_ref = f"{target}/src/app.py:1-2"
    result = write_report(
        [
            {
                "dimension": "blast-radius",
                "title": "Coupling concern",
                "detail": "The application entry point has several consumers.",
                "evidence_ref": absolute_ref,
                "confidence": "high",
                "severity": "medium",
            }
        ],
        packs,
        target,
    )

    document = (target / result.path).read_text(encoding="utf-8")
    assert '<div class="overall-rating"><h3>Overall</h3>' in document
    assert "dimensions contributed" in document
    assert "Rating withheld" in document
    assert "rating-below_coverage_floor" in document
    assert '<p class="rating-value">Rating ' in document
    assert "Assessment " in document
    assert "Divergence " in document
    assert "src/app.py:1-2" in document
    assert absolute_ref not in document


def test_failed_dimension_is_distinct_and_escaped_in_score_panel(
    tmp_path: Path,
) -> None:
    target = _target(tmp_path / "target")
    packs = _complete_pack_with_architecture_abstaining(target)
    failure = "collector <b>exploded</b>"
    failed_miss = (
        SourceMiss("architecture", f"not examined: dimension failed ({failure})"),
    )
    failed_slots = (
        DimensionSlot("architecture", None, failure),
        *packs.slots[1:],
    )
    failed_scores = (("architecture", None), *packs.coverage.per_dimension[1:])
    failed_misses = (("architecture", failed_miss), *packs.coverage.misses[1:])
    failed = replace(
        packs,
        slots=failed_slots,
        coverage=replace(
            packs.coverage,
            per_dimension=failed_scores,
            misses=failed_misses,
        ),
    )

    result = write_report([], failed, target)
    document = (target / result.path).read_text(encoding="utf-8")

    assert "rating-dimension_failed" in document
    assert "dimension_failed" in document
    assert "rating-below_coverage_floor" not in document
    assert "collector &lt;b&gt;exploded&lt;/b&gt;" in document
    assert "collector <b>exploded</b>" not in document


def test_adapters_delegate_without_scoring_arithmetic() -> None:
    for path in (CLI_PATH, MCP_PATH):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        assert "compute_metrics" not in source
        assert "rate_overall" not in source
        assert "coverage_score" not in source
        assert not any(
            isinstance(node, ast.BinOp)
            and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div))
            for node in ast.walk(tree)
        )


class _ReferenceScanner(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.urls: list[str] = []
        self.scripts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            self.scripts.append(tag)
        for name, value in attrs:
            if name in {"src", "href", "srcset", "poster", "data"} and value:
                self.urls.append(value)


def _complete_pack_with_architecture_abstaining(target: Path) -> CombinedPack:
    app_path = (target / "src/app.py").as_posix()
    test_path = (target / "tests/test_app.py").as_posix()
    slots = []
    scores = []
    misses = []
    for dimension in dimension_names():
        abstains = dimension == "architecture"
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
                Excerpt(
                    test_path,
                    1,
                    2,
                    "def test_app():\n    assert app() == 1\n",
                ),
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
            combined=6 / 7,
            method="fixture coverage",
            misses=tuple(misses),
        ),
        budget_model="per-dimension",
    )
