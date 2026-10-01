"""The one way this engine runs git against a target repository (T051, NFR-007).

A target repository is untrusted input, and so is its ``.git/config``: a copied
checkout, a tarball or a shared volume can carry one that names a program for
git to run — ``core.fsmonitor``, a ``diff.external`` or ``diff.<driver>.textconv``
command, a ``post-index-change`` hook, a pager. Plain ``git status`` against such
a repository executes that program. Every git subprocess in ``src/`` goes through
:func:`run_git`, and a test asserts no other module spawns git.

The runner only ever *adds* neutralising options; it never changes which
subcommand runs or its arguments, so parsed output is unchanged for an ordinary
repository:

* ``-c`` overrides for every repo-config key we know to execute something on a
  read-only command (:data:`SAFE_CONFIG`);
* ``--no-ext-diff --no-textconv`` on ``diff``/``log``/``show``;
* an explicit environment: ``GIT_CONFIG_NOSYSTEM`` (no system config),
  ``GIT_TERMINAL_PROMPT=0`` (never prompt), ``GIT_OPTIONAL_LOCKS=0`` (``status``
  does not rewrite the index, so no index hook can fire), and no ``HOME`` — so
  the operator's global ``~/.gitconfig`` is not read either (a
  ``safe.directory`` set there no longer applies);
* no shell, stdin closed, and a timeout — a hung git is a failed git.

Residual risk, stated plainly: this is a deny-list of the execution paths git
offers on the subcommands we run (``status``, ``diff``, ``log``, ``rev-parse``,
``ls-files``). A clean/smudge ``filter.<driver>`` is named by an arbitrary
driver, so it cannot be overridden by a fixed ``-c``; see
:func:`_filter_overrides` for how those are neutralised.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

GIT_TIMEOUT_SECONDS = 120

SAFE_CONFIG: tuple[str, ...] = (
    "core.fsmonitor=false",
    "core.hooksPath=/dev/null",
    "diff.external=",
    "core.pager=cat",
    "protocol.allow=never",
)

_DIFF_LIKE = frozenset({"diff", "log", "show"})

_SAFE_ENV = {
    # An explicit environment, not a copy of ours: the package never reads
    # the process environment (T001), and git needs nothing from it. ``PATH`` is the
    # platform default because the binary is already resolved absolutely.
    "PATH": os.defpath,
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_TERMINAL_PROMPT": "0",
    "GIT_OPTIONAL_LOCKS": "0",
}


def git_command(
    repo: Path | str, args: list[str], *, extra: tuple[str, ...] = ()
) -> list[str]:
    """The full argument vector :func:`run_git` executes (exposed for tests)."""
    command = [shutil.which("git") or "git"]
    for setting in (*SAFE_CONFIG, *extra):
        command += ["-c", setting]
    command += ["-C", str(repo)]
    if args and args[0] in _DIFF_LIKE:
        return [*command, args[0], "--no-ext-diff", "--no-textconv", *args[1:]]
    return [*command, *args]


def run_git(repo: Path | str, args: list[str]) -> tuple[bool, bytes, str]:
    """Run one read-only git subcommand; ``(ok, stdout bytes, stderr text)``.

    Never raises for "git is not there / failed / hung": that is ``ok=False``
    with a reason, which every caller already treats as a structured absence.
    """
    try:
        result = subprocess.run(
            git_command(repo, args, extra=_filter_overrides(repo)),
            capture_output=True,
            stdin=subprocess.DEVNULL,
            env=_SAFE_ENV,
            timeout=GIT_TIMEOUT_SECONDS,
            check=False,
        )
    except FileNotFoundError:
        return False, b"", "git binary not found on PATH"
    except subprocess.TimeoutExpired:
        return False, b"", f"git timed out after {GIT_TIMEOUT_SECONDS}s"
    except OSError as exc:
        return False, b"", f"git could not be run: {exc.strerror or 'OS error'}"
    stderr = result.stderr.decode("utf-8", "replace").strip()
    return result.returncode == 0, result.stdout, stderr


def run_git_text(repo: Path | str, args: list[str]) -> tuple[bool, str, str]:
    """:func:`run_git` with stdout decoded as text, as ``text=True`` did."""
    ok, stdout, stderr = run_git(repo, args)
    return ok, stdout.decode("utf-8", "replace"), stderr


def _filter_overrides(repo: Path | str) -> tuple[str, ...]:
    """``-c`` settings that disarm every ``filter.<driver>`` the repo configures.

    A clean filter runs whenever git hashes worktree content — ``status`` does
    that for any file whose stat data changed. Driver names are arbitrary, so
    they are read first with ``git config --get-regexp`` (reading config
    executes nothing) and each one's commands are blanked; an empty command is
    treated by git as "no filter", and ``required=false`` stops git from
    failing on it.
    """
    try:
        result = subprocess.run(
            git_command(
                repo, ["config", "--null", "--name-only", "--get-regexp", r"^filter\."]
            ),
            capture_output=True,
            stdin=subprocess.DEVNULL,
            env=_SAFE_ENV,
            timeout=GIT_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ()
    drivers = {
        name.decode("utf-8", "surrogateescape")[len("filter.") :].rpartition(".")[0]
        for name in result.stdout.split(b"\0")
        if name.startswith(b"filter.")
    }
    return tuple(
        f"filter.{driver}.{key}={value}"
        for driver in sorted(drivers)
        for key, value in (
            ("clean", ""),
            ("smudge", ""),
            ("process", ""),
            ("required", "false"),
        )
    )
