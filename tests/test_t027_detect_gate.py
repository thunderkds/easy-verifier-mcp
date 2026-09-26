"""T027 — MCP detect gate: `needs_input.picks` candidates for unfilled roles.

Every acceptance criterion in ``tasks/TASK_GUIDE_T027.md`` has at least one
test here.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from easy_verifier.core.gate import MAX_CANDIDATES_PER_ROLE, detect_pick_gates
from easy_verifier.core.score import score_repository


def _write(root: Path, files: dict[str, str]) -> Path:
    for relative, text in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


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
    assert "requirements-doc" in gates
    candidates = gates["requirements-doc"]["candidates"]
    assert {"path": "notes/product-brief.md", "heading": "Product Brief"} in candidates
    assert gates["requirements-doc"]["omitted"] == 0


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
    result = score_repository(repo)
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
    heading = gates["requirements-doc"]["candidates"][0]["heading"]
    assert fake_key not in heading
    assert "REDACTED" in heading or "***" in heading or len(heading) < len(fake_key)


def test_overflow_is_disclosed_as_a_count(tmp_path: Path) -> None:
    files = {f"notes/brief-{i:02d}.md": f"# Brief {i}\n" for i in range(30)}
    repo = _write(tmp_path, files)
    gates = detect_pick_gates(repo)
    assert gates is not None
    entry = gates["requirements-doc"]
    assert len(entry["candidates"]) == MAX_CANDIDATES_PER_ROLE
    assert entry["omitted"] == 10


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
    for entry in gates.values():
        paths = {item["path"] for item in entry["candidates"]}
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


# ---------------------------------------------------------------------------
# score_repository: round trip + suppression
# ---------------------------------------------------------------------------


def test_agent_input_suppresses_the_detect_gate(tmp_path: Path) -> None:
    repo = _write(tmp_path, {"notes/product-brief.md": "# Brief\n"})
    result = score_repository(repo, agent_input={"picks": {}})
    assert result.needs_input is None


def test_picks_round_trip_raises_coverage_and_shows_provenance(tmp_path: Path) -> None:
    repo = _write(tmp_path, {"notes/product-brief.md": "# Brief\n"})
    before = score_repository(repo)
    assert before.needs_input is not None
    assert "notes/product-brief.md" in [
        c["path"] for c in before.needs_input["requirements-doc"]["candidates"]
    ]

    after = score_repository(
        repo, agent_input={"picks": {"requirements-doc": ["notes/product-brief.md"]}}
    )
    provenance = dict(after.provenance)
    assert "agent picks (1 file)" in provenance["requirement-fidelity"]
    assert after.needs_input is None


# ---------------------------------------------------------------------------
# CLI never emits needs_input
# ---------------------------------------------------------------------------


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
