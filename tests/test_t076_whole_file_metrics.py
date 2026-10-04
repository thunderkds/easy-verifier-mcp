"""T076 — whole-file code metrics at or under the cap (FR-072).

Below the 200-file cap the code tiers' structure metrics are computed over the
whole text of every source file, through the same path as T068's batches above
the cap, so a byte budget that truncates the excerpts no longer makes them
abstain. Only the disclosure differs: "all N source files", never a sample.
"""

from __future__ import annotations

from pathlib import Path

from easy_verifier.core.metric_tables import curated_metric_tables
from easy_verifier.core.metrics import (
    MetricAbstention,
    compute_metrics,
    compute_sampled_metrics,
)
from easy_verifier.core.models import Excerpt, to_json_dict
from easy_verifier.core.pipeline import run_dimension
from easy_verifier.core.score import score_repository
from easy_verifier.dimensions import architecture, code_quality

WHOLE = {
    code_quality: (
        "functions_over_ccn_10_share",
        "max_function_ccn",
        "type_escapes_per_kloc",
        "todo_without_ticket_share",
    ),
    architecture: ("top_level_import_cycles", "layer_direction_violations"),
}
TINY_BUDGET = 200


def _module(index: int, other: str) -> str:
    branches = "".join(f"    if x == {i}:\n        x += 1\n" for i in range(index % 13))
    escape = "from typing import Any\n\n\ndef typed(v: Any) -> int:\n    return 1\n"
    todo = "# TODO tidy this\n" if index % 4 == 0 else "# FIXME see ABC-12\n"
    return f"import {other}\n{todo}\n\ndef f{index}(x):\n{branches}    return x\n\n" + (
        escape if index % 3 == 0 else ""
    )


def _repo(root: Path, count: int = 20) -> Path:
    files = {"README.md": "# Small\n\n" + "Words. " * 400 + "\n"}
    for i in range(count):
        # alpha (api layer) and beta (service layer) import each other: a
        # top-level cycle, and layered files for layer_direction_violations.
        package, other = ("alpha/api", "beta") if i % 2 else ("beta/services", "alpha")
        files[f"{package}/m{i:02}.py"] = _module(i, other)
    for relative, text in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


def _metrics(pack):
    return {m.name: m for m in compute_metrics(pack, curated_metric_tables()).metrics}


def _oracle(repo: Path, dimension: str) -> dict:
    units = [
        Excerpt(path=p, start_line=1, end_line=len(t.split("\n")), text=t)
        for p, t in sorted(
            (path.relative_to(repo).as_posix(), path.read_text(encoding="utf-8"))
            for path in repo.rglob("*.py")
            if not path.name.startswith(".")
        )
    ]
    return {
        m.name: m.value
        for m in compute_sampled_metrics(dimension, units, curated_metric_tables())
    }


def test_truncated_pack_still_computes_whole_file_metrics(tmp_path) -> None:
    repo = _repo(tmp_path)
    for module, names in WHOLE.items():
        pack = run_dimension(
            module.DESCRIPTOR, repo, scope="project", budget_bytes=TINY_BUDGET
        )
        assert pack.truncated  # FR-027a: still reported (AC3)
        metrics = _metrics(pack)
        oracle = _oracle(repo, module.NAME)
        for name in names:
            outcome = metrics[name].outcome
            assert not isinstance(outcome, MetricAbstention), (name, outcome)
            assert outcome == oracle[name], name  # SC2: equal to all files directly


def test_values_are_real_not_degenerate(tmp_path) -> None:
    repo = _repo(tmp_path)
    pack = run_dimension(
        code_quality.DESCRIPTOR, repo, scope="project", budget_bytes=TINY_BUDGET
    )
    metrics = _metrics(pack)
    assert metrics["max_function_ccn"].outcome == 13
    pack = run_dimension(
        architecture.DESCRIPTOR, repo, scope="project", budget_bytes=TINY_BUDGET
    )
    assert _metrics(pack)["top_level_import_cycles"].outcome >= 1


def test_disclosure_says_all_files_and_never_sample(tmp_path) -> None:
    repo = _repo(tmp_path)
    for module, names in WHOLE.items():
        pack = run_dimension(
            module.DESCRIPTOR, repo, scope="project", budget_bytes=TINY_BUDGET
        )
        assert "sample" not in to_json_dict(pack)
        metrics = _metrics(pack)
        for name in names:
            derivation = metrics[name].derivation
            assert "all 20 source files" in derivation, derivation
            assert "sample" not in derivation
    payload = score_repository(
        repo, scope="project", budget_bytes=TINY_BUDGET
    ).serialize()
    assert '"samples"' not in payload
    assert "continue_batches" not in payload


def test_secret_bearing_source_is_still_refused(tmp_path) -> None:
    repo = _repo(tmp_path)
    (repo / "alpha/api/.env.py").write_text("TOKEN=FAKEfake\n", encoding="utf-8")
    pack = run_dimension(
        code_quality.DESCRIPTOR, repo, scope="project", budget_bytes=TINY_BUDGET
    )
    assert "alpha/api/.env.py" not in pack.files_read
    for metric in _metrics(pack).values():
        assert "alpha/api/.env.py" not in metric.computed_from


def test_zero_source_files_abstain_as_before(tmp_path) -> None:
    (tmp_path / "README.md").write_text("# Docs only\n", encoding="utf-8")
    for module, names in WHOLE.items():
        pack = run_dimension(module.DESCRIPTOR, tmp_path, scope="project")
        assert "whole_file" not in to_json_dict(pack)
        metrics = _metrics(pack)
        for name in names:
            assert isinstance(metrics[name].outcome, MetricAbstention), name
