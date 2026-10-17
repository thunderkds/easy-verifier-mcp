"""T071 (FR-066): the evaluation guide, README pointer and SCORING_FLOW guidance.

Docs-only checks: required sections and links exist, every code name the guide
backticks is declared here and found in ``src/``, numeric examples are sourced
or marked illustrative, and no marketing wording slips in.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "docs" / "EVALUATION_GUIDE.md"
README = ROOT / "README.md"
FLOW = ROOT / "docs" / "SCORING_FLOW.md"
SRC = ROOT / "src"

GUIDE_SECTIONS = (
    "What you received",
    "The overall number",
    "When to trust a number",
    "Warnings: what could not be measured",
    "Large repositories: batches",
    "Improvement plan",
    "Engine text and agent text",
    "The report, top to bottom",
    "Act on it",
    "Worked examples",
)

# Every identifier-shaped backticked token in the guide, mapped to the text
# that must occur in src/ (a word-boundary match unless the needle has quotes).
DECLARED = {
    # T114: the blast-radius rule groups named in the scope bullet.
    "max_fan_in_changed": '"max_fan_in_changed"',
    "changed_files_in_churn_hotspots_share": '"changed_files_in_churn_hotspots_share"',
    "public_symbols_removed": '"public_symbols_removed"',
    "destructive_migration_ops": '"destructive_migration_ops"',
    "high_reach_files_without_test_share": '"high_reach_files_without_test_share"',
    "high_reach_churn_hotspot_share": '"high_reach_churn_hotspot_share"',
    "score": "score",
    "write_report": "write_report",
    "ratings": "ratings",
    "overall": "overall",
    "value": "value",
    "contributors": "contributors",
    "rated_by": "rated_by",
    "abstentions": "abstentions",
    "disclosure": "disclosure",
    "reason_code": "reason_code",
    "warnings": "warnings",
    "areas_measured": '"areas_measured"',
    "areas_without_rule": '"areas_without_rule"',
    "samples": "samples",
    "excluded": '"excluded"',
    "linguist-pattern": '"linguist-pattern"',
    "gitattributes": '"gitattributes"',
    "declared": '"declared"',
    "nested-project": '"nested-project"',
    "improvement_plan": "improvement_plan",
    "assessments": "assessments",
    "divergences": "divergences",
    "needs_input": "needs_input",
    "picks": "picks",
    "gate_evaluations": "gate_evaluations",
    "reference": "reference",
    "review": "review",
    "continue_batches": "continue_batches",
    "rules": '"rules"',
    "agent-rated": '"agent-rated"',
    "COVERAGE_FLOORS": "COVERAGE_FLOORS",
    "healthcare": '"healthcare"',
    "finance": '"finance"',
    "frontend-a11y": '"frontend-a11y"',
    "below_coverage_floor": '"below_coverage_floor"',
    "MEASURED_WEIGHT_FLOOR": "MEASURED_WEIGHT_FLOOR",
    "insufficient_measured_weight": '"insufficient_measured_weight"',
    "no_static_rule": '"no_static_rule"',
    "BORDERLINE_BAND": "BORDERLINE_BAND",
    "EVIDENCE_LACK_REASONS": "EVIDENCE_LACK_REASONS",
    "coverage_not_applicable": '"coverage_not_applicable"',
    "all_metrics_abstained": '"all_metrics_abstained"',
    "dimension_failed": '"dimension_failed"',
    "unmeasured_rules": '"unmeasured_rules"',
    "sources_missing": '"sources_missing"',
    "measured_share": '"measured_share"',
    "project": '"project"',
    "--scope": '"--scope"',
    "--batches": '"--batches"',
    "--all": '"--all"',
    "agent_input": "agent_input",
    "needs_input.continue_batches": "needs_input.continue_batches",
    "batches_done": '"batches_done"',
    "batches_total": '"batches_total"',
    "files_read": '"files_read"',
    "files_in_scope": '"files_in_scope"',
    "overall_gain": '"overall_gain"',
    "dimension_gain": '"dimension_gain"',
    "gain_basis": '"gain_basis"',
    "abstained": '"abstained"',
    "unmeasured": '"unmeasured"',
    "fix.source": '"source": "engine"',
    "engine": '"engine"',
    "agent": 'fix-source-agent">agent<',
    "summary": '"summary"',
    "improvements": '"improvements"',
    "redaction_hits_observed": '"redaction_hits_observed"',
    "max_function_ccn": '"max_function_ccn"',
    "architecture_description_missing": '"architecture_description_missing"',
    "decision_records_missing": '"decision_records_missing"',
    "requirements_doc_missing": '"requirements_doc_missing"',
    "routes_without_test_share": '"routes_without_test_share"',
    "commits_with_issue_reference_share": '"commits_with_issue_reference_share"',
    "requirement_items_traced_share": '"requirement_items_traced_share"',
    "source_files_without_covering_test_share": (
        '"source_files_without_covering_test_share"'
    ),
}

_IDENTIFIER = re.compile(r"^(--)?[A-Za-z_][A-Za-z0-9_.-]*$")
_MARKETING = (
    "powerful",
    "seamless",
    "robust",
    "cutting-edge",
    "best-in-class",
    "state-of-the-art",
    "effortless",
    "intelligent",
    "smart",
    "revolutionary",
    "world-class",
    "blazing",
    "comprehensive",
    "unparalleled",
)


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _src_text() -> str:
    return "\n".join(_text(p) for p in sorted(SRC.rglob("*.py")))


def _section(text: str, heading: str) -> str:
    """Body of a ``## heading`` section, up to the next ``## `` heading."""
    match = re.search(rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    assert match, f"missing section: ## {heading}"
    return match.group(1)


def _identifiers(text: str) -> set[str]:
    found = set()
    for span in re.findall(r"`([^`\n]+)`", text):
        token = span.split()[0] if span.startswith("--") else span
        if "/" in token or token.endswith((".py", ".md")):
            continue
        if _IDENTIFIER.match(token):
            found.add(token)
    return found


def _slug(heading: str) -> str:
    slug = re.sub(r"[^\w\- ]", "", heading.strip().lower())
    return slug.replace(" ", "-")


@pytest.mark.parametrize("heading", GUIDE_SECTIONS)
def test_guide_has_every_required_section(heading: str) -> None:
    assert _section(_text(GUIDE), heading).strip()


def test_guide_covers_acceptance_topics() -> None:
    guide = _text(GUIDE)
    for phrase in (
        "mean of the dimensions",
        "abstention can raise the overall",
        "50%",
        "sample: batches",
        "agent-rated",
        "continue_batches",
        "P0",
        "P1",
        "P2",
        "recomputed",
        "[if it fails, if it passes]",
        "gain_basis",
        "labelled `agent`",
    ):
        assert phrase in guide, phrase


def test_every_backticked_identifier_is_declared() -> None:
    undeclared = _identifiers(_text(GUIDE)) - set(DECLARED)
    assert not undeclared, f"declare these in DECLARED: {sorted(undeclared)}"


@pytest.mark.parametrize("name", sorted(DECLARED))
def test_declared_identifier_appears_in_guide_and_exists_in_src(name: str) -> None:
    assert name in _identifiers(_text(GUIDE)), f"{name} not backticked in the guide"
    needle = DECLARED[name]
    src = _src_text()
    if '"' in needle or "<" in needle:
        assert needle in src, f"{needle!r} not found in src/"
    else:
        assert re.search(rf"\b{re.escape(needle)}\b", src), f"{needle} not in src/"


def test_guide_relative_links_resolve() -> None:
    guide = _text(GUIDE)
    links = re.findall(r"\]\(([^)\s]+)\)", guide)
    assert links
    for link in links:
        target, _, anchor = link.partition("#")
        path = GUIDE.parent / target if target else GUIDE
        assert path.is_file(), link
        if anchor:
            headings = re.findall(r"^#+ (.+)$", _text(path), re.M)
            assert anchor in {_slug(h) for h in headings}, link


def test_numeric_examples_are_sourced_or_illustrative() -> None:
    guide = _text(GUIDE)
    examples = _section(guide, "Worked examples")
    assert "2026-10-05" in examples and "`score`" in examples
    assert "nest-api" in examples and "node-monorepo" in examples
    assert "false positives" in examples
    assert "74 = rules 68 + agent 88 (w 0.30)` (illustrative)" in guide


def test_no_marketing_and_no_quality_judgment_claim() -> None:
    for path in (GUIDE, README, FLOW):
        lowered = _text(path).lower()
        for word in _MARKETING:
            assert not re.search(rf"\b{re.escape(word)}\b", lowered), (path.name, word)
    guide = _text(GUIDE).lower()
    assert "does not judge quality" in guide
    assert not re.search(r"(?<!not )\bjudges (the )?quality", guide)


def test_readme_reading_a_report_section_is_short_and_links_the_guide() -> None:
    body = _section(_text(README), "Reading a report")
    assert len(body.strip().splitlines()) <= 25
    assert "](docs/EVALUATION_GUIDE.md)" in body


@pytest.mark.parametrize("heading", ["Evidence warnings", "Improvement plan"])
def test_scoring_flow_sections_link_the_guide(heading: str) -> None:
    body = _section(_text(FLOW), heading)
    assert "](EVALUATION_GUIDE.md#" in body
