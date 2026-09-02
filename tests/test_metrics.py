"""T019 - `core/metrics.py`: measured facts computed over the evidence pack.

Every pack here is hand-built. Running the real pipeline to make a fixture
would turn these into tests of the dimensions, and would make the truncation
and citation properties depend on whatever the byte budget happened to do.

Several tests below are written as *sabotage pairs*: the same assertion is
driven with the predicate it depends on hardwired to both extremes, so a test
that could not fail is visible as one that passes under both. This project has
shipped that green-test-that-cannot-fail five times (T005, T008, T010, T018).
"""

from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path

import pytest

from easy_verifier.core.metrics import (
    EVIDENCE_LOCAL,
    FAMILIES,
    METRIC_DEFINITIONS,
    WHOLE_SET,
    Metric,
    MetricAbstained,
    MetricAbstention,
    MetricCitationError,
    allowed_refs,
    check_citations,
    compute_metrics,
)
from easy_verifier.core.models import (
    CombinedPack,
    CoverageSummary,
    DimensionSlot,
    EvidencePack,
    Excerpt,
    RedactionHit,
    TruncationRecord,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

TEST_BODY = """
def test_one():
    assert widget(1) == 2
    assert widget(0) == 0


def test_two():
    assert widget(-1) is None
"""

SOURCE_BODY = """
def widget(value):
    return value * 2
"""


def make_pack(
    *,
    dimension="test-strategy",
    files_read=("src/widget.py", "tests/test_widget.py"),
    excerpts=None,
    sources_sought=("test layout", "test framework"),
    sources_found=("test layout",),
    coverage_score=0.5,
    truncated=False,
    omitted_count=0,
    redactions=(),
    truncation="mirror",
):
    if excerpts is None:
        excerpts = (
            Excerpt("src/widget.py", 1, 3, SOURCE_BODY),
            Excerpt("tests/test_widget.py", 1, 7, TEST_BODY),
        )
    if truncation == "mirror":
        truncation = TruncationRecord(truncated=truncated, omitted_count=omitted_count)
    return EvidencePack(
        dimension=dimension,
        mode="kit-aware",
        scope="project",
        files_read=tuple(files_read),
        excerpts=tuple(excerpts),
        sources_sought=tuple(sources_sought),
        sources_found=tuple(sources_found),
        sources_missing=(),
        coverage_score=coverage_score,
        truncated=truncated,
        omitted_count=omitted_count,
        redactions=tuple(redactions),
        truncation=truncation,
    )


def named(metric_set, name):
    (metric,) = metric_set.by_name(name)
    return metric


# ---------------------------------------------------------------------------
# AC #1 - shape
# ---------------------------------------------------------------------------


def test_compute_metrics_returns_metrics_with_name_kind_and_citations():
    metrics = compute_metrics(make_pack())

    assert len(metrics) == len(METRIC_DEFINITIONS)
    for metric in metrics:
        assert isinstance(metric, Metric)
        assert metric.name
        assert metric.kind in {WHOLE_SET, EVIDENCE_LOCAL}
        assert metric.dimension == "test-strategy"
        assert isinstance(metric.outcome, (int, float, MetricAbstention))
        assert metric.derivation


def test_metric_names_are_unique_per_dimension():
    names = [d.name for d in METRIC_DEFINITIONS]
    assert len(names) == len(set(names))


# ---------------------------------------------------------------------------
# AC #2 - the module structurally cannot read a file
# ---------------------------------------------------------------------------


def test_metrics_module_imports_nothing_that_reads_the_filesystem():
    source = (REPO_ROOT / "src/easy_verifier/core/metrics.py").read_text()
    tree = ast.parse(source)

    imported_modules = set()
    imported_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported_modules.add("." * node.level + (node.module or ""))
            imported_names.update(alias.name for alias in node.names)

    # Whitelist, not blacklist: a blacklist passes for any I/O module nobody
    # thought to name.
    assert imported_modules == {
        "__future__",
        "json",
        "re",
        "collections.abc",
        "dataclasses",
        "pathlib",
        ".models",
    }
    assert "Path" not in imported_names, "PurePosixPath is pure; Path is not"
    assert "RepoContext" not in imported_names

    called = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    attributes = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert "open" not in called
    assert not {a for a in attributes if a.startswith("read_")}
    assert "write_text" not in attributes and "read_text" not in attributes


def test_the_no_io_assertion_can_fail(tmp_path):
    """Sabotage: the same check over a module that *does* read a file."""
    guilty = tmp_path / "guilty.py"
    guilty.write_text("from pathlib import Path\n\nx = Path('a').read_text()\n")
    tree = ast.parse(guilty.read_text())
    imported = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    attributes = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert "Path" in imported
    assert "read_text" in attributes


# ---------------------------------------------------------------------------
# AC #3 / #8 - the four families, and what test strength means
# ---------------------------------------------------------------------------


def test_all_four_families_ship():
    metrics = compute_metrics(make_pack())
    assert {m.family for m in metrics} == set(FAMILIES)
    assert len(FAMILIES) == 4


def test_test_strength_measures_ratio_uncovered_modules_and_assertion_density():
    metrics = compute_metrics(make_pack())

    assert named(metrics, "test_to_source_ratio").numeric_value == 1.0
    assert named(metrics, "source_files_without_covering_test").numeric_value == 0
    # 3 assertions across 2 test functions in TEST_BODY.
    assert named(metrics, "assertion_density_per_test").numeric_value == 1.5
    assert named(metrics, "assertions_observed").numeric_value == 3


def test_a_source_file_with_no_test_is_counted_as_uncovered():
    pack = make_pack(
        files_read=("src/widget.py", "src/orphan.py", "tests/test_widget.py")
    )
    metric = named(compute_metrics(pack), "source_files_without_covering_test")
    assert metric.numeric_value == 1
    assert "src/orphan.py" in metric.derivation


def test_a_cross_project_test_does_not_cover_a_same_named_source():
    """Ported hardening from test_strategy: project boundaries are real."""
    pack = make_pack(
        files_read=(
            "svc_a/pyproject.toml",
            "svc_a/src/payments.py",
            "svc_b/pyproject.toml",
            "svc_b/tests/test_payments.py",
        )
    )
    assert (
        named(compute_metrics(pack), "source_files_without_covering_test").numeric_value
        == 1
    )
    # Sabotage: inside ONE project the same names DO match, so the assertion
    # above is pinning the boundary rule and not merely "matching never works".
    same_project = make_pack(
        files_read=("pyproject.toml", "src/payments.py", "tests/test_payments.py")
    )
    assert (
        named(
            compute_metrics(same_project), "source_files_without_covering_test"
        ).numeric_value
        == 0
    )


def test_assertion_density_uses_only_test_file_excerpts():
    """A source file full of the word `assert` must not inflate density."""
    noisy_source = "\n".join(f"assert x{i}" for i in range(50))
    pack = make_pack(
        excerpts=(
            Excerpt("src/widget.py", 1, 50, noisy_source),
            Excerpt("tests/test_widget.py", 1, 7, TEST_BODY),
        )
    )
    assert named(compute_metrics(pack), "assertions_observed").numeric_value == 3


# ---------------------------------------------------------------------------
# AC #4 / #5 - truncation, driven to both extremes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("truncated", [False, True])
def test_whole_set_abstains_and_evidence_local_computes_under_truncation(truncated):
    """The single sabotage pair this task's ACs live or die by.

    Same pack, one flag flipped. The whole_set assertions must hold ONLY when
    truncated is True, and the evidence_local assertions must hold under BOTH -
    which is exactly the difference between the two kinds.
    """
    pack = make_pack(truncated=truncated, omitted_count=40 if truncated else 0)
    metrics = compute_metrics(pack)

    whole_set = [m for m in metrics if m.kind == WHOLE_SET]
    local = [m for m in metrics if m.kind == EVIDENCE_LOCAL]
    assert whole_set and local, "both kinds must exist or this test proves nothing"

    for metric in whole_set:
        assert metric.abstained is truncated, metric.name
        if truncated:
            assert metric.abstention.omitted_lower_bound == 40
            assert "40" in metric.abstention.reason
            assert "lower bound" in metric.abstention.reason

    # AC #5: unaffected by truncation, both ways.
    for metric in local:
        assert not metric.abstained, metric.name
        assert metric.numeric_value is not None


def test_every_declared_whole_set_metric_abstains_on_truncation():
    """Not a sample - every one, so a metric added later cannot opt out."""
    metrics = compute_metrics(make_pack(truncated=True, omitted_count=7))
    abstaining = {m.name for m in metrics if m.abstained}
    declared = {d.name for d in METRIC_DEFINITIONS if d.kind == WHOLE_SET}
    assert declared <= abstaining
    assert declared, "there must be whole_set metrics for this to mean anything"


def test_truncation_is_believed_from_either_field():
    """A pack predating T005 carries `truncation=None` and only the flat flag."""
    legacy = make_pack(truncated=True, omitted_count=12, truncation=None)
    assert named(compute_metrics(legacy), "test_to_source_ratio").abstained

    record_only = make_pack(
        truncated=False,
        omitted_count=0,
        truncation=TruncationRecord(truncated=True, omitted_count=9),
    )
    metric = named(compute_metrics(record_only), "test_to_source_ratio")
    assert metric.abstained
    assert metric.abstention.omitted_lower_bound == 9


def test_omitted_count_is_never_phrased_as_exact():
    metrics = compute_metrics(make_pack(truncated=True, omitted_count=40))
    reason = named(metrics, "test_to_source_ratio").abstention.reason
    assert "at least 40" in reason
    assert "lower bound" in reason
    assert "exactly" not in reason


# ---------------------------------------------------------------------------
# AC #6 - abstention is a distinct type, at the consumer boundary
# ---------------------------------------------------------------------------


def test_abstention_is_not_a_number_and_cannot_be_used_as_one():
    metric = named(
        compute_metrics(make_pack(truncated=True, omitted_count=1)),
        "test_to_source_ratio",
    )
    outcome = metric.outcome

    assert not isinstance(outcome, (int, float))
    assert outcome != 0 and outcome is not None
    with pytest.raises(TypeError):
        float(outcome)
    with pytest.raises(TypeError):
        int(outcome)
    with pytest.raises(TypeError):
        _ = outcome + 1
    with pytest.raises(TypeError):
        _ = outcome > 0


def test_consumer_reaching_for_a_number_is_stopped_at_the_boundary():
    """AC #6 tested where a consumer stands, not only on the dataclass."""
    metrics = compute_metrics(make_pack(truncated=True, omitted_count=5))
    metric = named(metrics, "mean_excerpt_lines")

    with pytest.raises(MetricAbstained) as excinfo:
        _ = metric.numeric_value
    assert "abstained" in str(excinfo.value)

    # And the reason travels with the value, so a renderer cannot show the
    # slot without being able to show why it is empty (DDR-0004).
    assert metric.abstention.reason in metric.derivation

    # Sabotage: the identical consumer call succeeds on a non-truncated pack.
    ok = named(compute_metrics(make_pack()), "mean_excerpt_lines")
    assert ok.numeric_value > 0


# ---------------------------------------------------------------------------
# AC #7 - the citation guard, and proof that it can fail
# ---------------------------------------------------------------------------


def test_every_non_abstaining_metric_cites_refs_the_pack_actually_read():
    pack = make_pack()
    permitted = allowed_refs(pack)
    values = [m for m in compute_metrics(pack) if not m.abstained]

    assert values, "a pack with no values would make this vacuous"
    for metric in values:
        assert metric.computed_from, metric.name
        assert set(metric.computed_from) <= permitted, metric.name


def test_a_fabricated_metric_citing_an_unread_path_is_rejected():
    """Negative test: the guard is real, not decorative."""
    pack = make_pack()
    fabricated = Metric(
        name="fabricated",
        family="test_strength",
        kind=EVIDENCE_LOCAL,
        dimension="test-strategy",
        outcome=42,
        computed_from=("src/never_read.py",),
        derivation="invented",
    )
    with pytest.raises(MetricCitationError) as excinfo:
        check_citations([fabricated], allowed_refs(pack))
    assert "src/never_read.py" in str(excinfo.value)

    # Sabotage: the SAME guard, same metric shape, passes when the citation is
    # a path the pack really read. Without this, the test above would still
    # pass against a guard that rejected everything.
    honest = Metric(**{**fabricated.__dict__, "computed_from": ("src/widget.py",)})
    check_citations([honest], allowed_refs(pack))


def test_a_value_with_no_citation_at_all_is_rejected():
    uncited = Metric(
        name="uncited",
        family="code_shape",
        kind=EVIDENCE_LOCAL,
        dimension="test-strategy",
        outcome=1,
        computed_from=(),
        derivation="cites nothing",
    )
    with pytest.raises(MetricCitationError):
        check_citations([uncited], allowed_refs(make_pack()))

    # An abstention, by contrast, is allowed to cite nothing.
    abstaining = Metric(**{**uncited.__dict__, "outcome": MetricAbstention("none")})
    check_citations([abstaining], allowed_refs(make_pack()))


# ---------------------------------------------------------------------------
# AC #9 - determinism, across processes
# ---------------------------------------------------------------------------


def test_metrics_are_byte_identical_across_two_processes():
    script = (
        "import json;"
        "from easy_verifier.core.metrics import compute_metrics;"
        "from easy_verifier.core.models import EvidencePack, Excerpt, TruncationRecord;"
        "pack = EvidencePack(dimension='test-strategy', mode='kit-aware',"
        " scope='project', files_read=('src/widget.py','tests/test_widget.py'),"
        " excerpts=(Excerpt('src/widget.py',1,3,'def widget(v):\\n return v'),"
        " Excerpt('tests/test_widget.py',1,3,'def test_widget():\\n assert 1')),"
        " sources_sought=('a','b'), sources_found=('a',), sources_missing=(),"
        " coverage_score=0.5, truncated=False, omitted_count=0,"
        " truncation=TruncationRecord(False, 0));"
        "print(compute_metrics(pack).serialize())"
    )
    runs = [
        subprocess.run(
            [sys.executable, "-c", script],
            cwd=REPO_ROOT,
            env={"PYTHONPATH": str(REPO_ROOT / "src"), "PATH": "/usr/bin:/bin"},
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        for _ in range(2)
    ]
    assert runs[0] == runs[1]
    assert json.loads(runs[0])["metrics"], "an empty payload compares equal trivially"


def test_serialization_is_stable_within_a_process_and_reflects_abstentions():
    pack = make_pack()
    assert compute_metrics(pack).serialize() == compute_metrics(pack).serialize()

    truncated = compute_metrics(make_pack(truncated=True, omitted_count=3)).serialize()
    assert truncated != compute_metrics(pack).serialize()
    assert '"abstained":true' in truncated


# ---------------------------------------------------------------------------
# AC #10 - hand-recomputable
# ---------------------------------------------------------------------------


def test_every_value_states_how_to_recompute_it_from_the_evidence():
    for metric in compute_metrics(make_pack()):
        if metric.abstained:
            assert metric.derivation.startswith("no value: ")
        else:
            assert any(ch.isdigit() for ch in metric.derivation), metric.name


def test_redaction_metrics_are_recomputable_by_hand():
    hits = (
        RedactionHit(
            detector="generic-assignment",
            fingerprint="0123456789ab",
            offset=10,
            line=2,
            path="src/widget.py",
        ),
    )
    metrics = compute_metrics(make_pack(redactions=hits))
    assert named(metrics, "redaction_hits_observed").numeric_value == 1
    # 1 file of the 2 read carried a hit.
    assert named(metrics, "redacted_file_share").numeric_value == 0.5

    # Sabotage: with no hits the same two metrics report an honest zero, so
    # the assertions above are pinning the count and not a constant.
    clean = compute_metrics(make_pack())
    assert named(clean, "redaction_hits_observed").numeric_value == 0
    assert named(clean, "redacted_file_share").numeric_value == 0.0


# ---------------------------------------------------------------------------
# Edge cases from the guide's checklist
# ---------------------------------------------------------------------------


def test_files_read_duplicated_twice_does_not_double_any_count():
    """T009/T010 residue: `files_read` repeats each path 2x by default."""
    # Deliberately ASYMMETRIC: one source, one orphan source, one test - each
    # repeated. If the duplicates survived, the ratio would read 2/4 = 0.5 per
    # side and the uncovered count would read 2, so equality alone would not
    # catch a missing dedup. The absolute values below are what pin it.
    files = (
        "src/widget.py",
        "src/orphan.py",
        "tests/test_widget.py",
    )
    single = compute_metrics(make_pack(files_read=files))
    doubled = compute_metrics(make_pack(files_read=files * 2))

    for name in ("test_to_source_ratio", "source_file_share", "redacted_file_share"):
        assert named(single, name).numeric_value == named(doubled, name).numeric_value

    assert named(doubled, "test_to_source_ratio").numeric_value == 0.5
    assert named(doubled, "source_file_share").numeric_value == 2 / 3
    assert named(doubled, "source_files_without_covering_test").numeric_value == 1
    assert named(doubled, "source_files_without_covering_test").computed_from == (
        "src/orphan.py",
        "src/widget.py",
    )


def test_an_empty_but_untruncated_pack_abstains_and_never_raises():
    pack = make_pack(
        files_read=(),
        excerpts=(),
        sources_sought=(),
        sources_found=(),
        coverage_score=None,
    )
    metrics = compute_metrics(pack)
    assert len(metrics) == len(METRIC_DEFINITIONS)
    for metric in metrics:
        assert metric.abstained, metric.name
        assert metric.abstention.omitted_lower_bound is None, (
            "an empty scope is not truncation and must not claim omitted items"
        )


def test_coverage_none_and_zero_do_not_collapse():
    sought_nothing = named(
        compute_metrics(
            make_pack(sources_sought=(), sources_found=(), coverage_score=None)
        ),
        "declared_source_coverage",
    )
    sought_and_found_nothing = named(
        compute_metrics(
            make_pack(sources_sought=("a",), sources_found=(), coverage_score=0.0)
        ),
        "declared_source_coverage",
    )
    assert sought_nothing.abstained
    assert "sought no declared source" in sought_nothing.abstention.reason
    assert sought_and_found_nothing.numeric_value == 0.0


def test_tests_but_no_source_and_source_but_no_tests():
    tests_only = compute_metrics(make_pack(files_read=("tests/test_widget.py",)))
    ratio = named(tests_only, "test_to_source_ratio")
    assert ratio.abstained
    assert "zero denominator" in ratio.abstention.reason
    assert named(tests_only, "source_files_without_covering_test").abstained

    source_only = compute_metrics(make_pack(files_read=("src/widget.py",), excerpts=()))
    assert named(source_only, "test_to_source_ratio").numeric_value == 0.0
    assert named(source_only, "source_files_without_covering_test").numeric_value == 1
    assert named(source_only, "assertion_density_per_test").abstained


def test_a_dimension_that_failed_gets_no_metrics_and_is_named():
    combined = CombinedPack(
        slots=(
            DimensionSlot(dimension="test-strategy", pack=make_pack(), error=None),
            DimensionSlot(dimension="security", pack=None, error="ScopeError: boom"),
        ),
        coverage=CoverageSummary(
            per_dimension=(("test-strategy", 0.5), ("security", None)),
            combined=0.5,
            method="pooled",
            misses=(),
        ),
        budget_model="per-dimension",
    )
    metrics = compute_metrics(combined)

    assert {m.dimension for m in metrics} == {"test-strategy"}
    assert metrics.dimensions_without_pack == (("security", "ScopeError: boom"),)


def test_a_combined_pack_yields_each_metric_once_per_surviving_dimension():
    combined = CombinedPack(
        slots=(
            DimensionSlot("test-strategy", make_pack(), None),
            DimensionSlot(
                "security",
                make_pack(dimension="security", truncated=True, omitted_count=4),
                None,
            ),
        ),
        coverage=CoverageSummary((), None, "pooled", ()),
        budget_model="per-dimension",
    )
    metrics = compute_metrics(combined)

    assert len(metrics) == 2 * len(METRIC_DEFINITIONS)
    # Truncation is per-pack: only the security slot's whole_set metrics abstain.
    per_dimension = {
        (m.dimension, m.abstained) for m in metrics if m.name == "test_to_source_ratio"
    }
    assert per_dimension == {("test-strategy", False), ("security", True)}


# ---------------------------------------------------------------------------
# Stage 5 regression: production source whose basename looks like a test
# ---------------------------------------------------------------------------


def test_source_under_a_source_root_is_source_even_when_named_test_something():
    """Stage 5 `verify` defect: `src/.../test_strategy.py` is production code.

    Its basename matches `test_*.py`, so name evidence alone classified it as a
    test. On the real `test-strategy` pack over this repo that made
    `source_file_share` publish 0.0 (truth: 1/17) and made two more metrics
    abstain claiming "no source file appears in the evidence" -- a positive
    claim about the evidence that was false, with the file sitting in
    `files_read`. Directory evidence must beat name evidence.
    """
    pack = make_pack(
        files_read=(
            "pyproject.toml",
            "src/easy_verifier/dimensions/test_strategy.py",
            "tests/test_t009_test_strategy.py",
        ),
        excerpts=(),
    )
    metrics = compute_metrics(pack)

    share = named(metrics, "source_file_share")
    assert share.numeric_value == 1 / 3, "1 source of 3 files read, not 0"

    ratio = named(metrics, "test_to_source_ratio")
    assert not ratio.abstained, "there IS a source file; abstaining here lies"
    assert ratio.numeric_value == 1.0

    uncovered = named(metrics, "source_files_without_covering_test")
    assert not uncovered.abstained
    # `tests/test_t009_test_strategy.py` is not the conventional name for
    # `test_strategy.py` (`test_test_strategy.py` would be), so it is uncovered.
    assert uncovered.numeric_value == 1


def test_directory_evidence_beats_name_evidence_in_both_directions():
    """Sabotage pair: the rule must classify BOTH ways, not just rescue `src/`.

    If it only ever said "source", the assertion above would pass against a
    classifier that had simply stopped detecting tests at all.
    """
    metrics = compute_metrics(
        make_pack(
            files_read=(
                "src/pkg/test_helpers.py",  # source root, test-shaped name
                "src/pkg/nested/tests/test_real.py",  # deeper test dir wins
                "tests/test_plain.py",  # test dir, test-shaped name
                "src/pkg/widget.py",  # plain source
            ),
            excerpts=(),
        )
    )
    # sources: test_helpers.py + widget.py; tests: test_real.py + test_plain.py
    assert named(metrics, "source_file_share").numeric_value == 0.5
    assert named(metrics, "test_to_source_ratio").numeric_value == 1.0


def test_classification_rule_is_disclosed_wherever_it_decides_the_answer():
    """AC #10: a human recomputing by hand must be told the rule was a
    heuristic over paths, not a fact about the repository."""
    values = compute_metrics(make_pack(excerpts=()))
    for name in (
        "test_to_source_ratio",
        "source_files_without_covering_test",
        "source_file_share",
    ):
        assert "path convention" in named(values, name).derivation, name

    # And the abstention reason must describe the classifier, never assert
    # something false about the evidence.
    docs_only = compute_metrics(
        make_pack(files_read=("README.md", "docs/guide.md"), excerpts=())
    )
    reason = named(docs_only, "test_to_source_ratio").abstention.reason
    assert "path convention" in reason
    assert "no source file appears in the evidence" not in reason
