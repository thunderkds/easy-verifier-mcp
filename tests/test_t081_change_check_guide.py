"""T081: the README and Docker guide tell a user how to check a feature or bugfix.

Pins the documented commands, and the range semantics they promise: three dots
rate the whole branch from where it left its base, a bare branch name rates only
its tip commit. Also pins the stated limit, so the guide cannot quietly drop it
before change-risk rules exist.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from easy_verifier.core.scope import resolve_scope

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
DOCKER_GUIDE = ROOT / "docs" / "DOCKER_MCP_GUIDE.md"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def _commit(repo: Path, name: str) -> None:
    (repo / name).write_text(name, encoding="utf-8")
    _git(repo, "add", name)
    _git(repo, "commit", "-q", "-m", name)


def _branch_repo(tmp_path: Path) -> Path:
    """main: base.py, later.py. feature (from base): one.py, two.py."""
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "config", "user.email", "t@example.com")
    _git(tmp_path, "config", "user.name", "t")
    _commit(tmp_path, "base.py")
    _git(tmp_path, "switch", "-q", "-c", "feature")
    _commit(tmp_path, "one.py")
    _commit(tmp_path, "two.py")
    _git(tmp_path, "switch", "-q", "main")
    _commit(tmp_path, "later.py")
    _git(tmp_path, "switch", "-q", "feature")
    return tmp_path


def test_readme_documents_the_change_check() -> None:
    readme = README.read_text(encoding="utf-8")
    assert "### Checking a feature or bugfix" in readme
    assert "--scope changes --ref main...HEAD < /dev/null" in readme
    assert "--scope worktree" in readme
    assert 'scope="changes"' in readme and 'ref="main...HEAD"' in readme
    assert "**that one commit**" in readme


def test_readme_states_the_change_score_is_partial() -> None:
    readme = README.read_text(encoding="utf-8")
    assert "Read a change score as partial" in readme
    assert "**not penalised**" in readme
    assert "`overall.abstentions`" in readme


def test_docker_guide_points_to_the_change_check() -> None:
    guide = DOCKER_GUIDE.read_text(encoding="utf-8")
    assert "## 5. Check a feature or bugfix" in guide
    assert 'ref="main...HEAD"' in guide
    assert "not penalised" in guide


def test_three_dots_rate_the_whole_branch_only(tmp_path: Path) -> None:
    repo = _branch_repo(tmp_path)
    scope = resolve_scope("changes", repo, None, ref="main...HEAD")
    assert scope.changed_files == ("one.py", "two.py")


def test_bare_branch_name_rates_only_its_tip_commit(tmp_path: Path) -> None:
    repo = _branch_repo(tmp_path)
    scope = resolve_scope("changes", repo, None, ref="feature")
    assert scope.changed_files == ("two.py",)
