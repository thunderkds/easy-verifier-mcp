"""T040 - area rule-group metrics inside existing dimensions (FR-051, FR-043).

Metrics for #16 (tests without assertions, skipped tests, network calls in
unit tests), #17 (type-escape density) and #31 (TODO/FIXME without a ticket
reference). Language syntax (skip markers, network calls, type escapes, type
stub names) is registry data; each test pins a predicate against its twin, so
a metric that ignored the predicate would fail here.
"""

from __future__ import annotations

import dataclasses

import pytest

from easy_verifier.core.judge import AREAS, PROJECT_DEFAULT, RATING_RULES, rate
from easy_verifier.core.metric_tables import curated_metric_tables
from easy_verifier.core.metrics import (
    EVIDENCE_LOCAL,
    METRIC_DEFINITIONS,
    WHOLE_SET,
    compute_metrics,
)
from easy_verifier.core.models import (
    CoverageSummary,
    EvidencePack,
    Excerpt,
    TruncationRecord,
)
from easy_verifier.core.registry import load_registry
from easy_verifier.core.roles import GENERIC_PATTERNS

NEW_METRICS = {
    "tests_without_assertions_share": WHOLE_SET,
    "skipped_test_share": WHOLE_SET,
    "network_calls_in_unit_tests_observed": EVIDENCE_LOCAL,
    "type_escapes_per_kloc": WHOLE_SET,
    "todo_without_ticket_share": WHOLE_SET,
}
REQUIRED_FIELDS = ("skip_markers", "network_calls", "type_escapes")


def pack(files, *, dimension="test-strategy", truncated=False):
    """``files`` maps path -> text; each becomes one whole-file excerpt."""
    omitted = 3 if truncated else 0
    return EvidencePack(
        dimension=dimension,
        mode="kit-aware",
        scope="worktree",
        files_read=tuple(files),
        excerpts=tuple(
            Excerpt(path, 1, len(text.splitlines()), text)
            for path, text in files.items()
        ),
        sources_sought=("x",),
        sources_found=("x",),
        sources_missing=(),
        coverage_score=1.0,
        truncated=truncated,
        omitted_count=omitted,
        truncation=TruncationRecord(truncated=truncated, omitted_count=omitted),
    )


def metric(name, files, **kwargs):
    (found,) = compute_metrics(pack(files, **kwargs), curated_metric_tables()).by_name(
        name
    )
    return found


def test_new_metrics_are_declared_with_their_kind():
    kinds = {d.name: d.kind for d in METRIC_DEFINITIONS}
    for name, kind in NEW_METRICS.items():
        assert kinds.get(name) == kind, name


@pytest.mark.parametrize("field", REQUIRED_FIELDS)
def test_every_curated_language_declares_the_new_syntax_fields(field):
    registry = load_registry(known_roles=GENERIC_PATTERNS)
    lacking = [
        name
        for name, entry in registry.languages.items()
        if not entry.fields.get(field)
    ]
    assert lacking == []


# --- #16: tests without assertions -----------------------------------------

PY_TESTS = """\
def test_parse_runs():
    parse("1")


def test_parse_checks():
    assert parse("2") == 2
"""


def test_a_python_test_without_assertions_is_reported():
    found = metric("tests_without_assertions_share", {"tests/test_p.py": PY_TESTS})
    assert found.outcome == 0.5
    assert "tests/test_p.py:1" in found.derivation
    assert "tests/test_p.py:5" not in found.derivation


def test_an_assertion_in_a_comment_or_string_does_not_count():
    text = PY_TESTS.replace(
        'parse("1")', 'parse("1")  # assert later\n    x = "assert"'
    )
    found = metric("tests_without_assertions_share", {"tests/test_p.py": text})
    assert found.outcome == 0.5


def test_all_asserted_tests_share_is_zero_and_js_is_segmented_per_test():
    js = (
        'it("adds", () => {\n  expect(add(1, 1)).toBe(2);\n});\n'
        'it("runs", () => {\n  add(1, 1);\n});\n'
    )
    assert metric("tests_without_assertions_share", {"a.test.js": js}).outcome == 0.5
    fixed = js.replace("  add(1, 1);", "  expect(add(1, 1)).toBe(2);")
    assert metric("tests_without_assertions_share", {"a.test.js": fixed}).outcome == 0.0


def test_no_test_declaration_abstains_and_truncation_abstains():
    found = metric("tests_without_assertions_share", {"tests/test_p.py": "x = 1\n"})
    assert found.abstained
    found = metric(
        "tests_without_assertions_share", {"tests/test_p.py": PY_TESTS}, truncated=True
    )
    assert found.abstained and "truncated" in found.outcome.reason


# --- #16: skipped tests ------------------------------------------------------

SKIPS = """\
import pytest


@pytest.mark.skip
def test_a():
    assert 1


@pytest.mark.skip(reason="flaky upstream")
def test_b():
    assert 1


@pytest.mark.skipif(sys.platform == "win32", reason="posix only")
def test_c():
    assert 1


def test_d():
    # @pytest.mark.skip was removed
    s = "@pytest.mark.skip"
    assert s
"""


def test_skip_markers_are_counted_with_and_without_reason():
    found = metric("skipped_test_share", {"tests/test_s.py": SKIPS})
    # skipif is conditional, and markers in comments or strings are not code.
    assert found.outcome == 0.5
    assert "1 with a reason" in found.derivation
    assert "1 without" in found.derivation
    assert "tests/test_s.py:4" in found.derivation


def test_no_skips_is_zero_and_other_languages_use_their_markers():
    clean = SKIPS.replace("@pytest.mark.skip\n", "").replace(
        '@pytest.mark.skip(reason="flaky upstream")\n', ""
    )
    assert metric("skipped_test_share", {"tests/test_s.py": clean}).outcome == 0.0
    js = (
        'it.skip("a", () => {\n  expect(1).toBe(1);\n});\n'
        'it("b", () => {\n  expect(1).toBe(1);\n});\n'
    )
    assert metric("skipped_test_share", {"a.test.js": js}).outcome == 0.5


# --- #16: network calls in unit tests ---------------------------------------

NET = """\
import requests


def test_remote():
    requests.get("https://example.com")
    assert True
"""


def test_a_network_call_in_a_unit_test_is_counted_with_its_line():
    found = metric("network_calls_in_unit_tests_observed", {"tests/test_n.py": NET})
    assert found.outcome == 1
    assert "tests/test_n.py:5" in found.derivation


def test_network_calls_in_integration_tests_comments_and_sources_do_not_count():
    commented = NET.replace(
        '    requests.get("https://example.com")', "    # requests.get(url)"
    )
    assert (
        metric(
            "network_calls_in_unit_tests_observed", {"tests/test_n.py": commented}
        ).outcome
        == 0
    )
    found = metric(
        "network_calls_in_unit_tests_observed",
        {"tests/integration/test_n.py": NET, "src/app/client.py": NET},
    )
    assert found.abstained
    assert "integration" in found.outcome.reason


# --- #17: type escapes -------------------------------------------------------

TYPED = """\
from typing import Any


def parse(value: Any) -> int:  # type: ignore[arg-type]
    return int(value)


def name() -> str:
    return "type: ignore"
"""


def test_type_escapes_are_counted_per_thousand_quoted_source_lines():
    found = metric(
        "type_escapes_per_kloc", {"src/app/p.py": TYPED}, dimension="code-quality"
    )
    # ": Any" and "type: ignore" on line 4; the string on line 9 is not code.
    assert found.outcome == pytest.approx(2 / 9 * 1000)
    assert "src/app/p.py:4" in found.derivation
    assert "src/app/p.py:9" not in found.derivation


def test_generated_type_stubs_are_not_scanned_and_ts_any_counts():
    ts = "export function f(x: any): number {\n  return x as any;\n}\n"
    found = metric(
        "type_escapes_per_kloc",
        {"src/f.ts": ts, "src/types/gen.d.ts": "declare const y: any;\n" * 10},
        dimension="code-quality",
    )
    assert found.outcome == pytest.approx(2 / 3 * 1000)
    assert "gen.d.ts" not in found.derivation.split(";")[0]
    only_stub = metric(
        "type_escapes_per_kloc",
        {"src/types/gen.d.ts": "declare const y: any;\n"},
        dimension="code-quality",
    )
    assert only_stub.abstained


# --- #31: TODO/FIXME ticket references --------------------------------------

TODOS = """\
def login(user):  # TODO: add rate limiting
    # FIXME(ABC-123): constant-time compare
    note = "TODO this is data, not a comment"
    return user  # HACK see https://example.com/issues/9
"""


def test_todo_share_without_ticket_ignores_strings():
    found = metric(
        "todo_without_ticket_share", {"src/app/a.py": TODOS}, dimension="code-quality"
    )
    assert found.outcome == pytest.approx(1 / 3)
    assert "src/app/a.py:1" in found.derivation
    assert "src/app/a.py:3" not in found.derivation


def test_no_todo_abstains_as_zero_denominator():
    found = metric(
        "todo_without_ticket_share",
        {"src/app/a.py": "def f():\n    return 1\n"},
        dimension="code-quality",
    )
    assert found.abstained
    assert "zero denominator" in found.outcome.reason


def test_todo_share_abstains_on_a_truncated_pack():
    found = metric(
        "todo_without_ticket_share",
        {"src/app/a.py": TODOS},
        dimension="code-quality",
        truncated=True,
    )
    assert found.abstained and "truncated" in found.outcome.reason


def test_skip_marker_forms_decorator_attribute_and_in_body():
    java = '@Disabled\n@DisplayName("x")\n@Test\nvoid a() {}\n\n@Test\nvoid b() {}\n'
    assert (
        metric("skipped_test_share", {"src/test/java/ATest.java": java}).outcome == 0.5
    )
    go = (
        'func TestA(t *testing.T) {\n\tt.Skip("slow")\n}\n\n'
        "func TestB(t *testing.T) {\n\tt.Error(1)\n}\n"
    )
    found = metric("skipped_test_share", {"a_test.go": go})
    assert found.outcome == 0.5
    assert "1 with a reason" in found.derivation


# --- AC7: the signed-off weight tables, and each new rule met / unmet --------

SIGNED_OFF = {
    "test-strategy": {
        "source_files_without_covering_test_share": (25, AREAS[15]),
        "assertion_density_per_test": (20, AREAS[15]),
        "test_config_and_ci_missing": (20, AREAS[15]),
        "tests_without_assertions_share": (15, AREAS[15]),
        "skipped_test_share": (10, AREAS[15]),
        "network_calls_in_unit_tests_observed": (10, AREAS[15]),
    },
    "code-quality": {
        "functions_over_ccn_10_share": (25, AREAS[17]),
        "max_function_ccn": (15, AREAS[17]),
        "lint_config_missing": (10, AREAS[16]),
        "format_config_missing": (10, AREAS[16]),
        "type_escapes_per_kloc": (15, AREAS[16]),
        "todo_without_ticket_share": (15, AREAS[30]),
        "strict_type_config_missing": (10, AREAS[16]),  # T056, 2026-09-30
    },
}


@pytest.mark.parametrize("dimension", sorted(SIGNED_OFF))
def test_signed_off_weight_table_and_areas(dimension):
    rules = RATING_RULES[dimension]
    assert {n: (r.weight, r.area) for n, r in rules.items()} == SIGNED_OFF[dimension]
    assert sum(r.weight for r in rules.values()) == 100
    for name in NEW_METRICS:
        if name in rules:
            assert rules[name].threshold_citation == PROJECT_DEFAULT


def test_todo_rule_cites_iso_5055_only():
    (citation,) = RATING_RULES["code-quality"][
        "todo_without_ticket_share"
    ].metric_citation
    assert "5055" in citation.label


def rated_inputs(files, dimension):
    evidence = pack(files, dimension=dimension)
    coverage = CoverageSummary(
        per_dimension=((dimension, 1.0),),
        combined=1.0,
        method="test",
        misses=((dimension, ()),),
    )
    result = rate(compute_metrics(evidence, curated_metric_tables()), coverage)
    return {item.metric_name: item.passed for item in result.inputs}


UNIT_OK = """\
def test_a():
    assert parse("1") == 1


def test_b():
    assert parse("2") == 2
"""


@pytest.mark.parametrize(
    ("name", "met", "unmet"),
    [
        ("tests_without_assertions_share", UNIT_OK, PY_TESTS),
        ("skipped_test_share", UNIT_OK, SKIPS),
        (
            "network_calls_in_unit_tests_observed",
            UNIT_OK,
            UNIT_OK.replace(
                '    assert parse("2")', '    requests.get(u)\n    assert parse("2")'
            ),
        ),
    ],
)
def test_new_test_strategy_rules_are_met_and_unmet(name, met, unmet):
    assert rated_inputs({"tests/test_p.py": met}, "test-strategy")[name] is True
    assert rated_inputs({"tests/test_p.py": unmet}, "test-strategy")[name] is False


def test_new_code_quality_rules_are_met_and_unmet():
    clean = "def f(x: int) -> int:\n    # TODO(ABC-1): tidy\n    return x\n" * 4
    dirty = TYPED + "\n# TODO: one\n# FIXME: two\n"
    met = rated_inputs({"src/app/p.py": clean}, "code-quality")
    unmet = rated_inputs({"src/app/p.py": dirty}, "code-quality")
    for name in ("type_escapes_per_kloc", "todo_without_ticket_share"):
        assert met[name] is True, name
        assert unmet[name] is False, name


# --- Stage 4 P1: a test cut by the excerpt line cap is not judged -----------


def _long_test_file(last_asserts: bool = True) -> str:
    """10 asserting tests; the last starts near line 192 and asserts ~208."""
    parts = []
    for index in range(9):
        parts.append(f"def test_{index}():\n    assert {index} == {index}\n\n")
    head = "".join(parts)
    pad = "\n" * (191 - head.count("\n"))
    body = "    x = 1\n" * 15 + ("    assert x\n" if last_asserts else "    x += 1\n")
    return head + pad + "def test_last():\n" + body


def _clipped_pack(text: str):
    from easy_verifier.core.context import whole_file_excerpt

    excerpt = whole_file_excerpt("tests/test_core.py", text)
    evidence = pack({"tests/test_core.py": "x"})
    return dataclasses.replace(evidence, excerpts=(excerpt,))


def test_a_test_cut_by_the_excerpt_limit_is_not_judged():
    text = _long_test_file()
    assert text.split("\n").index("def test_last():") + 1 == 192
    evidence = _clipped_pack(text)
    assert "excerpt clipped" in evidence.excerpts[0].text
    (found,) = compute_metrics(evidence, curated_metric_tables()).by_name(
        "tests_without_assertions_share"
    )
    assert found.outcome == 0.0
    assert "0 of 9 observed test(s)" in found.derivation
    assert "1 test(s) cut by the excerpt line limit were not judged" in found.derivation
    assert "tests/test_core.py:19" not in found.derivation


def test_an_unclipped_last_test_without_assertion_is_still_reported():
    # sabotage twin: same shape, short enough to be quoted whole
    text = _long_test_file(last_asserts=False).replace("\n" * 150, "\n")
    found = metric("tests_without_assertions_share", {"tests/test_core.py": text})
    assert found.outcome == pytest.approx(1 / 10)
    line = text.split("\n").index("def test_last():") + 1
    assert f"tests/test_core.py:{line}" in found.derivation
    assert "cut by the excerpt line limit" not in found.derivation


def test_clip_marker_pattern_matches_both_excerpt_producers():
    from easy_verifier.core.context import whole_file_excerpt
    from easy_verifier.core.metrics import excerpt_clipped
    from easy_verifier.dimensions._code_extract import _excerpt

    lines = [f"line {n}" for n in range(300)]
    assert excerpt_clipped(whole_file_excerpt("a.py", "\n".join(lines)).text)
    assert excerpt_clipped(_excerpt("a.py", lines, 0, 299).text)
    assert not excerpt_clipped(whole_file_excerpt("a.py", "\n".join(lines[:5])).text)


# --- Stage 4 P2: a test's line is its declaration's, not the blank before --


def test_reported_line_is_the_declaration_line_not_the_preceding_blank():
    text = "def test_ok():\n    assert 1\n\n\ndef test_empty():\n    pass\n"
    found = metric("tests_without_assertions_share", {"tests/test_p.py": text})
    assert "tests/test_p.py:5" in found.derivation
    assert "tests/test_p.py:4" not in found.derivation


def test_a_clipped_excerpt_holding_only_a_cut_test_abstains():
    text = "\n" * 191 + "def test_last():\n" + "    x = 1\n" * 15 + "    assert x\n"
    (found,) = compute_metrics(_clipped_pack(text), curated_metric_tables()).by_name(
        "tests_without_assertions_share"
    )
    assert found.abstained
    assert "cut by the excerpt line limit" in found.outcome.reason
