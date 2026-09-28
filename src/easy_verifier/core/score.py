"""Shared score orchestration for the CLI, MCP adapter, and report.

This module owns no scoring policy or arithmetic. It composes the fixed T019,
T020, and T021 contracts so both adapters expose one deterministic operation.
"""

from __future__ import annotations

import dataclasses
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..dimensions import dimension_names
from .assessment import AssessmentSet, ComparisonSet, assess, compare
from .findings import Finding, validate_findings
from .gate import (
    apply_gate_evaluations,
    detect_evaluate_gates,
    detect_pick_gates,
    gate_requests,
)
from .judge import (
    GatedRating,
    OverallRating,
    Rating,
    RatingAbstention,
    rate,
    rate_overall,
)
from .metrics import MetricSet, compute_metrics
from .models import CombinedPack, CoverageSummary, EvidencePack
from .pipeline import DEFAULT_BUDGET_BYTES, DEFAULT_SCOPE
from .roles import load_repo_config, parse_agent_input
from .synthesis import combined_pack


@dataclass(frozen=True)
class ScoreResult:
    """Complete seven-dimension score output and optional caller assessment."""

    ratings: tuple[Rating | RatingAbstention | GatedRating, ...]
    overall: OverallRating | RatingAbstention
    metrics: MetricSet
    assessments: AssessmentSet | None = None
    comparisons: ComparisonSet | None = None
    provenance: tuple[tuple[str, str], ...] = ()
    """Per dimension, in canonical order: where its sources came from
    (FR-039, sources half)."""
    needs_input: dict[str, dict[str, Any]] | None = None
    """MCP-only detect gate (T027, FR-035): role -> {candidates, omitted}, or
    ``None`` when nothing qualifies. Computed here so the arithmetic stays
    shared (FR-021), but deliberately **not** part of :meth:`to_dict` — an
    adapter that wants to expose it merges it into the payload itself. The
    CLI never does (FR-034, FR-040); the parity test compares the two
    payloads with this field excluded from the MCP side."""
    gate_requests: tuple[dict[str, Any], ...] | None = None
    """MCP-only evaluate gate (T028, FR-036): one entry per gated dimension,
    ``{dimension, reason, evidence_refs, omitted}``. Like ``needs_input``,
    never part of :meth:`to_dict`; set only when no picks are pending and the
    call carried no ``gate_evaluations``."""

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "ratings": [item.to_dict() for item in self.ratings],
            "overall": self.overall.to_dict(),
            "metrics": json.loads(self.metrics.serialize()),
            "provenance": [
                {
                    "dimension": dimension,
                    "sources": sources,
                    "rating": _rating_provenance(rating),
                }
                for (dimension, sources), rating in zip(
                    self.provenance, self.ratings, strict=True
                )
            ],
        }
        if self.assessments is not None and self.comparisons is not None:
            payload["assessments"] = [
                item.to_dict() for item in self.assessments.outcomes
            ]
            payload["divergences"] = [
                item.divergence.to_dict() for item in self.comparisons.comparisons
            ]
        return payload

    def serialize(self) -> str:
        return json.dumps(
            self.to_dict(), sort_keys=True, ensure_ascii=True, separators=(",", ":")
        )


def score_repository(
    repo_path: str | Path,
    scope: str = DEFAULT_SCOPE,
    budget_bytes: int = DEFAULT_BUDGET_BYTES,
    *,
    ref: str | None = None,
    task_id: str | None = None,
    findings: list[dict[str, Any]] | str | bytes | None = None,
    agent_input: dict[str, Any] | str | bytes | None = None,
    detect_gates: bool = False,
) -> ScoreResult:
    """Gather all seven dimensions and return one complete score result.

    ``agent_input`` is the caller's optional agent-input document (FR-034):
    ``picks`` and ``gate_evaluations``. ``detect_gates`` computes the MCP-only
    hard gates (T027 detect, T028 evaluate); it defaults to ``False`` because
    the result is MCP-only (FR-021, FR-034, FR-040) and computing it for the
    CLI path would be a discarded repository walk on every call. Only the MCP
    ``score`` tool passes ``True`` — the core stays shared either way.

    Round order (DDR-0006 §7, at most two extra rounds): a first call with
    candidates pending asks for picks only; the call that carries picks (or a
    first call with nothing to pick) asks for gate evaluations; a call that
    carries ``gate_evaluations`` asks nothing.
    """
    document = parse_agent_input(agent_input) if agent_input is not None else None
    evaluations = document.get("gate_evaluations") if document is not None else None
    packs = combined_pack(
        dimension_names(),
        repo_path=repo_path,
        scope=scope,
        budget_bytes=budget_bytes,
        ref=ref,
        task_id=task_id,
        agent_input=document,
    )
    by_dimension: Mapping[str, Sequence[Finding]] | None = None
    if findings is not None:
        by_dimension = validate_findings(findings, _pack_map(packs)).by_dimension
    result = score_packs(packs, by_dimension, evaluations)

    # One round each: a caller that already supplied agent input gets no
    # detect gate, stateless and unconditional (DDR-0006 §7). No repository
    # walk happens at all in that case, so a picks round costs nothing extra.
    if not detect_gates or evaluations is not None:
        return result
    needs_input = None
    if agent_input is None:
        needs_input = detect_pick_gates(repo_path, load_repo_config(repo_path))
    requests = None
    if needs_input is None:
        found = gate_requests(detect_evaluate_gates(result.ratings), _pack_map(packs))
        requests = tuple(found) if found else None
    return dataclasses.replace(result, needs_input=needs_input, gate_requests=requests)


def score_packs(
    packs: CombinedPack,
    findings_by_dimension: Mapping[str, Sequence[Finding]] | None = None,
    gate_evaluations: object | None = None,
) -> ScoreResult:
    """Score one complete combined pack without gathering more evidence.

    ``gate_evaluations`` (T028) replaces each gated, validly evaluated
    dimension with its blended or agent-rated :class:`GatedRating`. Findings
    assessments are compared with the **rules** ratings only: FR-029a still
    forbids blending an assessment, and a divergence against a number the
    agent already moved would measure the agent against itself.
    """
    expected = dimension_names()
    actual = tuple(slot.dimension for slot in packs.slots)
    if actual != expected:
        raise ValueError(
            "score requires all seven dimensions in canonical order; got "
            + (", ".join(actual) or "none")
        )

    metrics = compute_metrics(packs)
    rules_ratings = tuple(
        rate(_metrics_for(metrics, dimension), _coverage_for(packs, dimension))
        for dimension in expected
    )
    ratings = (
        apply_gate_evaluations(gate_evaluations, rules_ratings, _pack_map(packs))
        if gate_evaluations is not None
        else rules_ratings
    )
    overall = rate_overall(ratings)

    assessments = None
    comparisons = None
    if findings_by_dimension is not None:
        assessments = assess(findings_by_dimension)
        comparisons = compare(rules_ratings, assessments)
    provenance = tuple(
        (
            slot.dimension,
            slot.pack.source_provenance
            if slot.pack is not None
            else "unavailable: the dimension failed and produced no pack",
        )
        for slot in packs.slots
    )
    return ScoreResult(ratings, overall, metrics, assessments, comparisons, provenance)


def _rating_provenance(rating: Rating | RatingAbstention | GatedRating) -> str:
    """FR-039, rating half: how this dimension's number was produced."""
    if type(rating) is GatedRating:
        return rating.rated_by
    return "rules" if type(rating) is Rating else "abstained"


def _pack_map(packs: CombinedPack) -> dict[str, EvidencePack]:
    return {slot.dimension: slot.pack for slot in packs.slots if slot.pack is not None}


def _metrics_for(metrics: MetricSet, dimension: str) -> MetricSet:
    return MetricSet(
        metrics=tuple(item for item in metrics if item.dimension == dimension),
        dimensions_without_pack=tuple(
            item for item in metrics.dimensions_without_pack if item[0] == dimension
        ),
    )


def _coverage_for(packs: CombinedPack, dimension: str) -> CoverageSummary:
    scores = tuple(
        item for item in packs.coverage.per_dimension if item[0] == dimension
    )
    misses = tuple(item for item in packs.coverage.misses if item[0] == dimension)
    if len(scores) != 1 or len(misses) != 1:
        raise ValueError(
            f"combined coverage must contain one score and miss list for {dimension!r}"
        )
    return CoverageSummary(
        per_dimension=scores,
        combined=scores[0][1],
        method=packs.coverage.method,
        misses=misses,
    )


__all__ = ["ScoreResult", "score_packs", "score_repository"]
