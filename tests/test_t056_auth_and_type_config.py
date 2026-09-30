"""T056 - area #8 AuthN/Z, sessions, offboarding (security) and #17 strict
type config (code-quality) (FR-051, FR-043, FR-052).

AC1: cookie-setting statements are checked for their Secure / HttpOnly /
SameSite flags from registry tokens, and the metric abstains when no cookie
statement was read, never 0. AC3: offboarding is a documentation rule the
security pack reads a document for. Each sabotage pair varies only the
predicate it pins.
"""

from __future__ import annotations

import dataclasses
import subprocess
from pathlib import Path

import pytest

from easy_verifier.core.judge import (
    AREAS,
    DOCUMENTATION_RULES,
    DocumentationRule,
)
from easy_verifier.core.metric_tables import FIELD_METRICS, curated_metric_tables
from easy_verifier.core.metrics import (
    EVIDENCE_LOCAL,
    FAMILY_SECURITY_SURFACE,
    METRIC_DEFINITIONS,
    MetricAbstention,
    compute_metrics,
)
from easy_verifier.core.models import EvidencePack, Excerpt, TruncationRecord
from easy_verifier.core.pipeline import run_dimension
from easy_verifier.core.registry import load_registry
from easy_verifier.core.roles import GENERIC_PATTERNS, documentation_present
from easy_verifier.dimensions import security

COOKIES = "cookie_flags_missing_observed"
COOKIE_FIELDS = ("cookie_calls", "cookie_secure", "cookie_httponly", "cookie_samesite")


def pack(files, *, dimension="security", truncated=False, starts=None):
    """``files`` maps path -> text; each becomes one excerpt."""
    omitted = 3 if truncated else 0
    starts = starts or {}
    return EvidencePack(
        dimension=dimension,
        mode="kit-aware",
        scope="worktree",
        files_read=tuple(files),
        excerpts=tuple(
            Excerpt(
                path,
                starts.get(path, 1),
                starts.get(path, 1) + len(text.splitlines()) - 1,
                text,
            )
            for path, text in files.items()
        ),
        sources_sought=("x",),
        sources_found=("x",),
        sources_missing=(),
        coverage_score=1.0,
        truncated=truncated,
        omitted_count=omitted,
        truncation=TruncationRecord(truncated=truncated, omitted_count=omitted),
    )


AUTH_PY = """\
from flask import session


def remember(uid):
    session["uid"] = uid
"""
"""Session code: opens the auth gate (AC2) for the pack it sits in."""


def metric(files, *, auth=True, **kwargs):
    """``auth`` adds :data:`AUTH_PY` so the cookie metric's gate is open."""
    files = {**files, "src/app/auth.py": AUTH_PY} if auth else files
    (found,) = compute_metrics(pack(files, **kwargs), curated_metric_tables()).by_name(
        COOKIES
    )
    return found


# --- declaration and registry ------------------------------------------------


def test_cookie_metric_is_declared_evidence_local_security_surface():
    (definition,) = [d for d in METRIC_DEFINITIONS if d.name == COOKIES]
    assert (definition.kind, definition.family) == (
        EVIDENCE_LOCAL,
        FAMILY_SECURITY_SURFACE,
    )


@pytest.mark.parametrize("field", COOKIE_FIELDS)
def test_every_curated_language_declares_the_cookie_fields(field):
    registry = load_registry(known_roles=GENERIC_PATTERNS)
    assert registry.warnings == ()
    lacking = [
        name
        for name, entry in registry.languages.items()
        if not entry.fields.get(field)
    ]
    assert lacking == []
    assert COOKIES in FIELD_METRICS[field]


def test_cookie_citations_are_https_links():
    registry = load_registry(known_roles=GENERIC_PATTERNS)
    for entry in registry.languages.values():
        for field in COOKIE_FIELDS:
            for cited in entry.fields[field]:
                assert cited.citation_url.startswith("https://"), (entry.name, field)


# --- AC1: flags counted where cookie code was read -------------------------

NO_HTTPONLY = """\
from flask import make_response


def login():
    resp = make_response("ok")
    resp.set_cookie("sid", "abc", secure=True, samesite="Lax")
    return resp
"""
ALL_FLAGS = NO_HTTPONLY.replace("secure=True,", "secure=True, httponly=True,")


def test_a_session_cookie_without_httponly_is_unmet_with_file_and_line():
    found = metric({"src/app/views.py": NO_HTTPONLY})
    assert found.outcome == 1
    assert "src/app/views.py:6 (no httponly)" in found.derivation
    assert found.computed_from == ("src/app/auth.py:1-5", "src/app/views.py:1-7")


def test_the_same_cookie_with_every_flag_is_zero():
    found = metric({"src/app/views.py": ALL_FLAGS})
    assert found.outcome == 0
    assert "0 of 1 cookie-setting statement(s)" in found.derivation


def test_the_reported_line_is_offset_by_the_excerpt_start():
    found = metric({"src/app/views.py": NO_HTTPONLY}, starts={"src/app/views.py": 40})
    assert "src/app/views.py:45 (no httponly)" in found.derivation


def test_a_flag_set_to_false_is_not_set():
    text = NO_HTTPONLY.replace("secure=True,", "secure=True, httponly=False,")
    assert metric({"src/app/views.py": text}).outcome == 1


def test_no_cookie_code_abstains_with_a_bounded_reason_never_zero():
    found = metric({"src/tool/cli.py": "import argparse\n\n\ndef main():\n    pass\n"})
    assert isinstance(found.outcome, MetricAbstention)
    reason = found.outcome.reason
    assert "no cookie-setting statement could be judged in 2 source-file" in reason
    assert "not the same as cookies with every flag set" in reason
    assert "framework" in reason


def test_a_cookie_call_in_a_comment_or_string_is_not_cookie_code():
    text = '# resp.set_cookie("sid", "abc")\nMSG = "resp.set_cookie(sid)"\n'
    assert isinstance(metric({"src/app/views.py": text}).outcome, MetricAbstention)


def test_a_cookie_statement_cut_by_its_excerpt_is_not_judged():
    cut = 'def f(resp):\n    resp.set_cookie("sid", "abc",\n        secure=True,\n'
    found = metric({"src/app/views.py": cut})
    assert isinstance(found.outcome, MetricAbstention)
    assert "(1 ran past the end of its excerpt)" in found.outcome.reason
    judged = metric({"src/app/views.py": cut, "src/app/other.py": NO_HTTPONLY})
    assert judged.outcome == 1
    assert "1 statement(s) ran past their excerpt" in judged.derivation


def test_cookies_set_in_test_files_are_not_counted():
    found = metric({"tests/test_views.py": NO_HTTPONLY})
    assert isinstance(found.outcome, MetricAbstention)


def test_one_statement_quoted_twice_is_counted_once():
    found = metric(
        {"src/app/views.py": NO_HTTPONLY},
    )
    twice = compute_metrics(
        dataclasses.replace(
            pack({"src/app/views.py": NO_HTTPONLY}),
            excerpts=(
                Excerpt("src/app/auth.py", 1, 5, AUTH_PY),
                Excerpt("src/app/views.py", 1, 7, NO_HTTPONLY),
                Excerpt("src/app/views.py", 6, 6, NO_HTTPONLY.split("\n")[5]),
            ),
        ),
        curated_metric_tables(),
    ).by_name(COOKIES)[0]
    assert found.outcome == twice.outcome == 1


def test_evidence_local_so_a_truncated_pack_still_counts():
    assert metric({"src/app/views.py": NO_HTTPONLY}, truncated=True).outcome == 1


@pytest.mark.parametrize(
    ("path", "unmet", "met"),
    [
        (
            "src/app/login.ts",
            "res.cookie('sid', v, { secure: true, sameSite: 'lax' });\n",
            "res.cookie('sid', v, { secure: true, httpOnly: true, "
            "sameSite: 'lax' });\n",
        ),
        (
            "internal/web/login.go",
            'http.SetCookie(w, &http.Cookie{\n\tName: "sid",\n\tSecure: true,\n'
            "\tSameSite: http.SameSiteLaxMode,\n})\n",
            'http.SetCookie(w, &http.Cookie{\n\tName: "sid",\n\tSecure: true,\n'
            "\tHttpOnly: true,\n\tSameSite: http.SameSiteLaxMode,\n})\n",
        ),
        (
            "src/main/java/app/Login.java",
            'ResponseCookie c = ResponseCookie.from("sid", v)\n    .secure(true)\n'
            '    .sameSite("Lax")\n    .build();\n',
            'ResponseCookie c = ResponseCookie.from("sid", v)\n    .secure(true)\n'
            '    .httpOnly(true)\n    .sameSite("Lax")\n    .build();\n',
        ),
        (
            "src/login.php",
            "<?php\nsetcookie('sid', $v, ['secure' => true, 'samesite' => 'Lax']);\n",
            "<?php\nsetcookie('sid', $v, ['secure' => true, 'httponly' => true, "
            "'samesite' => 'Lax']);\n",
        ),
        (
            "src/login.rs",
            'let c = Cookie::build(("sid", v)).secure(true)'
            ".same_site(SameSite::Lax);\n",
            'let c = Cookie::build(("sid", v)).secure(true).http_only(true)'
            ".same_site(SameSite::Lax);\n",
        ),
        (
            "app/login.rb",
            "response.set_cookie('sid', { value: v, secure: true, same_site: :lax })\n",
            "response.set_cookie('sid', { value: v, secure: true, httponly: true, "
            "same_site: :lax })\n",
        ),
        (
            "src/Login.cs",
            'Response.Cookies.Append("sid", v, new CookieOptions { Secure = true, '
            "SameSite = SameSiteMode.Lax });\n",
            'Response.Cookies.Append("sid", v, new CookieOptions { Secure = true, '
            "HttpOnly = true, SameSite = SameSiteMode.Lax });\n",
        ),
    ],
)
def test_other_languages_use_their_registry_tokens(path, unmet, met):
    found = metric({path: unmet})
    assert found.outcome == 1, found.derivation
    assert "(no httponly)" in found.derivation
    assert metric({path: met}).outcome == 0


# --- AC1 end to end: the security pack quotes the cookie statement ----------


def _repo(root: Path, files: dict[str, str]) -> Path:
    for relative, text in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


def _metric_over(evidence):
    return compute_metrics(evidence, curated_metric_tables()).by_name(COOKIES)[0]


def test_security_pack_quotes_a_cookie_statement_outside_auth_paths(tmp_path):
    body = "\n".join(f"X{i} = {i}" for i in range(250)) + "\n" + NO_HTTPONLY
    root = _repo(
        tmp_path / "r",
        {"src/app/views.py": body, "src/app/auth.py": AUTH_PY, "README.md": "# r\n"},
    )
    evidence = run_dimension(security.DESCRIPTOR, root, "project")
    quoted = [e for e in evidence.excerpts if e.path == "src/app/views.py"]
    line = (
        body.split("\n").index(
            '    resp.set_cookie("sid", "abc", secure=True, samesite="Lax")'
        )
        + 1
    )
    assert any(e.start_line <= line <= e.end_line and e.start_line > 1 for e in quoted)
    found = _metric_over(evidence)
    assert found.outcome == 1
    assert f"src/app/views.py:{line} (no httponly)" in found.derivation


def test_security_pack_without_cookie_code_abstains(tmp_path):
    root = _repo(
        tmp_path / "r",
        {"src/tool/cli.py": "import argparse\n\n\ndef main():\n    pass\n"},
    )
    found = _metric_over(run_dimension(security.DESCRIPTOR, root, "project"))
    assert isinstance(found.outcome, MetricAbstention)


# --- AC3: offboarding documentation rule -------------------------------------


def test_security_declares_one_offboarding_documentation_rule_for_area_8():
    (rule,) = DOCUMENTATION_RULES["security"]
    assert type(rule) is DocumentationRule
    assert rule.area == AREAS[7] == "AuthN/Z, sessions, offboarding"
    (citation,) = rule.citation
    assert "ASVS 5.0.0 V7.4.2" in citation.label
    assert not hasattr(rule, "weight") and not hasattr(rule, "threshold")


@pytest.mark.parametrize(
    "path",
    [
        "docs/offboarding.md",
        "OFFBOARDING.md",
        "ops/Deprovisioning.rst",
        "off-boarding.adoc",
    ],
)
def test_the_security_pack_reads_an_offboarding_document(tmp_path, path):
    root = _repo(tmp_path / "r", {path: "# Offboarding\nRevoke access.\n"})
    evidence = run_dimension(security.DESCRIPTOR, root, "project")
    (rule,) = DOCUMENTATION_RULES["security"]
    result = documentation_present(rule, evidence.files_read)
    assert (result.status, result.file) == ("present", path)
    assert any(e.path == path for e in evidence.excerpts)


def test_without_an_offboarding_document_the_rule_is_missing_never_a_number(tmp_path):
    root = _repo(tmp_path / "r", {"docs/onboarding.md": "# Onboarding\n"})
    evidence = run_dimension(security.DESCRIPTOR, root, "project")
    (rule,) = DOCUMENTATION_RULES["security"]
    result = documentation_present(rule, evidence.files_read)
    assert result.status == "missing"
    assert result.file is None
    assert "among the files this dimension read" in result.reason
    assert set(result.to_dict()) == {
        "kind",
        "area",
        "status",
        "file",
        "citation",
        "reason",
    }


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        env={
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@example.com",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@example.com",
            "PATH": "/usr/bin:/bin",
            "HOME": str(root),
        },
    )


def test_a_narrow_scope_does_not_read_an_offboarding_document_outside_it(tmp_path):
    root = _repo(
        tmp_path / "r",
        {"docs/offboarding.md": "# Offboarding\n", "src/app.py": "X = 1\n"},
    )
    _git(root, "init", "-q")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "init")
    (root / "src/app.py").write_text("X = 2\n", encoding="utf-8")
    _git(root, "commit", "-qam", "change")
    evidence = run_dimension(security.DESCRIPTOR, root, "changes", ref="HEAD~1..HEAD")
    assert "docs/offboarding.md" not in evidence.files_read
    (rule,) = DOCUMENTATION_RULES["security"]
    assert documentation_present(rule, evidence.files_read).status == "missing"


def test_the_offboarding_document_is_read_even_past_the_capped_sweep(tmp_path):
    files = {
        f"a/m{i:03}.py": f"X = {i}\n" for i in range(security.MAX_SECURITY_SOURCES + 5)
    }
    files["docs/offboarding.md"] = "# Offboarding\n"
    evidence = run_dimension(
        security.DESCRIPTOR, _repo(tmp_path / "r", files), "project"
    )
    (rule,) = DOCUMENTATION_RULES["security"]
    assert documentation_present(rule, evidence.files_read).status == "present"


# --- AC2: auth code presence gates the cookie metric, never scored ----------
# (user decision 2026-09-29: a gate only; CLI-only repos are never penalised)

AUTH_FIELD = "auth_markers"


def test_cookie_code_without_auth_code_abstains_naming_what_was_found():
    found = metric({"src/app/views.py": NO_HTTPONLY}, auth=False)
    assert isinstance(found.outcome, MetricAbstention)
    reason = found.outcome.reason
    assert "no authentication or session code" in reason
    assert "1 cookie-setting statement(s) were found (src/app/views.py:6)" in reason
    assert "never scored" in reason
    assert found.computed_from == ()


def test_a_cli_only_repo_abstains_naming_both_absences():
    found = metric(
        {"src/tool/cli.py": "import argparse\n\n\ndef main():\n    pass\n"},
        auth=False,
    )
    assert isinstance(found.outcome, MetricAbstention)
    reason = found.outcome.reason
    assert "no authentication or session code" in reason
    assert "no cookie-setting statement was found" in reason
    assert "in 1 source-file excerpt(s)" in reason


def test_auth_code_opens_the_gate_and_is_cited():
    found = metric({"src/app/views.py": NO_HTTPONLY})
    assert found.outcome == 1
    assert "authentication or session code was read at src/app/auth.py:5" in (
        found.derivation
    )


def test_an_auth_token_in_a_comment_or_string_does_not_open_the_gate():
    text = '# session["uid"] = 1\nMSG = "login_required"\n'
    found = metric({"src/app/views.py": NO_HTTPONLY, "src/app/x.py": text}, auth=False)
    assert isinstance(found.outcome, MetricAbstention)


def test_auth_code_in_a_test_file_does_not_open_the_gate():
    found = metric(
        {"src/app/views.py": NO_HTTPONLY, "tests/test_auth.py": AUTH_PY}, auth=False
    )
    assert isinstance(found.outcome, MetricAbstention)


@pytest.mark.parametrize(
    ("path", "text"),
    [
        ("src/auth.ts", "export const uid = req.session.uid;\n"),
        ("internal/auth.go", "func f(r *http.Request) { u, p, ok := r.BasicAuth() }\n"),
        ("src/main/java/app/Auth.java", "class Auth { void f(HttpSession s) {} }\n"),
        ("src/main/kotlin/Auth.kt", '@PreAuthorize("hasRole(\'A\')")\nfun f() {}\n'),
        ("src/auth.php", "<?php\nsession_start();\n"),
        ("app/auth.rb", "def logout\n  reset_session\nend\n"),
        ("src/auth.rs", "let m = SessionMiddleware::new(store, key);\n"),
        ("src/Auth.cs", "[Authorize]\npublic class A {}\n"),
    ],
)
def test_each_language_opens_the_gate_with_its_registry_tokens(path, text):
    opened = metric({"src/app/views.py": NO_HTTPONLY, path: text}, auth=False)
    assert opened.outcome == 1
    blank = "\n".join("" for _ in text.split("\n"))
    found = metric({"src/app/views.py": NO_HTTPONLY, path: blank}, auth=False)
    assert isinstance(found.outcome, MetricAbstention)


def test_every_curated_language_declares_auth_markers_with_https_citations():
    registry = load_registry(known_roles=GENERIC_PATTERNS)
    for entry in registry.languages.values():
        cited = entry.fields.get(AUTH_FIELD)
        assert cited, entry.name
        assert all(item.citation_url.startswith("https://") for item in cited)
    assert COOKIES in FIELD_METRICS[AUTH_FIELD]


def test_security_pack_quotes_auth_code_past_the_whole_file_excerpt(tmp_path):
    body = "\n".join(f"X{i} = {i}" for i in range(250)) + "\n" + AUTH_PY
    root = _repo(
        tmp_path / "r", {"src/app/views.py": NO_HTTPONLY, "src/app/store.py": body}
    )
    found = _metric_over(run_dimension(security.DESCRIPTOR, root, "project"))
    assert found.outcome == 1, found.derivation


# --- AC4: #17 strict type config, from targeted excerpts --------------------
# (user decision 2026-09-29: no new source role; no type-checker config abstains)

from easy_verifier.core.metric_tables import OPTIONAL_FIELDS  # noqa: E402
from easy_verifier.dimensions import code_quality  # noqa: E402

STRICT = "strict_type_config_missing"
STRICT_TS = '{\n  "compilerOptions": {\n    "strict": true\n  }\n}\n'
TYPE_FIELDS = (
    "type_config_files",
    "type_strict",
    "type_strict_off",
    "type_config_extends",
)


def strict(files, **kwargs):
    evidence = pack(files, dimension="code-quality", **kwargs)
    (found,) = compute_metrics(evidence, curated_metric_tables()).by_name(STRICT)
    return found


def test_strict_metric_is_declared_evidence_local():
    (definition,) = [d for d in METRIC_DEFINITIONS if d.name == STRICT]
    assert definition.kind == EVIDENCE_LOCAL


def test_tsconfig_without_strict_is_unmet_and_cited():
    text = '{\n  "compilerOptions": {\n    "noEmit": true\n  }\n}\n'
    found = strict({"tsconfig.json": text})
    assert found.outcome == 1
    assert "js-ts" in found.derivation
    assert "tsconfig.json" in found.derivation
    assert found.computed_from == ("tsconfig.json:1-5",)


def test_tsconfig_with_strict_is_met():
    text = '{\n  "compilerOptions": {\n    "strict": true\n  }\n}\n'
    assert strict({"tsconfig.json": text}).outcome == 0


def test_a_commented_strict_line_does_not_count():
    text = '{\n  "compilerOptions": {\n    // "strict": true\n  }\n}\n'
    assert strict({"tsconfig.json": text}).outcome == 1


def test_strict_inherited_through_extends_is_met():
    files = {
        "tsconfig.json": '{\n  "extends": "./tsconfig.base.json"\n}\n',
        "tsconfig.base.json": '{\n  "compilerOptions": { "strict": true }\n}\n',
    }
    assert strict(files).outcome == 0


def test_extends_without_the_json_suffix_and_in_another_directory():
    files = {
        "app/tsconfig.json": '{\n  "extends": "../configs/base"\n}\n',
        "configs/base.json": '{\n  "compilerOptions": {\n    "strict": true\n  }\n}\n',
    }
    assert strict(files).outcome == 0


def test_a_child_turning_strict_off_overrides_its_base():
    files = {
        "tsconfig.json": '{\n  "extends": "./tsconfig.base.json",\n'
        '  "compilerOptions": {\n    "strict": false\n  }\n}\n',
        "tsconfig.base.json": '{\n  "compilerOptions": {\n    "strict": true\n  }\n}\n',
    }
    assert strict(files).outcome == 1


def test_extends_array_last_entry_wins():
    files = {
        "tsconfig.json": '{\n  "extends": ["./a.json", "./b.json"]\n}\n',
        "a.json": '{\n  "compilerOptions": {\n    "strict": true\n  }\n}\n',
        "b.json": '{\n  "compilerOptions": {\n    "strict": false\n  }\n}\n',
    }
    assert strict(files).outcome == 1


def test_extends_a_package_config_that_was_not_read_abstains():
    found = strict({"tsconfig.json": '{\n  "extends": "@tsconfig/strictest"\n}\n'})
    assert isinstance(found.outcome, MetricAbstention)
    assert "@tsconfig/strictest" in found.outcome.reason


@pytest.mark.parametrize(
    ("path", "text", "expected"),
    [
        ("mypy.ini", "[mypy]\nstrict = True\n", 0),
        ("mypy.ini", "[mypy]\nwarn_unused_ignores = True\n", 1),
        (".mypy.ini", "[mypy]\nstrict = true\n", 0),
        ("setup.cfg", "[metadata]\nname = x\n\n[mypy]\nstrict_optional = True\n", 1),
        ("setup.cfg", "[mypy]\nstrict = True\n", 0),
        ("mypy.ini", "[mypy]\n# strict = True\n", 1),
        ("mypy.ini", "[mypy]\n\n[mypy-pkg.*]\nstrict = True\n", 1),
        ("pyproject.toml", "[tool.mypy]\nstrict = true\n\n[tool.ruff]\n", 0),
        ("pyproject.toml", "[tool.mypy]\npython_version = \"3.11\"\n", 1),
        (
            "pyproject.toml",
            "[tool.mypy]\n\n[[tool.mypy.overrides]]\nmodule = \"x\"\nstrict = true\n",
            1,
        ),
        ("pyproject.toml", '[tool.pyright]\ntypeCheckingMode = "strict"\n', 0),
        ("pyrightconfig.json", '{\n  "typeCheckingMode": "strict"\n}\n', 0),
        ("pyrightconfig.json", '{\n  "typeCheckingMode": "basic"\n}\n', 1),
    ],
)
def test_python_type_checker_configs(path, text, expected):
    found = strict({path: text})
    assert found.outcome == expected, found.derivation


def test_a_pyproject_without_a_type_checker_section_abstains():
    found = strict({"pyproject.toml": '[tool.ruff]\nline-length = 88\n'})
    assert isinstance(found.outcome, MetricAbstention)
    reason = found.outcome.reason
    assert "no type-checker configuration" in reason
    assert "command-line flags" in reason


def test_no_config_at_all_abstains_never_zero():
    found = strict({"src/app.py": "X = 1\n"})
    assert isinstance(found.outcome, MetricAbstention)


def test_a_clipped_section_without_strict_is_not_judged():
    body = "[tool.mypy]\n" + "\n".join(f"opt{i} = true" for i in range(199)) + (
        "\n…[excerpt clipped: showing lines 1–200 of 400]"
    )
    found = strict({"pyproject.toml": body})
    assert isinstance(found.outcome, MetricAbstention)


def test_each_language_counts_once():
    files = {
        "mypy.ini": "[mypy]\nstrict = True\n",
        "tsconfig.json": '{\n  "compilerOptions": {}\n}\n',
    }
    found = strict(files)
    assert found.outcome == 1
    assert "1 of 2 language(s)" in found.derivation


def test_any_strict_config_of_a_language_meets_it():
    files = {
        "pyproject.toml": '[tool.mypy]\nstrict = true\n\n[tool.pyright]\n'
        'typeCheckingMode = "basic"\n',
    }
    assert strict(files).outcome == 0


@pytest.mark.parametrize("field", TYPE_FIELDS)
def test_type_config_fields_are_optional(field):
    assert field in OPTIONAL_FIELDS
    assert STRICT in FIELD_METRICS[field]


def test_only_languages_with_a_type_checker_declare_type_config_files():
    registry = load_registry(known_roles=GENERIC_PATTERNS)
    assert registry.warnings == ()
    declaring = sorted(
        name
        for name, entry in registry.languages.items()
        if entry.fields.get("type_config_files")
    )
    assert declaring == ["js-ts", "python"]


PYPROJECT = """\
[project]
name = "demo"

[tool.poetry.source]
url = "https://example.invalid/simple"

[tool.mypy]
python_version = "3.11"

[tool.ruff]
line-length = 88
"""


def test_code_quality_pack_quotes_only_the_type_checker_section(tmp_path):
    root = _repo(tmp_path / "r", {"pyproject.toml": PYPROJECT, "src/app.py": "X = 1\n"})
    evidence = run_dimension(code_quality.DESCRIPTOR, root, "project")
    sections = [
        e for e in evidence.excerpts
        if e.path == "pyproject.toml" and e.text.startswith("[tool.mypy]")
    ]
    assert [(e.start_line, e.end_line) for e in sections] == [(7, 9)]
    assert "tool.ruff" not in sections[0].text
    assert evidence.sources_sought == code_quality.SOURCES_SOUGHT
    found = compute_metrics(evidence, curated_metric_tables()).by_name(STRICT)[0]
    assert found.outcome == 1
    assert "pyproject.toml:7-9" in found.computed_from


def test_code_quality_pack_follows_tsconfig_extends(tmp_path):
    root = _repo(
        tmp_path / "r",
        {
            "tsconfig.json": '{\n  "extends": "./configs/base"\n}\n',
            "configs/base.json": STRICT_TS,
            "src/app.ts": "export const x = 1;\n",
        },
    )
    evidence = run_dimension(code_quality.DESCRIPTOR, root, "project")
    assert "configs/base.json" in evidence.files_read
    found = compute_metrics(evidence, curated_metric_tables()).by_name(STRICT)[0]
    assert found.outcome == 0


def test_extends_never_reads_a_secret_bearing_file(tmp_path):
    root = _repo(
        tmp_path / "r",
        {
            "tsconfig.json": '{\n  "extends": "./secrets.json"\n}\n',
            "secrets.json": '{\n  "compilerOptions": {\n    "strict": true\n  }\n}\n',
        },
    )
    evidence = run_dimension(code_quality.DESCRIPTOR, root, "project")
    assert "secrets.json" not in evidence.files_read
    assert all(e.path != "secrets.json" for e in evidence.excerpts)
    found = compute_metrics(evidence, curated_metric_tables()).by_name(STRICT)[0]
    assert isinstance(found.outcome, MetricAbstention)


def test_extends_never_leaves_the_repository(tmp_path):
    tsconfig = '{\n  "extends": "../../x.json"\n}\n'
    root = _repo(tmp_path / "r", {"tsconfig.json": tsconfig})
    (tmp_path / "x.json").write_text('{"compilerOptions": {"strict": true}}\n')
    evidence = run_dimension(code_quality.DESCRIPTOR, root, "project")
    assert all(".." not in path for path in evidence.files_read)
    found = compute_metrics(evidence, curated_metric_tables()).by_name(STRICT)[0]
    assert isinstance(found.outcome, MetricAbstention)


# --- AC5: proposed weights (NOT wired: awaiting user sign-off) --------------

from easy_verifier.core import gate, judge  # noqa: E402
from easy_verifier.core.metrics import METRIC_NAMES  # noqa: E402

PROPOSED_WEIGHTS = {
    "security": {
        "redaction_hits_observed": 35,
        "sink_hits_observed": 35,
        "lockfile_missing": 15,
        COOKIES: 15,
    },
    "code-quality": {
        "functions_over_ccn_10_share": 25,
        "max_function_ccn": 15,
        "lint_config_missing": 10,
        "format_config_missing": 10,
        "type_escapes_per_kloc": 15,
        "todo_without_ticket_share": 15,
        STRICT: 10,
    },
}


@pytest.mark.parametrize("dimension", sorted(PROPOSED_WEIGHTS))
def test_proposed_weights_sum_to_100_over_real_metrics(dimension):
    proposed = PROPOSED_WEIGHTS[dimension]
    assert sum(proposed.values()) == 100
    assert set(proposed) <= set(METRIC_NAMES)
    assert set(judge.RATING_RULES[dimension]) <= set(proposed)


def test_the_new_rules_are_not_wired_before_sign_off():
    assert COOKIES not in judge.RATING_RULES["security"]
    assert STRICT not in judge.RATING_RULES["code-quality"]


def test_wiring_the_proposal_keeps_an_unknown_language_under_the_gate_cap(monkeypatch):
    rules = {dimension: dict(table) for dimension, table in judge.RATING_RULES.items()}
    for dimension, name in (("security", COOKIES), ("code-quality", STRICT)):
        rules[dimension][name] = dataclasses.replace(
            next(iter(rules[dimension].values())), metric_name=name
        )
    monkeypatch.setattr(gate, "RATING_RULES", rules)
    required = gate.required_fields()
    assert len(required) <= gate.MAX_REFERENCE_FIELDS
    assert {"cookie_calls", AUTH_FIELD} <= set(required)
    assert not {"cookie_secure", "cookie_httponly", "cookie_samesite"} & set(required)
    assert not set(TYPE_FIELDS) & set(required)


def test_configs_extending_each_other_abstain_without_looping():
    files = {
        "tsconfig.json": '{\n  "extends": "./tsconfig.b.json"\n}\n',
        "tsconfig.b.json": '{\n  "extends": "./tsconfig.json"\n}\n',
    }
    found = strict(files)
    assert isinstance(found.outcome, MetricAbstention)
    assert "cycle" in found.outcome.reason


def test_the_type_config_cap_reads_the_root_first_and_warns(tmp_path):
    files = {
        f"packages/p{i:02}/tsconfig.json": '{\n  "compilerOptions": {}\n}\n'
        for i in range(code_quality.MAX_TYPE_CONFIGS + 3)
    }
    files["tsconfig.json"] = STRICT_TS
    evidence = run_dimension(
        code_quality.DESCRIPTOR, _repo(tmp_path / "r", files), "project"
    )
    assert "tsconfig.json" in evidence.files_read
    assert any("exceed the cap" in warning for warning in evidence.warnings)
