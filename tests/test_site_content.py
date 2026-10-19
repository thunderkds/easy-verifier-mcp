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


def _docs_text() -> str:
    return "\n".join(
        (ROOT / p).read_text(encoding="utf-8")
        for p in ("README.md", "docs/DOCKER_MCP_GUIDE.md", "docs/LOCAL_MCP_GUIDE.md")
    )


def _lines(text: str) -> str:
    """Block text with each line stripped, so docs indentation does not matter."""
    return "\n".join(line.strip() for line in text.strip().splitlines())


def test_run_commands_verbatim_from_docs():
    docs = _docs_text()
    blocks = [e for e in _in(_page(), "run") if e.tag in ("pre", "code")]
    assert blocks, "#run shows no command"
    for block in blocks:
        assert "hub.docker" not in block.text
        for raw in block.text.splitlines():
            line = raw.strip()
            if line:
                assert line in docs, f"command not in README/docs: {line!r}"


# ---- T119: name, favicon, quick start, scoring diagram, worked example ----


def _head_title() -> str:
    match = re.search(r"<title>([^<]+)</title>", PAGE.read_text(encoding="utf-8"))
    assert match
    return match.group(1)


def test_product_name_is_easy_verifier():
    parser = _page()
    assert _head_title().startswith("Easy Verifier")
    h1 = [e for e in parser.elements if e.tag == "h1"]
    assert len(h1) == 1 and _norm(h1[0].text) == "Easy Verifier"
    brand = [e for e in parser.elements if e.attrs.get("class") == "brand"]
    assert len(brand) == 1 and _norm(brand[0].text) == "Easy Verifier"
    # commands and identifiers keep the package spelling
    assert "claude mcp add --transport http easy-verifier " in PAGE.read_text(
        encoding="utf-8"
    )


def check_favicon_link(html: str) -> None:
    links = re.findall(r"<link\b[^>]*\brel=\"icon\"[^>]*>", html, re.I)
    assert len(links) == 1, "expected exactly one <link rel=icon>"
    assert 'href="favicon.svg"' in links[0], f"icon href must be local: {links[0]}"
    assert 'type="image/svg+xml"' in links[0]


def check_favicon_file(svg: str) -> None:
    assert len(svg.encode("utf-8")) <= 2048, "favicon over 2 KB"
    assert re.search(r"<svg\b[^>]*\bviewBox=", svg), "favicon has no viewBox"
    assert not re.search(r"<script|<image|<foreignObject", svg, re.I)
    assert not re.search(r"(?:href|src)\s*=|url\(\s*[\"']?(?!#)", svg, re.I), (
        "favicon references an external resource"
    )
    assert not re.search(r"https?://(?!www\.w3\.org/2000/svg)", svg)


def test_favicon_link_and_file():
    html = PAGE.read_text(encoding="utf-8")
    check_favicon_link(html)
    favicon = SITE / "favicon.svg"
    assert favicon.is_file()
    svg = favicon.read_text(encoding="utf-8")
    check_favicon_file(svg)
    assert "#0a0a12" in svg.lower() and "#00d4ff" in svg.lower()


def test_favicon_with_external_reference_fails():
    html = PAGE.read_text(encoding="utf-8")
    with pytest.raises(AssertionError):
        check_favicon_link(
            html.replace('href="favicon.svg"', 'href="https://example.com/i.svg"')
        )
    good = (SITE / "favicon.svg").read_text(encoding="utf-8")
    with pytest.raises(AssertionError):
        check_favicon_file(
            good.replace(
                "<svg", '<svg><image href="https://example.com/x.png"/><svg', 1
            )
        )
    with pytest.raises(AssertionError):
        check_favicon_file(
            good.replace("<svg", '<svg onload="x"><script>1</script>', 1)
        )
    with pytest.raises(AssertionError):
        check_favicon_file(good + " " * 2100)


QUICK_START = (
    ("1-pull", "Pull", ("docker pull temvar/easy-verifier-mcp:0.1.0",)),
    (
        "2-run",
        "Run",
        (
            "mkdir -p ~/.easy-verifier-reports ~/.easy-verifier-sot",
            "sudo chown 10001:10001 ~/.easy-verifier-reports ~/.easy-verifier-sot",
            "docker run -d --name easy-verifier",
        ),
    ),
    (
        "3-register",
        "Register",
        ("claude mcp add --transport http easy-verifier http://127.0.0.1:8766/mcp",),
    ),
)


def check_quick_start(parser: _Parser, docs: str) -> None:
    run = _in(parser, "run")
    steps = [e for e in run if e.tag == "pre" and "data-step" in e.attrs]
    assert [e.attrs["data-step"] for e in steps] == [s[0] for s in QUICK_START]
    # the first <pre> in #run is step 1: nothing else comes before the quick start
    assert [e for e in run if e.tag == "pre"][0] is steps[0]
    heads = [_norm(e.text) for e in run if e.tag == "h3"]
    for (_, label, _n), head in zip(QUICK_START, heads[:3], strict=True):
        assert label in head, f"step heading {head!r} lacks {label!r}"
    docs_lines = _lines(docs)
    for (step, _, needles), pre in zip(QUICK_START, steps, strict=True):
        text = _lines(pre.text)
        for needle in needles:
            assert needle in text, f"step {step} lacks {needle!r}"
        # blank-line separated chunks (prep, then run) are each contiguous in the docs
        for chunk in re.split(r"\n\s*\n", pre.text.strip()):
            assert _lines(chunk) in docs_lines, (
                f"step {step} is not verbatim in the docs"
            )
    other = [e for e in run if e.tag == "details"]
    assert len(other) == 1, "expected one 'Other ways' <details>"
    order = parser.elements
    assert order.index(other[0]) > order.index(steps[-1]), (
        "Other ways precedes Quick start"
    )
    summary = [e for e in run if e.tag == "summary"]
    assert summary and "Other ways" in summary[0].text
    later = [e for e in run if e.tag == "pre" and "data-step" not in e.attrs]
    assert later and all(order.index(e) > order.index(other[0]) for e in later), (
        "build-from-source, stdio and CLI blocks must sit under Other ways"
    )


def test_quick_start_is_first_and_verbatim():
    check_quick_start(_page(), _docs_text())


def test_quick_start_command_missing_from_docs_fails():
    docs = _docs_text().replace("docker pull temvar/easy-verifier-mcp:0.1.0", "")
    with pytest.raises(AssertionError, match="verbatim"):
        check_quick_start(_page(), docs)


def test_quick_start_reordered_fails():
    html = PAGE.read_text(encoding="utf-8")
    swapped = (
        html.replace('data-step="1-pull"', 'data-step="X"')
        .replace('data-step="3-register"', 'data-step="1-pull"')
        .replace('data-step="X"', 'data-step="3-register"')
    )
    parser = _Parser()
    parser.feed(swapped)
    with pytest.raises(AssertionError):
        check_quick_start(parser, _docs_text())


def test_other_ways_keep_stdio_cli_and_build():
    details = " ".join(e.text for e in _in(_page(), "run") if e.tag in ("pre", "code"))
    for needle in (
        "docker compose build scorer",
        "claude mcp add easy-verifier -- easy-verifier-mcp",
        "python -m easy_verifier.adapters.cli score --repo . --scope project",
    ):
        assert needle in details


FLOW_ORDER = (
    "Repository",
    "Evidence",
    "Rules",
    "Coverage check",
    "Rating 0",
    "Abstention",
    "Overall",
    "Improvement plan",
)


def check_flow_diagram(parser: _Parser) -> None:
    svgs = _in(parser, "scoring", "svg")
    assert len(svgs) == 1, "expected one step diagram in #scoring"
    attrs = svgs[0].attrs
    assert attrs.get("role") == "img" and attrs.get("aria-labelledby")
    assert "viewbox" in attrs, "diagram does not scale (no viewBox)"
    titles = [e for e in _in(parser, "scoring", "title") if e.text.strip()]
    assert titles, "diagram has no <title> text equivalent"
    assert any(e.tag == "desc" and e.text.strip() for e in _in(parser, "scoring"))
    text = " | ".join(_norm(e.text) for e in _in(parser, "scoring", "text"))
    position = -1
    for label in FLOW_ORDER:
        found = text.find(label, position + 1)
        assert found > position, f"diagram step {label!r} missing or out of order"
        position = found
    for word in ("measured metrics", "citations", "100", "reason code", "mean", "gain"):
        assert word in text.lower(), f"diagram does not say {word!r}"


def test_scoring_step_diagram():
    check_flow_diagram(_page())


def test_diagram_missing_step_fails():
    html = PAGE.read_text(encoding="utf-8").replace("Coverage check", "Gate", 1)
    parser = _Parser()
    parser.feed(html)
    with pytest.raises(AssertionError, match="Coverage check"):
        check_flow_diagram(parser)


def check_worked_example(parser: _Parser, snap: dict) -> None:
    rows = {
        r.attrs["data-example-dimension"]: r
        for r in _in(parser, "scoring", "tr", "data-example-dimension")
    }
    by_dim = {r["dimension"]: r for r in snap["ratings"]}
    assert set(rows) <= set(by_dim), "example dimension not in the snapshot"
    rated = [d for d in rows if "value" in by_dim[d]]
    abstained = [d for d in rows if "reason_code" in by_dim[d]]
    assert 2 <= len(rated) <= 3, "example needs two or three rated dimensions"
    assert len(abstained) == 1, "example needs exactly one abstained dimension"
    for dim, row in rows.items():
        if dim in rated:
            assert row.attrs.get("data-value") == str(by_dim[dim]["value"]), dim
        else:
            assert row.attrs.get("data-reason") == by_dim[dim]["reason_code"], dim
            assert by_dim[dim]["reason_code"] in row.text
    overall = _in(parser, "scoring", None, "data-example-overall")
    assert len(overall) == 1
    assert overall[0].attrs["data-example-overall"] == str(snap["overall"])
    assert str(snap["overall"]) in overall[0].text
    count = _in(parser, "scoring", None, "data-example-rated-count")
    assert count and count[0].attrs["data-example-rated-count"] == str(
        sum(1 for r in snap["ratings"] if "value" in r)
    )


def test_worked_example_matches_snapshot():
    check_worked_example(_page(), _snapshot())


def test_worked_example_with_wrong_number_fails():
    snap = _snapshot()
    snap["overall"] += 1
    with pytest.raises(AssertionError):
        check_worked_example(_page(), snap)
    snap = _snapshot()
    for r in snap["ratings"]:
        if "value" in r:
            r["value"] += 1
    with pytest.raises(AssertionError):
        check_worked_example(_page(), snap)


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
