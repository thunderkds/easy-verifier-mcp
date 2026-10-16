"""T107 -- context roles are read repository-wide at narrow scopes (FR-078).

A one-file change sits in a repository whose test config, CI workflow,
lockfile, manifest, container config, API spec and README are all outside the
diff. At ``changes`` scope each dimension must read those as *context* (cited,
and named in a warning) while measuring only the changed file; ``project``
scope must not change at all, and an unresolved or empty narrow scope must
still refuse rather than turn into a repository read.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from easy_verifier.core import roles as roles_module
from easy_verifier.core.pipeline import run_dimension
from easy_verifier.dimensions import (
    api,
    data,
    infrastructure,
    operations,
    reliability,
    security,
    supply_chain,
    test_strategy,
)

LISTED = (
    test_strategy,
    security,
    supply_chain,
    operations,
    infrastructure,
    api,
    data,
    reliability,
)

#: Context files committed in the first commit, outside the one-file diff.
CONTEXT_FILES = {
    "vitest.config.ts": "export default { test: { include: ['tests/**'] } }\n",
    ".github/workflows/ci.yml": (
        "name: ci\non: [push]\njobs:\n  test:\n    runs-on: ubuntu-latest\n"
        "    steps:\n      - uses: actions/checkout@v4\n      - run: npm test\n"
    ),
    "package.json": (
        '{"name": "demo", "version": "1.0.0", "scripts": {"test": "vitest"}}\n'
    ),
    "package-lock.json": '{"name": "demo", "lockfileVersion": 3, "packages": {}}\n',
    "Dockerfile": "FROM node:20-alpine\nUSER node\nCMD [\"node\", \"src/app.js\"]\n",
    "openapi.yaml": (
        "openapi: 3.0.0\ninfo:\n  title: demo\n  version: 1.0.0\npaths: {}\n"
    ),
    "README.md": "# demo\n\nA demo service.\n",
}

#: Roles that are not context roles, also outside the diff: they must still be
#: reported as outside the scope (measured roles never widen).
NON_CONTEXT_FILES = {
    "Makefile": "test:\n\tnpm test\n",  # operations: dev-environment
    "prisma/schema.prisma": "model User {\n  id Int @id\n}\n",  # data: schema-file
    "src/auth/session.js": "export function login() { return 1 }\n",  # auth-code
}

#: Code that is outside the diff and must never be measured at changes scope.
UNCHANGED_CODE = {
    "src/other.js": "export function other() { return 2 }\n",
    "tests/other.test.js": "import { other } from '../src/other.js'\n"
    "test('other', () => { expect(other()).toBe(2) })\n",
}

CHANGED = "src/app.js"

EXPECTED_CONTEXT = {
    test_strategy: {
        "test-config": "vitest.config.ts",
        "ci-workflow": ".github/workflows/ci.yml",
    },
    security: {
        "package-manifest": "package.json",
        "lockfile": "package-lock.json",
        "container-config": "Dockerfile",
        "ci-workflow": ".github/workflows/ci.yml",
    },
    supply_chain: {
        "package-manifest": "package.json",
        "lockfile": "package-lock.json",
        "ci-workflow": ".github/workflows/ci.yml",
    },
    infrastructure: {"container-config": "Dockerfile"},
    api: {"api-spec": "openapi.yaml"},
    reliability: {"readme": "README.md"},
}

EXPECTED_STILL_OUT_OF_SCOPE = {
    operations: "dev-environment",
    data: "schema-file",
    security: "auth-code",
}


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        env={
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@example.com",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@example.com",
            "PATH": "/usr/bin:/bin",
            "HOME": str(repo),
        },
    )


def _write(root: Path, files: dict[str, str]) -> None:
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    _write(tmp_path, {**CONTEXT_FILES, **NON_CONTEXT_FILES, **UNCHANGED_CODE})
    _write(tmp_path, {CHANGED: "export function app() { return 1 }\n"})
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "base")
    _write(tmp_path, {CHANGED: "export function app() { return 3 }\n"})
    _git(tmp_path, "commit", "-q", "-am", "change app")
    return tmp_path


def _changes(module, repo: Path):
    return run_dimension(module.DESCRIPTOR, repo, scope="changes", ref="HEAD")


def _reasons(pack) -> dict[str, str]:
    return {miss.source: miss.reason for miss in pack.sources_missing}


def test_context_roles_are_one_shared_definition_of_fr078_roles() -> None:
    assert roles_module.CONTEXT_ROLES == frozenset(
        {
            "test-config",
            "ci-workflow",
            "lockfile",
            "lint-config",
            "format-config",
            "package-manifest",
            "container-config",
            "api-spec",
            "readme",
            "architecture-doc",
            "decision-record",
            "requirements-doc",
            "spec-doc",
            "task-breakdown",
            "contributing-guide",
            "licence-file",
        }
    )
    # Every name is a real role, and no measured or secret-bearing role is one.
    assert roles_module.CONTEXT_ROLES <= set(roles_module.GENERIC_PATTERNS)
    measured = {"test-file", "auth-code", "credential-file"}
    assert not roles_module.CONTEXT_ROLES & measured


@pytest.mark.parametrize("module", list(EXPECTED_CONTEXT), ids=lambda m: m.NAME)
def test_changes_scope_reads_context_roles_from_the_whole_repository(
    repo: Path, module
) -> None:
    pack = _changes(module, repo)
    reasons = _reasons(pack)
    for role_name, path in EXPECTED_CONTEXT[module].items():
        assert path in pack.files_read, (role_name, pack.files_read)
        assert role_name in pack.sources_found, role_name
        assert "not in the resolved" not in reasons.get(role_name, ""), role_name
    # AC3: the pack says which roles were read as repository context.
    notes = [w for w in pack.warnings if "repository context" in w]
    assert len(notes) == 1, pack.warnings
    for role_name in EXPECTED_CONTEXT[module]:
        assert role_name in notes[0]
    assert "changes scope" in notes[0]


@pytest.mark.parametrize("module", LISTED, ids=lambda m: m.NAME)
def test_changes_scope_still_measures_only_the_changed_code(repo: Path, module) -> None:
    pack = _changes(module, repo)
    for path in (*UNCHANGED_CODE, "src/auth/session.js"):
        assert path not in pack.files_read, (path, pack.files_read)
    for source, reason in _reasons(pack).items():
        if source in roles_module.CONTEXT_ROLES:
            assert "not in the resolved" not in reason, source


@pytest.mark.parametrize(
    "module", list(EXPECTED_STILL_OUT_OF_SCOPE), ids=lambda m: m.NAME
)
def test_non_context_roles_outside_the_diff_stay_outside_the_scope(
    repo: Path, module
) -> None:
    pack = _changes(module, repo)
    role_name = EXPECTED_STILL_OUT_OF_SCOPE[module]
    assert "not in the resolved" in _reasons(pack)[role_name]
    for path in NON_CONTEXT_FILES:
        assert path not in pack.files_read


def test_test_strategy_correspondence_counts_only_the_changed_file(repo: Path) -> None:
    pack = _changes(test_strategy, repo)
    reason = _reasons(pack)[test_strategy.CORRESPONDENCE_SOURCE]
    assert CHANGED in reason
    assert "src/other.js" not in reason


@pytest.mark.parametrize("module", LISTED, ids=lambda m: m.NAME)
def test_project_scope_is_unchanged_by_context_roles(
    repo: Path, module, monkeypatch: pytest.MonkeyPatch
) -> None:
    after = run_dimension(module.DESCRIPTOR, repo, scope="project")
    monkeypatch.setattr(roles_module, "CONTEXT_ROLES", frozenset())
    before = run_dimension(module.DESCRIPTOR, repo, scope="project")
    assert after == before
    assert not any("repository context" in w for w in after.warnings)


@pytest.mark.parametrize("module", LISTED, ids=lambda m: m.NAME)
def test_unresolved_narrow_scope_still_refuses(repo: Path, module) -> None:
    # `changes` without its ref never resolves: nothing may be read.
    pack = run_dimension(module.DESCRIPTOR, repo, scope="changes")
    assert pack.files_read == ()
    assert pack.excerpts == ()
    assert any("could not be resolved" in w for w in pack.warnings)
    assert all("could not be resolved" in m.reason for m in pack.sources_missing)


@pytest.mark.parametrize("module", LISTED, ids=lambda m: m.NAME)
def test_task_scope_without_kit_artifacts_still_reads_nothing(
    repo: Path, module
) -> None:
    pack = run_dimension(module.DESCRIPTOR, repo, scope="task", task_id="T999")
    assert pack.files_read == ()
    assert not any("repository context" in w for w in pack.warnings)
