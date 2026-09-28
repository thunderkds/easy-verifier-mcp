"""T030 — cited reference registry: schema, loader, curated 9 languages.

Every acceptance criterion in ``tasks/TASK_GUIDE_T030.md`` has at least one test
here. Fixture repositories are built per test under ``tmp_path``.
"""

from __future__ import annotations

import tomllib
from importlib import resources
from pathlib import Path

import pytest

from easy_verifier.core import registry as registry_module
from easy_verifier.core import roles as roles_module
from easy_verifier.core.pipeline import run_dimension
from easy_verifier.core.registry import (
    CURATED,
    MAX_ENTRY_BYTES,
    CitedValue,
    Registry,
    load_registry,
    merge,
)
from easy_verifier.core.roles import (
    GENERIC_PATTERNS,
    resolution_warnings,
    resolve,
    role,
)
from easy_verifier.dimensions import DIMENSIONS

LANGUAGES = (
    "csharp",
    "go",
    "java",
    "js-ts",
    "kotlin",
    "php",
    "python",
    "ruby",
    "rust",
)

URL = "https://example.org/docs"


def _write(root: Path, files: dict[str, str]) -> Path:
    for relative, text in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


def _resolve_all(repo: Path):
    return resolve(repo, [role(name) for name in GENERIC_PATTERNS])


def _load(directory: Path) -> Registry:
    return load_registry(directory, known_roles=GENERIC_PATTERNS)


def _cited(values: list[str], url: str = URL) -> str:
    quoted = ", ".join(f'"{value}"' for value in values)
    return f'value = [{quoted}]\ncitation_url = "{url}"\nsource_tag = "curated"\n'


GOOD_ENTRY = (
    "[[manifests]]\n"
    + _cited(["good.mod"])
    + "\n[[roles.lint-config]]\n"
    + _cited(["**/good-lint.cfg"])
)


# ---------------------------------------------------------------------------
# AC 1 — nine curated languages, every field cited
# ---------------------------------------------------------------------------


def _curated_dir():
    return resources.files("easy_verifier") / "registry" / "curated"


def test_curated_layer_ships_exactly_the_nine_languages() -> None:
    names = sorted(
        item.name for item in _curated_dir().iterdir() if item.name.endswith(".toml")
    )
    assert names == [f"{language}.toml" for language in LANGUAGES]

    loaded = load_registry(known_roles=GENERIC_PATTERNS)
    assert loaded.warnings == ()
    assert tuple(loaded.languages) == LANGUAGES


def _cited_fields(data: dict):
    for key, value in data.items():
        if key == "roles":
            for role_name, fields in value.items():
                for field in fields:
                    yield f"roles.{role_name}", field
        else:
            for field in value:
                yield key, field


@pytest.mark.parametrize("language", LANGUAGES)
def test_every_curated_field_carries_value_https_citation_and_curated_tag(
    language: str,
) -> None:
    raw = (_curated_dir() / f"{language}.toml").read_bytes()
    data = tomllib.loads(raw.decode("utf-8"))
    assert "manifests" in data, language
    fields = list(_cited_fields(data))
    assert fields, language
    for name, field in fields:
        assert set(field) == {"value", "citation_url", "source_tag"}, (language, name)
        assert field["value"] and all(isinstance(v, str) for v in field["value"])
        assert field["citation_url"].startswith("https://"), (language, name)
        assert field["source_tag"] == "curated", (language, name)


def test_loaded_entries_keep_the_citation_beside_every_value() -> None:
    kotlin = load_registry(known_roles=GENERIC_PATTERNS).languages["kotlin"]
    lint = kotlin.roles["lint-config"]
    assert all(isinstance(field, CitedValue) for field in lint)
    assert all(field.citation_url.startswith("https://") for field in lint)
    assert all(field.source_tag == CURATED for field in lint)
    assert any("detekt" in pattern for field in lint for pattern in field.value)


# ---------------------------------------------------------------------------
# AC 2 — the loader validates and rejects a bad entry with a warning
# ---------------------------------------------------------------------------


def test_a_field_without_citation_url_fails_that_entry_with_a_named_warning(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path,
        {
            "good.toml": GOOD_ENTRY,
            "bad.toml": (
                "[[manifests]]\n"
                + _cited(["bad.mod"])
                + '\n[[roles.lint-config]]\nvalue = ["x.cfg"]\nsource_tag = "curated"\n'
            ),
        },
    )
    loaded = _load(tmp_path)
    assert tuple(loaded.languages) == ("good",)
    assert len(loaded.warnings) == 1
    warning = loaded.warnings[0]
    assert "bad.toml" in warning
    assert "roles.lint-config[0]" in warning
    assert "citation_url" in warning


@pytest.mark.parametrize(
    ("content", "reason"),
    [
        (
            "[[manifests]]\n" + _cited(["a.mod"], "http://example.org/docs"),
            "https",
        ),
        ("[[manifests]]\n" + _cited(["a.mod"], "https://"), "https"),
        (
            "[[manifests]]\n" + _cited(["a.mod"]).replace("curated", "invented"),
            "source_tag",
        ),
        (
            "[[manifests]]\n" + _cited(["a.mod"]) + "\n[[sinks]]\n" + _cited(["x"]),
            "unknown field",
        ),
        (
            "[[manifests]]\n"
            + _cited(["a.mod"])
            + "\n[[roles.no-such-role]]\n"
            + _cited(["x"]),
            "unknown role",
        ),
        (
            "[[manifests]]\n" + _cited(["a.mod"]) + 'extra = "x"\n',
            "unknown key",
        ),
        (
            '[[manifests]]\nvalue = []\ncitation_url = "https://e.org"\n'
            'source_tag = "curated"\n',
            "value",
        ),
        ("[[manifests]]\n" + _cited(["/etc/passwd"]), "value"),
        ("[[manifests]]\n" + _cited(["../up"]), "value"),
        ('manifests = "a.mod"\n', "manifests"),
        ("[[roles.lint-config]]\n" + _cited(["x.cfg"]), "manifests"),
        ("", "empty"),
        ("not = [valid toml", "TOML"),
    ],
)
def test_malformed_entries_are_rejected_with_a_warning_never_a_crash(
    tmp_path: Path, content: str, reason: str
) -> None:
    _write(tmp_path, {"good.toml": GOOD_ENTRY, "bad.toml": content})
    loaded = _load(tmp_path)
    assert tuple(loaded.languages) == ("good",)
    assert len(loaded.warnings) == 1
    assert loaded.warnings[0].startswith("bad.toml")
    assert reason in loaded.warnings[0]


def test_oversized_and_non_utf8_entries_are_rejected(tmp_path: Path) -> None:
    _write(tmp_path, {"good.toml": GOOD_ENTRY})
    (tmp_path / "big.toml").write_bytes(b"#" * (MAX_ENTRY_BYTES + 1))
    (tmp_path / "latin.toml").write_bytes(b"# caf\xe9\n")
    loaded = _load(tmp_path)
    assert tuple(loaded.languages) == ("good",)
    assert [w.split(":")[0] for w in loaded.warnings] == ["big.toml", "latin.toml"]
    assert str(MAX_ENTRY_BYTES) in loaded.warnings[0]
    assert "UTF-8" in loaded.warnings[1]


def test_an_empty_registry_directory_loads_empty_without_warnings(
    tmp_path: Path,
) -> None:
    loaded = _load(tmp_path)
    assert loaded.languages == {} and loaded.frameworks == {}
    assert loaded.warnings == ()
    assert loaded.patterns_for("lint-config", ("python",)) == ()


def test_non_toml_files_are_ignored(tmp_path: Path) -> None:
    _write(tmp_path, {"good.toml": GOOD_ENTRY, "README.md": "# notes\n"})
    loaded = _load(tmp_path)
    assert tuple(loaded.languages) == ("good",)
    assert loaded.warnings == ()


def test_registry_warnings_surface_as_resolution_warnings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write(tmp_path / "reg", {"bad.toml": ""})
    monkeypatch.setattr(roles_module, "_registry", lambda: _load(tmp_path / "reg"))
    repo = _write(tmp_path / "repo", {"README.md": "# r\n"})
    warnings = resolution_warnings(_resolve_all(repo))
    assert any(w.startswith("Reference registry: bad.toml") for w in warnings)


# ---------------------------------------------------------------------------
# AC 3 — ECOSYSTEM_PATTERNS removed; the four former languages are unchanged
# ---------------------------------------------------------------------------

FORMER_ECOSYSTEM_PATTERNS: dict[str, dict] = {
    "python": {
        "manifests": (
            "pyproject.toml",
            "setup.py",
            "setup.cfg",
            "requirements.txt",
            "Pipfile",
        ),
        "roles": {
            "package-manifest": (
                "**/pyproject.toml",
                "**/setup.py",
                "**/setup.cfg",
                "**/requirements*.txt",
                "**/Pipfile",
            ),
            "lint-config": (
                "**/ruff.toml",
                "**/.ruff.toml",
                "**/.flake8",
                "**/pylintrc",
                "**/mypy.ini",
                "**/pyproject.toml",
                "**/setup.cfg",
            ),
            "test-config": (
                "**/pytest.ini",
                "**/tox.ini",
                "**/conftest.py",
                "**/noxfile.py",
                "**/pyproject.toml",
                "**/setup.cfg",
            ),
        },
    },
    "js-ts": {
        "manifests": ("package.json",),
        "roles": {
            "package-manifest": ("**/package.json", "**/pnpm-workspace.yaml"),
            "lint-config": (
                "**/eslint.config.*",
                "**/.eslintrc*",
                "**/biome.json",
                "**/biome.jsonc",
            ),
            "format-config": (
                "**/.prettierrc*",
                "**/prettier.config.*",
                "**/biome.json",
            ),
            "lockfile": ("**/npm-shrinkwrap.json",),
            "test-config": (
                "**/jest.config.*",
                "**/vitest.config.*",
                "**/vitest.workspace.*",
                "**/playwright.config.*",
                "**/cypress.config.*",
                "**/karma.conf.*",
                "**/.mocharc*",
                "package.json",
            ),
        },
    },
    "rust": {
        "manifests": ("Cargo.toml",),
        "roles": {
            "package-manifest": ("**/Cargo.toml",),
            "lint-config": ("**/clippy.toml", "**/.clippy.toml"),
            "format-config": ("**/rustfmt.toml", "**/.rustfmt.toml"),
            "test-config": ("**/Cargo.toml", "**/.config/nextest.toml"),
        },
    },
    "java": {
        "manifests": ("pom.xml", "build.gradle", "build.gradle.kts"),
        "roles": {
            "package-manifest": (
                "**/pom.xml",
                "**/build.gradle",
                "**/build.gradle.kts",
                "**/settings.gradle",
                "**/settings.gradle.kts",
            ),
            "lint-config": ("**/checkstyle*.xml", "**/pmd*.xml", "**/spotbugs*.xml"),
            "test-config": ("**/pom.xml", "**/build.gradle", "**/build.gradle.kts"),
            "test-file": ("**/src/test/**",),
        },
    },
}
"""Verbatim snapshot of the table T030 removed from ``core/roles.py``."""


def test_roles_module_no_longer_holds_an_ecosystem_table() -> None:
    assert not hasattr(roles_module, "ECOSYSTEM_PATTERNS")
    source = Path(roles_module.__file__).read_text(encoding="utf-8")
    assert "ECOSYSTEM_PATTERNS" not in source
    assert "clippy.toml" not in source


@pytest.mark.parametrize("language", sorted(FORMER_ECOSYSTEM_PATTERNS))
def test_registry_holds_exactly_the_former_patterns(language: str) -> None:
    former = FORMER_ECOSYSTEM_PATTERNS[language]
    entry = load_registry(known_roles=GENERIC_PATTERNS).languages[language]
    manifests = {p for field in entry.manifests for p in field.value}
    assert manifests == set(former["manifests"])
    assert set(entry.roles) == set(former["roles"])
    for name, patterns in former["roles"].items():
        registry_patterns = [p for field in entry.roles[name] for p in field.value]
        assert set(registry_patterns) == set(patterns), (language, name)
        assert len(registry_patterns) == len(set(registry_patterns)), (language, name)


def test_resolution_is_identical_to_the_former_table_on_a_mixed_repo(
    tmp_path: Path,
) -> None:
    """Behaviour parity: every role resolves to exactly the files the removed
    table resolved to, on a repo holding a file for every former pattern."""
    repo = _write(
        tmp_path / "mixed",
        {
            "pyproject.toml": "[project]\n",
            "setup.py": "",
            "setup.cfg": "",
            "requirements-dev.txt": "",
            "Pipfile": "",
            "ruff.toml": "",
            ".ruff.toml": "",
            ".flake8": "",
            "pylintrc": "",
            "mypy.ini": "",
            "pytest.ini": "",
            "tox.ini": "",
            "tests/conftest.py": "",
            "noxfile.py": "",
            "package.json": "{}\n",
            "web/package.json": "{}\n",
            "pnpm-workspace.yaml": "",
            "eslint.config.mjs": "",
            ".eslintrc.json": "",
            "biome.json": "{}",
            "biome.jsonc": "{}",
            ".prettierrc.yaml": "",
            "prettier.config.js": "",
            "npm-shrinkwrap.json": "{}",
            "jest.config.ts": "",
            "vitest.config.ts": "",
            "vitest.workspace.ts": "",
            "playwright.config.ts": "",
            "cypress.config.js": "",
            "karma.conf.js": "",
            ".mocharc.yml": "",
            "Cargo.toml": "[package]\n",
            "clippy.toml": "",
            ".clippy.toml": "",
            "rustfmt.toml": "",
            ".rustfmt.toml": "",
            ".config/nextest.toml": "",
            "pom.xml": "<project/>",
            "build.gradle": "",
            "build.gradle.kts": "",
            "settings.gradle": "",
            "settings.gradle.kts": "",
            "config/checkstyle-rules.xml": "",
            "config/pmd-rules.xml": "",
            "config/spotbugs-exclude.xml": "",
            "src/test/java/AppTest.java": "",
            "src/main/java/App.java": "",
            "latest.json": "{}",
            "notes/readme.txt": "",
        },
    )
    walked = sorted(
        p.relative_to(repo).as_posix() for p in repo.rglob("*") if p.is_file()
    )
    resolution = _resolve_all(repo)
    assert set(FORMER_ECOSYSTEM_PATTERNS) <= set(resolution.ecosystems)
    for name, generic in GENERIC_PATTERNS.items():
        former = generic + tuple(
            pattern
            for table in FORMER_ECOSYSTEM_PATTERNS.values()
            for pattern in table["roles"].get(name, ())
        )
        match = roles_module._matcher(former)
        expected = tuple(path for path in walked if match(path))
        assert resolution.files[name] == expected, name


# ---------------------------------------------------------------------------
# AC 4 — Go, Kotlin and C# fill manifest, lint and test config
# ---------------------------------------------------------------------------

NEW_LANGUAGE_FIXTURES = {
    "go": (
        {
            "go.mod": "module example.com/app\n\ngo 1.22\n",
            ".golangci.yml": "linters:\n  enable: [govet]\n",
            "main.go": "package main\n\nfunc main() {}\n",
            "main_test.go": "package main\n",
        },
        {
            "package-manifest": "go.mod",
            "lint-config": ".golangci.yml",
            "test-config": "go.mod",
        },
    ),
    "kotlin": (
        {
            "build.gradle.kts": 'plugins { kotlin("jvm") version "2.0.0" }\n',
            "detekt.yml": "build:\n  maxIssues: 0\n",
            "src/main/kotlin/App.kt": "fun main() {}\n",
            "src/test/kotlin/AppTest.kt": "class AppTest\n",
        },
        {
            "package-manifest": "build.gradle.kts",
            "lint-config": "detekt.yml",
            "test-config": "build.gradle.kts",
        },
    ),
    "csharp": (
        {
            "App/App.csproj": '<Project Sdk="Microsoft.NET.Sdk" />\n',
            "stylecop.json": "{}\n",
            "tests.runsettings": "<RunSettings />\n",
            "App/Program.cs": "class Program {}\n",
        },
        {
            "package-manifest": "App/App.csproj",
            "lint-config": "stylecop.json",
            "test-config": "tests.runsettings",
        },
    ),
    "ruby": (
        {
            "Gemfile": "source 'https://rubygems.org'\n",
            ".rubocop.yml": "AllCops: {}\n",
            ".rspec": "--require spec_helper\n",
            "lib/app.rb": "module App; end\n",
        },
        {
            "package-manifest": "Gemfile",
            "lint-config": ".rubocop.yml",
            "test-config": ".rspec",
        },
    ),
    "php": (
        {
            "composer.json": "{}\n",
            "phpstan.neon": "parameters: {}\n",
            "phpunit.xml.dist": "<phpunit/>\n",
            "src/App.php": "<?php\n",
        },
        {
            "package-manifest": "composer.json",
            "lint-config": "phpstan.neon",
            "test-config": "phpunit.xml.dist",
        },
    ),
}


@pytest.mark.parametrize("language", sorted(NEW_LANGUAGE_FIXTURES))
def test_new_language_fixture_fills_roles_via_its_registry_entry(
    tmp_path: Path, language: str
) -> None:
    files, expected = NEW_LANGUAGE_FIXTURES[language]
    repo = _write(tmp_path / language, files)
    resolution = _resolve_all(repo)
    assert language in resolution.ecosystems
    for name, path in expected.items():
        assert path in resolution.files[name], (language, name)
    found = run_dimension(DIMENSIONS["code-quality"], repo).sources_found
    assert "lint-config" in found


@pytest.mark.parametrize("language", sorted(NEW_LANGUAGE_FIXTURES))
def test_new_language_lint_config_needs_its_registry_entry(
    tmp_path: Path, language: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The lint file counts only because the language entry is active: with
    that one entry withheld from the registry, the same repo fills nothing."""
    files, expected = NEW_LANGUAGE_FIXTURES[language]
    repo = _write(tmp_path / language, files)
    full = load_registry(known_roles=GENERIC_PATTERNS)
    withheld = Registry(
        languages={k: v for k, v in full.languages.items() if k != language},
        frameworks={},
        warnings=(),
    )
    monkeypatch.setattr(roles_module, "_registry", lambda: withheld)
    resolution = _resolve_all(repo)
    assert language not in resolution.ecosystems
    assert expected["lint-config"] not in resolution.files["lint-config"]


def test_manifest_shared_by_two_languages_activates_both(tmp_path: Path) -> None:
    repo = _write(
        tmp_path / "shared",
        {
            "package.json": "{}\n",
            "pyproject.toml": "[project]\n",
            "build.gradle.kts": "",
        },
    )
    ecosystems = _resolve_all(repo).ecosystems
    assert {"js-ts", "python", "java", "kotlin"} <= set(ecosystems)
    assert list(ecosystems) == sorted(ecosystems)


def test_manifest_activation_is_case_sensitive(tmp_path: Path) -> None:
    repo = _write(tmp_path / "case", {"GO.MOD": "", "gemfile": "", "app.CSPROJ": ""})
    assert _resolve_all(repo).ecosystems == ()


def test_case_sensitive_globs_are_preserved(tmp_path: Path) -> None:
    repo = _write(
        tmp_path / "kt",
        {"build.gradle.kts": "", "latest.json": "{}", "Detekt.YML": ""},
    )
    resolution = _resolve_all(repo)
    assert "latest.json" not in resolution.files["test-file"]
    assert "Detekt.YML" not in resolution.files["lint-config"]


# ---------------------------------------------------------------------------
# AC 5 — a framework entry merges add-only into its language
# ---------------------------------------------------------------------------


def _framework(language: str, patterns: list[str], role_name: str = "lint-config"):
    return f'extends = "{language}"\n\n[[roles.{role_name}]]\n' + _cited(patterns)


def test_framework_entry_merges_add_only_in_deterministic_order(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path,
        {
            "good.toml": GOOD_ENTRY,
            "zeta.toml": _framework("good", ["**/zeta.cfg", "**/shared.cfg"]),
            "alpha.toml": _framework("good", ["**/shared.cfg", "**/alpha.cfg"]),
        },
    )
    loaded = _load(tmp_path)
    assert loaded.warnings == ()
    assert tuple(loaded.frameworks) == ("alpha", "zeta")
    base = loaded.languages["good"]
    alpha, zeta = loaded.frameworks["alpha"], loaded.frameworks["zeta"]

    one = merge(base, (zeta, alpha))
    other = merge(base, (alpha, zeta))
    assert one == other
    merged = Registry(languages={"good": one}, frameworks={}, warnings=())
    assert merged.patterns_for("lint-config", ("good",)) == (
        "**/good-lint.cfg",
        "**/shared.cfg",
        "**/alpha.cfg",
        "**/zeta.cfg",
    )
    # Nothing of the language entry is lost, and its manifests stay its own.
    assert one.manifests == base.manifests
    assert set(base.roles["lint-config"]) <= set(one.roles["lint-config"])


def test_a_framework_cannot_remove_a_pattern(tmp_path: Path) -> None:
    """A framework has no removal syntax, and its fields only ever add."""
    _write(
        tmp_path,
        {
            "good.toml": GOOD_ENTRY,
            "empty-list.toml": 'extends = "good"\n\n[[roles.lint-config]]\n'
            'value = []\ncitation_url = "https://e.org"\nsource_tag = "curated"\n',
            "remove.toml": 'extends = "good"\nremove = ["**/good-lint.cfg"]\n',
        },
    )
    loaded = _load(tmp_path)
    assert loaded.frameworks == {}
    assert [w.split(":")[0] for w in loaded.warnings] == [
        "empty-list.toml",
        "remove.toml",
    ]


def test_framework_extending_an_unknown_language_is_rejected(tmp_path: Path) -> None:
    _write(
        tmp_path,
        {
            "good.toml": GOOD_ENTRY,
            "orphan.toml": _framework("cobol", ["**/x.cfg"]),
            "nested.toml": _framework("orphan", ["**/y.cfg"]),
        },
    )
    loaded = _load(tmp_path)
    assert loaded.frameworks == {}
    assert sorted(w.split(":")[0] for w in loaded.warnings) == [
        "nested.toml",
        "orphan.toml",
    ]


def test_merge_refuses_a_framework_of_another_language(tmp_path: Path) -> None:
    _write(
        tmp_path,
        {
            "good.toml": GOOD_ENTRY,
            "other.toml": GOOD_ENTRY,
            "fw.toml": _framework("good", ["**/x.cfg"]),
        },
    )
    loaded = _load(tmp_path)
    with pytest.raises(ValueError, match="extends 'good'"):
        merge(loaded.languages["other"], (loaded.frameworks["fw"],))


def test_patterns_for_unions_languages_in_order_without_duplicates() -> None:
    loaded = load_registry(known_roles=GENERIC_PATTERNS)
    both = loaded.patterns_for("package-manifest", ("java", "kotlin"))
    assert len(both) == len(set(both))
    assert both[: len(loaded.patterns_for("package-manifest", ("java",)))] == (
        loaded.patterns_for("package-manifest", ("java",))
    )
    assert loaded.patterns_for("package-manifest", ("no-such-language",)) == ()


def test_default_registry_is_the_curated_layer() -> None:
    assert registry_module.curated_root().name == "curated"
