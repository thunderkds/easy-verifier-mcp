"""T084: breaking_api_changes_observed counts only removals in files the api
pack read, lists the rest as "not counted", and uses resolved conventions."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from easy_verifier.core.scope import resolve_scope
from easy_verifier.core.score import score_repository
from easy_verifier.dimensions import api

SPEC = "openapi: 3.1.0\ninfo:\n  title: S\n  version: 1.0.0\npaths:\n{body}"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.email=t@e.invalid", "-c", "user.name=t", *args],
        cwd=repo, check=True, capture_output=True,
    )


def _spec(n: int, extra: int = 2) -> str:
    body = "  /v1/keep:\n    get:\n      summary: k\n"
    return SPEC.format(
        body=body + "".join(f"  /v1/gone{n}x{i}:\n" for i in range(extra))
    )


def _commit_pair(repo: Path, before: dict[str, str], after: dict[str, str]):
    for rel, text in before.items():
        (repo / rel).parent.mkdir(parents=True, exist_ok=True)
        (repo / rel).write_text(text, encoding="utf-8")
    _git(repo, "init", "-q")
    _git(repo, "add", ".")
    _git(repo, "commit", "-qm", "base")
    for rel, text in after.items():
        (repo / rel).write_text(text, encoding="utf-8")
    _git(repo, "commit", "-qam", "drop")
    return resolve_scope("changes", repo, None, ref="HEAD~1..HEAD")


def _two_files(repo: Path, unread: int = 1):
    """a/openapi.yaml loses 2 paths; each unread spec file loses 3."""
    before = {"a/openapi.yaml": _spec(0)}
    after = {"a/openapi.yaml": _spec(0, 0)}
    for i in range(unread):
        before[f"u{i}/openapi.yaml"] = _spec(i + 1, 3)
        after[f"u{i}/openapi.yaml"] = _spec(i + 1, 0)
    return _commit_pair(repo, before, after)


def test_only_read_file_removals_counted_unread_listed(tmp_path: Path) -> None:
    metric = api._breaking_metric(_two_files(tmp_path), {"a/openapi.yaml"})
    assert metric.value == 2, metric
    assert tuple(metric.computed_from) == ("a/openapi.yaml",)
    assert "not counted" in metric.derivation
    assert "u0/openapi.yaml (3)" in metric.derivation


def test_all_files_read_has_no_not_counted_text(tmp_path: Path) -> None:
    metric = api._breaking_metric(
        _two_files(tmp_path), {"a/openapi.yaml", "u0/openapi.yaml"}
    )
    assert metric.value == 5
    assert "not counted" not in metric.derivation


def test_no_read_file_still_abstains(tmp_path: Path) -> None:
    metric = api._breaking_metric(_two_files(tmp_path), set())
    assert metric.abstention is not None
    assert "was read" in metric.abstention
    assert "5 removed" in metric.abstention


def test_unread_list_is_capped(tmp_path: Path) -> None:
    scope = _two_files(tmp_path, unread=api.MAX_EXAMPLES + 2)
    metric = api._breaking_metric(scope, {"a/openapi.yaml"})
    assert metric.value == 2
    assert "and 2 more" in metric.derivation
    assert metric.derivation.count("openapi.yaml (3)") == api.MAX_EXAMPLES


def test_unread_file_without_removals_not_listed(tmp_path: Path) -> None:
    scope = _commit_pair(
        tmp_path,
        {"a/openapi.yaml": _spec(0), "b/openapi.yaml": _spec(1, 0)},
        {"a/openapi.yaml": _spec(0, 0), "b/openapi.yaml": _spec(1, 0) + "  /v1/n:\n"},
    )
    metric = api._breaking_metric(scope, {"a/openapi.yaml"})
    assert metric.value == 2
    assert "not counted" not in metric.derivation


def _api_breaking(payload: dict) -> dict:
    return next(
        m for m in payload["metrics"]["metrics"]
        if m["dimension"] == "api" and m["name"] == "breaking_api_changes_observed"
    )


def test_repo_route_token_extra_finds_removed_custom_route(tmp_path: Path) -> None:
    (tmp_path / ".easy-verifier.toml").write_text(
        '[conventions]\nroute_tokens = ["ANY=app.mount("]\n', encoding="utf-8"
    )
    _commit_pair(
        tmp_path,
        {"src/routes.ts": "app.mount('/v1/ping', h);\napp.mount('/v1/pong', h);\n"},
        {"src/routes.ts": "app.mount('/v1/ping', h);\n"},
    )
    payload = json.loads(
        score_repository(tmp_path, scope="changes", ref="HEAD~1..HEAD").serialize()
    )
    metric = _api_breaking(payload)
    assert metric["outcome"].get("value") == 1, metric
    assert "/v1/pong" in metric["derivation"]


def test_cli_and_mcp_agree_on_changes_payload(tmp_path: Path) -> None:
    from tests.integration.conftest import cli_json, mcp_call

    count = api.MAX_SPEC_FILES + 2
    before = {f"s{i:02d}/openapi.yaml": _spec(i, 3) for i in range(count)}
    after = {k: _spec(i, 0) for i, k in enumerate(before)}
    _commit_pair(tmp_path, before, after)
    args = ["--repo", str(tmp_path), "--scope", "changes", "--ref", "HEAD~1..HEAD"]
    cli = _api_breaking(cli_json("score", *args))
    mcp = _api_breaking(
        mcp_call(
            "score",
            {
                "repo": str(tmp_path),
                "scope": "changes",
                "ref": "HEAD~1..HEAD",
                "detail": "full",
            },
        )
    )
    assert cli == mcp
    assert cli["outcome"]["value"] == 3 * api.MAX_SPEC_FILES
    assert "not counted" in cli["derivation"]
