"""Content pins for T103: the shared scoring container is the primary documented path.

Docs, spec and skill text only; no code changed. Each test pins one acceptance
criterion of tasks/TASK_GUIDE_T103.md by content. Historical rows (PRD issue #13,
the 2026-08-14 spec insight) are deliberately not pinned and not edited.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MARKER = "Amended 2026-10-15 (T103)"
SKILL = ROOT / ".claude" / "skills" / "verify" / "SKILL.md"


def _text(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def _prd_row(row_id: str) -> str:
    for line in _text("PRD.md").splitlines():
        if line.startswith(f"| {row_id} |"):
            return line
    raise AssertionError(f"PRD row {row_id} not found")


def _spec_line(prefix: str) -> str:
    for line in _text("PROJECT_SPEC.md").splitlines():
        if line.startswith(prefix):
            return line
    raise AssertionError(f"PROJECT_SPEC line {prefix!r} not found")


def test_ac1_fr019a_shared_container_primary_stdio_alternative():
    row = _prd_row("FR-019a")
    assert MARKER in row
    assert "required" not in row.lower()
    assert "primary" in row
    assert "FR-019b" in row and "DDR-0013" in row
    assert "alternative" in row
    assert "default" in row and "stdio" in row


def test_ac1_fr019b_loopback_rule_unchanged():
    row = _prd_row("FR-019b")
    assert "must never bind `0.0.0.0` or any routable address" in row
    assert "`127.0.0.1`" in row


@pytest.mark.parametrize("row_id", ["FR-017", "NFR-007", "NFR-013"])
def test_ac2_reports_dir_exception_named(row_id):
    row = _prd_row(row_id)
    assert MARKER in row
    assert "EASY_VERIFIER_REPORTS_DIR" in row
    assert "<that dir>/<repo name>/" in row


def test_ac2_nfr013_fully_read_only_in_shared_container():
    row = _prd_row("NFR-013")
    assert "fully read-only" in row
    assert "no writable `reports/`" in row


def test_ac2_nfr007_never_execute_unchanged():
    assert "must never execute code from the target repository" in _prd_row("NFR-007")


def test_ac2_nfr006_matches_ac1():
    row = _prd_row("NFR-006")
    assert MARKER in row
    assert "primary" in row and "shared" in row
    assert "required" not in row.lower()


def test_ac3_spec_deployment_target():
    line = _spec_line("- **Deployment target**")
    low = line.lower()
    assert "shared" in low and "primary" in low
    assert "stdio" in low and "alternative" in low
    assert "NFR-012" in line


def test_ac3_spec_constraint_5_reports_dir_exception():
    line = _spec_line("5. **Write nothing")
    assert "EASY_VERIFIER_REPORTS_DIR" in line
    assert "Never execute code from the target repo (NFR-007)" in line


def test_ac3_spec_constraint_6_matches_prd():
    line = _spec_line("6. ")
    assert "required" not in line.lower()
    assert "primary" in line and "alternative" in line
    assert "bind `127.0.0.1` only — never `0.0.0.0`" in line
    assert "FR-019b" in line and "NFR-012" in line


def test_ac3_spec_insight_row_dated_t103():
    lines = _text("PROJECT_SPEC.md").splitlines()
    rows = [ln for ln in lines if ln.startswith("| 2026-10-15 |")]
    assert any(ln.rstrip().endswith("| T103 |") for ln in rows)


def test_ac3_historical_insight_kept():
    text = _text("PROJECT_SPEC.md")
    assert "Transport corrected to stdio-first after user flagged" in text


def test_ac4_local_guide_streamable_http_before_legacy():
    text = _text("docs/LOCAL_MCP_GUIDE.md")
    section = text[text.index("## HTTP") : text.index("## Troubleshooting")]
    for needle in (
        "--transport streamable-http",
        "/mcp",
        "EASY_VERIFIER_PORT",
        "8766",
        "127.0.0.1",
        "no authentication",
        "any local process",
        "DOCKER_MCP_GUIDE.md",
    ):
        assert needle in section, needle
    legacy = section.index("easy-verifier-mcp --http\n")
    assert section.index("--transport streamable-http") < legacy


def test_ac4_local_guide_reports_line():
    text = _text("docs/LOCAL_MCP_GUIDE.md")
    assert "$EASY_VERIFIER_REPORTS_DIR/<repo name>/" in text
    assert "<repo>/reports/" in text


def test_ac5_verify_skill_shared_container_surface():
    if not SKILL.exists():
        pytest.skip(".claude/ is git-ignored; verify skill absent from this checkout")
    text = SKILL.read_text(encoding="utf-8")
    assert "Shared container (HTTP)" in text
    for needle in (
        "EASY_VERIFIER_WORKSPACE=",
        "docker compose up -d scorer",
        "http://127.0.0.1:8766/mcp",
        "docker compose down scorer",
        "EASY_VERIFIER_REPORTS_DIR",
    ):
        assert needle in text, needle


def test_ac6_release_guide_stdio_boundary_only_and_shared_checks():
    text = _text("docs/RELEASE_GUIDE.md")
    assert "stdio boundary only" in text
    assert "python -m pytest tests/test_t101_shared_container.py -q" in text
    assert "Shared container (HTTP)" in text
    assert text.index("stdio boundary only") < text.index("test_t101_shared_container")


def test_ac6_release_script_untouched_by_wording():
    assert "test_t101" not in _text("scripts/verify_release_gate.sh")


def test_ac7_no_doc_calls_stdio_required():
    pattern = re.compile(r"stdio[^|\n.]{0,40}required|required[^|\n.]{0,20}stdio", re.I)
    files = [
        "PRD.md",
        "PROJECT_SPEC.md",
        "docs/LOCAL_MCP_GUIDE.md",
        "docs/RELEASE_GUIDE.md",
    ]
    if SKILL.exists():
        files.append(str(SKILL.relative_to(ROOT)))
    for rel in files:
        for line in _text(rel).splitlines():
            if line.startswith("| 13 |"):  # PRD issue #13: historical, kept
                continue
            assert not pattern.search(line), f"{rel}: {line[:120]}"
