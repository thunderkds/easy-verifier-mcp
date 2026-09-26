"""AC #3/#4/#8: independent adapter parity oracle."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from easy_verifier.dimensions import dimension_names

from .conftest import (
    REPO_ROOT,
    cli_json,
    mcp_call,
    require_docker,
)


def normalize(
    value: object, *, field: str = "", repo_root: Path | None = None
) -> object:
    """DDR-0005's closed normalization: only paths, timestamps, filenames."""
    if isinstance(value, dict):
        return {
            key: normalize(item, field=key, repo_root=repo_root)
            for key, item in value.items()
            if not (key == "report_filename" or key == "filename")
        }
    if isinstance(value, list):
        return [normalize(item, field=field, repo_root=repo_root) for item in value]
    if isinstance(value, str):
        if field == "path":
            return value
        if field == "absolute_path" and repo_root is not None:
            root = str(repo_root.resolve())
            if value == root:
                return "."
            if value.startswith(root + "/"):
                return value[len(root) + 1 :]
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
    # `needs_input` is a declared MCP-only field (T027, FR-034/FR-040): the
    # core computes it but only the MCP adapter puts it on the wire, so the
    # CLI payload never carries the key. This is a test-declared exclusion,
    # not a widening of DDR-0005's closed normalization list.
    assert "needs_input" not in cli_score
    mcp_score_for_parity = {k: v for k, v in mcp_score.items() if k != "needs_input"}
    assert normalize(cli_score) == normalize(mcp_score_for_parity)


def test_score_with_the_same_picks_matches_across_adapters(tmp_path: Path) -> None:
    """FR-022 amended (T026 AC #11): agent input is part of the input, so the
    same picks through the MCP argument and the CLI file give the same bytes
    after DDR-0005's unchanged three-rule normalization."""
    agent_input = {"picks": {"ci-workflow": ["scripts/verify_container.sh"]}}
    document = tmp_path / "agent-input.json"
    document.write_text(json.dumps(agent_input), encoding="utf-8")

    cli_score = cli_json(
        "score",
        "--repo",
        str(REPO_ROOT),
        "--scope",
        "worktree",
        "--agent-input",
        str(document),
    )
    mcp_score = mcp_call(
        "score",
        {"repo": str(REPO_ROOT), "scope": "worktree", "agent_input": agent_input},
    )
    assert normalize(cli_score) == normalize(mcp_score)
    provenance = {
        item["dimension"]: item["sources"] for item in cli_score["provenance"]
    }
    assert provenance["security"] == "rules + agent picks (1 file)"
    assert provenance["test-strategy"] == "rules + agent picks (1 file)"


def test_normalization_is_field_limited_and_can_fail() -> None:
    root = Path("/repo")
    left = {"absolute_path": "/repo/src/a.py", "detail": "/repo/src/a.py"}
    right = {"absolute_path": "/other/src/a.py", "detail": "/other/src/a.py"}
    assert normalize(left, repo_root=root) != normalize(right, repo_root=root)
    assert normalize({"absolute_path": "/repoevil/src/a.py"}, repo_root=root) != {
        "absolute_path": "src/a.py"
    }
    assert normalize({"path": "/repo/src/a.py"}, repo_root=root) == {
        "path": "/repo/src/a.py"
    }
    assert normalize({"detail": "/repo/src/a.py"}, repo_root=root) == {
        "detail": "/repo/src/a.py"
    }
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
