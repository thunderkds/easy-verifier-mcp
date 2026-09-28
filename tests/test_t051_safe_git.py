"""T051 Stage 4 P0 — git never runs a program named by the target repo (NFR-007).

A target's ``.git/config`` is untrusted: a copied checkout can name a program
for ``core.fsmonitor``, ``diff.external``, a ``diff.<driver>.textconv``, a
``filter.<driver>.clean`` or an index hook, and plain ``git status`` runs it.
The fixture arms all of them with a script that writes a marker file outside
the repository, then drives the real CLI; the marker must never appear.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from easy_verifier.core.git import SAFE_CONFIG, git_command

SRC = Path(__file__).resolve().parents[1] / "src"

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git not on PATH")


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "user.email=t@example.invalid",
            "-c",
            "user.name=t",
            *args,
        ],
        check=True,
        capture_output=True,
        stdin=subprocess.DEVNULL,
    )


@pytest.fixture
def armed_repo(tmp_path: Path) -> tuple[Path, Path]:
    """A repo whose config names ``hook.sh`` for every execution path git has."""
    marker = tmp_path / "marker"
    hook = tmp_path / "hook.sh"
    hook.write_text(
        f'#!/bin/sh\necho "$0 $*" >> "{marker}"\nexit 0\n', encoding="utf-8"
    )
    hook.chmod(0o755)
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / ".gitattributes").write_text(
        "*.py filter=evil diff=evil\n", encoding="utf-8"
    )
    (repo / "app.py").write_text("x = 1\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "c1")
    (repo / "app.py").write_text("x = 2\n", encoding="utf-8")
    _git(repo, "commit", "-qam", "c2")
    for key in (
        "core.fsmonitor",
        "diff.external",
        "diff.evil.textconv",
        "diff.evil.command",
        "filter.evil.clean",
        "filter.evil.smudge",
        "core.pager",
    ):
        _git(repo, "config", key, str(hook))
    _git(repo, "config", "filter.evil.required", "true")
    hooks = repo / ".git" / "hooks"
    for name in ("post-index-change", "post-checkout", "reference-transaction"):
        shutil.copy(hook, hooks / name)
    # Same size, new mtime: `status` must re-hash, which is when a clean filter
    # runs; plus an uncommitted change for worktree scope to find.
    (repo / "app.py").write_text("x = 3\n", encoding="utf-8")
    os.utime(repo / "app.py", (1_000_000_000, 1_000_000_000))
    return repo, marker


def test_fixture_is_armed(armed_repo: tuple[Path, Path]) -> None:
    # Positive control: without the runner's defences the same git commands
    # execute the repo's program, so a clean marker below means something.
    repo, marker = armed_repo
    subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain"],
        capture_output=True,
        stdin=subprocess.DEVNULL,
        timeout=60,
        check=False,
    )
    assert marker.exists()


@pytest.mark.parametrize(
    "scope_args",
    [
        ["--scope", "project"],
        ["--scope", "worktree"],
        ["--scope", "changes", "--range", "HEAD"],
    ],
)
def test_cli_score_never_executes_repo_config_programs(
    armed_repo: tuple[Path, Path], scope_args: list[str]
) -> None:
    repo, marker = armed_repo
    env = {**os.environ, "PYTHONPATH": str(SRC)}
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "easy_verifier.adapters.cli",
            "score",
            "--repo",
            str(repo),
            *scope_args,
        ],
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        env=env,
        timeout=300,
        check=False,
    )
    assert result.returncode == 0, result.stderr[-2000:]
    # blast-radius (git log / rev-parse) is one of the seven dimensions scored.
    assert '"blast-radius"' in result.stdout
    assert not marker.exists(), marker.read_text(encoding="utf-8")


def test_runner_command_carries_every_defence() -> None:
    command = git_command("/r", ["diff", "--name-only", "A..B"])
    assert Path(command[0]).name == "git"
    for setting in (
        "core.fsmonitor=false",
        "core.hooksPath=/dev/null",
        "diff.external=",
        "core.pager=cat",
        "protocol.allow=never",
    ):
        assert setting in SAFE_CONFIG
        assert command[command.index(setting) - 1] == "-c"
    assert command[-5:] == [
        "diff",
        "--no-ext-diff",
        "--no-textconv",
        "--name-only",
        "A..B",
    ]
    assert git_command("/r", ["status"])[-1] == "status"


def test_no_git_subprocess_in_src_bypasses_the_runner() -> None:
    offenders = []
    for path in sorted(SRC.rglob("*.py")):
        if path.name == "git.py" and path.parent.name == "core":
            continue
        text = path.read_text(encoding="utf-8")
        for number, line in enumerate(text.splitlines(), 1):
            code = line.split("#", 1)[0]
            if re.search(
                r"\bimport subprocess\b|\bsubprocess\.|\bos\.(system|popen|exec)", code
            ) or re.search(r"""["']git["']\s*,""", code):
                offenders.append(f"{path.relative_to(SRC)}:{number}: {line.strip()}")
    assert offenders == []
