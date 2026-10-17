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

from ..dimensions import DIMENSIONS
from ..dimensions import dimension_names as available_dimension_names
from ..packs import PACKS
from . import redact as redact_module
from .batches import BatchInputError, parse_batches
from .findings import ValidationError
from .gate import parse_change_kind, parse_test_pairs
from .models import CombinedPack, CoverageSummary, DimensionSlot, SourceMiss
from .pipeline import (
    DEFAULT_BUDGET_BYTES,
    DEFAULT_SCOPE,
    RepoPathError,
    run_dimension,
)
from .roles import apply_registry_entries, parse_agent_input, validate_agent_input
from .structure import repo_conventions

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
    agent_input: object | None = None,
    batches: int | str | None = None,
    packs: tuple[str, ...] = (),
) -> CombinedPack:
    """Run each named dimension and return their packs plus aggregate coverage.

    Raises ``ValueError`` if ``dimension_names`` is empty or names a dimension
    ``available_dimension_names()`` does not know — never against a second,
    duplicated
    list of valid names. Duplicate names are deduplicated; a dimension that
    raises does not abort the call, and carries a structured error in its slot
    instead of a pack.

    ``packs`` are the active optional packs (T047, ``roles.active_packs``):
    only those may be named besides the dimensions, and they run after them.
    """
    available_names = (
        *available_dimension_names(),
        *(name for name in PACKS if name in packs),
    )
    if not dimension_names:
        raise ValueError(
            "combined_pack requires at least one dimension name; valid "
            f"dimensions: {', '.join(available_names)}"
        )

    requested = set(dimension_names)
    valid = set(available_names)
    unknown = requested - valid
    if unknown:
        raise ValueError(
            f"unknown dimension(s): {', '.join(sorted(unknown))}; "
            f"valid dimensions: {', '.join(available_names)}"
        )

    # Agent input is validated once, before any dimension runs, so a rejected
    # document is one validation error rather than seven failed slots (T026).
    picks = (
        validate_agent_input(agent_input, repo_path)
        if agent_input is not None
        else None
    )
    # Validated registry entries are saved and the registry reloaded before
    # any dimension runs, so this call already uses them (T036).
    if agent_input is not None:
        apply_registry_entries(parse_agent_input(agent_input), repo_path)
    # T078: resolved once, after the layer is written, for every dimension.
    conventions = repo_conventions(
        repo_path,
        parse_agent_input(agent_input) if agent_input is not None else None,
    )
    count = _batch_count(batches, agent_input)
    # T109: a valid agent_input.change_kind replaces the detected kind in the
    # change-risk dimension; an invalid one is reported by score, never raised.
    confirmed_kind = _confirmed_kind(agent_input)
    # T112: agent_input.test_pairs, shape-checked here; change-risk decides
    # whether each entry names this change's files.
    pair_answers = _pair_answers(agent_input)

    # Canonical, deterministic order regardless of the order requested (AC #10).
    ordered_names = tuple(name for name in available_names if name in requested)

    slots: list[DimensionSlot] = []
    for name in ordered_names:
        try:
            pack = run_dimension(
                DIMENSIONS[name] if name in DIMENSIONS else PACKS[name],
                repo_path=repo_path,
                scope=scope,
                budget_bytes=budget_bytes,
                ref=ref,
                task_id=task_id,
                picks=picks,
                batches=count,
                conventions=conventions,
                change_kind=confirmed_kind,
                test_pairs=pair_answers,
            )
        except (RepoPathError, ValidationError):
            # NOT isolated. AC #6's robustness is about one *dimension* failing
            # while the others still return; an unusable repository path is a
            # precondition of the whole call, and every dimension would fail
            # identically. Swallowing it per-slot turned "this repo does not
            # exist" into a successful call full of error slots, and gave the
            # CLI exit 0 where the single-dimension path exits 2 (FR-022). An
            # invalid `.easy-verifier.toml` is the same kind of precondition.
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


def _confirmed_kind(agent_input: object | None) -> str | None:
    """The kind a valid ``agent_input.change_kind`` names, else ``None``."""
    if agent_input is None:
        return None
    document = parse_agent_input(agent_input)
    if "change_kind" not in document:
        return None
    answer, _problems = parse_change_kind(document["change_kind"])
    return answer["value"] if answer is not None else None


def _pair_answers(agent_input: object | None) -> tuple | None:
    """``gate.parse_test_pairs`` of ``agent_input.test_pairs``, else ``None``."""
    if agent_input is None:
        return None
    document = parse_agent_input(agent_input)
    if "test_pairs" not in document:
        return None
    return parse_test_pairs(document["test_pairs"])


def _batch_count(explicit: object | None, agent_input: object | None) -> int | str:
    """The priority-batch count (T068): an adapter's explicit value (CLI
    ``--batches``/``--all``) or ``agent_input.batches``, default 1. Naming two
    different counts is an error rather than a silent choice."""
    named = (
        parse_agent_input(agent_input).get("batches")
        if agent_input is not None
        else None
    )
    if explicit is not None and named is not None and explicit != named:
        raise BatchInputError(
            "batches: the call names two different batch counts (an adapter "
            "option and agent_input.batches); name one"
        )
    value = explicit if explicit is not None else named
    return parse_batches(value) if value is not None else 1


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

    # A failed dimension still gets a miss entry. Dropping it left the only
    # trace of the failure on `slots[].error`, so any reader holding just this
    # summary saw a dimension with no score and no misses -- which reads as
    # "sought nothing, reached everything". T013 rendered exactly that: a
    # crashed dimension shown as clean, on a page that printed the traceback
    # message one section further down.
    misses = tuple(
        (
            slot.dimension,
            slot.pack.sources_missing
            if slot.pack is not None
            else (
                SourceMiss(
                    source=slot.dimension,
                    reason=(
                        "not examined: the dimension failed and produced no "
                        f"evidence pack ({slot.error})"
                    ),
                ),
            ),
        )
        for slot in slots
    )

    return CoverageSummary(
        per_dimension=per_dimension,
        combined=combined,
        method=method,
        misses=misses,
    )


def _score(slot: DimensionSlot) -> float | None:
    return slot.pack.coverage_score if slot.pack is not None else None
