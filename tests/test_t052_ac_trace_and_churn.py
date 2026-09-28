"""T052 acceptance tests: requirement-fidelity AC tracing, blast-radius
fan-in and repository-wide churn hotspots.

Each sabotage pair varies only the predicate it pins (T031/T032 learning):
the same fixture with one fact moved across the boundary under test.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from easy_verifier.core.judge import Rating, rate
from easy_verifier.core.metric_tables import curated_metric_tables
from easy_verifier.core.metrics import compute_metrics
from easy_verifier.core.models import CoverageSummary, EvidencePack
from easy_verifier.core.pipeline import run_dimension
from easy_verifier.dimensions import blast_radius, requirement_fidelity

CODE = "acceptance_criteria_traced_to_code_share"
TEST = "acceptance_criteria_traced_to_test_share"
FAN_IN = "max_fan_in_changed"
HOT = "changed_files_in_churn_hotspots_share"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        env={
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@example.com",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@example.com",
            "PATH": "/usr/bin:/bin",
            "HOME": str(repo),
        },
    )


def _commit(repo: Path, message: str) -> None:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", message)


def _write(root: Path, files: dict[str, str]) -> None:
    for relative, text in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def _metric(pack: EvidencePack, name: str):
    (metric,) = compute_metrics(pack, curated_metric_tables()).by_name(name)
    return metric


def _guide(task: str, rows: list[str]) -> str:
    body = "\n".join(f"| {n} | {row} | FR-000 |" for n, row in enumerate(rows, 1))
    return (
        f"# TASK_GUIDE — {task}\n\n## Acceptance Criteria\n\n"
        "| # | Criterion (testable) | Traces to requirement |\n"
        "|---|----------------------|-----------------------|\n"
        f"{body}\n\n## Evaluation\n\n| 1 | not a criterion | x |\n"
    )


def _kit_repo(root: Path, *, t004_in: str = "README.md") -> None:
    """Four guides, one AC each; T001-T003 named in code, T004 in ``t004_in``."""
    files = {
        f"tasks/TASK_GUIDE_T00{n}.md": _guide(f"T00{n}", [f"criterion {n}"])
        for n in range(1, 5)
    }
    files.update(
        {
            "src/app.py": "# implements T001 and T002\nVALUE = 1  # T003\n",
            "tests/test_app.py": "def test_value():  # T001\n    assert True\n",
            t004_in: "T004 is described here\n",
        }
    )
    _write(root, files)


def _rf(root: Path, budget_bytes: int = 120_000) -> EvidencePack:
    return run_dimension(requirement_fidelity.DESCRIPTOR, root, "project", budget_bytes)


# ---------------------------------------------------------------------------
# Success Criterion 1 / AC 1-2: 3 of 4 ACs traced to code -> 0.75
# ---------------------------------------------------------------------------


def test_three_of_four_criteria_named_in_code_give_a_share_of_075(tmp_path: Path):
    _kit_repo(tmp_path)
    pack = _rf(tmp_path)

    assert pack.mode == "kit-aware"
    code, test = _metric(pack, CODE), _metric(pack, TEST)
    assert code.outcome == 0.75
    assert test.outcome == 0.25
    # AC 1: four criteria (the Evaluation table after the next heading is not
    # one); the untraced one is cited at its own guide line.
    search = pack.trace_search
    assert (search.criteria, search.traced_to_code, search.traced_to_test) == (4, 3, 1)
    assert [c.id for c in search.untraced_code] == ["T004#1"]
    assert "tasks/TASK_GUIDE_T004.md:7-7" in code.computed_from
    assert "src/app.py:1-1" in code.computed_from
    assert "T004#1" in code.derivation


def test_docs_only_mention_is_no_trace_but_the_same_id_in_code_is(tmp_path: Path):
    # Sabotage pair: only where "T004" is written differs.
    docs, code = tmp_path / "docs", tmp_path / "code"
    _kit_repo(docs, t004_in="docs/notes.md")
    _kit_repo(code, t004_in="src/other.py")

    assert _metric(_rf(docs), CODE).outcome == 0.75
    assert _metric(_rf(code), CODE).outcome == 1.0


def test_an_id_in_a_test_file_traces_to_a_test_not_to_code(tmp_path: Path):
    _kit_repo(tmp_path, t004_in="tests/test_other.py")
    pack = _rf(tmp_path)
    assert _metric(pack, CODE).outcome == 0.75
    assert _metric(pack, TEST).outcome == 0.5  # T001 and T004


def test_fr_ids_are_criteria_and_trace_keys_with_exact_boundaries(tmp_path: Path):
    _write(
        tmp_path,
        {
            "PRD.md": "| ID | Req |\n|---|---|\n| FR-001 | one |\n| FR-002 | two |\n",
            "tasks/TASK_GUIDE_T009.md": _guide("T009", ["x"]).replace(
                "FR-000", "FR-002"
            ),
            # FR-001a is not FR-001; FR-002 traces FR-002 and the T009 row.
            "src/a.py": "# FR-001a\n# FR-002\n",
        },
    )
    pack = _rf(tmp_path)
    assert pack.trace_search.criteria == 3
    assert [c.id for c in pack.trace_search.untraced_code] == ["FR-001"]
    assert _metric(pack, CODE).outcome == pytest.approx(2 / 3)


def test_standalone_mode_abstains_with_its_stated_reason(tmp_path: Path):
    _write(tmp_path, {"README.md": "# x\n", "src/a.py": "# T001\n"})
    pack = _rf(tmp_path)
    assert pack.mode == "standalone" and pack.trace_search is None
    for name in (CODE, TEST):
        metric = _metric(pack, name)
        assert metric.abstained
        assert "never inferred" in metric.abstention.reason


# ---------------------------------------------------------------------------
# AC 5: bounded -- dropped evidence and a capped search abstain
# ---------------------------------------------------------------------------


def test_a_budget_that_drops_trace_lines_abstains_instead_of_undercounting(
    tmp_path: Path,
):
    # Sabotage pair: only the byte budget differs. 90 bytes holds the three
    # quoted untraced rows but not every trace line.
    _kit_repo(tmp_path)
    full = _metric(_rf(tmp_path), CODE)
    tight = _metric(_rf(tmp_path, budget_bytes=90), CODE)
    assert full.outcome == 0.75
    assert tight.abstained
    assert "byte budget dropped" in tight.abstention.reason


def test_a_trace_search_that_hits_its_file_ceiling_abstains(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    _kit_repo(tmp_path)
    monkeypatch.setattr(requirement_fidelity, "MAX_TRACE_SCAN_FILES", 1)
    capped = _rf(tmp_path)
    assert "ceiling of 1" in capped.trace_search.incomplete
    assert "incomplete" in _metric(capped, CODE).abstention.reason

    monkeypatch.setattr(requirement_fidelity, "MAX_TRACE_SCAN_FILES", 2)
    assert _metric(_rf(tmp_path), CODE).outcome == 0.75


def test_more_criteria_than_the_ceiling_abstains(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    # Sabotage pair: only the criteria ceiling differs (4 criteria).
    _kit_repo(tmp_path)
    monkeypatch.setattr(requirement_fidelity, "MAX_CRITERIA", 3)
    capped = _rf(tmp_path)
    assert capped.trace_search.criteria == 3
    assert "more than 3 criteria" in _metric(capped, CODE).abstention.reason

    monkeypatch.setattr(requirement_fidelity, "MAX_CRITERIA", 4)
    assert _metric(_rf(tmp_path), CODE).outcome == 0.75


def test_trace_metrics_are_deterministic_across_runs(tmp_path: Path):
    _kit_repo(tmp_path)
    tables = curated_metric_tables()
    first = compute_metrics(_rf(tmp_path), tables).serialize()
    assert compute_metrics(_rf(tmp_path), tables).serialize() == first


# ---------------------------------------------------------------------------
# Success Criterion 2 / AC 3: fan-in of a changed file
# ---------------------------------------------------------------------------


def _fan_in_repo(root: Path, importers: int) -> None:
    _write(root, {"target.py": "VALUE = 1\n"})
    for n in range(importers):
        _write(root, {f"m{n:02d}.py": "import target\n\nprint(target.VALUE)\n"})
    _git(root, "init", "-q", "-b", "main")
    _commit(root, "base")
    _write(root, {"target.py": "VALUE = 2\n"})
    _commit(root, "change target")


def _coverage(dimension: str) -> CoverageSummary:
    return CoverageSummary(
        per_dimension=((dimension, 1.0),),
        combined=1.0,
        method="fixture",
        misses=((dimension, ()),),
    )


def test_a_changed_file_imported_by_25_files_has_fan_in_25_and_fails_the_rule(
    tmp_path: Path,
):
    _fan_in_repo(tmp_path, 25)
    pack = run_dimension(blast_radius.DESCRIPTOR, tmp_path, "changes", ref="HEAD")
    metrics = compute_metrics(pack, curated_metric_tables())
    assert metrics.by_name(FAN_IN)[0].outcome == 25

    result = rate(metrics, _coverage("blast-radius"))
    assert isinstance(result, Rating)
    (fan_in,) = [i for i in result.inputs if i.metric_name == FAN_IN]
    assert fan_in.passed is False


def test_a_reference_sweep_that_hits_its_ceiling_abstains_on_fan_in(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    # Sabotage pair: only the sweep ceiling differs.
    _fan_in_repo(tmp_path, 25)
    monkeypatch.setattr(blast_radius, "MAX_SCAN_FILES", 5)
    capped = run_dimension(blast_radius.DESCRIPTOR, tmp_path, "changes", ref="HEAD")
    assert capped.reach.sweep_capped is True
    assert "ceiling" in _metric(capped, FAN_IN).abstention.reason

    monkeypatch.setattr(blast_radius, "MAX_SCAN_FILES", 400)
    whole = run_dimension(blast_radius.DESCRIPTOR, tmp_path, "changes", ref="HEAD")
    assert _metric(whole, FAN_IN).outcome == 25


# ---------------------------------------------------------------------------
# AC 3: churn hotspots ranked repository-wide, independent of the scope
# ---------------------------------------------------------------------------


def _churn_repo(root: Path) -> None:
    """hot1/hot2 change in 22 commits; c00..c17 once. 20 ranked files -> top 2."""
    _write(root, {f"c{n:02d}.py": f"C = {n}\n" for n in range(18)})
    _write(root, {"hot1.py": "H = 0\n", "hot2.py": "H = 0\n"})
    _git(root, "init", "-q", "-b", "main")
    _commit(root, "base")
    for n in range(1, 22):
        _write(root, {"hot1.py": f"H = {n}\n", "hot2.py": f"H = {n}\n"})
        _commit(root, f"churn {n}")


def _changes(root: Path, files: dict[str, str]) -> EvidencePack:
    _write(root, files)
    _commit(root, "the change")
    return run_dimension(blast_radius.DESCRIPTOR, root, "changes", ref="HEAD")


def test_share_of_changed_files_in_the_repo_wide_top_10_percent(tmp_path: Path):
    # Sabotage pair: only which files the change touches differs.
    hot, cold = tmp_path / "hot", tmp_path / "cold"
    for root in (hot, cold):
        root.mkdir()
        _churn_repo(root)

    touching_hot = _changes(hot, {"hot1.py": "H = 99\n", "c00.py": "C = 99\n"})
    touching_cold = _changes(cold, {"c01.py": "C = 99\n", "c00.py": "C = 99\n"})

    metric = _metric(touching_hot, HOT)
    assert metric.outcome == 0.5
    assert touching_hot.reach.hotspot_count == 2
    assert touching_hot.reach.ranked_files == 20
    assert "hot1.py" in metric.derivation
    assert _metric(touching_cold, HOT).outcome == 0.0
    assert blast_radius.HOTSPOT_SOURCE in touching_hot.sources_found


def test_little_history_abstains_with_a_reason(tmp_path: Path):
    _fan_in_repo(tmp_path, 2)  # two commits
    pack = run_dimension(blast_radius.DESCRIPTOR, tmp_path, "changes", ref="HEAD")
    metric = _metric(pack, HOT)
    assert metric.abstained
    assert "fewer than the 20" in metric.abstention.reason


def test_a_shallow_clone_abstains_with_a_reason(tmp_path: Path):
    origin, clone = tmp_path / "origin", tmp_path / "clone"
    origin.mkdir()
    _churn_repo(origin)
    _git(tmp_path, "clone", "-q", "--depth", "2", f"file://{origin}", str(clone))
    pack = run_dimension(blast_radius.DESCRIPTOR, clone, "changes", ref="HEAD")
    metric = _metric(pack, HOT)
    assert metric.abstained
    assert "shallow clone" in metric.abstention.reason


def test_project_scope_still_abstains_because_the_share_is_10_percent_by_construction(
    tmp_path: Path,
):
    _churn_repo(tmp_path)
    pack = run_dimension(blast_radius.DESCRIPTOR, tmp_path, "project")
    assert pack.reach is None
    assert "by construction" in _metric(pack, HOT).abstention.reason


def test_untraced_list_is_capped_and_counts_the_rest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    _kit_repo(tmp_path)
    monkeypatch.setattr(requirement_fidelity, "MAX_UNTRACED_LISTED", 1)
    pack = _rf(tmp_path)
    search = pack.trace_search
    assert [c.id for c in search.untraced_test] == ["T002#1"]
    assert search.untraced_test_omitted == 2
    assert _metric(pack, TEST).outcome == 0.25  # counted over all 4 criteria
    # Only the listed untraced rows are quoted; traced rows are not.
    quoted = {
        e.path
        for e in pack.excerpts
        if e.start_line == e.end_line and e.text.startswith("| 1 | criterion")
    }
    assert quoted == {"tasks/TASK_GUIDE_T002.md", "tasks/TASK_GUIDE_T004.md"}


# ---------------------------------------------------------------------------
# Review P1: colocated test names are tests even under a source root
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("path", "kind"),
    [
        ("src/app.controller.spec.ts", "test"),
        ("apps/api/src/tasks/tasks.service.test.tsx", "test"),
        ("internal/store/store_test.go", "test"),
        ("src/main/java/com/x/FooTests.java", "test"),
        ("src/main/kotlin/FooTest.kt", "test"),
        ("src/App/FooTests.cs", "test"),
        ("lib/foo_spec.rb", "test"),
        # prefix-style / ambiguous names keep the directory-first rule
        ("src/easy_verifier/dimensions/test_strategy.py", "source"),
        ("src/pkg/test_helpers.py", "source"),
        ("lib/test_thing.rb", "source"),
        ("src/app.controller.ts", "source"),
        ("tests/test_app.py", "test"),
    ],
)
def test_shared_classifier_colocated_names(path: str, kind: str):
    from easy_verifier.core.metrics import code_kind
    from easy_verifier.dimensions import test_strategy

    assert code_kind(path, curated_metric_tables()) == kind
    assert test_strategy._is_test_file(path) is (kind == "test")


def test_colocated_names_are_cited_registry_data_and_python_has_none():
    from easy_verifier.core.roles import _registry

    registry = _registry()
    (jsts,) = registry.languages["js-ts"].fields["colocated_test_name_patterns"]
    assert "?*.spec.ts" in jsts.value and jsts.citation_url.startswith("https://")
    assert "colocated_test_name_patterns" not in registry.languages["python"].fields


def test_a_colocated_spec_under_src_traces_to_a_test(tmp_path: Path):
    # Sabotage pair: only the file name differs (spec-suffixed vs plain).
    spec, plain = tmp_path / "spec", tmp_path / "plain"
    _kit_repo(spec, t004_in="src/app.controller.spec.ts")
    _kit_repo(plain, t004_in="src/app.controller.ts")
    assert _metric(_rf(spec), TEST).outcome == 0.5
    assert _metric(_rf(plain), TEST).outcome == 0.25
