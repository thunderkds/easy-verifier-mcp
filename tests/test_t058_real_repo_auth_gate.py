"""T058 - the #8 cookie rule never computed on a real Express/Passport repo.

Cause 2 (tokens): a session middleware's ``cookie: {...}`` options are the
usual way an Express app sets its session cookie, and Passport's setup lines
are its session code. Cause 1 (selection): the security sweep spends its read
budget in path order, so auth code in a file whose path carries no auth
marker is never read on a repository larger than the budget.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from test_t056_auth_and_type_config import COOKIES, metric

from easy_verifier.core.metric_tables import curated_metric_tables
from easy_verifier.core.metrics import MetricAbstention, compute_metrics
from easy_verifier.core.pipeline import run_dimension
from easy_verifier.dimensions import security

# Shaped like bryony backend/server/dashboard/index.js:93-99 and 163-164.
DASHBOARD_JS = """\
var express = require('express');
var passport = require('passport');

function Dashboard(webapp, conf) {
    webapp.use(express.cookieParser('x'));

    const sessionHandler = express.session({
      secret: 'bryony',
      store: new MongoStore({url : conf.get('db')}),
      cookie: {
          maxAge: conf.get('maxAge') || 60 * 60 * 24 * 14 * 1000 // 2 weeks
      }
    });
    webapp.use(sessionHandler);

    webapp.use(passport.initialize());
    webapp.use(passport.session());
    this.authenticateMethod = _.bind(passport.authenticate, passport);
}
"""
SESSION_LINE = 7
PASSPORT_LINE = 16


def _js(text, *, auth=False):
    return metric({"server/dashboard/index.js": text}, auth=auth)


# --- cause 2: session-middleware cookies and Passport session code -----------


def test_express_session_cookie_options_are_a_cookie_statement_with_no_flags():
    found = _js(DASHBOARD_JS)
    assert found.outcome == 1
    assert (
        f"server/dashboard/index.js:{SESSION_LINE} (no secure, httponly, samesite)"
        in found.derivation
    )


def test_passport_setup_opens_the_gate_on_its_own():
    found = _js(DASHBOARD_JS, auth=False)
    assert not isinstance(found.outcome, MetricAbstention), found
    assert f"server/dashboard/index.js:{PASSPORT_LINE}" in found.derivation


def test_express_session_package_call_with_every_flag_is_zero():
    text = (
        "const session = require('express-session');\n"
        "app.use(session({\n"
        "  secret: s,\n"
        "  cookie: { secure: true, httpOnly: true, sameSite: 'lax' }\n"
        "}));\n"
    )
    found = _js(text, auth=True)
    assert found.outcome == 0


def test_express_session_without_cookie_options_leaves_every_flag_unset():
    # Framework defaults count as unset (T056 rule; no httpOnly exemption).
    found = _js("app.use(session({ secret: s }));\n", auth=True)
    assert found.outcome == 1
    assert "index.js:1 (no secure, httponly, samesite)" in found.derivation


def test_cookie_session_flags_are_judged_at_its_top_level():
    met = (
        "app.use(cookieSession({ secure: true, httpOnly: true, "
        "sameSite: 'strict' }));\n"
    )
    unmet = "app.use(cookieSession({ name: 'sid', keys: k }));\n"
    assert _js(met, auth=True).outcome == 0
    assert _js(unmet, auth=True).outcome == 1


def test_a_member_session_call_is_not_a_cookie_statement():
    text = "app.use(passport.session());\nconst s = driver.session();\n"
    found = _js(text, auth=True)
    assert isinstance(found.outcome, MetricAbstention), found
    assert "no cookie-setting statement could be judged" in found.outcome.reason


def test_session_tokens_in_comments_or_strings_do_not_count():
    text = "// app.use(session({}))\nlog('passport.initialize()');\n"
    found = _js(text, auth=False)
    assert isinstance(found.outcome, MetricAbstention)
    assert "no authentication or session code" in found.outcome.reason


def test_new_tokens_are_in_the_curated_js_tables():
    tables = curated_metric_tables()
    assert tables.cookie_calls[".js"].search("x = express.session({")
    assert tables.cookie_calls[".ts"].search("app.use(cookieSession({")
    assert tables.auth_markers[".js"].search("app.use(passport.initialize())")


# --- cause 1: content selection within the read budget -----------------------


def _repo(root: Path, files: dict[str, str]) -> Path:
    for relative, text in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


def _bryony_shaped(root: Path) -> Path:
    """Auth code in a path without an auth marker, behind path-ranked decoys
    (auth-path templates, manifests, Dockerfiles) and more alphabetically
    earlier token-free generic files than the read budget holds."""
    files = {"server/dashboard/index.js": DASHBOARD_JS, "package.json": "{}\n"}
    for i in range(20):
        files[f"frontend/modules/auth/templates/t{i:02}.hbs"] = "<form></form>\n"
        files[f"svc{i:02}/Dockerfile"] = "FROM node:8\n"
    for i in range(security.MAX_SECURITY_SOURCES + 50):
        files[f"data/keywords/k{i:03}.json"] = '{"k": 1}\n'
    return _repo(root, files)


@pytest.mark.xfail(
    strict=True,
    reason="T058 cause 1: selection by content is pending the Supervisor's "
    "design decision (a pre-screen beyond MAX_SECURITY_SOURCES vs "
    "Critical Constraint 4a)",
)
def test_auth_code_behind_the_read_budget_is_quoted_and_judged(tmp_path):
    root = _bryony_shaped(tmp_path / "r")
    evidence = run_dimension(security.DESCRIPTOR, root, "project")
    quoted = [e for e in evidence.excerpts if e.path == "server/dashboard/index.js"]
    assert any(e.start_line <= SESSION_LINE <= e.end_line for e in quoted)
    (found,) = compute_metrics(evidence, curated_metric_tables()).by_name(COOKIES)
    assert found.outcome == 1
    assert f"server/dashboard/index.js:{SESSION_LINE}" in found.derivation


def test_a_repo_without_auth_code_still_abstains_behind_decoys(tmp_path):
    root = _bryony_shaped(tmp_path / "r")
    (root / "server/dashboard/index.js").write_text("module.exports = 1;\n")
    evidence = run_dimension(security.DESCRIPTOR, root, "project")
    (found,) = compute_metrics(evidence, curated_metric_tables()).by_name(COOKIES)
    assert isinstance(found.outcome, MetricAbstention)

