"""T026 — any-language source roles, `.easy-verifier.toml`, agent-input picks.

Every acceptance criterion in ``tasks/TASK_GUIDE_T026.md`` has at least one test
here. Fixture repositories are built per test under ``tmp_path``; none of them
contains a kit artifact, so every run is standalone unless stated otherwise.
"""

from __future__ import annotations

import asyncio
import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from easy_verifier.adapters import cli
from easy_verifier.core import roles as roles_module
from easy_verifier.core.findings import ValidationError
from easy_verifier.core.models import SourceRole
from easy_verifier.core.pipeline import run_dimension
from easy_verifier.core.report import write_report
from easy_verifier.core.roles import (
    ECOSYSTEM_PATTERNS,
    GENERIC_PATTERNS,
    load_repo_config,
    resolve,
    validate_agent_input,
)
from easy_verifier.core.score import score_repository
from easy_verifier.core.synthesis import combined_pack
from easy_verifier.dimensions import DIMENSIONS, dimension_names, list_dimensions

# ---------------------------------------------------------------------------
# fixture repositories
# ---------------------------------------------------------------------------


def _write(root: Path, files: dict[str, str]) -> Path:
    for relative, text in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


def _git_commit(root: Path) -> None:
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@example.invalid",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@example.invalid",
    }
    for args in (["init", "-q"], ["add", "-A"], ["commit", "-qm", "init"]):
        subprocess.run(["git", "-C", str(root), *args], check=True, env=env)


ELIXIR_FILES = {
    "README.md": "# App\n\nAn Elixir service.\n",
    "CONTRIBUTING.md": "# Contributing\n\n## Code style\nRun mix format.\n",
    "docs/specs/requirements.md": (
        "# Requirements\n\n## Functional requirements\n- FR-1: greet.\n"
    ),
    "docs/specs/architecture.md": "# Architecture\n\n## Overview\nOne GenServer.\n",
    ".formatter.exs": '[inputs: ["lib/**/*.ex"]]\n',
    "mix.exs": "defmodule App.MixProject do\n  use Mix.Project\nend\n",
    "mix.lock": '%{"jason": {:hex, :jason, "1.4.1"}}\n',
    "lib/app/greeter.ex": 'defmodule App.Greeter do\n  def greet, do: "hi"\nend\n',
    "test/greeter_test.exs": (
        "defmodule App.GreeterTest do\n  use ExUnit.Case\n"
        '  test "greets" do\n    assert App.Greeter.greet() == "hi"\n  end\nend\n'
    ),
    "test/test_helper.exs": "ExUnit.start()\n",
    ".github/workflows/ci.yml": "name: ci\non: [push]\njobs: {}\n",
    "Dockerfile": "FROM elixir:1.16\nUSER nobody\n",
}


@pytest.fixture
def elixir_repo(tmp_path: Path) -> Path:
    repo = _write(tmp_path / "elixir", ELIXIR_FILES)
    _git_commit(repo)
    return repo


def _all_roles() -> tuple[SourceRole, ...]:
    seen: dict[str, SourceRole] = {}
    for descriptor in DIMENSIONS.values():
        for role in descriptor.roles:
            seen.setdefault(role.name, role)
    return tuple(seen.values())


def _file_roles() -> tuple[SourceRole, ...]:
    return tuple(role for role in _all_roles() if role.patterns)


def _cli(capsys, *args: str) -> tuple[int, str, str]:
    """Run the CLI in-process with an empty, non-tty stdin (no findings)."""
    real = sys.stdin
    sys.stdin = io.TextIOWrapper(io.BytesIO(b""))
    try:
        code = cli.main(list(args))
    finally:
        sys.stdin = real
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def _mcp(name: str, arguments: dict) -> object:
    from easy_verifier.adapters import mcp_server

    _content, result = asyncio.run(mcp_server.mcp.call_tool(name, arguments))
    return result


# ---------------------------------------------------------------------------
# AC 1 — roles are static descriptor data, discoverable
# ---------------------------------------------------------------------------


def test_every_descriptor_declares_roles_and_sources_sought_is_their_names() -> None:
    assert len(DIMENSIONS) == 7
    for name, descriptor in DIMENSIONS.items():
        assert descriptor.roles, name
        assert all(isinstance(role, SourceRole) for role in descriptor.roles), name
        assert descriptor.sources_sought == tuple(r.name for r in descriptor.roles)
        assert len(set(descriptor.sources_sought)) == len(descriptor.sources_sought)
        # At least one role per dimension is file-backed: pseudo-roles alone
        # would leave the dimension with nothing a pattern can fill.
        assert any(role.patterns for role in descriptor.roles), name


def test_every_file_backed_role_takes_its_patterns_from_the_generic_table() -> None:
    for role in _file_roles():
        assert role.name in GENERIC_PATTERNS
        assert role.patterns == GENERIC_PATTERNS[role.name]
    used = {role.name for role in _file_roles()}
    assert used == set(GENERIC_PATTERNS)


def test_list_dimensions_lists_roles_and_their_patterns(capsys) -> None:
    by_name = {item.name: item for item in list_dimensions()}
    for name, descriptor in DIMENSIONS.items():
        assert by_name[name].roles == descriptor.roles

    code, out, _ = _cli(capsys, "list-dimensions")
    assert code == 0
    payload = {item["name"]: item for item in json.loads(out)}
    security = payload["security"]
    listed = {role["name"]: role["patterns"] for role in security["roles"]}
    assert listed["lockfile"] == list(GENERIC_PATTERNS["lockfile"])
    assert security["sources_sought"] == [role["name"] for role in security["roles"]]


# ---------------------------------------------------------------------------
# AC 2 / AC 3 — role coverage in all seven dimensions, any language
# ---------------------------------------------------------------------------


def test_coverage_is_roles_filled_over_roles_declared_for_all_seven(
    elixir_repo: Path,
) -> None:
    packs = combined_pack(dimension_names(), repo_path=elixir_repo)
    for slot in packs.slots:
        pack = slot.pack
        assert pack is not None, slot.error
        roles = DIMENSIONS[slot.dimension].sources_sought
        assert pack.sources_sought == roles
        assert set(pack.sources_found) <= set(roles)
        missing = tuple(miss.source for miss in pack.sources_missing)
        assert sorted((*pack.sources_found, *missing)) == sorted(roles)
        assert pack.coverage_score == len(pack.sources_found) / len(roles)


@pytest.mark.parametrize(
    ("dimension", "role"),
    [
        # The three bespoke loops, each filled by a file no exact-name
        # checklist on `main` would ever have named.
        ("security", "lockfile"),  # mix.lock
        ("security", "package-manifest"),  # mix.exs
        ("test-strategy", "test-file"),  # test/greeter_test.exs
        ("test-strategy", "test-config"),  # test/test_helper.exs
        ("blast-radius", "package-manifest"),  # mix.exs
        # The shared document helper.
        ("requirement-fidelity", "requirements-doc"),  # docs/specs/requirements.md
        ("architecture", "architecture-doc"),  # docs/specs/architecture.md
        ("code-quality", "format-config"),  # .formatter.exs
    ],
)
def test_a_language_without_a_table_fills_roles_by_generic_patterns(
    elixir_repo: Path, dimension: str, role: str
) -> None:
    pack = run_dimension(DIMENSIONS[dimension], elixir_repo)
    assert role in pack.sources_found, pack.sources_missing


def test_the_generic_fixture_rates_dimensions_that_abstain_on_main(
    elixir_repo: Path,
) -> None:
    """Success criterion 1: on `develop` HEAD 6328455 this exact tree rated
    only code-quality; the other six abstained below their coverage floor."""
    ratings = {
        item["dimension"]: item
        for item in score_repository(elixir_repo).to_dict()["ratings"]
    }
    for dimension in (
        "architecture",
        "solution-fit",
        "requirement-fidelity",
        "security",
        "test-strategy",
        "blast-radius",
    ):
        assert ratings[dimension]["kind"] == "rating", ratings[dimension]


# ---------------------------------------------------------------------------
# AC 4 — ecosystem tables, activated by manifests
# ---------------------------------------------------------------------------


def _resolve_all(repo: Path, **kwargs):
    return resolve(repo, _file_roles(), **kwargs)


def test_js_ts_pnpm_monorepo_fills_roles_via_the_js_table(tmp_path: Path) -> None:
    repo = _write(
        tmp_path / "js",
        {
            "package.json": '{"name": "mono", "private": true}\n',
            "pnpm-lock.yaml": "lockfileVersion: '9.0'\n",
            "pnpm-workspace.yaml": "packages: ['packages/*']\n",
            "eslint.config.js": "export default [];\n",
            ".prettierrc": "{}\n",
            "vitest.config.ts": "export default {};\n",
            "packages/app/package.json": '{"name": "app"}\n',
            "packages/app/src/sum.ts": "export const sum = (a, b) => a + b;\n",
            "packages/app/src/sum.test.ts": "expect(sum(1, 2)).toBe(3);\n",
        },
    )
    resolution = _resolve_all(repo)
    assert "js-ts" in resolution.ecosystems
    assert "eslint.config.js" in resolution.files["lint-config"]
    assert ".prettierrc" in resolution.files["format-config"]
    assert "pnpm-lock.yaml" in resolution.files["lockfile"]
    assert "vitest.config.ts" in resolution.files["test-config"]
    assert "packages/app/src/sum.test.ts" in resolution.files["test-file"]
    assert "packages/app/package.json" in resolution.files["package-manifest"]

    assert "lint-config" in run_dimension(DIMENSIONS["code-quality"], repo).sources_found
    assert "lockfile" in run_dimension(DIMENSIONS["security"], repo).sources_found
    found = run_dimension(DIMENSIONS["test-strategy"], repo).sources_found
    assert {"test-config", "test-file"} <= set(found)


def test_python_fixture_fills_roles_via_the_python_table(tmp_path: Path) -> None:
    repo = _write(
        tmp_path / "py",
        {
            "pyproject.toml": "[project]\nname = 'p'\n",
            "ruff.toml": "line-length = 88\n",
            "poetry.lock": "# lock\n",
            "src/p/core.py": "def f():\n    return 1\n",
            "tests/conftest.py": "import pytest\n",
            "tests/test_core.py": "def test_f():\n    assert True\n",
        },
    )
    resolution = _resolve_all(repo)
    assert "python" in resolution.ecosystems
    assert "ruff.toml" in resolution.files["lint-config"]
    assert "tests/conftest.py" in resolution.files["test-config"]
    assert "pyproject.toml" in resolution.files["package-manifest"]
    assert "poetry.lock" in resolution.files["lockfile"]


def test_rust_fixture_fills_roles_via_the_rust_table(tmp_path: Path) -> None:
    repo = _write(
        tmp_path / "rs",
        {
            "Cargo.toml": "[package]\nname = 'r'\n",
            "Cargo.lock": "version = 3\n",
            "clippy.toml": "msrv = '1.70'\n",
            "src/lib.rs": "pub fn f() -> u8 { 1 }\n",
            "tests/it.rs": "#[test]\nfn works() { assert_eq!(r::f(), 1); }\n",
        },
    )
    resolution = _resolve_all(repo)
    assert "rust" in resolution.ecosystems
    assert "clippy.toml" in resolution.files["lint-config"]
    assert "Cargo.lock" in resolution.files["lockfile"]
    assert "Cargo.toml" in resolution.files["package-manifest"]
    assert "tests/it.rs" in resolution.files["test-file"]


def test_an_ecosystem_table_is_inactive_without_its_manifest(tmp_path: Path) -> None:
    """The Rust-only `clippy.toml` counts only because `Cargo.toml` activated
    the table — without it, the same file fills nothing."""
    repo = _write(tmp_path / "bare", {"clippy.toml": "msrv = '1.70'\n"})
    resolution = _resolve_all(repo)
    assert "rust" not in resolution.ecosystems
    assert "clippy.toml" not in resolution.files["lint-config"]


def test_java_fixture_fills_roles_via_the_java_table(tmp_path: Path) -> None:
    repo = _write(
        tmp_path / "java",
        {
            "build.gradle.kts": "plugins { java }\n",
            "config/checkstyle/checkstyle.xml": "<module/>\n",
            "src/main/java/App.java": "class App {}\n",
            "src/test/java/AppTest.java": "class AppTest {}\n",
        },
    )
    resolution = _resolve_all(repo)
    assert "java" in resolution.ecosystems
    assert "build.gradle.kts" in resolution.files["package-manifest"]
    assert "build.gradle.kts" in resolution.files["test-config"]
    assert "config/checkstyle/checkstyle.xml" in resolution.files["lint-config"]
    assert "src/test/java/AppTest.java" in resolution.files["test-file"]


# ---------------------------------------------------------------------------
# AC 5 — no table adds, removes or exempts a role
# ---------------------------------------------------------------------------


def test_ecosystem_tables_only_extend_existing_roles() -> None:
    for ecosystem, table in ECOSYSTEM_PATTERNS.items():
        assert table["manifests"], ecosystem
        assert set(table["roles"]) <= set(GENERIC_PATTERNS), ecosystem


def test_role_set_is_identical_with_every_table_active_and_with_none(
    tmp_path: Path,
) -> None:
    every = _write(
        tmp_path / "every",
        {
            "pyproject.toml": "[project]\n",
            "package.json": "{}\n",
            "Cargo.toml": "[package]\n",
            "pom.xml": "<project/>\n",
        },
    )
    none = _write(tmp_path / "none", {"notes.txt": "nothing\n"})
    active = _resolve_all(every)
    inactive = _resolve_all(none)
    assert set(active.ecosystems) == set(ECOSYSTEM_PATTERNS)
    assert inactive.ecosystems == ()
    assert set(active.files) == set(inactive.files) == {r.name for r in _file_roles()}
    for descriptor in DIMENSIONS.values():
        assert (
            run_dimension(descriptor, every).sources_sought
            == run_dimension(descriptor, none).sources_sought
            == descriptor.sources_sought
        )


# ---------------------------------------------------------------------------
# AC 6 — vendor/build directories never fill a role
# ---------------------------------------------------------------------------

EXCLUDED = ("node_modules", "target", "dist", "build", ".venv", "vendor", ".git")


def test_excluded_directories_never_fill_a_role(tmp_path: Path) -> None:
    files = {"README.md": "# r\n"}
    for directory in EXCLUDED:
        files[f"{directory}/pkg/x.lock"] = "lock\n"
        files[f"{directory}/pkg/x.test.js"] = "test\n"
        files[f"{directory}/pkg/Dockerfile"] = "FROM x\n"
        files[f"{directory}/pkg/package.json"] = "{}\n"
    repo = _write(tmp_path / "vendored", files)
    resolution = _resolve_all(repo)
    for role, paths in resolution.files.items():
        for path in paths:
            assert path.split("/")[0] not in EXCLUDED, (role, path)
    pack = run_dimension(DIMENSIONS["security"], repo)
    assert "lockfile" not in pack.sources_found
    assert "container-config" not in pack.sources_found


# ---------------------------------------------------------------------------
# AC 7 — `.easy-verifier.toml`
# ---------------------------------------------------------------------------


def _config(repo: Path, text: str) -> None:
    (repo / ".easy-verifier.toml").write_text(text, encoding="utf-8")


def test_config_adds_paths_to_a_role(tmp_path: Path) -> None:
    repo = _write(tmp_path / "cfg", {"notes/wants.md": "# Wants\n\nThe need.\n"})
    before = run_dimension(DIMENSIONS["solution-fit"], repo)
    assert "requirements-doc" not in before.sources_found
    assert before.source_provenance == "rules"

    _config(repo, '[roles]\nrequirements-doc = ["notes/*.md"]\n')
    assert load_repo_config(repo) == {"requirements-doc": ("notes/*.md",)}
    after = run_dimension(DIMENSIONS["solution-fit"], repo)
    assert "requirements-doc" in after.sources_found
    assert "notes/wants.md" in after.files_read
    assert after.source_provenance == "rules + config"
    # A dimension the config does not touch keeps plain `rules`.
    assert run_dimension(DIMENSIONS["security"], repo).source_provenance == "rules"


def test_an_absent_config_changes_nothing(elixir_repo: Path) -> None:
    assert load_repo_config(elixir_repo) == {}
    first = score_repository(elixir_repo).serialize()
    assert first == score_repository(elixir_repo).serialize()
    provenance = json.loads(first)["provenance"]
    assert [item["sources"] for item in provenance] == ["rules"] * 7


@pytest.mark.parametrize(
    ("text", "named"),
    [
        ("coverage_floor = 0.1\n", "coverage_floor"),
        ('[roles]\nnonsense = ["x"]\n', "nonsense"),
        ('[roles]\nlockfile = "x.lock"\n', "roles.lockfile"),
        ("[roles]\nlockfile = []\n", "roles.lockfile"),
        ("[roles.lockfile]\nexclude = true\n", "roles.lockfile"),
        ('[roles]\nlockfile = [1]\n', "roles.lockfile[0]"),
        ('[roles]\nlockfile = ["/abs/x.lock"]\n', "roles.lockfile[0]"),
        ('[roles]\nlockfile = ["../x.lock"]\n', "roles.lockfile[0]"),
        ('[floors]\nsecurity = 0.1\n', "floors"),
        ('[roles]\n"git history (out of scope for v1)" = ["x"]\n', "git history"),
        ("roles = [\n", ".easy-verifier.toml"),
    ],
)
def test_invalid_config_is_a_validation_error_naming_the_key(
    tmp_path: Path, text: str, named: str
) -> None:
    repo = _write(tmp_path / "bad", {"README.md": "# r\n"})
    _config(repo, text)
    with pytest.raises(ValidationError) as caught:
        load_repo_config(repo)
    assert named in str(caught.value)


def test_config_reports_every_error_at_once(tmp_path: Path) -> None:
    repo = _write(tmp_path / "bad", {"README.md": "# r\n"})
    _config(repo, 'coverage_floor = 0.1\n[roles]\nnonsense = ["x"]\n')
    with pytest.raises(ValidationError) as caught:
        load_repo_config(repo)
    assert "coverage_floor" in str(caught.value)
    assert "nonsense" in str(caught.value)


def test_invalid_config_exits_2_at_the_cli_and_errors_over_mcp(
    tmp_path: Path, capsys
) -> None:
    from mcp.server.fastmcp.exceptions import ToolError

    repo = _write(tmp_path / "bad", {"README.md": "# r\n"})
    _config(repo, "coverage_floor = 0.1\n")
    code, _, err = _cli(capsys, "score", "--repo", str(repo))
    assert code == cli.VALIDATION_EXIT
    assert "coverage_floor" in err
    code, _, err = _cli(capsys, "architecture", "--repo", str(repo))
    assert code == cli.VALIDATION_EXIT
    with pytest.raises(ToolError) as caught:
        _mcp("score", {"repo": str(repo)})
    assert "coverage_floor" in str(caught.value)


# ---------------------------------------------------------------------------
# AC 8 — agent-input picks
# ---------------------------------------------------------------------------


def test_picks_are_additive_and_counted_in_provenance(tmp_path: Path) -> None:
    repo = _write(tmp_path / "picks", {"notes/wants.md": "# Wants\n\nThe need.\n"})
    doc = {"picks": {"requirements-doc": ["notes/wants.md"]}}
    assert validate_agent_input(doc, repo) == {"requirements-doc": ("notes/wants.md",)}

    result = score_repository(repo, agent_input=doc).to_dict()
    provenance = {item["dimension"]: item["sources"] for item in result["provenance"]}
    assert provenance["solution-fit"] == "rules + agent picks (1 file)"
    assert provenance["requirement-fidelity"] == "rules + agent picks (1 file)"
    assert provenance["security"] == "rules"

    packs = combined_pack(
        dimension_names(),
        repo_path=repo,
        agent_input={"picks": {"requirements-doc": ["notes/wants.md"]}},
    )
    pack = next(s.pack for s in packs.slots if s.dimension == "solution-fit")
    assert "requirements-doc" in pack.sources_found


def test_config_and_picks_combine_in_provenance(tmp_path: Path) -> None:
    repo = _write(
        tmp_path / "both",
        {"notes/wants.md": "# Wants\n", "notes/more.md": "# More\n", "x/y.md": "# Y\n"},
    )
    _config(repo, '[roles]\nrequirements-doc = ["notes/*.md"]\n')
    doc = {"picks": {"requirements-doc": ["x/y.md", "notes/wants.md"]}}
    result = score_repository(repo, agent_input=doc).to_dict()
    provenance = {item["dimension"]: item["sources"] for item in result["provenance"]}
    # notes/wants.md is already config-sourced, so the pick adds one file.
    assert provenance["solution-fit"] == "rules + config + agent picks (1 file)"


def test_invalid_picks_are_all_rejected_by_name(tmp_path: Path) -> None:
    outside = tmp_path / "outside.md"
    outside.write_text("# outside\n", encoding="utf-8")
    repo = _write(
        tmp_path / "repo",
        {
            "ok.md": "# ok\n",
            ".env.local": "TOKEN=FAKEfakeFAKEfake\n",
            "node_modules/pkg/readme.md": "# vendored\n",
        },
    )
    (repo / "escape.md").symlink_to(outside)
    (repo / "adir").mkdir()
    doc = {
        "picks": {
            "requirements-doc": [
                "/etc/passwd",
                "../outside.md",
                "escape.md",
                "missing.md",
                ".env.local",
                "node_modules/pkg/readme.md",
                "adir",
                7,
            ],
            "not-a-role": ["ok.md"],
        }
    }
    with pytest.raises(ValidationError) as caught:
        validate_agent_input(doc, repo)
    message = str(caught.value)
    for fragment in (
        "/etc/passwd",
        "../outside.md",
        "escape.md",
        "missing.md",
        ".env.local",
        "node_modules/pkg/readme.md",
        "adir",
        "picks.requirements-doc[7]",
        "not-a-role",
    ):
        assert fragment in message, fragment
    assert "secret-bearing" in message
    assert "FAKEfake" not in message


@pytest.mark.parametrize(
    ("doc", "named"),
    [
        ({"picks": {"lockfile": ["../etc/passwd"]}}, "../etc/passwd"),
        ({"gate_evaluations": {}}, "gate_evaluations"),
        ({"picks": {}, "extra": 1}, "extra"),
        ({"picks": ["x"]}, "picks"),
        ({"picks": {"lockfile": "x.lock"}}, "picks.lockfile"),
        (["picks"], "agent input"),
        ("{not json", "agent input"),
        ({"picks": {"git history (out of scope for v1)": ["README.md"]}}, "git history"),
    ],
)
def test_malformed_agent_input_is_rejected_naming_it(
    tmp_path: Path, doc: object, named: str
) -> None:
    repo = _write(tmp_path / "repo", {"README.md": "# r\n"})
    with pytest.raises(ValidationError) as caught:
        validate_agent_input(doc, repo)
    assert named in str(caught.value)


def test_gate_evaluations_are_not_yet_supported(tmp_path: Path) -> None:
    repo = _write(tmp_path / "repo", {"README.md": "# r\n"})
    with pytest.raises(ValidationError) as caught:
        score_repository(repo, agent_input={"picks": {}, "gate_evaluations": {}})
    assert "not yet supported" in str(caught.value)


def test_cli_replays_agent_input_from_a_file(tmp_path: Path, capsys) -> None:
    repo = _write(tmp_path / "repo", {"notes/wants.md": "# Wants\n"})
    doc = tmp_path / "agent-input.json"
    doc.write_text(json.dumps({"picks": {"requirements-doc": ["notes/wants.md"]}}))
    code, out, err = _cli(capsys, "score", "--repo", str(repo), "--agent-input", str(doc))
    assert code == 0, err
    provenance = {i["dimension"]: i["sources"] for i in json.loads(out)["provenance"]}
    assert provenance["solution-fit"] == "rules + agent picks (1 file)"

    doc.write_text(json.dumps({"picks": {"lockfile": ["../etc/passwd"]}}))
    code, _, err = _cli(capsys, "score", "--repo", str(repo), "--agent-input", str(doc))
    assert code == cli.VALIDATION_EXIT
    assert "../etc/passwd" in err


def test_mcp_score_takes_agent_input_as_an_argument(tmp_path: Path) -> None:
    from mcp.server.fastmcp.exceptions import ToolError

    repo = _write(tmp_path / "repo", {"notes/wants.md": "# Wants\n"})
    result = _mcp(
        "score",
        {
            "repo": str(repo),
            "agent_input": {"picks": {"requirements-doc": ["notes/wants.md"]}},
        },
    )
    provenance = {i["dimension"]: i["sources"] for i in result["provenance"]}
    assert provenance["solution-fit"] == "rules + agent picks (1 file)"
    with pytest.raises(ToolError) as caught:
        _mcp("score", {"repo": str(repo), "agent_input": {"gate_evaluations": {}}})
    assert "gate_evaluations" in str(caught.value)


# ---------------------------------------------------------------------------
# AC 9 — secret-bearing matches never fill a role
# ---------------------------------------------------------------------------


def test_a_role_matched_only_by_a_secret_file_is_not_filled(tmp_path: Path) -> None:
    repo = _write(
        tmp_path / "secret",
        {".env": "TOKEN=FAKEfakeFAKEfake\n", "config/lint.pem": "FAKE\n"},
    )
    security = run_dimension(DIMENSIONS["security"], repo)
    reasons = {miss.source: miss.reason for miss in security.sources_missing}
    assert "credential-file" not in security.sources_found
    # Security asks the operator first (T008), so its reason carries that too.
    assert reasons["credential-file"] == (
        "excluded: secret-bearing; operator approval required"
    )

    _config(repo, '[roles]\nlint-config = ["config/*.pem"]\n')
    quality = run_dimension(DIMENSIONS["code-quality"], repo)
    reasons = {miss.source: miss.reason for miss in quality.sources_missing}
    assert "lint-config" not in quality.sources_found
    assert reasons["lint-config"] == "excluded: secret-bearing"
    assert "config/lint.pem" not in quality.files_read


# ---------------------------------------------------------------------------
# AC 10 — provenance in the HTML report
# ---------------------------------------------------------------------------


def test_report_renders_one_provenance_line_per_dimension(tmp_path: Path) -> None:
    repo = _write(tmp_path / "rep", {"notes/wants.md": "# Wants\n", "README.md": "# r\n"})
    packs = combined_pack(
        dimension_names(),
        repo_path=repo,
        agent_input={"picks": {"requirements-doc": ["notes/wants.md"]}},
    )
    written = write_report([], packs, repo)
    document = Path(written.absolute_path).read_text(encoding="utf-8")
    assert document.count("Sources: ") == 7
    assert document.count("Sources: rules + agent picks (1 file)") == 2
    assert document.count("Sources: rules</") == 5


# ---------------------------------------------------------------------------
# AC 12 — deterministic and bounded resolution
# ---------------------------------------------------------------------------


def test_role_files_are_sorted_and_capped_with_explicit_truncation(
    tmp_path: Path,
) -> None:
    cap = roles_module.MAX_ROLE_FILES
    files = {f"tests/t{index:04d}_test.exs": "x\n" for index in range(cap + 5)}
    repo = _write(tmp_path / "many", files)
    resolution = _resolve_all(repo)
    chosen = resolution.files["test-file"]
    assert len(chosen) == cap
    assert list(chosen) == sorted(files)[:cap]
    assert "test-file" in resolution.truncated_roles

    pack = run_dimension(DIMENSIONS["test-strategy"], repo)
    assert any("test-file" in w and str(cap) in w for w in pack.warnings)


def test_a_bounded_walk_says_so_in_the_miss_reason(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(roles_module, "MAX_ROLE_WALK_FILES", 3)
    repo = _write(
        tmp_path / "walk", {f"a{index}.txt": "x\n" for index in range(5)} | {"z.lock": "l\n"}
    )
    resolution = _resolve_all(repo)
    assert resolution.walk_truncated is True
    assert resolution.files["lockfile"] == ()
    pack = run_dimension(DIMENSIONS["security"], repo)
    reason = {m.source: m.reason for m in pack.sources_missing}["lockfile"]
    assert "3" in reason and "bounded" in reason
    assert any("bounded" in w for w in pack.warnings)


def test_role_resolution_is_deterministic(elixir_repo: Path) -> None:
    first = _resolve_all(elixir_repo)
    second = _resolve_all(elixir_repo)
    assert first == second
    for paths in first.files.values():
        assert list(paths) == sorted(paths)
