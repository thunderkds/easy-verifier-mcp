"""T114: blast-radius rated at project scope from the repository import graph.

Synthetic repositories only. The graph is known: ``src/core.ts`` and
``src/util.ts`` are each imported by alpha/beta/gamma/delta (fan-in 4),
``src/helper.ts`` by delta (fan-in 1); a test imports core; ``util.ts`` is the
churn hotspot.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from easy_verifier.core.score import score_repository

HIGH_REACH = ("high_reach_files_without_test_share", "high_reach_churn_hotspot_share")
CHANGE_RULES = (
    "max_fan_in_changed",
    "changed_files_in_churn_hotspots_share",
    "public_symbols_removed",
    "destructive_migration_ops",
)

IMPORTERS = ("alpha", "beta", "gamma")


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.email=t@example.invalid", "-c", "user.name=t", *args],
        cwd=repo,
        check=True,
        capture_output=True,
    )


def _make_repo(root: Path, *, commits: int = 24, test_text: str | None = None) -> Path:
    (root / "src").mkdir(parents=True)
    (root / "tests").mkdir()
    (root / "node_modules" / "lib").mkdir(parents=True)
    (root / "package.json").write_text('{"name": "synth", "version": "1.0.0"}\n')
    (root / "src" / "core.ts").write_text(
        "export function coreValue() {\n  return 1;\n}\n"
    )
    (root / "src" / "util.ts").write_text(
        "export function formatThing(x: number) {\n  return String(x);\n}\n"
    )
    (root / "src" / "helper.ts").write_text(
        "export function helperCall() {\n  return 2;\n}\n"
    )
    for name in IMPORTERS:
        (root / "src" / f"{name}.ts").write_text(
            "import express from 'express';\n"
            "import { coreValue } from './core';\n"
            "import { formatThing } from './util';\n"
            f"export const {name} = formatThing(coreValue());\n"
        )
    (root / "src" / "delta.ts").write_text(
        "import { coreValue } from './core';\n"
        "import { formatThing } from './util';\n"
        "import { helperCall } from './helper';\n"
        "export const delta = formatThing(coreValue() + helperCall());\n"
    )
    # Third-party: never an importer, so helper's fan-in stays 1.
    (root / "node_modules" / "lib" / "index.js").write_text(
        "const h = require('../../src/helper');\nmodule.exports = h;\n"
    )
    (root / "tests" / "core.test.ts").write_text(
        test_text
        or "import { coreValue } from '../src/core';\n"
        "test('core', () => { expect(coreValue()).toBe(1); });\n"
    )
    subprocess.run(["git", "init", "-q", "."], cwd=root, check=True)
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "init")
    for i in range(commits):
        with (root / "src" / "util.ts").open("a") as handle:
            handle.write(f"// {i}\n")
        _git(root, "commit", "-qam", f"c{i}")
    return root


def _blast(result):
    rating = next(r for r in result.ratings if r.dimension == "blast-radius")
    metrics = {
        m.name: m for m in result.metrics if m.dimension == "blast-radius"
    }
    return rating, metrics


def _rows(metric) -> dict[str, list[str]]:
    *rows, _summary = metric.derivation.split("\n")
    return {row.split(" | ")[0]: row.split(" | ")[1:] for row in rows}


# AC1 -------------------------------------------------------------------------


def test_fan_in_over_the_resolver_gives_the_exact_table():
    from easy_verifier.core.metrics import import_fan_in

    files = ["src/core.ts", "src/util.ts", "src/helper.ts", "src/alpha.ts"]
    statements = [
        ("src/alpha.ts", "import { coreValue } from './core';"),
        ("src/alpha.ts", "import { formatThing } from './util';"),
        ("src/alpha.ts", "import express from 'express';"),
        ("src/helper.ts", "import { coreValue } from './core';"),
        ("src/core.ts", "import { x } from './core';"),  # self: never an edge
    ]
    assert import_fan_in(files, statements) == {
        "src/core.ts": frozenset({"src/alpha.ts", "src/helper.ts"}),
        "src/util.ts": frozenset({"src/alpha.ts"}),
    }


def test_fan_in_matches_whole_words_only_and_skips_shared_names():
    from easy_verifier.core.metrics import import_fan_in

    files = ["a/user.ts", "b/user.ts", "src/user.service.ts", "src/main.ts"]
    statements = [
        ("src/main.ts", "import { u } from './user';"),  # shared stem: no edge
        ("src/main.ts", "import { s } from './user.service';"),
        ("src/main.ts", "import { m } from './users';"),
    ]
    assert import_fan_in(files, statements) == {
        "src/user.service.ts": frozenset({"src/main.ts"}),
    }


def test_project_payload_states_the_known_fan_in_table(tmp_path):
    repo = _make_repo(tmp_path / "repo")
    _rating, metrics = _blast(score_repository(repo, scope="project"))
    rows = _rows(metrics["high_reach_files_without_test_share"])
    assert {path: cells[0] for path, cells in rows.items()} == {
        "src/core.ts": "fan-in 4",
        "src/util.ts": "fan-in 4",
    }
    assert "over the whole text of all 7 application source files" in (
        metrics["high_reach_files_without_test_share"].derivation
    )


def test_a_file_is_named_only_by_a_specifier_last_segment():
    """Real-repo precision (AC7 spot checks): a directory segment, a hyphenated
    piece or an imported binding never names a file; an extension does not
    hide one; a dotted module name is named by its last segment."""
    from easy_verifier.core.metrics import import_fan_in

    files = [
        "src/auth.ts", "utils/service.js", "src/dtos/index.ts", "src/util.ts",
        "pkg/core/__init__.py", "pkg/core/config.py", "src/main.ts", "app/run.py",
    ]
    statements = [
        ("src/main.ts", "import { x } from './auth/guards/jwt-auth.guard';"),
        ("src/main.ts", "const s = require('../platform/base-mongodb-service');"),
        ("src/main.ts", "import { service } from '../dtos/user.dto';"),
        ("src/main.ts", "const u = require('./util.js');"),
        ("app/run.py", "from pkg.core.config import settings"),
        ("app/run.py", "import pkg.core"),
    ]
    assert import_fan_in(files, statements, suffixes={".ts", ".js", ".py"}) == {
        "src/util.ts": frozenset({"src/main.ts"}),
        "pkg/core/config.py": frozenset({"app/run.py"}),
        "pkg/core/__init__.py": frozenset({"app/run.py"}),
    }


# AC2 -------------------------------------------------------------------------


def test_high_reach_is_top_ten_percent_ties_included_minimum_three():
    from easy_verifier.core.metrics import high_reach_files

    fan_in = {f"f{i}.ts": 3 for i in range(5)} | {"top.ts": 9, "low.ts": 2}
    # 30 sources -> top 3; the third place is a tie at 3: all five tie in.
    assert high_reach_files(fan_in, 30) == [
        "top.ts", "f0.ts", "f1.ts", "f2.ts", "f3.ts", "f4.ts"
    ]
    # 5 sources -> top 1 (at least one file).
    assert high_reach_files(fan_in, 5) == ["top.ts"]
    assert high_reach_files({"a.ts": 2, "b.ts": 1}, 4) == []


def test_no_file_with_fan_in_three_abstains_both_rules_with_a_reason(tmp_path):
    repo = _make_repo(tmp_path / "repo")
    for name in ("beta", "gamma"):
        (repo / "src" / f"{name}.ts").write_text(f"export const {name} = 1;\n")
    _git(repo, "commit", "-qam", "fewer imports")
    rating, metrics = _blast(score_repository(repo, scope="project"))
    for name in HIGH_REACH:
        reason = metrics[name].outcome.reason
        assert "imported by at least 3 other in-repo source files" in reason
        assert "highest fan-in 2 over 7 files" in reason
    assert rating.reason_code == "all_metrics_abstained"
    assert [name for name, _ in rating.unavailable_metrics] == list(HIGH_REACH)


# AC3 -------------------------------------------------------------------------


def test_coverage_by_name_and_uncovered_files_cited_with_fan_in(tmp_path):
    repo = _make_repo(tmp_path / "repo")
    rating, metrics = _blast(score_repository(repo, scope="project"))
    metric = metrics["high_reach_files_without_test_share"]
    assert metric.outcome == 0.5
    rows = _rows(metric)
    assert rows["src/core.ts"][2] == "tested by tests/core.test.ts (name)"
    assert rows["src/util.ts"][2] == "no covering test"
    assert "1 of 2 high-reach file(s) have no covering test: src/util.ts " \
        "(fan-in 4, churn 25 (hotspot))" in metric.derivation
    assert set(metric.computed_from) == {"src/core.ts", "src/util.ts"}


def test_a_test_naming_a_public_symbol_covers_the_file(tmp_path):
    repo = _make_repo(
        tmp_path / "repo",
        test_text="import { coreValue } from '../src/core';\n"
        "import { formatThing } from '../src/util';\n"
        "test('both', () => { expect(formatThing(coreValue())).toBe('1'); });\n",
    )
    _rating, metrics = _blast(score_repository(repo, scope="project"))
    metric = metrics["high_reach_files_without_test_share"]
    assert metric.outcome == 0.0
    assert _rows(metric)["src/util.ts"][2] == (
        "tested by tests/core.test.ts (symbol formatThing)"
    )


def test_a_symbol_named_by_another_projects_test_does_not_cover(tmp_path):
    repo = _make_repo(tmp_path / "repo")
    (repo / "other").mkdir()
    (repo / "other" / "package.json").write_text('{"name": "other"}\n')
    (repo / "other" / "fmt.test.ts").write_text(
        "test('fmt', () => { expect(formatThing(1)).toBe('1'); });\n"
    )
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "other project")
    _rating, metrics = _blast(score_repository(repo, scope="project"))
    rows = _rows(metrics["high_reach_files_without_test_share"])
    assert rows["src/util.ts"][2] == "no covering test"


# AC4 -------------------------------------------------------------------------


def test_churn_share_uses_the_repository_ranking(tmp_path):
    repo = _make_repo(tmp_path / "repo")
    rating, metrics = _blast(score_repository(repo, scope="project"))
    metric = metrics["high_reach_churn_hotspot_share"]
    assert metric.outcome == 0.5
    assert "src/util.ts (fan-in 4, churn 25 (hotspot))" in metric.derivation
    assert rating.value == 0  # both rules fail: 0.5 > 0.20 and 0.5 > 0.30


def test_churn_rule_abstains_below_min_churn_commits(tmp_path):
    repo = _make_repo(tmp_path / "repo", commits=3)
    rating, metrics = _blast(score_repository(repo, scope="project"))
    reason = metrics["high_reach_churn_hotspot_share"].outcome.reason
    assert "only 4 local commit(s), fewer than the 20 a churn ranking needs" in reason
    # The test rule alone is half the group's weight: the dimension still rates.
    assert [i.metric_name for i in rating.inputs] == [HIGH_REACH[0]]


def test_churn_rule_abstains_on_a_shallow_clone(tmp_path):
    origin = _make_repo(tmp_path / "origin")
    clone = tmp_path / "clone"
    subprocess.run(
        ["git", "clone", "-q", "--depth", "1", origin.as_uri(), str(clone)],
        check=True,
        capture_output=True,
    )
    _rating, metrics = _blast(score_repository(clone, scope="project"))
    reason = metrics["high_reach_churn_hotspot_share"].outcome.reason
    assert "this is a shallow clone" in reason


# AC5 -------------------------------------------------------------------------


def test_rules_are_declared_project_defaults_with_an_area():
    from easy_verifier.core.judge import AREAS, PROJECT_DEFAULT, RATING_RULES

    rules = RATING_RULES["blast-radius"]
    assert (rules[HIGH_REACH[0]].threshold, rules[HIGH_REACH[1]].threshold) == (
        0.20,
        0.30,
    )
    for name in HIGH_REACH:
        assert rules[name].comparison == "at_most"
        assert rules[name].threshold_citation == PROJECT_DEFAULT
        assert rules[name].area == AREAS[4]


def test_project_rating_holds_only_the_high_reach_rules(tmp_path):
    repo = _make_repo(tmp_path / "repo")
    result = score_repository(repo, scope="project")
    rating, metrics = _blast(result)
    assert [i.metric_name for i in rating.inputs] == list(HIGH_REACH)
    assert rating.unavailable_metrics == ()
    for name in CHANGE_RULES:
        assert "not evaluated at project scope" in metrics[name].outcome.reason
    from easy_verifier.core.judge import AREAS

    assert AREAS[4] in result.areas_measured


def test_report_renders_the_high_reach_table(tmp_path):
    from easy_verifier.core.report import write_report
    from easy_verifier.core.score import report_dimensions
    from easy_verifier.core.synthesis import combined_pack

    repo = _make_repo(tmp_path / "repo")
    result = write_report(
        [], combined_pack(report_dimensions(repo)[0], repo, "project"), repo
    )
    document = (repo / result.path).read_text(encoding="utf-8")
    assert '<details class="high-reach"><summary>High-reach files: 2 listed' in (
        document
    )
    assert (
        "<tr><td>src/util.ts</td><td>fan-in 4</td><td>churn 25 (hotspot)</td>"
        "<td>no covering test</td></tr>" in document
    )


# AC6 -------------------------------------------------------------------------


def test_narrow_scopes_list_no_high_reach_metric_and_hold_the_change_rules(
    tmp_path,
):
    repo = _make_repo(tmp_path / "repo")
    (repo / "src" / "core.ts").write_text(
        "export function coreValue() {\n  return 2;\n}\n"
    )
    for scope, ref in (("worktree", None), ("changes", "HEAD~1..HEAD")):
        if scope == "changes":
            _git(repo, "commit", "-qam", "change core")
        result = score_repository(repo, scope=scope, ref=ref)
        payload = json.dumps(result.to_dict())
        assert "high_reach" not in payload
        rating, metrics = _blast(result)
        held = {i.metric_name for i in getattr(rating, "inputs", ())} | {
            name for name, _ in rating.unavailable_metrics
        }
        assert held == set(CHANGE_RULES), scope
        assert not set(metrics) & set(HIGH_REACH)
