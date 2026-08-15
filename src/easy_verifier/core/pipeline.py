"""The pipeline choke point.

``run_dimension`` owns redaction, budgeting, truncation reporting and coverage
arithmetic. A dimension supplies only ``sources_sought`` data and a ``collect``
callable, so it never gets the chance to bypass any of those (Option D).

Every later dimension is written against this function's contract. Changing the
contract is a broad, cross-cutting rewrite — treat it accordingly.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from . import redact as redact_module
from .context import RepoContext, detect_mode
from .models import DimensionDescriptor, EvidencePack, Excerpt, SourceMiss

DEFAULT_BUDGET_BYTES = 120_000

DEFAULT_SCOPE = "project"
"""T003 owns real scope selection (task | changes | worktree | project)."""


class RepoPathError(ValueError):
    """The target repository path is unusable. Reported as a clear message, not
    a traceback."""


def run_dimension(
    descriptor: DimensionDescriptor,
    repo_path: str | Path,
    scope: str = DEFAULT_SCOPE,
    budget_bytes: int = DEFAULT_BUDGET_BYTES,
) -> EvidencePack:
    """Run one dimension against a repository and return its evidence pack.

    Works on any directory; git is not required for ``project`` scope (only
    ``changes`` will need it, in T003).
    """
    repo = Path(repo_path).expanduser()
    if not repo.exists():
        raise RepoPathError(f"target repository path does not exist: {repo}")
    if not repo.is_dir():
        raise RepoPathError(f"target repository path is not a directory: {repo}")
    repo = repo.resolve()

    context = RepoContext(repo_path=repo, mode=detect_mode(repo), scope=scope)

    kept, truncated, omitted_count = _budget(
        descriptor.collect(context), budget_bytes=budget_bytes
    )

    sought = tuple(descriptor.sources_sought)
    # Clamped to the declared checklist. `context.sources_found` is the raw read
    # record and may include files the dimension read without declaring; counting
    # those would let a dimension inflate its own coverage above 1.0, which FR-016
    # does not admit. The undeclared reads stay visible in `files_read`, because
    # they genuinely were read.
    found = tuple(source for source in sought if source in context.sources_found)
    missing = _missing_sources(sought, found, context.sources_missing, truncated)
    coverage_score = (len(found) / len(sought)) if sought else None

    return EvidencePack(
        dimension=descriptor.name,
        mode=context.mode,
        scope=context.scope,
        files_read=tuple(context.files_read),
        excerpts=tuple(kept),
        sources_sought=sought,
        sources_found=found,
        sources_missing=missing,
        coverage_score=coverage_score,
        truncated=truncated,
        omitted_count=omitted_count,
    )


def _missing_sources(
    sought: tuple[str, ...],
    found: tuple[str, ...],
    attempted_misses: list[SourceMiss],
    truncated: bool,
) -> tuple[SourceMiss, ...]:
    """Every declared source that produced no evidence, with a stated reason.

    Together with ``found`` this partitions ``sources_sought`` exactly, which is
    what makes the miss list auditable (FR-016a). Two things have to be handled
    for that to hold:

    * a miss recorded for an *undeclared* path is dropped — it is not part of
      this dimension's checklist;
    * a declared source the dimension never even attempted still has to be
      accounted for. Lazy consumption makes this ordinary rather than
      exceptional: when the byte budget stops the pull, later sources are never
      probed. Reporting them as absent would be a claim the engine did not
      check, so they are reported as *not examined*.
    """
    reasons = {
        miss.source: miss.reason for miss in attempted_misses if miss.source in sought
    }
    unexamined = (
        "not examined: the byte budget was reached before this source was read"
        if truncated
        else "not examined by this dimension"
    )
    return tuple(
        SourceMiss(source=source, reason=reasons.get(source, unexamined))
        for source in sought
        if source not in found
    )


def _budget(raw_excerpts, budget_bytes: int) -> tuple[list[Excerpt], bool, int]:
    """Consume ``raw_excerpts`` lazily, redacting and byte-capping as it goes.

    Stops at the **first excerpt that does not fit**: that excerpt is pulled,
    redacted, rejected, counted, and iteration ends. The remainder is never
    drained (AC #5a) — ``omitted_count`` is therefore a lower bound.

    Setting ``truncated`` from an actual rejection, rather than from
    ``used >= budget_bytes``, is what makes it honest: a stream that ends exactly
    at the budget boundary reports ``truncated=False``, because nothing was ever
    rejected.

    T005 replaces this naive cap with real relevance ordering; the contract it
    must preserve is the laziness and the lower-bound semantics.
    """
    kept: list[Excerpt] = []
    used = 0

    for raw in raw_excerpts:
        # Redaction happens here, at the evidence layer, before an excerpt can
        # reach a pack, a report, a log or an error message (NFR-010). It runs
        # on the rejected excerpt too — a rejected excerpt is still an excerpt
        # this process has held in memory.
        safe = replace(raw, text=redact_module.redact(raw.text))
        size = len(safe.text.encode("utf-8"))

        if used + size > budget_bytes:
            return kept, True, 1

        kept.append(safe)
        used += size

    return kept, False, 0
