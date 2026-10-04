"""T072: docs/AREA_COVERAGE.md must agree with the code's area mapping.

Every row's rules must equal ``judge.RATING_RULES`` for that area, every
status must match whether the area has a rule, and the summary counts must
match the rows.
"""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path

from easy_verifier.core import judge

DOC = Path(__file__).resolve().parents[1] / "docs" / "AREA_COVERAGE.md"
_ROW = re.compile(
    r"\| (\d+) \| (.+?) \| (Covered|Partial|Not yet) \| (.*?) \| (.*?) \| (.*?) \|$"
)


def _rows() -> dict[int, dict[str, str]]:
    rows = {}
    for line in DOC.read_text(encoding="utf-8").splitlines():
        match = _ROW.match(line)
        if match:
            number, area, status, rules, planned, notes = match.groups()
            rows[int(number)] = {
                "area": area,
                "status": status,
                "rules": rules,
                "planned": planned,
                "notes": notes,
            }
    return rows


def _code_rules() -> dict[str, set[tuple[str, str]]]:
    found: dict[str, set[tuple[str, str]]] = defaultdict(set)
    for dimension, rules in judge.RATING_RULES.items():
        for name, rule in rules.items():
            found[rule.area].add((dimension, name))
    return found


def test_every_area_has_exactly_one_row_in_code_order() -> None:
    rows = _rows()
    assert sorted(rows) == list(range(1, len(judge.AREAS) + 1))
    for number, area in enumerate(judge.AREAS, start=1):
        assert rows[number]["area"] == area


def test_row_rules_equal_rating_rules_by_area() -> None:
    code = _code_rules()
    for number, row in _rows().items():
        listed = set(re.findall(r"`([a-z-]+)` · `([a-z0-9_]+)`", row["rules"]))
        assert listed == code[judge.AREAS[number - 1]], f"area {number}"


def test_status_matches_whether_the_area_has_a_rule() -> None:
    code = _code_rules()
    for number, row in _rows().items():
        has_rule = bool(code[judge.AREAS[number - 1]])
        assert (row["status"] != "Not yet") == has_rule, f"area {number}"


def test_not_yet_rows_name_a_planned_home_and_task() -> None:
    for number, row in _rows().items():
        if row["status"] == "Not yet":
            assert re.search(r"\(T0\d\d\)", row["planned"]), f"area {number}"


def test_summary_counts_match_rows() -> None:
    text = DOC.read_text(encoding="utf-8")
    statuses = [row["status"] for row in _rows().values()]
    for status in ("Covered", "Partial", "Not yet"):
        match = re.search(rf"\| {status} \| (\d+) \|", text)
        assert match and int(match.group(1)) == statuses.count(status), status


def test_documentation_checks_are_listed() -> None:
    rows = _rows()
    for dimension, rules in judge.DOCUMENTATION_RULES.items():
        for rule in rules:
            number = judge.AREAS.index(rule.area) + 1
            assert f"`{dimension}` documentation check" in rows[number]["rules"]
