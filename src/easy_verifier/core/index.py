"""One repository code index per run (T113, FR-085).

Every code file (a registry source or test file) of the resolved scope is read
**once** and shared by every dimension of the call: ``RepoContext.read_source``
serves an indexed path from here instead of opening it again, and the code
metrics that describe a whole set are computed over the index, never over the
byte-budgeted excerpts (``dimensions/_code_extract.record_index_metrics``).

The file list is the scope's own (``core.scope``'s walk: containment,
``.gitignore`` and third-party exclusion); each file is read through
``RepoContext.peek_source``, so the refusals are exactly ``read_source``'s
(secret-bearing, outside the repository, unreadable, not UTF-8). Caps are
deterministic -- no wall clock, so a replay stays byte-equal -- and applied in
``core.batches`` order (purpose class, git churn, path): files over
:data:`MAX_INDEX_FILE_BYTES` are skipped, and the index stops at the first file
that would pass :data:`MAX_INDEX_FILES` or :data:`MAX_INDEX_BYTES`. Anything
not indexed is disclosed as ``capped: {dimension: "index", role: "code"}``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import batches
from .context import MODE_STANDALONE, RepoContext
from .metric_tables import curated_metric_tables
from .metrics import code_kind
from .models import CapHit

MAX_INDEX_FILES = 5000
MAX_INDEX_BYTES = 50_000_000
MAX_INDEX_FILE_BYTES = 1_000_000


@dataclass(frozen=True)
class CodeIndex:
    """The texts of the indexed code files, in batches order."""

    texts: dict[str, str]
    matched: int
    """Code files in the scope (before any cap or refusal)."""

    @property
    def read(self) -> int:
        return len(self.texts)

    @property
    def cap(self) -> CapHit | None:
        """The disclosure when fewer files were indexed than matched."""
        if self.read >= self.matched:
            return None
        return CapHit("code", self.matched, self.read)


def build_index(repo: str | Path, files) -> CodeIndex:
    """Index the code files among ``files`` (repository-relative paths)."""
    context = RepoContext(Path(repo).resolve(), MODE_STANDALONE, "project")
    tables = curated_metric_tables()
    candidates = sorted({path for path in files if code_kind(path, tables)})
    ordered = (
        batches.plan(context.repo_path, candidates, MAX_INDEX_FILES, 1).ordered
        if candidates
        else ()
    )
    texts: dict[str, str] = {}
    total = 0
    for path in ordered:
        try:
            size = (context.repo_path / path).stat().st_size
        except OSError:
            continue
        if size > MAX_INDEX_FILE_BYTES:
            continue
        if len(texts) >= MAX_INDEX_FILES or total + size > MAX_INDEX_BYTES:
            break
        text = context.peek_source(path)
        if text is None:
            continue
        texts[path] = text
        total += size
    return CodeIndex(texts=texts, matched=len(candidates))


class IndexCache:
    """Builds the index once per distinct file set, for one call (``score``)."""

    def __init__(self) -> None:
        self._built: dict[tuple[str, ...], CodeIndex] = {}

    def get(self, repo: str | Path, files) -> CodeIndex:
        key = tuple(files)
        if key not in self._built:
            self._built[key] = build_index(repo, key)
        return self._built[key]

    @property
    def cap(self) -> CapHit | None:
        return next(
            (item.cap for item in self._built.values() if item.cap is not None), None
        )
