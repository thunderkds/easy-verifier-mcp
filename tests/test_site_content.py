"""T115 drift + safety test for site/index.html (scope: PROJECT_SPEC_SITE.md).

Every engine fact on the page is asserted against its source of truth at test
time: DIMENSIONS, judge.AREAS and the rule tables, the docs the commands come
from, and the committed sample snapshot. Adding a dimension, an area or a rule
without updating the page must fail this suite.
"""

from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

from easy_verifier.core import judge, redact
from easy_verifier.dimensions import DIMENSIONS

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
PAGE = SITE / "index.html"
SNAPSHOT = SITE / "sample-score.json"
SECTION_IDS = ("what", "run", "dimensions", "areas", "scoring", "sample")
_VOID = {"meta", "link", "br", "img", "hr", "input"}
# README's own placeholder, shown verbatim in #run; the only host-path text allowed.
_PLACEHOLDER = "/home/you/code"


class Element:
    def __init__(self, tag: str, attrs: dict[str, str | None], section: str | None):
        self.tag, self.attrs, self.section = tag, attrs, section
        self.parts: list[str] = []

    @property
    def text(self) -> str:
        return "".join(self.parts)


class _Parser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.elements: list[Element] = []
        self.stack: list[Element] = []
        self.section: str | None = None
        self.section_depth = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "section" and attrs.get("id"):
            self.section = attrs["id"]
            self.section_depth = len(self.stack)
        el = Element(tag, attrs, self.section)
        self.elements.append(el)
        if tag not in _VOID:
            self.stack.append(el)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                break
        if tag == "section" and len(self.stack) == self.section_depth:
            self.section = None

    def handle_data(self, data):
        for el in self.stack:
            el.parts.append(data)


def _page() -> _Parser:
    parser = _Parser()
    parser.feed(PAGE.read_text(encoding="utf-8"))
    return parser


def _in(parser: _Parser, section: str, tag: str | None = None, attr: str | None = None):
    return [
        e
        for e in parser.elements
        if e.section == section
        and (tag is None or e.tag == tag)
        and (attr is None or attr in e.attrs)
    ]


def _snapshot() -> dict:
    return json.loads(SNAPSHOT.read_text(encoding="utf-8"))


def _norm(text: str) -> str:
    return " ".join(text.split())


# ---- checks (functions, so the negative tests can run them under a patch) ----


def check_dimensions(parser: _Parser) -> None:
    shown = {
        e.attrs["data-dimension"]
        for e in _in(parser, "dimensions", "tr", "data-dimension")
    }
    expected = set(DIMENSIONS)
    assert not expected - shown, (
        f"dimension(s) missing from #dimensions: {sorted(expected - shown)}"
    )
    assert not shown - expected, (
        f"unknown dimension(s) in #dimensions: {sorted(shown - expected)}"
    )
    codes = {e.text for e in _in(parser, "dimensions", "code")}
    assert shown <= codes, (
        f"dimension rows without a <code> name: {sorted(shown - codes)}"
    )


def expected_status(area: str) -> str:
    core = {
        d
        for d in (*judge.RATING_RULES, *judge.DOCUMENTATION_RULES)
        if d not in judge.PACK_FLOORS
    }
    in_dim = {
        d
        for d, rules in judge.RATING_RULES.items()
        if any(r.area == area for r in rules.values())
    } | {
        d
        for d, rules in judge.DOCUMENTATION_RULES.items()
        if any(r.area == area for r in rules)
    }
    if in_dim & core:
        return "ruled"
    packs = sorted(in_dim & set(judge.PACK_FLOORS))
    return f"pack:{packs[0]}" if packs else "none"


def check_areas(parser: _Parser) -> None:
    rows = _in(parser, "areas", "tr", "data-area")
    shown = [r.attrs["data-area"] for r in rows]
    assert shown == list(judge.AREAS), (
        "#areas differs from judge.AREAS; "
        f"missing={[a for a in judge.AREAS if a not in shown]} "
        f"extra={[a for a in shown if a not in judge.AREAS]}"
    )
    for row in rows:
        area = row.attrs["data-area"]
        assert _norm(area) in _norm(row.text), f"row text does not carry area {area!r}"
        assert row.attrs.get("data-status") == expected_status(area), (
            f"{area!r}: page says {row.attrs.get('data-status')!r}, "
            f"rules say {expected_status(area)!r}"
        )


# ---- AC 1, 2 ----


def test_page_is_standalone_html():
    text = PAGE.read_text(encoding="utf-8")
    assert text.lstrip().lower().startswith("<!doctype html>")
    assert re.search(r"<title>[^<]+</title>", text)
    assert re.search(r"<meta\s+charset=", text, re.I)
    assert re.search(r'<meta\s+name="viewport"', text, re.I)
    assert not re.search(r"<script\b[^>]*\bsrc=", text, re.I)
    assert not re.search(r"@import|@font-face|fonts\.googleapis", text, re.I)
    for url in re.findall(r"""(?:src|href)\s*=\s*["'](https?:[^"']+)""", text, re.I):
        assert url.startswith(
            "https://github.com/thunderkds/easy-verifier-mcp"
        ) or _is_citation(url), f"external resource not allowed: {url}"
    for url in re.findall(r"""(?:src|href)\s*=\s*["'](//[^"']+)""", text, re.I):
        pytest.fail(f"protocol-relative external resource: {url}")


def _is_citation(url: str) -> bool:
    """A cited standard already in the registry (judge's rule citations)."""
    cited = set()
    for rules in judge.RATING_RULES.values():
        for rule in rules.values():
            for c in (
                *_as_list(rule.metric_citation),
                *_as_list(rule.threshold_citation),
            ):
                cited.add(c.url)
    return url in cited


def _as_list(value):
    if value is None:
        return []
    return list(value) if isinstance(value, (list, tuple)) else [value]


def test_sections_present():
    ids = {
        e.attrs["id"]
        for e in _page().elements
        if e.tag == "section" and "id" in e.attrs
    }
    assert set(SECTION_IDS) <= ids, (
        f"missing sections: {sorted(set(SECTION_IDS) - ids)}"
    )


# ---- AC 3, 4 ----


def test_dimensions_match_registry():
    check_dimensions(_page())


def test_change_risk_scope_stated():
    text = " ".join(
        e.text
        for e in _in(_page(), "dimensions", "tr", "data-dimension")
        if e.attrs["data-dimension"] == "change-risk"
    )
    assert "changes" in text and "worktree" in text


def test_areas_match_judge_and_status():
    check_areas(_page())


def test_status_counts_today():
    statuses = [expected_status(a) for a in judge.AREAS]
    assert len(statuses) == 32
    assert statuses.count("ruled") == 27
    assert statuses.count("none") == 1
    assert statuses.count("pack:finance") == 1
    assert statuses.count("pack:healthcare") == 2
    assert statuses.count("pack:frontend-a11y") == 1


# ---- AC 5 ----


def test_run_commands_verbatim_from_docs():
    docs = "\n".join(
        (ROOT / p).read_text(encoding="utf-8")
        for p in ("README.md", "docs/DOCKER_MCP_GUIDE.md", "docs/LOCAL_MCP_GUIDE.md")
    )
    blocks = [e for e in _in(_page(), "run") if e.tag in ("pre", "code")]
    assert blocks, "#run shows no command"
    for block in blocks:
        assert "temvar/" not in block.text and "hub.docker" not in block.text
        for raw in block.text.splitlines():
            line = raw.strip()
            if line:
                assert line in docs, f"command not in README/docs: {line!r}"
    assert "temvar/" not in PAGE.read_text(encoding="utf-8")


# ---- AC 6 ----


def test_snapshot_shape_and_no_extras():
    snap = _snapshot()
    assert set(snap) == {
        "commit",
        "date",
        "scope",
        "overall",
        "ratings",
        "areas_measured",
        "areas_without_rule",
    }
    assert snap["scope"] == "project"
    for r in snap["ratings"]:
        assert set(r) in ({"dimension", "value"}, {"dimension", "reason_code"})
        assert r["dimension"] in DIMENSIONS


def test_sample_matches_snapshot():
    snap, parser = _snapshot(), _page()
    overall = _in(parser, "sample", None, "data-overall")
    assert len(overall) == 1 and overall[0].attrs["data-overall"] == str(
        snap["overall"]
    )
    assert _norm(overall[0].text).startswith(str(snap["overall"]))
    commit = _in(parser, "sample", None, "data-commit")
    assert commit and commit[0].text.strip() == snap["commit"]
    date = _in(parser, "sample", None, "data-date")
    assert date and date[0].text.strip() == snap["date"]
    rows = {
        r.attrs["data-sample-dimension"]: r
        for r in _in(parser, "sample", "tr", "data-sample-dimension")
    }
    assert set(rows) == {r["dimension"] for r in snap["ratings"]}
    for r in snap["ratings"]:
        row = rows[r["dimension"]]
        if "value" in r:
            assert row.attrs.get("data-value") == str(r["value"])
        else:
            assert row.attrs.get("data-reason") == r["reason_code"]
            assert r["reason_code"] in row.text
    measured = _in(parser, "sample", None, "data-areas-measured")
    assert measured and measured[0].attrs["data-areas-measured"] == str(
        len(snap["areas_measured"])
    )
    shown = [
        e.text.strip() for e in _in(parser, "sample", "li", "data-area-without-rule")
    ]
    assert shown == snap["areas_without_rule"]


# ---- AC 7 ----


def test_scoring_section_states_required_facts():
    text = " ".join(
        _norm(e.text)
        for e in _in(_page(), "scoring", "p") + _in(_page(), "scoring", "li")
    ).lower()
    for phrase in (
        "declared rules",
        "measured",
        "coverage floor",
        "abstain",
        "improvement plan",
        "gain",
        "no model call",
        "no network",
    ):
        assert phrase in text, f"#scoring does not state {phrase!r}"


def test_dimension_count_pinned():
    marks = _in(_page(), "dimensions", "span", "data-dimension-count")
    assert len(marks) == 1
    assert marks[0].attrs["data-dimension-count"] == str(len(DIMENSIONS) - 1)
    assert marks[0].text.strip().lower() == "thirteen"


def test_scope_weight_claim_holds_in_engine():
    text = " ".join(_norm(e.text) for e in _in(_page(), "scoring", "li"))
    assert "rules that apply at one scope add up to 100" in text
    assert "solution-fit" in text and "no static rule" in text
    for dimension, rules in judge.RATING_RULES.items():
        if not rules:
            assert dimension == "solution-fit" or not rules
            continue
        groups = judge.SCOPE_RULE_GROUPS.get(dimension, (tuple(rules),))
        for group in groups:
            assert sum(rules[n].weight for n in group) == 100, dimension
    assert not judge.RATING_RULES.get("solution-fit")


# ---- AC 8 ----


def _site_files():
    return [p for p in SITE.rglob("*") if p.is_file()]


def test_site_files_are_publication_safe():
    files = _site_files()
    assert {p.name for p in files} >= {"index.html", "sample-score.json"}
    for path in files:
        text = path.read_text(encoding="utf-8").replace(_PLACEHOLDER, "")
        for bad in ("/home/", "/Users/", "/workspace"):
            assert bad not in text, f"{path.name} contains {bad!r}"
        assert not re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text), (
            f"{path.name} contains an email"
        )
        assert not redact.scan(text).hits, f"{path.name} matches a secret pattern"


# ---- AC 9: the drift test bites ----


def test_extra_area_makes_check_fail(monkeypatch):
    monkeypatch.setattr(judge, "AREAS", (*judge.AREAS, "Invented area"))
    with pytest.raises(AssertionError, match="Invented area"):
        check_areas(_page())


def test_extra_dimension_makes_check_fail(monkeypatch):
    patched = dict(DIMENSIONS)
    patched["invented-dimension"] = next(iter(DIMENSIONS.values()))
    monkeypatch.setitem(globals(), "DIMENSIONS", patched)
    with pytest.raises(AssertionError, match="invented-dimension"):
        check_dimensions(_page())


def test_wrong_status_makes_check_fail(monkeypatch):
    real = expected_status

    def flipped(area):
        return (
            "none" if real(area) == "ruled" and area == judge.AREAS[0] else real(area)
        )

    monkeypatch.setitem(globals(), "expected_status", flipped)
    with pytest.raises(AssertionError, match="rules say"):
        check_areas(_page())
