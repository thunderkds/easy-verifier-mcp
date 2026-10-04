"""T073 — structure convention patterns (FR-068, DDR-0011).

Declared, cited, extendable pattern lists for layers, routes, requirement
items and issue references, and the pure finders over them. No score change.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from easy_verifier.core import registry as reg
from easy_verifier.core.gate import required_fields
from easy_verifier.core.metric_tables import curated_metric_tables
from easy_verifier.core.roles import (
    GENERIC_PATTERNS,
    RoleInputError,
    load_repo_config,
    load_repo_conventions,
)
from easy_verifier.core.structure import (
    Route,
    find_issue_references,
    find_requirement_items,
    find_routes,
    layer_of,
    route_tokens_for,
)

TABLES = curated_metric_tables()


def _syntax(suffix: str):
    return TABLES.syntax[suffix]


def _tokens(language: str) -> tuple[str, ...]:
    return route_tokens_for(reg.load_registry(known_roles=GENERIC_PATTERNS), language)


# --- AC1/AC2: declared, cited data in the curated registry -------------------


def test_curated_conventions_entry_is_cited_and_has_every_shared_field():
    entry, warnings = reg.load_conventions()
    assert warnings == ()
    for field in ("layer_paths", "requirement_item_patterns", "issue_reference_patterns"):
        cited = entry.fields[field]
        assert cited, field
        for item in cited:
            assert item.citation_url.startswith("https://")
            assert item.source_tag == reg.CURATED


def test_conventions_file_is_not_loaded_as_a_language():
    registry = reg.load_registry(known_roles=GENERIC_PATTERNS)
    assert "conventions" not in registry.languages
    assert registry.warnings == ()


@pytest.mark.parametrize(
    "language", ["js-ts", "python", "java", "kotlin", "csharp", "go", "rust", "php"]
)
def test_each_curated_language_declares_cited_route_tokens(language):
    entry = reg.load_registry(known_roles=GENERIC_PATTERNS).languages[language]
    cited = entry.fields["route_tokens"]
    assert all(item.citation_url.startswith("https://") for item in cited)


def test_route_tokens_is_a_registry_field_not_yet_required_by_any_rule():
    assert "route_tokens" in reg.ENTRY_FIELDS
    # No rule consumes it until T075: the reference gate must not ask for it.
    assert "route_tokens" not in required_fields()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("layer_paths", "controller=**/x/**"),  # unknown layer
        ("layer_paths", "api=/abs/**"),  # not repository-relative
        ("route_tokens", "FETCH=@Get("),  # unknown method
        ("route_tokens", "@Get("),  # no method
        ("requirement_item_patterns", "word=AC-<0-9>*"),  # unknown kind
    ],
)
def test_malformed_convention_values_are_rejected(field, value):
    assert reg.convention_value_problem(field, value) is not None


# --- success criterion 1: layer_of ---------------------------------------------


def test_layer_of_classifies_by_declared_path_patterns():
    assert layer_of("src/users/users.controller.ts") == "api"
    assert layer_of("app/models/user.py") == "data"
    assert layer_of("lib/util.js") is None


def test_layer_of_normalises_windows_separators():
    assert layer_of("app\\models\\user.py") == "data"


def test_layer_of_never_classifies_a_test_file():
    assert layer_of("src/users/users.controller.spec.ts") is None
    assert layer_of("tests/models/test_user.py") is None


def test_layer_of_leaves_a_file_matching_two_layers_unclassified():
    assert layer_of("src/a.ts", ["api=src/**", "data=**/a.ts"]) is None


# --- success criteria 2, 3: routes ---------------------------------------------

NEST = """\
import { Controller, Get } from '@nestjs/common';

@Controller('users')
export class UsersController {
  // @Post('commented') must never count
  private note = "@Delete('in a string')";

  @Get(':id')
  findOne(@Param('id') id: string) {
    return id;
  }

  @Post(
    'many')
  async createMany() {}
}
"""


def test_nest_decorator_route_with_method_path_and_handler():
    routes = find_routes(NEST, _tokens("js-ts"), _syntax(".ts"))
    assert routes[0] == Route(line=8, method="GET", path=":id", handler="findOne")


def test_decorator_split_over_lines_and_tokens_in_comments_or_strings_never_match():
    routes = find_routes(NEST, _tokens("js-ts"), _syntax(".ts"))
    assert [(r.method, r.path, r.handler) for r in routes] == [
        ("GET", ":id", "findOne"),
        ("POST", "many", "createMany"),
    ]


def test_express_router_call_route():
    text = "const router = express.Router();\nrouter.post('/orders', create);\n"
    routes = find_routes(text, _tokens("js-ts"), _syntax(".js"))
    assert routes == (Route(line=2, method="POST", path="/orders", handler="create"),)


def test_python_flask_and_django_routes():
    flask = '@app.route("/health")\ndef health():\n    return "ok"\n'
    django = 'urlpatterns = [\n    path("users/", views.user_list, name="users"),\n]\n'
    syntax = _syntax(".py")
    assert find_routes(flask, _tokens("python"), syntax) == (
        Route(line=1, method="ANY", path="/health", handler="health"),
    )
    assert find_routes(django, _tokens("python"), syntax) == (
        Route(line=2, method="ANY", path="users/", handler="user_list"),
    )


def test_spring_mapping_with_named_path_argument():
    text = (
        "@RestController\nclass C {\n"
        '  @GetMapping(value = "/users/{id}")\n'
        "  public User get(@PathVariable long id) { return null; }\n}\n"
    )
    assert find_routes(text, _tokens("java"), _syntax(".java")) == (
        Route(line=3, method="GET", path="/users/{id}", handler="get"),
    )


def test_unknown_language_or_no_syntax_finds_nothing_and_never_raises():
    assert find_routes(NEST, (), _syntax(".ts")) == ()
    assert find_routes(NEST, _tokens("js-ts"), None) == ()
    assert route_tokens_for(reg.load_registry(known_roles=GENERIC_PATTERNS), "cobol") == ()


# --- success criterion 4: requirement items -------------------------------------


def test_requirement_items_in_any_recognised_form():
    text = (
        "# Spec\n\nAC-3: the user pays.\n\n"
        "Feature: checkout\n  Scenario: pay\n\n- [ ] user can see the total\n"
    )
    items = find_requirement_items(text)
    assert [(i.line, i.text) for i in items] == [
        (3, "AC-3"),
        (6, "pay"),
        (8, "user can see the total"),
    ]


def test_requirement_ids_match_as_whole_identifiers_only():
    items = find_requirement_items("NFR-1 and FR-2 but not xFR-3")
    assert [i.text for i in items] == ["NFR-1", "FR-2"]


def test_openapi_operation_id_is_an_item():
    items = find_requirement_items("paths:\n  /u:\n    get:\n      operationId: getUser\n")
    assert [i.text for i in items] == ["getUser"]


# --- success criterion 5: issue references ---------------------------------------


def test_issue_references_in_commit_messages():
    messages = ["fix: x (#12)", "PROJ-9 add y", "chore: z"]
    found = [find_issue_references(m) for m in messages]
    assert found == [("#12",), ("PROJ-9",), ()]


def test_closing_keyword_and_issue_url_are_references():
    assert find_issue_references("Fixes #4") == ("Fixes #4",)
    assert find_issue_references(
        "see https://github.com/o/r/issues/77 for context"
    ) == ("issues/77",)


# --- AC3 / success criterion 6: extension ---------------------------------------


def test_easy_verifier_toml_extends_layer_paths(tmp_path: Path):
    (tmp_path / ".easy-verifier.toml").write_text(
        '[conventions]\nlayer_paths = ["service=src/domain/**"]\n'
    )
    assert load_repo_config(tmp_path) == {}  # roles unchanged, file valid
    config = load_repo_conventions(tmp_path)
    entry = reg.with_config_conventions(reg.load_conventions()[0], config)
    added = [c for c in entry.fields["layer_paths"] if c.source_tag != reg.CURATED]
    assert [c.source_tag for c in added] == [reg.USER_SUPPLIED]
    patterns = [v for c in entry.fields["layer_paths"] for v in c.value]
    assert layer_of("src/domain/a.ts", patterns) == "service"
    assert layer_of("src/domain/a.ts") is None  # curated alone does not know it


def test_easy_verifier_toml_rejects_a_bad_convention(tmp_path: Path):
    (tmp_path / ".easy-verifier.toml").write_text(
        '[conventions]\nlayer_paths = ["controller=src/**"]\nunknown = ["x"]\n'
    )
    with pytest.raises(RoleInputError) as caught:
        load_repo_config(tmp_path)
    assert len(caught.value.errors) == 2


def test_local_layer_conventions_add_only_and_keep_their_tag(tmp_path: Path, monkeypatch):
    (tmp_path / "conventions.toml").write_text(
        "[[requirement_item_patterns]]\n"
        'value = ["id=STORY-<0-9>*", "id=AC-<0-9>*"]\n'
        'citation_url = "https://example.org/our-process"\n'
        'source_tag = "user-supplied"\n'
    )
    monkeypatch.setenv(reg.SOT_ENV, str(tmp_path))
    entry, warnings = reg.layered_conventions()
    local = [
        c for c in entry.fields["requirement_item_patterns"] if c.source_tag != reg.CURATED
    ]
    assert [c.value for c in local] == [("id=STORY-<0-9>*",)]  # curated wins AC-
    assert local[0].source_tag == reg.USER_SUPPLIED
    assert any("curated wins" in w for w in warnings)
    patterns = [v for c in entry.fields["requirement_item_patterns"] for v in c.value]
    assert [i.text for i in find_requirement_items("STORY-7 done", patterns)] == ["STORY-7"]
    # The reserved file never becomes a language of the layered registry.
    assert "conventions" not in reg.layered_registry(known_roles=GENERIC_PATTERNS).languages
