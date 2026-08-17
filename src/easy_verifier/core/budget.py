"""Relevance-ordered, lazy, explicitly-truncated evidence budgeting (T005,
FR-011a, FR-011b).

:func:`budget` replaces the naive "stop at the first excerpt that does not
fit" cap ``pipeline.py`` shipped with T001. The cap itself — stop at the first
rejection, never drain the remainder, report a lower-bound ``omitted_count`` —
is the contract this module must preserve; what changes is *which* excerpts
are offered a slot when the budget is tight.

Perfect relevance ordering wants the whole candidate set in hand to sort it,
while laziness forbids exactly that. This is resolved by **tiering rather
than sorting**: each excerpt's tier (changed file / spec-referenced file /
everything else) is knowable from its ``path`` alone, before any excerpt is
produced, because tier 1 and tier 2 membership come entirely from ``scope``
(``scope.changed_files`` and ``scope.task_ref.guide_path``), never from the
stream itself. ``collect`` is therefore invoked **once per non-empty tier**
(never more than three times), each pass admitting only that tier's excerpts
and stopping the instant one does not fit — which stops every later pass too,
since nothing lower-priority is worth pulling once the budget is spent. A
tier whose membership set is empty (no ``scope``, or a scope naming neither
changed files nor a task guide) is skipped without ever calling ``collect``
for it — this is what keeps a caller with no scope information down to the
single pass this pipeline always ran before T005.

A pass whose tier is non-empty but never hits a misfit has no way to know a
later item of its tier will not show up except by reaching the end of the
stream, so such a pass does drain fully — this is the accepted cost of true
tier priority under lazy, single-direction consumption (a documented
trade-off, not a bug): the generator is still never advanced past the point
that decides that pass's outcome.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, replace

from . import redact as redact_module
from .models import Excerpt, RedactionHit, TruncationRecord

DEFAULT_BUDGET_BYTES = 120_000
"""Default per-dimension byte ceiling (FR-011a), overridable per call."""

_TIER_CHANGED = 1
_TIER_REFERENCED = 2
_TIER_OTHER = 3
_TIERS_IN_PRIORITY_ORDER = (_TIER_CHANGED, _TIER_REFERENCED, _TIER_OTHER)

__all__ = ["DEFAULT_BUDGET_BYTES", "BudgetError", "BudgetResult", "budget"]


class BudgetError(ValueError):
    """``limit_bytes`` was not a usable positive number of bytes."""


@dataclass(frozen=True)
class BudgetResult:
    """What :func:`budget` returns: the admitted excerpts plus the record."""

    excerpts: tuple[Excerpt, ...]
    truncation: TruncationRecord
    redactions: tuple[RedactionHit, ...]
    """Every secret replaced while inspecting an excerpt — including one that
    was pulled and then rejected (T004, NFR-011): a secret that only ever
    appeared in material that did not make the final pack still happened."""


def budget(
    collect: Callable[[], Iterable[Excerpt]],
    scope,
    limit_bytes: int = DEFAULT_BUDGET_BYTES,
) -> BudgetResult:
    """Admit excerpts from ``collect`` in relevance order, lazily.

    ``collect`` is a zero-argument callable returning a fresh
    ``Iterable[Excerpt]`` each time it is called — a dimension's ``collect``
    bound to its context, typically. It may be invoked up to three times, once
    per tier; each invocation gets its own independent stream.

    ``scope`` supplies the tiering data — ``scope.changed_files`` for tier 1,
    ``scope.task_ref.guide_path`` (when present) for tier 2 — and may be
    ``None`` when no scope has been resolved for this call, in which case
    both tiers are empty, only the tier-3 pass runs, and the result is
    ordered by arrival within that single pass — the same behaviour this
    pipeline had before T005.

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

    kept: list[Excerpt] = []
    seen_refs: set[str] = set()
    hits: list[RedactionHit] = []
    used = 0
    truncated = False
    omitted_count = 0

    # A tier whose membership set is provably empty can never match anything
    # `_tier` returns, so its pass is skipped without a `collect()` call at
    # all — not merely an optimisation: it is what keeps a `scope=None` (or
    # scope-with-nothing-declared) caller down to the single tier-3 pass this
    # pipeline always ran before T005, rather than two wasted full drains.
    reachable_tiers = [
        tier
        for tier in _TIERS_IN_PRIORITY_ORDER
        if (tier != _TIER_CHANGED or changed)
        and (tier != _TIER_REFERENCED or referenced)
    ]

    for pass_tier in reachable_tiers:
        if truncated:
            # A rejection in an earlier, higher-priority pass ends the whole
            # run: nothing in a lower-priority tier is worth pulling once the
            # budget is spent (AC #4 — triggered by a rejection, never by
            # `used >= limit_bytes` alone; that property already held before
            # this pass started).
            break

        for raw in collect():
            # Classified on the *raw* path — cheap, and avoids redacting text
            # this pass has no use for. `changed_files`/kit-artifact names are
            # ordinary repo-relative paths, never secret-shaped, so comparing
            # against the raw path is safe.
            if _tier(raw.path, changed, referenced) != pass_tier:
                continue

            safe, item_hits, size = _prepare(raw)

            if safe.ref in seen_refs:
                # Same file, same line range, possibly re-encountered by a
                # later pass: admitted once, and not counted as an omission
                # (Edge Case Checklist).
                continue
            seen_refs.add(safe.ref)
            hits.extend(item_hits)

            if used + size <= limit_bytes:
                kept.append(safe)
                used += size
                continue

            # The first excerpt in this pass that does not fit as pulled ends
            # this pass — and, via the `truncated` check above, every pass
            # after it. The stream is never drained further.
            omitted_count = 1
            truncated = True
            break

    record = TruncationRecord(truncated=truncated, omitted_count=omitted_count)
    return BudgetResult(excerpts=tuple(kept), truncation=record, redactions=tuple(hits))


def _referenced_files(scope) -> frozenset[str]:
    """Tier-2 paths: files referenced by the loaded spec/kit artifacts that
    this specific call's ``scope`` actually resolved — ``scope.task_ref``'s
    guide, for a ``task`` scope. Deliberately not every file that merely has a
    kit-shaped name (``PROJECT_SPEC.md`` and the like): that would make tier 2
    reachable even when ``scope`` carries no data at all, forcing a pass — and
    a full drain, in the common case where no such name shows up — for every
    caller, not only ones that actually resolved a scope.
    """
    task_ref = getattr(scope, "task_ref", None)
    if task_ref is None:
        return frozenset()
    return frozenset({task_ref.guide_path})


def _tier(path: str, changed: frozenset[str], referenced: frozenset[str]) -> int:
    """A path's relevance tier (FR-011a). A path in both tier 1 and tier 2 is
    tier 1 — checked first, so it is admitted once, in the tier-1 pass."""
    if path in changed:
        return _TIER_CHANGED
    if path in referenced:
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
