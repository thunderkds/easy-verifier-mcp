"""Combined multi-dimension pack + aggregate coverage (FR-025).

``combined_pack`` runs several named dimensions in one call and returns their
packs together with an aggregate coverage summary. Its contribution is
**aggregation and presentation only** (FR-026) — arithmetic and grouping, never
a cross-dimension narrative, correlation, ranking or "these findings suggest"
sentence. Deciding what several dimensions' findings mean together remains the
calling agent's job.

Budget model is **per-dimension** (user decision, 2026-08-25, recorded in
``memory/decisions.md``): each requested dimension gets the full
``budget_bytes`` independently, exactly as if it had been run alone via
:func:`easy_verifier.core.pipeline.run_dimension`. This is what makes a
single-dimension ``combined_pack`` call genuinely equivalent to a direct
``run_dimension`` call — a pooled/divided budget would make a dimension's
contents depend on what else was requested in the same call, which is neither
reproducible nor auditable. The accepted cost (NFR-009): a call requesting all
seven dimensions is roughly seven budgets, so boundedness rests on the caller
asking for fewer dimensions, not on this function shrinking anyone's budget.
"""

from __future__ import annotations

from pathlib import Path

from ..dimensions import DIMENSIONS, list_dimensions
from . import redact as redact_module
from .models import CombinedPack, CoverageSummary, DimensionSlot
from .pipeline import (
    DEFAULT_BUDGET_BYTES,
    DEFAULT_SCOPE,
    RepoPathError,
    run_dimension,
)

BUDGET_MODEL = "per-dimension"

_AGGREGATE_METHOD = (
    "pooled: sum(sources_found) / sum(sources_sought) across every requested "
    "dimension whose sources_sought is non-empty; dimensions that sought "
    "nothing do not affect the ratio"
)

_EXCLUSION_NOTE = (
    "; EXCLUDED from the ratio because they failed and produced no pack: "
    "{names} — the figure above describes only the {counted} dimension(s) that "
    "ran, not the {requested} requested"
)


def combined_pack(
    dimension_names,
    repo_path: str | Path,
    scope: str = DEFAULT_SCOPE,
    budget_bytes: int = DEFAULT_BUDGET_BYTES,
    *,
    ref: str | None = None,
    task_id: str | None = None,
) -> CombinedPack:
    """Run each named dimension and return their packs plus aggregate coverage.

    Raises ``ValueError`` if ``dimension_names`` is empty or names a dimension
    ``list_dimensions()`` does not know — never against a second, duplicated
    list of valid names. Duplicate names are deduplicated; a dimension that
    raises does not abort the call, and carries a structured error in its slot
    instead of a pack.
    """
    if not dimension_names:
        raise ValueError(
            "combined_pack requires at least one dimension name; valid "
            f"dimensions: {', '.join(list_dimensions())}"
        )

    requested = set(dimension_names)
    valid = set(list_dimensions())
    unknown = requested - valid
    if unknown:
        raise ValueError(
            f"unknown dimension(s): {', '.join(sorted(unknown))}; "
            f"valid dimensions: {', '.join(list_dimensions())}"
        )

    # Canonical, deterministic order regardless of the order requested (AC #10).
    ordered_names = tuple(name for name in list_dimensions() if name in requested)

    slots: list[DimensionSlot] = []
    for name in ordered_names:
        try:
            pack = run_dimension(
                DIMENSIONS[name],
                repo_path=repo_path,
                scope=scope,
                budget_bytes=budget_bytes,
                ref=ref,
                task_id=task_id,
            )
        except RepoPathError:
            # NOT isolated. AC #6's robustness is about one *dimension* failing
            # while the others still return; an unusable repository path is a
            # precondition of the whole call, and every dimension would fail
            # identically. Swallowing it per-slot turned "this repo does not
            # exist" into a successful call full of error slots, and gave the
            # CLI exit 0 where the single-dimension path exits 2 (FR-022).
            raise
        except Exception as exc:  # noqa: BLE001 - isolated per dimension, never re-raised
            # Redacted like any other engine-surfaced message (NFR-010): an
            # exception raised outside a dimension's own collect() has not
            # necessarily passed through run_dimension's own redaction.
            error = redact_module.scan(f"{type(exc).__name__}: {exc}").text
            slots.append(DimensionSlot(dimension=name, pack=None, error=error))
        else:
            slots.append(DimensionSlot(dimension=name, pack=pack, error=None))

    return CombinedPack(
        slots=tuple(slots),
        coverage=_aggregate_coverage(slots),
        budget_model=BUDGET_MODEL,
    )


def _aggregate_coverage(slots: list[DimensionSlot]) -> CoverageSummary:
    per_dimension = tuple((slot.dimension, _score(slot)) for slot in slots)

    found_total = 0
    sought_total = 0
    for slot in slots:
        if slot.pack is None:
            continue
        sought_total += len(slot.pack.sources_sought)
        found_total += len(slot.pack.sources_found)
    combined = (found_total / sought_total) if sought_total else None

    # A coverage figure must say what bounded it. A dimension that raised
    # contributes nothing to `found_total`/`sought_total`, so the ratio is
    # computed over a subset -- and `per_dimension` renders a failed dimension
    # as `None`, which is indistinguishable from one that sought nothing. If
    # the exclusion is not named here, the only honest signal lives on
    # `slots[].error`, and any reader holding just this summary is misled.
    failed = tuple(slot.dimension for slot in slots if slot.pack is None)
    method = _AGGREGATE_METHOD
    if failed:
        method += _EXCLUSION_NOTE.format(
            names=", ".join(failed),
            counted=len(slots) - len(failed),
            requested=len(slots),
        )

    misses = tuple(
        (slot.dimension, slot.pack.sources_missing)
        for slot in slots
        if slot.pack is not None
    )

    return CoverageSummary(
        per_dimension=per_dimension,
        combined=combined,
        method=method,
        misses=misses,
    )


def _score(slot: DimensionSlot) -> float | None:
    return slot.pack.coverage_score if slot.pack is not None else None
