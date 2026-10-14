"""T080: the evaluation guide matches DDR-0011 (T074-T077) code-derived rules.

Pins the three corrections so the stale claims cannot return: requirement-fidelity
code rules are measured (each abstains only on its own empty input), a missing
document is a failed rule rather than a warning, and the worked examples are the
2026-10-05 re-run numbers.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "docs" / "EVALUATION_GUIDE.md"


def _guide() -> str:
    return GUIDE.read_text(encoding="utf-8")


def _section(text: str, heading: str) -> str:
    match = re.search(rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    assert match, f"missing section: ## {heading}"
    return match.group(1)


def test_guide_no_longer_says_traceability_always_abstains() -> None:
    guide = _guide()
    assert "always\n  abstain" not in guide and "always abstain" not in guide
    warnings = _section(guide, "Warnings: what could not be measured")
    for rule, condition in (
        ("`routes_without_test_share`", "no route"),
        ("`commits_with_issue_reference_share`", "below 20 commits"),
        ("`requirement_items_traced_share`", "no\n  requirement item"),
    ):
        assert rule in warnings, rule
        assert condition in warnings, condition


def test_missing_document_is_a_failed_rule_not_a_warning() -> None:
    trust = _section(_guide(), "When to trust a number")
    assert "documents 20\n   and code 80" in trust
    assert "fails its rule" in trust and "It is not a warning" in trust
    assert "improvement plan" in trust
    for rule in (
        "`architecture_description_missing`",
        "`decision_records_missing`",
        "`requirements_doc_missing`",
    ):
        assert rule in trust, rule


def test_worked_examples_are_the_2026_10_05_rerun() -> None:
    examples = _section(_guide(), "Worked examples")
    assert "2026-10-05" in examples and "`7d64f08`" in examples
    nest_api, monorepo = examples.split("**node-monorepo**")
    assert "overall 65; 4 of 7" in nest_api
    nest_api_parts = (
        "architecture 80",
        "code-quality 71",
        "requirement-fidelity 50",
        "security 59",
    )
    for part in nest_api_parts:
        assert part in nest_api, part
    assert "overall 69; 4 of 7" in monorepo
    monorepo_parts = (
        "architecture 83",
        "code-quality 67",
        "test-strategy 75",
        "security\n50",
    )
    for part in monorepo_parts:
        assert part in monorepo, part
    assert "coverage floor" in monorepo
    # stale 2026-10-04 claims
    assert "2 of 7 dimensions rated (code-quality 71, security 59)" not in examples
    assert "architecture 70" not in examples
