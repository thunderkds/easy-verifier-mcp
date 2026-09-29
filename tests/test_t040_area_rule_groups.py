"""T040 - area rule-group metrics inside existing dimensions (FR-051, FR-043).

Metrics for #16 (tests without assertions, skipped tests, network calls in
unit tests), #17 (type-escape density) and #31 (TODO/FIXME without a ticket
reference). Language syntax (skip markers, network calls, type escapes, type
stub names) is registry data; each test pins a predicate against its twin, so
a metric that ignored the predicate would fail here.
"""

from __future__ import annotations

import pytest

from easy_verifier.core.metric_tables import curated_metric_tables
from easy_verifier.core.metrics import (
    EVIDENCE_LOCAL,
    METRIC_DEFINITIONS,
    WHOLE_SET,
    compute_metrics,
)
from easy_verifier.core.models import EvidencePack, Excerpt, TruncationRecord
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
