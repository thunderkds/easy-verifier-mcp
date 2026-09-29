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


def metric(files, **kwargs):
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
    assert found.computed_from == ("src/app/views.py:1-7",)


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
    assert "no cookie-setting statement could be judged in 1 source-file" in reason
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
    root = _repo(tmp_path / "r", {"src/app/views.py": body, "README.md": "# r\n"})
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
