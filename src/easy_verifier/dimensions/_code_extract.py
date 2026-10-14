"""Trailing code-evidence tiers for ``code-quality`` and ``architecture`` (T050).

T033's structure metrics (approximate CCN, import cycles) read only what a pack
quotes, and these two packs quoted docs and config only, so the metrics always
abstained. Each dimension now appends one lowest-relevance tier after its
existing document evidence:

* ``function_excerpts`` -- whole functions, most complex first (code-quality);
* ``import_excerpts`` -- import-statement lines only (architecture).

Candidates are the in-scope files ``core.metrics`` itself classifies as source
of a registry language with structure syntax, so the pack carries exactly what
the metrics can read. Reading goes through ``context.read_source`` (secret-
bearing files are refused there, unread) and every excerpt passes the
pipeline's budget and redaction like any other. Selection is deterministic:
sorted paths, then a stable key.

Priority batches (T068, DDR-0010; reverses T031/T050's all-or-none): above
:data:`MAX_CODE_SOURCES` candidates the tier reads batches 1…N of them, ordered
by purpose class, git churn and path (``core.batches``), and says so in a
warning. The tier's sampled metrics are then computed over the whole text of
those files (:func:`record_sample`), so the byte budget cutting the excerpts
does not make them abstain; it is still reported as truncation. At or under
the cap every candidate is read, and the same metrics are computed over the
whole text of all of them as one full batch (T076, FR-072), disclosed as "all
N source files" rather than a sample; the byte budget still cuts the excerpts
and is reported (FR-027a).
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import replace
from pathlib import PurePosixPath

from ..core import batches
from ..core.context import MAX_EXCERPT_LINES, MAX_LINE_CHARS
from ..core.metric_tables import curated_metric_tables, with_conventions
from ..core.metrics import _is_source_file, compute_sampled_metrics
from ..core.models import (
    DimensionContext,
    Excerpt,
    SampledMetric,
    SampleFacts,
)
from ..core.redact import redact
from ..core.roles import walked_role_paths
from ..core.structure import context_conventions
from ..core.tokens import LanguageSyntax, approximate_ccn, import_statements

MAX_CODE_SOURCES = 200
"""Source files per priority batch of one code tier (the former all-or-none cap)."""

BATCH_WARNING = (
    "{count} in-scope source files exceed the cap of {cap} for {what}; read in "
    "priority batches of {cap}: batches {done} of {total} ({read} of {count} "
    "files), ordered by {order}. Metrics over {what} describe this sample."
)


_LINE_MARK = " …[line truncated]"
_CLIP_MARK = "…[excerpt clipped: showing lines {start}–{end}]"


def function_excerpts(
    context: DimensionContext, sources: list[str]
) -> Iterator[Excerpt]:
    """Whole outermost functions of ``sources``, highest CCN first.

    Ranking needs every candidate read before the first yield, which is what
    the cap bounds. Ties break on path then line. A nested function stays
    inside its parent's excerpt and ranks the parent by the higher CCN.
    """
    ranked: list[tuple[int, str, int, Excerpt]] = []
    for path, lines, syntax in _read(context, sources):
        outermost: list[list[int]] = []  # [start, end, highest ccn inside]
        for function in approximate_ccn("\n".join(lines), syntax):
            if outermost and function.line <= outermost[-1][1]:
                outermost[-1][2] = max(outermost[-1][2], function.ccn)
            else:
                outermost.append([function.line, function.end_line, function.ccn])
        for start, end, ccn in outermost:
            excerpt = _excerpt(path, lines, start - 1, end - 1)
            if excerpt is not None:
                ranked.append((-ccn, path, start, excerpt))
    for *_key, excerpt in sorted(ranked, key=lambda item: item[:3]):
        yield excerpt


def import_excerpts(context: DimensionContext, sources: list[str]) -> Iterator[Excerpt]:
    """Import-statement lines of ``sources``, in path order, lazily.

    Each excerpt is one run of consecutive statement lines (a multi-line
    statement whole), cited by its own path and line range.
    """
    for path, lines, syntax in _read(context, sources):
        spans: list[list[int]] = []
        for line, statement in import_statements("\n".join(lines), syntax):
            end = line + statement.count("\n")
            if spans and line <= spans[-1][1] + 1:
                spans[-1][1] = max(spans[-1][1], end)
            else:
                spans.append([line, end])
        for start, end in spans:
            excerpt = _excerpt(path, lines, start - 1, end - 1)
            if excerpt is not None:
                yield excerpt


def _read(
    context: DimensionContext, sources: list[str]
) -> Iterator[tuple[str, list[str], LanguageSyntax]]:
    """``(path, lines, syntax)`` per readable source, lazily.

    Lines split on ``\\n`` only, as ``core.tokens`` does, so a function's line
    numbers are the same in the file and in the excerpt cut from it. At or
    under the cap the texts were already read once by :func:`record_sample`
    (``context.source_texts``), so a file is read and recorded only once.
    """
    texts = getattr(context, "source_texts", None) or {}
    for path in sources:
        text = texts[path] if path in texts else context.read_source(path)
        if text:
            lines = [line.removesuffix("\r") for line in text.split("\n")]
            yield (
                path,
                lines,
                curated_metric_tables().syntax[PurePosixPath(path).suffix],
            )


def _excerpt(path: str, lines: list[str], start: int, end: int) -> Excerpt | None:
    """1-indexed excerpt of ``lines[start:end + 1]``, bounded like every other
    excerpt (line count, per-line characters); a clipped function says so."""
    kept = lines[start : min(end, start + MAX_EXCERPT_LINES - 1) + 1]
    if not kept:
        return None
    text = [
        line if len(line) <= MAX_LINE_CHARS else line[:MAX_LINE_CHARS] + _LINE_MARK
        for line in kept
    ]
    if end - start + 1 > len(kept):
        text.append(_CLIP_MARK.format(start=start + 1, end=start + len(kept)))
    return Excerpt(
        path=path,
        start_line=start + 1,
        end_line=start + len(kept),
        text="\n".join(text),
    )


def code_sources(files) -> list[str]:
    """In-scope source files with registry syntax, sorted: the candidates of
    every code tier, test-strategy's source batches included (T068)."""
    tables = curated_metric_tables()
    return sorted(
        path
        for path in set(files)
        if PurePosixPath(path).suffix in tables.syntax and _is_source_file(path, tables)
    )


def source_candidates(context: DimensionContext, what: str) -> list[str]:
    """The sources this tier reads: every candidate at or under the cap,
    else the files of priority batches 1…N (``context.batches``).

    Call before the dimension's first yield: the budget may abandon the
    generator at any yield, and the warning must not be lost with it. Raises
    :class:`~easy_verifier.core.batches.BatchInputError` when the requested
    batch count is out of range for this scope.
    """
    files = getattr(context.resolved_scope, "files", ()) or ()
    sources = code_sources(files)
    requested = getattr(context, "batches", 1)
    if len(sources) <= MAX_CODE_SOURCES:
        batches.resolve_count(requested, 1)
        return sources
    plan = getattr(context, "batch_plan", None)
    if plan is None:
        plan = batches.plan(context.repo_path, sources, MAX_CODE_SOURCES, requested)
        context.batch_plan = plan
    message = BATCH_WARNING.format(
        count=len(sources),
        cap=MAX_CODE_SOURCES,
        what=what,
        done=plan.batches_done,
        total=plan.batches_total,
        read=len(plan.selected),
        order=plan.order,
    )
    if message not in context.warnings:
        context.warnings = (*context.warnings, message)
    return list(plan.selected)


def record_sample(
    context: DimensionContext, dimension: str, sources: list[str]
) -> None:
    """Compute the tier's structure metrics over the whole text of ``sources``.

    Above the cap these are the files of priority batches 1…N and the result
    is ``context.sample`` (T068); at or under it, every candidate is one full
    batch and the result is ``context.whole_file``, disclosed as "all N source
    files", never as a sample (T076). Reads each file once through
    ``read_source`` (a secret-bearing file is refused there and counts for
    nothing); at or under the cap the texts are kept on the context for the
    excerpt tier, so nothing is read twice. Only the metric result reaches the
    pack, with its paths and derivation redacted like any other pack field.
    Once per context: the budget may call ``collect`` once per tier pass. No
    sources, no result: the metrics then abstain as before.
    """
    plan = getattr(context, "batch_plan", None)
    if getattr(context, "sample", None) is not None:
        return
    if getattr(context, "whole_file", None) is not None or not sources:
        return
    if not plan:
        context.source_texts = {path: context.read_source(path) for path in sources}
    units = [
        Excerpt(path=path, start_line=1, end_line=len(lines), text="\n".join(lines))
        for path, lines, _syntax in _read(context, plan.selected if plan else sources)
    ]
    note = ""
    if not plan:
        read = sum(text is not None for text in context.source_texts.values())
        note = "; " + _whole_note(read, len(sources))
    metrics = tuple(
        SampledMetric(
            name=item.name,
            value=item.value,
            abstention=(
                None if item.abstention is None else redact(item.abstention + note)
            ),
            computed_from=tuple(redact(path) for path in item.computed_from),
            derivation=redact(item.derivation + note) if item.derivation else "",
        )
        for item in compute_sampled_metrics(
            dimension,
            units,
            replace(
                with_conventions(curated_metric_tables(), context_conventions(context)),
                package_manifests=_package_manifests(context),
            ),
        )
    )
    if plan:
        context.sample = sample_facts(plan, metrics)
    else:
        context.whole_file = metrics


def _package_manifests(context: DimensionContext) -> tuple[str, ...]:
    """The repository's package manifests (T093), from the role resolution's
    whole-repository walk: batches do not hide a unit's manifest."""
    resolution = getattr(context, "role_resolution", None)
    if resolution is None:
        return ()
    return walked_role_paths(resolution, "package-manifest")


def _whole_note(read: int, candidates: int) -> str:
    """``all N source files`` (T076, FR-072), naming any refused unread."""
    note = f"all {read} source files"
    if candidates > read:
        note += f" ({candidates - read} more refused unread or unreadable)"
    return (
        note + " -- computed over the whole text of those files, not only the "
        "excerpts quoted in this pack"
    )


def sample_facts(plan, metrics=()) -> SampleFacts:
    return SampleFacts(
        batches_done=plan.batches_done,
        batches_total=plan.batches_total,
        files_read=len(plan.selected),
        files_in_scope=len(plan.ordered),
        order=plan.order,
        metrics=tuple(metrics),
    )
