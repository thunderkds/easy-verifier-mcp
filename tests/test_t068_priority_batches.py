"""T068 — large repos: code-tier sources read in priority batches (DDR-0010 §3–§5).

FR-060: above the cap, sources are ordered purpose class -> git churn -> path
and read in batches of the cap, with the sample disclosed. FR-061: MCP asks
``needs_input.continue_batches``; the CLI takes ``--batches N`` / ``--all``.
FR-062: stateless -- the agent names only a batch count, the engine re-derives
batches 1..N, and replay is byte-equal.
"""

from __future__ import annotations

import io
import json
import subprocess
from pathlib import Path

import pytest

from easy_verifier.adapters import cli, mcp_server
from easy_verifier.core import batches
from easy_verifier.core.findings import ValidationError
from easy_verifier.core.metric_tables import curated_metric_tables
from easy_verifier.core.metrics import compute_metrics
from easy_verifier.core.models import EvidencePack, Excerpt, to_json_dict
from easy_verifier.core.pipeline import run_dimension
from easy_verifier.core.report import _Ctx, _render_score_panel
from easy_verifier.core.score import score_repository
from easy_verifier.dimensions import (
    _code_extract,
    architecture,
    code_quality,
    test_strategy,
)

SNAPSHOT = Path(__file__).parent / "snapshots" / "t068_under_cap_score.json"

SAMPLED = {
    "code-quality": (
        "functions_over_ccn_10_share",
        "max_function_ccn",
        "type_escapes_per_kloc",
        "todo_without_ticket_share",
    ),
    "architecture": ("top_level_import_cycles",),
}


# ---------------------------------------------------------------------------
# fixtures


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
            "GIT_AUTHOR_DATE": "2026-01-01T00:00:00Z",
            "GIT_COMMITTER_DATE": "2026-01-01T00:00:00Z",
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


def _module(name: str, other: str, index: int) -> str:
    """A small source file whose metrics vary by index: some functions over
    CCN 10, a type escape every 3rd file, a debt marker every 4th, and an
    import of another top-level module (so cycles exist)."""
    branches = "".join(f"    if x == {i}:\n        x += 1\n" for i in range(index % 13))
    escape = (
        "from typing import Any\n\n\ndef typed(v: Any) -> int:\n    return 1\n"
        if index % 3 == 0
        else ""
    )
    todo = "# TODO tidy this\n" if index % 4 == 0 else "# FIXME see ABC-12\n"
    return (
        f"import {other}\n{todo}\n\ndef {name}(x):\n{branches}    return x\n\n{escape}"
    )


APP, SCRIPTS, VENDOR = 250, 100, 100
HOT = ("app/m249.py", "app/m248.py", "app/m247.py")


@pytest.fixture(scope="module")
def big_repo(tmp_path_factory) -> Path:
    """450 sources across app/, scripts/, generated/ with git history: the
    last three app files by path are the most churned, so churn -- not path --
    must put them first. (`generated/`, not `vendor/`: since T087 a vendor
    directory is third-party and leaves the scope, while a generated one is
    still evaluated, last.)"""
    repo = tmp_path_factory.mktemp("t068") / "big"
    files = {"README.md": "# Big\n\nA large fixture.\n"}
    files |= {f"app/m{i:03}.py": _module(f"a{i}", "scripts", i) for i in range(APP)}
    files |= {f"scripts/s{i:03}.py": _module(f"s{i}", "app", i) for i in range(SCRIPTS)}
    files |= {
        f"generated/v{i:03}.py": _module(f"v{i}", "app", i) for i in range(VENDOR)
    }
    files |= {
        f"tests/test_m{i:03}.py": f"def test_m{i}():\n    assert True\n"
        for i in range(5)
    }
    _write(repo, files)
    _git(repo, "init", "-q")
    _commit(repo, "initial")
    for count in (3, 2, 1):
        for path in HOT[:count]:
            with (repo / path).open("a", encoding="utf-8") as handle:
                handle.write(f"# churn {count}\n")
        _commit(repo, f"churn {count}")
    return repo


@pytest.fixture
def small(tmp_path, monkeypatch) -> Path:
    """Ten sources, cap 4 -> three batches; classes and churn both matter."""
    monkeypatch.setattr(_code_extract, "MAX_CODE_SOURCES", 4)
    monkeypatch.setattr(test_strategy, "MAX_TEST_SOURCES", 4)
    repo = tmp_path / "small"
    _write(
        repo,
        {
            "README.md": "# Small\n",
            "web/a.py": "def a(x):\n    return x\n",
            "web/b.py": "def b(x):\n    return x\n",
            "web/c.py": "def c(x):\n    return x\n",
            "backend/api/z.py": "def z(x):\n    return x\n",
            "server/y.py": "def y(x):\n    return x\n",
            "scripts/deploy.py": "def deploy(x):\n    return x\n",
            "tools/gen.py": "def gen(x):\n    return x\n",
            "webpack.config.js": "function cfg(x) {\n  return x;\n}\n",
            "vendor/lib.py": "def lib(x):\n    return x\n",
            "web/bundle.min.js": "function m(x) {\n  return x;\n}\n",
        },
    )
    _git(repo, "init", "-q")
    _commit(repo, "initial")
    (repo / "web/c.py").write_text("def c(x):\n    return x + 1\n", encoding="utf-8")
    _commit(repo, "churn c")
    return repo


def _under_cap_repo(root: Path) -> Path:
    """50 sources, no git, project scope: the at-or-under-cap regression."""
    repo = root / "under"
    files = {
        "README.md": "# Under\n\nFifty sources.\n",
        "ruff.toml": "line-length = 88\n",
    }
    files |= {f"src/pkg/m{i:02}.py": _module(f"f{i}", "pkg", i) for i in range(50)}
    files |= {"tests/test_m00.py": "def test_m00():\n    assert True\n"}
    _write(repo, files)
    return repo


def _payload(repo: Path, **kwargs) -> str:
    return score_repository(repo, scope="project", **kwargs).serialize()


# ---------------------------------------------------------------------------
# AC2: ordering (purpose class -> churn -> path), declared data


def test_purpose_classes_are_declared_data_with_a_basis() -> None:
    names = [item.name for item in batches.PURPOSE_CLASSES]
    assert names == [
        "application/server source",
        "other application source",
        "scripts/tooling",
        "generated/vendored",
    ]
    for item in batches.PURPOSE_CLASSES:
        assert item.basis == "project-default" or item.basis.startswith("https://")


@pytest.mark.parametrize(
    ("path", "rank"),
    [
        ("backend/api/z.py", 0),
        ("server/y.py", 0),
        ("web/a.py", 1),
        ("src/pkg/core.py", 1),
        ("scripts/deploy.py", 2),
        ("backend/scripts/job.js", 2),
        ("webpack.config.js", 2),
        ("vendor/lib.py", 3),
        ("server/vendor/x.py", 3),
        ("web/bundle.min.js", 3),
        ("proto/thing_pb2.py", 3),
    ],
)
def test_purpose_rank(path: str, rank: int) -> None:
    assert batches.purpose_rank(path) == rank


def test_order_is_class_then_churn_then_path(small: Path) -> None:
    sources = sorted(
        path.relative_to(small).as_posix()
        for path in small.rglob("*")
        if path.suffix in {".py", ".js"}
    )
    plan = batches.plan(small, sources, 4, 1)
    assert plan.ordered == (
        "backend/api/z.py",
        "server/y.py",
        "web/c.py",  # churn 2 beats path order
        "web/a.py",
        "web/b.py",
        "scripts/deploy.py",
        "tools/gen.py",
        "webpack.config.js",
        "vendor/lib.py",
        "web/bundle.min.js",
    )
    assert plan.batches_total == 3
    assert plan.selected == plan.ordered[:4]
    assert "churn" in plan.order and "400" in plan.order
    # Deterministic: the same input gives the same plan.
    assert batches.plan(small, list(reversed(sources)), 4, 1) == plan


def test_no_git_history_falls_back_to_class_then_path_and_says_so(tmp_path) -> None:
    _write(tmp_path, {"b.py": "", "a.py": "", "scripts/s.py": "", "vendor/v.py": ""})
    plan = batches.plan(tmp_path, ["vendor/v.py", "scripts/s.py", "b.py", "a.py"], 2, 1)
    assert plan.ordered == ("a.py", "b.py", "scripts/s.py", "vendor/v.py")
    assert "not a git repository" in plan.order


def test_generated_and_vendored_files_are_last_never_dropped(small: Path) -> None:
    # T087: third-party files (a vendor dir, a minified bundle) are excluded
    # and disclosed before batching, so they never count toward a batch.
    pack = run_dimension(code_quality.DESCRIPTOR, small, scope="project", batches="all")
    assert pack.sample.files_read == pack.sample.files_in_scope == 8
    assert not {"vendor/lib.py", "web/bundle.min.js"} & set(pack.files_read)
    assert {item.path for item in pack.excluded} == {"vendor/", "web/bundle.min.js"}


# ---------------------------------------------------------------------------
# AC1 / AC8 / SC1: batch 1 is read instead of nothing


def test_batch_one_is_200_app_files_most_churned_first(big_repo: Path) -> None:
    pack = run_dimension(code_quality.DESCRIPTOR, big_repo, scope="project")
    sample = pack.sample
    assert (sample.batches_done, sample.batches_total) == (1, 3)
    assert (sample.files_read, sample.files_in_scope) == (200, 450)
    # The batch is read first, before any document tier (whose standalone
    # code fallback may read a few more files on its own account).
    read = [p for p in dict.fromkeys(pack.files_read) if p.endswith(".py")][:200]
    assert read[:3] == list(HOT)
    assert all(p.startswith("app/") for p in read)
    assert "app/m197.py" not in read  # path order alone would have read it
    assert any(e.path.startswith("app/") for e in pack.excerpts)
    assert any("batches 1 of 3 (200 of 450 files)" in w for w in pack.warnings)
    assert not any("none were read" in w for w in pack.warnings)


def test_architecture_and_test_strategy_read_batch_one_too(big_repo: Path) -> None:
    arch = run_dimension(architecture.DESCRIPTOR, big_repo, scope="project")
    assert (arch.sample.batches_done, arch.sample.files_read) == (1, 200)
    assert any(e.path.startswith("app/") for e in arch.excerpts)

    strategy = run_dimension(test_strategy.DESCRIPTOR, big_repo, scope="project")
    assert (strategy.sample.batches_total, strategy.sample.files_in_scope) == (3, 450)
    sources = {p for p in strategy.files_read if p.startswith(("app/", "scripts/"))}
    assert len(sources) == 200
    assert not any("were not read" in w for w in strategy.warnings)


def test_test_strategy_tests_keep_their_own_read_cap(big_repo: Path) -> None:
    pack = run_dimension(test_strategy.DESCRIPTOR, big_repo, scope="project")
    tests = {p for p in pack.files_read if p.startswith("tests/")}
    assert 0 < len(tests) <= test_strategy.MAX_TEST_SOURCES


# ---------------------------------------------------------------------------
# AC3 / SC3: whole-set metrics over batches 1..N, oracle


def _oracle(repo: Path, dimension: str, paths) -> dict:
    """The metric computed directly over these files' whole text."""
    excerpts = []
    for path in paths:
        lines = (repo / path).read_text(encoding="utf-8").split("\n")
        excerpts.append(Excerpt(path, 1, len(lines), "\n".join(lines)))
    pack = EvidencePack(
        dimension=dimension,
        mode="standalone",
        scope="project",
        files_read=tuple(paths),
        excerpts=tuple(excerpts),
        sources_sought=(),
        sources_found=(),
        sources_missing=(),
        coverage_score=None,
        truncated=False,
    )
    metrics = compute_metrics(pack, curated_metric_tables())
    return {m.name: m.outcome for m in metrics}


@pytest.mark.parametrize("dimension", ["code-quality", "architecture"])
def test_metric_over_batches_one_and_two_equals_the_oracle(big_repo, dimension):
    descriptor = {"code-quality": code_quality, "architecture": architecture}[
        dimension
    ].DESCRIPTOR
    pack = run_dimension(descriptor, big_repo, scope="project", batches=2)
    plan = batches.plan(
        big_repo, list(batches_candidates(big_repo)), _code_extract.MAX_CODE_SOURCES, 2
    )
    assert len(plan.selected) == 400
    # T113: the metrics come from the code index, i.e. every one of the 450
    # sources whatever the batch count; batches now bound only the excerpts.
    expected = _oracle(big_repo, dimension, plan.ordered)
    measured = {m.name: m for m in compute_metrics(pack, curated_metric_tables())}
    for name in SAMPLED[dimension]:
        assert measured[name].outcome == expected[name], name
        assert "all 450 source files" in measured[name].derivation
        assert "sample:" not in measured[name].derivation
        assert set(measured[name].computed_from) <= set(pack.code_index_files)


def batches_candidates(repo: Path):
    return sorted(
        p.relative_to(repo).as_posix()
        for p in repo.rglob("*.py")
        if not p.relative_to(repo).as_posix().startswith(("tests/", ".git/"))
    )


def test_sampled_metrics_survive_byte_budget_truncation(big_repo: Path) -> None:
    pack = run_dimension(
        code_quality.DESCRIPTOR, big_repo, scope="project", budget_bytes=3_000
    )
    assert pack.truncated  # still reported (FR-027a)
    (share,) = compute_metrics(pack, curated_metric_tables()).by_name(
        "functions_over_ccn_10_share"
    )
    assert not share.abstained
    assert "whole text of those files" in share.derivation
    # AC9: the excerpts themselves stay within the budget.
    assert sum(len(e.text.encode()) for e in pack.excerpts) <= 3_000


def test_token_bound_each_continued_pack_stays_in_budget(big_repo: Path) -> None:
    for count in (1, 2, "all"):
        pack = run_dimension(
            code_quality.DESCRIPTOR, big_repo, scope="project", batches=count
        )
        assert sum(len(e.text.encode()) for e in pack.excerpts) <= 120_000


def test_test_strategy_metric_derivation_discloses_the_sample(big_repo) -> None:
    pack = run_dimension(test_strategy.DESCRIPTOR, big_repo, scope="project")
    (ratio,) = compute_metrics(pack, curated_metric_tables()).by_name(
        "test_to_source_ratio"
    )
    # T113: over the code index (450 sources + 5 tests), not the batch sample.
    assert "all 455 code files" in ratio.derivation
    assert "sample:" not in ratio.derivation


# ---------------------------------------------------------------------------
# AC6 / SC2: stateless, byte-equal, validated


def test_batches_all_equals_batches_total_and_replay_is_byte_equal(big_repo) -> None:
    three = _payload(big_repo, batches=3)
    assert three == _payload(big_repo, batches="all")
    assert three == _payload(big_repo, agent_input={"batches": 3})
    assert three == _payload(big_repo, batches=3)


def test_score_payload_discloses_samples(big_repo: Path) -> None:
    payload = json.loads(_payload(big_repo))
    samples = {item["dimension"]: item for item in payload["samples"]}
    assert set(samples) == {
        "architecture",
        "code-quality",
        "test-strategy",
        "reliability",  # T043: its rule metrics read the same batches
    }
    assert samples["code-quality"] == {
        "dimension": "code-quality",
        "batches_done": 1,
        "batches_total": 3,
        "files_read": 200,
        "files_in_scope": 450,
        "order": samples["code-quality"]["order"],
    }
    two = json.loads(_payload(big_repo, batches=2))
    assert {s["files_read"] for s in two["samples"]} == {400}


@pytest.mark.parametrize("bad", [0, -1, 99, 4, "x", True, 1.5, None, [2]])
def test_batches_out_of_range_or_malformed_is_a_validation_error(big_repo, bad):
    with pytest.raises(ValidationError):
        score_repository(big_repo, scope="project", agent_input={"batches": bad})


def test_batches_above_one_on_a_repo_under_the_cap_is_an_error(tmp_path) -> None:
    repo = _under_cap_repo(tmp_path)
    with pytest.raises(ValidationError, match="batches"):
        score_repository(repo, scope="project", batches=2)
    score_repository(repo, scope="project", batches="all")  # == 1, fine


def test_conflicting_cli_and_agent_input_batches_is_an_error(big_repo) -> None:
    with pytest.raises(ValidationError, match="batches"):
        score_repository(
            big_repo, scope="project", batches=2, agent_input={"batches": 3}
        )


# ---------------------------------------------------------------------------
# AC4 / SC4: MCP continue_batches round trip


def test_mcp_asks_to_continue_then_continues(big_repo: Path) -> None:
    first = mcp_server.score(repo=str(big_repo), scope="project")
    ask = first["needs_input"]["continue_batches"]
    assert {k: ask[k] for k in ask if k != "question"} == {
        "batches_done": 1,
        "batches_total": 3,
        "files_read": 200,
        "files_in_scope": 450,
    }
    assert '"batches": 2' in ask["question"] and "stop" in ask["question"]

    second = mcp_server.score(
        repo=str(big_repo), scope="project", agent_input={"batches": 2}
    )
    assert second["needs_input"]["continue_batches"]["batches_done"] == 2
    last = mcp_server.score(
        repo=str(big_repo), scope="project", agent_input={"batches": "all"}
    )
    assert "continue_batches" not in last.get("needs_input", {})


@pytest.fixture
def no_stdin(monkeypatch) -> None:
    monkeypatch.setattr("sys.stdin", io.TextIOWrapper(io.BytesIO(b"")))


@pytest.mark.usefixtures("no_stdin")
def test_mcp_and_cli_payloads_agree_apart_from_needs_input(big_repo, capsys) -> None:
    mcp = mcp_server.score(
        repo=str(big_repo), scope="project", agent_input={"batches": 2}
    )
    mcp.pop("needs_input", None)
    assert (
        cli.main(
            ["score", "--repo", str(big_repo), "--scope", "project", "--batches", "2"]
        )
        == 0
    )
    out = capsys.readouterr()
    assert json.loads(out.out) == mcp
    assert "--batches 3" in out.err and "--all" in out.err


# ---------------------------------------------------------------------------
# AC5: CLI flags


@pytest.mark.usefixtures("no_stdin")
def test_cli_all_and_validation(big_repo: Path, capsys) -> None:
    assert (
        cli.main(["score", "--repo", str(big_repo), "--scope", "project", "--all"]) == 0
    )
    out = capsys.readouterr()
    assert {s["batches_done"] for s in json.loads(out.out)["samples"]} == {3}
    assert "warning [batches]" not in out.err
    assert (
        cli.main(
            ["score", "--repo", str(big_repo), "--scope", "project", "--batches", "9"]
        )
        == cli.VALIDATION_EXIT
    )
    with pytest.raises(SystemExit):
        cli.main(["score", "--repo", str(big_repo), "--batches", "2", "--all"])


# ---------------------------------------------------------------------------
# AC7 / SC6: at or under the cap nothing changes


def test_under_the_cap_payload_is_identical_to_develop(tmp_path) -> None:
    # Snapshot regenerated for T074 (DDR-0011 architecture 10/10/40/40, code
    # evidence counts toward coverage): only architecture changed (below
    # floor -> 67) and the layer_direction_violations metric was added.
    # Regenerated for T076 (whole-file metrics at or under the cap): no rating
    # changed; the whole-file metrics cite file paths instead of excerpt refs
    # and say "all 50 source files", and type_escapes_per_kloc dropped from
    # 34 escapes / 1725 lines (overlapping excerpts counted twice) to the true
    # 17 / 1063.
    # Regenerated for T075 (DDR-0011 requirement-fidelity 10/10/40/20/20): no
    # rating or overall changed; requirement-fidelity seeks route handlers,
    # test files and git history instead of task-breakdown (coverage 0 ->
    # 0.2, still below its floor) and the three code-fact metrics were added.
    # Regenerated for T077 (requirements_doc_missing replaces the count in the
    # rating): no rating or overall changed; the requirements_doc_missing
    # metric was added (1 where the role is sought and unfilled, else abstains).
    # Regenerated for T082 (FR-073): no rating or overall changed; the payload
    # gained areas_measured and areas_without_rule, and the overall disclosure
    # gained "measured 3 of 32 evaluation areas". Nothing else differs.
    # Regenerated for T088 (behaviour layers): only the layer rule's abstention
    # text changed (framework_not_recognized: no route or DB/ORM call in the
    # fixture); every rating, value and the overall are byte-identical.
    # Merged T082 + T043 (2026-10-06): both additions above, regenerated together.
    # Regenerated for T078: only the layer_paths disclosure text changed
    # ("curated layer_paths only: ..."); every other byte is identical.
    # Regenerated for T043 (reliability dimension): every existing rating,
    # metric and the overall (61) are byte-identical; added are the
    # reliability rating (insufficient_measured_weight: no outbound call,
    # retry or query in the fixture), its pack's metrics, the four
    # reliability metrics in every pack, and reliability's warning,
    # provenance and abstained plan line.
    # Regenerated for T041 (supply-chain dimension): every existing rating,
    # metric and the overall (61) are byte-identical; added are the
    # supply-chain rating (below_coverage_floor), its four new metrics in
    # every pack, its rollback documentation result (area #22 now counts as
    # measured), and its warning, provenance and abstained plan line.
    # Regenerated for T044 (api dimension): every existing rating and the
    # overall (61) are unchanged; added are the api rating
    # (below_coverage_floor: no route, validation or spec in the fixture), its
    # four metrics in every pack, its warning, provenance and plan line, and
    # area #7 leaves areas_without_rule; the disclosure counts 10 dimensions.
    # Regenerated for T045 (data dimension): every existing rating and the
    # overall (61) are unchanged; added are the data rating
    # (below_coverage_floor: no migration, schema or data model in the
    # fixture), its four metrics in every pack, its warning, provenance and
    # plan line, and area #4 leaves areas_without_rule; 11 dimensions.
    # Regenerated for T046 (operations dimension): every existing rating and
    # the overall are unchanged; added are the operations rating, its eight
    # metrics in every pack, its documentation results, warning, provenance and
    # plan line, and areas #14/#26/#29/#30 leave areas_without_rule; 12
    # dimensions.
    # Regenerated for T042 (infrastructure dimension): every existing rating
    # and the overall (61) are unchanged; added are the infrastructure rating
    # (below_coverage_floor: no IaC in the fixture), its seven metrics in every
    # pack, its documentation result, warning, provenance and plan line, and
    # areas #11/#23/#24 leave areas_without_rule; 13 dimensions.
    # Regenerated for T089 (document roles by content): every rating, value
    # and the overall (61) are unchanged; only the three document rules'
    # derivation text changed ("N documents read; none ...").
    # Regenerated for T089 AC 10-12: every rating, value and the overall (61)
    # are unchanged; only the decision/requirements shape text changed.
    # Regenerated for T090 (request_paths): every rating, value and the overall
    # are unchanged; only the unrated request_paths metric was added, in every
    # pack like its layer sibling (no route in the fixture, so it abstains).
    # Regenerated for T092 (test-path sinks): every rating and the overall
    # are unchanged; only unrated sink_hits_observed text changed, and the
    # test-strategy pack (which holds only the one test file) now abstains
    # instead of reporting 0 (only test files were scanned).
    # Regenerated for T113 (code index): every rating, value and the overall
    # (61) are unchanged; only the six test-strategy index metrics'
    # derivations gain "; all 51 code files -- computed over the whole text
    # ..." (they now come from the index, not the pack); and every
    # top_level_import_cycles derivation names its application-source root
    # (T113 P1: a root config file no longer moves it); and (T113 AC5) a
    # derivation lists at most 20 uncovered files "(+K more)", an index
    # metric cites its first 20 files and names the full count. Values,
    # ratings and the overall unchanged.
    # Regenerated for T114 (project blast-radius): every rating, value and the
    # overall (61) are unchanged; only the blast-radius pack changed: its four
    # change-rule metrics read "not evaluated at project scope" and it adds the
    # two high-reach metrics (abstaining: no file in the fixture is imported);
    # re-regenerated after 5ac6cfc: only their method text changed.
    repo = _under_cap_repo(tmp_path)
    assert _payload(repo) == SNAPSHOT.read_text(encoding="utf-8").strip()


def test_under_the_cap_pack_has_no_sample_key(tmp_path) -> None:
    repo = _under_cap_repo(tmp_path)
    pack = run_dimension(code_quality.DESCRIPTOR, repo, scope="project")
    assert "sample" not in to_json_dict(pack)


# ---------------------------------------------------------------------------
# Edge cases


def test_secret_bearing_files_are_still_refused(small: Path) -> None:
    (small / "web/.env.py").write_text("TOKEN=FAKEfake\n", encoding="utf-8")
    pack = run_dimension(code_quality.DESCRIPTOR, small, scope="project", batches="all")
    assert "web/.env.py" not in pack.files_read
    assert not any(e.path == "web/.env.py" for e in pack.excerpts)


def test_report_card_shows_the_sample(big_repo: Path) -> None:
    result = score_repository(big_repo, scope="project")
    html = _render_score_panel(_Ctx(big_repo), result)
    assert html.count("Sample: batches 1 of 3") == 4  # + reliability (T043)
    assert "200 of 450 in-scope source files" in html
