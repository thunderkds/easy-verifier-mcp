"""T087 -- third-party code is excluded from evaluation and disclosed (FR-074,
DDR-0012 §5).

Every reason kind (linguist-pattern, gitattributes, declared, nested-project)
has a fixture, and the nested-project predicate is pinned to both extremes:
the SC 5 sabotage (remove NOTICE) must flip it, and a monorepo package with
only its own LICENSE must never trip it.
"""

from __future__ import annotations

import importlib.util
import io
import json
import subprocess
from pathlib import Path

import pytest

from easy_verifier.adapters import cli, mcp_server
from easy_verifier.core.context import _walk, detect_context
from easy_verifier.core.findings import ValidationError
from easy_verifier.core.models import to_json_dict
from easy_verifier.core.pipeline import run_dimension
from easy_verifier.core.report import _Ctx, _render_score_panel
from easy_verifier.core.roles import (
    GENERIC_PATTERNS,
    resolve,
    role,
    validate_agent_input,
)
from easy_verifier.core.scope import resolve_scope, third_party_filter
from easy_verifier.core.score import score_repository
from easy_verifier.dimensions import code_quality, security

REPO_ROOT = Path(__file__).resolve().parent.parent
VENDORED = REPO_ROOT / "src" / "easy_verifier" / "registry" / "vendored"
SCRIPT = REPO_ROOT / "scripts" / "vendor_sources.py"


def _write(root: Path, files: dict[str, str]) -> Path:
    for relative, text in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


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
            "HOME": str(repo),
            "PATH": "/usr/bin:/bin",
        },
    ).stdout


def _project(repo: Path):
    return resolve_scope("project", repo, detect_context(repo))


def _roots(scope) -> dict[str, tuple[str, str]]:
    return {item.path: (item.reason, item.rule) for item in scope.excluded}


APP = {"README.md": "# App\n", "app/main.py": "def main():\n    return 1\n"}

HARBOR = {
    "third/harbor/LICENSE": "Apache License\n",
    "third/harbor/NOTICE": "Harbor\n",
    "third/harbor/api/a.go": "package api\n",
}


# ---------------------------------------------------------------------------
# SC 1 / AC 1: Linguist third-party patterns


def test_linguist_patterns_exclude_vendor_dir_and_minified_bundle(tmp_path):
    repo = _write(
        tmp_path,
        {**APP, "vendor/lib.js": "var x;\n", "app/x.min.js": "var y;\n"},
    )
    scope = _project(repo)
    assert "vendor/lib.js" not in scope.files
    assert "app/x.min.js" not in scope.files
    assert "app/main.py" in scope.files
    roots = _roots(scope)
    assert roots["vendor/"] == (
        "linguist-pattern",
        "linguist vendor.yml: (^|/)vendors?/",
    )
    assert roots["app/x.min.js"][0] == "linguist-pattern"
    assert "min" in roots["app/x.min.js"][1]


@pytest.mark.parametrize(
    "path",
    ["third_party/a.c", "lib/3rd-party/b.c", "node_modules/c/i.js", "web/vendors/d.js"],
)
def test_linguist_patterns_cover_the_named_dependency_dirs(tmp_path, path):
    assert third_party_filter(tmp_path)(path) is not None


@pytest.mark.parametrize(
    "path",
    [
        ".github/workflows/ci.yml",  # kitchd CI
        "src/types/express.d.ts",  # coffee-shop-api hand-written types
        "backend/scripts/companies/external/mark-public/a.js",  # bryony
        "frontend/app/scripts/config/bootstrap.conf.js",  # bryony
        "backend/utils/db-entity/prototype.js",  # bryony
        "design/src/files/styles/base/__import.scss",  # bryony
        "backend/bin/fabric/fabfile.py",
        "tests/fixtures/data.json",
        "pkg/testdata/x.txt",
        "package-lock.json",
        "poetry.lock",
        "Jenkinsfile",
        ".gitignore",
    ],
)
def test_dropped_categories_never_exclude_team_files(tmp_path, path):
    """AC 1 Option A: what vendor.yml lists for language statistics but a team
    writes itself stays in. Lockfiles are never excluded (no 'generated')."""
    assert third_party_filter(tmp_path)(path) is None


def test_vendored_snapshot_is_filtered_cited_and_checksummed():
    data = json.loads((VENDORED / "linguist_vendor.json").read_text(encoding="utf-8"))
    assert data["meta"]["license"] == "MIT"
    assert "d0921d10bb68a1249fc9eac64e472759f36e2fd8" in data["meta"]["source_url"]
    kept = {p for item in data["kept"] for p in item["patterns"]}
    for required in (
        "(^|/)node_modules/",
        "(^|/)vendors?/",
        "(3rd|[Tt]hird)[-_]?[Pp]arty/",
        "(\\.|-)min\\.(js|css)$",
        "(^|/)Carthage/",
        "(^|/)flow-typed/.*\\.js$",
    ):
        assert required in kept
    for dropped in (
        "(^|/)\\.github/",
        "(.*?)\\.d\\.ts$",
        "(^|/)[Ee]xtern(als?)?/",
        "(^|/)dist/",
    ):
        assert dropped not in kept
    notice = (VENDORED / "NOTICE").read_text(encoding="utf-8")
    for item in data["kept"]:
        assert f"kept    {item['category']} -- " in notice
    for item in data["dropped"]:
        assert f"dropped {item['category']}" in notice
    checksums = (VENDORED / "CHECKSUMS.sha256").read_text(encoding="utf-8")
    assert "  linguist_vendor.json" in checksums


def test_vendor_script_fails_loudly_on_an_unclassified_category():
    spec = importlib.util.spec_from_file_location("vendor_sources_t087", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    upstream = "".join(
        f"# {name.split(' / ', 1)[1]}\n- (^|/)x{i}/\n"
        for i, name in enumerate(module.VENDOR_CATEGORIES)
        if name.startswith("Vendor Conventions")
    )
    categories = module._parse_vendor_yml(upstream + "# Brand new category\n- y/\n")
    with pytest.raises(module.UpstreamFormatError):
        module._filter_vendor(categories * 3)


# ---------------------------------------------------------------------------
# SC 2 / AC 2: .gitattributes


def test_gitattributes_linguist_generated_excludes_its_paths(tmp_path):
    repo = _write(
        tmp_path,
        {
            **APP,
            ".gitattributes": "gen/** linguist-generated\n",
            "gen/api.py": "x = 1\n",
        },
    )
    scope = _project(repo)
    assert "gen/api.py" not in scope.files
    assert _roots(scope)["gen/"] == (
        "gitattributes",
        ".gitattributes: gen/** linguist-generated",
    )


@pytest.mark.parametrize("token", ["-linguist-vendored", "linguist-vendored=false"])
def test_gitattributes_unset_re_includes_a_default_exclusion(tmp_path, token):
    repo = _write(
        tmp_path,
        {
            **APP,
            ".gitattributes": f"vendor/ours.js {token}\n",
            "vendor/ours.js": "var ours;\n",
            "vendor/theirs.js": "var theirs;\n",
        },
    )
    scope = _project(repo)
    assert "vendor/ours.js" in scope.files
    assert "vendor/theirs.js" not in scope.files


@pytest.mark.parametrize("token", ["!linguist-vendored", "-linguist-generated"])
def test_unspecified_or_other_attribute_does_not_re_include(tmp_path, token):
    repo = _write(
        tmp_path,
        {**APP, ".gitattributes": f"vendor/** {token}\n", "vendor/theirs.js": "v\n"},
    )
    assert "vendor/theirs.js" not in _project(repo).files


def test_gitattributes_last_matching_line_and_deeper_file_win(tmp_path):
    repo = _write(
        tmp_path,
        {
            **APP,
            ".gitattributes": "*.py linguist-generated\n*.py -linguist-generated\n",
            "sub/.gitattributes": "*.py linguist-generated\n",
            "sub/a.py": "a = 1\n",
            "b.py": "b = 1\n",
        },
    )
    scope = _project(repo)
    assert "b.py" in scope.files  # root file: last line unsets
    assert "sub/a.py" not in scope.files  # sub/.gitattributes applies below it
    assert (
        _roots(scope)["sub/a.py"][1] == "sub/.gitattributes: **/*.py linguist-generated"
    )


def test_subdirectory_gitattributes_applies_only_below_it(tmp_path):
    repo = _write(
        tmp_path,
        {
            **APP,
            "sub/.gitattributes": "*.py linguist-vendored\n",
            "sub/a.py": "a = 1\n",
            "other/a.py": "a = 1\n",
        },
    )
    scope = _project(repo)
    assert "other/a.py" in scope.files
    assert "sub/a.py" not in scope.files


def test_directory_only_and_quoted_gitattributes_lines_exclude_nothing(tmp_path):
    repo = _write(
        tmp_path,
        {
            **APP,
            ".gitattributes": 'lib/ linguist-vendored\n"lib/*" linguist-vendored\n',
            "lib/a.py": "a = 1\n",
        },
    )
    assert "lib/a.py" in _project(repo).files


# ---------------------------------------------------------------------------
# AC 3: declared in .easy-verifier.toml


def test_declared_exclude_glob(tmp_path):
    repo = _write(
        tmp_path,
        {
            **APP,
            ".easy-verifier.toml": 'exclude = ["legacy/**", "**/*.gen.ts"]\n',
            "legacy/old.py": "x = 1\n",
            "web/a.gen.ts": "x\n",
        },
    )
    scope = _project(repo)
    roots = _roots(scope)
    assert roots["legacy/"] == ("declared", ".easy-verifier.toml exclude: legacy/**")
    assert roots["web/a.gen.ts"] == (
        "declared",
        ".easy-verifier.toml exclude: **/*.gen.ts",
    )
    assert "app/main.py" in scope.files


@pytest.mark.parametrize(
    "value",
    ['["../outside/**"]', '["/abs/**"]', '["a**b"]', '["*/*/*/*/*"]', '"legacy/**"'],
)
def test_invalid_declared_exclude_is_a_rejected_config(
    tmp_path, value, capsys, monkeypatch
):
    monkeypatch.setattr("sys.stdin", io.TextIOWrapper(io.BytesIO(b"")))
    repo = _write(tmp_path, {**APP, ".easy-verifier.toml": f"exclude = {value}\n"})
    with pytest.raises(ValidationError, match="exclude"):
        _project(repo)
    with pytest.raises(ValidationError, match="exclude"):
        score_repository(repo, scope="project")
    assert (
        cli.main(["score", "--repo", str(repo), "--scope", "project"])
        == cli.VALIDATION_EXIT
    )


# ---------------------------------------------------------------------------
# SC 3-5 / AC 4, AC 6: nested third-party project roots, both extremes


def test_nested_project_root_is_excluded_with_everything_below(tmp_path):
    repo = _write(tmp_path, {**APP, **HARBOR})
    scope = _project(repo)
    assert not [p for p in scope.files if p.startswith("third/harbor/")]
    assert _roots(scope) == {"third/harbor/": ("nested-project", "LICENSE + NOTICE")}


def test_sabotage_removing_notice_un_excludes_the_root(tmp_path):
    """SC 5: the predicate is not hard-wired -- the same fixture minus NOTICE
    keeps every Harbor file in scope."""
    files = {**APP, **HARBOR}
    del files["third/harbor/NOTICE"]
    scope = _project(_write(tmp_path, files))
    assert "third/harbor/api/a.go" in scope.files
    assert scope.excluded == ()


def test_monorepo_package_with_only_its_own_licence_is_not_excluded(tmp_path):
    repo = _write(
        tmp_path,
        {
            **APP,
            "packages/shared/LICENSE": "MIT\n",
            "packages/shared/package.json": '{"name": "shared"}\n',
            "packages/shared/index.ts": "export const x = 1;\n",
        },
    )
    scope = _project(repo)
    assert "packages/shared/index.ts" in scope.files
    assert scope.excluded == ()


@pytest.mark.parametrize(
    ("licence", "project", "excluded"),
    [
        ("COPYING", "AUTHORS", True),
        ("LICENSE.txt", "CONTRIBUTORS.md", True),
        (None, "NOTICE", False),  # no licence: not a project root
        ("license", "notice", False),  # case-sensitive, as written in AC 4
    ],
)
def test_nested_predicate_needs_a_licence_and_a_project_file(
    tmp_path, licence, project, excluded
):
    files = {**APP, "dep/x.go": "package x\n", f"dep/{project}": "people\n"}
    if licence:
        files[f"dep/{licence}"] = "licence\n"
    scope = _project(_write(tmp_path, files))
    assert ("dep/x.go" not in scope.files) is excluded


def test_repo_root_is_never_a_nested_project(tmp_path):
    repo = _write(tmp_path, {**APP, "LICENSE": "MIT\n", "NOTICE": "n\n"})
    scope = _project(repo)
    assert "app/main.py" in scope.files
    assert scope.excluded == ()


def test_nested_root_inside_an_excluded_dir_is_disclosed_once(tmp_path):
    repo = _write(
        tmp_path,
        {
            **APP,
            **HARBOR,
            "third/harbor/vendor/golang.org/x/LICENSE": "BSD\n",
            "third/harbor/vendor/golang.org/x/AUTHORS": "Go\n",
            "third/harbor/vendor/golang.org/x/a.go": "package x\n",
            "vendor/dep/LICENSE": "MIT\n",
            "vendor/dep/NOTICE": "n\n",
            "vendor/dep/d.go": "package d\n",
        },
    )
    assert sorted(_roots(_project(repo))) == ["third/harbor/", "vendor/"]


def test_secret_bearing_file_inside_third_party_dir_is_never_read(tmp_path):
    repo = _write(tmp_path, {**APP, **HARBOR, "third/harbor/.env": "TOKEN=FAKEfake\n"})
    pack = run_dimension(security.DESCRIPTOR, repo, scope="project")
    assert not [p for p in pack.files_read if p.startswith("third/harbor/")]
    assert [item.path for item in pack.excluded] == ["third/harbor/"]


def test_symlink_out_of_the_repo_stays_handled_by_containment(tmp_path):
    outside = _write(
        tmp_path / "outside",
        {"LICENSE": "x\n", "NOTICE": "y\n", "lib.go": "package z\n"},
    )
    repo = _write(tmp_path / "repo", dict(APP))
    (repo / "ext").symlink_to(outside, target_is_directory=True)
    scope = _project(repo)
    assert not [p for p in scope.files if p.startswith("ext/")]
    assert scope.excluded == ()


# ---------------------------------------------------------------------------
# One predicate for both walks, every scope kind, and role picks


def test_context_walk_and_role_resolution_skip_third_party(tmp_path):
    repo = _write(
        tmp_path,
        {**APP, **HARBOR, "third/harbor/package.json": "{}\n", "package.json": "{}\n"},
    ).resolve()
    walked = list(_walk(repo, repo, extensions=None))
    assert "app/main.py" in walked
    assert not [p for p in walked if p.startswith("third/harbor/")]
    resolution = resolve(repo, (role("package-manifest"),))
    assert resolution.files["package-manifest"] == ("package.json",)


def test_a_pick_of_a_third_party_file_is_rejected(tmp_path):
    repo = _write(tmp_path, {**APP, **HARBOR, "third/harbor/README.md": "# Harbor\n"})
    assert "readme" in GENERIC_PATTERNS
    with pytest.raises(ValidationError, match="third-party"):
        validate_agent_input({"picks": {"readme": ["third/harbor/README.md"]}}, repo)


def test_worktree_and_changes_scopes_apply_the_exclusion(tmp_path):
    repo = _write(tmp_path, {**APP, "vendor/lib.js": "var a;\n"})
    _git(repo, "init", "-q")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "init")
    _write(
        repo,
        {"vendor/lib.js": "var b;\n", "app/main.py": "def main():\n    return 2\n"},
    )

    worktree = resolve_scope("worktree", repo, detect_context(repo))
    assert worktree.files == ("app/main.py",)
    assert [item.path for item in worktree.excluded] == ["vendor/"]

    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "change")
    changes = resolve_scope("changes", repo, detect_context(repo), ref="HEAD")
    assert changes.files == changes.changed_files == ("app/main.py",)
    assert "vendor/lib.js" not in changes.diff
    assert "app/main.py" in changes.diff
    assert [item.path for item in changes.excluded] == ["vendor/"]


# ---------------------------------------------------------------------------
# SC 6 shape / AC 5, AC 8: payload, report, parity


@pytest.fixture
def harbor_repo(tmp_path) -> Path:
    files = {
        **APP,
        **HARBOR,
        "third/harbor/dao/a.go": 'package dao\nimport "x/service"\n',
        "third/harbor/service/b.go": 'package service\nimport "x/dao"\n',
    }
    return _write(tmp_path / "repo", files)


def test_payload_discloses_each_root_once_and_no_rating_cites_it(harbor_repo):
    payload = score_repository(harbor_repo, scope="project").to_dict()
    assert payload["excluded"] == [
        {
            "path": "third/harbor/",
            "excluded": "third-party",
            "reason": "nested-project",
            "rule": "LICENSE + NOTICE",
        }
    ]
    cited = {
        path
        for rating in payload["ratings"]
        for item in rating.get("inputs", []) or []
        for path in item.get("computed_from") or []
    }
    assert not [p for p in cited if p.startswith("third/harbor/")]


def test_nothing_excluded_means_no_excluded_key_anywhere(tmp_path):
    repo = _write(tmp_path, dict(APP))
    assert "excluded" not in score_repository(repo, scope="project").to_dict()
    pack = run_dimension(code_quality.DESCRIPTOR, repo, scope="project")
    assert "excluded" not in to_json_dict(pack)


def test_report_shows_a_folded_count_and_list(harbor_repo):
    result = score_repository(harbor_repo, scope="project")
    html = _render_score_panel(_Ctx(harbor_repo), result)
    assert (
        '<details class="third-party-excluded"><summary>Excluded as third-party (1)'
        in html
    )
    assert "<code>third/harbor/</code> (nested-project: LICENSE + NOTICE)" in html


def test_cli_and_mcp_payloads_are_equal(harbor_repo, capsys, monkeypatch):
    monkeypatch.setattr("sys.stdin", io.TextIOWrapper(io.BytesIO(b"")))
    mcp = mcp_server.score(repo=str(harbor_repo), scope="project")
    mcp.pop("needs_input", None)
    assert cli.main(["score", "--repo", str(harbor_repo), "--scope", "project"]) == 0
    cli_payload = json.loads(capsys.readouterr().out)
    assert cli_payload == mcp
    assert cli_payload["excluded"][0]["path"] == "third/harbor/"


def test_churn_ranking_leaves_third_party_files_out(tmp_path):
    """Blast-radius ranks hotspots over `git ls-files`, not a walk: the same
    predicate keeps a heavily churned vendor file out of the ranking."""
    from easy_verifier.dimensions import blast_radius

    repo = _write(tmp_path, {**APP, "vendor/lib.js": "v0\n", "app/other.py": "o\n"})
    _git(repo, "init", "-q")
    for index in range(22):
        _write(repo, {"vendor/lib.js": f"v{index}\n"})
        if index % 2:
            _write(repo, {"app/main.py": f"def main():\n    return {index}\n"})
        _git(repo, "add", "-A")
        _git(repo, "commit", "-qm", f"c{index}")
    pack = run_dimension(blast_radius.DESCRIPTOR, repo, scope="changes", ref="HEAD")
    # README.md, app/main.py, app/other.py -- vendor/lib.js is not ranked.
    assert pack.reach.ranked_files == 3
    assert pack.reach.hotspots_changed == ("app/main.py",)
