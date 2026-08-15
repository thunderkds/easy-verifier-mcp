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
from .models import DimensionDescriptor, EvidencePack, Excerpt

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
    found = tuple(context.sources_found)
    coverage_score = (len(found) / len(sought)) if sought else None

    return EvidencePack(
        dimension=descriptor.name,
        mode=context.mode,
        scope=context.scope,
        files_read=tuple(context.files_read),
        excerpts=tuple(kept),
        sources_sought=sought,
        sources_found=found,
        sources_missing=tuple(context.sources_missing),
        coverage_score=coverage_score,
        truncated=truncated,
        omitted_count=omitted_count,
    )


def _budget(
    raw_excerpts, budget_bytes: int
) -> tuple[list[Excerpt], bool, int]:
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
