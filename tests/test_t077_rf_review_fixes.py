"""T077 — T075 review fixes: requirement-fidelity reflects real repositories.

A missing requirements document is a failed rule (``requirements_doc_missing``);
checklist lines are plan tasks, not requirement items; route handlers survive
multi-line and stacked decorators; a target nested inside a larger git
repository reads its own history, with paths relative to itself (DDR-0011
addendum 2026-10-04).
"""

from __future__ import annotations

from pathlib import Path

from easy_verifier.core import judge
from easy_verifier.core import registry as reg
from easy_verifier.core.metrics import MetricAbstention
from easy_verifier.core.roles import GENERIC_PATTERNS
from easy_verifier.core.structure import (
    convention_values,
    find_requirement_items,
    find_routes,
    route_tokens_for,
)
from test_t075_requirement_fidelity_code_rules import (
    ROUTES_JS,
    TESTS_JS,
    _git,
    _metrics,
    _pack,
    _repo,
    _value,
    _write,
)
from test_t073_structure_patterns import _syntax, _tokens

RF = "requirement-fidelity"


# ---------------------------------------------------------------------------
# AC 1 — requirements_doc_missing replaces requirements_docs_count
# ---------------------------------------------------------------------------


def test_requirements_doc_missing_is_rated_and_the_count_is_not() -> None:
    rules = judge.RATING_RULES[RF]
    rule = rules["requirements_doc_missing"]
    assert (rule.weight, rule.threshold, rule.comparison) == (10, 0, "at_most")
    assert "29148" in rule.metric_citation[0].title
    assert "requirements_docs_count" not in rules
    assert sum(r.weight for r in rules.values()) == 100


def test_no_requirements_document_fails_and_one_passes(tmp_path) -> None:
    files = {"src/routes.js": ROUTES_JS, "test/api.test.js": TESTS_JS}
    bare = _repo(tmp_path / "bare", files)
    metric = _metrics(_pack(bare))["requirements_doc_missing"]
    assert metric.outcome == 1, metric.derivation
    assert "not filled" in metric.derivation
    # the count is still computed (unrated evidence)
    assert "requirements_docs_count" in _metrics(_pack(bare))

    documented = _repo(tmp_path / "doc", {**files, "PRD.md": "# PRD\n"})
    assert _value(_pack(documented), "requirements_doc_missing") == 0


# ---------------------------------------------------------------------------
# AC 2 — checklist lines are plan tasks, not requirement items
# ---------------------------------------------------------------------------


def test_curated_item_patterns_hold_no_checklist_line() -> None:
    values = convention_values(
        reg.load_conventions()[0], "requirement_item_patterns"
    )
    assert values  # the curated list is not empty, only checklist-free
    text = "# Plan\n\n- [ ] build the cart\n- [x] add the menu\n"
    assert find_requirement_items(text) == ()
    assert not any(value.startswith("line=- [") for value in values)
    # a repository may still declare them
    declared = find_requirement_items(text, ["line=- [ ]", "line=- [x]"])
    assert [i.text for i in declared] == ["build the cart", "add the menu"]


# ---------------------------------------------------------------------------
# AC 3 — handler names under multi-line and stacked decorators
# ---------------------------------------------------------------------------

NEST = """\
@Controller('orders')
export class OrdersController {
  @Get(':id')
  @ApiResponse({
    status: 200,
    description: 'The order',
  })
  @UseGuards(AuthGuard)
  @HttpCode(200)
  async findOne(@Param('id') id: string) {
    return id;
  }

  @Post()
  @ApiBody({ type: CreateOrderDto })
  create(@Body() dto: CreateOrderDto) {}
}
"""

SPRING = """\
@RestController
class OrderController {
  @GetMapping("/orders/{id}")
  @Operation(summary = "one order",
      description = "by id")
  @PreAuthorize("hasRole('USER')")
  @ResponseBody
  public ResponseEntity<List<Order>> getOrder(@PathVariable long id) { return null; }
}
"""

ASPNET = """\
public class OrdersController : ControllerBase
{
    [HttpGet("{id}")]
    [ProducesResponseType(typeof(Order),
        StatusCodes.Status200OK)]
    [Authorize]
    public async Task<IActionResult> GetOrder(int id) { return Ok(); }
}
"""


def test_nest_handler_survives_multi_line_and_stacked_decorators() -> None:
    routes = find_routes(NEST, _tokens("js-ts"), _syntax(".ts"))
    assert [(r.method, r.handler) for r in routes] == [
        ("GET", "findOne"),
        ("POST", "create"),
    ]


def test_spring_handler_survives_multi_line_and_stacked_annotations() -> None:
    routes = find_routes(SPRING, _tokens("java"), _syntax(".java"))
    assert [(r.method, r.path, r.handler) for r in routes] == [
        ("GET", "/orders/{id}", "getOrder")
    ]


def test_aspnet_handler_survives_multi_line_and_stacked_attributes() -> None:
    tokens = route_tokens_for(reg.load_registry(known_roles=GENERIC_PATTERNS), "csharp")
    routes = find_routes(ASPNET, tokens, _syntax(".cs"))
    assert [(r.method, r.path, r.handler) for r in routes] == [
        ("GET", "{id}", "GetOrder")
    ]


# ---------------------------------------------------------------------------
# AC 4 / 5 — a target nested inside a larger git repository
# ---------------------------------------------------------------------------


def _nested(tmp_path: Path, api_messages, outer_messages) -> Path:
    """An outer repository whose ``api/`` subdirectory is the target. Every
    api commit touches ``api/src/app.js`` and ``api/docs/guide.md``; every
    outer commit touches ``web/main.js`` only. No path outside ``api/``
    coincides with a path inside it."""
    outer = tmp_path / "outer"
    outer.mkdir()
    _git(outer, "init", "-q", "-b", "main")
    _write(outer, {"api/src/routes.js": ROUTES_JS, "web/index.js": "0;\n"})
    _git(outer, "add", "-A")
    _git(outer, "commit", "-qm", "init")
    for index, message in enumerate(api_messages):
        _write(
            outer,
            {
                "api/src/app.js": f"module.exports = {index};\n",
                "api/docs/guide.md": f"# Guide {index}\n",
            },
        )
        _git(outer, "add", "-A")
        _git(outer, "commit", "-qm", message)
    for index, message in enumerate(outer_messages):
        _write(outer, {"web/main.js": f"module.exports = {index};\n"})
        _git(outer, "add", "-A")
        _git(outer, "commit", "-qm", message)
    return outer / "api"


def test_issue_share_reads_the_targets_own_commits_with_relative_paths(
    tmp_path,
) -> None:
    target = _nested(
        tmp_path,
        [f"feat: step {i} (#{i})" for i in range(24)],
        [f"web: tweak {i}" for i in range(30)],
    )
    metric = _metrics(_pack(target))["commits_with_issue_reference_share"]
    # without --relative the changed paths are api/src/app.js, never read
    assert not isinstance(metric.outcome, MetricAbstention), metric.derivation
    assert "src/app.js" in metric.computed_from
    # sibling commits outside the target are not the target's history: 24
    # referencing commits of the target's 25 (its "init" names no issue)
    assert metric.outcome == 24 / 25, metric.derivation


def test_co_change_share_reads_the_targets_own_commits_with_relative_paths(
    tmp_path,
) -> None:
    target = _nested(
        tmp_path,
        [f"feat: step {i}" for i in range(4)],
        [f"web: tweak {i}" for i in range(6)],
    )
    metric = _metrics(_pack(target))["code_commits_with_docs_share"]
    assert not isinstance(metric.outcome, MetricAbstention), metric.derivation
    # the target's 5 code commits ("init" changed no document), not the 11
    # of the whole repository
    assert metric.outcome == 4 / 5, metric.derivation
    assert "co-changed documents cited: docs/guide.md" in metric.derivation
    assert "docs/guide.md" in metric.computed_from
