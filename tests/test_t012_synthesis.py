"""T012 acceptance tests for ``combined_pack`` (combined multi-dimension pack +
aggregate coverage, FR-025/FR-026)."""

from __future__ import annotations

import dataclasses
import subprocess
import sys
from pathlib import Path

import pytest

from easy_verifier.adapters.cli import main as cli_main
from easy_verifier.core import synthesis
from easy_verifier.core.pipeline import RepoPathError, run_dimension
from easy_verifier.core.synthesis import combined_pack
from easy_verifier.dimensions import DIMENSIONS, list_dimensions

REPO_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# AC #1, #8 — runs each named dimension, all seven works and stays bounded
# ---------------------------------------------------------------------------


def test_all_seven_dimensions_return_a_slot_each() -> None:
    result = combined_pack(list_dimensions(), REPO_ROOT, scope="project")

    assert len(result.slots) == 7
    assert {slot.dimension for slot in result.slots} == set(list_dimensions())
    for slot in result.slots:
        assert slot.error is None
        assert slot.pack is not None
    # Bounded: per-dimension budget default is 120 KB; total JSON should not
    # explode past a small multiple of that for this repo.
    import dataclasses as dc
    import json

    payload = json.dumps(dc.asdict(result))
    assert len(payload.encode("utf-8")) < 2_000_000


# ---------------------------------------------------------------------------
# AC #2, #3 — aggregate coverage with stated method + union of miss lists
# ---------------------------------------------------------------------------


def test_coverage_summary_states_method_and_carries_misses_per_dimension() -> None:
    result = combined_pack(["security", "architecture"], REPO_ROOT, scope="project")

    assert result.coverage.method
    assert isinstance(result.coverage.method, str)
    names_with_misses = {name for name, _misses in result.coverage.misses}
    assert names_with_misses == {"security", "architecture"}

    for slot in result.slots:
        expected = slot.pack.sources_missing
        actual = dict(result.coverage.misses)[slot.dimension]
        assert actual == expected


def test_combined_score_is_none_when_nothing_sought_anywhere(monkeypatch) -> None:
    import easy_verifier.core.synthesis as synthesis_module

    empty_pack = run_dimension(DIMENSIONS["architecture"], REPO_ROOT, scope="project")
    empty_pack = dataclasses.replace(
        empty_pack, sources_sought=(), sources_found=(), coverage_score=None
    )

    def _fake_run_dimension(descriptor, **kwargs):
        return dataclasses.replace(empty_pack, dimension=descriptor.name)

    monkeypatch.setattr(synthesis_module, "run_dimension", _fake_run_dimension)

    result = combined_pack(["architecture", "security"], REPO_ROOT, scope="project")

    assert result.coverage.combined is None
    assert result.coverage.per_dimension == (
        ("architecture", None),
        ("security", None),
    )


def test_combined_score_pools_found_and_sought_without_poisoning_from_empty_dims(
    monkeypatch,
) -> None:
    import easy_verifier.core.synthesis as synthesis_module

    base = run_dimension(DIMENSIONS["architecture"], REPO_ROOT, scope="project")

    def _fake_run_dimension(descriptor, **kwargs):
        if descriptor.name == "architecture":
            # 2 sought, 2 found -> ratio 1.0
            return dataclasses.replace(
                base,
                dimension="architecture",
                sources_sought=("a", "b"),
                sources_found=("a", "b"),
                coverage_score=1.0,
            )
        # nothing sought -> must not poison the pooled ratio as 0
        return dataclasses.replace(
            base,
            dimension="security",
            sources_sought=(),
            sources_found=(),
            coverage_score=None,
        )

    monkeypatch.setattr(synthesis_module, "run_dimension", _fake_run_dimension)

    result = combined_pack(["architecture", "security"], REPO_ROOT, scope="project")

    assert result.coverage.combined == 1.0


# ---------------------------------------------------------------------------
# AC #4 — no cross-dimension narrative field exists at all (structural)
# ---------------------------------------------------------------------------


def test_no_narrative_field_exists_anywhere_on_the_result() -> None:
    result = combined_pack(["security", "architecture"], REPO_ROOT, scope="project")

    forbidden = {"narrative", "summary", "verdict", "correlation", "ranking", "insight"}
    for obj in (result, result.coverage, *result.slots):
        field_names = {f.name for f in dataclasses.fields(obj)}
        assert not (field_names & forbidden)


# ---------------------------------------------------------------------------
# AC #5 — truncation reported per dimension, budget model recorded
# ---------------------------------------------------------------------------


def test_budget_model_is_recorded_as_per_dimension() -> None:
    result = combined_pack(["security"], REPO_ROOT, scope="project")
    assert result.budget_model == "per-dimension"


def test_truncation_is_visible_per_dimension_not_merged() -> None:
    result = combined_pack(list_dimensions(), REPO_ROOT, scope="project")
    for slot in result.slots:
        assert slot.pack is not None
        # each pack still carries its own truncated/omitted_count fields
        assert isinstance(slot.pack.truncated, bool)
        assert isinstance(slot.pack.omitted_count, int)


# ---------------------------------------------------------------------------
# AC #6 — a failing dimension does not abort the call
# ---------------------------------------------------------------------------


def test_a_raising_dimension_carries_a_structured_error_others_still_return(
    monkeypatch,
) -> None:
    import easy_verifier.core.synthesis as synthesis_module

    real_run_dimension = synthesis_module.run_dimension

    def _boom(descriptor, **kwargs):
        if descriptor.name == "security":
            raise RuntimeError("kaboom")
        return real_run_dimension(descriptor, **kwargs)

    monkeypatch.setattr(synthesis_module, "run_dimension", _boom)

    result = combined_pack(["security", "architecture"], REPO_ROOT, scope="project")

    by_name = {slot.dimension: slot for slot in result.slots}
    assert by_name["security"].pack is None
    assert by_name["security"].error is not None
    assert "kaboom" in by_name["security"].error

    assert by_name["architecture"].pack is not None
    assert by_name["architecture"].error is None


def test_a_raising_dimension_does_not_abort_the_call_sabotage_check(
    monkeypatch,
) -> None:
    """Sabotage both extremes of the predicate this AC depends on: a version
    that always aborts on any dimension error, and the real implementation.
    The aborting version must fail this test; the real one must pass it."""
    import easy_verifier.core.synthesis as synthesis_module

    real_run_dimension = synthesis_module.run_dimension

    def _boom(descriptor, **kwargs):
        if descriptor.name == "security":
            raise RuntimeError("kaboom")
        return real_run_dimension(descriptor, **kwargs)

    monkeypatch.setattr(synthesis_module, "run_dimension", _boom)

    # Extreme A: an aborting implementation (what AC #6 forbids) — simulated
    # directly, to prove the assertion below can actually fail.
    def _aborting_combined_pack(names, *a, **k):
        for name in names:
            _boom(DIMENSIONS[name], repo_path=REPO_ROOT, scope="project")
        raise AssertionError("unreachable")

    with pytest.raises(RuntimeError):
        _aborting_combined_pack(["security", "architecture"])

    # Extreme B: the real implementation must not raise.
    result = combined_pack(["security", "architecture"], REPO_ROOT, scope="project")
    assert len(result.slots) == 2


def test_all_dimensions_failing_yields_a_result_not_an_exception(monkeypatch) -> None:
    import easy_verifier.core.synthesis as synthesis_module

    def _always_boom(descriptor, **kwargs):
        raise RuntimeError(f"boom for {descriptor.name}")

    monkeypatch.setattr(synthesis_module, "run_dimension", _always_boom)

    result = combined_pack(list_dimensions(), REPO_ROOT, scope="project")

    assert len(result.slots) == 7
    assert all(slot.pack is None and slot.error is not None for slot in result.slots)


# ---------------------------------------------------------------------------
# AC #7 — unknown dimension name rejected, valid names from list_dimensions()
# ---------------------------------------------------------------------------


def test_unknown_dimension_name_is_rejected_naming_valid_dimensions() -> None:
    with pytest.raises(ValueError) as excinfo:
        combined_pack(["security", "not-a-dimension"], REPO_ROOT, scope="project")

    message = str(excinfo.value)
    assert "not-a-dimension" in message
    for name in list_dimensions():
        assert name in message


def test_valid_names_come_from_list_dimensions_not_a_duplicated_list() -> None:
    # Sabotage check: if a second hand list existed and drifted, this would
    # catch it by asserting the two sources are the same object's output.
    assert set(list_dimensions()) == set(DIMENSIONS)


# ---------------------------------------------------------------------------
# AC #9 — single dimension equivalent to a direct run_dimension() call
# ---------------------------------------------------------------------------


def test_single_dimension_combined_call_matches_direct_run_dimension() -> None:
    direct = run_dimension(DIMENSIONS["security"], REPO_ROOT, scope="project")
    result = combined_pack(["security"], REPO_ROOT, scope="project")

    assert len(result.slots) == 1
    slot = result.slots[0]
    assert slot.error is None
    assert slot.pack == direct


def test_sabotage_single_dimension_equivalence_catches_a_divided_budget() -> None:
    """Hardwire the predicate to the extreme AC #9 forbids: dividing the
    budget across a combined call. Prove that extreme would fail the
    equivalence assertion, then prove the real implementation passes it."""
    direct = run_dimension(
        DIMENSIONS["security"], REPO_ROOT, scope="project", budget_bytes=120_000
    )
    # Extreme: budget divided as if pooled across N dimensions requested.
    divided = run_dimension(
        DIMENSIONS["security"], REPO_ROOT, scope="project", budget_bytes=120_000 // 3
    )
    assert divided != direct  # the forbidden behaviour is detectably different

    result = combined_pack(
        ["security"], REPO_ROOT, scope="project", budget_bytes=120_000
    )
    assert result.slots[0].pack == direct


# ---------------------------------------------------------------------------
# AC #10 — deterministic order regardless of request order
# ---------------------------------------------------------------------------


def test_dimension_order_is_deterministic_regardless_of_request_order() -> None:
    forward = combined_pack(["architecture", "security", "code-quality"], REPO_ROOT)
    shuffled = combined_pack(["code-quality", "security", "architecture"], REPO_ROOT)

    forward_names = [slot.dimension for slot in forward.slots]
    shuffled_names = [slot.dimension for slot in shuffled.slots]

    assert forward_names == shuffled_names


def test_sabotage_order_uses_request_order_not_canonical_order() -> None:
    """Hardwire the predicate to the extreme AC #10 forbids: preserving
    request order verbatim. Prove that extreme is detectably different from
    canonical order, then prove the real implementation is canonical."""
    requested = ["code-quality", "security", "architecture"]
    request_order_extreme = tuple(requested)  # what a naive implementation would return

    result = combined_pack(requested, REPO_ROOT)
    actual_order = tuple(slot.dimension for slot in result.slots)

    assert actual_order != request_order_extreme
    assert actual_order == tuple(
        name for name in list_dimensions() if name in requested
    )


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_empty_dimension_list_is_a_structured_error() -> None:
    with pytest.raises(ValueError):
        combined_pack([], REPO_ROOT, scope="project")


def test_duplicate_names_are_deduplicated_and_run_once() -> None:
    result = combined_pack(["security", "security"], REPO_ROOT, scope="project")
    assert len(result.slots) == 1


# ---------------------------------------------------------------------------
# Miss-list consistency (the project's recurring defect class)
# ---------------------------------------------------------------------------


def test_aggregated_misses_are_consistent_with_each_packs_own_miss_list() -> None:
    result = combined_pack(list_dimensions(), REPO_ROOT, scope="project")
    misses_by_name = dict(result.coverage.misses)

    for slot in result.slots:
        assert slot.pack is not None
        assert misses_by_name[slot.dimension] == slot.pack.sources_missing
        # nothing reported missing that is actually in sources_found
        missing_sources = {miss.source for miss in misses_by_name[slot.dimension]}
        assert not (missing_sources & set(slot.pack.sources_found))


# ---------------------------------------------------------------------------
# CLI adapter
# ---------------------------------------------------------------------------


def test_cli_combined_subcommand_prints_json(tmp_path, capsys) -> None:
    exit_code = cli_main(
        [
            "combined",
            "--repo",
            str(REPO_ROOT),
            "--dimensions",
            "architecture,security",
        ]
    )
    assert exit_code == 0
    out = capsys.readouterr().out
    assert '"slots"' in out
    assert '"budget_model": "per-dimension"' in out


def test_cli_combined_requires_dimensions_flag() -> None:
    with pytest.raises(SystemExit):
        cli_main(["combined", "--repo", str(REPO_ROOT)])


def test_cli_single_dimension_still_works_unchanged() -> None:
    # Backward-compat guard: adding 'combined' must not disturb the existing
    # single-dimension CLI contract (FR-022).
    exit_code = subprocess.run(
        [
            sys.executable,
            "-m",
            "easy_verifier.adapters.cli",
            "architecture",
            "--repo",
            str(REPO_ROOT),
        ],
        cwd=REPO_ROOT,
        env={"PYTHONPATH": str(REPO_ROOT / "src")},
        capture_output=True,
        check=False,
    ).returncode
    assert exit_code == 0


# --- Stage 4 review regressions (T012) ------------------------------------


def test_aggregate_method_names_the_dimensions_excluded_by_failure(
    monkeypatch, tmp_path
) -> None:
    """A coverage figure must say what bounded it.

    A dimension that raises contributes nothing to the pooled ratio, and
    renders in ``per_dimension`` as ``None`` -- indistinguishable from a
    dimension that sought nothing. Unless ``method`` names the exclusion, a
    reader holding only the :class:`CoverageSummary` sees a confident number
    computed over a silently smaller set. This is the same defect class as the
    cap-truncated sweep that reported a repository-wide zero (T010).
    """
    real = synthesis.run_dimension

    def flaky(descriptor, **kwargs):
        if descriptor.name == "security":
            raise RuntimeError("boom")
        return real(descriptor, **kwargs)

    monkeypatch.setattr(synthesis, "run_dimension", flaky)
    result = synthesis.combined_pack(["architecture", "security"], ".")

    method = result.coverage.method
    assert "security" in method
    assert "EXCLUDED" in method
    # and the healthy dimension is not mislabelled as excluded
    assert "architecture" not in method.split("EXCLUDED")[1]


def test_aggregate_method_is_unchanged_when_every_dimension_succeeds() -> None:
    """The exclusion note must not fire on a clean run -- a permanent warning
    is the same as no warning."""
    result = synthesis.combined_pack(["architecture"], ".")
    assert "EXCLUDED" not in result.coverage.method


def test_an_unusable_repo_path_raises_instead_of_filling_every_slot_with_errors() -> (
    None
):
    """AC #6 isolates a failing *dimension*, not a failing precondition.

    A repository path that does not exist makes every dimension fail
    identically. Reporting that as a successful combined call full of error
    slots gave the CLI exit 0 for a repo that is not there, while the
    single-dimension path exits 2 -- an FR-022 divergence between two entry
    points that must agree.
    """
    with pytest.raises(RepoPathError):
        synthesis.combined_pack(["architecture", "security"], "/nope/does-not-exist")


def test_cli_combined_exits_2_on_a_bad_repo_path_like_the_single_path(capsys) -> None:
    single = cli_main(["architecture", "--repo", "/nope/does-not-exist"])
    combined = cli_main(
        ["combined", "--dimensions", "architecture", "--repo", "/nope/does-not-exist"]
    )
    assert single == combined == 2
