"""T109 -- the ``change_kind`` gate (FR-081, FR-022, FR-034; DDR-0014).

The engine detects a change's kind; the MCP ``score`` response asks the
calling agent to confirm or override it (``needs_input.change_kind``), and the
answer comes back as ``agent_input.change_kind = {value, reason}``. A valid
answer replaces the detected kind (``source: "confirmed"``, with the agent's
redacted reason) and the rating follows it; an invalid one is rejected in the
payload and the detected kind is kept. The CLI never asks but replays the same
answer through ``--agent-input``, byte-equal to MCP.
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from pathlib import Path

import pytest

from easy_verifier.core.gate import (
    CHANGE_KIND_INSTRUCTIONS,
    MAX_CHANGE_KIND_REASON_CHARS,
    change_kind_request,
    parse_change_kind,
)
from easy_verifier.core.redact import redact
from easy_verifier.core.score import score_repository

RULE = "bugfix_without_regression_test"
ALLOWED = ["bugfix", "feature", "refactor", "chore"]
SRC = Path(__file__).resolve().parents[1] / "src"


# --------------------------------------------------------------------------
# synthetic repositories
# --------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


def _commit(repo: Path, message: str, files: dict[str, str]) -> None:
    for path, text in files.items():
        target = repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)


BASE = {
    "pyproject.toml": "[project]\nname = 'demo'\n",
    "src/calc.py": "def add(a, b):\n    return a + b\n",
    "tests/test_calc.py": (
        "from calc import add\n\n\ndef test_add():\n    assert add(1, 2) == 3\n"
    ),
    "README.md": "# demo\n",
}
CHANGE = {"src/calc.py": "def add(a, b):\n    return b + a\n"}


def _repo(tmp_path: Path, subject: str) -> Path:
    """One source-only commit on top of a base; ``subject`` sets the kind."""
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "t")
    _commit(root, "chore: initial", BASE)
    _commit(root, subject, CHANGE)
    return root


@pytest.fixture
def feature_repo(tmp_path: Path) -> Path:
    return _repo(tmp_path, "add: swap operands")  # no signal -> feature


@pytest.fixture
def bugfix_repo(tmp_path: Path) -> Path:
    return _repo(tmp_path, "fix: swap operands")


def _answer(value: object = "bugfix", reason: object = "swaps operands") -> dict:
    return {"change_kind": {"value": value, "reason": reason}}


def _headline(repo: Path, agent_input: dict | None = None, **kwargs) -> dict:
    kwargs.setdefault("scope", "changes")
    kwargs.setdefault("ref", "HEAD")
    result = score_repository(repo, agent_input=agent_input, **kwargs)
    return result.to_dict()["change_risk"]


def _mcp(arguments: dict) -> dict:
    from easy_verifier.adapters import mcp_server

    _content, result = asyncio.run(mcp_server.mcp.call_tool("score", arguments))
    return result


def _cli(repo: Path, tmp_path: Path, *extra: str, agent_input=None) -> dict:
    argv = [sys.executable, "-m", "easy_verifier.adapters.cli", "score"]
    argv += ["--repo", str(repo), *extra]
    if agent_input is not None:
        document = tmp_path / "agent-input.json"
        document.write_text(json.dumps(agent_input), encoding="utf-8")
        argv += ["--agent-input", str(document)]
    done = subprocess.run(
        argv,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        env={"PYTHONPATH": str(SRC), "PATH": "/usr/bin:/bin"},
        check=False,
    )
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


# --------------------------------------------------------------------------
# AC2 / AC3 -- validation of agent_input.change_kind
# --------------------------------------------------------------------------


@pytest.mark.parametrize("value", ALLOWED)
def test_valid_answer_is_accepted(value: str) -> None:
    answer, problems = parse_change_kind({"value": value, "reason": "the diff"})
    assert problems == []
    assert answer == {"value": value, "reason": "the diff"}


@pytest.mark.parametrize(
    ("raw", "named"),
    [
        ("bugfix", "change_kind: must be an object"),
        (["bugfix"], "change_kind: must be an object"),
        ({"value": "hotfix", "reason": "r"}, "change_kind.value: must be one of"),
        ({"value": "BUGFIX", "reason": "r"}, "change_kind.value: must be one of"),
        ({"value": 1, "reason": "r"}, "change_kind.value: must be one of"),
        ({"reason": "r"}, "change_kind.value: must be one of"),
        ({"value": "bugfix"}, "change_kind.reason: must be a non-empty string"),
        ({"value": "bugfix", "reason": ""}, "change_kind.reason: must be a non-empty"),
        (
            {"value": "bugfix", "reason": "   "},
            "change_kind.reason: must be a non-empty",
        ),
        ({"value": "bugfix", "reason": 7}, "change_kind.reason: must be a non-empty"),
        (
            {"value": "bugfix", "reason": None},
            "change_kind.reason: must be a non-empty",
        ),
        (
            {"value": "bugfix", "reason": "x" * (MAX_CHANGE_KIND_REASON_CHARS + 1)},
            "change_kind.reason: at most 500 characters",
        ),
        (
            {"value": "bugfix", "reason": "r", "confidence": 1},
            "change_kind.confidence: unknown key",
        ),
    ],
)
def test_invalid_answer_is_rejected_naming_the_field(raw: object, named: str) -> None:
    answer, problems = parse_change_kind(raw)
    assert answer is None
    assert any(named in problem for problem in problems), problems


def test_reason_bound_is_500_characters_including_unicode() -> None:
    assert MAX_CHANGE_KIND_REASON_CHARS == 500
    ok = "é" * 500
    assert parse_change_kind({"value": "chore", "reason": ok}) == (
        {"value": "chore", "reason": ok},
        [],
    )
    answer, problems = parse_change_kind({"value": "chore", "reason": "é" * 501})
    assert answer is None and problems


def test_unknown_key_in_rejection_is_redacted() -> None:
    secret = "token: " + "FAKEfake" + "Q7x9Lm2Pz8Rt4Kw6Yb3N"
    _answer_, problems = parse_change_kind(
        {"value": "bugfix", "reason": "r", secret: 1}
    )
    assert problems and secret not in " ".join(problems)


# --------------------------------------------------------------------------
# AC1 -- the request
# --------------------------------------------------------------------------


def test_request_carries_proposal_signals_allowed_and_fixed_instructions(
    bugfix_repo: Path,
) -> None:
    kind = score_repository(bugfix_repo, scope="changes", ref="HEAD").change_kind
    request = change_kind_request(kind)
    assert set(request) == {
        "proposal",
        "signals",
        "signals_omitted",
        "allowed",
        "instructions",
    }
    assert request["proposal"] == "bugfix"
    assert request["allowed"] == ALLOWED
    assert request["signals"][0]["source"] == "commit subject"
    assert request["instructions"] == CHANGE_KIND_INSTRUCTIONS
    for word in ("diff", "agent_input.change_kind", "value", "reason", "500"):
        assert word in CHANGE_KIND_INSTRUCTIONS


def test_mcp_asks_at_changes_scope_and_cli_never_does(
    bugfix_repo: Path, tmp_path: Path
) -> None:
    payload = _mcp({"repo": str(bugfix_repo), "scope": "changes", "ref": "HEAD"})
    asked = payload["needs_input"]["change_kind"]
    assert asked["proposal"] == "bugfix" and asked["allowed"] == ALLOWED
    cli = _cli(bugfix_repo, tmp_path, "--scope", "changes", "--ref", "HEAD")
    assert "needs_input" not in cli
    assert "change_kind" not in json.dumps(
        {k: v for k, v in cli.items() if k != "change_risk"}
    )


def test_mcp_asks_at_worktree_scope(bugfix_repo: Path) -> None:
    (bugfix_repo / "src" / "calc.py").write_text("def add(a, b):\n    return 0\n")
    payload = _mcp({"repo": str(bugfix_repo), "scope": "worktree"})
    assert payload["needs_input"]["change_kind"]["proposal"] == "feature"


def test_mcp_does_not_ask_after_a_valid_answer(bugfix_repo: Path) -> None:
    payload = _mcp(
        {
            "repo": str(bugfix_repo),
            "scope": "changes",
            "ref": "HEAD",
            "agent_input": _answer("bugfix"),
        }
    )
    assert "change_kind" not in payload.get("needs_input", {})


def test_mcp_asks_again_after_an_invalid_answer(bugfix_repo: Path) -> None:
    payload = _mcp(
        {
            "repo": str(bugfix_repo),
            "scope": "changes",
            "ref": "HEAD",
            "agent_input": _answer("hotfix"),
        }
    )
    assert payload["needs_input"]["change_kind"]["proposal"] == "bugfix"


def test_mcp_never_asks_at_project_scope(bugfix_repo: Path) -> None:
    payload = _mcp({"repo": str(bugfix_repo), "scope": "project"})
    assert "change_kind" not in payload.get("needs_input", {})


def test_score_tool_description_explains_change_kind() -> None:
    from easy_verifier.adapters import mcp_server

    tool = mcp_server.mcp._tool_manager.get_tool("score")
    assert "needs_input.change_kind" in tool.description
    assert "agent_input.change_kind" in tool.description


# --------------------------------------------------------------------------
# AC2 / AC5 -- a valid answer replaces the kind and the rating follows it
# --------------------------------------------------------------------------


def test_confirmed_bugfix_over_detected_feature_applies_the_rule(
    feature_repo: Path,
) -> None:
    before = _headline(feature_repo)
    assert before["change_kind"]["value"] == "feature"
    assert before["change_kind"]["source"] == "detected"
    assert before["kind"] == "rating_abstention"
    assert "rules for feature arrive in T110" in json.dumps(before)

    after = _headline(feature_repo, _answer("bugfix", "swapping operands fixes a sum"))
    assert after["change_kind"]["value"] == "bugfix"
    assert after["change_kind"]["source"] == "confirmed"
    assert after["change_kind"]["reason"] == "swapping operands fixes a sum"
    assert after["kind"] == "rating"
    (rule,) = after["inputs"]
    assert rule["metric_name"] == RULE
    assert rule["passed"] is False and rule["metric_value"] == 0
    # the detected signals stay disclosed beside the confirmed value
    assert after["change_kind"]["signals"] == before["change_kind"]["signals"]


def test_confirmed_feature_over_detected_bugfix_abstains(bugfix_repo: Path) -> None:
    before = _headline(bugfix_repo)
    assert before["change_kind"]["value"] == "bugfix"
    assert before["kind"] == "rating" and before["inputs"][0]["passed"] is False

    after = _headline(bugfix_repo, _answer("feature", "adds behaviour"))
    assert after["change_kind"] == {
        **before["change_kind"],
        "value": "feature",
        "source": "confirmed",
        "reason": "adds behaviour",
    }
    assert after["kind"] == "rating_abstention"
    assert "rules for feature arrive in T110" in json.dumps(after)


def test_answer_equal_to_detected_is_confirmed_and_rating_unchanged(
    bugfix_repo: Path,
) -> None:
    before = _headline(bugfix_repo)
    after = _headline(bugfix_repo, _answer("bugfix", "it fixes a bug"))
    assert after["change_kind"]["source"] == "confirmed"
    assert after["change_kind"]["value"] == "bugfix"
    strip = {"change_kind"}
    assert {k: v for k, v in after.items() if k not in strip} == {
        k: v for k, v in before.items() if k not in strip
    }


def test_secret_shaped_reason_is_redacted(bugfix_repo: Path) -> None:
    secret = "token: " + "FAKEfake" + "Q7x9Lm2Pz8Rt4Kw6Yb3N"
    reason = "fixes the sum; " + secret
    assert redact(reason) != reason
    result = score_repository(
        bugfix_repo, scope="changes", ref="HEAD", agent_input=_answer("bugfix", reason)
    )
    headline = result.to_dict()["change_risk"]
    assert headline["change_kind"]["reason"] == redact(reason)
    assert "Q7x9Lm2Pz8Rt4Kw6Yb3N" not in result.serialize()


# --------------------------------------------------------------------------
# AC3 -- invalid answers are rejected in the payload, never a crash
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw",
    [
        {"value": "hotfix", "reason": "r"},
        {"value": "bugfix", "reason": ""},
        {"value": "bugfix", "reason": "x" * 501},
        {"value": "bugfix"},
        {"value": "bugfix", "reason": "r", "extra": True},
        "bugfix",
        None,
    ],
)
def test_invalid_answer_keeps_the_detected_kind(feature_repo: Path, raw) -> None:
    before = _headline(feature_repo)
    after = _headline(feature_repo, {"change_kind": raw})
    assert after["change_kind"]["source"] == "detected"
    assert after["change_kind"]["value"] == "feature"
    assert "reason" not in after["change_kind"]
    rejected = after["change_kind"]["rejected"]
    assert rejected and all(item.startswith("change_kind") for item in rejected)
    assert {k: v for k, v in after.items() if k != "change_kind"} == {
        k: v for k, v in before.items() if k != "change_kind"
    }


def test_no_answer_has_no_reason_or_rejected_key(bugfix_repo: Path) -> None:
    kind = _headline(bugfix_repo)["change_kind"]
    assert set(kind) == {"value", "source", "signals", "signals_omitted"}


def test_answer_at_project_scope_is_ignored_with_a_note(bugfix_repo: Path) -> None:
    plain = score_repository(bugfix_repo, scope="project")
    answered = score_repository(bugfix_repo, scope="project", agent_input=_answer())
    assert "change_risk" not in answered.to_dict()
    assert any("change_kind" in note for note in answered.registry_notes)
    assert not any("change_kind" in note for note in plain.registry_notes)
    assert answered.serialize() == plain.serialize()


def test_answer_at_task_scope_is_ignored_with_a_note(bugfix_repo: Path) -> None:
    result = score_repository(
        bugfix_repo, scope="task", task_id="T1", agent_input=_answer()
    )
    assert result.to_dict()["change_risk"]["change_kind"] is None
    assert any("change_kind" in note for note in result.registry_notes)


def test_change_kind_and_picks_are_validated_independently(
    feature_repo: Path,
) -> None:
    picks = {"requirements-doc": ["README.md"]}
    both = score_repository(
        feature_repo,
        scope="changes",
        ref="HEAD",
        agent_input={"picks": picks, **_answer("hotfix")},
    ).to_dict()
    only_picks = score_repository(
        feature_repo, scope="changes", ref="HEAD", agent_input={"picks": picks}
    ).to_dict()
    assert both["change_risk"]["change_kind"]["rejected"]
    assert {k: v for k, v in both.items() if k != "change_risk"} == {
        k: v for k, v in only_picks.items() if k != "change_risk"
    }
    applied = score_repository(
        feature_repo,
        scope="changes",
        ref="HEAD",
        agent_input={"picks": picks, **_answer("bugfix")},
    ).to_dict()
    assert applied["change_risk"]["change_kind"]["source"] == "confirmed"
    assert _outside_change_risk(applied) == _outside_change_risk(only_picks)


def _outside_change_risk(payload: dict) -> dict:
    """The payload without the change-risk headline and its own metrics."""
    rest = {k: v for k, v in payload.items() if k != "change_risk"}
    metrics = rest["metrics"]["metrics"]
    rest["metrics"] = {
        **rest["metrics"],
        "metrics": [m for m in metrics if m["dimension"] != "change-risk"],
    }
    return rest


# --------------------------------------------------------------------------
# AC4 -- CLI and MCP payloads are byte-equal with and without the answer
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "agent_input",
    [None, _answer("bugfix", "swaps operands"), _answer("hotfix", "bad")],
    ids=["no-answer", "valid-answer", "invalid-answer"],
)
def test_cli_and_mcp_payloads_are_byte_equal(
    feature_repo: Path, tmp_path: Path, agent_input
) -> None:
    arguments = {"repo": str(feature_repo), "scope": "changes", "ref": "HEAD"}
    if agent_input is not None:
        arguments["agent_input"] = agent_input
    mcp = _mcp(arguments)
    cli = _cli(
        feature_repo,
        tmp_path,
        "--scope",
        "changes",
        "--ref",
        "HEAD",
        agent_input=agent_input,
    )
    # needs_input and registry_notes are MCP-only (FR-034, DDR-0005): the CLI
    # never asks, and prints registry notes to stderr.
    shared = {
        k: v for k, v in mcp.items() if k not in ("needs_input", "registry_notes")
    }
    dump = {"sort_keys": True, "separators": (",", ":")}
    assert json.dumps(cli, **dump) == json.dumps(shared, **dump)
    if agent_input is not None and agent_input["change_kind"]["value"] == "bugfix":
        assert cli["change_risk"]["change_kind"]["source"] == "confirmed"
