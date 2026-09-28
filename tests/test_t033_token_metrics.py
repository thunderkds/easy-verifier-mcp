"""T033 - registry-driven token metrics: approximate CCN, imports, fan-in, cycles.

Every CCN fixture below is hand-counted; the per-line comments in the expected
tables give the count. Sabotage pairs vary exactly one predicate -- the
delimiters, the line length, one import line, the dimension, the truncation
flag -- and show the metric move with it.
"""

from __future__ import annotations

import ast
import dataclasses
import re
from pathlib import Path
from urllib.parse import urlsplit

import pytest

from easy_verifier.core.metric_tables import curated_metric_tables, metric_tables
from easy_verifier.core.metrics import allowed_refs, compute_metrics
from easy_verifier.core.models import EvidencePack, Excerpt, TruncationRecord
from easy_verifier.core.registry import load_registry
from easy_verifier.core.roles import GENERIC_PATTERNS, _registry
from easy_verifier.core.tokens import (
    approximate_ccn,
    import_statements,
    language_syntax,
    strip,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
STRUCTURE_FIELDS = (
    "branch_keywords",
    "comment_delimiters",
    "string_delimiters",
    "function_start",
    "import_syntax",
)
NEW_METRICS = (
    "functions_over_ccn_10_share",
    "max_function_ccn",
    "top_level_import_cycles",
    "max_fan_in_changed",
)
CCN_LABEL = "approximate CCN (lizard-style), McCabe 1976"


def syntax_for(suffix):
    return curated_metric_tables().syntax[suffix]


def without_delimiters(syntax):
    """The same language with no comment/string delimiters: nothing stripped."""
    return language_syntax(
        syntax.language,
        comments=[],
        strings=["\x00"],  # an opener that never occurs
        branch=syntax.branch,
        function_start=syntax.function_start,
        imports=syntax.imports,
    )


# ---------------------------------------------------------------------------
# AC #1 - the five fields exist for all 9 languages, each cited
# ---------------------------------------------------------------------------


def test_every_curated_language_carries_every_structure_field_cited():
    registry = _registry()
    assert registry.warnings == ()
    assert len(registry.languages) == 9
    for name, entry in registry.languages.items():
        for field in STRUCTURE_FIELDS:
            cited = entry.fields.get(field, ())
            assert cited, f"{name} lacks {field}"
            for item in cited:
                assert urlsplit(item.citation_url).scheme == "https"
                assert item.source_tag == "curated"
        assert name in {s.language for s in curated_metric_tables().syntax.values()}


def _entry(root, body):
    (root / "demo.toml").write_text(
        '[[manifests]]\nvalue = ["demo.cfg"]\n'
        'citation_url = "https://example.org/"\nsource_tag = "curated"\n' + body
    )
    return load_registry(root, known_roles=GENERIC_PATTERNS)


def _cited(field, value):
    return (
        f"\n[[{field}]]\nvalue = [{value}]\n"
        'citation_url = "https://example.org/x"\nsource_tag = "curated"\n'
    )


@pytest.mark.parametrize(
    ("value", "accepted"),
    [('"//", "/* */"', True), ('"a b c"', False), ('"\\\\"', False)],
)
def test_delimiter_shape_is_validated(tmp_path, value, accepted):
    registry = _entry(tmp_path, _cited("comment_delimiters", value))
    assert ("demo" in registry.languages) is accepted, registry.warnings


def test_path_checks_still_apply_outside_delimiter_fields(tmp_path):
    """Sabotage: ``//`` is only accepted because delimiters are exempt."""
    registry = _entry(tmp_path, _cited("roles.lint-config", '"//x"'))
    assert "demo" not in registry.languages
    assert "repository-relative" in registry.warnings[0]


def test_language_missing_one_structure_field_gets_no_syntax():
    registry = _registry()
    python = registry.languages["python"]
    fields = {k: v for k, v in python.fields.items() if k != "function_start"}
    broken = dataclasses.replace(
        registry,
        languages={
            **registry.languages,
            "python": dataclasses.replace(python, fields=fields),
        },
    )
    assert ".py" in metric_tables(registry).syntax
    assert ".py" not in metric_tables(broken).syntax


def test_delimiters_are_literal_never_regex():
    syntax = language_syntax(
        "x",
        comments=[".*"],
        strings=["("],
        branch=re.compile(r"\bif\b"),
        function_start=re.compile(r"\bdef\b"),
        imports=re.compile(r"\bimport\b"),
    )
    assert strip("abc if x", syntax) == "abc if x"
    assert strip("a .* if", syntax) == "a" + " " * 6


# ---------------------------------------------------------------------------
# AC #2 / #4 - hand-counted CCN per language, keywords in strings/comments
# ---------------------------------------------------------------------------

PYTHON = '''
def classify(x, y):
    """if for while and or"""
    # if while for
    s = "if and or"
    if x > 0 and y > 0:
        return s
    elif x < 0:
        pass
    for i in range(y):
        while i:
            i -= 1
    try:
        pass
    except ValueError:
        pass
    return 'or' if x else y
'''  # if+and 2, elif 1, for 1, while 1, except 1, if 1 -> 7 -> CCN 8

JS = """
function check(a, b) {
  // if (a) for while
  const s = "if (a && b)";
  const t = `case ${a} || b`;
  /* while (x) { if } */
  if (a && b) {
    return s;
  } else if (a || t) {
    return t;
  }
  for (let i = 0; i < 3; i++) {}
  switch (a) {
    case 1:
      break;
    default:
      break;
  }
  try { x(); } catch (e) { }
  return 'while';
}
"""  # if+&& 2, if+|| 2, for 1, case 1, catch 1 -> 7 -> CCN 8

GO = """
func Check(a int, b bool) int {
	// if for case
	s := "if && ||"
	r := `for
case`
	if a > 0 && b {
		return 1
	}
	for i := 0; i < a; i++ {
	}
	switch a {
	case 1:
		return 2
	case 2, 3:
		return 3
	}
	_ = s + r + string('"')
	return 0
}
"""  # if+&& 2, for 1, case 1, case 1 -> 5 -> CCN 6

JAVA = '''
public class Demo {
    public static int check(int a, boolean b) {
        String s = "if (a && b) while";
        String t = """
            for case catch
            """;
        char c = '"';
        // if || case
        if (a > 0 && b) {
            return 1;
        }
        while (a > 10) { a--; }
        try {
            a = a / 0;
        } catch (ArithmeticException e) {
            a = 0;
        }
        return a > 5 || b ? 1 : 0;
    }
}
'''  # if+&& 2, while 1, catch 1, || 1 -> 5 -> CCN 6

CSHARP = '''
public class Demo
{
    public static int Check(int a, bool b)
    {
        var s = "if (a && b) foreach";
        var r = """
            while case catch
            """;
        // for || if
        /* catch */
        if (a > 0 && b)
        {
            return 1;
        }
        foreach (var x in new[] { 1 })
        {
            a += x;
        }
        switch (a)
        {
            case 1:
                return 2;
        }
        return a;
    }
}
'''  # if+&& 2, foreach 1, case 1 -> 4 -> CCN 5

KOTLIN = '''
fun check(a: Int, b: Boolean): Int {
    val s = "if (a && b) while"
    val t = """
        for catch ||
    """
    val c = '"'
    // if for
    val f = { x: Int -> if (x > 0) 1 else 0 }
    if (a > 0 && b) {
        return 1
    }
    for (i in 0..a) { }
    try {
        println(a)
    } catch (e: Exception) { }
    return if (a > 1 || b) 1 else 0
}
'''  # lambda if 1 (a lambda is not a function), if+&& 2, for 1, catch 1,
# if+|| 2 -> 7 -> CCN 8

PHP = """<?php
function check($a, $b)
{
    $s = "if ($a && $b) foreach";
    $t = 'while or and';
    # if for
    // case catch
    /* elseif */
    if ($a > 0 && $b) {
        return 1;
    } elseif ($a < 0 or $b) {
        return 2;
    }
    foreach ([1, 2] as $x) {
        $a += $x;
    }
    try {
        throw new Exception();
    } catch (Exception $e) {
        $a = 0;
    }
    return $a;
}
"""  # if+&& 2, elseif+or 2, foreach 1, catch 1 -> 6 -> CCN 7

RUBY = """
def check(a, b)
  s = "if a && b"
  t = 'unless while'
  # if elsif
  [1, 2].each do |x|
    a += x if x > 1
  end
  if a > 0 && b
    1
  elsif a < 0
    2
  end
  a -= 1 until a < 5
  begin
    raise "boom"
  rescue StandardError
    0
  end
end
"""  # block if 1 (a block is not a function), if+&& 2, elsif 1, until 1,
# rescue 1 -> 6 -> CCN 7

RUST = """
fn check(a: i32, b: bool) -> i32 {
    let s = "if a && b while";
    // for match =>
    /* if */
    let label: &'static str = "x";
    if a > 0 && b {
        return 1;
    }
    let r = match a {
        1 => 10,
        2 | 3 => 20,
        _ => 0,
    };
    for i in 0..a {
        let _ = i;
    }
    while false {}
    r + s.len() as i32 + label.len() as i32
}
"""  # if+&& 2, three match arms 3, for 1, while 1 -> 7 -> CCN 8

FIXTURES = [
    (".py", PYTHON, 8),
    (".js", JS, 8),
    (".go", GO, 6),
    (".java", JAVA, 6),
    (".cs", CSHARP, 5),
    (".kt", KOTLIN, 8),
    (".php", PHP, 7),
    (".rb", RUBY, 7),
    (".rs", RUST, 8),
]


@pytest.mark.parametrize(("suffix", "text", "expected"), FIXTURES)
def test_hand_counted_ccn_per_language(suffix, text, expected):
    (function,) = approximate_ccn(text, syntax_for(suffix))
    assert function.ccn == expected


@pytest.mark.parametrize(("suffix", "text", "expected"), FIXTURES)
def test_keywords_in_strings_and_comments_are_what_stripping_removes(
    suffix, text, expected
):
    """Sabotage: the same text with the delimiters withheld counts more."""
    unstripped = approximate_ccn(text, without_delimiters(syntax_for(suffix)))
    assert max(f.ccn for f in unstripped) > expected


def test_success_criterion_python_if_elif_for_and_is_5():
    text = (
        "def f(a, b, xs):\n    if a:\n        return 1\n"
        "    elif b and a:\n        return 2\n    for x in xs:\n        pass\n"
    )
    assert [f.ccn for f in approximate_ccn(text, syntax_for(".py"))] == [5]


@pytest.mark.parametrize(("line", "expected"), [(r'"a \" if (x)"', 1), ('"a" + if', 2)])
def test_an_escaped_quote_does_not_end_the_string(line, expected):
    text = "function f(x) {\n  const s = " + line + ";\n}\n"
    assert [f.ccn for f in approximate_ccn(text, syntax_for(".js"))] == [expected]


@pytest.mark.parametrize(("quoted", "expected"), [(True, 1), (False, 2)])
def test_success_criterion_js_if_inside_a_string_is_not_counted(quoted, expected):
    line = '  const s = "if (x) {}";' if quoted else "  if (x) {}"
    text = "function f(x) {\n" + line + "\n}\n"
    assert [f.ccn for f in approximate_ccn(text, syntax_for(".js"))] == [expected]


def test_nested_function_decisions_are_not_counted_in_the_parent():
    text = (
        "def outer(a):\n    if a:\n        pass\n\n"
        "    def inner(b):\n        if b and a:\n            return 1\n"
        "        return 0\n\n    for x in a:\n        pass\n    return inner\n"
    )
    assert [(f.line, f.ccn) for f in approximate_ccn(text, syntax_for(".py"))] == [
        (1, 3),
        (5, 3),
    ]


@pytest.mark.parametrize(
    ("suffix", "text", "functions"),
    [
        (".js", "const f = (x) => {\n  if (x) {}\n};\n", 1),
        (".js", "class A {\n  m(x) {\n    if (x) {}\n  }\n}\n", 0),
        (".rb", "[1].each do |x|\n  x if x\nend\n", 0),
        (".kt", "val f = { x: Int ->\n    if (x > 0) 1 else 0\n}\n", 0),
        (".java", "interface I {\n    void f(int a);\n}\n", 0),
        (".java", "class C {\n    void f(int a) {\n    }\n}\n", 1),
    ],
)
def test_what_counts_as_a_function_per_language(suffix, text, functions):
    assert len(approximate_ccn(text, syntax_for(suffix))) == functions


@pytest.mark.parametrize(
    ("width", "expected"), [(500, 2), (501, 1)]  # the documented cap, literal
)
def test_lines_over_the_length_cap_are_ignored(width, expected):
    line = "    x = 1 if a else 0"
    text = "def f(a):\n" + line + " " * (width - len(line)) + "\n    return x\n"
    assert [f.ccn for f in approximate_ccn(text, syntax_for(".py"))] == [expected]


def test_wrapped_signature_does_not_end_the_function():
    text = "def f(\n    a,\n):\n    if a:\n        return 1\n"
    assert [f.ccn for f in approximate_ccn(text, syntax_for(".py"))] == [2]


def test_import_statements_span_open_brackets_and_skip_strings():
    text = 'import (\n\t"fmt"\n\t"example.com/m/store"\n)\nvar s = "import x"\n'
    ((line, statement),) = import_statements(text, syntax_for(".go"))
    assert line == 1 and "example.com/m/store" in statement


# ---------------------------------------------------------------------------
# AC #3 / #5 - the metrics over a pack
# ---------------------------------------------------------------------------


def pack(files, *, dimension="architecture", truncated=False, starts=None):
    """``files`` maps path -> text; each becomes one whole-file excerpt."""
    return EvidencePack(
        dimension=dimension,
        mode="kit-aware",
        scope="worktree",
        files_read=tuple(files),
        excerpts=tuple(
            Excerpt(path, first, first + len(text.splitlines()) - 1, text)
            for path, text in files.items()
            for first in [(starts or {}).get(path, 1)]
        ),
        sources_sought=("x",),
        sources_found=("x",),
        sources_missing=(),
        coverage_score=1.0,
        truncated=truncated,
        omitted_count=5 if truncated else 0,
        truncation=TruncationRecord(
            truncated=truncated, omitted_count=5 if truncated else 0
        ),
    )


def metric(evidence, name):
    (found,) = compute_metrics(evidence, curated_metric_tables()).by_name(name)
    return found


BRANCHY = "def big(a):\n" + "".join(
    f"    if a == {i}:\n        pass\n" for i in range(11)
)
CYCLE = {
    "src/pkg/core/a.py": "from pkg.api import handler\n\ndef a():\n    return 1\n",
    "src/pkg/api/handler.py": "from pkg.core import a\n",
    "src/pkg/util/tools.py": "from pkg.core import a\n",
}


def test_ccn_metrics_over_a_pack_cite_evidence_and_carry_the_label():
    files = {"src/app/big.py": BRANCHY, "src/app/small.py": "def s():\n    return 1\n"}
    evidence = pack(files)
    share = metric(evidence, "functions_over_ccn_10_share")
    top = metric(evidence, "max_function_ccn")
    assert share.numeric_value == 0.5
    assert top.numeric_value == 12
    assert top.computed_from == ("src/app/big.py:1-23",)
    for found in (share, top):
        assert CCN_LABEL in found.derivation
        assert set(found.computed_from) <= allowed_refs(evidence)


def test_test_files_are_not_counted_as_observed_functions():
    evidence = pack({"tests/test_big.py": BRANCHY})
    assert metric(evidence, "max_function_ccn").abstained


@pytest.mark.parametrize(
    ("core_line", "expected"),
    [
        ("from pkg.api import handler", 1),
        ("import os", 0),
        ('x = "from pkg.api import handler"', 0),
    ],
)
def test_top_level_import_cycles_vary_with_one_import_line(core_line, expected):
    files = dict(CYCLE)
    files["src/pkg/core/a.py"] = core_line + "\n\ndef a():\n    return 1\n"
    found = metric(pack(files), "top_level_import_cycles")
    assert found.numeric_value == expected
    if expected:
        assert "api <-> core" in found.derivation


def test_cycles_abstain_without_any_import_statement():
    found = metric(
        pack({"src/a.py": "def a():\n    return 1\n"}), "top_level_import_cycles"
    )
    assert found.abstained and "no import statement" in found.abstention.reason


FAN_IN = {
    "src/app/alpha.py": "from app import beta\n",
    "src/app/gamma.py": "from app import beta\n",
    "tests/test_beta.py": "from app.beta import helper\n",
    "src/app/beta.py": "def helper(x):\n    return x\n",
}


@pytest.mark.parametrize(
    ("dimension", "gamma_line", "expected"),
    [
        ("blast-radius", "from app import beta", 3),
        ("blast-radius", "    return beta.helper(3)", 2),
        ("architecture", "from app import beta", None),
    ],
)
def test_max_fan_in_changed(dimension, gamma_line, expected):
    files = dict(FAN_IN)
    files["src/app/gamma.py"] = gamma_line + "\n"
    found = metric(pack(files, dimension=dimension), "max_fan_in_changed")
    if expected is None:
        assert found.abstained and "blast-radius" in found.abstention.reason
    else:
        assert found.numeric_value == expected
        assert "src/app/beta.py" in found.computed_from


@pytest.mark.parametrize("truncated", [False, True])
def test_truncation_abstains_whole_set_and_keeps_max_function_ccn(truncated):
    files = {**CYCLE, **FAN_IN, "src/app/big.py": BRANCHY}
    evidence = pack(files, dimension="blast-radius", truncated=truncated)
    found = {name: metric(evidence, name) for name in NEW_METRICS}
    assert found["max_function_ccn"].numeric_value == 12
    for name in (
        "functions_over_ccn_10_share",
        "top_level_import_cycles",
        "max_fan_in_changed",
    ):
        assert found[name].abstained is truncated, name


def test_excerpt_offsets_are_absolute_file_lines():
    evidence = pack({"src/app/big.py": BRANCHY}, starts={"src/app/big.py": 40})
    assert "src/app/big.py:40" in metric(evidence, "max_function_ccn").derivation


def test_tokens_module_imports_nothing_that_reads_the_filesystem():
    tree = ast.parse((REPO_ROOT / "src/easy_verifier/core/tokens.py").read_text())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add("." * node.level + (node.module or ""))
    assert imported == {"__future__", "re", "collections.abc", "dataclasses"}
