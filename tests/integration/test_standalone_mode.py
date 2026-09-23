"""AC #2: standalone mode remains explicit about limited context."""

from __future__ import annotations

import json
from pathlib import Path

from .conftest import cli_json, mcp_call, run_cli, target_repo


def test_standalone_cli_report_contains_limited_context_warning(tmp_path: Path) -> None:
    target = target_repo(tmp_path / "plain")
    completed = run_cli(
        "write-report",
        "--repo",
        str(target),
        "--dimensions",
        "architecture",
        "--findings",
        "/dev/stdin",
        input_text="[]",
    )
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    report = (target / result["path"]).read_text(encoding="utf-8")
    assert "Limited context" in report


def test_standalone_mcp_dimension_carries_warning(tmp_path: Path) -> None:
    target = target_repo(tmp_path / "plain")
    payload = mcp_call("architecture", {"repo": str(target), "scope": "project"})
    assert payload["mode"] == "standalone"
    assert any("Limited context" in warning for warning in payload["warnings"])


def test_standalone_score_is_a_successful_report_even_when_context_is_limited(
    tmp_path: Path,
) -> None:
    target = target_repo(tmp_path / "plain")
    payload = cli_json("score", "--repo", str(target), "--scope", "project")
    assert len(payload["ratings"]) == 7
    assert "overall" in payload
