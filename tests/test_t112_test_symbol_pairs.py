"""T112 -- agent-confirmed test <-> changed-symbol pairs (FR-084, change-risk S2).

A changed test is matched to a changed source file when it references one of
that file's changed symbols as a whole word (``basis: "symbol"``), else when
the names correspond (``basis: "name"``). MCP ``score`` asks the calling
agent to confirm, reject or add pairs (``needs_input.test_pairs``); the
answer (``agent_input.test_pairs``) is untrusted, and the bugfix and feature
rules use the final pair set. Synthetic git repositories only.
"""

from __future__ import annotations

import asyncio
import dataclasses
import json
import subprocess
import sys
from pathlib import Path

import pytest

from easy_verifier.core import gate
from easy_verifier.core.metric_tables import curated_metric_tables
from easy_verifier.core.models import MatchedPair, PairFacts
from easy_verifier.core.roles import validate_agent_input
from easy_verifier.core.score import TEST_PAIRS_IGNORED, score_repository
from easy_verifier.dimensions import change_risk
from easy_verifier.dimensions.blast_radius import _diff_files

RULE = "bugfix_without_regression_test"
FEATURE_RULE = "new_code_without_test_share"
SRC = Path(__file__).resolve().parents[1] / "src"

DATES = (
    "import datetime\n\n\ndef parse_date(text):\n"
    '    day, month, year = text.split("/")\n'
    "    return datetime.date(int(year), int(month), int(day) + 1)\n"
)
FIXED = DATES.replace("int(day) + 1", "int(day)")
API_TEST = (
    "from utils.dates import parse_date\n\n\ndef test_basic():\n"
    '    assert parse_date("01/02/2020").year == 2020\n'
)
API_TEST_CHANGED = API_TEST + (
    '\n\ndef test_keeps_the_day():\n    assert parse_date("01/02/2020").day == 1\n'
)


# --------------------------------------------------------------------------
# synthetic repositories
# --------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout


def _commit(repo: Path, message: str, files: dict[str, str | None]) -> None:
    for path, text in files.items():
        target = repo / path
        if text is None:
            target.unlink()
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)


def _init(tmp_path: Path, base: dict[str, str]) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "t")
    _commit(root, "chore: initial", base)
    return root


@pytest.fixture
def symbol_repo(tmp_path: Path) -> Path:
    """A bugfix whose only changed test calls the changed function but is
    named differently (the Demonstration repo)."""
    root = _init(
        tmp_path,
        {
            "pyproject.toml": "[project]\nname = 'demo'\n",
            "utils/dates.py": DATES,
            "tests/test_api.py": API_TEST,
        },
    )
    _commit(
        root,
        "fix: parse_date added one day",
        {"utils/dates.py": FIXED, "tests/test_api.py": API_TEST_CHANGED},
    )
    return root


def _risk(repo: Path, agent_input: dict | None = None, **kwargs) -> dict:
    kwargs.setdefault("scope", "changes")
    kwargs.setdefault("ref", "HEAD")
    return score_repository(repo, agent_input=agent_input, **kwargs).to_dict()[
        "change_risk"
    ]


def _input(risk: dict, name: str) -> dict:
    return next(item for item in risk["inputs"] if item["metric_name"] == name)


def _derivation(repo: Path, name: str, agent_input: dict | None = None) -> str:
    payload = score_repository(
        repo, scope="changes", ref="HEAD", agent_input=agent_input
    ).to_dict()
    return next(
        item["derivation"]
        for item in payload["metrics"]["metrics"]
        if item["dimension"] == "change-risk" and item["name"] == name
    )


def _mcp(arguments: dict) -> dict:
    from easy_verifier.adapters import mcp_server

    _content, result = asyncio.run(mcp_server.mcp.call_tool("score", arguments))
    return result


def _cli(repo: Path, tmp_path: Path, agent_input=None) -> str:
    argv = [sys.executable, "-m", "easy_verifier.adapters.cli", "score"]
    argv += ["--repo", str(repo), "--scope", "changes", "--ref", "HEAD"]
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
    return done.stdout


def _answer(*entries: dict) -> dict:
    return {"test_pairs": list(entries)}


def _entry(source: str, test: str, verdict: str = "confirm", **extra) -> dict:
    return {"source": source, "test": test, "verdict": verdict, "reason": "r", **extra}


# --------------------------------------------------------------------------
# AC1 -- changed symbols
# --------------------------------------------------------------------------


def _symbols_of(tmp_path: Path, path: str, before: str, after: str) -> tuple:
    root = _init(tmp_path, {path: before})
    _commit(root, "change", {path: after})
    (item,) = _diff_files(_git(root, "diff", "HEAD~1", "HEAD"))
    pattern = curated_metric_tables().public_declarations[Path(path).suffix]
    return change_risk.changed_symbols(item, pattern)


def test_python_body_edit_names_the_function_from_the_hunk_header(
    tmp_path: Path,
) -> None:
    body = "".join(f"    step_{n} = {n}\n" for n in range(12))
    before = f"def parse_date(text):\n{body}    return text\n"
    after = before.replace("return text", "return text.strip()")
    # The def line is far above the hunk: only the header names it.
    assert _symbols_of(tmp_path, "dates.py", before, after) == ("parse_date",)


def test_python_edit_inside_a_small_function_names_it(tmp_path: Path) -> None:
    assert _symbols_of(tmp_path, "dates.py", DATES, FIXED) == ("parse_date",)


def test_typescript_body_edit_names_the_exported_function(tmp_path: Path) -> None:
    body = "".join(f"  const step{n} = {n};\n" for n in range(12))
    before = f"export function parseDate(text: string) {{\n{body}  return text;\n}}\n"
    after = before.replace("return text;", "return text.trim();")
    assert _symbols_of(tmp_path, "dates.ts", before, after) == ("parseDate",)


def test_added_and_removed_declaration_lines_yield_their_names(
    tmp_path: Path,
) -> None:
    before = "def old_name(a):\n    return a\n"
    after = "def new_name(a):\n    return a\n\n\ndef helper_two(b):\n    return b\n"
    found = _symbols_of(tmp_path, "mod.py", before, after)
    assert {"old_name", "new_name", "helper_two"} <= set(found)


def test_hunk_without_a_declaration_yields_nothing(tmp_path: Path) -> None:
    before = "".join(f"VALUE_{n} = {n}\n" for n in range(10))
    after = before.replace("VALUE_5 = 5", "VALUE_5 = 6")
    assert _symbols_of(tmp_path, "consts.py", before, after) == ()


def test_language_without_a_pattern_yields_no_symbols_and_says_so(
    symbol_repo: Path, monkeypatch
) -> None:
    tables = curated_metric_tables()
    stripped = dataclasses.replace(tables, public_declarations={})
    monkeypatch.setattr(change_risk, "curated_metric_tables", lambda: stripped)
    risk = _risk(symbol_repo)
    assert risk["test_pairs"]["no_symbols"] == ["utils/dates.py"]
    assert risk["test_pairs"]["pairs"] == []
    assert "no changed symbols read for utils/dates.py" in _derivation(
        symbol_repo, RULE
    )


# --------------------------------------------------------------------------
# AC2 / AC3 -- proposed pairs and their basis
# --------------------------------------------------------------------------


def test_symbol_reference_pairs_although_names_differ(symbol_repo: Path) -> None:
    risk = _risk(symbol_repo)
    assert risk["test_pairs"]["pairs"] == [
        {
            "source": "utils/dates.py",
            "test": "tests/test_api.py",
            "basis": "symbol",
            "symbol": "parse_date",
            # The line the diff added, not the import above it.
            "ref": "tests/test_api.py:9",
            "status": "detected",
        }
    ]
    assert _input(risk, RULE)["passed"] is True
    assert risk["value"] == 100


def test_substring_of_a_changed_symbol_does_not_pair(tmp_path: Path) -> None:
    root = _init(
        tmp_path,
        {
            "pyproject.toml": "[project]\nname = 'demo'\n",
            "utils/dates.py": DATES,
            "tests/test_api.py": "def test_x():\n    assert True\n",
        },
    )
    _commit(
        root,
        "fix: day",
        {
            "utils/dates.py": FIXED,
            "tests/test_api.py": "from v2 import parse_date_v2\n\n\n"
            "def test_x():\n    assert parse_date_v2('x')\n",
        },
    )
    risk = _risk(root)
    assert risk["test_pairs"]["pairs"] == []
    assert risk["test_pairs"]["unpaired_tests"] == ["tests/test_api.py"]
    assert _input(risk, RULE)["passed"] is False


def test_test_in_another_project_does_not_pair(tmp_path: Path) -> None:
    root = _init(
        tmp_path,
        {
            "svc_a/pyproject.toml": "[project]\nname = 'a'\n",
            "svc_b/pyproject.toml": "[project]\nname = 'b'\n",
            "svc_a/utils/dates.py": DATES,
            "svc_b/tests/test_api.py": API_TEST,
        },
    )
    _commit(
        root,
        "fix: day",
        {"svc_a/utils/dates.py": FIXED, "svc_b/tests/test_api.py": API_TEST_CHANGED},
    )
    risk = _risk(root)
    assert risk["test_pairs"]["pairs"] == []
    assert _input(risk, RULE)["metric_value"] == 0


def test_test_that_only_defines_a_same_named_helper_does_not_pair(
    tmp_path: Path,
) -> None:
    helper = "def parse_date(text):\n    return text\n\n\ndef test_x():\n"
    root = _init(
        tmp_path,
        {
            "pyproject.toml": "[project]\nname = 'demo'\n",
            "utils/dates.py": DATES,
            "tests/test_api.py": helper + "    assert True\n",
        },
    )
    _commit(
        root,
        "fix: day",
        {
            "utils/dates.py": FIXED,
            "tests/test_api.py": helper + "    assert parse_date('x')\n",
        },
    )
    assert _risk(root)["test_pairs"]["pairs"] == []


@pytest.mark.parametrize("name", ["get", "run", "main", "setup"])
def test_short_or_common_symbols_never_pair(tmp_path: Path, name: str) -> None:
    source = f"def {name}(a):\n    return a\n"
    root = _init(
        tmp_path,
        {
            "pyproject.toml": "[project]\nname = 'demo'\n",
            "utils/tool.py": source,
            "tests/test_api.py": "def test_x():\n    assert True\n",
        },
    )
    _commit(
        root,
        "fix: tool",
        {
            "utils/tool.py": source.replace("return a", "return a + 1"),
            "tests/test_api.py": f"from utils.tool import {name}\n\n\n"
            f"def test_x():\n    assert {name}(1)\n",
        },
    )
    assert _risk(root)["test_pairs"]["pairs"] == []


def test_name_pair_stays_and_symbol_wins_when_both_hold(tmp_path: Path) -> None:
    root = _init(
        tmp_path,
        {
            "pyproject.toml": "[project]\nname = 'demo'\n",
            "src/calc.py": "def add_numbers(a, b):\n    return a + b\n",
            "src/fmt.py": "def show(a):\n    return str(a)\n",
            "tests/test_calc.py": "def test_x():\n    assert True\n",
            "tests/test_fmt.py": "def test_y():\n    assert True\n",
        },
    )
    _commit(
        root,
        "fix: both",
        {
            "src/calc.py": "def add_numbers(a, b):\n    return b + a\n",
            "src/fmt.py": "def show(a):\n    return repr(a)\n",
            "tests/test_calc.py": "from calc import add_numbers\n\n\n"
            "def test_x():\n    assert add_numbers(1, 2) == 3\n",
            "tests/test_fmt.py": "def test_y():\n    assert 1\n",
        },
    )
    pairs = _risk(root)["test_pairs"]["pairs"]
    assert [(p["source"], p["test"], p["basis"]) for p in pairs] == [
        ("src/calc.py", "tests/test_calc.py", "symbol"),
        ("src/fmt.py", "tests/test_fmt.py", "name"),
    ]
    assert pairs[1]["symbol"] is None and pairs[1]["ref"] is None


def test_deleted_test_never_pairs(tmp_path: Path) -> None:
    root = _init(
        tmp_path,
        {
            "pyproject.toml": "[project]\nname = 'demo'\n",
            "utils/dates.py": DATES,
            "tests/test_api.py": API_TEST,
        },
    )
    _commit(root, "fix: day", {"utils/dates.py": FIXED, "tests/test_api.py": None})
    risk = _risk(root)
    assert risk["test_pairs"]["pairs"] == []
    assert _input(risk, RULE)["passed"] is False


# --------------------------------------------------------------------------
# AC4 -- the MCP gate
# --------------------------------------------------------------------------


def test_mcp_asks_test_pairs_at_changes_scope(symbol_repo: Path) -> None:
    payload = _mcp({"repo": str(symbol_repo), "scope": "changes", "ref": "HEAD"})
    asked = payload["needs_input"]["test_pairs"]
    assert asked["proposals"] == [
        {
            "source": "utils/dates.py",
            "test": "tests/test_api.py",
            "basis": "symbol",
            "symbol": "parse_date",
            "ref": "tests/test_api.py:9",
        }
    ]
    assert asked["unpaired_tests"] == [] and asked["unpaired_sources"] == []
    assert asked["proposals_omitted"] == 0
    assert asked["listed_cap"] == gate.MAX_TEST_PAIRS_LISTED
    assert asked["instructions"] == gate.TEST_PAIRS_INSTRUCTIONS


def test_mcp_asks_at_worktree_scope(symbol_repo: Path) -> None:
    (symbol_repo / "utils/dates.py").write_text(DATES)
    (symbol_repo / "tests/test_api.py").write_text(API_TEST_CHANGED + "\n# more\n")
    payload = _mcp({"repo": str(symbol_repo), "scope": "worktree"})
    proposals = payload["needs_input"]["test_pairs"]["proposals"]
    assert [(p["basis"], p["symbol"]) for p in proposals] == [("symbol", "parse_date")]


def test_mcp_does_not_ask_after_a_valid_answer(symbol_repo: Path) -> None:
    answer = _answer(_entry("utils/dates.py", "tests/test_api.py"))
    payload = _mcp(
        {
            "repo": str(symbol_repo),
            "scope": "changes",
            "ref": "HEAD",
            "agent_input": answer,
        }
    )
    assert "test_pairs" not in payload.get("needs_input", {})


def test_mcp_never_asks_at_project_scope(symbol_repo: Path) -> None:
    payload = _mcp({"repo": str(symbol_repo), "scope": "project"})
    assert "test_pairs" not in payload.get("needs_input", {})
    assert "change_risk" not in payload


@pytest.mark.parametrize("kind", ["refactor", "chore"])
def test_no_gate_for_refactor_or_chore(symbol_repo: Path, kind: str) -> None:
    answer = {"change_kind": {"value": kind, "reason": "the diff"}}
    payload = _mcp(
        {
            "repo": str(symbol_repo),
            "scope": "changes",
            "ref": "HEAD",
            "agent_input": answer,
        }
    )
    assert "test_pairs" not in payload.get("needs_input", {})
    assert "test_pairs" not in payload["change_risk"]


def test_no_gate_without_changed_source(tmp_path: Path) -> None:
    root = _init(tmp_path, {"tests/test_api.py": API_TEST})
    _commit(root, "fix: test only", {"tests/test_api.py": API_TEST_CHANGED})
    payload = _mcp({"repo": str(root), "scope": "changes", "ref": "HEAD"})
    assert "test_pairs" not in payload.get("needs_input", {})


def test_request_caps_each_list_and_discloses_the_rest() -> None:
    many = tuple(
        MatchedPair(f"s{n}.py", f"t{n}.py", "name", None, None, "detected")
        for n in range(gate.MAX_TEST_PAIRS_LISTED + 7)
    )
    facts = PairFacts(many, many, (), (), ("t.py",) * 60, (), (), False)
    asked = gate.test_pairs_request(facts)
    assert len(asked["proposals"]) == gate.MAX_TEST_PAIRS_LISTED
    assert asked["proposals_omitted"] == 7
    assert asked["unpaired_tests_omitted"] == 60 - gate.MAX_TEST_PAIRS_LISTED


def test_score_tool_description_explains_test_pairs() -> None:
    from easy_verifier.adapters import mcp_server

    (tool,) = [t for t in asyncio.run(mcp_server.mcp.list_tools()) if t.name == "score"]
    assert "needs_input.test_pairs" in tool.description
    assert "agent_input.test_pairs" in tool.description


# --------------------------------------------------------------------------
# AC5 -- validation of agent_input.test_pairs (untrusted)
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "named"),
    [
        ("not a list", "test_pairs: must be a list"),
        (["x"], "test_pairs[0]: must be an object"),
        ([{**_entry("a", "b"), "extra": 1}], "test_pairs[0].extra: unknown key"),
        ([_entry("a", "b", verdict="maybe")], "test_pairs[0].verdict"),
        ([{**_entry("a", "b"), "reason": ""}], "test_pairs[0].reason"),
        ([{**_entry("a", "b"), "reason": "x" * 501}], "at most 500"),
        ([{**_entry("a", "b"), "ref": 3}], "test_pairs[0].ref"),
        ([{"test": "b", "verdict": "confirm", "reason": "r"}], ".source"),
    ],
)
def test_malformed_entries_are_rejected_naming_the_field(raw, named: str) -> None:
    entries, problems = gate.parse_test_pairs(raw)
    assert entries == ()
    assert named in problems[0][1]


def test_reason_of_500_characters_is_accepted() -> None:
    entry = {**_entry("a", "b"), "reason": "é" * 500}
    entries, problems = gate.parse_test_pairs([entry])
    assert problems == () and len(entries) == 1


def test_agent_input_accepts_the_test_pairs_key(tmp_path: Path) -> None:
    validate_agent_input({"test_pairs": []}, tmp_path)


@pytest.mark.parametrize(
    ("entry", "why"),
    [
        (_entry("utils/other.py", "tests/test_api.py"), "source is not a live source"),
        (_entry("utils/dates.py", "tests/test_nope.py"), "test is not a readable test"),
        (
            _entry("utils/dates.py", "tests/test_api.py", verdict="reject")
            | {"source": "README.md"},
            "source is not",
        ),
    ],
)
def test_entries_naming_files_outside_the_change_are_rejected(
    symbol_repo: Path, entry: dict, why: str
) -> None:
    risk = _risk(symbol_repo, _answer(entry))
    (rejected,) = risk["test_pairs"]["rejected"]
    assert rejected.startswith("test_pairs[0]: ") and why in rejected
    assert [p["status"] for p in risk["test_pairs"]["pairs"]] == ["detected"]


def _two_test_repo(tmp_path: Path) -> Path:
    """A bugfix of dates.py; tests/test_misc.py changes without referencing
    it; tests/test_old.py is deleted; svc_b is another project."""
    root = _init(
        tmp_path,
        {
            "pyproject.toml": "[project]\nname = 'demo'\n",
            "utils/dates.py": DATES,
            "tests/test_misc.py": "def test_m():\n    assert 1\n",
            "tests/test_old.py": "def test_o():\n    assert 1\n",
            "svc_b/pyproject.toml": "[project]\nname = 'b'\n",
            "svc_b/tests/test_b.py": "def test_b():\n    assert 1\n",
        },
    )
    _commit(
        root,
        "fix: day",
        {
            "utils/dates.py": FIXED,
            "tests/test_misc.py": "def test_m():\n    assert 2\n",
            "tests/test_old.py": None,
            "svc_b/tests/test_b.py": "def test_b():\n    assert 2\n",
        },
    )
    return root


@pytest.mark.parametrize(
    ("entry", "why"),
    [
        (
            _entry("utils/dates.py", "tests/test_old.py", ref="tests/test_old.py:1"),
            "test is deleted by this change",
        ),
        (
            _entry(
                "utils/dates.py", "svc_b/tests/test_b.py", ref="svc_b/tests/test_b.py:1"
            ),
            "different projects",
        ),
        (_entry("utils/dates.py", "tests/test_misc.py"), "needs a ref"),
        (
            _entry("utils/dates.py", "tests/test_misc.py", ref="tests/test_misc.py:99"),
            "ref does not name an existing line",
        ),
        (
            _entry("utils/dates.py", "tests/test_misc.py", ref="tests/other.py:1"),
            "ref does not name an existing line",
        ),
        (
            _entry("utils/dates.py", "tests/test_misc.py", verdict="reject"),
            "nothing to reject",
        ),
    ],
)
def test_invalid_added_pairs_are_rejected_and_change_nothing(
    tmp_path: Path, entry: dict, why: str
) -> None:
    root = _two_test_repo(tmp_path)
    risk = _risk(root, _answer(entry))
    (rejected,) = risk["test_pairs"]["rejected"]
    assert rejected.startswith("test_pairs[0]: ") and why in rejected
    assert risk["test_pairs"]["pairs"] == []
    assert _input(risk, RULE)["passed"] is False


def test_valid_and_invalid_entries_are_judged_independently(
    symbol_repo: Path,
) -> None:
    risk = _risk(
        symbol_repo,
        _answer(
            "garbage",
            _entry("utils/dates.py", "tests/test_api.py"),
            _entry("utils/dates.py", "tests/test_api.py", verdict="reject"),
        ),
    )
    assert risk["test_pairs"]["rejected"] == [
        "test_pairs[0]: must be an object",
        "test_pairs[2]: a duplicate answer for this pair; the first one counts",
    ]
    assert [p["status"] for p in risk["test_pairs"]["pairs"]] == ["confirmed"]


def test_secret_shaped_reason_is_redacted(symbol_repo: Path) -> None:
    secret = "token=" + "FAKEfake" + "Q7xZ9mK2pL4vN8wR3tY6"
    entry = _entry("utils/dates.py", "tests/test_api.py") | {"reason": secret}
    risk = _risk(symbol_repo, _answer(entry))
    assert secret not in json.dumps(risk)


def test_answer_with_no_pairs_to_answer_is_ignored_with_a_note(
    symbol_repo: Path,
) -> None:
    answer = _answer(_entry("utils/dates.py", "tests/test_api.py")) | {
        "change_kind": {"value": "refactor", "reason": "same behaviour"}
    }
    result = score_repository(
        symbol_repo, scope="changes", ref="HEAD", agent_input=answer
    )
    assert TEST_PAIRS_IGNORED in result.registry_notes


# --------------------------------------------------------------------------
# AC6 -- the final pair set drives the rules
# --------------------------------------------------------------------------


def test_rejecting_the_only_pair_flips_the_bugfix_to_fail(symbol_repo: Path) -> None:
    assert _input(_risk(symbol_repo), RULE)["passed"] is True
    entry = _entry("utils/dates.py", "tests/test_api.py", verdict="reject")
    risk = _risk(symbol_repo, _answer(entry))
    assert _input(risk, RULE)["passed"] is False
    assert risk["test_pairs"]["pairs"] == []
    assert risk["test_pairs"]["dropped"][0]["status"] == "rejected"
    assert "rejected by the agent: utils/dates.py -> tests/test_api.py" in _derivation(
        symbol_repo, RULE, _answer(entry)
    )


def test_adding_a_valid_pair_flips_the_bugfix_to_pass(tmp_path: Path) -> None:
    root = _two_test_repo(tmp_path)
    assert _input(_risk(root), RULE)["passed"] is False
    entry = _entry("utils/dates.py", "tests/test_misc.py", ref="tests/test_misc.py:2")
    risk = _risk(root, _answer(entry))
    assert _input(risk, RULE)["passed"] is True
    assert risk["test_pairs"]["pairs"] == [
        {
            "source": "utils/dates.py",
            "test": "tests/test_misc.py",
            "basis": "agent",
            "symbol": None,
            "ref": "tests/test_misc.py:2",
            "status": "added",
            "reason": "r",
        }
    ]
    assert "(agent at tests/test_misc.py:2, added)" in _derivation(
        root, RULE, _answer(entry)
    )


def test_derivation_says_detected_or_confirmed_with_the_basis(
    symbol_repo: Path,
) -> None:
    assert (
        "utils/dates.py -> tests/test_api.py (symbol parse_date at "
        "tests/test_api.py:9, detected)" in _derivation(symbol_repo, RULE)
    )
    answer = _answer(_entry("utils/dates.py", "tests/test_api.py"))
    assert "tests/test_api.py:9, confirmed)" in _derivation(symbol_repo, RULE, answer)


@pytest.fixture
def feature_repo(tmp_path: Path) -> Path:
    root = _init(
        tmp_path,
        {
            "pyproject.toml": "[project]\nname = 'demo'\n",
            "utils/dates.py": DATES,
            "tests/test_api.py": API_TEST,
            "tests/test_misc.py": "def test_m():\n    assert 1\n",
        },
    )
    _commit(
        root,
        "add: day handling",
        {
            "utils/dates.py": FIXED,
            "tests/test_api.py": API_TEST_CHANGED,
            "tests/test_misc.py": "def test_m():\n    assert 2\n",
        },
    )
    return root


def test_feature_share_follows_the_final_pair_set(feature_repo: Path) -> None:
    assert _input(_risk(feature_repo), FEATURE_RULE)["metric_value"] == 0
    rejected = _entry("utils/dates.py", "tests/test_api.py", verdict="reject")
    risk = _risk(feature_repo, _answer(rejected))
    assert _input(risk, FEATURE_RULE)["metric_value"] == 1
    added = _entry("utils/dates.py", "tests/test_misc.py", ref="tests/test_misc.py:1")
    risk = _risk(feature_repo, _answer(rejected, added))
    assert _input(risk, FEATURE_RULE)["metric_value"] == 0
    assert [p["status"] for p in risk["test_pairs"]["pairs"]] == ["added"]


# --------------------------------------------------------------------------
# AC7 -- CLI parity and replay
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "agent_input",
    [
        None,
        {"test_pairs": [_entry("utils/dates.py", "tests/test_api.py", "reject")]},
        {"test_pairs": ["garbage"]},
    ],
    ids=["no-answer", "valid-answer", "invalid-answer"],
)
def test_cli_matches_mcp_and_replays_byte_equal(
    symbol_repo: Path, tmp_path: Path, agent_input
) -> None:
    arguments = {"repo": str(symbol_repo), "scope": "changes", "ref": "HEAD"}
    if agent_input is not None:
        arguments["agent_input"] = agent_input
    mcp = _mcp(arguments)
    first = _cli(symbol_repo, tmp_path, agent_input)
    assert _cli(symbol_repo, tmp_path, agent_input) == first
    shared = {
        k: v for k, v in mcp.items() if k not in ("needs_input", "registry_notes")
    }
    dump = {"sort_keys": True, "separators": (",", ":")}
    assert json.dumps(json.loads(first), **dump) == json.dumps(shared, **dump)
    assert "test_pairs" in json.loads(first)["change_risk"]


# --------------------------------------------------------------------------
# AC10 -- report rows
# --------------------------------------------------------------------------


def test_report_lists_each_pair_with_basis_and_status(
    symbol_repo: Path, tmp_path: Path, monkeypatch
) -> None:
    from easy_verifier.core.report import write_report
    from easy_verifier.core.score import report_dimensions
    from easy_verifier.core.synthesis import combined_pack

    monkeypatch.setenv("EASY_VERIFIER_REPORTS_DIR", str(tmp_path / "reports"))
    names, _active = report_dimensions(symbol_repo, scope="changes")
    packs = combined_pack(names, repo_path=symbol_repo, scope="changes", ref="HEAD")
    html = Path(write_report([], packs, symbol_repo).absolute_path).read_text()
    assert (
        "Test pairs: utils/dates.py -&gt; tests/test_api.py (symbol parse_date at "
        "tests/test_api.py:9, detected)." in html
    )
