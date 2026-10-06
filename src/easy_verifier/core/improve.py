"""Improvement plan for the scored repository (FR-055..FR-057, DDR-0009).

Aggregation and presentation only: every unmet or unmeasured rule of a rated
dimension becomes one item, grouped by closeness to its threshold and ordered
by what fixing it is worth. That worth is **recomputed** with the judge's own
arithmetic (``rating_value``, ``overall_value``), never read off the weight,
because each number is rounded once (ties to even). No narrative, no
cross-dimension interpretation (FR-026 as amended).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from .findings import ValidationError
from .judge import (
    RATING_RULES,
    GatedRating,
    OverallRating,
    Rating,
    RatingAbstention,
    overall_value,
    rating_value,
    within_band,
)
from .redact import redact

GROUPS = ("P0", "P1", "P2")
"""P0 near-miss (unmet, within ``BORDERLINE_BAND``), P1 clear failure, P2 not
measurable yet (the metric abstained)."""

FIX_HINTS: dict[str, str] = {
    # architecture
    "architecture_description_missing": (
        "Add an architecture description (e.g. ARCHITECTURE.md or docs/architecture) "
        "naming the components, their responsibilities and how they connect."
    ),
    "decision_records_missing": (
        "Record significant design decisions as decision records (ADRs) with "
        "context, decision and consequences."
    ),
    "top_level_import_cycles": (
        "Break import cycles between top-level modules: move the shared code into "
        "a lower-level module or invert the dependency behind an interface."
    ),
    "layer_direction_violations": (
        "Make imports point from higher to lower layers only (api -> service -> "
        "data): move what the lower layer needs into it, or pass it in through "
        "an interface the lower layer owns."
    ),
    # requirement-fidelity
    "routes_without_test_share": (
        "Add a test that calls each untested route by its path (or names its "
        "handler), starting with the examples listed."
    ),
    "commits_with_issue_reference_share": (
        "Name the issue or ticket a commit serves in its message (e.g. "
        '"Fixes #12" or "ABC-34"), so each change traces to a request.'
    ),
    "requirement_items_traced_share": (
        "Reference each untraced requirement item (its id, or its scenario text) "
        "from the code or test that implements it, and drop items no longer "
        "intended."
    ),
    "requirements_doc_missing": (
        "Add one requirements document (e.g. PRD.md or docs/requirements.md) "
        "listing what the system must do, with identifiable items."
    ),
    "code_commits_with_docs_share": (
        "Update the affected documentation in the same commit as behavior "
        "changes."
    ),
    # code-quality
    "functions_over_ccn_10_share": (
        "Split the most complex functions into smaller ones, each with a single "
        "responsibility, keeping behavior covered by tests."
    ),
    "max_function_ccn": (
        "Refactor the most complex function: extract branches into named helpers "
        "or replace conditional chains with a lookup or polymorphism."
    ),
    "lint_config_missing": (
        "Add a linter configuration for the project's language and run it in CI."
    ),
    "format_config_missing": (
        "Add a formatter configuration for the project's language and check it "
        "in CI."
    ),
    "type_escapes_per_kloc": (
        "Replace type escapes (Any, type: ignore, @ts-ignore) with precise types; "
        "keep any remaining one with a comment saying why."
    ),
    "todo_without_ticket_share": (
        "Link each TODO/FIXME to a tracked issue, or resolve it."
    ),
    "strict_type_config_missing": (
        "Enable strict mode in the type-checker configuration file (e.g. mypy "
        "strict = true, tsconfig \"strict\": true) and fix what it reports."
    ),
    # security
    "redaction_hits_observed": (
        "Remove the secret-shaped values from the repository, rotate any real "
        "credential, and load secrets from the environment or a secret manager."
    ),
    "sink_hits_observed": (
        "Replace dangerous sinks (eval, shell execution, string-built SQL) with "
        "safe APIs: parameterized queries and argument-list process calls."
    ),
    "lockfile_missing": (
        "Commit the package manager's lockfile so dependency versions are pinned "
        "and reviewable."
    ),
    "cookie_flags_missing_observed": (
        "Set Secure, HttpOnly and SameSite on every session and authentication "
        "cookie."
    ),
    # test-strategy
    "source_files_without_covering_test_share": (
        "Add tests for the source files no test covers, starting with the most "
        "changed ones."
    ),
    "assertion_density_per_test": (
        "Make tests check behavior: assert on results and side effects, not only "
        "that code runs."
    ),
    "test_config_and_ci_missing": (
        "Add a test runner configuration and a CI workflow that runs the tests "
        "on every change."
    ),
    "tests_without_assertions_share": (
        "Add assertions to tests that have none, so each one can fail when "
        "behavior breaks."
    ),
    "skipped_test_share": (
        "Fix and re-enable skipped tests; for any that stays skipped, give the "
        "reason and a tracking issue."
    ),
    "network_calls_in_unit_tests_observed": (
        "Replace real network calls in unit tests with fakes or recorded "
        "responses; keep live calls in a separate integration suite."
    ),
    # blast-radius
    "max_fan_in_changed": (
        "Reduce coupling to the most-imported changed module: split it or put a "
        "stable interface in front of it."
    ),
    "changed_files_in_churn_hotspots_share": (
        "Stabilize churn hotspots: refactor the most frequently changed files and "
        "cover them with tests before further change."
    ),
    "public_symbols_removed": (
        "Deprecate public symbols before removing them, or bump the major version "
        "and document the break."
    ),
    "destructive_migration_ops": (
        "Make schema changes expand-then-contract: add the new structure, migrate "
        "data, and drop the old one in a later release."
    ),
    # reliability
    "swallowed_errors_observed": (
        "Handle or propagate each caught error: log it with context, recover, "
        "or re-raise; if ignoring it is intended, say why in a comment."
    ),
    "outbound_calls_without_timeout_observed": (
        "Give every outbound HTTP or database call a deadline (a timeout or an "
        "abort signal), or route it through a client configured with one."
    ),
    "retries_without_backoff_observed": (
        "Wait between retries with capped, randomized exponential backoff and "
        "limit the attempts."
    ),
    "queries_in_loops_observed": (
        "Fetch the rows in one batched query (IN list, join or bulk API) "
        "instead of one query per loop iteration."
    ),
    # healthcare pack (T047)
    "phi_values_in_test_data_observed": (
        "Replace real-looking SSNs, record numbers and birth dates in test data "
        "with synthetic or documented placeholder values (e.g. 000-00-0000)."
    ),
    "phi_values_in_log_statements_observed": (
        "Stop logging patient identifiers: log an internal reference instead, "
        "or mask the value before it reaches the log."
    ),
    # finance pack (T048)
    "float_money_observed": (
        "Hold money in a decimal type (Decimal, BigDecimal, numeric) or in "
        "integer minor units (cents), never in a binary float."
    ),
    "ledger_tables_without_audit_columns_observed": (
        "Record when and by whom each ledger row was written (created_at, "
        "created_by) on the ledger table itself."
    ),
    "ledger_rows_mutated_observed": (
        "Keep ledger rows append-only: correct an entry by posting a reversing "
        "entry instead of updating or deleting the row."
    ),
}
"""One static engine fix line per declared rule metric (FR-057). Each line
names the real remedy, never a move that only satisfies the metric."""

_METHOD = (
    "per item, the dimension and overall are recomputed with the rating "
    "arithmetic as if that one rule passed (P2: as if the metric were measured "
    "and failed, then passed, giving [low, high]); gain = recomputed minus "
    "current. Gated dimensions use their rules part on both sides (gain_basis "
    "rules); the agent half of a blend is never predicted."
)


@dataclass(frozen=True)
class PlanItem:
    group: str
    dimension: str
    area: str
    metric_name: str
    metric_value: float | int | None
    unavailable_reason: str | None
    comparison: str
    threshold: float
    weight: int
    computed_from: tuple[str, ...]
    dimension_gain: int | tuple[int, int]
    overall_gain: int | tuple[int, int]
    gain_basis: str

    def sort_key(self) -> tuple:
        gain = self.overall_gain
        high = gain[1] if isinstance(gain, tuple) else gain
        return (-high, self.dimension, self.metric_name)

    def to_dict(self) -> dict[str, Any]:
        return {
            "group": self.group,
            "dimension": self.dimension,
            "area": self.area,
            "metric_name": self.metric_name,
            "metric_value": self.metric_value,
            "unavailable_reason": self.unavailable_reason,
            "comparison": self.comparison,
            "threshold": self.threshold,
            "weight": self.weight,
            "computed_from": list(self.computed_from),
            "dimension_gain": _gain(self.dimension_gain),
            "overall_gain": _gain(self.overall_gain),
            "gain_basis": self.gain_basis,
            "fix": {"text": FIX_HINTS[self.metric_name], "source": "engine"},
        }


@dataclass(frozen=True)
class ImprovementPlan:
    items: tuple[PlanItem, ...]
    """Already in group order, then gain order (see :meth:`PlanItem.sort_key`)."""
    abstained: tuple[tuple[str, str, str, tuple[tuple[str, str], ...]], ...]
    """Per dimension without a rules rating: (dimension, reason_code, reason,
    unmeasured rules as (metric_name, reason)) — FR-059: what the repo lacks."""

    def to_dict(self) -> dict[str, Any]:
        return {
            "groups": {
                group: [item.to_dict() for item in self.items if item.group == group]
                for group in GROUPS
            },
            "abstained": [
                {
                    "dimension": d,
                    "reason_code": code,
                    "reason": reason,
                    **(
                        {
                            "unmeasured": [
                                {"metric_name": n, "reason": r, "fix": FIX_HINTS[n]}
                                for n, r in unmeasured
                            ]
                        }
                        if unmeasured
                        else {}
                    ),
                }
                for d, code, reason, unmeasured in self.abstained
            ],
            "method": _METHOD,
        }

    def item_keys(self) -> tuple[tuple[str, str], ...]:
        """Each item's identity, ``(dimension, metric_name)``: the name an
        agent suggestion is attached by (FR-057). Unique within a plan."""
        return tuple((item.dimension, item.metric_name) for item in self.items)


def improvement_plan(
    ratings: Sequence[Rating | RatingAbstention | GatedRating],
    overall: OverallRating | RatingAbstention,
) -> ImprovementPlan:
    """Every unmet or unmeasured rule of every rated dimension, with its gain."""
    # The rules value each contributor counts with in the overall: its final
    # value, except a gated dimension's own items, which use the rules part.
    contributors = {
        item.dimension: item.value
        for item in ratings
        if type(item) in (Rating, GatedRating)
    }
    items: list[PlanItem] = []
    abstained: list[tuple[str, str, str, tuple[tuple[str, str], ...]]] = []
    for item in ratings:
        rules = item.rules if type(item) is GatedRating else item
        if type(rules) is RatingAbstention:
            abstained.append(
                (
                    rules.dimension,
                    rules.reason_code,
                    rules.reason,
                    rules.unavailable_metrics,
                )
            )
            continue
        gated = type(item) is GatedRating
        basis = dict(contributors, **{rules.dimension: rules.value})
        current_overall = (
            overall_value(list(basis.values())) if gated else overall.value
        )
        items.extend(_items(rules, basis, current_overall, gated))
    ordered = sorted(items, key=lambda i: (GROUPS.index(i.group), *i.sort_key()))
    return ImprovementPlan(tuple(ordered), tuple(abstained))


def _items(
    rating: Rating, basis: dict[str, int], current_overall: int, gated: bool
) -> list[PlanItem]:
    earned = sum(i.earned_weight for i in rating.inputs)
    available = sum(i.weight for i in rating.inputs)
    rules = RATING_RULES[rating.dimension]

    def gains(add_earned: int, add_available: int) -> tuple[int, int]:
        value = rating_value(earned + add_earned, available + add_available)
        after = dict(basis, **{rating.dimension: value})
        return (
            value - rating.value,
            overall_value(list(after.values())) - current_overall,
        )

    found: list[PlanItem] = []
    for item in rating.inputs:
        if item.passed:
            continue
        dimension_gain, overall_gain = gains(item.weight, 0)
        found.append(
            PlanItem(
                group="P0" if within_band(item.metric_value, item.threshold) else "P1",
                dimension=rating.dimension,
                area=item.area,
                metric_name=item.metric_name,
                metric_value=item.metric_value,
                unavailable_reason=None,
                comparison=item.comparison,
                threshold=item.threshold,
                weight=item.weight,
                computed_from=item.computed_from,
                dimension_gain=dimension_gain,
                overall_gain=overall_gain,
                gain_basis="rules" if gated else "final",
            )
        )
    for name, reason in rating.unavailable_metrics:
        rule = rules[name]
        low = gains(0, rule.weight)
        high = gains(rule.weight, rule.weight)
        found.append(
            PlanItem(
                group="P2",
                dimension=rating.dimension,
                area=rule.area,
                metric_name=name,
                metric_value=None,
                unavailable_reason=reason,
                comparison=rule.comparison,
                threshold=rule.threshold,
                weight=rule.weight,
                computed_from=(),
                dimension_gain=(low[0], high[0]),
                overall_gain=(low[1], high[1]),
                gain_basis="rules" if gated else "final",
            )
        )
    return found


MAX_SUGGESTION_CHARS = 1000
"""Upper bound on one agent suggestion, after surrounding whitespace is
stripped: a fix line, not an essay."""

MAX_IMPROVEMENTS = 500
"""Bound on a submitted ``improvements`` list, like ``MAX_FINDINGS``: a
caller-sized list must not size the error message."""

_IMPROVEMENT_FIELDS = ("dimension", "metric_name", "suggestion")


@dataclass(frozen=True)
class ImprovementError:
    """One rejection reason for one submitted improvement."""

    index: int
    """Position in the submitted list, or -1 for the list itself."""
    field: str | None
    reason: str

    def __str__(self) -> str:
        where = "improvements" if self.index < 0 else f"improvements[{self.index}]"
        return f"{where}{'.' + self.field if self.field else ''}: {self.reason}"


class ImprovementValidationError(ValidationError):
    """A :class:`ValidationError` (so both adapters already report it as one)
    naming every rejected improvement at once."""

    def __init__(self, errors: list[ImprovementError]) -> None:
        super().__init__(errors)
        self.args = (
            f"{len(self.errors)} improvement error(s): "
            + "; ".join(str(e) for e in self.errors),
        )


def validate_improvements(
    value: object, plan: ImprovementPlan | None
) -> dict[tuple[str, str], str]:
    """The agent's suggestions keyed by plan-item identity (FR-057).

    ``plan`` is the plan of the score the report renders, or ``None`` when the
    report has no score. Fails closed: any unknown, duplicate or malformed
    entry raises :class:`ImprovementValidationError` naming all of them.
    Agent-supplied names are redacted before they are echoed; a suggestion is
    never echoed.
    """
    if not isinstance(value, list):
        _reject(
            -1, None, "must be a list of {dimension, metric_name, suggestion} objects"
        )
    if len(value) > MAX_IMPROVEMENTS:
        _reject(
            -1, None, f"has {len(value)} items, exceeding the {MAX_IMPROVEMENTS} limit"
        )
    if value and plan is None:
        _reject(
            -1,
            None,
            "this report has no improvement plan (it does not cover every "
            "declared dimension), so no item can be named",
        )
    known = plan.item_keys() if plan is not None else ()
    errors: list[ImprovementError] = []
    accepted: dict[tuple[str, str], str] = {}
    for index, raw in enumerate(value):
        if not isinstance(raw, dict):
            errors.append(
                ImprovementError(
                    index, None, "must be an object with dimension, metric_name "
                    "and suggestion"
                )
            )
            continue
        problems = [
            ImprovementError(
                index,
                _echo(key),
                "unknown key; only dimension, metric_name and suggestion are accepted",
            )
            for key in raw
            if key not in _IMPROVEMENT_FIELDS
        ]
        for field in _IMPROVEMENT_FIELDS:
            if field not in raw:
                problems.append(ImprovementError(index, field, "missing"))
            elif not isinstance(raw[field], str):
                problems.append(ImprovementError(index, field, "must be a string"))
        suggestion = raw.get("suggestion")
        if isinstance(suggestion, str):
            suggestion = suggestion.strip()
            if not suggestion:
                problems.append(
                    ImprovementError(index, "suggestion", "must not be empty")
                )
            elif len(suggestion) > MAX_SUGGESTION_CHARS:
                problems.append(
                    ImprovementError(
                        index,
                        "suggestion",
                        f"must be at most {MAX_SUGGESTION_CHARS} characters, "
                        f"got {len(suggestion)}",
                    )
                )
        if problems:
            errors.extend(problems)
            continue
        identity = (raw["dimension"], raw["metric_name"])
        if identity not in known:
            items = ", ".join(f"{d}/{m}" for d, m in known) or "none"
            errors.append(
                ImprovementError(
                    index,
                    None,
                    f"{_echo('/'.join(identity))} is not an item of the "
                    f"improvement plan; items: {items}",
                )
            )
        elif identity in accepted:
            errors.append(
                ImprovementError(
                    index,
                    None,
                    f"duplicate: {_echo('/'.join(identity))} is already named by "
                    "an earlier entry",
                )
            )
        else:
            accepted[identity] = suggestion
    if errors:
        raise ImprovementValidationError(errors)
    return accepted


def _reject(index: int, field: str | None, reason: str) -> None:
    raise ImprovementValidationError([ImprovementError(index, field, reason)])


def _echo(value: object) -> str:
    """An agent-supplied name, safe to put in an error message."""
    text = redact(str(value))
    return text if len(text) <= 120 else text[:120] + "…"


def _gain(value: int | tuple[int, int]) -> int | list[int]:
    return list(value) if isinstance(value, tuple) else value


__all__ = [
    "FIX_HINTS",
    "GROUPS",
    "MAX_IMPROVEMENTS",
    "MAX_SUGGESTION_CHARS",
    "ImprovementError",
    "ImprovementPlan",
    "ImprovementValidationError",
    "PlanItem",
    "improvement_plan",
    "validate_improvements",
]
