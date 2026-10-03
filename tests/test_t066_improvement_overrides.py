"""T066: the calling agent's repo-specific fix text on improvement-plan items.

FR-057 / DDR-0009 decision 6: ``write_report`` accepts ``improvements`` in
the agent-input document, validated against the plan computed from the same
score the report renders; the report shows the agent line labelled ``agent``
beside the engine line labelled ``engine``.
"""

from __future__ import annotations

import asyncio
import html
import importlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

from easy_verifier.core.findings import ValidationError
from easy_verifier.core.improve import (
    MAX_SUGGESTION_CHARS,
    ImprovementPlan,
    PlanItem,
    validate_improvements,
)
from easy_verifier.core.report import write_report
from easy_verifier.core.roles import RoleInputError, validate_agent_input
from easy_verifier.core.synthesis import combined_pack
from easy_verifier.dimensions import dimension_names

REPO_ROOT = Path(__file__).resolve().parents[1]

# Assembled at runtime: never commit a whole credential-shaped literal.
SECRET = "FAKEfake" + "9Qx7Lm2Vt8Rk4Wz6Np3Jh5"

# The tiny fixture repo below has exactly this P1 item and an abstained
# architecture dimension (checked by `test_fixture_plan_has_the_items_used`).
P1_ITEM = ("code-quality", "format_config_missing")
P2_ITEM = ("code-quality", "max_function_ccn")
ABSTAINED_DIMENSION = "architecture"


def _repo(root: Path) -> Path:
    files = {
        "README.md": "# Demo\n\nA tiny service.\n",
        "src/app.py": "def add(a, b):\n    return a + b\n",
        "tests/test_app.py": "from app import add\n\n"
        "def test_add():\n    assert add(1, 2) == 3\n",
        "pyproject.toml": "[project]\nname = 'demo'\n",
    }
    for relative, text in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


def _override(item=P1_ITEM, suggestion="Add a ruff format section to pyproject.toml."):
    return {"dimension": item[0], "metric_name": item[1], "suggestion": suggestion}


def _write(repo: Path, improvements, dimensions=None) -> str:
    packs = combined_pack(
        dimensions or dimension_names(), repo_path=repo, scope="worktree"
    )
    result = write_report(
        [], packs, repo, agent_input={"improvements": improvements}
    )
    return (repo / result.path).read_text(encoding="utf-8")


def _plan_section(document: str) -> str:
    start = document.index('<section class="improvement-plan">')
    return document[start : document.index("</section>", start)]


def _row(document: str, metric_name: str) -> str:
    section = _plan_section(document)
    marker = f"<code>{metric_name}</code>"
    start = section.rindex("<tr>", 0, section.index(marker))
    return section[start : section.index("</tr>", start)]


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    return _repo(tmp_path / "target")


def test_fixture_plan_has_the_items_used(repo: Path) -> None:
    from easy_verifier.core.score import score_repository

    plan = score_repository(repo, scope="worktree").to_dict()["improvement_plan"]
    keys = {
        (group, item["dimension"], item["metric_name"])
        for group, items in plan["groups"].items()
        for item in items
    }
    assert ("P1", *P1_ITEM) in keys
    assert ("P2", *P2_ITEM) in keys
    assert ABSTAINED_DIMENSION in {line["dimension"] for line in plan["abstained"]}


# AC 2 / success criterion 1


def test_named_item_renders_agent_text_labelled_agent_beside_engine_line(
    repo: Path,
) -> None:
    from easy_verifier.core.improve import FIX_HINTS

    document = _write(repo, [_override()])
    row = _row(document, P1_ITEM[1])
    assert "Add a ruff format section to pyproject.toml." in row
    assert 'class="fix-source fix-source-agent">agent<' in row
    # the engine line stays visible as fallback, labelled engine
    assert html.escape(FIX_HINTS[P1_ITEM[1]], quote=True) in row
    assert 'class="fix-source">engine<' in row
    assert row.index(">agent<") < row.index(">engine<")
    # exactly one agent label in the whole document
    assert document.count(">agent<") == 1


# AC 6


def test_items_without_a_suggestion_stay_engine_only(repo: Path) -> None:
    document = _write(repo, [_override()])
    other = _row(document, P2_ITEM[1])
    assert ">agent<" not in other
    assert 'class="fix-source">engine<' in other


def test_no_improvements_means_no_agent_label(repo: Path) -> None:
    for improvements in ([],):
        document = _write(repo, improvements)
        assert ">agent<" not in document
        assert 'class="fix-source">engine<' in document


# AC 3 / success criterion 2


@pytest.mark.parametrize(
    "item",
    [
        ("security", "no_such_metric"),
        ("no-such-dimension", "format_config_missing"),
        # an abstained dimension has a reason line, not an item
        (ABSTAINED_DIMENSION, "below_coverage_floor"),
        (ABSTAINED_DIMENSION, "decision_records_missing"),
    ],
)
def test_unknown_item_is_rejected_before_anything_is_written(
    repo: Path, item: tuple[str, str]
) -> None:
    with pytest.raises(ValidationError) as raised:
        _write(repo, [_override(item)])
    assert "not an item of the improvement plan" in str(raised.value)
    assert not (repo / "reports").exists()


# AC 4 / success criterion 4


@pytest.mark.parametrize(
    ("improvements", "expected"),
    [
        ("not a list", "must be a list"),
        (["not an object"], "must be an object"),
        ([{**_override(), "suggestion": 42}], "suggestion: must be a string"),
        ([{**_override(), "suggestion": None}], "suggestion: must be a string"),
        ([{**_override(), "suggestion": ""}], "suggestion: must not be empty"),
        ([{**_override(), "suggestion": "  \n\t"}], "suggestion: must not be empty"),
        (
            [{**_override(), "suggestion": "x" * (MAX_SUGGESTION_CHARS + 1)}],
            f"at most {MAX_SUGGESTION_CHARS}",
        ),
        ([{"dimension": "code-quality", "suggestion": "x"}], "metric_name: missing"),
        ([{**_override(), "dimension": 7}], "dimension: must be a string"),
        ([{**_override(), "fix": "x"}], "unknown key"),
        ([_override(), _override(suggestion="Another")], "duplicate"),
    ],
)
def test_malformed_improvements_are_rejected_before_anything_is_written(
    repo: Path, improvements, expected: str
) -> None:
    with pytest.raises(ValidationError) as raised:
        _write(repo, improvements)
    assert expected in str(raised.value)
    assert not (repo / "reports").exists()


def test_suggestion_at_the_length_limit_is_accepted(repo: Path) -> None:
    document = _write(repo, [_override(suggestion="y" * MAX_SUGGESTION_CHARS)])
    assert "y" * MAX_SUGGESTION_CHARS in document


def test_every_error_is_reported_at_once(repo: Path) -> None:
    with pytest.raises(ValidationError) as raised:
        _write(
            repo,
            [
                _override(("security", "no_such_metric")),
                {**_override(), "suggestion": ""},
            ],
        )
    assert len(raised.value.errors) == 2


def test_an_error_never_echoes_a_secret_from_the_item(repo: Path) -> None:
    with pytest.raises(ValidationError) as raised:
        _write(repo, [_override(("security", f"api_key={SECRET}"))])
    assert SECRET not in str(raised.value)


def test_improvements_without_a_plan_are_rejected(repo: Path) -> None:
    """A report over a subset of dimensions has no score and so no plan: an
    override can name nothing, and is refused rather than dropped."""
    with pytest.raises(ValidationError) as raised:
        _write(repo, [_override()], dimensions=["code-quality"])
    assert "no improvement plan" in str(raised.value)
    assert not (repo / "reports").exists()


# AC 5 / success criterion 3


def test_secret_in_a_suggestion_is_redacted_and_html_is_escaped(repo: Path) -> None:
    suggestion = f"Rotate api_key={SECRET} then <script>alert(1)</script> & move on"
    document = _write(repo, [_override(suggestion=suggestion)])
    assert SECRET not in document
    assert "<script>alert(1)</script>" not in document
    row = _row(document, P1_ITEM[1])
    assert "&lt;script&gt;alert(1)&lt;/script&gt; &amp; move on" in row
    assert "Rotate api_" in row  # redaction, not suppression


# Unit: the validator against a synthetic plan


def _synthetic_plan() -> ImprovementPlan:
    item = PlanItem(
        group="P1",
        dimension="security",
        area="secrets",
        metric_name="lockfile_missing",
        metric_value=1,
        unavailable_reason=None,
        comparison="at_most",
        threshold=0,
        weight=20,
        computed_from=(),
        dimension_gain=10,
        overall_gain=3,
        gain_basis="final",
    )
    return ImprovementPlan(
        items=(item,),
        abstained=(("architecture", "below_coverage_floor", "low coverage"),),
    )


def test_validator_returns_suggestions_keyed_by_item_identity() -> None:
    plan = _synthetic_plan()
    assert plan.item_keys() == (("security", "lockfile_missing"),)
    result = validate_improvements(
        [
            {
                "dimension": "security",
                "metric_name": "lockfile_missing",
                "suggestion": "  Commit package-lock.json.  ",
            }
        ],
        plan,
    )
    assert result == {("security", "lockfile_missing"): "Commit package-lock.json."}


def test_validator_names_the_known_items_on_an_unknown_one() -> None:
    with pytest.raises(ValidationError) as raised:
        validate_improvements(
            [{"dimension": "architecture", "metric_name": "x", "suggestion": "s"}],
            _synthetic_plan(),
        )
    assert "security/lockfile_missing" in str(raised.value)


def test_validator_caps_the_list_length() -> None:
    from easy_verifier.core.improve import MAX_IMPROVEMENTS

    with pytest.raises(ValidationError) as raised:
        validate_improvements([{}] * (MAX_IMPROVEMENTS + 1), _synthetic_plan())
    assert len(raised.value.errors) == 1
    assert f"{MAX_IMPROVEMENTS} limit" in str(raised.value)


# AC 1 / AC 7: the agent-input document accepts the key on both adapters


def test_agent_input_accepts_improvements_and_shape_checks_them(repo: Path) -> None:
    assert validate_agent_input({"improvements": [_override()]}, repo) == {}
    with pytest.raises(RoleInputError) as raised:
        validate_agent_input({"improvements": {"a": 1}}, repo)
    assert "improvements: must be a list" in str(raised.value)


def test_cli_and_mcp_write_the_same_plan_with_the_agent_fix(
    tmp_path: Path,
) -> None:
    agent_input = {
        "improvements": [_override(suggestion=f"Use ruff format; key={SECRET}")]
    }
    cli_repo = _repo(tmp_path / "cli")
    mcp_repo = _repo(tmp_path / "mcp")
    input_path = tmp_path / "agent_input.json"
    input_path.write_text(json.dumps(agent_input), encoding="utf-8")
    findings_path = tmp_path / "findings.json"
    findings_path.write_text("[]", encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "easy_verifier.adapters.cli",
            "write-report",
            "--repo",
            str(cli_repo),
            "--scope",
            "worktree",
            "--findings",
            str(findings_path),
            "--agent-input",
            str(input_path),
        ],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        env={"PYTHONPATH": str(REPO_ROOT / "src"), "PATH": "/usr/bin:/bin"},
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    cli_document = (cli_repo / json.loads(completed.stdout)["path"]).read_text(
        encoding="utf-8"
    )

    server = importlib.import_module("easy_verifier.adapters.mcp_server")
    _content, structured = asyncio.run(
        server.mcp.call_tool(
            "write_report",
            {
                "findings": [],
                "repo": str(mcp_repo),
                "scope": "worktree",
                "agent_input": agent_input,
            },
        )
    )
    mcp_document = (mcp_repo / structured["path"]).read_text(encoding="utf-8")

    assert ">agent<" in _plan_section(cli_document)
    assert SECRET not in cli_document and SECRET not in mcp_document
    assert _plan_section(cli_document) == _plan_section(mcp_document)


def test_cli_rejects_an_unknown_item_with_the_validation_exit(tmp_path: Path) -> None:
    repo = _repo(tmp_path / "target")
    input_path = tmp_path / "agent_input.json"
    input_path.write_text(
        json.dumps({"improvements": [_override(("security", "no_such_metric"))]}),
        encoding="utf-8",
    )
    findings_path = tmp_path / "findings.json"
    findings_path.write_text("[]", encoding="utf-8")
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "easy_verifier.adapters.cli",
            "write-report",
            "--repo",
            str(repo),
            "--scope",
            "worktree",
            "--findings",
            str(findings_path),
            "--agent-input",
            str(input_path),
        ],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        env={"PYTHONPATH": str(REPO_ROOT / "src"), "PATH": "/usr/bin:/bin"},
        check=False,
    )
    assert completed.returncode == 2
    assert "security/no_such_metric" in completed.stderr
    assert not (repo / "reports").exists()


# Edge: replay with stored agent input reproduces the same report (DDR-0005)


def test_replay_with_the_same_agent_input_is_byte_equal(repo: Path) -> None:
    first = _write(repo, [_override()])
    second = _write(repo, [_override()])
    generated = re.compile(r"<dt>Generated</dt><dd>[^<]*</dd>")
    advisory = re.compile(r'<section class="advisory">.*?</section>', re.S)

    def normalize(document: str) -> str:
        return advisory.sub("", generated.sub("", document))

    assert normalize(first) == normalize(second)


# T065 Stage 4 P2: a long abstention reason folds like the cited files


def test_p2_unavailable_reason_folds_into_a_details_block(repo: Path) -> None:
    document = _write(repo, [])
    row = _row(document, P2_ITEM[1])
    assert "<details><summary>Why not measured</summary>" in row
    assert "no source-file excerpt" in row


def test_mcp_write_report_description_tells_the_agent_about_improvements() -> None:
    server = importlib.import_module("easy_verifier.adapters.mcp_server")
    tools = {tool.name: tool for tool in asyncio.run(server.mcp.list_tools())}
    description = tools["write_report"].description
    assert '"improvements"' in description
    assert "metric_name" in description and "suggestion" in description
