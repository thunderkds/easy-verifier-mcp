"""T108 -- the ``change-risk`` dimension, slice 1 (FR-079, FR-080, FR-082).

A change (not the repository) is rated at ``changes`` and ``worktree`` scope:
its kind is detected from the branch name, commit subjects, issue references
and file kinds, and a bugfix passes ``bugfix_without_regression_test`` only
when a test file added or changed in the scope is a matched test for changed
code. The rating is a separate ``change_risk`` headline, never averaged into
``overall``; at ``project`` scope the dimension is left out of the score and,
called alone, abstains with a stated reason.
"""

from __future__ import annotations

import io
import json
import subprocess
from pathlib import Path

import pytest

from easy_verifier.core.judge import RATING_RULES, floor_of
from easy_verifier.core.pipeline import run_dimension
from easy_verifier.core.score import score_repository
from easy_verifier.dimensions import DIMENSIONS, change_risk, list_dimensions

RULE = "bugfix_without_regression_test"
SCOPE_ONLY = "change risk is rated at changes/worktree scope only"


# --------------------------------------------------------------------------
# synthetic repositories
# --------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


def _write(repo: Path, files: dict[str, str]) -> None:
    for path, text in files.items():
        target = repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)


def _commit(repo: Path, message: str, files: dict[str, str] | None = None) -> str:
    _write(repo, files or {})
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


BASE = {
    "pyproject.toml": "[project]\nname = 'demo'\n",
    "src/calc.py": "def add(a, b):\n    return a + b\n",
    "tests/test_calc.py": (
        "from calc import add\n\n\ndef test_add():\n    assert add(1, 2) == 3\n"
    ),
    "README.md": "# demo\n",
}


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "t")
    _commit(root, "chore: initial", BASE)
    return root


def _headline(repo: Path, **kwargs) -> dict:
    return score_repository(repo, **kwargs).to_dict()["change_risk"]


# --------------------------------------------------------------------------
# AC1 -- registered, listed, callable alone, descriptor + roles + floor
# --------------------------------------------------------------------------


def test_registered_listed_with_roles_and_floor() -> None:
    assert DIMENSIONS["change-risk"] is change_risk.DESCRIPTOR
    listed = {item.name: item for item in list_dimensions()}
    assert "change-risk" in listed
    assert listed["change-risk"].roles == change_risk.ROLES
    assert listed["change-risk"].roles
    assert floor_of("change-risk") is not None
    # T110 adds the feature and refactor rules beside the bugfix rule
    assert set(RATING_RULES["change-risk"]) == {
        RULE,
        "new_code_without_test_share",
        "refactor_tests_deleted",
        "refactor_uncovered_share",
    }


def test_cli_and_mcp_expose_it_alone(repo: Path, capsys) -> None:
    from easy_verifier.adapters import cli, mcp_server

    assert cli.main(["change-risk", "--repo", str(repo), "--scope", "project"]) == 0
    pack = json.loads(capsys.readouterr().out)
    assert pack["dimension"] == "change-risk"
    names = {item["name"] for item in mcp_server.discover_dimensions()}
    assert "change-risk" in names


# --------------------------------------------------------------------------
# AC3 -- kind detection, one test per signal, per conflict, default
# --------------------------------------------------------------------------


def _detect(**kwargs):
    args = {"branch": None, "commits": (), "changed_files": ("src/a.py",)}
    return change_risk.detect_change_kind(**{**args, **kwargs})


@pytest.mark.parametrize(
    ("branch", "kind"),
    [
        ("fix/login", "bugfix"),
        ("bugfix/login", "bugfix"),
        ("hotfix/login", "bugfix"),
        ("feat/login", "feature"),
        ("feature/login", "feature"),
        ("refactor/login", "refactor"),
        ("chore/bump", "chore"),
        ("docs/readme", "chore"),
        ("ci/cache", "chore"),
        ("deps/bump", "chore"),
    ],
)
def test_branch_prefix_signal(branch: str, kind: str) -> None:
    detected = _detect(branch=branch)
    assert detected.value == kind
    assert detected.source == "detected"
    assert [(s.source, s.value, s.kind) for s in detected.signals] == [
        ("branch", branch, kind)
    ]


@pytest.mark.parametrize(
    ("subject", "kind"),
    [
        ("fix: off by one", "bugfix"),
        ("fix(api): off by one", "bugfix"),
        ("feat: add login", "feature"),
        ("feat(ui)!: new login", "feature"),
        ("refactor: split module", "refactor"),
        ("chore: bump", "chore"),
        ("docs: readme", "chore"),
        ("ci: cache", "chore"),
        ("build: pin", "chore"),
        ("Bugfix/ Update condition time range", "bugfix"),
    ],
)
def test_commit_subject_signal(subject: str, kind: str) -> None:
    detected = _detect(commits=(("abcdef1234567890", subject + "\n\nbody\n"),))
    assert detected.value == kind
    assert [(s.source, s.kind) for s in detected.signals] == [("commit subject", kind)]
    assert detected.signals[0].value == f"abcdef12 {subject}"


def test_unconventional_subject_is_no_signal() -> None:
    detected = _detect(commits=(("abcdef1234567890", "Update the login page"),))
    assert detected.value == "feature"
    assert detected.signals == ()


def test_issue_reference_signal() -> None:
    detected = _detect(
        commits=(("abcdef1234567890", "Update login\n\nFixes #12\nRefs #3\n"),)
    )
    assert detected.value == "bugfix"
    assert [(s.source, s.value, s.kind) for s in detected.signals] == [
        ("issue reference", "abcdef12 Fixes #12", "bugfix")
    ]


def test_file_kinds_signal_only_docs_config_lockfile() -> None:
    detected = _detect(changed_files=("README.md", "package-lock.json", "a.toml"))
    assert detected.value == "chore"
    assert [(s.source, s.kind) for s in detected.signals] == [("file kinds", "chore")]


def test_code_change_gives_no_file_kind_signal() -> None:
    assert _detect(changed_files=("README.md", "src/a.py")).signals == ()


@pytest.mark.parametrize(
    ("branch", "subject", "kind"),
    [
        ("feature/x", "fix: y", "bugfix"),
        ("refactor/x", "feat: y", "feature"),
        ("chore/x", "refactor: y", "refactor"),
        ("fix/x", "docs: y", "bugfix"),
    ],
)
def test_conflict_most_demanding_wins(branch: str, subject: str, kind: str) -> None:
    detected = _detect(branch=branch, commits=(("abcdef1234567890", subject),))
    assert detected.value == kind
    assert [s.source for s in detected.signals] == ["branch", "commit subject"]


def test_no_signal_defaults_to_feature() -> None:
    detected = _detect()
    assert detected.value == "feature"
    assert detected.signals == ()


def test_detection_is_deterministic() -> None:
    commits = (("1" * 40, "fix: a"), ("2" * 40, "feat: b\n\nfixes #4"))
    assert _detect(branch="fix/x", commits=commits) == _detect(
        branch="fix/x", commits=commits
    )


# --------------------------------------------------------------------------
# AC4 / AC8 -- the bugfix rule on synthetic git repositories
# --------------------------------------------------------------------------


def test_bugfix_with_matched_test_passes_then_without_fails(repo: Path) -> None:
    _commit(
        repo,
        "fix: add handles negatives",
        {
            "src/calc.py": "def add(a, b):\n    return int(a) + int(b)\n",
            "tests/test_calc.py": BASE["tests/test_calc.py"]
            + "\n\ndef test_negative():\n    assert add(-1, 1) == 0\n",
        },
    )
    passing = _headline(repo, scope="changes", ref="HEAD")
    assert passing["kind"] == "rating"
    assert passing["value"] == 100
    (rule,) = passing["inputs"]
    assert rule["metric_name"] == RULE
    assert rule["passed"] is True and rule["metric_value"] == 1
    assert rule["computed_from"] == ["tests/test_calc.py"]
    assert rule["threshold"] == 1 and rule["comparison"] == "at_least"
    assert rule["threshold_citation"] == "project-default"
    assert passing["change_kind"]["value"] == "bugfix"
    assert passing["change_kind"]["source"] == "detected"
    assert passing["change_kind"]["signals"][0]["source"] == "commit subject"

    _commit(
        repo,
        "fix: add handles strings",
        {"src/calc.py": "def add(a, b):\n    return float(a) + float(b)\n"},
    )
    failing = _headline(repo, scope="changes", ref="HEAD")
    assert failing["kind"] == "rating"
    assert failing["value"] == 0
    (rule,) = failing["inputs"]
    assert rule["passed"] is False and rule["metric_value"] == 0
    assert rule["computed_from"] == ["src/calc.py"]


def test_deleted_test_never_matches(repo: Path) -> None:
    (repo / "tests" / "test_calc.py").unlink()
    _commit(repo, "fix: add", {"src/calc.py": "def add(a, b):\n    return b + a\n"})
    headline = _headline(repo, scope="changes", ref="HEAD")
    assert headline["value"] == 0
    assert headline["inputs"][0]["computed_from"] == ["src/calc.py"]


def test_test_in_another_project_of_a_monorepo_does_not_match(tmp_path: Path) -> None:
    root = tmp_path / "mono"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "t")
    # The manifests are outside the diff: only a repository-wide boundary
    # keeps src/a and src/b apart (both sit under the layout segment `src`).
    _commit(
        root,
        "chore: two packages",
        {
            "src/a/package.json": '{"name": "a"}\n',
            "src/b/package.json": '{"name": "b"}\n',
            "src/a/util.js": "export const f = () => 1\n",
            "src/b/util.js": "export const f = () => 2\n",
        },
    )
    _commit(
        root,
        "fix: a returns one",
        {
            "src/a/util.js": "export const f = () => 1 + 0\n",
            "src/b/util.test.js": "test('f', () => { expect(1).toBe(1) })\n",
        },
    )
    assert _headline(root, scope="changes", ref="HEAD")["value"] == 0

    _commit(
        root,
        "fix: a again",
        {
            "src/a/util.js": "export const f = () => 0 + 1\n",
            "src/a/util.test.js": "test('f', () => { expect(1).toBe(1) })\n",
        },
    )
    headline = _headline(root, scope="changes", ref="HEAD")
    assert headline["value"] == 100
    assert headline["inputs"][0]["computed_from"] == ["src/a/util.test.js"]


def test_worktree_scope_uses_branch_and_rates(repo: Path) -> None:
    _git(repo, "checkout", "-q", "-b", "fix/negatives")
    _write(repo, {"src/calc.py": "def add(a, b):\n    return b + a\n"})
    failing = _headline(repo, scope="worktree")
    assert failing["value"] == 0
    assert [
        (s["source"], s["value"]) for s in failing["change_kind"]["signals"]
    ] == [("branch", "fix/negatives")]

    _write(repo, {"tests/test_calc.py": BASE["tests/test_calc.py"] + "\n# more\n"})
    assert _headline(repo, scope="worktree")["value"] == 100


def test_project_scope_abstains_alone_and_is_left_out_of_score(repo: Path) -> None:
    pack = run_dimension(DIMENSIONS["change-risk"], repo, scope="project")
    assert [m.reason for m in pack.sources_missing] == [SCOPE_ONLY]
    assert pack.coverage_score == 0.0

    payload = score_repository(repo, scope="project").to_dict()
    assert "change_risk" not in payload
    assert "change-risk" not in json.dumps(payload)
    assert payload["overall"]["total_dimension_count"] == 13


def test_task_scope_abstains_with_stated_reason(repo: Path) -> None:
    pack = run_dimension(
        DIMENSIONS["change-risk"], repo, scope="task", task_id="T001"
    )
    assert [m.reason for m in pack.sources_missing] == [SCOPE_ONLY]


def test_overall_is_unchanged_by_the_dimension(repo: Path) -> None:
    _commit(repo, "fix: add", {"src/calc.py": "def add(a, b):\n    return b + a\n"})
    payload = score_repository(repo, scope="changes", ref="HEAD").to_dict()
    overall = payload["overall"]
    assert "change-risk" not in overall["contributors"]
    assert overall["total_dimension_count"] == 13
    assert all(item["dimension"] != "change-risk" for item in payload["ratings"])
    assert all(item["dimension"] != "change-risk" for item in payload["provenance"])
    assert payload["change_risk"]["value"] == 0


def test_other_kinds_get_their_own_rules_from_t110(repo: Path) -> None:
    subtract = {"src/calc.py": "def sub(a, b):\n    return a - b\n"}
    _commit(repo, "feat: subtract", subtract)
    headline = _headline(repo, scope="changes", ref="HEAD")
    # T110: a feature is rated by its own rule, the bugfix rule not evaluated
    assert headline["kind"] == "rating"
    assert [item["metric_name"] for item in headline["inputs"]] == [
        "new_code_without_test_share"
    ]
    assert headline["unavailable_metrics"] == []
    assert headline["change_kind"]["value"] == "feature"


def test_test_only_bugfix_has_no_changed_source(repo: Path) -> None:
    _commit(
        repo,
        "fix: cover zero",
        {"tests/test_calc.py": BASE["tests/test_calc.py"] + "\n# zero\n"},
    )
    headline = _headline(repo, scope="changes", ref="HEAD")
    assert headline["kind"] == "rating_abstention"
    assert headline["unavailable_metrics"] == [[RULE, "no changed source code"]]


def test_rename_only_is_not_changed_code(repo: Path) -> None:
    _git(repo, "mv", "src/calc.py", "src/arith.py")
    _git(repo, "commit", "-q", "-m", "fix: rename")
    headline = _headline(repo, scope="changes", ref="HEAD")
    assert headline["unavailable_metrics"] == [[RULE, "no changed source code"]]


def test_root_commit_abstains_disclosed(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "t")
    _commit(root, "fix: first", {"src/calc.py": "x = 1\n"})
    headline = _headline(root, scope="changes", ref="HEAD")
    assert headline["kind"] == "rating_abstention"
    reasons = [miss["reason"] for miss in headline["sources_missing"]]
    assert any("root commit" in reason for reason in reasons)


def test_clipped_diff_abstains_disclosed(repo: Path) -> None:
    _commit(
        repo,
        "fix: big",
        {
            "src/calc.py": "def add(a, b):\n    return b + a\n",
            "tests/test_calc.py": BASE["tests/test_calc.py"] + "\n# more\n",
            "data.txt": "x" * 210_000 + "\n",
        },
    )
    headline = _headline(repo, scope="changes", ref="HEAD")
    assert headline["kind"] == "rating_abstention"
    reasons = [miss["reason"] for miss in headline["sources_missing"]]
    assert any("clipped" in reason for reason in reasons)


def test_empty_worktree_abstains(repo: Path) -> None:
    headline = _headline(repo, scope="worktree")
    assert headline["kind"] == "rating_abstention"
    assert headline["change_kind"] is None


def test_replay_is_byte_equal(repo: Path) -> None:
    _commit(repo, "fix: add", {"src/calc.py": "def add(a, b):\n    return b + a\n"})
    first = score_repository(repo, scope="changes", ref="HEAD").serialize()
    second = score_repository(repo, scope="changes", ref="HEAD").serialize()
    assert first == second


def test_cli_payload_carries_the_headline(repo: Path, capsys, monkeypatch) -> None:
    from easy_verifier.adapters import cli

    monkeypatch.setattr("sys.stdin", io.TextIOWrapper(io.BytesIO(b"")))
    _commit(repo, "fix: add", {"src/calc.py": "def add(a, b):\n    return b + a\n"})
    argv = ["score", "--repo", str(repo), "--scope", "changes", "--ref", "HEAD"]
    assert cli.main(argv) == 0
    payload = json.loads(capsys.readouterr().out)
    expected = score_repository(repo, scope="changes", ref="HEAD").to_dict()
    assert payload["change_risk"] == expected["change_risk"]
    assert list(payload)[:2] == ["ratings", "overall"]
    assert list(payload)[2] == "change_risk"


# --------------------------------------------------------------------------
# AC6 -- HTML report block
# --------------------------------------------------------------------------


def test_report_shows_change_risk_block(
    repo: Path, tmp_path: Path, monkeypatch
) -> None:
    from easy_verifier.core.report import write_report
    from easy_verifier.core.score import report_dimensions
    from easy_verifier.core.synthesis import combined_pack

    monkeypatch.setenv("EASY_VERIFIER_REPORTS_DIR", str(tmp_path / "reports"))
    _commit(repo, "fix: add", {"src/calc.py": "def add(a, b):\n    return b + a\n"})
    names, packs_active = report_dimensions(repo)
    packs = combined_pack(names, repo_path=repo, scope="changes", ref="HEAD")
    result = write_report([], packs, repo)
    html = Path(result.absolute_path).read_text()
    assert "Change risk <strong>0/100</strong>" in html
    assert "bugfix" in html and "commit subject" in html
    assert RULE in html and "src/calc.py" in html


def test_project_report_omits_the_change_risk_line(
    repo: Path, tmp_path: Path, monkeypatch
) -> None:
    from easy_verifier.core.report import write_report
    from easy_verifier.core.score import report_dimensions
    from easy_verifier.core.synthesis import combined_pack
    from easy_verifier.dimensions import dimension_names

    monkeypatch.setenv("EASY_VERIFIER_REPORTS_DIR", str(tmp_path / "reports"))
    names, _active = report_dimensions(repo, scope="project")
    assert "change-risk" not in names
    assert "change-risk" in report_dimensions(repo, scope="changes")[0]
    for gathered in (names, dimension_names()):
        packs = combined_pack(gathered, repo_path=repo, scope="project")
        html = Path(write_report([], packs, repo).absolute_path).read_text()
        assert "Change risk" not in html
        assert "Overall <strong>" in html
