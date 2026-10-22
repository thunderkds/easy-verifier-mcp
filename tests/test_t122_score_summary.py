"""T122 acceptance tests: the MCP ``score`` reply is a summary by default.

Every acceptance criterion in ``tasks/TASK_GUIDE_T122.md`` has a test here.
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from pathlib import Path

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from easy_verifier.adapters import mcp_server
from easy_verifier.core.score import score_repository

REPO_ROOT = Path(__file__).resolve().parents[1]
CLI = [sys.executable, "-m", "easy_verifier.adapters.cli"]


def _target(path: Path) -> Path:
    path.mkdir()
    (path / "README.md").write_text("# Target\n\nA small service.\n", encoding="utf-8")
    (path / "app.py").write_text("def main():\n    return 1\n", encoding="utf-8")
    return path


def _score(arguments: dict) -> dict:
    _content, structured = asyncio.run(mcp_server.mcp.call_tool("score", arguments))
    return structured.get("result", structured)


def _tool_description() -> str:
    tools = asyncio.run(mcp_server.mcp.list_tools())
    return next(tool.description for tool in tools if tool.name == "score")


def test_default_reply_has_no_metric_rows_and_matches_full_elsewhere(tmp_path):
    repo = _target(tmp_path / "repo")
    summary = _score({"repo": str(repo)})
    full = _score({"repo": str(repo), "detail": "full"})

    assert "metrics" not in summary["metrics"]
    assert len(full["metrics"]["metrics"]) > 0
    assert set(summary) == set(full)
    for key in full:
        if key != "metrics":
            assert summary[key] == full[key], key
    assert summary["metrics"] == {
        "dimensions_without_pack": full["metrics"]["dimensions_without_pack"]
    }
    assert len(json.dumps(summary)) < len(json.dumps(full))


def test_explicit_summary_equals_the_default(tmp_path):
    repo = _target(tmp_path / "repo")
    assert _score({"repo": str(repo), "detail": "summary"}) == _score(
        {"repo": str(repo)}
    )


def test_full_reply_is_the_unfiltered_payload(tmp_path):
    repo = _target(tmp_path / "repo")
    full = _score({"repo": str(repo), "detail": "full"})
    direct = mcp_server.score(repo=str(repo), detail="full")
    assert full == json.loads(json.dumps(direct))
    assert json.dumps(full["metrics"], sort_keys=True) == json.dumps(
        direct["metrics"], sort_keys=True
    )


@pytest.mark.parametrize("bad", ["brief", "", "FULL", None, 1])
def test_invalid_detail_is_a_validation_error_naming_allowed_values(tmp_path, bad):
    repo = _target(tmp_path / "repo")
    with pytest.raises(ToolError) as caught:
        _score({"repo": str(repo), "detail": bad})
    assert "summary" in str(caught.value)
    assert "full" in str(caught.value)


def test_gate_refs_resolve_without_metric_rows(tmp_path):
    repo = _target(tmp_path / "repo")
    first = _score({"repo": str(repo)})
    requests = first["needs_input"]["gate_evaluations"]
    assert requests and all(entry["evidence_refs"] for entry in requests)
    assert "metrics" not in first["metrics"]

    # Refs are excerpt refs from each dimension's pack, so the next call
    # accepts them although the caller never saw a metric row.
    answer = {
        entry["dimension"]: {
            "score": 70,
            "confidence": 0.5,
            "evidence_refs": entry["evidence_refs"][:1],
        }
        for entry in requests
    }
    second = _score(
        {"repo": str(repo), "agent_input": {"gate_evaluations": answer}}
    )
    assert "needs_input" not in second or "gate_evaluations" not in second.get(
        "needs_input", {}
    )


def test_tool_description_states_budget_scope_and_detail_full():
    description = _tool_description()
    assert "budget_bytes" in description
    assert "excerpt" in description
    assert 'detail="full"' in description


def test_cli_score_output_still_carries_metric_rows(tmp_path):
    repo = _target(tmp_path / "repo")
    done = subprocess.run(
        [*CLI, "score", "--repo", str(repo)],
        capture_output=True,
        text=True,
        env={"PYTHONPATH": str(REPO_ROOT / "src"), "PATH": ""},
        stdin=subprocess.DEVNULL,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    payload = json.loads(done.stdout)
    assert len(payload["metrics"]["metrics"]) > 0
    assert payload == json.loads(score_repository(repo).serialize())
