"""T085 - a Next.js config counts as the framework's default browser
targets when no explicit browser-support declaration exists (area #19)."""

from __future__ import annotations

from test_t049_a11y_pack import BROWSERS, _derivation, _metric, _repo, _score, _value

from easy_verifier.core.registry import PACK_FIELDS, _value_problem, load_pack

APP = {"src/A.tsx": "export const A = () => <p/>;\n"}
FIELD = "browser_support_default_entries"


def _run(tmp_path, files):
    return _score(_repo(tmp_path, {**APP, **files}))


def test_next_config_is_the_framework_default(tmp_path):
    result = _run(tmp_path, {"next.config.js": "module.exports = {};\n"})
    assert _value(result, BROWSERS) == 0
    text = _derivation(result, BROWSERS)
    assert "framework default" in text and "Next.js" in text
    assert _metric(result, BROWSERS)["computed_from"] == ["next.config.js"]


def test_nuxt_config_is_not_credited_no_documented_default(tmp_path):
    result = _run(tmp_path, {"nuxt.config.ts": "export default {};\n"})
    assert _value(result, BROWSERS) == 1
    text = _derivation(result, BROWSERS)
    assert "no browser-support declaration" in text
    assert "framework default" not in text


def test_explicit_declaration_wins(tmp_path):
    result = _run(
        tmp_path,
        {
            "next.config.js": "module.exports = {};\n",
            ".browserslistrc": "last 2 versions\n",
        },
    )
    assert _value(result, BROWSERS) == 0
    text = _derivation(result, BROWSERS)
    assert "browser support declared at .browserslistrc" in text
    assert "framework default" not in text


def test_neither_is_still_missing(tmp_path):
    result = _run(tmp_path, {"package.json": '{"name": "web"}\n'})
    assert _value(result, BROWSERS) == 1
    assert "no browser-support declaration" in _derivation(result, BROWSERS)
    assert "framework default" not in _derivation(result, BROWSERS)


def test_config_in_a_test_path_is_not_credited(tmp_path):
    result = _run(tmp_path, {"tests/fixtures/next.config.js": "module.exports = {};\n"})
    assert _value(result, BROWSERS) == 1


def test_two_next_configs_pick_the_first_by_path(tmp_path):
    result = _run(
        tmp_path,
        {
            "web/next.config.js": "module.exports = {};\n",
            "admin/next.config.js": "module.exports = {};\n",
        },
    )
    metric = _metric(result, BROWSERS)
    assert metric["computed_from"] == ["admin/next.config.js"]


def test_field_is_a_cited_registry_field_with_a_shape_check():
    assert FIELD in PACK_FIELDS["frontend-a11y"]
    items = load_pack("frontend-a11y").fields[FIELD]
    assert {c.citation_url for c in items} == {
        "https://nextjs.org/docs/architecture/supported-browsers"
    }
    assert _value_problem(FIELD, "Remix=**/remix.config.js", local=True) is None
    assert _value_problem(FIELD, "**/remix.config.js", local=True) is not None
