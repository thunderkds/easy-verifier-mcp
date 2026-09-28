"""T027 — MCP detect gate: `needs_input.picks` candidates for unfilled roles.

Every acceptance criterion in ``tasks/TASK_GUIDE_T027.md`` has at least one
test here, plus the Stage 4 regressions: symlink containment (P1), grouped
candidates (P2), and the CLI never paying for the detect walk (P2).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import easy_verifier.core.score as score_module
from easy_verifier.core.gate import MAX_CANDIDATES_PER_ROLE, detect_pick_gates
from easy_verifier.core.score import score_repository


def _write(root: Path, files: dict[str, str]) -> Path:
    for relative, text in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


def _group_with_role(gates: dict, role_name: str) -> dict:
    """The one group in ``gates["groups"]`` whose ``roles`` names ``role_name``."""
    matches = [g for g in gates["groups"] if role_name in g["roles"]]
    assert len(matches) == 1, gates
    return matches[0]


# ---------------------------------------------------------------------------
# core: detect_pick_gates
# ---------------------------------------------------------------------------


def test_unfilled_role_with_unmatched_doc_is_offered_as_a_candidate(
    tmp_path: Path,
) -> None:
    repo = _write(
        tmp_path,
        {"notes/product-brief.md": "# Product Brief\n\nSome prose.\n"},
    )
    gates = detect_pick_gates(repo)
    assert gates is not None
    group = _group_with_role(gates, "requirements-doc")
    assert {"path": "notes/product-brief.md", "heading": "Product Brief"} in group[
        "candidates"
    ]
    assert group["omitted"] == 0


def test_fully_resolved_repo_yields_no_needs_input(tmp_path: Path) -> None:
    repo = _write(
        tmp_path,
        {
            "README.md": "# Readme\n",
            "PROJECT_SPEC.md": "# Spec\n",
            "docs/adr/0001.md": "# ADR\n",
            "PRD.md": "# PRD\n",
            "docs/spec/spec.md": "# Spec doc\n",
            "tasks/TASK_GUIDE_T001.md": "# Task\n",
            "CONTRIBUTING.md": "# Contributing\n",
        },
    )
    result = score_repository(repo, detect_gates=True)
    assert result.needs_input is None
    assert "needs_input" not in result.to_dict()


def test_candidate_heading_is_redacted(tmp_path: Path) -> None:
    fake_key = "sk_live_" + "A" * 32
    repo = _write(
        tmp_path,
        {"notes/brief.md": f"secret={fake_key}\nrest of the file\n"},
    )
    gates = detect_pick_gates(repo)
    assert gates is not None
    group = _group_with_role(gates, "requirements-doc")
    heading = group["candidates"][0]["heading"]
    assert fake_key not in heading
    assert "REDACTED" in heading or "***" in heading or len(heading) < len(fake_key)


def test_overflow_is_disclosed_as_a_count(tmp_path: Path) -> None:
    files = {f"notes/brief-{i:02d}.md": f"# Brief {i}\n" for i in range(30)}
    repo = _write(tmp_path, files)
    gates = detect_pick_gates(repo)
    assert gates is not None
    group = _group_with_role(gates, "requirements-doc")
    assert len(group["candidates"]) == MAX_CANDIDATES_PER_ROLE
    assert group["omitted"] == 10


def test_candidates_exclude_files_already_filling_a_role(tmp_path: Path) -> None:
    repo = _write(
        tmp_path,
        {
            "README.md": "# Readme\n",  # fills 'readme'
            "notes/other.md": "# Other note\n",
        },
    )
    gates = detect_pick_gates(repo)
    assert gates is not None
    for group in gates["groups"]:
        paths = {item["path"] for item in group["candidates"]}
        assert "README.md" not in paths


def test_candidates_exclude_vendor_secret_and_binary(tmp_path: Path) -> None:
    repo = _write(
        tmp_path,
        {
            "node_modules/pkg/brief.md": "# Vendored\n",
            ".env": "SECRET=1\n",
        },
    )
    (repo / "notes").mkdir()
    (repo / "notes/image.png").write_bytes(b"\x89PNG\x00\x00fake")
    gates = detect_pick_gates(repo)
    assert gates is None  # nothing eligible: vendor/secret/binary all excluded


def test_no_needs_input_when_no_candidate_exists(tmp_path: Path) -> None:
    repo = _write(tmp_path, {"main.py": "print('hi')\n"})
    gates = detect_pick_gates(repo)
    assert gates is None


def test_candidates_are_grouped_by_shape_not_repeated_per_role(tmp_path: Path) -> None:
    """P2 (token cost): one candidate is listed once per bucket, not once per
    unfilled role that shares its shape."""
    repo = _write(tmp_path, {"notes/product-brief.md": "# Product Brief\n"})
    gates = detect_pick_gates(repo)
    assert gates is not None
    doc_group = _group_with_role(gates, "requirements-doc")
    assert set(doc_group["roles"]) >= {
        "requirements-doc",
        "spec-doc",
        "readme",
        "decision-record",
        "task-breakdown",
        "contributing-guide",
        "architecture-doc",
    }
    # Exactly one group carries every doc-shaped unfilled role; the candidate
    # itself appears exactly once inside it, never duplicated per role.
    assert doc_group["candidates"].count(
        {"path": "notes/product-brief.md", "heading": "Product Brief"}
    ) == 1


# ---------------------------------------------------------------------------
# P1 (security): symlink containment
# ---------------------------------------------------------------------------


def test_escaping_symlink_is_never_a_candidate_and_never_read(tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    secret_file = outside / "private.md"
    secret_file.write_text(
        "# HOST-ONLY SECRET PLAN codename bluebird\n", encoding="utf-8"
    )

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "notes").mkdir()
    try:
        os.symlink(secret_file, repo / "notes" / "brief.md")
    except OSError:
        return  # symlinks unsupported on this filesystem; nothing to prove

    result = score_repository(repo, detect_gates=True)
    payload_text = str(result.needs_input)
    assert "bluebird" not in payload_text
    assert "HOST-ONLY" not in payload_text
    if result.needs_input is not None:
        for group in result.needs_input["groups"]:
            assert "notes/brief.md" not in {c["path"] for c in group["candidates"]}


def test_in_repo_symlink_to_a_secret_bearing_file_is_never_a_candidate(
    tmp_path: Path,
) -> None:
    repo = _write(tmp_path, {".env": "SECRET=1\n"})
    (repo / "notes").mkdir()
    try:
        os.symlink(repo / ".env", repo / "notes" / "brief.md")
    except OSError:
        return

    gates = detect_pick_gates(repo)
    if gates is not None:
        for group in gates["groups"]:
            assert "notes/brief.md" not in {c["path"] for c in group["candidates"]}


# ---------------------------------------------------------------------------
# score_repository: round trip + suppression
# ---------------------------------------------------------------------------


def test_agent_input_suppresses_the_detect_gate(tmp_path: Path) -> None:
    repo = _write(tmp_path, {"notes/product-brief.md": "# Brief\n"})
    result = score_repository(
        repo, agent_input={"picks": {}}, detect_gates=True
    )
    assert result.needs_input is None


def test_picks_round_trip_raises_coverage_and_shows_provenance(tmp_path: Path) -> None:
    repo = _write(tmp_path, {"notes/product-brief.md": "# Brief\n"})
    before = score_repository(repo, detect_gates=True)
    assert before.needs_input is not None
    group = _group_with_role(before.needs_input, "requirements-doc")
    assert "notes/product-brief.md" in [c["path"] for c in group["candidates"]]

    after = score_repository(
        repo,
        agent_input={"picks": {"requirements-doc": ["notes/product-brief.md"]}},
        detect_gates=True,
    )
    provenance = dict(after.provenance)
    assert "agent picks (1 file)" in provenance["requirement-fidelity"]
    assert after.needs_input is None


# ---------------------------------------------------------------------------
# P2 (wasted work): detect_gates defaults to False; the CLI never asks
# ---------------------------------------------------------------------------


def test_detect_gates_defaults_to_false_and_skips_the_walk(
    tmp_path: Path, monkeypatch
) -> None:
    repo = _write(tmp_path, {"notes/product-brief.md": "# Brief\n"})

    def _fail(*_args, **_kwargs):
        raise AssertionError("detect_pick_gates must not run when detect_gates=False")

    monkeypatch.setattr(score_module, "detect_pick_gates", _fail)
    result = score_repository(repo)  # detect_gates defaults to False
    assert result.needs_input is None


class _NoStdin:
    """A stdin stand-in that looks like a TTY, so the CLI's `score` command
    never tries to block on `sys.stdin.buffer.read()` under pytest's own
    stdin capture (findings are optional there; see `_read_findings`)."""

    def isatty(self) -> bool:
        return True


def test_cli_score_never_calls_detect_pick_gates(
    tmp_path: Path, monkeypatch
) -> None:
    repo = _write(tmp_path, {"notes/product-brief.md": "# Brief\n"})

    def _fail(*_args, **_kwargs):
        raise AssertionError("CLI score must never call detect_pick_gates")

    monkeypatch.setattr(score_module, "detect_pick_gates", _fail)
    monkeypatch.setattr(sys, "stdin", _NoStdin())
    from easy_verifier.adapters import cli

    exit_code = cli.main(["score", "--repo", str(repo)])
    assert exit_code == 0


def test_cli_score_never_emits_needs_input(tmp_path: Path) -> None:
    repo = _write(tmp_path, {"notes/product-brief.md": "# Brief\n"})
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "easy_verifier.adapters.cli",
            "score",
            "--repo",
            str(repo),
        ],
        capture_output=True,
        text=True,
        cwd=Path(__file__).resolve().parents[1] / "src",
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "needs_input" not in completed.stdout


# ---------------------------------------------------------------------------
# MCP tool description (AC9)
# ---------------------------------------------------------------------------


def test_score_tool_description_mentions_needs_input() -> None:
    from easy_verifier.adapters import mcp_server

    tools = mcp_server.mcp._tool_manager.list_tools()
    tool = next(t for t in tools if t.name == "score")
    assert "needs_input" in tool.description
