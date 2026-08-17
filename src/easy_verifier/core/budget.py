"""Relevance-ordered, lazy, explicitly-truncated evidence budgeting (T005,
FR-011a, FR-011b).

:func:`budget` replaces the naive "stop at the first excerpt that does not
fit" cap ``pipeline.py`` shipped with T001. The cap itself — stop at the first
rejection, never drain the remainder, report a lower-bound ``omitted_count`` —
is the contract this module must preserve; what changes is *which* excerpt is
offered the last slot when the budget is nearly full.

The design tension is real: perfect relevance ordering wants the whole
candidate set in hand to sort it, while laziness forbids exactly that. This is
resolved by tiering rather than sorting: each excerpt's tier (changed file /
spec-referenced file / everything else) is knowable from its ``path`` alone,
cheaply, the moment it is pulled — no need to see the rest of the stream. The
working set kept in memory is bounded by ``limit_bytes`` (how much material
can ever be admitted), never by the length of the candidate stream.

Ordering only has to be *decided* once real contention shows up: when an
excerpt arrives that does not fit as pulled. At that single point, one
already-admitted excerpt from a strictly lower-priority tier may be evicted to
make room — never more than one, and never a general sort. Either way, that
excerpt is the last one pulled: the stream is never drained further, matching
the laziness contract exactly.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, replace

from . import redact as redact_module
from .context import KIT_ARTIFACTS
from .models import Excerpt, RedactionHit, TruncationRecord

DEFAULT_BUDGET_BYTES = 120_000
"""Default per-dimension byte ceiling (FR-011a), overridable per call."""

_KIT_FILES = frozenset(
    artifact
    for artifact in KIT_ARTIFACTS
    if not artifact.endswith("/") and "*" not in artifact
)
_KIT_DIR_PREFIXES = tuple(
    artifact for artifact in KIT_ARTIFACTS if artifact.endswith("/")
)
"""Reuses ``context.KIT_ARTIFACTS`` rather than a second list, so "spec/kit
artifact" means the same thing here as it does during kit detection."""

_TIER_CHANGED = 1
_TIER_REFERENCED = 2
_TIER_OTHER = 3

__all__ = ["DEFAULT_BUDGET_BYTES", "BudgetError", "BudgetResult", "budget"]


class BudgetError(ValueError):
    """``limit_bytes`` was not a usable positive number of bytes."""


@dataclass(frozen=True)
class BudgetResult:
    """What :func:`budget` returns: the admitted excerpts plus the record."""

    excerpts: tuple[Excerpt, ...]
    truncation: TruncationRecord
    redactions: tuple[RedactionHit, ...]
    """Every secret replaced while preparing an excerpt — including one that
    was pulled and then rejected or evicted (T004, NFR-011): a secret that
    only ever appeared in material that did not make the final pack still
    happened."""


def budget(
    excerpts: Iterable[Excerpt],
    scope,
    limit_bytes: int = DEFAULT_BUDGET_BYTES,
) -> BudgetResult:
    """Consume ``excerpts`` lazily and admit them in relevance order.

    ``scope`` supplies the tiering data — ``scope.changed_files`` for tier 1,
    ``scope.task_ref.guide_path`` (when present) for tier 2 — and may be
    ``None`` when no scope has been resolved for this call, in which case
    every excerpt not matching a known kit artifact falls into tier 3 and the
    result is ordered by arrival, same as before this task.

    Byte accounting is ``len(text.encode("utf-8"))`` on the *redacted* text,
    with no additional per-excerpt overhead constant: T001 fixed the naive cap
    to this same formula and sixteen later tasks are tested against its exact
    thresholds, so the accounting stays byte-exact (a zero, not merely
    "documented", tolerance) rather than introducing a constant that would
    silently move every existing budget boundary (AC #8).
    """
    if limit_bytes <= 0:
        raise BudgetError(
            f"limit_bytes must be a positive number of bytes, got {limit_bytes!r}"
        )

    changed = frozenset(getattr(scope, "changed_files", None) or ())
    referenced = _referenced_files(scope)

    # (tier, arrival index, excerpt) — arrival index breaks ties within a tier
    # so the final sort is stable, matching AC #2 ("deterministic within each
    # tier"). The list is bounded by how many excerpts fit in `limit_bytes`,
    # not by how many were offered.
    kept: list[tuple[int, int, Excerpt]] = []
    seen_refs: set[str] = set()
    hits: list[RedactionHit] = []
    used = 0
    arrival = 0
    truncated = False
    omitted_count = 0

    for raw in excerpts:
        safe, item_hits, size = _prepare(raw)
        hits.extend(item_hits)

        if safe.ref in seen_refs:
            # Same file, same line range: admitted once. Checked before sizing
            # so a duplicate never counts against the budget or as an omission
            # (Edge Case Checklist).
            continue
        seen_refs.add(safe.ref)

        tier = _tier(safe.path, changed, referenced)

        if used + size <= limit_bytes:
            kept.append((tier, arrival, safe))
            used += size
            arrival += 1
            continue

        # The first excerpt that does not fit as pulled ends the run — the
        # stream is never drained further, whether or not eviction below
        # succeeds. Truncation is triggered by this rejection, never by
        # ``used >= limit_bytes`` on its own, so a stream that ends exactly at
        # the boundary never reaches this branch (AC #4).
        evicted = _evict_for(kept, tier, size, used, limit_bytes)
        if evicted is not None:
            kept, used = evicted
            kept.append((tier, arrival, safe))
            arrival += 1
        omitted_count = 1
        truncated = True
        break

    kept.sort(key=lambda item: (item[0], item[1]))
    ordered = tuple(item[2] for item in kept)

    record = TruncationRecord(truncated=truncated, omitted_count=omitted_count)
    return BudgetResult(excerpts=ordered, truncation=record, redactions=tuple(hits))


def _referenced_files(scope) -> frozenset[str]:
    """Tier-2 paths: files referenced by the loaded spec/kit artifacts.

    ``scope.task_ref.guide_path`` is the one per-call addition — the guide a
    ``task`` scope resolved to. The fixed kit-artifact filenames
    (``PROJECT_SPEC.md`` etc.) are tier 2 unconditionally, via ``_tier``.
    """
    task_ref = getattr(scope, "task_ref", None)
    if task_ref is None:
        return frozenset()
    return frozenset({task_ref.guide_path})


def _tier(path: str, changed: frozenset[str], referenced: frozenset[str]) -> int:
    """A path's relevance tier (FR-011a). A path in both tier 1 and tier 2 is
    tier 1 — checked first, so it is admitted once, at the higher tier."""
    if path in changed:
        return _TIER_CHANGED
    if path in referenced or path in _KIT_FILES or path.startswith(_KIT_DIR_PREFIXES):
        return _TIER_REFERENCED
    return _TIER_OTHER


def _prepare(raw: Excerpt) -> tuple[Excerpt, list[RedactionHit], int]:
    """Redact ``raw`` and return the safe excerpt, its hits, and its byte size.

    Redaction happens here, before an excerpt can be sized, ranked or
    admitted — the same evidence-layer discipline ``pipeline.py`` used to
    apply inline (NFR-010).
    """
    path_result = redact_module.scan(raw.path)
    text_result = redact_module.scan(raw.text)
    # The text that lands on the pack comes from `redact` — the seam T001
    # fixed and that every dimension is written against — while `scan` above
    # supplies the hit metadata. They are the same computation (`redact` is
    # defined as `scan(text).text`), so this costs a little CPU inside an
    # already byte-bounded excerpt and keeps the seam function the single
    # thing governing pack content, as `pipeline.py`'s equivalent code did.
    safe = replace(raw, path=path_result.text, text=redact_module.redact(raw.text))

    hits = [replace(hit, path=safe.path) for hit in path_result.hits]
    hits.extend(
        replace(hit, path=safe.path, line=raw.start_line + hit.line - 1)
        for hit in text_result.hits
    )
    size = len(safe.text.encode("utf-8"))
    return safe, hits, size


def _evict_for(
    kept: list[tuple[int, int, Excerpt]],
    tier: int,
    size: int,
    used: int,
    limit_bytes: int,
) -> tuple[list[tuple[int, int, Excerpt]], int] | None:
    """Try to make room for a tier-``tier`` excerpt of ``size`` bytes by
    evicting the single worst already-admitted excerpt strictly outranked by
    it. Returns ``None`` when no eviction can help — no candidate, or freeing
    one victim still is not enough (evicting more than one victim is not
    attempted; that would turn a bounded, single decision into a search).
    """
    candidates = [
        index for index, (kept_tier, _, _) in enumerate(kept) if kept_tier > tier
    ]
    if not candidates:
        return None

    victim_index = max(candidates, key=lambda index: (kept[index][0], kept[index][1]))
    victim_size = len(kept[victim_index][2].text.encode("utf-8"))
    freed_used = used - victim_size
    if freed_used + size > limit_bytes:
        return None

    remaining = kept[:victim_index] + kept[victim_index + 1 :]
    return remaining, freed_used
