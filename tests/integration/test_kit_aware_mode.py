"""AC #1: kit-aware evidence and report integration."""

from __future__ import annotations

import json
from pathlib import Path

from .conftest import REPO_ROOT, cli_json, run_cli


def test_kit_aware_report_contains_all_dimensions_coverage_and_misses() -> None:
    completed = run_cli(
        "write-report",
        "--repo",
        str(REPO_ROOT),
        "--scope",
        "project",
        "--findings",
        "/dev/stdin",
        input_text="[]",
    )

    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    report = (REPO_ROOT / result["path"]).read_text(encoding="utf-8")
    try:
        assert "kit-aware" in report
        for name in (
            "architecture",
            "blast-radius",
            "code-quality",
            "requirement-fidelity",
            "security",
            "solution-fit",
            "test-strategy",
        ):
            assert f"<h3>{name}</h3>" in report
        assert "Checklist coverage" in report
        assert "miss-list" in report
    finally:
        Path(REPO_ROOT / result["path"]).unlink(missing_ok=True)


def test_kit_aware_dimension_payload_has_real_sources_and_coverage() -> None:
    payload = cli_json("architecture", "--repo", str(REPO_ROOT), "--scope", "project")
    assert payload["mode"] == "kit-aware"
    assert payload["coverage_score"] is not None
    assert payload["sources_sought"]
    assert all(
        isinstance(miss, dict) and miss.get("source") and miss.get("reason")
        for miss in payload["sources_missing"]
    )
