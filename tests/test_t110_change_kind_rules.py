"""T110 -- ``change-risk`` rules for feature, refactor and chore (FR-082).

Slice 1 rules, project defaults (user 2026-10-16): a **feature** passes
``new_code_without_test_share`` <= 0.20 (changed source files with no matched
test added or changed in the scope); a **refactor** passes
``refactor_tests_deleted`` = 0 and ``refactor_uncovered_share`` <= 0.20
(changed source files with no covering test anywhere in the repository); a
**chore** has no rule and abstains with "chore: no test expectation". Only the
active kind's rules are evaluated; the others are not (no silent zero).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from easy_verifier.core.judge import CHANGE_KIND_RULES, RATING_RULES
from easy_verifier.core.score import score_repository

BUGFIX = "bugfix_without_regression_test"
FEATURE = "new_code_without_test_share"
DELETED = "refactor_tests_deleted"
UNCOVERED = "refactor_uncovered_share"
CHORE = "chore: no test expectation"


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()


def _commit(repo: Path, message: str, files: dict[str, str] | None = None) -> None:
    for path, text in (files or {}).items():
        target = repo / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)


BASE = {
    "pyproject.toml": "[project]\nname = 'demo'\n",
    "src/calc.py": "def add(a, b):\n    return a + b\n",
    "src/fmt.py": "def show(x):\n    return str(x)\n",
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


def _headline(repo: Path, agent_input: dict | None = None) -> dict:
    result = score_repository(
        repo, scope="changes", ref="HEAD", agent_input=agent_input
    )
    return result.to_dict()["change_risk"]


def _inputs(headline: dict) -> dict[str, dict]:
    return {item["metric_name"]: item for item in headline["inputs"]}


# --------------------------------------------------------------------------
# AC1 -- three rules, thresholds, project-default citation, kind groups
# --------------------------------------------------------------------------


def test_rule_table_has_the_three_rules_with_project_defaults() -> None:
    rules = RATING_RULES["change-risk"]
    assert list(rules) == [BUGFIX, FEATURE, DELETED, UNCOVERED]
    assert (rules[FEATURE].threshold, rules[FEATURE].comparison) == (0.20, "at_most")
    assert (rules[DELETED].threshold, rules[DELETED].comparison) == (0, "at_most")
    assert (rules[UNCOVERED].threshold, rules[UNCOVERED].comparison) == (
        0.20,
        "at_most",
    )
    for name in (FEATURE, DELETED, UNCOVERED):
        assert rules[name].threshold_citation == "project-default"
    assert CHANGE_KIND_RULES == {
        "bugfix": (BUGFIX,),
        "feature": (FEATURE,),
        "refactor": (DELETED, UNCOVERED),
    }
    for names in CHANGE_KIND_RULES.values():
        assert sum(rules[name].weight for name in names) == 100


# --------------------------------------------------------------------------
# AC1 / AC2 / AC4 -- feature
# --------------------------------------------------------------------------


def test_feature_with_matched_test_passes_only_feature_rule(repo: Path) -> None:
    _commit(
        repo,
        "feat: subtract",
        {
            "src/calc.py": BASE["src/calc.py"] + "\n\ndef sub(a, b):\n    return a - b\n",
            "tests/test_calc.py": BASE["tests/test_calc.py"]
            + "\n\ndef test_sub():\n    assert True\n",
        },
    )
    headline = _headline(repo)
    assert headline["change_kind"]["value"] == "feature"
    assert headline["kind"] == "rating" and headline["value"] == 100
    assert list(_inputs(headline)) == [FEATURE]
    rule = _inputs(headline)[FEATURE]
    assert rule["passed"] is True and rule["metric_value"] == 0
    assert rule["computed_from"] == ["tests/test_calc.py"]
    # the other kinds' rules are not evaluated: neither rated nor listed
    assert headline["unavailable_metrics"] == []


def test_feature_without_test_fails_citing_uncovered_sources(repo: Path) -> None:
    _commit(
        repo,
        "feat: subtract and shout",
        {
            "src/calc.py": BASE["src/calc.py"] + "\n\ndef sub(a, b):\n    return a - b\n",
            "src/fmt.py": "def show(x):\n    return str(x).upper()\n",
            "tests/test_calc.py": BASE["tests/test_calc.py"] + "\n# sub\n",
        },
    )
    headline = _headline(repo)
    assert headline["kind"] == "rating" and headline["value"] == 0
    rule = _inputs(headline)[FEATURE]
    # calc.py has its matched test changed; fmt.py has none: 1 of 2
    assert rule["metric_value"] == 0.5 and rule["passed"] is False
    assert rule["computed_from"] == ["src/fmt.py"]


def test_feature_counts_only_tests_changed_in_scope(repo: Path) -> None:
    # tests/test_calc.py exists in the repository but is not in the change
    _commit(repo, "feat: subtract", {"src/calc.py": "def sub(a, b):\n    return a - b\n"})
    rule = _inputs(_headline(repo))[FEATURE]
    assert rule["metric_value"] == 1.0 and rule["passed"] is False
    assert rule["computed_from"] == ["src/calc.py"]


def test_feature_tests_only_abstains_no_changed_source(repo: Path) -> None:
    _commit(
        repo, "feat: more cases", {"tests/test_calc.py": BASE["tests/test_calc.py"] + "\n#\n"}
    )
    headline = _headline(repo)
    assert headline["kind"] == "rating_abstention"
    assert headline["unavailable_metrics"] == [[FEATURE, "no changed source code"]]


def test_feature_deleted_test_is_not_matched(repo: Path) -> None:
    (repo / "tests" / "test_calc.py").unlink()
    _commit(repo, "feat: subtract", {"src/calc.py": "def sub(a, b):\n    return a - b\n"})
    rule = _inputs(_headline(repo))[FEATURE]
    assert rule["metric_value"] == 1.0 and rule["passed"] is False


# --------------------------------------------------------------------------
# AC1 / AC2 / AC4 / AC5 -- refactor
# --------------------------------------------------------------------------


def test_refactor_covered_by_unchanged_repo_test_passes(repo: Path) -> None:
    _commit(repo, "refactor: tidy add", {"src/calc.py": "def add(x, y):\n    return x + y\n"})
    headline = _headline(repo)
    assert headline["change_kind"]["value"] == "refactor"
    assert headline["kind"] == "rating" and headline["value"] == 100
    assert list(_inputs(headline)) == [DELETED, UNCOVERED]
    assert _inputs(headline)[DELETED]["metric_value"] == 0
    assert _inputs(headline)[UNCOVERED]["metric_value"] == 0
    assert headline["unavailable_metrics"] == []


def test_refactor_uncovered_source_fails_citing_it(repo: Path) -> None:
    _commit(
        repo,
        "refactor: tidy both",
        {
            "src/calc.py": "def add(x, y):\n    return x + y\n",
            "src/fmt.py": "def show(v):\n    return str(v)\n",
        },
    )
    headline = _headline(repo)
    rule = _inputs(headline)[UNCOVERED]
    assert rule["metric_value"] == 0.5 and rule["passed"] is False
    assert rule["computed_from"] == ["src/fmt.py"]
    assert headline["value"] == 50


def test_refactor_deleting_a_test_fails_and_names_it(repo: Path) -> None:
    (repo / "tests" / "test_calc.py").unlink()
    _commit(repo, "refactor: tidy add", {"src/calc.py": "def add(x, y):\n    return x + y\n"})
    headline = _headline(repo)
    deleted = _inputs(headline)[DELETED]
    assert deleted["metric_value"] == 1 and deleted["passed"] is False
    assert "tests/test_calc.py" in str(_derivation(repo, DELETED))
    # a deleted test never covers (AC5)
    assert _inputs(headline)[UNCOVERED]["metric_value"] == 1.0


def test_refactor_rename_with_test_is_covered_nothing_deleted(repo: Path) -> None:
    _git(repo, "mv", "src/calc.py", "src/arith.py")
    _git(repo, "mv", "tests/test_calc.py", "tests/test_arith.py")
    _commit(
        repo,
        "refactor: rename calc",
        {
            "src/arith.py": "def add(a, b):\n    # sum\n    return a + b\n",
            "tests/test_arith.py": BASE["tests/test_calc.py"].replace("calc", "arith"),
        },
    )
    headline = _headline(repo)
    assert _inputs(headline)[DELETED]["metric_value"] == 0
    assert _inputs(headline)[UNCOVERED]["metric_value"] == 0


def test_refactor_monorepo_test_in_other_project_does_not_cover(repo: Path) -> None:
    _commit(
        repo,
        "chore: two services",
        {
            "svc_a/pyproject.toml": "[project]\nname = 'a'\n",
            "svc_a/src/pay.py": "def pay():\n    return 1\n",
            "svc_b/pyproject.toml": "[project]\nname = 'b'\n",
            "svc_b/tests/test_pay.py": "def test_pay():\n    assert True\n",
        },
    )
    _commit(repo, "refactor: pay", {"svc_a/src/pay.py": "def pay():\n    return 2 - 1\n"})
    rule = _inputs(_headline(repo))[UNCOVERED]
    assert rule["metric_value"] == 1.0 and rule["computed_from"] == ["svc_a/src/pay.py"]


def test_confirmed_refactor_applies_refactor_rules(repo: Path) -> None:
    _commit(repo, "feat: tidy add", {"src/calc.py": "def add(x, y):\n    return x + y\n"})
    before = _headline(repo)
    assert before["change_kind"]["value"] == "feature"
    assert list(_inputs(before)) == [FEATURE]
    answer = {"change_kind": {"value": "refactor", "reason": "renames parameters"}}
    after = _headline(repo, answer)
    assert after["change_kind"]["source"] == "confirmed"
    assert after["change_kind"]["value"] == "refactor"
    assert list(_inputs(after)) == [DELETED, UNCOVERED]
    assert after["value"] == 100


# --------------------------------------------------------------------------
# AC2 / AC3 -- bugfix untouched, chore abstains
# --------------------------------------------------------------------------


def test_bugfix_evaluates_only_its_rule(repo: Path) -> None:
    _commit(repo, "fix: add", {"src/calc.py": "def add(a, b):\n    return b + a\n"})
    headline = _headline(repo)
    assert list(_inputs(headline)) == [BUGFIX]
    assert headline["unavailable_metrics"] == []


@pytest.mark.parametrize(
    ("message", "files"),
    [
        ("docs: readme", {"README.md": "# demo\n\nmore\n"}),
        ("update lockfile", {"uv.lock": "version = 1\n"}),
    ],
)
def test_chore_abstains_with_exact_reason(repo: Path, message: str, files) -> None:
    _commit(repo, message, files)
    headline = _headline(repo)
    assert headline["change_kind"]["value"] == "chore"
    assert headline["kind"] == "rating_abstention"
    assert not headline.get("inputs")
    assert {reason for _name, reason in headline["unavailable_metrics"]} == {CHORE}
    assert [name for name, _ in headline["unavailable_metrics"]] == list(
        RATING_RULES["change-risk"]
    )


def _derivation(repo: Path, metric: str) -> str:
    payload = score_repository(repo, scope="changes", ref="HEAD").to_dict()
    for item in payload["metrics"]:
        if item.get("name") == metric and item.get("dimension") == "change-risk":
            return str(item)
    return ""
