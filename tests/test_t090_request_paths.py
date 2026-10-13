"""T090: each route's request path, reported and never scored (FR-077).

The unrated ``request_paths`` metric walks T088's import edges from every file
that registers a route to the nearest file that calls a DB/ORM API, citing each
hop by file:line. No rating, overall, improvement-plan item or area count reads
it (user: the database belongs to another service).
"""

from __future__ import annotations

from pathlib import Path

from test_t088_behaviour_layers import EXPRESS, ROUTE, STORE, _repo

from easy_verifier.core import metrics as metrics_module
from easy_verifier.core.metric_tables import curated_metric_tables
from easy_verifier.core.metrics import MAX_REQUEST_PATHS_LISTED, compute_metrics
from easy_verifier.core.pipeline import run_dimension
from easy_verifier.core.score import score_repository
from easy_verifier.dimensions import architecture


def _paths(root: Path, files: dict[str, str]):
    pack = run_dimension(architecture.DESCRIPTOR, _repo(root, files), "project")
    found = {m.name: m for m in compute_metrics(pack, curated_metric_tables())}
    return found["request_paths"]


def _lines(metric) -> list[str]:
    return metric.derivation.split("\n")[:-1]


def test_sc1_express_path_cites_each_hop(tmp_path) -> None:
    metric = _paths(tmp_path, EXPRESS)
    assert not metric.abstained, metric.outcome
    assert metric.outcome == 1
    assert _lines(metric) == [
        "GET /users: server/r.js:4 -> lib/svc.js:1 "
        "-> lib/store.js:4 (return User.find({});)"
    ]
    summary = metric.derivation.split("\n")[-1]
    assert (
        "1 route(s) found in 1 file(s): 0 reach a DB/ORM call in their own file, "
        "1 through at least one other in-repo module, 0 reach none" in summary
    )


def test_sc2_route_with_no_data_reach_is_listed_under_none(tmp_path) -> None:
    files = {
        **EXPRESS,
        "lib/svc.js": "function list() {\n  return [];\n}\nmodule.exports = {};\n",
    }
    metric = _paths(tmp_path, files)
    assert (
        "0 through at least one other in-repo module, 1 reach none" in metric.derivation
    )
    assert _lines(metric) == [
        "GET /users: server/r.js:4 -> reaches no file that calls a DB/ORM API"
    ]


def test_route_file_calling_the_db_itself_is_direct(tmp_path) -> None:
    text = (
        "const mongoose = require('mongoose');\n"
        "const User = mongoose.model('User', new mongoose.Schema({}));\n"
        "const express = require('express');\n"
        "const webapp = express();\n"
        "webapp.get('/direct', function (req, res) {\n"
        "  res.json(User.find({}));\n"
        "});\n"
    )
    metric = _paths(tmp_path, {"app.js": text, "lib/store.js": STORE})
    assert "1 reach a DB/ORM call in their own file, 0 through" in metric.derivation
    assert _lines(metric) == [
        "GET /direct: app.js:5 -> DB/ORM call at line 6 (res.json(User.find({}));)"
    ]


def test_import_cycle_does_not_loop_and_several_routes_share_a_file(tmp_path) -> None:
    route = ROUTE + "webapp.post('/users', function (req, res) {\n  res.end();\n});\n"
    files = {
        "server/r.js": route,
        "lib/svc.js": "const back = require('../server/r');\n"
        "const store = require('./store');\nmodule.exports = {};\n",
        "lib/store.js": "const svc = require('./svc');\n" + STORE,
    }
    metric = _paths(tmp_path, files)
    assert metric.outcome == 2
    lines = _lines(metric)
    assert lines[0].startswith(
        "GET /users: server/r.js:4 -> lib/svc.js:2 -> lib/store.js:"
    )
    assert lines[1].startswith(
        "POST /users: server/r.js:8 -> lib/svc.js:2 -> lib/store.js:"
    )


def test_listed_routes_are_capped_and_the_cap_is_disclosed(tmp_path) -> None:
    extra = "".join(
        f"webapp.get('/r{i}', function (req, res) {{ res.end(); }});\n"
        for i in range(MAX_REQUEST_PATHS_LISTED + 4)
    )
    metric = _paths(tmp_path, {**EXPRESS, "server/r.js": ROUTE + extra})
    total = MAX_REQUEST_PATHS_LISTED + 5
    assert metric.outcome == total
    assert len(_lines(metric)) == MAX_REQUEST_PATHS_LISTED
    assert (
        f"the first {MAX_REQUEST_PATHS_LISTED} of {total} routes are listed (cap)"
        in metric.derivation
    )


def test_no_route_means_abstention_not_zero(tmp_path) -> None:
    metric = _paths(
        tmp_path,
        {"lib/store.js": STORE, "lib/svc.js": "const s = require('./store');\n"},
    )
    assert metric.abstained


def test_wording_is_descriptive_only(tmp_path) -> None:
    text = _paths(tmp_path, EXPRESS).derivation.lower()
    for word in ("violation", "bad", "should"):
        assert word not in text


def test_ac4_ratings_overall_plan_and_areas_equal_with_metric_on_and_off(
    tmp_path, monkeypatch
) -> None:
    target = _repo(tmp_path, EXPRESS)
    on = score_repository(target, scope="project").to_dict()
    assert any(m["name"] == "request_paths" for m in on["metrics"]["metrics"])
    monkeypatch.setattr(
        metrics_module,
        "METRIC_DEFINITIONS",
        tuple(
            d for d in metrics_module.METRIC_DEFINITIONS if d.name != "request_paths"
        ),
    )
    off = score_repository(target, scope="project").to_dict()
    assert not any(m["name"] == "request_paths" for m in off["metrics"]["metrics"])
    for key in (
        "ratings",
        "overall",
        "improvement_plan",
        "areas_measured",
        "areas_without_rule",
    ):
        assert on[key] == off[key], key


def test_ac3_report_shows_a_folded_capped_list_in_the_architecture_card(
    tmp_path,
) -> None:
    from easy_verifier.core.report import write_report
    from easy_verifier.core.score import report_dimensions
    from easy_verifier.core.synthesis import combined_pack

    target = _repo(tmp_path, EXPRESS)
    result = write_report(
        [], combined_pack(report_dimensions(target)[0], target, "project"), target
    )
    document = (target / result.path).read_text(encoding="utf-8")
    assert (
        '<details class="request-paths"><summary>Request paths: 1 route(s)' in document
    )
    assert "reported only, not scored" in document
    assert (
        "GET /users: server/r.js:4 -&gt; lib/svc.js:1 -&gt; lib/store.js:4" in document
    )
