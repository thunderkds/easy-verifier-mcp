"""Data carried across the pipeline.

Everything here is plain data. There is deliberately no ``Dimension`` base class
and no registry: a dimension is a :class:`DimensionDescriptor` value plus a
``collect`` callable, and every cross-cutting rule lives in
:func:`easy_verifier.core.pipeline.run_dimension` where a dimension cannot reach
it (Option D, see ``BRAINSTORMING_LOG.md``).

Nothing in this module carries a verdict, score, grade, severity or pass/fail
about the code being evaluated (FR-013). The only number here is
``coverage_score``, which describes *this engine's own* checklist completeness,
not the quality of the target repository.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class Excerpt:
    """A single citable unit of evidence.

    ``start_line`` and ``end_line`` are **1-indexed and inclusive**, matching
    what an editor shows on screen. An off-by-one here poisons every citation
    downstream, so it is asserted directly in the test suite.
    """

    path: str
    """Repository-relative POSIX path. Never absolute — absolute paths would
    leak container-internal locations into reports (FR-021c)."""

    start_line: int
    end_line: int
    text: str


@dataclass(frozen=True)
class SourceMiss:
    """A declared source that could not be turned into evidence, and why.

    The reason is attached to the source rather than held in a parallel
    structure, so the two cannot drift apart. Callers that want the plain named
    miss list required by FR-016a read the ``source`` field.
    """

    source: str
    reason: str


class DimensionContext(Protocol):
    """What ``collect`` is handed. Structural, so it needs no import cycle.

    The concrete implementation is
    :class:`easy_verifier.core.context.RepoContext`. A dimension reads files
    *only* through ``read_source`` — that is what keeps symlink escape, invalid
    UTF-8, permission errors and found/missing bookkeeping out of dimension code
    and inside the core, where they are enforced once.
    """

    repo_path: object
    mode: str
    scope: str

    def read_source(self, relative_path: str) -> str | None: ...


@dataclass(frozen=True)
class DimensionDescriptor:
    """The entire contract a dimension implements. Static data + one callable."""

    name: str
    purpose: str
    sources_sought: tuple[str, ...]
    collect: Callable[[DimensionContext], Iterable[Excerpt]]
    """Returns an ``Iterable[Excerpt]``, consumed lazily by the pipeline.

    Non-negotiable (``PROJECT_SPEC.md`` Critical Constraint 3): returning a
    ``list`` forces full materialisation on exactly the monorepo size that most
    needs budgeting.
    """


@dataclass(frozen=True)
class EvidencePack:
    """The structured result of one dimension. Evidence only, never a verdict."""

    dimension: str
    mode: str
    scope: str
    files_read: tuple[str, ...]
    excerpts: tuple[Excerpt, ...]
    sources_sought: tuple[str, ...]
    sources_found: tuple[str, ...]
    sources_missing: tuple[SourceMiss, ...]
    coverage_score: float | None
    """Unweighted ``len(sources_found) / len(sources_sought)`` (FR-016).

    ``None`` — not ``0.0`` — when nothing was sought, because ``0.0`` would read
    as total failure. Never rendered without ``sources_missing`` (FR-016a).
    """

    truncated: bool
    """True only if an excerpt was pulled from ``collect`` and rejected because
    it did not fit the byte budget."""

    omitted_count: int = field(default=0)
    """Excerpts pulled and rejected by the byte budget.

    This is a **lower bound**, not a total. The pipeline stops pulling at the
    first rejection and never drains the remainder to produce an exact count:
    for a file-reading ``collect``, "just counting" means reading every file,
    which is the exact cost budgeting exists to avoid (AC #5a).
    """
