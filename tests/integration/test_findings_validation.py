"""AC #6: both adapters reject unevidenced findings before writing reports."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from .conftest import run_cli, target_repo


@pytest.mark.parametrize(
    "finding",
    [
        {
            "dimension": "architecture",
            "title": "x",
            "detail": "x",
            "confidence": "high",
        },
        {
            "dimension": "architecture",
            "title": "x",
            "detail": "x",
            "evidence_ref": "README.md:1-1",
        },
        {
            "dimension": "architecture",
            "title": "x",
            "detail": "x",
            "evidence_ref": "missing.py:1-1",
            "confidence": "high",
        },
    ],
)
def test_cli_invalid_findings_have_no_report(tmp_path: Path, finding: dict) -> None:
    target = target_repo(tmp_path / "target")
    completed = run_cli(
        "write-report",
        "--repo",
        str(target),
        "--dimensions",
        "architecture",
        input_text=json.dumps([finding]),
    )
    assert completed.returncode == 2
    assert completed.stdout == ""
    assert not (target / "reports").exists()


def test_mcp_invalid_findings_are_rejected_without_report(tmp_path: Path) -> None:
    target = target_repo(tmp_path / "target")
    with pytest.raises(Exception) as raised:
        asyncio.run(
            __import__(
                "easy_verifier.adapters.mcp_server", fromlist=["mcp_server"]
            ).mcp.call_tool(
                "write_report",
                {
                    "repo": str(target),
                    "dimensions": ["architecture"],
                    "findings": [{"dimension": "architecture"}],
                },
            )
        )
    assert "finding" in str(raised.value).lower()
    assert not (target / "reports").exists()
