"""Make the *worktree's* ``src`` the import root for the test run.

Without this, a run that picks up an editable install pointing at another
checkout would silently test that other copy of the code. Inserted at position
0 so it wins over any ``.pth``-installed path.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import os  # noqa: E402
import tempfile  # noqa: E402

import pytest  # noqa: E402

# Never read or write the real ~/.easy-verifier-sot/ (T036): every test, and
# every CLI/MCP subprocess it spawns, gets an empty local registry layer.
os.environ["EASY_VERIFIER_SOT"] = os.path.join(
    tempfile.mkdtemp(prefix="ev-sot-"), "sot"
)


@pytest.fixture(autouse=True)
def _empty_local_registry(tmp_path, monkeypatch):
    from easy_verifier.core.roles import _registry

    monkeypatch.setenv("EASY_VERIFIER_SOT", str(tmp_path / "ev-sot"))
    _registry.cache_clear()
    yield
    _registry.cache_clear()
