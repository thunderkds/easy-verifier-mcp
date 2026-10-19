"""T117 theme test for site/index.html: the kit's dark neon theme, pinned.

Pins the design tokens, dark-only rendering, colours only via ``var(--...)``,
the sidebar navigation and the inline-only script. Content stays pinned by
``tests/test_site_content.py``.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

PAGE = Path(__file__).resolve().parent.parent / "site" / "index.html"
SECTION_IDS = ("what", "run", "dimensions", "areas", "scoring", "sample")
KIT_TOKENS = {
    "--bg": "#0a0a12",
    "--surface": "#111128",
    "--surface2": "#16162e",
    "--border": "#1e1e42",
    "--text": "#e2e2f0",
    "--cyan": "#00d4ff",
    "--green": "#00ff88",
    "--amber": "#ffb800",
    "--purple": "#a855f7",
}
DIM_TOKENS = ("--cyan-dim", "--green-dim", "--amber-dim", "--purple-dim")
_RAW_COLOR = re.compile(r"#[0-9a-fA-F]{3,8}\b|\b(?:rgba?|hsla?)\s*\(")


def _html() -> str:
    return PAGE.read_text(encoding="utf-8")


def _style(html: str) -> str:
    match = re.search(r"<style>(.*?)</style>", html, re.S)
    assert match, "no <style> block"
    return match.group(1)


def _root_block(style: str) -> str:
    match = re.search(r":root\s*\{(.*?)\}", style, re.S)
    assert match, "no :root block"
    return match.group(1)


def _tokens(html: str) -> dict[str, str]:
    root = _root_block(_style(html))
    return {k: v.strip() for k, v in re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", root)}


# ---- checks (functions, so the negative tests can run them on edited copies) ----


def check_tokens(html: str) -> None:
    tokens = _tokens(html)
    for name, value in KIT_TOKENS.items():
        assert tokens.get(name, "").lower() == value, f"{name}: {tokens.get(name)!r}"
    for name in DIM_TOKENS:
        assert tokens.get(name, "").startswith("rgba("), f"{name} missing"
    assert "--muted" in tokens


def check_dark_only(html: str) -> None:
    assert "prefers-color-scheme" not in html


def check_no_raw_colors(html: str) -> None:
    style = _style(html)
    rules = style.replace(_root_block(style), "", 1)
    assert not _RAW_COLOR.findall(rules), (
        f"raw colour outside :root: {_RAW_COLOR.findall(rules)}"
    )
    assert not re.search(r'\bstyle\s*=\s*"[^"]*(#[0-9a-f]{3}|rgb)', html, re.I)


def check_sidebar_nav(html: str) -> None:
    aside = re.search(
        r"<aside\b[^>]*class=\"[^\"]*\bsidebar\b[^\"]*\".*?</aside>", html, re.S
    )
    assert aside, "no aside.sidebar"
    side = aside.group(0)
    assert "nav-toggle" in side, "no .nav-toggle in the sidebar"
    assert len(re.findall(r"<nav\b", html)) == 1, "exactly one <nav> expected"
    nav = re.search(r"<nav\b.*?</nav>", side, re.S)
    assert nav, "no <nav> inside the sidebar"
    hrefs = re.findall(r'href="#([^"]+)"', nav.group(0))
    assert sorted(hrefs) == sorted(SECTION_IDS), f"sidebar links {hrefs}"
    assert "https://github.com/thunderkds/easy-verifier-mcp" in side
    assert '<div class="layout"' in html and 'class="header"' in html


def check_scripts_inline(html: str) -> None:
    scripts = re.findall(r"<script\b([^>]*)>", html, re.I)
    assert scripts, "expected the inline nav script"
    assert not any("src" in attrs.lower() for attrs in scripts)


# ---- AC 1-3 ----


def test_kit_tokens_in_root():
    check_tokens(_html())


def test_dark_only():
    check_dark_only(_html())


def test_colors_only_via_variables():
    check_no_raw_colors(_html())


def test_sidebar_nav_links_exactly_the_six_sections():
    check_sidebar_nav(_html())


def test_scripts_are_inline_only():
    check_scripts_inline(_html())


def test_nav_is_open_in_markup_without_js():
    html = _html()
    nav = re.search(r"<nav\b[^>]*>", html)
    assert nav and "data-collapsed" not in nav.group(0)


def test_accessibility_details():
    html = _html()
    style = _style(html)
    assert 'class="skip-link"' in html
    assert ":focus-visible" in style
    assert "prefers-reduced-motion" in style


# ---- negatives: the checks bite ----


def test_missing_nav_link_fails():
    html = _html().replace('<a href="#scoring">', '<a href="#nowhere">', 1)
    with pytest.raises(AssertionError):
        check_sidebar_nav(html)


def test_hex_outside_root_fails():
    html = _html().replace("</style>", "  a { color: #fff; }\n</style>", 1)
    with pytest.raises(AssertionError):
        check_no_raw_colors(html)


def test_rgba_outside_root_fails():
    html = _html().replace("</style>", "  a { color: rgba(0,0,0,.5); }\n</style>", 1)
    with pytest.raises(AssertionError):
        check_no_raw_colors(html)


def test_color_scheme_block_fails():
    html = _html().replace(
        "</style>", "@media (prefers-color-scheme: light){}\n</style>", 1
    )
    with pytest.raises(AssertionError):
        check_dark_only(html)


def test_external_script_fails():
    html = _html().replace("<script>", '<script src="https://x.example/a.js">', 1)
    with pytest.raises(AssertionError):
        check_scripts_inline(html)
