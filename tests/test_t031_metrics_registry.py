"""T031 - metrics read test naming, declarations and assertions from the registry.

Every pack is hand-built (as in ``test_metrics.py``); the language tables come
from the curated reference registry, or from a copy of it under ``tmp_path``
when a test needs to prove that the *data* is what drives the result.
"""

from __future__ import annotations

import re
from importlib import resources
from pathlib import Path

import pytest

from easy_verifier.core.metric_tables import curated_metric_tables, metric_tables
from easy_verifier.core.metrics import compute_metrics
from easy_verifier.core.models import EvidencePack, Excerpt
from easy_verifier.core.registry import load_registry
from easy_verifier.core.roles import GENERIC_PATTERNS

REPO_ROOT = Path(__file__).resolve().parents[1]
CURATED_DIR = resources.files("easy_verifier") / "registry" / "curated"
URL = "https://example.org/docs"


def _pack(files, excerpts=()) -> EvidencePack:
    return EvidencePack(
        dimension="test-strategy",
        mode="standalone",
        scope="project",
        files_read=tuple(files),
        excerpts=tuple(excerpts),
        sources_sought=("test layout",),
        sources_found=("test layout",),
        sources_missing=(),
        coverage_score=1.0,
        truncated=False,
        omitted_count=0,
        redactions=(),
    )


def _value(metrics, name):
    (metric,) = metrics.by_name(name)
    return "abstained" if metric.abstained else metric.numeric_value


def _measure(files, excerpts=(), tables=None):
    metrics = compute_metrics(_pack(files, excerpts), tables or curated_metric_tables())
    return {
        name: _value(metrics, name)
        for name in (
            "source_files_without_covering_test",
            "assertions_observed",
            "assertion_density_per_test",
            "source_file_share",
        )
    }


def _registry_copy(tmp_path: Path, edit=None) -> Path:
    target = tmp_path / "curated"
    target.mkdir(parents=True)
    for item in CURATED_DIR.iterdir():
        if item.name.endswith(".toml"):
            (target / item.name).write_bytes(item.read_bytes())
    if edit:
        edit(target)
    return target


def _tables_from(directory: Path, **kwargs):
    registry = load_registry(directory, known_roles=GENERIC_PATTERNS)
    assert registry.warnings == (), registry.warnings
    return metric_tables(registry, **kwargs)


# ---------------------------------------------------------------------------
# Success criteria 1 / AC #3 - idiomatic Go
# ---------------------------------------------------------------------------

GO_TEST = """func TestAdd(t *testing.T) {
    if Add(1, 1) != 2 {
        t.Errorf("want 2, got %d", Add(1, 1))
    }
    if Add(0, 0) != 0 {
        t.Fatalf("want 0")
    }
}
"""


def test_go_t_errorf_and_t_fatalf_count_as_assertions_and_calc_go_is_covered():
    result = _measure(
        ["go.mod", "calc.go", "calc_test.go"],
        [Excerpt("calc_test.go", 1, 8, GO_TEST)],
    )
    assert result["assertions_observed"] == 2
    assert result["assertion_density_per_test"] == 2.0
    assert result["source_files_without_covering_test"] == 0


def test_go_same_package_rule_is_preserved():
    """A same-named `_test.go` in another directory is another package.

    `src/calc.go` and `calc_test.go` share a project boundary (`src/` is a
    layout segment), so only the same-directory rule can tell them apart."""
    result = _measure(["go.mod", "src/calc.go", "calc_test.go"])
    assert result["source_files_without_covering_test"] == 1
    # Sabotage pair: in the same directory the same names DO match.
    assert (
        _measure(["go.mod", "calc.go", "calc_test.go"])[
            "source_files_without_covering_test"
        ]
        == 0
    )


def test_t_error_is_not_double_counted_inside_t_errorf():
    """Word boundaries: `t.Error` must not also match the `t.Error` in `t.Errorf`."""
    text = 'func TestX(t *testing.T) {\n    t.Errorf("a")\n    t.Error("b")\n}\n'
    result = _measure(["x.go", "x_test.go"], [Excerpt("x_test.go", 1, 4, text)])
    assert result["assertions_observed"] == 2


# ---------------------------------------------------------------------------
# Success criteria 2 / AC #2 - Kotlin and PHP correspondence
# ---------------------------------------------------------------------------


def test_kotlin_footest_covers_foo():
    result = _measure(["build.gradle.kts", "Foo.kt", "src/test/kotlin/FooTest.kt"])
    assert result["source_files_without_covering_test"] == 0


def test_php_footest_covers_foo_and_test_methods_are_declarations():
    body = (
        "final class FooTest extends TestCase {\n"
        "    public function testAdds(): void {\n"
        "        $this->assertSame(2, add(1, 1));\n"
        "    }\n"
        "    #[Test]\n"
        "    public function subtracts(): void {\n"
        "        $this->assertSame(0, sub(1, 1));\n"
        "    }\n"
        "}\n"
    )
    result = _measure(
        ["composer.json", "src/Foo.php", "tests/FooTest.php"],
        [Excerpt("tests/FooTest.php", 1, 9, body)],
    )
    assert result["source_files_without_covering_test"] == 0
    assert result["assertion_density_per_test"] == 1.0


def test_kotlin_correspondence_comes_from_the_registry_not_from_code(tmp_path):
    """Sabotage: delete Kotlin's `test_candidates` from a registry copy and the
    same fixture is uncovered again - the data is what drives the result."""

    def drop_candidates(directory: Path) -> None:
        path = directory / "kotlin.toml"
        text = path.read_text(encoding="utf-8")
        start = text.index("[[test_candidates]]")
        end = text.index("[[", start + 2)
        path.write_text(text[:start] + text[end:], encoding="utf-8")

    files = ["build.gradle.kts", "Foo.kt", "src/test/kotlin/FooTest.kt"]
    intact = _tables_from(_registry_copy(tmp_path / "a"))
    broken = _tables_from(_registry_copy(tmp_path / "b", drop_candidates))
    assert _measure(files, tables=intact)["source_files_without_covering_test"] == 0
    assert _measure(files, tables=broken)["source_files_without_covering_test"] == 1


# ---------------------------------------------------------------------------
# AC #3 - RSpec and C# declarations
# ---------------------------------------------------------------------------


def test_rspec_it_do_counts_as_a_test_declaration():
    body = (
        'RSpec.describe Calc do\n  it "adds" do\n    expect(add(1, 1)).to eq(2)\n'
        "  end\n  it 'subtracts' do\n    expect(sub(1, 1)).to eq(0)\n  end\nend\n"
    )
    result = _measure(
        ["Gemfile", "lib/calc.rb", "spec/calc_spec.rb"],
        [Excerpt("spec/calc_spec.rb", 1, 8, body)],
    )
    assert result["assertion_density_per_test"] == 1.0


@pytest.mark.parametrize("attribute", ["[Fact]", "[Test]", "[TestMethod]"])
def test_csharp_test_attributes_count_as_declarations(attribute):
    body = (
        f"    {attribute}\n    public void Adds() {{\n"
        "        Assert.Equal(2, Calc.Add(1, 1));\n    }\n"
    )
    result = _measure(
        ["Calc.csproj", "src/Calc.cs", "tests/CalcTests.cs"],
        [Excerpt("tests/CalcTests.cs", 1, 4, body)],
    )
    assert result["assertion_density_per_test"] == 1.0


def test_csharp_attribute_prefixes_do_not_overlap():
    """`[Test` must not also match `[TestMethod]`, nor `[Fact` a `[Factory]`."""
    body = (
        "    [TestMethod]\n    [Factory]\n    public void X() { Assert.True(true); }\n"
    )
    result = _measure(
        ["tests/XTests.cs", "src/X.cs"], [Excerpt("tests/XTests.cs", 1, 3, body)]
    )
    assert result["assertion_density_per_test"] == 1.0


# ---------------------------------------------------------------------------
# AC #1 - no hard-coded language table remains in core/metrics.py
# ---------------------------------------------------------------------------


def test_metrics_module_holds_no_language_table():
    source = (REPO_ROOT / "src/easy_verifier/core/metrics.py").read_text()
    for former in (
        "_SOURCE_SUFFIXES",
        "_TEST_NAME_PATTERNS",
        "_ASSERTION_PATTERN",
        "_TEST_DECLARATION_PATTERNS",
    ):
        assert former not in source, former
    extensions = re.findall(
        r"[\"']\.(?:py|go|rs|java|kt|php|rb|cs|jsx?|tsx?)[\"']", source
    )
    assert extensions == []
    assert "def test" not in source and "@Test" not in source


def test_every_curated_language_declares_the_metric_fields():
    registry = load_registry(known_roles=GENERIC_PATTERNS)
    for name, entry in registry.languages.items():
        for field in ("source_extensions", "test_name_patterns", "assertions"):
            assert entry.fields.get(field), (name, field)
        for cited in entry.fields.get("test_declarations", ()):
            assert cited.citation_url.startswith("https://"), name


# ---------------------------------------------------------------------------
# AC #4 - languages outside the nine: the generic set, and the Linguist seam
# ---------------------------------------------------------------------------


def test_extensions_outside_the_nine_are_not_source_without_extra_data():
    assert _measure(["main.c", "util.c"])["source_file_share"] == 0.0


def test_extra_source_extensions_seam_makes_them_source(tmp_path):
    tables = metric_tables(
        load_registry(known_roles=GENERIC_PATTERNS), extra_source_extensions=(".c",)
    )
    result = _measure(["main.c", "util.c", "tests/test_main.c"], tables=tables)
    assert result["source_file_share"] == pytest.approx(2 / 3)
    # Directory evidence still classifies the test; no candidate rule for C,
    # so both sources stay uncovered rather than being guessed covered.
    assert result["source_files_without_covering_test"] == 2


def test_an_empty_registry_does_not_crash(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    tables = metric_tables(load_registry(empty, known_roles=GENERIC_PATTERNS))
    result = _measure(
        ["src/widget.py", "tests/test_widget.py"],
        [Excerpt("tests/test_widget.py", 1, 2, "def test_a():\n    assert 1\n")],
        tables=tables,
    )
    assert result["source_file_share"] == 0.0
    assert result["source_files_without_covering_test"] == "abstained"
    assert result["assertions_observed"] == "abstained"


# ---------------------------------------------------------------------------
# AC #5 - the former Python/JS/Java/Rust behaviour, pinned against an oracle
# ---------------------------------------------------------------------------

# The tables metrics.py held before T031, copied verbatim as the oracle.
_FORMER_NAMES = (
    re.compile(r"^test_.+\.py$"),
    re.compile(r"^.+_test\.py$"),
    re.compile(r"^.+_test\.go$"),
    re.compile(r"^.+_test\.rs$"),
    re.compile(r"^.+_spec\.rb$"),
    re.compile(r"^test_.+\.rb$"),
    re.compile(r"^.+\.(test|spec)\.[cm]?[jt]sx?$"),
    re.compile(r"^.+Test\.java$"),
    re.compile(r"^Test.+\.java$"),
    re.compile(r"^.+Tests?\.cs$"),
)
_FORMER_ASSERTIONS = re.compile(
    r"(?:\bassert\b|\bassert!|\bassert_[a-z_]+\b|\bassert[A-Z]\w*"
    r"|\bexpect\s*\(|\.should\b|\bAssert\.\w+)"
)

NAMES = [
    "test_a.py",
    "a_test.py",
    "test_.py",
    "a.py",
    "conftest.py",
    "tester.py",
    "a.test.js",
    "a.spec.ts",
    "a.test.tsx",
    "a.spec.jsx",
    "a_test.js",
    "a.js",
    "ATest.java",
    "TestA.java",
    "A.java",
    "ATests.java",
    "Testing.java",
    "a_test.rs",
    "lib.rs",
    "a_test.go",
    "a.go",
    "a_spec.rb",
    "test_a.rb",
    "ATest.cs",
    "ATests.cs",
    "A.cs",
]

ASSERTION_TEXTS = [
    "assert x == 1\nassert(y)",
    "self.assertEqual(a, b)\nself.assertTrue(c)\nmock.assert_called_once_with(1)",
    "assertion = 1\nasserts = 2  # the word assertion is not an assertion",
    "assert!(ok);\nassert_eq!(a, b);\nassert_ne!(a, b);",
    "expect(a).toBe(1)\nexpect (b).toEqual(2)\nx.should.equal(3)",
    "Assert.Equal(1, x);\nAssertions.assertEquals(1, x);\nassertThat(x).isEqualTo(1);",
]


@pytest.mark.parametrize("name", NAMES)
def test_test_name_classification_matches_the_former_table(name):
    tables = curated_metric_tables()
    former = any(pattern.match(name) for pattern in _FORMER_NAMES)
    assert any(pattern.match(name) for pattern in tables.test_name_patterns) is former


@pytest.mark.parametrize("text", ASSERTION_TEXTS)
def test_assertion_counts_match_the_former_pattern(text):
    tables = curated_metric_tables()
    assert len(tables.assertions.findall(text)) == len(_FORMER_ASSERTIONS.findall(text))


def test_source_suffixes_match_the_former_set():
    assert curated_metric_tables().source_suffixes == frozenset(
        {
            ".cs",
            ".go",
            ".java",
            ".js",
            ".jsx",
            ".kt",
            ".php",
            ".py",
            ".rb",
            ".rs",
            ".ts",
            ".tsx",
        }
    )


# ---------------------------------------------------------------------------
# Registry intake - the new fields are validated like every other field
# ---------------------------------------------------------------------------


def _cited(values):
    quoted = ", ".join(f"'{value}'" for value in values)
    return f'value = [{quoted}]\ncitation_url = "{URL}"\nsource_tag = "curated"\n'


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_extensions", "py"),
        ("source_extensions", ".p y"),
        ("test_name_patterns", "tests/test_*.py"),
        ("test_candidates", "test_x.py"),
        ("test_candidates", "sub/{stem}_test{ext}"),
    ],
)
def test_malformed_metric_field_values_reject_the_entry(tmp_path, field, value):
    (tmp_path / "odd.toml").write_text(
        "[[manifests]]\n" + _cited(["odd.mod"]) + f"\n[[{field}]]\n" + _cited([value]),
        encoding="utf-8",
    )
    registry = load_registry(tmp_path, known_roles=GENERIC_PATTERNS)
    assert "odd" not in registry.languages
    (warning,) = registry.warnings
    assert field in warning


def test_a_framework_adds_metric_fields_to_its_language(tmp_path):
    (tmp_path / "base.toml").write_text(
        "[[manifests]]\n"
        + _cited(["base.mod"])
        + "\n[[assertions]]\n"
        + _cited(["check"]),
        encoding="utf-8",
    )
    (tmp_path / "addon.toml").write_text(
        'extends = "base"\n\n[[assertions]]\n' + _cited(["verify"]),
        encoding="utf-8",
    )
    from easy_verifier.core.registry import merge

    registry = load_registry(tmp_path, known_roles=GENERIC_PATTERNS)
    assert registry.warnings == ()
    merged = merge(registry.languages["base"], [registry.frameworks["addon"]])
    values = [v for field in merged.fields["assertions"] for v in field.value]
    assert values == ["check", "verify"]


# ---------------------------------------------------------------------------
# The token syntax cannot inject regex
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("token", "matches", "misses"),
    [
        ("assert<A-Z>*", "self.assertEqual(a)", "assertion = 1"),
        ("t.Errorf", "t.Errorf(x)", "tXErrorf(x)"),
        ("(.+)", "call (.+) literal", "call abc"),
        ("<Z-A>x", "<Z-A>x", "Bx"),
        ("a**b", "a_b", "a b"),
        ("def test*", "def   test_it", "deftest_it"),
    ],
)
def test_token_regex_is_literal_except_for_its_own_syntax(token, matches, misses):
    from easy_verifier.core.metric_tables import token_regex

    pattern = re.compile(token_regex(token))
    assert pattern.search(matches), (token, pattern.pattern)
    assert not pattern.search(misses), (token, pattern.pattern)
    assert r"\w*\w*" not in pattern.pattern
