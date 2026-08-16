"""Make the *worktree's* ``src`` the import root for the test run.

Without this, a run that picks up an editable install pointing at another
checkout would silently test that other copy of the code. Inserted at position
0 so it wins over any ``.pth``-installed path.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
