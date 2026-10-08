"""T078: local-layer and ``.easy-verifier.toml`` conventions used in scoring,
embedded in ``registry_entries`` so ``--agent-input`` replay is byte-equal.

User decision (option B, 2026-10-08): toml conventions are embedded as
``{"language": "conventions", ..., "citation_url": ".easy-verifier.toml",
"source_tag": "user-supplied"}`` items; on replay they apply to that call only
and are never written to the local layer. Local-layer convention values are
embedded as ``conventions`` items too and replay-saved like other entries.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from easy_verifier.adapters import mcp_server
from easy_verifier.core import registry as reg
from easy_verifier.core.roles import (
    GENERIC_PATTERNS,
    RoleInputError,
    _registry,
    validate_agent_input,
)
from easy_verifier.core.score import score_repository
from easy_verifier.core.structure import convention_values, layer_of, repo_conventions

SRC = Path(__file__).resolve().parents[1] / "src"
TOML = '[conventions]\nlayer_paths = ["api=**/endpoints/**"]\n'
LOCAL_URL = "https://example.org/our-layout"
TOML_ITEM = {
    "language": "conventions",
    "field": "layer_paths",
    "value": ["api=**/endpoints/**"],
    "citation_url": ".easy-verifier.toml",
    "source_tag": "user-supplied",
}


@pytest.fixture
def sot(tmp_path, monkeypatch) -> Path:
    root = tmp_path / "machine-a" / "sot"
    monkeypatch.setenv("EASY_VERIFIER_SOT", str(root))
    _registry.cache_clear()
    return root


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.email=t@example.org", "-c", "user.name=t", *args],
        cwd=repo,
        check=True,
        capture_output=True,
    )


def layered_repo(root: Path, *, toml: str | None = None) -> Path:
    """endpoints -> services -> repositories, and one data -> api import. The
    toml is git-ignored, so it is never evidence: deleting it changes only
    the conventions, which is what replay must reproduce."""
    (root / "app/endpoints").mkdir(parents=True)
    (root / "app/services").mkdir()
    (root / "app/repositories").mkdir()
    (root / "requirements.txt").write_text("fastapi\n")
    (root / ".gitignore").write_text(".easy-verifier.toml\n")
    (root / "app/endpoints/users.py").write_text(
        "from app.services.user_service import get_user\n\n\n"
        "def read_user(user_id):\n    return get_user(user_id)\n"
    )
    (root / "app/services/user_service.py").write_text(
        "from app.repositories.user_repo import load\n\n\n"
        "def get_user(user_id):\n    return load(user_id)\n"
    )
    (root / "app/repositories/user_repo.py").write_text(
        "from app.endpoints.users import read_user\n\n\n"
        "def load(user_id):\n    return {'id': user_id, 'via': read_user}\n"
    )
    _git(root, "init", "-q")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "init")
    if toml is not None:
        (root / ".easy-verifier.toml").write_text(toml)
    return root


def layer_violations(payload: dict) -> object:
    (metric,) = [
        m
        for m in payload["metrics"]["metrics"]
        if m["name"] == "layer_direction_violations"
        and m["dimension"] == "architecture"
    ]
    return metric


def metric(payload: dict, dimension: str, name: str) -> dict:
    (found,) = [
        m
        for m in payload["metrics"]["metrics"]
        if m["name"] == name and m["dimension"] == dimension
    ]
    return found


def score(repo: Path, agent_input: dict | None = None) -> dict:
    return score_repository(repo, agent_input=agent_input, batches="all").to_dict()


def cli(*args: str, sot_dir: Path) -> subprocess.CompletedProcess:
    env = dict(os.environ, EASY_VERIFIER_SOT=str(sot_dir), PYTHONPATH=str(SRC))
    return subprocess.run(
        [sys.executable, "-m", "easy_verifier.adapters.cli", *args],
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=False,
    )


def tree(root: Path) -> dict[str, bytes]:
    if not root.exists():
        return {}
    return {
        p.relative_to(root).as_posix(): p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


# ---------------------------------------------------------------------------
# merge: add-only, curated wins, uncached
# ---------------------------------------------------------------------------


def test_repo_conventions_add_toml_values_once_and_curated_wins(tmp_path, sot):
    repo = layered_repo(
        tmp_path / "r",
        toml='[conventions]\nlayer_paths = ["api=**/endpoints/**", '
        '"api=**/controllers/**"]\n',
    )
    entry = repo_conventions(repo)
    paths = convention_values(entry, "layer_paths")
    assert paths.count("api=**/controllers/**") == 1  # curated, not repeated
    assert "api=**/endpoints/**" in paths
    assert layer_of("app/endpoints/users.py", paths) == "api"
    # the curated value is not embedded
    assert reg.convention_entries(entry) == (TOML_ITEM,)


def test_repo_conventions_without_extras_is_curated(tmp_path, sot):
    repo = layered_repo(tmp_path / "r")
    entry = repo_conventions(repo)
    assert reg.convention_entries(entry) == ()
    assert convention_values(entry, "layer_paths") == convention_values(
        reg.load_conventions()[0], "layer_paths"
    )


# ---------------------------------------------------------------------------
# AC 1 / AC 4: toml layer_paths change the architecture metric, embedded
# ---------------------------------------------------------------------------


def test_toml_layer_paths_change_architecture_metric_and_are_embedded(tmp_path, sot):
    bare = score(layered_repo(tmp_path / "bare"))
    assert layer_violations(bare)["outcome"]["value"] == 0
    assert "registry_entries" not in bare

    extended = score(layered_repo(tmp_path / "ext", toml=TOML))
    found = layer_violations(extended)
    assert found["outcome"]["value"] == 1  # the data -> api import is now seen
    assert "3 of 3 non-shared source file(s)" in found["derivation"]
    assert "only the curated layer_paths apply" not in found["derivation"]
    assert extended["registry_entries"] == [TOML_ITEM]


# ---------------------------------------------------------------------------
# AC 2: route_tokens, requirement_item_patterns, issue_reference_patterns
# ---------------------------------------------------------------------------


def rf_repo(root: Path, *, toml: str | None = None) -> Path:
    (root / "app").mkdir(parents=True)
    (root / "tests").mkdir()
    (root / "requirements.txt").write_text("flask\n")
    (root / ".gitignore").write_text(".easy-verifier.toml\n")
    (root / "PRD.md").write_text("# PRD\n\nCAP-1 the user can ping the service.\n")
    (root / "app/web.py").write_text(
        "srv = object()\n\n\n@srv.endpoint(\"/ping\")\ndef ping():\n    return 'pong'\n"
    )
    (root / "tests/test_web.py").write_text(
        "def test_ping():\n    assert '/ping'\n"
    )
    _git(root, "init", "-q")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "init tkt1")
    for index in range(2, 23):
        (root / "app/web.py").write_text(
            (root / "app/web.py").read_text() + f"# change {index}\n"
        )
        _git(root, "commit", "-qam", f"change tkt{index}")
    if toml is not None:
        (root / ".easy-verifier.toml").write_text(toml)
    return root


RF_TOML = (
    "[conventions]\n"
    'route_tokens = ["GET=@*.endpoint("]\n'
    'requirement_item_patterns = ["id=CAP-<0-9>*"]\n'
    'issue_reference_patterns = ["tkt<0-9>*"]\n'
)


def test_toml_route_item_and_issue_patterns_reach_the_rules(tmp_path, sot):
    bare = score(rf_repo(tmp_path / "bare"))
    extended = score(rf_repo(tmp_path / "ext", toml=RF_TOML))
    rf = "requirement-fidelity"

    routes_bare = metric(bare, rf, "routes_without_test_share")
    routes_ext = metric(extended, rf, "routes_without_test_share")
    assert routes_bare["outcome"]["abstained"] is True
    assert routes_ext["outcome"]["abstained"] is False
    assert "app/web.py" in routes_ext["computed_from"]

    items_bare = metric(bare, rf, "requirement_items_traced_share")
    items_ext = metric(extended, rf, "requirement_items_traced_share")
    assert items_bare["outcome"]["abstained"] is True
    assert items_ext["outcome"]["abstained"] is False

    issues_bare = metric(bare, rf, "commits_with_issue_reference_share")
    issues_ext = metric(extended, rf, "commits_with_issue_reference_share")
    assert issues_bare["outcome"]["value"] == 0
    assert issues_ext["outcome"]["value"] == 1.0

    # api reads the same route tokens (T075 shared tokens)
    api_bare = [m for m in bare["metrics"]["metrics"] if m["dimension"] == "api"]
    api_ext = [m for m in extended["metrics"]["metrics"] if m["dimension"] == "api"]
    assert api_bare != api_ext
    assert {item["field"] for item in extended["registry_entries"]} == {
        "issue_reference_patterns",
        "requirement_item_patterns",
        "route_tokens",
    }


# ---------------------------------------------------------------------------
# AC 3: local-layer conventions.toml, curated wins; replay-saved
# ---------------------------------------------------------------------------


def save_local_layer_paths(root: Path, values: list[str]) -> None:
    entries, errors = reg.parse_local_entries(
        [
            {
                "language": "conventions",
                "field": "layer_paths",
                "value": values,
                "citation_url": LOCAL_URL,
                "source_tag": "user-supplied",
            }
        ],
        GENERIC_PATTERNS,
    )
    assert errors == []
    reg.save_local_entries(entries, root, known_roles=GENERIC_PATTERNS)


def test_local_layer_conventions_are_used_and_embedded(tmp_path, sot):
    save_local_layer_paths(sot, ["api=**/endpoints/**", "api=**/controllers/**"])
    payload = score(layered_repo(tmp_path / "r"))
    assert layer_violations(payload)["outcome"]["value"] == 1
    assert payload["registry_entries"] == [
        {
            "language": "conventions",
            "field": "layer_paths",
            "value": ["api=**/endpoints/**"],  # the curated value is dropped
            "citation_url": LOCAL_URL,
            "source_tag": "user-supplied",
        }
    ]


def test_local_layer_replay_is_byte_equal_and_saved(tmp_path):
    machine_a, machine_b = tmp_path / "a-sot", tmp_path / "b-sot"
    save_local_layer_paths(machine_a, ["api=**/endpoints/**"])
    repo = layered_repo(tmp_path / "r")
    common = ("--repo", str(repo), "--scope", "project", "--all")
    original = cli("score", *common, sot_dir=machine_a)
    assert original.returncode == 0, original.stderr
    replay = tmp_path / "replay.json"
    replay.write_text(
        json.dumps(
            {"registry_entries": json.loads(original.stdout)["registry_entries"]}
        )
    )
    replayed = cli("score", *common, "--agent-input", str(replay), sot_dir=machine_b)
    assert replayed.returncode == 0, replayed.stderr
    assert replayed.stdout == original.stdout
    assert "conventions.toml" in tree(machine_b)  # replay-saved like other entries


# ---------------------------------------------------------------------------
# AC 5: replay of toml items is byte-equal and never written to disk
# ---------------------------------------------------------------------------


def test_toml_replay_is_byte_equal_without_the_toml_and_writes_nothing(tmp_path):
    machine_a, machine_b = tmp_path / "a-sot", tmp_path / "b-sot"
    repo = layered_repo(tmp_path / "r", toml=TOML)
    common = ("--repo", str(repo), "--scope", "project", "--all")
    original = cli("score", *common, sot_dir=machine_a)
    assert original.returncode == 0, original.stderr
    entries = json.loads(original.stdout)["registry_entries"]
    assert entries == [TOML_ITEM]

    (repo / ".easy-verifier.toml").unlink()
    bare = cli("score", *common, sot_dir=machine_b)
    assert bare.stdout != original.stdout  # the toml did change the score

    replay = tmp_path / "replay.json"
    replay.write_text(json.dumps({"registry_entries": entries}))
    before = tree(machine_b)
    replayed = cli("score", *common, "--agent-input", str(replay), sot_dir=machine_b)
    assert replayed.returncode == 0, replayed.stderr
    assert replayed.stdout == original.stdout
    assert tree(machine_b) == before  # per call only: nothing saved


# ---------------------------------------------------------------------------
# AC 6: CLI / MCP parity on the AC 1 repo
# ---------------------------------------------------------------------------


def test_cli_and_mcp_payloads_match_with_toml_conventions(tmp_path, sot):
    repo = layered_repo(tmp_path / "r", toml=TOML)
    completed = cli(
        "score", "--repo", str(repo), "--scope", "project", "--all", sot_dir=sot
    )
    assert completed.returncode == 0, completed.stderr
    _content, mcp_payload = asyncio.run(
        mcp_server.mcp.call_tool(
            "score",
            {"repo": str(repo), "scope": "project", "agent_input": {"batches": "all"}},
        )
    )
    cli_payload = json.loads(completed.stdout)
    for key in set(mcp_payload) - set(cli_payload):  # MCP-only questions
        mcp_payload.pop(key)
    assert cli_payload == mcp_payload
    assert cli_payload["registry_entries"] == [TOML_ITEM]


# ---------------------------------------------------------------------------
# same MCP process: no leak between calls
# ---------------------------------------------------------------------------


def test_no_leak_between_back_to_back_mcp_calls(tmp_path, sot):
    with_toml = layered_repo(tmp_path / "with", toml=TOML)
    without = layered_repo(tmp_path / "without")

    def call(repo: Path, agent_input: dict | None = None) -> dict:
        payload = mcp_server.score(repo=str(repo), agent_input=agent_input)
        return {k: v for k, v in payload.items() if k != "needs_input"}

    first_bare = call(without)
    assert layer_violations(call(with_toml))["outcome"]["value"] == 1
    assert call(without) == first_bare
    # a replayed toml item applies to its own call only
    assert layer_violations(
        call(without, {"registry_entries": [TOML_ITEM]})
    )["outcome"]["value"] == 1
    assert call(without) == first_bare
    assert layer_violations(first_bare)["outcome"]["value"] == 0


# ---------------------------------------------------------------------------
# AC 8: validation of agent-supplied convention entries
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("overrides", "reason"),
    [
        ({"source_tag": "agent-researched"}, "citation_url"),
        ({"language": "python", "field": "route_tokens", "value": ["GET=@x("]},
         "citation_url"),
        ({"field": "manifests", "value": ["x.toml"]}, "unknown field"),
        ({"value": ["web=**/endpoints/**"]}, "layer"),
        ({"citation_url": "http://example.org"}, "citation_url"),
    ],
)
def test_invalid_convention_entries_are_refused_with_a_reason(
    tmp_path, sot, overrides, reason
):
    repo = layered_repo(tmp_path / "r")
    item = {**TOML_ITEM, **overrides}
    with pytest.raises(RoleInputError) as caught:
        validate_agent_input({"registry_entries": [item]}, repo)
    assert reason in str(caught.value)


def test_framework_entry_cannot_use_the_toml_source(sot):
    _entries, errors = reg.parse_local_entries(
        [
            {
                "framework": "express",
                "extends": "javascript",
                "field": "route_tokens",
                "value": ["GET=app.get("],
                "citation_url": ".easy-verifier.toml",
                "source_tag": "user-supplied",
            }
        ],
        GENERIC_PATTERNS,
    )
    assert errors and "citation_url" in errors[0]


def test_valid_toml_item_is_accepted(tmp_path, sot):
    repo = layered_repo(tmp_path / "r")
    validate_agent_input({"registry_entries": [TOML_ITEM]}, repo)
    entries, errors = reg.parse_local_entries([TOML_ITEM], GENERIC_PATTERNS)
    assert errors == [] and reg.is_config_convention(entries[0])


# ---------------------------------------------------------------------------
# Stage 4 finding: a secret-shaped convention value is never used or embedded
# ---------------------------------------------------------------------------

SECRET_TOKEN = "GET=password=FAKEfakeFAKEfake9x8y7z"


def test_secret_shaped_toml_value_is_ignored_with_a_warning(tmp_path, sot):
    repo = rf_repo(
        tmp_path / "r",
        toml=f'[conventions]\nroute_tokens = ["{SECRET_TOKEN}", "GET=@*.endpoint("]\n',
    )
    entry = repo_conventions(repo)
    assert SECRET_TOKEN not in convention_values(entry, "route_tokens")  # not used
    assert "GET=@*.endpoint(" in convention_values(entry, "route_tokens")

    result = score_repository(repo, batches="all")
    payload = json.dumps(result.to_dict())
    assert "FAKEfake" not in payload  # not embedded, not quoted anywhere
    assert [item["value"] for item in result.to_dict()["registry_entries"]] == [
        ["GET=@*.endpoint("]
    ]
    notes = [n for n in result.registry_notes if "looks like a secret" in n]
    assert notes == [
        "conventions.route_tokens: 1 value(s) from .easy-verifier.toml "
        "ignored: looks like a secret"
    ]
    assert "FAKEfake" not in notes[0]
