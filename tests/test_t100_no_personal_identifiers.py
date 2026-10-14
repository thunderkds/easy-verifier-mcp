"""T100: no tracked file names the user's personal or client repositories,
or other people.

The forbidden tokens are stored reversed so this file never contains them in
plain text (a plain-text list would itself be a match). The aliases that
replaced them, and the real paths, live in ``.local/real-repos.md``, which is
git-ignored.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

# Each entry is a forbidden token written backwards; matched case-insensitively.
_REVERSED_TOKENS = (
    "ynoyrb",
    "dhctik",
    "spoved-gniparcs",
    "gniniart-ia",
    "ipa-pohs-eeffoc",
    "tahcpat",
    "ylfituaeb",
    "uuhneyugngnuh",
    "111neyugngnuh",
    "0111hngnuh",
    "neyugn.neit",
    "naoh.gnaoh",
    "iubgnouhp",
)
_FORBIDDEN = re.compile(
    "|".join(re.escape(token[::-1]) for token in _REVERSED_TOKENS), re.IGNORECASE
)


def _tracked_files() -> list[Path]:
    try:
        out = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "ls-files", "-z"],
            check=True,
            capture_output=True,
            stdin=subprocess.DEVNULL,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("not a git checkout")
    return [REPO_ROOT / name for name in out.decode().split("\0") if name]


def test_reversed_tokens_decode_to_the_ac1_list() -> None:
    # Pins the decoding itself: an empty or mangled list would pass everything.
    assert len(_REVERSED_TOKENS) == 13
    assert _FORBIDDEN.search("x" + _REVERSED_TOKENS[0][::-1].upper() + "x")
    assert not _FORBIDDEN.search("node-monorepo fullstack-ts k8s-ops python-ml")


def test_no_tracked_file_contains_a_personal_identifier() -> None:
    hits = []
    for path in _tracked_files():
        if not path.is_file():
            continue
        data = path.read_bytes()
        if b"\0" in data:  # binary, as `git grep -I` skips it
            continue
        text = data.decode("utf-8", errors="replace")
        for number, line in enumerate(text.splitlines(), start=1):
            if _FORBIDDEN.search(line):
                hits.append(f"{path.relative_to(REPO_ROOT)}:{number}")
    assert not hits, f"{len(hits)} line(s) name a personal identifier: {hits[:20]}"


def test_no_tracked_path_contains_a_personal_identifier() -> None:
    # T102: the contents scan above never matched a file *name*.
    hits = [
        str(path.relative_to(REPO_ROOT))
        for path in _tracked_files()
        if _FORBIDDEN.search(str(path.relative_to(REPO_ROOT)))
    ]
    assert not hits, f"{len(hits)} tracked path(s) name a personal identifier"
