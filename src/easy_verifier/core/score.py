"""Shared score orchestration for the CLI, MCP adapter, and report.

This module owns no scoring policy or arithmetic. It composes the fixed T019,
T020, and T021 contracts so both adapters expose one deterministic operation.
"""

from __future__ import annotations

import dataclasses
import json
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ..dimensions import dimension_names
from .assessment import AssessmentSet, ComparisonSet, assess, compare
from .findings import Finding, validate_findings
from .gate import (
    apply_gate_evaluations,
    change_kind_request,
    detect_evaluate_gates,
    detect_pick_gates,
    detect_stack,
    gate_requests,
    parse_change_kind,
    reference_requests,
    review_requests,
    test_pairs_request,
)
from .improve import ImprovementPlan, improvement_plan
from .judge import (
    CHANGE_FLOORS,
    DOCUMENTATION_RULES,
    EVIDENCE_LACK_REASONS,
    MEASURED_WEIGHT_FLOOR,
    PACK_FLOORS,
    GatedRating,
    OverallRating,
    Rating,
    RatingAbstention,
    areas_measured,
    areas_without_rule,
    rate,
    rate_overall,
)
from .metric_tables import (
    curated_metric_tables,
    metric_tables,
    registry_sources,
    rejected_abstentions,
    with_conventions,
)
from .metrics import MetricSet, compute_metrics
from .models import (
    ChangeKind,
    CombinedPack,
    CoverageSummary,
    EvidencePack,
    PairFacts,
)
from .pipeline import DEFAULT_BUDGET_BYTES, DEFAULT_SCOPE
from .redact import redact
from .registry import RegistryEntry, convention_entries, sot_root
from .roles import (
    GENERIC_PATTERNS,
    _registry,
    active_packs,
    documentation_present,
    load_repo_config,
    parse_agent_input,
    registry_notes,
    review_notes,
)
from .structure import repo_convention_notes, repo_conventions
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
    registry_entries: tuple[dict[str, Any], ...] = ()
    """Every local-layer registry field the tables were built with, as
    replayable agent-input items with source tag and link (FR-048)."""
    stack: dict[str, Any] | None = None
    """Languages and frameworks detected from manifests (T037, FR-044);
    listed in :meth:`to_dict` for both adapters when anything is detected."""
    reference: dict[str, Any] | None = None
    """MCP-only reference gate (T037, FR-045): ``{requests, omitted,
    instructions}`` for missing registry fields. Like ``needs_input``, never
    part of :meth:`to_dict`; the CLI never shows it (FR-040)."""
    registry_notes: tuple[str, ...] = ()
    """Registry warnings for this machine ("curated wins", research that
    could not be saved). Like ``needs_input``, not part of :meth:`to_dict`:
    it describes the local layer, not the score, so replay stays byte-equal
    (DDR-0005); each adapter surfaces it itself."""
    review: dict[str, Any] | None = None
    """MCP-only review gate (T038, FR-047): ``{entries, omitted,
    instructions}`` for local entries awaiting the user's review. Like
    ``reference``, never part of :meth:`to_dict`; the CLI never shows it."""
    samples: tuple[dict[str, Any], ...] = ()
    """Per sampled dimension, in canonical order (T068, FR-060): which
    priority batches of its sources were read. In :meth:`to_dict` for both
    adapters, only when non-empty, so a repository at or under the cap
    serialises exactly as before."""
    excluded: tuple[dict[str, str], ...] = ()
    """Third-party roots the evaluation left out (T087, FR-074): ``{path,
    excluded: "third-party", reason, rule}``, one per root. In
    :meth:`to_dict` for both adapters, only when non-empty, so a repository
    with nothing excluded serialises exactly as before."""
    capped: tuple[dict[str, Any], ...] = ()
    """Every per-role cap a dimension's inputs hit (T098, NFR-009):
    ``{dimension, role, matched, read}``, in canonical dimension order and then
    role name. In :meth:`to_dict` for both adapters, only when non-empty, so a
    repository with no cap hit serialises exactly as before."""
    continue_batches: dict[str, Any] | None = None
    """MCP-only (T068, FR-061): ``{batches_done, batches_total, files_read,
    files_in_scope, question}`` while batches remain. Like ``needs_input``,
    never part of :meth:`to_dict`."""
    change_risk: Rating | RatingAbstention | None = None
    """The change-risk rating (T108, FR-079): the separate ``change_risk``
    headline beside ``overall``, never in ``ratings`` or the overall. ``None``
    when the dimension was not gathered (``project`` scope), and then left out
    of :meth:`to_dict`, so a project payload serialises exactly as before."""
    change_kind: ChangeKind | None = None
    """The change kind shown with ``change_risk`` (FR-080): detected, or
    confirmed by the calling agent (T109, FR-081)."""
    change_kind_reason: str | None = None
    """The agent's redacted reason for a confirmed kind (T109); in
    :meth:`to_dict` only when the kind is confirmed."""
    change_kind_rejected: tuple[str, ...] = ()
    """Why an ``agent_input.change_kind`` answer was rejected (T109); in
    :meth:`to_dict` only when non-empty, the detected kind kept."""
    change_kind_question: dict[str, Any] | None = None
    """MCP-only change-kind gate (T109, FR-081): ``needs_input.change_kind``
    while the kind is only detected. Like ``needs_input``, never part of
    :meth:`to_dict`; the CLI never asks (FR-034)."""
    test_pairs: PairFacts | None = None
    """The change's test <-> source pairs (T112, FR-084) shown with
    ``change_risk``; ``None`` unless the change is a bugfix or feature with
    changed source."""
    test_pairs_question: dict[str, Any] | None = None
    """MCP-only test-pairs gate (T112, FR-084): ``needs_input.test_pairs``
    until an answer applies. Never part of :meth:`to_dict`."""

    @property
    def improvement_plan(self) -> ImprovementPlan:
        """FR-055: a pure function of the ratings, so both adapters, replay
        and the report all see the same plan (DDR-0009)."""
        return improvement_plan(self.ratings, self.overall)

    @property
    def warnings(self) -> list[dict[str, Any]]:
        """FR-059: one warning per abstention for missing evidence, in
        canonical order, naming what was not measured or not found. A pure
        function of the ratings, like the plan."""
        return [
            _evidence_warning(item)
            for item in self.ratings
            if type(item) is RatingAbstention
            and item.reason_code in EVIDENCE_LACK_REASONS
        ]

    @property
    def areas_measured(self) -> tuple[str, ...]:
        """FR-073: the evaluation areas this run measured; a pure function of
        the ratings, so it is present whether or not the overall is withheld."""
        return areas_measured(self.ratings)

    @property
    def areas_without_rule(self) -> tuple[str, ...]:
        """FR-073: the evaluation areas no declared rule covers yet; an
        optional pack's rules count only when it ran (T047)."""
        return areas_without_rule([item.dimension for item in self.ratings])

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "ratings": [item.to_dict() for item in self.ratings],
            "overall": self.overall.to_dict(),
        }
        if self.change_risk is not None:
            payload["change_risk"] = {
                **self.change_risk.to_dict(),
                "change_kind": _change_kind_dict(
                    self.change_kind,
                    self.change_kind_reason,
                    self.change_kind_rejected,
                ),
            }
            if self.test_pairs is not None:
                payload["change_risk"]["test_pairs"] = _test_pairs_dict(
                    self.test_pairs
                )
        payload |= {
            "areas_measured": list(self.areas_measured),
            "areas_without_rule": list(self.areas_without_rule),
            "improvement_plan": self.improvement_plan.to_dict(),
            "warnings": self.warnings,
        }
        if self.samples:
            payload["samples"] = [dict(item) for item in self.samples]
        if self.excluded:
            payload["excluded"] = [dict(item) for item in self.excluded]
        if self.capped:
            payload["capped"] = [dict(item) for item in self.capped]
        payload |= {
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
        if self.stack and (self.stack["languages"] or self.stack["frameworks"]):
            payload["detected_stack"] = self.stack
        if self.registry_entries:
            payload["registry_entries"] = [dict(item) for item in self.registry_entries]
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
    batches: int | str | None = None,
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

    ``batches`` (T068) is an adapter's explicit priority-batch count (CLI
    ``--batches``/``--all``); MCP callers name it as ``agent_input.batches``.
    While batches remain, the MCP-only ``continue_batches`` question rides
    along with every round: it asks the user, not the rules.
    """
    document = parse_agent_input(agent_input) if agent_input is not None else None
    evaluations = document.get("gate_evaluations") if document is not None else None
    # Before the answers change the layer: which of them will be ignored.
    ignored_reviews = review_notes(document)
    # T047: optional packs run only when configured or picked, after the
    # dimensions; an unknown name is a note, never an error.
    pack_names, pack_notes = active_packs(repo_path, document)
    packs = combined_pack(
        (*scored_dimensions(scope), *pack_names),
        repo_path=repo_path,
        scope=scope,
        budget_bytes=budget_bytes,
        ref=ref,
        task_id=task_id,
        agent_input=document,
        batches=batches,
        packs=pack_names,
    )
    by_dimension: Mapping[str, Sequence[Finding]] | None = None
    if findings is not None:
        by_dimension = validate_findings(findings, _pack_map(packs)).by_dimension
    stack = detect_stack(repo_path, _registry())
    frameworks = tuple((item["name"], item["language"]) for item in stack["frameworks"])
    result = score_packs(
        packs,
        by_dimension,
        evaluations,
        frameworks=frameworks,
        conventions=repo_conventions(repo_path, document),
    )
    kind_answer = _change_kind_answer(document, result.change_kind)
    result = dataclasses.replace(
        result,
        stack=stack,
        registry_notes=registry_notes(document, repo_path)
        + ignored_reviews
        + pack_notes
        + repo_convention_notes(repo_path, document)
        + kind_answer[2]
        + _test_pairs_notes(document, result.test_pairs),
        change_kind_reason=kind_answer[0],
        change_kind_rejected=kind_answer[1],
    )

    # One round each: a caller that already supplied agent input gets no
    # detect gate, stateless and unconditional (DDR-0006 §7). No repository
    # walk happens at all in that case, so a picks round costs nothing extra.
    # The change-kind question rides along with every round too (T109): it
    # is asked until a valid answer arrives, never at project/task scope.
    if detect_gates:
        kind = result.change_kind
        result = dataclasses.replace(
            result,
            continue_batches=continue_question(result.samples),
            change_kind_question=change_kind_request(kind)
            if kind is not None and kind.source == "detected"
            else None,
            test_pairs_question=_test_pairs_question(result.test_pairs),
        )
    if not detect_gates or evaluations is not None:
        return result
    # The reference gate rides along with whichever round is asked: it adds
    # no round of its own (DDR-0006 §7), and answers arrive as
    # registry_entries in the same next call as picks or gate evaluations.
    reference = reference_requests(stack, _registry())
    review = review_requests(sot_root(), GENERIC_PATTERNS)
    result = dataclasses.replace(result, reference=reference, review=review)
    needs_input = None
    if agent_input is None:
        needs_input = detect_pick_gates(repo_path, load_repo_config(repo_path))
    requests = None
    if needs_input is None:
        found = gate_requests(detect_evaluate_gates(result.ratings), _pack_map(packs))
        requests = tuple(found) if found else None
    return dataclasses.replace(result, needs_input=needs_input, gate_requests=requests)


def scored_dimensions(scope: str) -> tuple[str, ...]:
    """The dimensions ``score`` gathers at ``scope``, canonical order: all of
    them, except that ``change-risk`` rates a change and is left out at
    ``project`` scope (FR-079), so project payloads stay as they were."""
    return tuple(
        name
        for name in dimension_names()
        if not (scope == "project" and name in CHANGE_FLOORS)
    )


def report_dimensions(
    repo_path: str | Path,
    agent_input: object | None = None,
    scope: str | None = None,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """``(dimensions to gather, active packs)`` for ``write_report`` (T047):
    every dimension, then the packs ``.easy-verifier.toml`` or
    ``agent_input.packs`` enable, so the report scores what ``score`` does."""
    document = parse_agent_input(agent_input) if agent_input is not None else None
    names, _notes = active_packs(repo_path, document)
    core = scored_dimensions(scope) if scope is not None else dimension_names()
    return (*core, *names), names


def score_packs(
    packs: CombinedPack,
    findings_by_dimension: Mapping[str, Sequence[Finding]] | None = None,
    gate_evaluations: object | None = None,
    *,
    frameworks: Sequence[tuple[str, str]] = (),
    conventions: RegistryEntry | None = None,
) -> ScoreResult:
    """Score one complete combined pack without gathering more evidence.

    ``gate_evaluations`` (T028) replaces each gated, validly evaluated
    dimension with its blended or agent-rated :class:`GatedRating`. Findings
    assessments are compared with the **rules** ratings only: FR-029a still
    forbids blending an assessment, and a divergence against a number the
    agent already moved would measure the agent against itself.

    ``frameworks`` are the detected ``(framework, language)`` pairs (T037):
    each one's registry entry is merged into its language before the metric
    tables are compiled, so framework fields reach the rules.

    ``conventions`` is the call's resolved entry (T078,
    ``structure.repo_conventions``): its layer_paths classify layers, and its
    non-curated values are embedded in ``registry_entries`` for replay.
    """
    actual = tuple(slot.dimension for slot in packs.slots)
    # Every dimension in canonical order (change-risk only where gathered,
    # T108), then any active optional packs (T047) in declared order.
    expected = (
        *(
            name
            for name in dimension_names()
            if name not in CHANGE_FLOORS or name in actual
        ),
        *(name for name in PACK_FLOORS if name in actual),
    )
    if actual != expected:
        raise ValueError(
            "score requires all declared dimensions in canonical order; got "
            + (", ".join(actual) or "none")
        )

    registry = _registry()
    applied = registry.applied(frameworks)
    tables = curated_metric_tables() if applied is registry else metric_tables(applied)
    if conventions is not None:
        tables = with_conventions(tables, conventions)
    metrics = rejected_abstentions(compute_metrics(packs, tables), packs, applied)
    sources = registry_sources(packs, applied)
    pack_map = _pack_map(packs)
    every_rating = tuple(
        rate(
            _metrics_for(metrics, dimension),
            _coverage_for(packs, dimension),
            registry_sources=sources.get(dimension),
            documentation=tuple(
                documentation_present(rule, pack_map[dimension].files_read)
                for rule in DOCUMENTATION_RULES.get(dimension, ())
            )
            if dimension in pack_map
            else None,
        )
        for dimension in expected
    )
    # T108: change-risk is its own headline, kept out of the overall, and
    # absent at project scope (as in the score payload) even when gathered.
    change_risk = next(
        (
            item
            for item in every_rating
            if item.dimension in CHANGE_FLOORS
            and getattr(pack_map.get(item.dimension), "scope", None) != "project"
        ),
        None,
    )
    rules_ratings = tuple(
        item for item in every_rating if item.dimension not in CHANGE_FLOORS
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
        # Assessments cover the dimensions only; packs are rules-only (T047).
        assessments = assess(
            {
                name: items
                for name, items in findings_by_dimension.items()
                if name not in PACK_FLOORS and name not in CHANGE_FLOORS
            }
        )
        comparisons = compare(
            tuple(r for r in rules_ratings if r.dimension not in PACK_FLOORS),
            assessments,
        )
    provenance = tuple(
        (
            slot.dimension,
            slot.pack.source_provenance
            if slot.pack is not None
            else "unavailable: the dimension failed and produced no pack",
        )
        for slot in packs.slots
        if slot.dimension not in CHANGE_FLOORS
    )
    samples = tuple(
        {
            "dimension": slot.dimension,
            "batches_done": slot.pack.sample.batches_done,
            "batches_total": slot.pack.sample.batches_total,
            "files_read": slot.pack.sample.files_read,
            "files_in_scope": slot.pack.sample.files_in_scope,
            "order": slot.pack.sample.order,
        }
        for slot in packs.slots
        if slot.pack is not None and slot.pack.sample is not None
    )
    # Every pack resolved the same scope, so any pack carries the same list.
    excluded = next(
        (
            tuple(asdict(item) for item in slot.pack.excluded)
            for slot in packs.slots
            if slot.pack is not None and slot.pack.excluded
        ),
        (),
    )
    index_cap = (
        ({"dimension": "index", **asdict(packs.index_capped)},)
        if packs.index_capped is not None
        else ()
    )
    capped = index_cap + tuple(
        {"dimension": slot.dimension, **asdict(item)}
        for slot in packs.slots
        if slot.pack is not None and slot.pack.capped
        for item in slot.pack.capped
    )
    return ScoreResult(
        ratings,
        overall,
        metrics,
        assessments,
        comparisons,
        provenance,
        registry_entries=tuple(
            sorted(
                (
                    *registry.local_entries(name for name, _ in frameworks),
                    *(convention_entries(conventions) if conventions else ()),
                ),
                key=lambda item: json.dumps(item, sort_keys=True),
            )
        ),
        samples=samples,
        excluded=excluded,
        capped=capped,
        change_risk=change_risk,
        change_kind=next(
            (
                pack_map[name].change_kind
                for name in CHANGE_FLOORS
                if name in pack_map
            ),
            None,
        ),
        test_pairs=next(
            (
                pack_map[name].test_pairs
                for name in CHANGE_FLOORS
                if name in pack_map
            ),
            None,
        ),
    )


CONTINUE_QUESTION = (
    "Only {read} of {scope} in-scope source files were read (batches {done} of "
    "{total}, most important and most-changed first), so code-quality, "
    "architecture and test-strategy describe a sample. Ask the user whether to "
    "read the next batch (a larger sample, more tokens) or stop here and keep "
    "this result. To continue, call score again with the same agent_input plus "
    '"batches": {next} (or "all" for every remaining batch); never send a file '
    "count or a metric."
)


def continue_note(samples: Sequence[Mapping[str, Any]]) -> str | None:
    """The CLI's disclosure of remaining batches and the flag that continues
    (T068, FR-061), or ``None`` when none remain. Here, not in the adapter,
    so the adapter stays free of arithmetic (FR-021)."""
    ask = continue_question(samples)
    if ask is None:
        return None
    return (
        f"read batches {ask['batches_done']} of {ask['batches_total']} "
        f"({ask['files_read']} of {ask['files_in_scope']} in-scope source files, "
        "most important and most-changed first); continue with --batches "
        f"{ask['batches_done'] + 1}, or --all"
    )


def continue_question(samples: Sequence[Mapping[str, Any]]) -> dict[str, Any] | None:
    """``needs_input.continue_batches`` (T068, FR-061), or ``None`` when every
    sampled dimension read all its batches. Every code tier batches the same
    candidate list, so the first unfinished sample speaks for all of them."""
    for item in samples:
        if item["batches_done"] < item["batches_total"]:
            return {
                "batches_done": item["batches_done"],
                "batches_total": item["batches_total"],
                "files_read": item["files_read"],
                "files_in_scope": item["files_in_scope"],
                "question": CONTINUE_QUESTION.format(
                    read=item["files_read"],
                    scope=item["files_in_scope"],
                    done=item["batches_done"],
                    total=item["batches_total"],
                    next=item["batches_done"] + 1,
                ),
            }
    return None


CHANGE_KIND_IGNORED = (
    "agent_input.change_kind ignored: there is no change kind to confirm on "
    "this call (change risk is rated only for a change, at changes or "
    "worktree scope)"
)


def _change_kind_answer(
    document: Mapping[str, Any] | None, kind: ChangeKind | None
) -> tuple[str | None, tuple[str, ...], tuple[str, ...]]:
    """``(reason, rejected, notes)`` for ``agent_input.change_kind`` (T109):
    the redacted reason of a valid answer, the problems of an invalid one,
    or a note when this call has no kind to confirm. Never raises."""
    if document is None or "change_kind" not in document:
        return None, (), ()
    if kind is None:
        return None, (), (CHANGE_KIND_IGNORED,)
    answer, problems = parse_change_kind(document["change_kind"])
    if answer is None:
        return None, tuple(problems), ()
    return redact(answer["reason"]), (), ()


def _change_kind_dict(
    kind: ChangeKind | None,
    reason: str | None = None,
    rejected: tuple[str, ...] = (),
) -> dict[str, Any] | None:
    if kind is None:
        return None
    payload: dict[str, Any] = {
        "value": kind.value,
        "source": kind.source,
        "signals": [dataclasses.asdict(item) for item in kind.signals],
        "signals_omitted": kind.signals_omitted,
    }
    if kind.source == "confirmed" and reason is not None:
        payload["reason"] = reason
    if rejected:
        payload["rejected"] = list(rejected)
    return payload


TEST_PAIRS_IGNORED = (
    "agent_input.test_pairs ignored: this call proposes no test pairs (they "
    "are matched only for a bugfix or feature change with changed source "
    "code, at changes or worktree scope)"
)


def _test_pairs_notes(
    document: Mapping[str, Any] | None, facts: PairFacts | None
) -> tuple[str, ...]:
    """A note when ``agent_input.test_pairs`` has no pairs to answer (T112)."""
    if document is None or "test_pairs" not in document or facts is not None:
        return ()
    return (TEST_PAIRS_IGNORED,)


def _test_pairs_question(facts: PairFacts | None) -> dict[str, Any] | None:
    """``needs_input.test_pairs`` while no answer applied and there is a
    changed test to judge (T112): never for chore/refactor or no source."""
    if facts is None or facts.answered:
        return None
    if not (facts.proposals or facts.unpaired_tests):
        return None
    return test_pairs_request(facts)


def _test_pairs_dict(facts: PairFacts) -> dict[str, Any]:
    def pair(item) -> dict[str, Any]:
        payload = dataclasses.asdict(item)
        if payload["reason"] is None:
            del payload["reason"]
        return payload

    payload: dict[str, Any] = {
        "pairs": [pair(item) for item in facts.pairs],
        "unpaired_tests": list(facts.unpaired_tests),
        "unpaired_sources": list(facts.unpaired_sources),
        "no_symbols": list(facts.no_symbols),
    }
    if facts.dropped:
        payload["dropped"] = [pair(item) for item in facts.dropped]
    if facts.rejected:
        payload["rejected"] = list(facts.rejected)
    return payload


def _evidence_warning(item: RatingAbstention) -> dict[str, Any]:
    share = item.measured_share
    if share is not None:
        message = (
            f"no number given — only {share * 100:.0f}% of its rule weight was "
            f"measured (a rating needs at least {MEASURED_WEIGHT_FLOOR * 100:.0f}%); "
            "add what the unmeasured rules need"
        )
    else:
        message = f"no number given — {item.reason}"
    warning: dict[str, Any] = {
        "dimension": item.dimension,
        "reason_code": item.reason_code,
        "message": message,
        "unmeasured_rules": [
            {"metric_name": name, "reason": reason}
            for name, reason in item.unavailable_metrics
        ],
        "sources_missing": [
            {"source": miss.source, "reason": miss.reason}
            for miss in item.sources_missing
        ],
    }
    if share is not None:
        warning["measured_share"] = item.to_dict()["measured_share"]
    return warning


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


__all__ = [
    "ScoreResult",
    "report_dimensions",
    "score_packs",
    "score_repository",
    "scored_dimensions",
]
