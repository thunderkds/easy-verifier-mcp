"""T015 acceptance tests for the complete path-mode CLI."""

from __future__ import annotations

import ast
import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

from easy_verifier.adapters import mcp_server
from easy_verifier.dimensions import dimension_names, list_dimensions

REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "src/easy_verifier/adapters/cli.py"
MODULE_COMMAND = [sys.executable, "-m", "easy_verifier.adapters.cli"]
FROZEN_REPORT_RUNNER = """
import sys
from datetime import UTC, datetime
from easy_verifier.core import report

class FrozenDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 9, 2, 5, 0, 0, 123456, tzinfo=tz or UTC)

report.datetime = FrozenDateTime
from easy_verifier.adapters.cli import main
raise SystemExit(main(sys.argv[1:]))
"""


def _env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    return env


def _run(*args: str, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [*MODULE_COMMAND, *args],
        input=input_text,
        capture_output=True,
        text=True,
        env=_env(),
        check=False,
    )


def _target(path: Path) -> Path:
    path.mkdir()
    (path / "README.md").write_text("# Target\n", encoding="utf-8")
    return path


def test_help_lists_every_descriptor_purpose() -> None:
    completed = _run("--help")

    assert completed.returncode == 0
    for descriptor in list_dimensions():
        assert descriptor.name in completed.stdout
        assert descriptor.purpose in completed.stdout


def test_discovery_is_machine_readable_and_needs_no_repo() -> None:
    completed = _run("list-dimensions")

    assert completed.returncode == 0
    assert completed.stderr == ""
    payload = json.loads(completed.stdout)
    assert {item["name"] for item in payload} == set(dimension_names())
    assert all(item["purpose"] and item["sources_sought"] for item in payload)


def test_all_seven_dimension_subcommands_run_from_a_plain_checkout(
    tmp_path: Path,
) -> None:
    target = _target(tmp_path / "target")

    for name in dimension_names():
        completed = _run(
            name,
            "--repo",
            str(target),
            "--scope",
            "project",
            "--budget-bytes",
            "120000",
        )
        assert completed.returncode == 0, (name, completed.stderr)
        assert json.loads(completed.stdout)["dimension"] == name


def test_cli_dimension_payload_matches_mcp_payload(tmp_path: Path) -> None:
    target = _target(tmp_path / "target")
    completed = _run("architecture", "--repo", str(target), "--scope", "project")

    _content, mcp_payload = asyncio.run(
        mcp_server.mcp.call_tool(
            "architecture", {"repo": str(target), "scope": "project"}
        )
    )

    assert completed.returncode == 0
    assert json.loads(completed.stdout) == mcp_payload


def test_combined_accepts_aliases_for_task_and_range(tmp_path: Path) -> None:
    target = _target(tmp_path / "target")
    completed = _run(
        "combined",
        "--repo",
        str(target),
        "--dimensions",
        "security,architecture",
        "--task",
        "T015",
        "--range",
        "HEAD~1..HEAD",
    )

    assert completed.returncode == 0
    assert [slot["dimension"] for slot in json.loads(completed.stdout)["slots"]] == [
        "architecture",
        "security",
    ]


def test_write_report_file_and_stdin_take_the_same_path(tmp_path: Path) -> None:
    file_target = _target(tmp_path / "file-target")
    stdin_target = _target(tmp_path / "stdin-target")
    findings_file = tmp_path / "findings.json"
    findings_file.write_text("[]", encoding="utf-8")

    base = [sys.executable, "-c", FROZEN_REPORT_RUNNER, "write-report"]
    from_file = subprocess.run(
        [*base, "--repo", str(file_target), "--findings", str(findings_file)],
        capture_output=True,
        text=True,
        env=_env(),
        check=False,
    )
    from_stdin = subprocess.run(
        [*base, "--repo", str(stdin_target)],
        input="[]",
        capture_output=True,
        text=True,
        env=_env(),
        check=False,
    )

    assert from_file.returncode == from_stdin.returncode == 0
    assert from_file.stdout == from_stdin.stdout
    result = json.loads(from_file.stdout)
    assert set(result) == {"path", "advisory"}
    assert (file_target / result["path"]).is_file()
    assert (stdin_target / result["path"]).is_file()


def test_findings_file_takes_precedence_over_piped_stdin(tmp_path: Path) -> None:
    target = _target(tmp_path / "target")
    findings_file = tmp_path / "findings.json"
    findings_file.write_text("[]", encoding="utf-8")

    completed = _run(
        "write-report",
        "--repo",
        str(target),
        "--findings",
        str(findings_file),
        input_text="not json",
    )

    assert completed.returncode == 0
    assert json.loads(completed.stdout)["path"].startswith("reports/")


def test_validation_and_operational_failures_have_distinct_exit_codes(
    tmp_path: Path,
) -> None:
    target = _target(tmp_path / "target")
    invalid = json.dumps(
        [
            {
                "dimension": "architecture",
                "title": "Missing confidence",
                "detail": "Rejected",
                "evidence_ref": "README.md:1-1",
            }
        ]
    )

    validation = _run("write-report", "--repo", str(target), input_text=invalid)
    operational = _run("architecture", "--repo", str(tmp_path / "missing"))

    assert validation.returncode == 2
    assert operational.returncode == 3
    assert validation.stdout == operational.stdout == ""
    assert "confidence" in validation.stderr
    assert "does not exist" in operational.stderr
    assert not (target / "reports").exists()


def test_malformed_and_empty_findings_are_clear_validation_errors(
    tmp_path: Path,
) -> None:
    target = _target(tmp_path / "target")

    malformed = _run("write-report", "--repo", str(target), input_text="{")
    empty = _run("write-report", "--repo", str(target), input_text="")

    assert malformed.returncode == empty.returncode == 2
    assert "malformed JSON" in malformed.stderr
    assert "malformed JSON" in empty.stderr
    assert malformed.stdout == empty.stdout == ""


def test_adapter_is_structurally_thin() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    source = MODULE_PATH.read_text(encoding="utf-8")

    assert "coverage_score" not in source
    assert "Excerpt(" not in source
    assert "render" not in source.lower()
    file_reads = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in {"read_text", "read_bytes"}
    ]
    assert len(file_reads) <= 1
