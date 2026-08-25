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
import os
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from easy_verifier.core.context import RepoPathError, _resolved_repo
from easy_verifier.core.findings import Finding, validate_findings
from easy_verifier.core.models import (
    CombinedPack,
    CoverageSummary,
    EvidencePack,
    ReportResult,
    SourceMiss,
)
from easy_verifier.core.redact import redact

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


def write_report(
    findings: list[dict[str, Any]] | str | bytes,
    packs: CombinedPack,
    target_repo: str | Path,
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

    reports_dir = repo / REPORTS_DIRNAME
    first_write = not _has_existing_reports(reports_dir)

    ctx = _Ctx(repo=repo)
    document = _render_document(
        ctx, validated.by_dimension, packs, first_write=first_write
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
    *,
    first_write: bool,
) -> str:
    generated = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    finding_count = sum(len(v) for v in by_dimension.values())

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
        _render_warnings(ctx, packs),
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
        '<p class="disclaimer">This engine performs no inference and renders no '
        "verdict. Every claim below was made by the calling agent and is shown "
        "next to the evidence it cited.</p>"
        "</header>"
    )


def _render_advisory(ctx: _Ctx, *, first_write: bool) -> str:
    marker = (
        "This is the first report written into this repository's reports/ directory."
        if first_write
        else ""
    )
    return (
        '<section class="advisory"><h2>Before you share this report</h2>'
        f"<p>{ctx.esc(SENSITIVITY_ADVISORY)}</p>"
        f'<p class="first-write">{ctx.esc(marker)}</p></section>'
    )


def _render_warnings(ctx: _Ctx, packs: CombinedPack) -> str:
    warnings: list[str] = []
    for slot in packs.slots:
        if slot.pack is None:
            continue
        for warning in slot.pack.warnings:
            if warning not in warnings:
                warnings.append(warning)
    if not warnings:
        return ""
    items = "".join(f"<li>{ctx.esc(w)}</li>" for w in warnings)
    return (
        '<section class="warning-banner"><h2>Context warnings</h2>'
        f"<ul>{items}</ul></section>"
    )


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
    return (
        '<section class="coverage"><h2>Checklist coverage</h2>'
        f'<p class="method">Method: {ctx.esc(coverage.method)}. A coverage score '
        "describes how much of this engine's own source checklist it reached — "
        "never the quality of the repository.</p>"
        f"{combined}{''.join(entries)}</section>"
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
        sections = ['<p class="empty">No dimensions were submitted.</p>']
    return (
        f'<section class="dimensions"><h2>Dimensions</h2>{"".join(sections)}</section>'
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
        f"{ctx.esc(finding.suggestion)}</p>"
        if finding.suggestion
        else ""
    )
    return (
        '<li class="finding">'
        f"<h4>{ctx.esc(finding.title)}</h4>"
        f'<p class="confidence">Confidence: <span class="confidence-value">'
        f"{ctx.esc(finding.confidence)}</span> (stated by the calling agent)</p>"
        f'<p class="detail">{ctx.esc(finding.detail)}</p>'
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
