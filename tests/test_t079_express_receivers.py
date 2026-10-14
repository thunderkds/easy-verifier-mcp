"""T079 — Express routes on any app/router variable bound in the same file."""

from __future__ import annotations

import pytest

from easy_verifier.core import registry as reg
from easy_verifier.core.metric_tables import curated_metric_tables
from easy_verifier.core.roles import GENERIC_PATTERNS
from easy_verifier.core.structure import Route, find_routes, route_tokens_for

SYNTAX = curated_metric_tables().syntax[".js"]
REGISTRY = reg.load_registry(known_roles=GENERIC_PATTERNS)
TOKENS = route_tokens_for(REGISTRY, "js-ts")


def _routes(text: str):
    return find_routes(text, TOKENS, SYNTAX)


def test_bound_receiver_routes_are_found():
    text = (
        "const webapp = express();\n"
        "webapp.get('/api/x', handler);\n"
        "webapp.post('/api/y', auth, other);\n"
    )
    assert _routes(text) == (
        Route(line=2, method="GET", path="/api/x", handler="handler"),
        Route(line=3, method="POST", path="/api/y", handler="other"),
    )


@pytest.mark.parametrize(
    "binding",
    [
        "var webapp = self.webapp = express();",
        "const r = express.Router();",
        "const r = Router();",
        "const r = new Router();",
        "const r: Router = Router();",
        "let r = express();",
    ],
)
def test_constructor_shapes_are_recognised(binding):
    name = "self.webapp" if "self.webapp" in binding else "r"
    routes = _routes(f"{binding}\n{name}.get('/api/x', h);\n")
    assert routes == (Route(line=2, method="GET", path="/api/x", handler="h"),)


def test_chained_assignment_binds_every_target():
    text = "var webapp = self.webapp = express();\nwebapp.get('/a', h);\n"
    assert len(_routes(text)) == 1


@pytest.mark.parametrize(
    "call",
    ["$.get('/api/x', cb);", "axios.get('/api/x', cfg);", "map.get('/k', v);"],
)
def test_unbound_receivers_are_not_routes(call):
    assert _routes(call + "\n") == ()


def test_only_the_bound_receiver_counts_when_a_client_shares_the_file():
    text = (
        "const app = express();\n$.get('/c', cb);\n"
        "app2.get('/z', h);\nzz.get('/y', h);\napi.get('/x', h);\n"
    )
    assert _routes(text) == ()  # `app` is bound, but nothing is called on it
    text += "app.get('/ok', h);\n"
    assert [r.path for r in _routes(text)] == ["/ok"]


def test_binding_in_comment_or_string_does_not_count():
    text = (
        "// const webapp = express();\n"
        'const s = "webapp = express()";\n'
        "webapp.get('/x', h);\n"
    )
    assert _routes(text) == ()


def test_one_argument_guard_applies_to_bound_receivers():
    text = "const webapp = express();\nconst v = webapp.get('setting');\n"
    assert _routes(text) == ()


def test_dollar_and_underscore_names():
    text = (
        "const $app = express();\nconst _r = Router();\n"
        "$app.get('/a', h);\n_r.get('/b', g);\n"
    )
    assert [r.path for r in _routes(text)] == ["/a", "/b"]


def test_literal_app_and_router_still_work_without_binding():
    assert [r.path for r in _routes("app.get('/a', h);\nrouter.put('/b', g);\n")] == [
        "/a",
        "/b",
    ]


def test_constructors_are_cited_registry_data():
    entry = REGISTRY.languages["js-ts"]
    cited = [
        c
        for c in entry.fields["route_tokens"]
        if any(v.startswith("RECEIVER=") for v in c.value)
    ]
    assert cited
    values = {v for c in cited for v in c.value}
    assert {
        "RECEIVER=express(",
        "RECEIVER=express.Router(",
        "RECEIVER=Router(",
    } <= values
    assert all(c.citation_url.startswith("https://expressjs.com") for c in cited)
    assert reg.convention_value_problem("route_tokens", "RECEIVER=express(") is None


# --- amendment: router-module rule (AC 7) -------------------------------------


@pytest.mark.parametrize(
    "head",
    [
        "module.exports = function (app, webapp) {",
        "module.exports = function(webapp) {",
        "module.exports = async (webapp) => {",
        "module.exports = webapp => {",
        "export default function (webapp) {",
        "export default function router(webapp = null) {",
    ],
)
def test_exported_function_parameter_binds_receiver(head):
    text = head + "\n  webapp.get('/api/a', function (req, res) {});\n};\n"
    assert [r.path for r in _routes(text)] == ["/api/a"]


@pytest.mark.parametrize(
    "assign",
    [
        "let webapp = app.webapp,",
        "var webapp = app.app;",
    ],
)
def test_property_assignment_binds_receiver(assign):
    text = (
        "module.exports = function (app) {\n"
        f"{assign}\nwebapp.post('/api/a', function (req, res) {{}});\n}};\n"
    )
    assert [r.path for r in _routes(text)] == ["/api/a"]


def test_middleware_chain_with_identifier_handler_counts():
    text = (
        "module.exports = function (app) {\n"
        "let webapp = app.webapp;\nwebapp.get('/a', auth, handler);\n};\n"
    )
    assert [r.path for r in _routes(text)] == ["/a"]


@pytest.mark.parametrize(
    "text",
    [
        "$.get('/x', cb);\n",
        "axios.get('/x', cfg);\n",
        "http.get('/x', cb);\n",
        "module.exports = function (app, webapp) {\n  webapp.get('setting');\n};\n",
        "module.exports = function (app, webapp) {\n  webapp.get(name, cb);\n};\n",
        "module.exports = function (app, webapp) {\n  webapp.get('x', cb);\n};\n",
        "const http = this.http;\nhttp.get('/x', cfg);\n",
        "const http = require('http');\nhttp.get('/x', cfg);\n",
        "function f(webapp) { webapp.get('/x', cfg); }\n",
        "module.exports = function (api) {\n  other.get('/x', cb);\n};\n",
    ],
)
def test_loose_shapes_stay_zero(text):
    assert _routes(text) == ()


def test_weak_receiver_kinds_are_cited_registry_data():
    values = {
        v for c in REGISTRY.languages["js-ts"].fields["route_tokens"] for v in c.value
    }
    assert "RECEIVER_PARAM=module.exports =" in values
    assert "RECEIVER_ASSIGN=property" in values
    assert (
        reg.convention_value_problem("route_tokens", "RECEIVER_PARAM=export default")
        is None
    )


@pytest.mark.parametrize(
    "text",
    [
        "var $ = window.jQuery;\n$.get('/api/x', function (d) { render(d); });\n",
        "const http = Vue.http;\n"
        "http.get('/api/users', (res) => { this.users = res; });\n",
        "const webapp = this.router;\nwebapp.get('/a', function () {});\n",
        "function helper(app) { var w = app.x; w.get('/a', function(){}) }\n",
    ],
)
def test_property_of_a_non_parameter_binds_nothing(text):
    assert _routes(text) == ()


def test_property_of_an_exported_parameter_or_strong_receiver_binds():
    exported = (
        "module.exports = function (app) { var webapp = app.app;"
        " webapp.get('/api/c', function (req, res) {}); }\n"
    )
    assert [r.path for r in _routes(exported)] == ["/api/c"]
    strong = (
        "const app = express();\nconst r = app.router;\n"
        "r.get('/api/d', function (req, res) {});\n"
    )
    assert [r.path for r in _routes(strong)] == ["/api/d"]
