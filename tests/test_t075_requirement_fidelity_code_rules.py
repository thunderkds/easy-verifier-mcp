"""T075 — requirement-fidelity from code + documents (DDR-0011, FR-067..072).

Documents carry 20 (requirements_docs_count 10, code_commits_with_docs_share
10), code 80: routes_without_test_share 40, commits_with_issue_reference_share
20, requirement_items_traced_share 20. The two acceptance-criteria trace rules
are gone; requirement items in any declared form replace them. The coverage
floor counts route handlers, test files and git history.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from easy_verifier.core import judge
from easy_verifier.core.metric_tables import curated_metric_tables
from easy_verifier.core.metrics import MetricAbstention, compute_metrics
from easy_verifier.core.pipeline import run_dimension
from easy_verifier.core.roles import GENERIC_PATTERNS, _config_matcher
from easy_verifier.dimensions import requirement_fidelity

RF = "requirement-fidelity"

ROUTES_JS = """const express = require('express');
const router = express.Router();
router.get('/users', listUsers);
router.get('/items/:id', getItem);
router.post('/orders', createOrder);
router.put('/carts', updateCart);
router.get('/health', health);
module.exports = router;
"""

TESTS_JS = """const request = require('supertest');
test('users', async () => { await request(app).get('/users'); });
test('item', async () => { await request(app).get('/items/3'); });
test('order', async () => { await request(app).post('/orders'); });
test('cart', async () => { await request(app).put(`/carts`); });
"""


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        env={
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@example.com",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@example.com",
            "PATH": "/usr/bin:/bin",
            "HOME": str(repo),
        },
    ).stdout


def _write(root: Path, files: dict[str, str]) -> None:
    for relative, text in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def _repo(root: Path, files: dict[str, str], messages=("init",)) -> Path:
    """A git repository whose first commit holds ``files``; every further
    message is one more commit touching ``src/log.js``."""
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "-q", "-b", "main")
    _write(root, files)
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", messages[0])
    for index, message in enumerate(messages[1:]):
        _write(root, {"src/log.js": f"module.exports = {index};\n"})
        _git(root, "add", "-A")
        _git(root, "commit", "-qm", message)
    return root


def _pack(repo: Path, budget: int = 300_000):
    return run_dimension(requirement_fidelity.DESCRIPTOR, repo, "project", budget)


def _metrics(pack) -> dict:
    return {m.name: m for m in compute_metrics(pack, curated_metric_tables()).metrics}


def _value(pack, name: str):
    metric = _metrics(pack)[name]
    assert not isinstance(metric.outcome, MetricAbstention), metric.derivation
    return metric.outcome


def _abstained(pack, name: str) -> str:
    metric = _metrics(pack)[name]
    assert isinstance(metric.outcome, MetricAbstention), metric.derivation
    return metric.derivation


# ---------------------------------------------------------------------------
# AC 1 — rules, weights, thresholds
# ---------------------------------------------------------------------------


def test_requirement_fidelity_rules_are_the_ddr_0011_table() -> None:
    rules = judge.RATING_RULES[RF]
    assert {
        name: (r.weight, r.threshold, r.comparison) for name, r in rules.items()
    } == {
        "requirements_docs_count": (10, 1, "at_most"),
        "code_commits_with_docs_share": (10, 0.30, "at_least"),
        "routes_without_test_share": (40, 0.20, "at_most"),
        "commits_with_issue_reference_share": (20, 0.50, "at_least"),
        "requirement_items_traced_share": (20, 0.80, "at_least"),
    }
    assert sum(rule.weight for rule in rules.values()) == 100
    for rule in rules.values():
        assert rule.area in judge.AREAS and rule.metric_citation
    for name in ("routes_without_test_share", "requirement_items_traced_share"):
        assert rules[name].threshold_citation == judge.PROJECT_DEFAULT


# ---------------------------------------------------------------------------
# AC 2 / 11 — routes without a test
# ---------------------------------------------------------------------------


def test_five_routes_four_tested_is_a_share_of_0_2_and_passes(tmp_path) -> None:
    repo = _repo(
        tmp_path / "r", {"src/routes.js": ROUTES_JS, "test/api.test.js": TESTS_JS}
    )
    pack = _pack(repo)
    metric = _metrics(pack)["routes_without_test_share"]
    assert metric.outcome == pytest.approx(0.2)
    assert "5 route(s)" in metric.derivation and "4 tested" in metric.derivation
    assert "/health" in metric.derivation  # the untested example
    assert "src/routes.js" in metric.computed_from
    assert "test/api.test.js" in metric.computed_from
    rule = judge.RATING_RULES[RF]["routes_without_test_share"]
    assert metric.outcome <= rule.threshold


def test_parameterised_paths_match_their_static_segments(tmp_path) -> None:
    routes = "router.get('/users/:id/orders', a);\nrouter.get('/teams/{id}', b);\n"
    tests = "get('/users/9'); get('/teams/1');\n"
    repo = _repo(tmp_path / "r", {"src/r.js": routes, "test/r.test.js": tests})
    assert _value(_pack(repo), "routes_without_test_share") == 0


def test_handler_name_is_the_fallback_and_matched_by_is_reported(tmp_path) -> None:
    controller = (
        "@Controller('orders')\nexport class OrdersController {\n"
        "  @Get(':id')\n  findOne(id: string) { return id; }\n"
        "  @Post()\n  create() { return 1; }\n}\n"
    )
    tests = "it('reads', () => apiPath(controller.findOne('1')));\n"
    repo = _repo(
        tmp_path / "r",
        {"src/orders.controller.ts": controller, "test/orders.e2e-spec.ts": tests},
    )
    metric = _metrics(_pack(repo))["routes_without_test_share"]
    assert metric.outcome == pytest.approx(0.5)
    assert "handler name 1" in metric.derivation
    assert "create" in metric.derivation  # the untested one, by handler


def test_no_route_abstains_and_says_what_was_searched(tmp_path) -> None:
    repo = _repo(tmp_path / "lib", {"src/lib.js": "module.exports = 1;\n"})
    reason = _abstained(_pack(repo), "routes_without_test_share")
    assert "no route" in reason and "source file" in reason


def test_routes_are_found_over_whole_files_when_the_budget_truncates(tmp_path) -> None:
    repo = _repo(
        tmp_path / "r",
        {
            "src/routes.js": ROUTES_JS,
            "test/api.test.js": TESTS_JS,
            "README.md": "# r\n" + "words " * 2000,
        },
    )
    pack = _pack(repo, budget=400)
    assert pack.truncated
    assert _value(pack, "routes_without_test_share") == pytest.approx(0.2)


def test_other_packs_abstain_on_the_new_metrics(tmp_path) -> None:
    from easy_verifier.dimensions import architecture

    repo = _repo(tmp_path / "r", {"src/routes.js": ROUTES_JS})
    pack = run_dimension(architecture.DESCRIPTOR, repo, "project")
    for name in (
        "routes_without_test_share",
        "commits_with_issue_reference_share",
        "requirement_items_traced_share",
    ):
        assert "requirement-fidelity pack" in _abstained(pack, name)


# ---------------------------------------------------------------------------
# AC 3 — commits with an issue reference
# ---------------------------------------------------------------------------


def test_thirty_commits_eighteen_with_references_is_0_6(tmp_path) -> None:
    messages = ["init"] + [
        f"feat: change {i} (#{i + 1})" if i < 18 else f"chore: tidy {i}"
        for i in range(29)
    ]
    # init has no reference: 18 of 30 reference an issue
    repo = _repo(tmp_path / "r", {"src/routes.js": ROUTES_JS}, messages)
    metric = _metrics(_pack(repo))["commits_with_issue_reference_share"]
    assert metric.outcome == pytest.approx(0.6)
    assert "18 of 30" in metric.derivation
    assert metric.computed_from


def test_ten_commits_abstain_below_the_declared_minimum(tmp_path) -> None:
    messages = ["init"] + [f"fix #{i}" for i in range(9)]
    repo = _repo(tmp_path / "r", {"src/routes.js": ROUTES_JS}, messages)
    reason = _abstained(_pack(repo), "commits_with_issue_reference_share")
    assert "10" in reason and "minimum of 20" in reason


def test_a_non_git_directory_abstains_on_history(tmp_path) -> None:
    _write(tmp_path, {"src/routes.js": ROUTES_JS})
    reason = _abstained(_pack(tmp_path), "commits_with_issue_reference_share")
    assert "not a git repository" in reason


# ---------------------------------------------------------------------------
# AC 4 — requirement items traced
# ---------------------------------------------------------------------------


SPEC = """# Ordering
Scenario: customer orders a latte
Scenario: customer cancels an order
Scenario: barista marks an order ready
Scenario: manager exports a report
"""


def test_four_scenarios_three_referenced_in_tests_is_0_75(tmp_path) -> None:
    tests = (
        "it('customer orders a latte', () => {});\n"
        "it('Customer cancels an order', () => {});\n"
        "it('barista marks an   order ready', () => {});\n"
    )
    repo = _repo(
        tmp_path / "r",
        {"specs/001-ordering/spec.md": SPEC, "test/order.test.js": tests},
    )
    metric = _metrics(_pack(repo))["requirement_items_traced_share"]
    assert metric.outcome == pytest.approx(0.75)
    assert "manager exports a report" in metric.derivation
    assert "specs/001-ordering/spec.md" in metric.computed_from


def test_id_items_trace_through_code_as_whole_words(tmp_path) -> None:
    prd = "# PRD\n- FR-001 list users\n- FR-002 export\n- FR-0021 other\n"
    code = "// FR-001: list users\nfunction list() {}\n// FR-00210 not it\n"
    repo = _repo(tmp_path / "r", {"PRD.md": prd, "src/users.js": code})
    assert _value(_pack(repo), "requirement_items_traced_share") == pytest.approx(1 / 3)


def test_no_requirement_item_abstains(tmp_path) -> None:
    repo = _repo(tmp_path / "r", {"src/routes.js": ROUTES_JS})
    reason = _abstained(_pack(repo), "requirement_items_traced_share")
    assert "no requirement item" in reason


# ---------------------------------------------------------------------------
# AC 5 / 6 / 7 — floor sources, document conventions, missing documents
# ---------------------------------------------------------------------------


def test_floor_sources_count_code_evidence_and_drop_task_breakdown() -> None:
    sought = requirement_fidelity.SOURCES_SOUGHT
    assert "task-breakdown" not in sought
    assert {"requirements-doc", "spec-doc"} <= set(sought)
    assert {
        requirement_fidelity.ROUTES_SOURCE,
        requirement_fidelity.TESTS_SOURCE,
        requirement_fidelity.HISTORY_SOURCE,
    } <= set(sought)


def test_routes_tests_and_history_without_documents_pass_the_floor(tmp_path) -> None:
    repo = _repo(
        tmp_path / "r", {"src/routes.js": ROUTES_JS, "test/api.test.js": TESTS_JS}
    )
    pack = _pack(repo)
    assert pack.coverage_score >= judge.COVERAGE_FLOORS[RF].value
    assert requirement_fidelity.ROUTES_SOURCE in pack.sources_found


def test_a_library_without_routes_names_the_route_miss(tmp_path) -> None:
    repo = _repo(tmp_path / "lib", {"src/lib.js": "module.exports = 1;\n"})
    pack = _pack(repo)
    assert requirement_fidelity.ROUTES_SOURCE not in pack.sources_found
    assert any(
        m.source == requirement_fidelity.ROUTES_SOURCE for m in pack.sources_missing
    )


@pytest.mark.parametrize(
    ("role", "path"),
    [
        ("spec-doc", "specs/001-orders/plan.md"),
        ("requirements-doc", "docs/requirements/orders.md"),
        ("spec-doc", "openapi.yaml"),
        ("spec-doc", "api/swagger.json"),
    ],
)
def test_document_roles_accept_common_conventions(role, path) -> None:
    assert _config_matcher(GENERIC_PATTERNS[role])(path)


def test_missing_documents_fail_the_co_change_rule_instead_of_abstaining(
    tmp_path,
) -> None:
    repo = _repo(
        tmp_path / "r", {"src/routes.js": ROUTES_JS, "test/api.test.js": TESTS_JS}
    )
    assert _value(_pack(repo), "code_commits_with_docs_share") == 0


# ---------------------------------------------------------------------------
# AC 9 — false positives carried from the T073 review
# ---------------------------------------------------------------------------


def test_encoding_hash_and_date_names_and_hex_colours_are_not_issue_references():
    from easy_verifier.core.structure import find_issue_references

    message = (
        "Read files as UTF-8, hash with SHA-256, dates in ISO-8601; "
        "colour #3a3a3a and #1e90ff. Fixes #12, see ABC-34"
    )
    assert find_issue_references(message) == ("Fixes #12", "ABC-34")
    # declared and extendable: an exclusion list a caller passes replaces it
    assert "UTF-8" in find_issue_references("UTF-8", exclusions=())


def test_a_single_argument_express_call_is_a_settings_read_not_a_route():
    from easy_verifier.core.structure import find_routes
    tables = curated_metric_tables()
    code = "const env = app.get('env');\napp.get('/users', listUsers);\n"
    routes = find_routes(code, ("GET=app.get(",), tables.syntax[".js"])
    assert [(r.path, r.handler) for r in routes] == [("/users", "listUsers")]


def test_ruby_bare_route_tokens_apply_only_in_declared_routes_files(tmp_path) -> None:
    files = {
        "config/routes.rb": "Rails.application.routes.draw do\n"
        "  get '/users', to: 'users#index'\nend\n",
        "app/services/cache.rb": "class Cache\n  def read\n    get 'key'\n"
        "    delete 'other'\n  end\nend\n",
        "spec/users_spec.rb": "get '/users'\n",
    }
    repo = _repo(tmp_path / "r", files)
    metric = _metrics(_pack(repo))["routes_without_test_share"]
    assert "0 of 1 route(s)" in metric.derivation
    assert "app/services/cache.rb" not in metric.computed_from

