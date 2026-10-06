"""``write_report`` — validated findings rendered into one self-contained HTML
document, written into the **evaluated** repository's ``reports/`` (FR-014,
FR-017, FR-018, FR-018a/b).

Three properties are structural here rather than conventional, because each of
them is a rule that is easy to satisfy today and easy to lose in a later edit:

* **Nothing is written until validation passes.** ``validate_findings`` runs
  before the document is even rendered, and it raises; there is no code path
  from a rejected submission to an open file descriptor (AC #9).
* **A coverage score cannot be rendered without its named miss list.**
  :func:`_coverage_entry` is the only function in this module that formats a
  score, and it takes the miss tuple as a required argument and always emits
  it. The per-pack ``coverage_score`` field is deliberately never rendered —
  the only score source is :class:`CoverageSummary`, which carries its misses
  inside it (DDR-0004, FR-016a, AC #6).
* **Every caller-supplied string is escaped at one chokepoint.**
  :class:`_Ctx.esc` is the only way text reaches the document; no Markdown
  subset, no "safe" HTML passthrough. The text being rendered was written by an
  LLM about source code and routinely contains angle brackets (AC #12).

The document requests nothing from the network: CSS is inlined, there are no
scripts, no fonts and no images. Grouping uses ``<details>``, which is inert
HTML (AC #2, FR-018).
"""

from __future__ import annotations

import html
import json
import os
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from easy_verifier.core.assessment import (
    Assessment,
    AssessmentAbsence,
    Divergence,
    DivergenceAbsence,
)
from easy_verifier.core.context import RepoPathError, _resolved_repo
from easy_verifier.core.findings import Finding, ValidationError, validate_findings
from easy_verifier.core.improve import (
    GROUPS,
    ImprovementPlan,
    validate_improvements,
)
from easy_verifier.core.judge import (
    AREAS,
    BORDERLINE_BAND,
    PACK_FLOORS,
    PROJECT_DEFAULT,
    RATING_RULES,
    GatedRating,
    OverallRating,
    Rating,
    RatingAbstention,
    _measured_share,
)
from easy_verifier.core.models import (
    CombinedPack,
    CoverageSummary,
    EvidencePack,
    ReportResult,
    SourceMiss,
)
from easy_verifier.core.redact import redact
from easy_verifier.core.roles import parse_agent_input
from easy_verifier.core.score import ScoreResult, score_packs
from easy_verifier.dimensions import dimension_names

REPORTS_DIRNAME = "reports"

SENSITIVITY_ADVISORY = (
    "Sensitivity notice: this report is written inside the evaluated repository, "
    "so it can be committed to version control, attached to a ticket, or pasted "
    "into a pull request — and in MCP mode the same evidence also reaches the "
    "calling agent, which may be a hosted model outside your control. Secrets "
    "detected while gathering evidence are replaced by non-reversible "
    "fingerprints before they reach this document, but excerpts still quote real "
    "source code and file paths from this repository. Review before sharing it "
    "anywhere either destination can carry it."
)
"""NFR-011 / AC #15. It names the two real exposures — the report travelling out
of the repo, and pack content reaching a hosted model — rather than merely
asserting that redaction happened."""

MAX_FILENAME_ATTEMPTS = 1000
"""Bound on the never-overwrite retry loop, so a pathological directory fails
loudly instead of spinning."""


class ReportWriteError(OSError):
    """The report could not be written. A clear, actionable message — not a
    traceback out of ``open()``. Covers the read-only mount case (NFR-013)."""


def _scoreable(names: tuple[str, ...]) -> bool:
    """Every dimension in canonical order, then only active optional packs
    (T047): the set ``score`` rates, so the report shows the same score."""
    core = dimension_names()
    return names[: len(core)] == core and set(names[len(core) :]) <= set(PACK_FLOORS)


def write_report(
    findings: list[dict[str, Any]] | str | bytes,
    packs: CombinedPack,
    target_repo: str | Path,
    *,
    agent_input: object | None = None,
) -> ReportResult:
    """Validate `findings` against `packs`, then render one HTML report into
    ``<target_repo>/reports/``.

    `packs` is the combined multi-dimension pack (DDR-0004): its slots supply
    the per-dimension evidence that validation resolves citations against, and
    its :class:`CoverageSummary` is the only source of a rendered score.

    Raises :class:`easy_verifier.core.findings.ValidationError` — before
    anything is created on disk — if any finding is unevidenced, and
    :class:`ReportWriteError` if the target's ``reports/`` cannot be written.
    """
    repo = _resolved_repo(target_repo)

    pack_map: dict[str, EvidencePack] = {
        slot.dimension: slot.pack for slot in packs.slots if slot.pack is not None
    }

    # Gate first. Nothing below this line may run for a rejected submission —
    # validate_findings raises, so AC #9 holds by control flow, not by a check.
    validated = validate_findings(findings, pack_map)
    # T028: the same agent input that shaped `packs` also carries any gate
    # evaluations; they are validated by `score_packs` before anything is
    # written, and their rationale never reaches the document.
    document_input = (
        parse_agent_input(agent_input) if agent_input is not None else {}
    )

    reports_dir = repo / REPORTS_DIRNAME
    first_write = not _has_existing_reports(reports_dir)

    ctx = _Ctx(repo=repo)
    score = (
        score_packs(
            packs, validated.by_dimension, document_input.get("gate_evaluations")
        )
        if _scoreable(tuple(slot.dimension for slot in packs.slots))
        else None
    )
    # T066: agent suggestions name items of the plan this report renders --
    # one plan, computed once -- and are rejected before anything is written.
    plan = score.improvement_plan if score is not None else None
    improvements = (
        validate_improvements(document_input["improvements"], plan)
        if "improvements" in document_input
        else {}
    )
    # T069: the agent's summary paragraph, also rejected before any write.
    agent_summary = (
        _validate_agent_summary(document_input["summary"])
        if "summary" in document_input
        else None
    )
    document = _render_document(
        ctx,
        validated.by_dimension,
        packs,
        score,
        plan,
        improvements,
        agent_summary,
        first_write=first_write,
    )

    written = _write_new_file(reports_dir, _filename(packs), document)

    return ReportResult(
        path=written.relative_to(repo).as_posix(),
        absolute_path=str(written),
        advisory=SENSITIVITY_ADVISORY if first_write else None,
    )


# ---------------------------------------------------------------------------
# Escaping + path normalization chokepoint
# ---------------------------------------------------------------------------


class _Ctx:
    """The single door text and paths pass through on the way into the document.

    Holding the repo root here is what lets the same object enforce both
    escaping (AC #12) and FR-021c path normalization (AC #11): a renderer that
    wants to emit anything caller-supplied has to call one of these two methods.
    """

    def __init__(self, repo: Path) -> None:
        self.repo = repo
        self._repo_str = str(repo)

    def esc(self, value: object) -> str:
        """HTML-escape any caller-supplied value, first removing the target
        repo's own absolute prefix.

        The prefix scrub matters inside the container, where the repo is mounted
        at a path like ``/workspace``: an absolute path embedded in prose or in
        an excerpt is not a path *field* and would otherwise slip past
        :meth:`path` (FR-021c).
        """
        text = "" if value is None else str(value)
        if self._repo_str and self._repo_str != os.sep:
            text = text.replace(self._repo_str + os.sep, "").replace(
                self._repo_str, "."
            )
        return html.escape(text, quote=True)

    def agent_text(self, value: object) -> str:
        """Escape free text the *calling agent* wrote, redacting it first.

        Excerpts are redacted at the evidence layer (T004) before they ever
        reach a pack. Finding titles, details and suggestions are not: they are
        prose the calling agent composed, and an agent describing a hardcoded
        credential routinely quotes it ("the key AKIA... must be rotated").
        That text used to land verbatim in a file written into the evaluated
        repository -- the one artifact this system creates whose own advisory
        says it will be committed, attached to tickets and pasted into pull
        requests. The pack layer redacting is not enough once a new egress
        path is added; this is that path.
        """
        return self.esc(redact("" if value is None else str(value)))

    def path(self, value: str | None) -> str:
        """Render a path field as repo-relative, escaped.

        Containment is decided the way the rest of this codebase decides it —
        ``resolve()`` then ``is_relative_to`` (``context.read_source``,
        ``scope._is_contained``) — so a symlinked target repo resolves the same
        way for the rendered path as it does for the write location. A path we
        cannot place inside the repo is reduced to its basename rather than
        printed: an unplaceable absolute path is exactly the container-internal
        leak FR-021c forbids.
        """
        if not value:
            return self.esc(value)
        candidate = Path(value)
        if not candidate.is_absolute():
            # A relative path that climbs out of the repo describes a location
            # this engine never read; printing it verbatim would still be a
            # location outside the repo on the reader's screen.
            if ".." in candidate.parts:
                return self.esc("…/" + candidate.name)
            return self.esc(candidate.as_posix())
        try:
            resolved = candidate.resolve()
        except OSError:
            return self.esc("…/" + candidate.name)
        if resolved.is_relative_to(self.repo):
            return self.esc(resolved.relative_to(self.repo).as_posix())
        return self.esc("…/" + candidate.name)


# ---------------------------------------------------------------------------
# Filename + write
# ---------------------------------------------------------------------------


def _filename(packs: CombinedPack) -> str:
    """``evidence-report-<scope>-<UTC to the microsecond>.html`` (FR-018b).

    Self-describing (scope + instant) and sub-second, so two reports written in
    the same second do not collide on the name. Collision is still handled at
    the filesystem, not here — see :func:`_write_new_file`.
    """
    scopes = {slot.pack.scope for slot in packs.slots if slot.pack is not None}
    if len(scopes) == 1:
        scope = next(iter(scopes))
    elif scopes:
        scope = "mixed"
    else:
        scope = "unknown"
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S-%fZ")
    return f"evidence-report-{_slug(scope)}-{stamp}.html"


def _slug(value: str) -> str:
    safe = "".join(c if c.isalnum() or c in "-_" else "-" for c in value)
    return safe.strip("-") or "unknown"


def _has_existing_reports(reports_dir: Path) -> bool:
    try:
        return any(reports_dir.glob("*.html"))
    except OSError:
        return False


def _write_new_file(reports_dir: Path, filename: str, document: str) -> Path:
    """Create the report, never clobbering an existing file (AC #5).

    ``O_CREAT | O_EXCL`` makes that structural: the kernel refuses the open if
    the name is taken, so there is no check-then-write window two concurrent
    writers could both pass. A taken name produces a new name, never a
    truncation of someone else's report.
    """
    _guard_reports_dir(reports_dir)

    try:
        reports_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise ReportWriteError(
            f"cannot create the reports directory {redact(str(reports_dir))}: "
            f"{exc.strerror}. If the target repository is mounted read-only "
            "(the container case), mount its reports/ directory writable."
        ) from exc

    stem, suffix = filename[: -len(".html")], ".html"
    for attempt in range(MAX_FILENAME_ATTEMPTS):
        name = filename if attempt == 0 else f"{stem}-{attempt + 1}{suffix}"
        candidate = reports_dir / name
        try:
            fd = os.open(candidate, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError:
            continue
        except OSError as exc:
            raise ReportWriteError(
                f"cannot write the report into {redact(str(reports_dir))}: "
                f"{exc.strerror}. If the target repository is mounted read-only "
                "(the container case), mount its reports/ directory writable."
            ) from exc
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(document)
        return candidate

    raise ReportWriteError(
        f"could not find an unused report filename in {redact(str(reports_dir))} "
        f"after {MAX_FILENAME_ATTEMPTS} attempts"
    )


def _guard_reports_dir(reports_dir: Path) -> None:
    """NFR-007: write nothing outside the target repo's ``reports/``.

    ``reports/`` being a symlink out of the repository is the one way the write
    location can leave the tree, and it is checked the same way every other
    containment check in this codebase is.
    """
    repo = reports_dir.parent
    try:
        resolved = reports_dir.resolve()
    except OSError as exc:
        raise ReportWriteError(
            f"reports directory could not be resolved: {exc.strerror}"
        ) from exc
    if not resolved.is_relative_to(repo.resolve()):
        raise ReportWriteError(
            "the target repository's reports/ resolves outside the repository; "
            "refusing to write there (NFR-007)"
        )


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _render_document(
    ctx: _Ctx,
    by_dimension: dict[str, tuple[Finding, ...]],
    packs: CombinedPack,
    score: ScoreResult | None,
    plan: ImprovementPlan | None,
    improvements: dict[tuple[str, str], str],
    agent_summary: str | None = None,
    *,
    first_write: bool,
) -> str:
    generated = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    finding_count = sum(len(v) for v in by_dimension.values())
    context_warnings = _context_warnings(packs)
    nothing_rated = score is not None and all(
        type(rating) is RatingAbstention for rating in score.ratings
    )

    parts = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        f"<title>Evidence report — {ctx.esc(ctx.repo.name)}</title>",
        f"<style>{_CSS}</style>",
        "</head>",
        "<body>",
        _render_header(ctx, packs, generated, finding_count),
        _render_advisory(ctx, first_write=first_write),
        _render_summary(
            ctx,
            score,
            plan,
            agent_summary,
            {s.dimension: s.pack.scope for s in packs.slots if s.pack is not None},
            context_warning_count=len(context_warnings),
        ),
        _render_improvement_plan(
            ctx, plan, improvements, nothing_rated=nothing_rated
        )
        if plan
        else "",
        _render_unknowns(ctx, context_warnings, score),
        _render_score_panel(ctx, score),
        _render_coverage(ctx, packs.coverage),
        _render_dimensions(ctx, by_dimension, packs),
        _render_footer(),
        "</body>",
        "</html>",
    ]
    return "\n".join(parts) + "\n"


def _render_header(
    ctx: _Ctx, packs: CombinedPack, generated: str, finding_count: int
) -> str:
    dimensions = ", ".join(slot.dimension for slot in packs.slots) or "none"
    modes = sorted({slot.pack.mode for slot in packs.slots if slot.pack is not None})
    return (
        '<header class="header">'
        "<h1>Evidence report</h1>"
        '<dl class="meta">'
        f"<dt>Repository</dt><dd>{ctx.esc(ctx.repo.name)}</dd>"
        f"<dt>Generated</dt><dd>{ctx.esc(generated)}</dd>"
        f"<dt>Dimensions</dt><dd>{ctx.esc(dimensions)}</dd>"
        f"<dt>Mode</dt><dd>{ctx.esc(', '.join(modes) or 'unknown')}</dd>"
        f"<dt>Budget model</dt><dd>{ctx.esc(packs.budget_model)}</dd>"
        f"<dt>Findings</dt><dd>{ctx.esc(finding_count)}</dd>"
        "</dl>"
        '<p class="disclaimer">This engine performs no inference. Ratings are '
        "declared arithmetic over the cited metrics; every narrative claim below "
        "was made by the calling agent and is shown next to its evidence.</p>"
        "</header>"
    )


_ADVISORY_LINE = (
    "This report quotes source code and file paths from this repository: "
    "review it before sharing."
)
"""The share notice's one visible line (FR-065); the full notice is folded."""


def _render_advisory(ctx: _Ctx, *, first_write: bool) -> str:
    marker = (
        "This is the first report written into this repository's reports/ directory."
        if first_write
        else ""
    )
    return (
        '<section class="advisory"><h2>Before you share this report</h2>'
        f"<details><summary>{ctx.esc(_ADVISORY_LINE)}</summary>"
        f"<p>{ctx.esc(SENSITIVITY_ADVISORY)}</p></details>"
        f'<p class="first-write">{ctx.esc(marker)}</p></section>'
    )


MAX_AGENT_SUMMARY_CHARS = 2000
"""Upper bound on the agent's summary paragraph, after surrounding whitespace
is stripped (FR-064): a paragraph, not a second report."""

SUMMARY_FOCUS_LIMIT = 3
"""At most this many improvement-plan items open the report (FR-063)."""

_METRIC_TEXT: dict[str, str] = {
    # architecture
    "architecture_description_missing": "no architecture description",
    "decision_records_missing": "no decision records (ADRs)",
    "top_level_import_cycles": "import cycles between top-level modules",
    "layer_direction_violations": "imports from a lower to a higher layer",
    # requirement-fidelity
    "routes_without_test_share": "share of routes no test calls",
    "commits_with_issue_reference_share": "share of commits naming an issue",
    "requirement_items_traced_share": (
        "share of requirement items traced to code or tests"
    ),
    "requirements_doc_missing": "no requirements document",
    "code_commits_with_docs_share": "share of code commits that also update docs",
    # code-quality
    "functions_over_ccn_10_share": "share of functions with complexity over 10",
    "max_function_ccn": "highest function complexity",
    "lint_config_missing": "no linter configuration",
    "format_config_missing": "no formatter configuration",
    "type_escapes_per_kloc": "type escapes per 1,000 lines",
    "todo_without_ticket_share": "share of TODOs without a ticket",
    "strict_type_config_missing": "type checker not in strict mode",
    # security
    "redaction_hits_observed": "secret-shaped values in the code",
    "sink_hits_observed": "dangerous calls (eval, shell, string-built SQL)",
    "lockfile_missing": "no dependency lockfile",
    "cookie_flags_missing_observed": "cookies without Secure/HttpOnly/SameSite",
    # test-strategy
    "source_files_without_covering_test_share": (
        "share of source files no test covers"
    ),
    "assertion_density_per_test": "assertions per test",
    "test_config_and_ci_missing": "no test configuration and CI workflow",
    "tests_without_assertions_share": "share of tests without assertions",
    "skipped_test_share": "share of skipped tests",
    "network_calls_in_unit_tests_observed": "real network calls in unit tests",
    # blast-radius
    "max_fan_in_changed": "most imports of one changed module (fan-in)",
    "changed_files_in_churn_hotspots_share": (
        "share of changed files in churn hotspots"
    ),
    "public_symbols_removed": "public symbols removed",
    "destructive_migration_ops": "destructive migration operations",
    # reliability
    "swallowed_errors_observed": "error handlers that do nothing",
    "outbound_calls_without_timeout_observed": "outbound calls with no timeout",
    "retries_without_backoff_observed": "retries with no backoff",
    "queries_in_loops_observed": "database queries inside loops",
    # healthcare pack (T047)
    "phi_values_in_test_data_observed": "PHI-shaped values in test data",
    "phi_values_in_log_statements_observed": "PHI-shaped values in log statements",
    # finance pack (T048)
    "float_money_observed": "money fields held in binary floating point",
    "ledger_tables_without_audit_columns_observed": (
        "ledger tables with no audit column"
    ),
    "ledger_rows_mutated_observed": "updates or deletes of ledger rows",
}
"""One plain description per declared rule metric, for the summary (FR-063).
Presentation only."""

_SOURCE_TEXT: dict[str, str | None] = {
    "readme": "README",
    "architecture-doc": "architecture doc",
    "decision-record": "decision records",
    "requirements-doc": "requirements doc",
    "spec-doc": "spec doc",
    "contributing-guide": "contributing guide",
    "lint-config": "linter config",
    "format-config": "formatter config",
    "package-manifest": "package manifest",
    "lockfile": "lockfile",
    "auth-code": "auth code",
    "container-config": "container config",
    "ci-workflow": "CI workflow",
    "credential-file": "credential file",
    "test-config": "test config",
    "test-file": "test files",
    # Derived evidence, not something the user adds: not named in the summary.
    "git history (out of scope for v1)": None,
    "source-to-test correspondence for files in the active scope": None,
    "source files with import statements": None,
    "route handlers in source files": None,
    "test files": "test files",
    "git history": None,
    "referencing files (textual reference search over repository code)": None,
    "git co-change history (local `git log --name-only`)": None,
    "repository change hotspots (local git history)": None,
    "source files of a registry language": None,
    "outbound HTTP client calls in source files": None,
    "database access calls in source files": None,
    "test data files (the pack's test_data_paths)": "test data files",
    "log statements in source files (the pack's log_calls)": None,
    "money-named field declarations (the pack's money_declarations)": None,
    "ledger, transaction or payment tables (the pack's ledger_declarations)": None,
}
"""Plain name per declared sought source (every dimension's
``sources_sought``), for the could-not-evaluate lines (FR-063). ``None`` marks
derived evidence the user cannot add. A missing source not declared here is
counted, never quoted."""

_NOT_RATED_TEXT = {
    "no_static_rule": "rated only by the calling agent (MCP evaluate gate)",
}
"""Short text per non-evidence-lack abstention reason; others use the judge's
own reason."""

_CHANGES_ONLY = {
    "blast-radius": (
        "measured only on a change: run with --scope changes "
        "(a commit, range or branch)"
    ),
}
"""Dimensions whose rules read a change; at project scope the line says how
to run them instead of listing what was not measured."""


class SummaryValidationError(ValidationError):
    """A rejected agent ``summary`` (FR-064). A :class:`ValidationError`, so
    both adapters already report it as one; the text is never echoed."""

    def __init__(self, reason: str) -> None:
        super().__init__([])
        self.args = (f"summary: {reason}",)


def _validate_agent_summary(value: object) -> str:
    """The agent's summary paragraph, stripped; fails closed (FR-064)."""
    if not isinstance(value, str):
        raise SummaryValidationError("must be a string")
    text = value.strip()
    if not text:
        raise SummaryValidationError("must not be empty")
    if len(text) > MAX_AGENT_SUMMARY_CHARS:
        raise SummaryValidationError(
            f"must be at most {MAX_AGENT_SUMMARY_CHARS} characters, got {len(text)}"
        )
    return text


def _render_summary(
    ctx: _Ctx,
    score: ScoreResult | None,
    plan: ImprovementPlan | None,
    agent_summary: str | None,
    scopes: dict[str, str],
    *,
    context_warning_count: int = 0,
) -> str:
    """FR-063/FR-064: the report's opening section. Templated sentences built
    from the score only (FR-026); the agent's paragraph, when given, follows
    it labelled ``agent`` and changes nothing above it."""
    parts = ['<section class="summary"><h2>Summary</h2>']
    if score is None or plan is None:
        parts.append(
            '<p class="summary-overall">No score in this report: it does not '
            "cover every declared dimension.</p>"
        )
    else:
        parts.append(_summary_overall(ctx, score))
        parts.append(_summary_evidence(ctx, score, context_warning_count))
        if type(score.overall) is OverallRating:
            parts.append(_summary_focus(ctx, plan))
        parts.append(_summary_missing(ctx, score.warnings, scopes))
    if agent_summary is not None:
        # Agent prose is a new egress path: redact, then escape (DDR-0001).
        parts.append(
            f'<p class="summary-agent">{ctx.agent_text(agent_summary)} '
            '<span class="fix-source fix-source-agent">agent</span></p>'
        )
    parts.append("</section>")
    return "".join(parts)


def _summary_overall(ctx: _Ctx, score: ScoreResult) -> str:
    samples = {item["dimension"]: item for item in score.samples}
    warned = {warning["dimension"] for warning in score.warnings}
    rated: list[str] = []
    not_rated: list[str] = []
    for rating in score.ratings:
        if type(rating) is RatingAbstention:
            if rating.dimension not in warned:
                reason = _NOT_RATED_TEXT.get(rating.reason_code, rating.reason)
                not_rated.append(f"{rating.dimension} — {reason}")
            continue
        label = f"{rating.dimension} {rating.value}"
        if type(rating) is GatedRating:
            label += (
                " (agent-rated)"
                if rating.is_agent_rated
                else " (blended with an agent evaluation)"
            )
        sample = samples.get(rating.dimension)
        if sample is not None:
            label += (
                f" (sample: {sample['files_read']:,} of "
                f"{sample['files_in_scope']:,} files)"
            )
        rated.append(label)
    total = len(score.ratings)
    if type(score.overall) is OverallRating:
        head = (
            f"Overall <strong>{ctx.esc(score.overall.value)}/100</strong> — "
            f"{len(rated)} of {total} dimensions rated: {ctx.esc(', '.join(rated))}."
        )
    else:
        head = f"Overall: no number — none of the {total} dimensions could be rated."
    css = (
        "summary-overall"
        if type(score.overall) is OverallRating
        else "summary-overall notice notice-abstain"
    )
    line = f'<p class="{css}">{head}</p>'
    if not_rated:
        line += f"<p>Not rated: {ctx.esc('; '.join(not_rated))}.</p>"
    return line


def _summary_evidence(
    ctx: _Ctx, score: ScoreResult, context_warning_count: int
) -> str:
    """FR-065: how much evidence stands behind the numbers, as counts only --
    rated dimensions, the lowest measured rule-weight share among rated and
    insufficient-weight dimensions (when any is known), and warnings."""
    rated = sum(type(rating) is not RatingAbstention for rating in score.ratings)
    shares = []
    for rating in score.ratings:
        rules = rating.rules if type(rating) is GatedRating else rating
        if type(rules) is Rating and RATING_RULES[rules.dimension]:
            share = _measured_share(rules.dimension, rules.unavailable_metrics)
        else:
            share = rules.measured_share
        if share is not None:
            shares.append((share, rules.dimension))
    parts = [f"{rated} of {len(score.ratings)} dimensions rated"]
    if shares:
        share, dimension = min(shares, key=lambda pair: pair[0])
        parts.append(f"lowest measured rule weight {share * 100:.0f}% ({dimension})")
    warnings = len(score.warnings) + context_warning_count
    parts.append(
        f"{warnings} warning{'s' if warnings != 1 else ''} — see What we "
        "couldn't measure"
        if warnings
        else "no warnings"
    )
    text = "Evidence: " + "; ".join(parts) + "."
    return f'<p class="summary-evidence">{ctx.esc(text)}</p>'


def _summary_focus(ctx: _Ctx, plan: ImprovementPlan) -> str:
    focus = [item for item in plan.items if item.group in ("P0", "P1")]
    if not focus:
        unmeasured = len(plan.items)
        if not unmeasured:
            return '<p class="no-gaps">No gaps: every measured rule is met.</p>'
        return (
            f"<p>No measured rule fails; {unmeasured} "
            f"rule{'s' if unmeasured != 1 else ''} could not be measured — see "
            "the improvement plan.</p>"
        )
    rows = "".join(
        _summary_focus_item(ctx, item) for item in focus[:SUMMARY_FOCUS_LIMIT]
    )
    return f'<h3>Focus on these first</h3><ol class="summary-focus">{rows}</ol>'


def _summary_focus_item(ctx: _Ctx, item) -> str:
    rule = RATING_RULES[item.dimension][item.metric_name]
    worth = (
        f"{item.overall_gain:+d} overall ({item.dimension} {item.dimension_gain:+d}"
        f"{', rules part' if item.gain_basis == 'rules' else ''})"
    )
    standard = _render_citation(ctx, rule.metric_citation[0])
    if (
        rule.threshold_citation != PROJECT_DEFAULT
        and rule.threshold_citation not in rule.metric_citation
    ):
        standard += f"; threshold: {_render_citation(ctx, rule.threshold_citation)}"
    return (
        f"<li><strong>{ctx.esc(item.dimension)}</strong>: "
        f"{ctx.esc(_METRIC_TEXT[item.metric_name])} — now "
        f"{ctx.esc(_number(item.metric_value))}, rule "
        f"{ctx.esc(item.comparison.replace('_', ' '))} "
        f"{ctx.esc(_number(item.threshold))}; worth {ctx.esc(worth)}. "
        f"Standard: {standard}</li>"
    )


def _summary_missing(
    ctx: _Ctx, warnings: list[dict[str, Any]], scopes: dict[str, str]
) -> str:
    if not warnings:
        return ""
    lines = []
    for warning in warnings:
        dimension = warning["dimension"]
        if dimension in _CHANGES_ONLY and scopes.get(dimension) == "project":
            text = _CHANGES_ONLY[dimension]
        else:
            text = _missing_text(warning)
        lines.append(
            f"<li><strong>{ctx.esc(dimension)}</strong>: {ctx.esc(text)}</li>"
        )
    return (
        "<h3>Could not evaluate — add what each needs</h3>"
        f'<ul class="summary-missing">{"".join(lines)}</ul>'
    )


def _missing_text(warning: dict[str, Any]) -> str:
    """Plain names of missing declared sources, then counts; never a raw
    source string or reason."""
    sources = [miss["source"] for miss in warning["sources_missing"]]
    names = [_SOURCE_TEXT[s] for s in sources if _SOURCE_TEXT.get(s)]
    other = sum(1 for s in sources if s not in _SOURCE_TEXT)
    details = []
    if names:
        details.append(
            "no "
            + (
                names[0]
                if len(names) == 1
                else f"{', '.join(names[:-1])} or {names[-1]}"
            )
        )
    if other:
        details.append(f"{other} other source{'s' if other != 1 else ''} not found")
    unmeasured = len(warning["unmeasured_rules"])
    if unmeasured:
        details.append(
            f"{unmeasured} rule{'s' if unmeasured != 1 else ''} not measured"
        )
    return "; ".join(details) or warning["message"].removeprefix(
        "no number given — "
    )


def _number(value: float | int) -> str:
    return f"{round(value, 2):g}" if isinstance(value, float) else str(value)


def _context_warnings(packs: CombinedPack) -> list[str]:
    """Every pack's context warnings, first occurrence kept, in slot order."""
    warnings: list[str] = []
    for slot in packs.slots:
        if slot.pack is None:
            continue
        for warning in slot.pack.warnings:
            if warning not in warnings:
                warnings.append(warning)
    return warnings


def _render_unknowns(
    ctx: _Ctx, context_warnings: list[str], score: ScoreResult | None
) -> str:
    """FR-065: context warnings and FR-059 evidence-lack warnings in one
    section, one summary line per item, the full text folded below it."""
    evidence = score.warnings if score is not None else []
    if not context_warnings and not evidence:
        return ""
    items = [
        f'<li class="unknown"><details><summary>{ctx.esc(_first_sentence(w))}'
        f"</summary><p>{ctx.esc(w)}</p></details></li>"
        for w in context_warnings
    ]
    for warning in evidence:
        rows = [
            f"<li><code>{ctx.esc(rule['metric_name'])}</code> — "
            f"{ctx.esc(rule['reason'])}</li>"
            for rule in warning["unmeasured_rules"]
        ] + [
            f"<li><code>{ctx.esc(miss['source'])}</code> — "
            f"{ctx.esc(miss['reason'])}</li>"
            for miss in warning["sources_missing"]
        ]
        listed = f'<ul class="miss-list">{"".join(rows)}</ul>' if rows else ""
        items.append(
            '<li class="unknown"><details><summary>'
            f"<strong>{ctx.esc(warning['dimension'])}</strong> "
            f"({ctx.esc(warning['reason_code'])}): no number given</summary>"
            f"<p>{ctx.esc(warning['message'])}</p>{listed}</details></li>"
        )
    method = (
        '<p class="method">These dimensions lacked the evidence for a rating. '
        "Neither the rules nor the calling agent fills that in; each is "
        "excluded from the overall and listed in the improvement plan.</p>"
        if evidence
        else ""
    )
    return (
        '<section class="warning-banner unknowns">'
        "<h2>What we couldn't measure</h2>"
        f'{method}<ul class="unknown-list">{"".join(items)}</ul></section>'
    )


def _first_sentence(text: str) -> str:
    head, separator, _rest = text.partition(". ")
    return head + "." if separator else text


def _render_score_panel(ctx: _Ctx, score: ScoreResult | None) -> str:
    """Render declared ratings separately from optional caller assessments."""
    if score is None:
        return (
            '<section class="score-panel"><h2>Quality score</h2>'
            '<p class="score-unavailable">Overall and per-dimension ratings are '
            "unavailable because this report does not contain all declared "
            "dimensions."
            "</p></section>"
        )

    overall = score.overall
    if type(overall) is OverallRating:
        overall_html = (
            '<div class="overall-rating"><h3>Overall</h3>'
            f'<p class="rating-value">{ctx.esc(overall.value)}/100</p>'
            f'<p class="rating-disclosure">{ctx.esc(overall.disclosure)}</p></div>'
        )
    else:
        overall_html = (
            '<div class="overall-rating rating-abstention"><h3>Overall</h3>'
            '<p class="rating-withheld">Overall rating withheld</p>'
            f"<p>{ctx.esc(overall.reason)}</p>"
            f"{_render_nested_abstentions(ctx, overall)}"
            "</div>"
        )

    assessments = (
        {item.dimension: item for item in score.assessments.outcomes}
        if score.assessments is not None
        else {}
    )
    divergences = (
        {item.dimension: item.divergence for item in score.comparisons.comparisons}
        if score.comparisons is not None
        else {}
    )
    samples = {item["dimension"]: item for item in score.samples}
    cards = "".join(
        _render_score_card(
            ctx,
            rating,
            assessments.get(rating.dimension),
            divergences.get(rating.dimension),
            samples.get(rating.dimension),
        )
        for rating in score.ratings
    )
    return (
        '<section class="score-panel"><h2>Quality score</h2>'
        '<p class="method">Ratings are declared arithmetic over the cited metrics. '
        "At a hard gate a cited agent evaluation may blend in (w = 0.5 x "
        "confidence) or stand alone as agent-rated, always shown with its parts. "
        "An assessment appears only when caller findings were submitted; divergence "
        "is shown separately and never blended.</p>"
        f"{overall_html}{_render_area_coverage(ctx, score)}"
        f'<div class="score-grid">{cards}</div>'
        f"{_render_registry_entries(ctx, score.registry_entries)}</section>"
    )


def _render_area_coverage(ctx: _Ctx, score: ScoreResult) -> str:
    """FR-073: how many evaluation areas the score speaks for, and a folded
    list of the areas no declared rule covers yet."""
    missing = score.areas_without_rule
    text = (
        f"This score measured {len(score.areas_measured)} of {len(AREAS)} "
        f"evaluation areas; {len(missing)} have no rule yet, so it says nothing "
        "about them."
    )
    rows = "".join(f"<li>{ctx.esc(area)}</li>" for area in missing)
    folded = (
        '<details class="areas-without-rule"><summary>Areas no rule covers yet '
        f'({len(missing)})</summary><ul class="miss-list">{rows}</ul></details>'
        if missing
        else ""
    )
    return f'<div class="area-coverage"><p>{ctx.esc(text)}</p>{folded}</div>'


_GROUP_TITLES = {
    "P0": "P0 — near miss: unmet, within ±{band}% of the threshold",
    "P1": "P1 — clear failure",
    "P2": "P2 — not measurable yet: the metric abstained",
}


def _render_improvement_plan(
    ctx: _Ctx,
    plan: ImprovementPlan,
    improvements: dict[tuple[str, str], str] | None = None,
    *,
    nothing_rated: bool = False,
) -> str:
    """FR-055/FR-056: every gap, P0 then P1 then P2, each with its
    recomputed gain and the engine's fix line, labelled as such (FR-057);
    a validated agent suggestion for an item is shown above its engine line,
    labelled ``agent``. FR-065: one card per item; the first P0/P1 items the
    summary names are highlighted; P2 is folded."""
    improvements = improvements or {}
    data = plan.to_dict()
    band = format((BORDERLINE_BAND * 100).normalize(), "f")
    parts = [
        '<section class="improvement-plan"><h2>Improvement plan</h2>',
        f'<p class="method">{ctx.esc(data["method"])}</p>',
    ]
    if not plan.items:
        parts.append(
            '<p class="notice notice-abstain">No number for any dimension: none '
            "could be rated, so there is no measured gap to rank. What each "
            "dimension lacks is listed below.</p>"
            if nothing_rated
            else '<p class="notice no-gaps">No gaps: every measured rule is met '
            "and no rule metric of a rated dimension is unmeasured.</p>"
        )
    highlighted = 0
    for group in GROUPS:
        items = data["groups"][group]
        title = f"<h3>{ctx.esc(_GROUP_TITLES[group].format(band=band))}</h3>"
        if not items:
            parts.append(f'{title}<p class="empty">None.</p>')
            continue
        cards = []
        for item in items:
            top = group != "P2" and highlighted < SUMMARY_FOCUS_LIMIT
            highlighted += top
            cards.append(
                _render_plan_item(
                    ctx,
                    item,
                    improvements.get((item["dimension"], item["metric_name"])),
                    top=top,
                )
            )
        body = f'<div class="plan-cards">{"".join(cards)}</div>'
        if group == "P2":
            parts.append(
                f'<details class="plan-group"><summary>{title}</summary>'
                f"{body}</details>"
            )
        else:
            parts.append(title + body)
    if data["abstained"]:
        lines = "".join(
            f"<li><strong>{ctx.esc(line['dimension'])}</strong> — "
            f"{ctx.esc(line['reason_code'])}: {ctx.esc(line['reason'])}"
            f"{_render_unmeasured(ctx, line.get('unmeasured', ()))}</li>"
            for line in data["abstained"]
        )
        parts.append(
            "<h3>Dimensions without a rules rating</h3>"
            f'<ul class="miss-list">{lines}</ul>'
        )
    parts.append("</section>")
    return "".join(parts)


def _render_unmeasured(ctx: _Ctx, unmeasured) -> str:
    """FR-059: what the repository lacks for an abstained dimension."""
    if not unmeasured:
        return ""
    rows = "".join(
        f"<li><code>{ctx.esc(rule['metric_name'])}</code> — "
        f"{ctx.esc(rule['reason'])}. Engine fix: {ctx.esc(rule['fix'])}</li>"
        for rule in unmeasured
    )
    return f"<ul>{rows}</ul>"


def _render_plan_item(
    ctx: _Ctx, item: dict[str, Any], suggestion: str | None = None, *, top=False
) -> str:
    now = (
        "not measured"
        if item["metric_value"] is None
        else f"{item['metric_value']}"
    )
    gain = (
        f"{_signed(item['overall_gain'])} overall / "
        f"{_signed(item['dimension_gain'])} {item['dimension']}"
    )
    note = (
        '<p class="method">(rules part; the final rating also depends on the '
        "gate)</p>"
        if item["gain_basis"] == "rules"
        else ""
    )
    if item["computed_from"]:
        evidence = "".join(
            f"<li><code>{_render_ref(ctx, ref)}</code></li>"
            for ref in item["computed_from"]
        )
        count = len(item["computed_from"])
        evidence = (
            f"<details><summary>{count} cited file{'s' if count != 1 else ''}"
            f"</summary><ul>{evidence}</ul></details>"
        )
    elif item["unavailable_reason"]:
        evidence = (
            "<details><summary>Why not measured</summary>"
            f"<p>{ctx.esc(item['unavailable_reason'])}</p></details>"
        )
    else:
        evidence = '<p class="empty">no file cited</p>'
    engine = (
        f"{ctx.esc(item['fix']['text'])} "
        f'<span class="fix-source">{ctx.esc(item["fix"]["source"])}</span>'
    )
    if suggestion is not None:
        # Agent prose is a new egress path: redact, then escape (DDR-0001).
        fix = (
            f'<p class="suggestion">{ctx.agent_text(suggestion)} '
            '<span class="fix-source fix-source-agent">agent</span></p>'
            f'<p class="fix-engine">{engine}</p>'
        )
    else:
        fix = f'<p class="fix">{engine}</p>'
    css = f"plan-card plan-{item['group']}" + (" plan-top" if top else "")
    return (
        f'<article class="{ctx.esc(css)}">'
        f'<p class="plan-head"><strong>{ctx.esc(item["dimension"])} · '
        f'{ctx.esc(item["area"])}</strong> '
        f'<span class="plan-gain">Gain {ctx.esc(gain)}</span></p>'
        f'<p class="plan-now">Metric <code>{ctx.esc(item["metric_name"])}</code> — '
        f"Now → rule: {ctx.esc(now)}; {ctx.esc(item['comparison'])} "
        f"{ctx.esc(item['threshold'])}; weight {ctx.esc(item['weight'])}</p>"
        f"{note}{fix}{evidence}</article>"
    )


def _signed(value: int | list[int]) -> str:
    if isinstance(value, list):
        return f"{value[0]:+d} to {value[1]:+d}"
    return f"{value:+d}"


def _render_registry_entries(ctx: _Ctx, entries) -> str:
    """The local-layer registry data behind these ratings, tag and link on
    every item (FR-048), plus the same items as replayable agent input: add
    them to ``--agent-input`` to reproduce this score on any machine."""
    if not entries:
        return ""
    items = "".join(
        f'<li><span class="source-tag">{ctx.agent_text(item["source_tag"])}</span> '
        + (
            "<strong>rejected by the user: not used; rules needing it abstain"
            "</strong> "
            if item.get("review_status") == "rejected"
            else ""
        )
        + f"<code>{ctx.agent_text(item.get('language') or item.get('framework'))}"
        f".{ctx.agent_text(item['field'])}</code> = "
        + ", ".join(f"<code>{ctx.agent_text(v)}</code>" for v in item["value"])
        + f' — <a href="{html.escape(str(item["citation_url"]), quote=True)}" '
        f'rel="noreferrer">{ctx.agent_text(item["citation_url"])}</a></li>'
        for item in entries
    )
    replay = json.dumps(
        {"registry_entries": [dict(item) for item in entries]},
        sort_keys=True,
        indent=2,
    )
    return (
        '<section class="registry-entries"><h3>Registry data from the local '
        "layer</h3><p>These rule inputs come from research saved on the "
        "scoring machine, not from the curated registry. Add the block below "
        "to <code>--agent-input</code> to reproduce this score anywhere.</p>"
        f'<ul>{items}</ul><pre class="registry-replay">{ctx.agent_text(replay)}'
        "</pre></section>"
    )


def _render_score_card(
    ctx: _Ctx,
    rating: Rating | RatingAbstention | GatedRating,
    assessment: Assessment | AssessmentAbsence | None,
    divergence: Divergence | DivergenceAbsence | None,
    sample: dict[str, Any] | None = None,
) -> str:
    gated = ""
    row = ""
    if type(rating) is GatedRating:
        row = f"{rating.parts}; "
        # FR-038: the number never appears without its parts; the rules
        # result (rating or abstention record) is rendered in full below it.
        refs = "".join(
            f"<li><code>{_render_ref(ctx, ref)}</code></li>"
            for ref in rating.evidence_refs
        )
        gated = (
            f'<p class="rating-value">Rating {ctx.esc(rating.parts)}</p>'
            f'<p class="rating-method">Rating: {ctx.esc(rating.rated_by)}. '
            "Agent evidence cited:</p>"
            f'<ul class="rating-agent-refs">{refs}</ul>'
        )
        rating = rating.rules
    label = "Rules rating" if gated else "Rating"
    if type(rating) is Rating:
        areas = _render_areas(ctx, rating.inputs, rating.documentation)
        unavailable = "".join(
            f"<li><code>{ctx.esc(name)}</code> — {ctx.esc(reason)}</li>"
            for name, reason in rating.unavailable_metrics
        )
        unavailable_block = (
            "<details><summary>Unavailable metrics</summary>"
            f"<ul>{unavailable}</ul></details>"
            if unavailable
            else ""
        )
        met = sum(item.passed for item in rating.inputs)
        row += (
            f"{rating.value}/100 · rules met {met}/"
            f"{len(RATING_RULES[rating.dimension])}"
        )
        rating_html = (
            f'<p class="rating-value">{label} {ctx.esc(rating.value)}/100</p>'
            f'<p class="rating-method">{ctx.esc(rating.method)}</p>'
            f"{areas}{unavailable_block}"
        )
        css = "score-card"
    else:
        misses = "".join(_miss_row(ctx, miss) for miss in rating.sources_missing)
        coverage = ""
        if rating.coverage_floor is not None:
            achieved = (
                "n/a"
                if rating.achieved_coverage is None
                else f"{rating.achieved_coverage * 100:.1f}%"
            )
            coverage = (
                f"<p>Declared floor: {ctx.esc(rating.coverage_floor * 100)}% · "
                f"achieved: {ctx.esc(achieved)}</p>"
            )
        failure = (
            f'<p class="error">Failure: {ctx.esc(rating.failure)}</p>'
            if rating.failure
            else ""
        )
        row += f"no number — {rating.reason_code}"
        rating_html = (
            f'<p class="rating-withheld">{label} withheld</p>'
            f"<p>{ctx.esc(rating.reason_code)} — {ctx.esc(rating.reason)}</p>"
            f'{coverage}{failure}<ul class="miss-list">{misses}</ul>'
            f"{_render_areas(ctx, (), rating.documentation)}"
        )
        css = f"score-card rating-abstention rating-{rating.reason_code}"

    return (
        f'<article class="{css}"><h3>{ctx.esc(rating.dimension)}</h3>'
        f'<p class="score-row">{ctx.esc(row)}</p>'
        f"{_render_sample(ctx, sample)}"
        "<details><summary>Rule inputs, citations and cited files</summary>"
        f"{gated}{rating_html}{_render_assessment(ctx, assessment)}"
        f"{_render_divergence(ctx, divergence)}</details></article>"
    )


def _render_sample(ctx: _Ctx, sample: dict[str, Any] | None) -> str:
    """T068: a sampled dimension says so beside its number (FR-060)."""
    if sample is None:
        return ""
    return (
        '<p class="rating-method">Sample: batches '
        f"{ctx.esc(sample['batches_done'])} of {ctx.esc(sample['batches_total'])} — "
        f"{ctx.esc(format(sample['files_read'], ','))} of "
        f"{ctx.esc(format(sample['files_in_scope'], ','))} in-scope source files "
        f"read, ordered by {ctx.esc(sample['order'])}</p>"
    )


def _render_areas(ctx: _Ctx, inputs, documentation) -> str:
    """Rule results grouped by area (FR-051), inside their dimension's card,
    in declared order. Documentation results carry no number (FR-052)."""
    groups: dict[str, list[str]] = {}
    for item in inputs:
        groups.setdefault(item.area, []).append(_render_rating_input(ctx, item))
    for item in documentation:
        groups.setdefault(item.area, []).append(_render_documentation(ctx, item))
    return "".join(
        f'<h4 class="rating-area">{ctx.esc(area)}</h4>'
        f'<ol class="rating-inputs">{"".join(rows)}</ol>'
        for area, rows in groups.items()
    )


def _render_documentation(ctx: _Ctx, item) -> str:
    cited = ", ".join(_render_citation(ctx, c) for c in item.citation)
    if item.status == "present":
        detail = f"<code>{ctx.path(item.file)}</code>"
    else:
        detail = ctx.esc(item.reason)
    return (
        f'<li class="documentation-{ctx.esc(item.status)}">Documentation '
        f"{ctx.esc(item.status)} (not scored): {detail}"
        f'<p class="rating-citation">Standard: {cited}</p></li>'
    )


def _render_rating_input(ctx: _Ctx, item) -> str:
    refs = "".join(
        f"<li><code>{_render_ref(ctx, ref)}</code></li>" for ref in item.computed_from
    )
    return (
        "<li>"
        f"<code>{ctx.esc(item.metric_name)}</code> = {ctx.esc(item.metric_value)}; "
        f"{ctx.esc(item.comparison)} {ctx.esc(item.threshold)}; weight "
        f"{ctx.esc(item.weight)}; earned {ctx.esc(item.earned_weight)}"
        '<p class="rating-citation">Metric: '
        + ", ".join(_render_citation(ctx, c) for c in item.metric_citation)
        + "; threshold: "
        + _render_citation(ctx, item.threshold_citation)
        + f"; source: {ctx.esc(item.source_tag)}"
        + "".join(
            f"; registry data: {_render_citation(ctx, c)}"
            for c in item.registry_citations
        )
        + "</p>"
        f"<ul>{refs}</ul></li>"
    )


def _render_citation(ctx: _Ctx, citation) -> str:
    """A cited source as a link (FR-048); ``project-default`` stays text."""
    if isinstance(citation, str):
        return ctx.esc(citation)
    return (
        f'<a href="{html.escape(citation.url, quote=True)}" rel="noreferrer">'
        f"{ctx.esc(citation.label)}</a>"
    )


def _render_ref(ctx: _Ctx, ref: str) -> str:
    path, separator, lines = ref.rpartition(":")
    if separator and "-" in lines:
        return f"{ctx.path(path)}:{ctx.esc(lines)}"
    return ctx.path(ref)


def _render_assessment(
    ctx: _Ctx, assessment: Assessment | AssessmentAbsence | None
) -> str:
    if assessment is None:
        return '<p class="assessment-absent">Assessment: not submitted</p>'
    if type(assessment) is Assessment:
        return (
            '<p class="assessment-value">Assessment '
            f"{ctx.esc(assessment.value)}/100</p>"
            f'<p class="method">{ctx.esc(assessment.provenance)}</p>'
        )
    return (
        '<p class="assessment-absent">Assessment absent: '
        f"{ctx.esc(assessment.reason)}</p>"
    )


def _render_divergence(
    ctx: _Ctx, divergence: Divergence | DivergenceAbsence | None
) -> str:
    if divergence is None:
        return '<p class="divergence-absent">Divergence: not available</p>'
    if type(divergence) is Divergence:
        return (
            '<p class="divergence-value">Divergence '
            f"{ctx.esc(divergence.signed_gap):s} "
            f"({ctx.esc(divergence.direction)})</p>"
        )
    return (
        '<p class="divergence-absent">Divergence absent: '
        f"{ctx.esc(divergence.reason)}</p>"
    )


def _render_nested_abstentions(ctx: _Ctx, overall) -> str:
    rows = "".join(
        f"<li><strong>{ctx.esc(item.dimension)}</strong>: "
        f"{ctx.esc(item.reason_code)} — {ctx.esc(item.reason)}</li>"
        for item in overall.abstentions
    )
    return f'<ul class="overall-abstentions">{rows}</ul>'


def _render_coverage(ctx: _Ctx, coverage: CoverageSummary) -> str:
    """The only place in this module a coverage score is rendered."""
    misses = dict(coverage.misses)
    entries = [
        _coverage_entry(ctx, dimension, score, misses.get(dimension, ()))
        for dimension, score in coverage.per_dimension
    ]
    combined_misses = tuple(m for _, dim_misses in coverage.misses for m in dim_misses)
    combined = _coverage_entry(
        ctx, "All dimensions (combined)", coverage.combined, combined_misses
    )
    # Counts only: a coverage score never appears without its miss list
    # (FR-016a), so the folded entries below are the only place it is shown.
    missing = len(combined_misses)
    count = len(entries)
    summary = (
        f"{count} dimension{'s' if count != 1 else ''}; {missing} "
        f"source{'s' if missing != 1 else ''} missing"
    )
    return (
        '<section class="coverage"><h2>Checklist coverage</h2>'
        f"<details><summary>{ctx.esc(summary)}</summary>"
        f'<p class="method">Method: {ctx.esc(coverage.method)}. A coverage score '
        "describes how much of this engine's own source checklist it reached — "
        "never the quality of the repository.</p>"
        f"{combined}{''.join(entries)}</details></section>"
    )


def _coverage_entry(
    ctx: _Ctx, label: str, score: float | None, misses: Iterable[SourceMiss]
) -> str:
    """Format one score **with** its named miss list (FR-016a, AC #6).

    ``misses`` is a required parameter and is always rendered, so there is no
    way to reach a formatted score in this module without holding the list that
    explains it.
    """
    misses = tuple(misses)
    if misses:
        rows = "".join(_miss_row(ctx, miss) for miss in misses)
        miss_block = f'<ul class="miss-list">{rows}</ul>'
    elif score is None:
        # An all-clear must never be printed for an entry that has no score.
        # "no misses" and "no score" together mean the dimension produced
        # nothing at all -- a crash, most often -- and "every declared source
        # was reached" is then flatly false. The dimension's own section
        # carries the real reason.
        miss_block = (
            '<p class="miss-list miss-list-empty">No coverage was recorded for '
            "this entry — see its section below for why.</p>"
        )
    else:
        miss_block = (
            '<p class="miss-list miss-list-empty">No sources missing — every '
            "declared source on the checklist was reached.</p>"
        )
    return (
        '<div class="coverage-entry">'
        f"<h3>{ctx.esc(label)}</h3>"
        f'<p class="coverage-score">{ctx.esc(_format_score(score))}</p>'
        f"{miss_block}</div>"
    )


def _format_score(score: float | None) -> str:
    """Render a score, or say there isn't one -- without inventing why.

    ``None`` reaches here from two different situations: a dimension that
    sought nothing, and a dimension that failed and produced no pack at all.
    This function cannot tell them apart, so it must not name a cause. It said
    "no sources were sought" for both, which rendered a crashed dimension as a
    benign one. The adjacent miss list is what explains the gap (FR-016a) --
    that adjacency is the whole reason the miss list is a required argument to
    :func:`_coverage_entry`.
    """
    if score is None:
        return "n/a"
    return f"{score * 100:.1f}%"


_MISS_LABELS = (
    ("excluded: secret-bearing", "excluded: secret-bearing", "miss-excluded"),
    ("not examined", "not examined", "miss-unexamined"),
)


def _miss_row(ctx: _Ctx, miss: SourceMiss) -> str:
    """One named miss, badged by category.

    AC #14: "we chose not to read this" must be visibly distinct from "this
    wasn't there" — a reader who cannot tell them apart reads a deliberate
    exclusion as an absence.
    """
    label, css = "not found", "miss-missing"
    reason = miss.reason.lower()
    for needle, badge, badge_css in _MISS_LABELS:
        if needle in reason:
            label, css = badge, badge_css
            break
    return (
        f'<li class="{css}">'
        f'<span class="miss-badge">{ctx.esc(label)}</span> '
        f"<code>{ctx.path(miss.source)}</code> — {ctx.esc(miss.reason)}</li>"
    )


def _render_dimensions(
    ctx: _Ctx, by_dimension: dict[str, tuple[Finding, ...]], packs: CombinedPack
) -> str:
    sections = [
        _render_dimension(ctx, slot, by_dimension.get(slot.dimension, ()))
        for slot in packs.slots
    ]
    if not sections:
        return (
            '<section class="dimensions"><h2>Dimensions</h2>'
            '<p class="empty">No dimensions were submitted.</p></section>'
        )
    findings = sum(len(v) for v in by_dimension.values())
    files = len(
        {
            path
            for slot in packs.slots
            if slot.pack is not None
            for path in slot.pack.files_read
        }
    )
    summary = (
        f"{len(sections)} dimension{'s' if len(sections) != 1 else ''}; "
        f"{findings} finding{'s' if findings != 1 else ''}; "
        f"{files} file{'s' if files != 1 else ''} read"
    )
    return (
        '<section class="dimensions"><h2>Dimensions</h2>'
        f"<details><summary>{ctx.esc(summary)}</summary>{''.join(sections)}"
        "</details></section>"
    )


def _render_dimension(ctx: _Ctx, slot: Any, findings: tuple[Finding, ...]) -> str:
    head = f"<h3>{ctx.esc(slot.dimension)}</h3>"
    if slot.pack is None:
        return (
            '<article class="dimension dimension-error">'
            f'{head}<p class="error">This dimension produced no evidence pack: '
            f"{ctx.esc(slot.error)}</p></article>"
        )

    pack = slot.pack
    body = [
        head,
        _render_pack_meta(ctx, pack),
        _render_findings(ctx, pack, findings),
    ]
    return f'<article class="dimension">{"".join(body)}</article>'


def _render_pack_meta(ctx: _Ctx, pack: EvidencePack) -> str:
    truncated = pack.truncated or (
        pack.truncation is not None and pack.truncation.truncated
    )
    omitted = pack.omitted_count
    if pack.truncation is not None:
        omitted = max(omitted, pack.truncation.omitted_count)
    if truncated:
        truncation = (
            f"Truncated by the evidence budget — at least {ctx.esc(omitted)} "
            "excerpt(s) omitted (a lower bound, not a total). Coverage below is "
            "therefore an upper bound on what this report shows."
        )
        truncation_css = "flag flag-on"
    else:
        truncation = "Not truncated — the byte budget rejected nothing."
        truncation_css = "flag"

    if pack.had_redactions or pack.redactions:
        rows = "".join(
            f"<li><code>{ctx.path(hit.path)}</code>:{ctx.esc(hit.line)} — "
            f"{ctx.esc(hit.detector)} → <code>{ctx.esc(hit.fingerprint)}</code></li>"
            for hit in pack.redactions
        )
        detail = (
            f'<ul class="redactions">{rows}</ul>'
            if rows
            else '<p class="redactions">Redacted material was removed from '
            "excerpts the byte budget then rejected, so no individual hit is "
            "listed here.</p>"
        )
        redaction = (
            '<p class="flag flag-on">Secrets were detected and replaced with '
            "non-reversible fingerprints while this pack was built. The raw "
            "values are not in this report and cannot be recovered from it.</p>"
            f"{detail}"
        )
    else:
        redaction = '<p class="flag">No secrets were detected in this pack.</p>'

    files = "".join(f"<li><code>{ctx.path(p)}</code></li>" for p in pack.files_read)
    files_block = (
        f"<details><summary>{ctx.esc(len(pack.files_read))} file(s) read</summary>"
        f"<ul>{files}</ul></details>"
        if files
        else '<p class="empty">No files were read.</p>'
    )

    return (
        '<div class="pack-meta">'
        f"<p>Mode: <code>{ctx.esc(pack.mode)}</code> · Scope: "
        f"<code>{ctx.esc(pack.scope)}</code></p>"
        f'<p class="provenance">Sources: {ctx.esc(pack.source_provenance)}</p>'
        f'<p class="{truncation_css}">{truncation}</p>'
        f"{redaction}{files_block}</div>"
    )


def _render_findings(
    ctx: _Ctx, pack: EvidencePack, findings: tuple[Finding, ...]
) -> str:
    if not findings:
        return (
            '<p class="empty">No findings were submitted for this dimension. '
            "That is a result, not an omission: the evidence above was gathered "
            "and the calling agent made no claim about it.</p>"
        )
    excerpts = {excerpt.ref: excerpt for excerpt in pack.excerpts}
    rendered = "".join(_render_finding(ctx, f, excerpts) for f in findings)
    return f'<ol class="findings">{rendered}</ol>'


def _render_finding(ctx: _Ctx, finding: Finding, excerpts: dict[str, Any]) -> str:
    excerpt = excerpts.get(finding.evidence_ref)
    if excerpt is not None:
        ref_display = f"{excerpt.path}:{excerpt.start_line}-{excerpt.end_line}"
        quoted = f'<pre class="excerpt">{ctx.esc(excerpt.text)}</pre>'
    else:
        ref_display = finding.evidence_ref
        quoted = ""
    ref_path, _, ref_lines = ref_display.rpartition(":")
    evidence = (
        '<p class="evidence">Evidence: <code>'
        f"{ctx.path(ref_path)}:{ctx.esc(ref_lines)}</code></p>"
    )
    suggestion = (
        f'<p class="suggestion"><strong>Suggested improvement:</strong> '
        f"{ctx.agent_text(finding.suggestion)}</p>"
        if finding.suggestion
        else ""
    )
    return (
        '<li class="finding">'
        f"<h4>{ctx.agent_text(finding.title)}</h4>"
        f'<p class="confidence">Confidence: <span class="confidence-value">'
        f"{ctx.esc(finding.confidence)}</span> (stated by the calling agent)</p>"
        f'<p class="detail">{ctx.agent_text(finding.detail)}</p>'
        f"{evidence}{quoted}{suggestion}</li>"
    )


def _render_footer() -> str:
    return (
        '<footer class="footer"><p>Generated by easy-verifier-mcp. '
        "Self-contained: this file requests nothing from the network.</p></footer>"
    )


_CSS = """
:root { color-scheme: dark; }
* { box-sizing: border-box; }
body { font-family: system-ui, sans-serif; max-width: 60rem; margin: 2rem auto;
  padding: 0 1rem; background: #0a0a12; color: #e2e2f0; line-height: 1.55; }
h1 { font-size: 1.4rem; margin: 0 0 .5rem; color: #fff; }
h2 { font-size: .8rem; text-transform: uppercase; letter-spacing: .08em;
  color: #6b6b9a; margin: 2rem 0 .75rem; }
h3 { font-size: 1.05rem; margin: 0 0 .5rem; color: #00d4ff; }
h4 { font-size: .95rem; margin: 0 0 .35rem; color: #fff; }
code { background: rgba(0,212,255,.12); color: #00d4ff; padding: .05rem .35rem;
  border-radius: 4px; word-break: break-all; }
section, article { background: #111128; border: 1px solid #1e1e42;
  border-radius: 10px; padding: 1rem 1.25rem; margin-bottom: 1rem; }
.header { border-top: 2px solid #00d4ff; }
.meta { display: grid; grid-template-columns: max-content 1fr; gap: .1rem .75rem;
  margin: 0; font-size: .85rem; }
.meta dt { color: #6b6b9a; }
.meta dd { margin: 0; }
.disclaimer, .method, .empty { color: #6b6b9a; font-size: .85rem; }
.advisory { border-left: 3px solid #ffb800; background: rgba(255,184,0,.08); }
.warning-banner { border-left: 3px solid #ff3b6b; background: rgba(255,59,107,.08); }
.coverage-entry { border-top: 1px solid #1e1e42; padding-top: .75rem;
  margin-top: .75rem; }
.score-grid { display: grid;
  grid-template-columns: repeat(auto-fit, minmax(18rem, 1fr));
  gap: .75rem; }
.score-card { margin: 0; min-width: 0; }
.overall-rating { border-left: 3px solid #00ff88; padding-left: .8rem; margin: 1rem 0; }
.rating-value, .assessment-value { font-size: 1.35rem; font-weight: 700;
  font-variant-numeric: tabular-nums; color: #00ff88; margin: .2rem 0; }
.assessment-value { color: #ffb800; }
.rating-method, .rating-inputs, .rating-disclosure, .assessment-absent,
.divergence-absent, .divergence-value, .score-unavailable { font-size: .8rem; }
.rating-abstention { border-color: #ffb800; background: rgba(255,184,0,.06); }
.rating-dimension_failed { border-color: #ff3b6b; background: rgba(255,59,107,.08); }
.rating-withheld { color: #ffb800; font-weight: 800; text-transform: uppercase;
  letter-spacing: .05em; }
.rating-abstention .rating-value { display: none; }
.coverage-score { font-size: 1.6rem; font-weight: 700; margin: .2rem 0;
  font-variant-numeric: tabular-nums; color: #00ff88; }
.miss-list { margin: .25rem 0 0; padding-left: 1.1rem; font-size: .85rem; }
.miss-badge { display: inline-block; padding: .05rem .45rem; border-radius: 999px;
  font-size: .7rem; font-weight: 700; text-transform: uppercase;
  letter-spacing: .04em; }
.miss-missing .miss-badge { background: rgba(255,59,107,.15); color: #ff3b6b; }
.miss-unexamined .miss-badge { background: rgba(107,107,154,.2); color: #9a9ac0; }
.miss-excluded .miss-badge { background: rgba(168,85,247,.15); color: #c084fc; }
.flag { font-size: .85rem; color: #6b6b9a; margin: .3rem 0; }
.flag-on { color: #ffb800; }
.redactions { font-size: .8rem; color: #9a9ac0; }
.findings { padding-left: 1.2rem; }
.finding { margin-bottom: 1.25rem; }
.confidence, .evidence, .suggestion, .detail { font-size: .9rem; margin: .3rem 0; }
.confidence-value { font-weight: 700; color: #ffb800; }
.suggestion { border-left: 2px solid #a855f7; padding-left: .6rem; }
.excerpt { background: #16162e; border: 1px solid #1e1e42; border-radius: 6px;
  padding: .6rem .8rem; overflow-x: auto; white-space: pre-wrap;
  word-break: break-word; font-size: .8rem; }
.dimension-error .error { color: #ff3b6b; }
.fix-source { display: inline-block; padding: .05rem .45rem; border-radius: 999px;
  font-size: .7rem; font-weight: 700; text-transform: uppercase;
  background: rgba(168,85,247,.15); color: #c084fc; }
.fix-source-agent { background: rgba(255,184,0,.15); color: #ffb800; }
summary { cursor: pointer; }
section, article, li, dd { min-width: 0; overflow-wrap: break-word; }
.plan-cards { display: grid; gap: .6rem; margin-bottom: .75rem; }
.plan-card { margin: 0; padding: .6rem .8rem; font-size: .85rem;
  background: #16162e; }
.plan-P0 { border-left: 3px solid #ffb800; }
.plan-P1 { border-left: 3px solid #ff3b6b; }
.plan-top { box-shadow: inset 0 0 0 1px #00d4ff; }
.plan-card p { margin: .2rem 0; }
.plan-card ul { margin: 0; padding-left: 1rem; }
.plan-gain { display: inline-block; padding: .05rem .45rem; border-radius: 999px;
  font-size: .75rem; font-weight: 700; font-variant-numeric: tabular-nums;
  background: rgba(0,212,255,.12); color: #00d4ff; }
.plan-card .suggestion { margin: 0 0 .35rem; font-size: inherit; }
.plan-card .fix-engine { margin: 0; color: #9a9ac0; }
.plan-group > summary h3 { display: inline; }
.unknown-list { padding-left: 1.1rem; }
.unknown { margin-bottom: .35rem; overflow-wrap: anywhere; }
.unknown p { margin: .25rem 0; font-size: .9rem; }
.score-row { font-weight: 700; font-variant-numeric: tabular-nums;
  color: #00ff88; margin: .2rem 0; }
.rating-abstention .score-row { color: #ffb800; }
.score-card details, .coverage details, .dimensions details { font-size: .9rem; }
pre { overflow-x: auto; }
.notice { border-left: 3px solid #00ff88; background: #16162e;
  border-radius: 6px; padding: .5rem .75rem; margin: .5rem 0; }
.notice-abstain { border-left-color: #ffb800; background: rgba(255,184,0,.08);
  color: #ffb800; font-weight: 700; }
.no-gaps { color: #00ff88; font-weight: 700; }
.summary { border-left: 3px solid #00d4ff; }
.summary h3 { margin-top: .75rem; }
.summary-focus, .summary-missing { margin: .25rem 0 0; padding-left: 1.2rem;
  font-size: .9rem; }
.summary-focus li, .summary-missing li { margin-bottom: .35rem;
  overflow-wrap: break-word; }
.summary-agent { border-left: 2px solid #ffb800; padding-left: .6rem;
  margin: .75rem 0 0; overflow-wrap: break-word; }
.footer { border: none; background: none; color: #6b6b9a; font-size: .8rem;
  text-align: center; }
"""


__all__ = [
    "REPORTS_DIRNAME",
    "SENSITIVITY_ADVISORY",
    "RepoPathError",
    "ReportWriteError",
    "write_report",
]
