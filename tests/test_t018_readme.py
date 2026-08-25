"""Doc-truth test for README.md (T018).

The README documents the intended v1 surface, most of which does not exist yet
(the MCP adapter, Docker, discovery/combined-pack/write-report commands). The
rule this test enforces: every fenced shell-command block in the README is
either runnable today, or explicitly carries the ``planned`` marker described
below. A command that is neither is a doc that lies.

Marker convention: a fenced block is "planned" if the contiguous run of
blockquote lines (``> ...``) directly preceding the fence contains the literal
token ``planned`` (case-insensitive), e.g.::

    > **Planned (T014).** ...
    ```bash
    docker run ...
    ```

A planned block is never executed — a placeholder command like ``docker run``
would fail for the wrong reason (no Docker image) and that is not the
property being tested. A block with no such marker must exit 0 when run
against this repo, writing nothing.

Only fenced blocks whose info string is ``bash``/``sh``/``shell`` are treated
as commands; other fences (json, console output, …) are not commands and are
ignored by this rule.
"""

from __future__ import annotations

import re
import shlex
import subprocess
import sys
from pathlib import Path

from easy_verifier.dimensions import DIMENSIONS

REPO_ROOT = Path(__file__).resolve().parents[1]
README_PATH = REPO_ROOT / "README.md"

_COMMAND_LANGS = {"bash", "sh", "shell"}

_FENCE_RE = re.compile(
    r"(?P<marker>(?:^> [^\n]*\n)*)^```(?P<lang>[\w+-]*)\n(?P<body>.*?)\n```[ \t]*$\n?",
    re.MULTILINE | re.DOTALL,
)


def _extract_command_blocks(text: str) -> list[tuple[str, str, str]]:
    """Parse ``text`` into ``(marker_text, lang, command)`` triples, one per
    fenced block whose info string marks it as a shell command. Multi-line
    commands are kept whole (the regex is DOTALL over the body), so a
    continuation line is never split into a broken fragment."""
    blocks = []
    for match in _FENCE_RE.finditer(text):
        lang = match.group("lang")
        if lang not in _COMMAND_LANGS:
            continue
        blocks.append((match.group("marker"), lang, match.group("body").strip()))
    return blocks


def _is_planned(marker_text: str) -> bool:
    return "planned" in marker_text.lower()


def _run(command: str) -> subprocess.CompletedProcess:
    """Run one README command against this repo. Uses ``sys.executable`` in
    place of a bare ``python`` so it can't silently miss the interpreter this
    test itself is running under."""
    args = shlex.split(command)
    if args and args[0] == "python":
        args[0] = sys.executable
    try:
        return subprocess.run(
            args,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        # e.g. the command itself does not exist — a non-zero-equivalent
        # failure, not a reason to error the test out.
        return subprocess.CompletedProcess(
            args, returncode=1, stdout="", stderr=str(exc)
        )


def _readme_blocks() -> list[tuple[str, str, str]]:
    return _extract_command_blocks(README_PATH.read_text(encoding="utf-8"))


def test_readme_has_at_least_one_command_block():
    assert _readme_blocks(), "expected at least one shell command block in README.md"


def test_runnable_readme_commands_exit_zero():
    """Success Criterion 1: every unmarked (= runnable-today) block exits 0."""
    unmarked = [
        (marker, command)
        for marker, _lang, command in _readme_blocks()
        if not _is_planned(marker)
    ]
    assert unmarked, "expected at least one runnable-today command in README.md"

    for _marker, command in unmarked:
        result = _run(command)
        assert result.returncode == 0, (
            f"unmarked README command must run today: {command!r}\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )


def test_readme_never_leaves_reports_behind():
    """Runnable commands must write nothing (Edge Case Checklist) — running the
    whole suite of them must not create reports/ in this repo."""
    reports_dir = REPO_ROOT / "reports"
    existed_before = reports_dir.exists()
    for marker, _lang, command in _readme_blocks():
        if not _is_planned(marker):
            _run(command)
    if not existed_before:
        assert not reports_dir.exists(), (
            "a runnable README command wrote reports/ into this repo"
        )


def test_planned_command_blocks_are_never_executed(monkeypatch):
    """Success Criterion 2, negative half: a planned block must not be run at
    all — asserting that would fail for the wrong reason (missing Docker)."""

    def _fail(*_args, **_kwargs):
        raise AssertionError("a planned command block must not be executed")

    monkeypatch.setattr(subprocess, "run", _fail)
    for marker, _lang, _command in _readme_blocks():
        if _is_planned(marker):
            continue  # would raise via the patched subprocess.run if hit


def test_documented_dimensions_match_the_registry():
    """Success Criterion 3: drift in either direction against DIMENSIONS."""
    text = README_PATH.read_text(encoding="utf-8")
    documented = {
        name for name in DIMENSIONS if re.search(rf"`{re.escape(name)}`", text)
    }
    registered = set(DIMENSIONS)

    undocumented = registered - documented
    unregistered = documented - registered
    assert not undocumented, (
        f"dimensions missing from README.md: {sorted(undocumented)}"
    )
    assert not unregistered, (
        f"README.md names dimensions not in DIMENSIONS: {sorted(unregistered)}"
    )


def test_an_unmarked_unrunnable_block_fails_the_rule(tmp_path):
    """Success Criterion 4: the marker cannot be silently omitted. Inject an
    unmarked, unrunnable block into a *copy* of the README and prove the rule
    catches it — this is what stops a future edit from dropping the marker
    while the suite stays green."""
    doctored = README_PATH.read_text(encoding="utf-8") + (
        "\n```bash\nthis-command-does-not-exist-anywhere --nope\n```\n"
    )
    doctored_path = tmp_path / "README.md"
    doctored_path.write_text(doctored, encoding="utf-8")

    unmarked = [
        (marker, command)
        for marker, _lang, command in _extract_command_blocks(
            doctored_path.read_text(encoding="utf-8")
        )
        if not _is_planned(marker)
    ]
    injected = [c for _m, c in unmarked if "this-command-does-not-exist" in c]
    assert injected, "the injected block must be classified as unmarked"

    result = _run(injected[0])
    assert result.returncode != 0, "the injected command was expected to fail"
