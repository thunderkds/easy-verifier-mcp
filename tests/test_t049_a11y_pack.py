"""T049 - the optional frontend accessibility pack (area #19, DDR-0008 §4,
FR-053).

AC1 images without alt, form controls without a name and aria-hidden on a
focusable element count (WCAG 2.2 SC 1.1.1, 1.3.1, 4.1.2 cited); alt="" is
allowed; a spread or server-template expression in the tag is not verifiable,
never missing. AC2 viewport declared in the HTML entry, browser support
declared. AC3 markup syntax comes from the pack registry. AC4/5 inactive =
nothing in the payload and #19 unruled; floor 0.25; weights sum 100 and admit
an exact 50.
"""

from __future__ import annotations

import itertools
from pathlib import Path

import pytest

from easy_verifier.core.judge import (
    AREAS,
    PACK_FLOORS,
    RATING_RULES,
    areas_without_rule,
)
from easy_verifier.core.registry import PACK_FIELDS, load_pack
from easy_verifier.core.score import score_repository
from easy_verifier.packs import PACKS

NAME = "frontend-a11y"
IMAGES = "images_without_alt_observed"
CONTROLS = "form_controls_without_label_observed"
HIDDEN = "aria_hidden_focusable_observed"
VIEWPORT = "viewport_missing_or_zoom_disabled_observed"
BROWSERS = "browser_support_declaration_missing"
AREA = AREAS[18]
CONFIG = f'packs = ["{NAME}"]\n'
PACKAGE = '{"name": "web", "browserslist": ["defaults"]}\n'
BARE_IMG = 'export const A = () => <img src="x" />;\n'
INDEX = (
    '<!doctype html>\n<html>\n<head>\n'
    '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
    "</head>\n<body><div id=root></div></body>\n</html>\n"
)


def _write(root: Path, files: dict[str, str]) -> Path:
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


def _repo(tmp_path: Path, files: dict[str, str], *, config: str | None = CONFIG):
    base = {"README.md": "# Web\n\nA small app.\n"}
    if config is not None:
        base[".easy-verifier.toml"] = config
    return _write(tmp_path / "repo", {**base, **files})


def _score(repo: Path):
    return score_repository(repo, scope="project")


def _metric(result, name: str) -> dict:
    return next(
        m
        for m in result.to_dict()["metrics"]["metrics"]
        if m["dimension"] == NAME and m["name"] == name
    )


def _value(result, name: str):
    outcome = _metric(result, name)["outcome"]
    return None if outcome["abstained"] else outcome["value"]


def _derivation(result, name: str) -> str:
    return _metric(result, name)["derivation"]


def _rating(result) -> dict:
    return next(r for r in result.to_dict()["ratings"] if r["dimension"] == NAME)


def _one(tmp_path, path: str, text: str):
    return _score(_repo(tmp_path, {path: text}))


# ---------------------------------------------------------------------------
# rule table, registry, activation


def test_rules_are_cited_labelled_and_weights_admit_an_exact_fifty() -> None:
    rules = RATING_RULES[NAME]
    assert list(rules) == [IMAGES, CONTROLS, HIDDEN, VIEWPORT, BROWSERS]
    weights = [rule.weight for rule in rules.values()]
    assert sum(weights) == 100
    assert any(
        sum(combo) == 50
        for n in range(1, len(weights))
        for combo in itertools.combinations(weights, n)
    )
    for rule in rules.values():
        assert rule.area == AREA
        assert (rule.comparison, rule.threshold) == ("at_most", 0)
        assert all(c.url.startswith("https://") for c in rule.metric_citation)
    labels = {
        name: " ".join(c.label for c in rule.metric_citation)
        for name, rule in rules.items()
    }
    assert "WCAG 2.2" in labels[IMAGES] and "1.1.1" in labels[IMAGES]
    assert "1.3.1" in labels[CONTROLS] and "4.1.2" in labels[CONTROLS]
    assert "4.1.2" in labels[HIDDEN]
    assert "1.4.4" in labels[VIEWPORT]
    assert PACK_FLOORS[NAME].value == 0.25
    assert PACK_FLOORS[NAME].boundary == "inclusive"
    assert NAME in PACKS


def test_markup_syntax_lives_in_the_registry_with_citations() -> None:
    entry = load_pack(NAME)
    assert set(entry.fields) == set(PACK_FIELDS[NAME])
    urls = set()
    for items in entry.fields.values():
        for item in items:
            assert item.citation_url.startswith("https://")
            assert item.source_tag == "curated"
            urls.add(item.citation_url)
    for doc in ("react.dev", "vuejs.org", "svelte.dev", "jinja", "ERB", "w3.org"):
        assert any(doc in url for url in urls), doc
    source = Path("src/easy_verifier/packs/frontend_a11y.py").read_text(
        encoding="utf-8"
    )
    for literal in ('"img"', '"aria-label"', '"htmlfor"', '"viewport"', "*.tsx"):
        assert literal not in source


# ---------------------------------------------------------------------------
# AC1 images (SC 1.1.1)


def test_react_img_without_alt_is_unmet_with_path_line_and_wcag_link(tmp_path):
    result = _one(
        tmp_path,
        "src/Avatar.tsx",
        "export function Avatar({ url }) {\n  return (\n"
        "    <img src={url} className=\"a\" />\n  );\n}\n",
    )
    assert _value(result, IMAGES) == 1
    derivation = _derivation(result, IMAGES)
    assert "src/Avatar.tsx:3" in derivation
    assert "https://www.w3.org/WAI/WCAG22/Understanding/non-text-content.html" in (
        derivation
    )
    assert "src/Avatar.tsx" in _metric(result, IMAGES)["computed_from"]


def test_empty_alt_is_decorative_and_met(tmp_path):
    result = _one(
        tmp_path,
        "src/Logo.jsx",
        'export const Logo = () => <img alt="" src="l.svg" />;\n',
    )
    assert _value(result, IMAGES) == 0


def test_spread_props_are_not_verifiable_not_missing(tmp_path):
    result = _one(
        tmp_path,
        "src/Pic.tsx",
        "export const Pic = (props) => <img {...props} />;\n"
        "export const Bad = () => <img src=\"b.png\" />;\n",
    )
    assert _value(result, IMAGES) == 1
    derivation = _derivation(result, IMAGES)
    assert "src/Pic.tsx:2" in derivation
    assert "not verifiable" in derivation and "src/Pic.tsx:1" in derivation


@pytest.mark.parametrize(
    ("path", "text", "expected"),
    [
        ("src/A.vue", '<template>\n  <img :alt="caption" :src="u">\n</template>\n', 0),
        ("src/A.vue", '<template>\n  <img v-bind:alt="c" src="u">\n</template>\n', 0),
        ("src/A.vue", '<template>\n  <img src="u.png">\n</template>\n', 1),
        ("src/A.vue", '<template>\n  <img v-bind="attrs">\n</template>\n', None),
        ("src/A.svelte", "<img {src} {alt} />\n", 0),
        ("src/A.svelte", "<img {src} />\n", 1),
        ("src/a.component.html", '<img [alt]="caption" [src]="u">\n', 0),
        ("templates/a.html", '<img src="{{ url }}">\n', 1),
        ("templates/a.html", '<img alt="{{ caption }}" src="{{ url }}">\n', 0),
        ("templates/a.html", "<img {{ attrs }}>\n", None),
        ("app/views/a.html.erb", '<img src="<%= u %>">\n', 1),
        ("app/views/a.html.erb", "<img <%= tag_options %>>\n", None),
        ("public/a.html", "<!-- <img src=x> -->\n<p>hi</p>\n<img src=y alt=z>\n", 0),
        (
            "src/A.jsx",
            "const A = () => (\n  <div>{/* <img src=\"x\" /> */}</div>\n);\n",
            None,
        ),
        ("src/A.tsx", "export const Hero = () => <Image src=\"h.png\" />;\n", None),
    ],
)
def test_image_syntax_per_framework(tmp_path, path, text, expected):
    assert _value(_one(tmp_path, path, text), IMAGES) == expected


def test_no_image_abstains(tmp_path):
    result = _one(tmp_path, "src/A.tsx", "export const A = () => <p>hi</p>;\n")
    assert _value(result, IMAGES) is None
    assert "nothing to judge" in _metric(result, IMAGES)["outcome"]["reason"]


def test_comparisons_are_not_tags(tmp_path):
    result = _one(
        tmp_path,
        "src/loop.tsx",
        "export function f(input: number[]) {\n"
        "  for (let i = 0; i<input.length; i++) {}\n"
        "  return i < input.length && <p>x</p>;\n}\n",
    )
    assert _value(result, CONTROLS) is None


# ---------------------------------------------------------------------------
# AC1 form controls (SC 1.3.1 / 4.1.2)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ('<input type="text" name="q">', 1),
        ('<input placeholder="Search">', 1),
        ('<input aria-label="Search">', 0),
        ('<input aria-labelledby="h">', 0),
        ('<input title="Search">', 0),
        ("<label>Name <input name=\"n\"></label>", 0),
        ('<label for="e">Email</label>\n<input id="e">', 0),
        ('<label htmlFor="e">Email</label>\n<input id="e" />', 0),
        ('<label htmlFor="other">Email</label>\n<input id="e" />', 1),
        ('<input type="hidden" name="t">', None),
        ('<input type="submit" value="Go">', None),
        ("<select name=\"s\"><option>a</option></select>", 1),
        ("<textarea></textarea>", 1),
        ("<input {...field} />", None),
    ],
)
def test_form_controls_need_a_name(tmp_path, text, expected):
    code = f"export const F = () => (\n<form>{text}</form>\n);\n"
    result = _one(tmp_path, "src/Form.jsx", code)
    assert _value(result, CONTROLS) == expected


def test_capitalised_components_are_not_dom_elements(tmp_path):
    # next-web 2026-10-08: <Input placeholder=...> / <Select label=...> are
    # React components (they may label themselves), never <input> / <select>.
    result = _one(
        tmp_path,
        "src/Search.tsx",
        "export const S = () => (\n  <div>\n    <Input placeholder=\"Search\" />\n"
        "    <Select label=\"Filter\" options={o} />\n    <IMG src=\"x\" />\n"
        "  </div>\n);\n",
    )
    assert _value(result, CONTROLS) is None
    assert _value(result, IMAGES) is None


def test_dynamic_label_for_makes_an_id_not_verifiable(tmp_path):
    result = _one(
        tmp_path,
        "src/Field.tsx",
        "export const F = ({ id, other }) => (\n  <>\n"
        "    <label htmlFor={other}>Name</label>\n"
        "    <input id={id} />\n  </>\n);\n",
    )
    assert _value(result, CONTROLS) is None
    reason = _metric(result, CONTROLS)["outcome"]["reason"]
    assert "not verifiable" in reason and "src/Field.tsx:4" in reason


def test_the_same_expression_in_for_and_id_is_a_label(tmp_path):
    result = _one(
        tmp_path,
        "src/Select.tsx",
        "export const S = ({ n }) => (\n  <>\n"
        "    <label htmlFor={`select-${n}`}>Pick</label>\n"
        "    <select id={`select-${n}`}></select>\n  </>\n);\n",
    )
    assert _value(result, CONTROLS) == 0


# ---------------------------------------------------------------------------
# AC1 aria-hidden on focusable (SC 4.1.2)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ('<button aria-hidden="true">x</button>', 1),
        ('<a href="/x" aria-hidden="true">x</a>', 1),
        ('<a aria-hidden="true">x</a>', 0),
        ("<div tabIndex={0} aria-hidden>x</div>", 1),
        ('<span tabindex="-1" aria-hidden="true">x</span>', 0),
        ('<div aria-hidden="true">x</div>', 0),
        ('<button aria-hidden="false">x</button>', 0),
        ('<button disabled aria-hidden="true">x</button>', 0),
        ("<p>no aria</p>", None),
    ],
)
def test_aria_hidden_on_focusable(tmp_path, text, expected):
    code = f"export const H = () => (\n<div>{text}</div>\n);\n"
    result = _one(tmp_path, "src/H.jsx", code)
    assert _value(result, HIDDEN) == expected


# ---------------------------------------------------------------------------
# AC2 viewport and browser support


def test_viewport_in_the_html_entry(tmp_path):
    assert _value(_one(tmp_path / "a", "index.html", INDEX), VIEWPORT) == 0
    missing = _one(tmp_path / "b", "index.html", "<html><head></head></html>\n")
    assert _value(missing, VIEWPORT) == 1
    assert "index.html:1" in _derivation(missing, VIEWPORT)
    zoom = INDEX.replace("initial-scale=1", "initial-scale=1, user-scalable=no")
    capped = _one(tmp_path / "c", "index.html", zoom)
    assert _value(capped, VIEWPORT) == 1
    assert "index.html:4" in _derivation(capped, VIEWPORT)
    assert "resize-text" in _derivation(capped, VIEWPORT)


def test_next_root_layout_gets_a_default_viewport_unless_zoom_is_disabled(tmp_path):
    layout = (
        "export default function RootLayout({ children }) {\n"
        "  return <html><body>{children}</body></html>;\n}\n"
    )
    assert _value(_one(tmp_path / "a", "src/app/layout.tsx", layout), VIEWPORT) == 0
    locked = (
        "export const viewport = {\n  width: 'device-width',\n"
        "  maximumScale: 1,\n  userScalable: false,\n};\n" + layout
    )
    result = _one(tmp_path / "b", "src/app/layout.tsx", locked)
    assert _value(result, VIEWPORT) == 1
    assert "src/app/layout.tsx:3" in _derivation(result, VIEWPORT)


def test_no_entry_document_abstains(tmp_path):
    result = _one(tmp_path, "src/A.tsx", "export const A = () => <p>hi</p>;\n")
    assert _value(result, VIEWPORT) is None


@pytest.mark.parametrize(
    ("files", "expected"),
    [
        ({"package.json": PACKAGE}, 0),
        ({"package.json": '{"name": "web"}\n'}, 1),
        (
            {
                "package.json": '{"name": "web"}\n',
                ".browserslistrc": "> 0.5%\nlast 2 versions\n",
            },
            0,
        ),
        ({"package.json": '{"nx": {"targets": {}}}\n'}, 1),
        (
            {
                "vite.config.ts": (
                    "export default {\n  build: {\n    target: 'es2020',\n  },\n};\n"
                )
            },
            0,
        ),
    ],
)
def test_browser_support_declared(tmp_path, files, expected):
    repo = _repo(tmp_path, {"src/A.tsx": "export const A = () => <p/>;\n", **files})
    assert _value(_score(repo), BROWSERS) == expected


def test_no_markup_abstains_browser_support(tmp_path):
    result = _one(tmp_path, "src/app.py", "def app():\n    return 1\n")
    assert _value(result, BROWSERS) is None
    assert _value(result, IMAGES) is None


# ---------------------------------------------------------------------------
# rating, activation, inactivity


def test_a_clean_frontend_rates_100_and_area_19_is_measured(tmp_path):
    repo = _repo(
        tmp_path,
        {
            "package.json": PACKAGE,
            "index.html": INDEX,
            "src/App.tsx": (
                "export const App = () => (\n  <main>\n"
                "    <img alt=\"\" src=\"x.svg\" />\n"
                "    <input aria-label=\"q\" />\n  </main>\n);\n"
            ),
        },
    )
    result = _score(repo)
    assert _rating(result)["value"] == 100
    payload = result.to_dict()
    assert AREA not in payload["areas_without_rule"]
    assert AREA in payload["areas_measured"]
    assert f"packs active: {NAME}" in payload["overall"]["disclosure"]


def test_test_and_story_files_are_not_shipped_markup(tmp_path):
    repo = _repo(
        tmp_path,
        {
            "src/A.test.tsx": 'render(<img src="x" />);\n',
            "src/A.stories.tsx": 'export const S = () => <img src="x" />;\n',
            "src/A.tsx": 'export const A = () => <img alt="a" src="x" />;\n',
        },
    )
    assert _value(_score(repo), IMAGES) == 0


def test_inactive_pack_leaves_no_trace_and_area_stays_unruled(tmp_path):
    repo = _repo(tmp_path, {"src/A.tsx": BARE_IMG}, config=None)
    result = _score(repo)
    payload = result.serialize()
    assert NAME not in payload and IMAGES not in payload
    assert AREA in result.to_dict()["areas_without_rule"]
    assert AREA in areas_without_rule()
    assert AREA not in areas_without_rule((NAME,))


def test_agent_pick_activates_and_replay_is_byte_equal(tmp_path):
    repo = _repo(tmp_path, {"src/A.tsx": BARE_IMG}, config=None)
    first = score_repository(repo, scope="project", agent_input={"packs": [NAME]})
    assert _value(first, IMAGES) == 1
    again = score_repository(repo, scope="project", agent_input={"packs": [NAME]})
    assert again.serialize() == first.serialize()
