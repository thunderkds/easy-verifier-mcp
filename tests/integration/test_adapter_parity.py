"""AC #3/#4/#8: independent adapter parity oracle."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from easy_verifier.dimensions import dimension_names

from .conftest import REPO_ROOT, cli_json, mcp_call, require_docker


def normalize(value: object, *, field: str = "") -> object:
    """DDR-0005's closed normalization: only paths, timestamps, filenames."""
    if isinstance(value, dict):
        return {
            key: normalize(item, field=key)
            for key, item in value.items()
            if not (key == "report_filename" or key == "filename")
        }
    if isinstance(value, list):
        return [normalize(item, field=field) for item in value]
    if isinstance(value, str):
        if field in {"path", "absolute_path"}:
            return Path(value).name if field == "absolute_path" else value
        if "timestamp" in field or field in {"generated", "created_at"}:
            return "<TIMESTAMP>"
    return value


def test_all_seven_dimension_adapters_match_byte_for_byte() -> None:
    for name in dimension_names():
        cli_payload = cli_json(name, "--repo", str(REPO_ROOT), "--scope", "worktree")
        mcp_payload = mcp_call(name, {"repo": str(REPO_ROOT), "scope": "worktree"})
        assert normalize(cli_payload) == normalize(mcp_payload), name


def test_combined_score_and_discovery_match_across_adapters() -> None:
    cli_discovery = cli_json("list-dimensions")
    mcp_discovery = mcp_call("list_dimensions", {})
    assert normalize(cli_discovery) == normalize(mcp_discovery)

    cli_combined = cli_json(
        "combined",
        "--repo",
        str(REPO_ROOT),
        "--scope",
        "worktree",
        "--dimensions",
        ",".join(dimension_names()),
    )
    mcp_combined = mcp_call(
        "combined",
        {
            "repo": str(REPO_ROOT),
            "scope": "worktree",
            "dimensions": list(dimension_names()),
        },
    )
    assert normalize(cli_combined) == normalize(mcp_combined)

    cli_score = cli_json("score", "--repo", str(REPO_ROOT), "--scope", "worktree")
    mcp_score = mcp_call("score", {"repo": str(REPO_ROOT), "scope": "worktree"})
    assert normalize(cli_score) == normalize(mcp_score)


def test_normalization_is_field_limited_and_can_fail() -> None:
    left = {"path": "/repo/src/a.py", "detail": "/repo/src/a.py"}
    right = {"path": "/other/src/a.py", "detail": "/other/src/a.py"}
    assert normalize(left) != normalize(right)
    assert normalize({"timestamp": "one"}) == normalize({"timestamp": "two"})


def test_adapters_do_not_contain_scoring_or_parity_logic() -> None:
    for relative in (
        "src/easy_verifier/adapters/cli.py",
        "src/easy_verifier/adapters/mcp_server.py",
    ):
        source = (REPO_ROOT / relative).read_text(encoding="utf-8")
        assert "coverage_score" not in source
        assert "MetricSet" not in source
        assert "RatingAbstention" not in source
        assert "rate_overall" not in source


def test_container_parity_is_explicitly_verified() -> None:
    require_docker()
    completed = subprocess.run(
        ["bash", str(REPO_ROOT / "scripts/verify_container.sh")],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        env=os.environ.copy(),
        check=False,
    )
    assert completed.returncode == 0, completed.stderr + completed.stdout
