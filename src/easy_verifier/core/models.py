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

    @property
    def ref(self) -> str:
        """The one canonical, stable evidence-reference string a finding can
        cite (T006): ``path:start_line-end_line``, 1-indexed and inclusive,
        matching this excerpt's own fields. Other shapes — a lone line number,
        a bespoke pack item ID — are not this identifier and must be rejected
        by a citation-resolving caller."""
        return f"{self.path}:{self.start_line}-{self.end_line}"


@dataclass(frozen=True)
class SourceMiss:
    """A declared source that could not be turned into evidence, and why.

    The reason is attached to the source rather than held in a parallel
    structure, so the two cannot drift apart. Callers that want the plain named
    miss list required by FR-016a read the ``source`` field.
    """

    source: str
    reason: str


@dataclass(frozen=True)
class TruncationRecord:
    """The structured truncation report FR-011b requires: whether the byte
    budget rejected anything, and how many excerpts it rejected.

    Mirrors :class:`EvidencePack`'s own ``truncated``/``omitted_count`` fields
    — kept separately here, rather than replacing them, because sixteen other
    tasks are already tested against those two flat fields (T001's contract).
    ``EvidencePack.truncation`` is the structured form the same computation
    also produces, for a caller that wants one field to check.
    """

    truncated: bool
    omitted_count: int = field(default=0)
    """A lower bound, never a total (:mod:`easy_verifier.core.budget`)."""


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
    resolved_scope: object | None

    def read_source(self, relative_path: str) -> str | None: ...

    def request_secret_source(self, relative_path: str) -> str | None: ...


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
class ApprovalRequest:
    """A safe per-file request for operator consent to read excluded bytes.

    Carries only a repository-relative path and fixed reason; never file
    contents, callback details, a verdict, or an inferred risk level.
    """

    path: str
    reason: str


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

    warnings: tuple[str, ...] = field(default=())
    """Context-level caveats every response and report must surface (FR-004).

    Copied verbatim from the ``RepoContext`` by ``run_dimension``, so a pack
    built in standalone mode always carries the limited-context warning: the
    pack is the only way evidence leaves the engine, and no adapter has to
    remember to add it.
    """

    redactions: tuple[RedactionHit, ...] = field(default=())
    """Every secret replaced while building this pack (T004, NFR-010).

    Location and detector only — never the raw value.
    """

    had_redactions: bool = field(default=False)
    """True if anything was redacted, so T013 can render the NFR-011 advisory.

    Not derived from ``redactions`` being non-empty at render time: redaction
    also happens on excerpts the byte budget *rejected*, which never appear on
    the pack, and the advisory must still fire for those.
    """

    truncation: TruncationRecord | None = field(default=None)
    """The structured form of ``truncated``/``omitted_count`` (T005,
    FR-011b). ``None`` only when a pack was built by a caller that predates
    T005 and never went through :func:`easy_verifier.core.budget.budget`;
    every pack ``run_dimension`` builds sets this."""

    approval_requests: tuple[ApprovalRequest, ...] = field(default=())
    """Per-file operator approvals requested by the security dimension.

    Empty for existing callers and every other dimension.
    """


@dataclass(frozen=True)
class RedactionHit:
    """One secret replaced by a fingerprint. Carries no raw value, ever.

    There is deliberately no ``value`` field: keeping the raw material "just in
    case" is how it reaches a serializer later. ``detector``, ``path`` and
    ``line`` are what keep the finding actionable (NFR-010) — a reader can go
    look. Nothing here is a severity, score or verdict (FR-013).
    """

    detector: str
    fingerprint: str
    offset: int
    """Character offset into the *original* text the redaction was found in."""

    line: int
    """1-indexed line within that text, matching :class:`Excerpt`'s convention."""

    path: str | None = field(default=None)
    """Repository-relative path, when the text came from a file."""


@dataclass(frozen=True)
class RedactionResult:
    """What :func:`easy_verifier.core.redact.scan` returns: safe text + hits."""

    text: str
    hits: tuple[RedactionHit, ...]


# ---------------------------------------------------------------------------
# T012/T013 seam (DDR-0004, Supervisor-locked).
#
# These three types are T012's output and T013's input. T012 owns them and
# builds them in `core.synthesis`; T013 only reads them in `core.report`. They
# were locked by the Supervisor before either task started because the two were
# built in parallel, in separate worktrees, and neither branch's tests could
# have caught a mismatch. Both branches defined them independently and the
# definitions came out field-identical, so merging them was a de-duplication
# rather than a reconciliation of two designs. Change them in step, or not at
# all.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DimensionSlot:
    """One requested dimension's outcome inside a :class:`CombinedPack`.

    ``pack`` is ``None`` iff ``error`` is set — a dimension that fails does not
    abort the whole combined call (FR-025 robustness); its slot simply carries
    a structured failure instead of a pack, and the other slots are unaffected.
    """

    dimension: str
    pack: EvidencePack | None
    error: str | None


@dataclass(frozen=True)
class CoverageSummary:
    """Aggregation only — no interpretation of what the numbers mean together
    (FR-026). Deciding what several dimensions' coverage implies together is
    the calling agent's job, not this engine's.
    """

    per_dimension: tuple[tuple[str, float | None], ...]
    """Deterministic order, mirroring :attr:`CombinedPack.slots`."""

    combined: float | None
    """``None`` — never ``0.0`` — when nothing was sought anywhere, mirroring
    :attr:`EvidencePack.coverage_score`'s convention."""

    method: str
    """States exactly how ``combined`` was derived (FR-025), e.g. a pooled
    found/sought ratio across every dimension that sought anything."""

    misses: tuple[tuple[str, tuple[SourceMiss, ...]], ...]
    """The union of miss lists, named per dimension (FR-016a). Lives inside
    ``CoverageSummary`` — not beside it — so a renderer cannot reach a score
    without also having its miss list."""


@dataclass(frozen=True)
class CombinedPack:
    """The result of :func:`easy_verifier.core.synthesis.combined_pack`."""

    slots: tuple[DimensionSlot, ...]
    """Deterministic order regardless of the order dimensions were requested
    in."""

    coverage: CoverageSummary
    budget_model: str
    """Literal ``"per-dimension"``: each dimension in a combined call gets the
    full byte budget independently (user decision, 2026-08-25). A future
    total-budget regime is therefore a value change here, not a schema
    change."""


@dataclass(frozen=True)
class ReportResult:
    """What :func:`easy_verifier.core.report.write_report` returns.

    Validation failures are *not* reported here: they raise
    :class:`easy_verifier.core.findings.ValidationError` before any file is
    opened, so a ``ReportResult`` existing at all means a report was written.
    """

    path: str
    """Repository-relative POSIX path of the written report, e.g.
    ``reports/evidence-report-project-20260825T095341-123456Z.html``.
    Relative on purpose: an absolute path here is the container-internal leak
    FR-021c forbids, and the caller already knows the target repo."""

    absolute_path: str
    """The resolved path on the machine that ran the write. Returned to the
    caller (who is on that machine) but never rendered into the document."""

    advisory: str | None
    """The NFR-011 sensitivity advisory, set only on the **first** report
    written into this target's ``reports/``. ``None`` on later writes; the
    advisory itself is rendered in every report regardless."""
