"""The pipeline choke point.

``run_dimension`` owns redaction, budgeting, truncation reporting and coverage
arithmetic. A dimension supplies only ``sources_sought`` data and a ``collect``
callable, so it never gets the chance to bypass any of those (Option D).

Every later dimension is written against this function's contract. Changing the
contract is a broad, cross-cutting rewrite — treat it accordingly.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from . import redact as redact_module
from .context import DEFAULT_SCOPE, RepoPathError, detect_context
from .models import (
    DimensionDescriptor,
    EvidencePack,
    Excerpt,
    RedactionHit,
    SourceMiss,
)

DEFAULT_BUDGET_BYTES = 120_000

__all__ = [
    "DEFAULT_BUDGET_BYTES",
    "DEFAULT_SCOPE",
    "RepoPathError",
    "run_dimension",
]
"""``DEFAULT_SCOPE`` and ``RepoPathError`` now live in ``context`` (detection
validates the path), and are re-exported here because the adapters and T001's
tests import them from the pipeline."""


def run_dimension(
    descriptor: DimensionDescriptor,
    repo_path: str | Path,
    scope: str = DEFAULT_SCOPE,
    budget_bytes: int = DEFAULT_BUDGET_BYTES,
) -> EvidencePack:
    """Run one dimension against a repository and return its evidence pack.

    Works on any directory; git is not required for ``project`` scope (only
    ``changes`` will need it, in T003).
    """
    # Path validation lives in `detect_context` (T002), which raises
    # `RepoPathError` for a path that is absent or is not a directory. T004's
    # redaction of that message moved with it — the path itself is content, a
    # directory or file name can carry a secret, and an exception message is one
    # of the leak paths NFR-010 names.
    context = detect_context(repo_path, scope=scope)

    # The *call* is handed over, not its result: a conforming dimension can
    # still read and parse eagerly before returning its lazy iterator, and an
    # exception raised in that window must be redacted like any other.
    kept, truncated, omitted_count, hits = _budget(
        lambda: descriptor.collect(context), budget_bytes=budget_bytes
    )

    sought = tuple(descriptor.sources_sought)
    # Clamped to the declared checklist. `context.sources_found` is the raw read
    # record and may include files the dimension read without declaring; counting
    # those would let a dimension inflate its own coverage above 1.0, which FR-016
    # does not admit. The undeclared reads stay visible in `files_read`, because
    # they genuinely were read.
    found = tuple(source for source in sought if source in context.sources_found)
    missing = _missing_sources(sought, found, context.sources_missing, truncated)
    coverage_score = (len(found) / len(sought)) if sought else None

    # Paths are redacted too, and with the same function, so `found` stays an
    # exact subset of `sought` and the partition in `_missing_sources` holds.
    files_read, file_hits = _redact_paths(context.files_read)
    hits = (*hits, *file_hits)

    return EvidencePack(
        dimension=descriptor.name,
        mode=context.mode,
        scope=context.scope,
        files_read=files_read,
        excerpts=tuple(kept),
        sources_sought=_redact_paths(sought)[0],
        sources_found=_redact_paths(found)[0],
        sources_missing=tuple(
            SourceMiss(
                # `scan(...).text`, not `redact`, so the seam-call count that
                # T001 pins to excerpts stays about excerpts. A miss reason
                # echoes an OS error string, which can carry a path.
                source=redact_module.scan(miss.source).text,
                reason=redact_module.scan(miss.reason).text,
            )
            for miss in missing
        ),
        coverage_score=coverage_score,
        truncated=truncated,
        omitted_count=omitted_count,
        redactions=hits,
        had_redactions=bool(hits),
        # Unconditional: the pack is the only way evidence leaves the engine, so
        # copying the context's warnings here is what makes FR-004 hold for
        # every response and every report without any adapter opting in.
        warnings=context.warnings,
    )


def _redact_paths(paths) -> tuple[tuple[str, ...], tuple[RedactionHit, ...]]:
    """Redact a sequence of paths, reporting any hit against the path itself.

    A secret can sit in a file *name*, not only in file contents, and a name
    reaches the pack through ``files_read`` without ever passing through an
    excerpt.
    """
    safe: list[str] = []
    hits: list[RedactionHit] = []
    for path in paths:
        result = redact_module.scan(path)
        safe.append(result.text)
        hits.extend(replace(hit, path=result.text) for hit in result.hits)
    return tuple(safe), tuple(hits)


def _missing_sources(
    sought: tuple[str, ...],
    found: tuple[str, ...],
    attempted_misses: list[SourceMiss],
    truncated: bool,
) -> tuple[SourceMiss, ...]:
    """Every declared source that produced no evidence, with a stated reason.

    Together with ``found`` this partitions ``sources_sought`` exactly, which is
    what makes the miss list auditable (FR-016a). Two things have to be handled
    for that to hold:

    * a miss recorded for an *undeclared* path is dropped — it is not part of
      this dimension's checklist;
    * a declared source the dimension never even attempted still has to be
      accounted for. Lazy consumption makes this ordinary rather than
      exceptional: when the byte budget stops the pull, later sources are never
      probed. Reporting them as absent would be a claim the engine did not
      check, so they are reported as *not examined*.
    """
    reasons = {
        miss.source: miss.reason for miss in attempted_misses if miss.source in sought
    }
    unexamined = (
        "not examined: the byte budget was reached before this source was read"
        if truncated
        else "not examined by this dimension"
    )
    return tuple(
        SourceMiss(source=source, reason=reasons.get(source, unexamined))
        for source in sought
        if source not in found
    )


class DimensionFailure(RuntimeError):
    """A dimension's ``collect`` raised something that could not be rebuilt.

    Only used as a fallback by :func:`_redacting_exceptions`, when the original
    exception type cannot be reconstructed from redacted arguments. The original
    type name is preserved in the message so the failure is still diagnosable.
    """


def _redacting_exceptions(source):
    """Yield from ``source``, redacting any exception message it raises.

    ``source`` is either an iterable or a **zero-argument callable returning
    one**. The callable form matters: a dimension may conform to Critical
    Constraint 3 and still do real work eagerly, because a generator-*returning*
    function executes up to its ``return`` at call time::

        def collect(ctx):
            raw = _parse(ctx.read_source("config.yml"))   # runs at call time
            return (_excerpt(x) for x in raw)             # consumed lazily

    Wrapping only the iteration would leave that read-and-parse outside the
    protection, so the call itself is made in here too. It happens at the first
    pull, which if anything is lazier than before.

    A dimension is first-party code, so this is not an attacker path — but
    ``raise ValueError(f"malformed config line: {line}")`` is an ordinary thing
    to write, and ``line`` is exactly the content that carries secrets. An
    unhandled exception from a dimension propagates out through the adapter to
    the calling agent, which NFR-010 forbids in absolute terms. ``RepoPathError``
    is already redacted where it is raised; this covers the exceptions the core
    did *not* raise itself.

    The type and the traceback are preserved — only the message text is
    sanitised — so debugging keeps everything except the raw value. ``from None``
    is deliberate: chaining would re-attach the original, unredacted exception as
    ``__cause__`` and a printed traceback would show it after all.
    """
    try:
        iterator = iter(source() if callable(source) else source)
    except Exception as exc:  # noqa: BLE001 - re-raised, never swallowed
        raise _redacted_exception(exc).with_traceback(exc.__traceback__) from None

    while True:
        try:
            yield next(iterator)
        except StopIteration:
            return
        except Exception as exc:  # noqa: BLE001 - re-raised, never swallowed
            raise _redacted_exception(exc).with_traceback(exc.__traceback__) from None


def _redacted_exception(exc: BaseException) -> BaseException:
    """Rebuild ``exc`` with every string argument redacted.

    Rebuilding rather than mutating, because a few exception types compute their
    ``str`` from attributes rather than from ``args``. When the type cannot be
    reconstructed — it takes required keyword arguments, say — the message is
    carried over into :class:`DimensionFailure` rather than risking a raise from
    inside the error path.
    """
    args = tuple(
        redact_module.scan(arg).text if isinstance(arg, str) else arg
        for arg in exc.args
    )
    try:
        return type(exc)(*args)
    except Exception:  # noqa: BLE001 - any failure falls back, never propagates
        detail = redact_module.scan(str(exc)).text
        return DimensionFailure(f"{type(exc).__name__}: {detail}")


def _budget(
    raw_excerpts, budget_bytes: int
) -> tuple[list[Excerpt], bool, int, tuple[RedactionHit, ...]]:
    """Consume ``raw_excerpts`` lazily, redacting and byte-capping as it goes.

    ``raw_excerpts`` may be an iterable or a zero-argument callable returning
    one; see :func:`_redacting_exceptions`, which protects both the call and the
    iteration.

    Stops at the **first excerpt that does not fit**: that excerpt is pulled,
    redacted, rejected, counted, and iteration ends. The remainder is never
    drained (AC #5a) — ``omitted_count`` is therefore a lower bound.

    Setting ``truncated`` from an actual rejection, rather than from
    ``used >= budget_bytes``, is what makes it honest: a stream that ends exactly
    at the budget boundary reports ``truncated=False``, because nothing was ever
    rejected.

    T005 replaces this naive cap with real relevance ordering; the contract it
    must preserve is the laziness and the lower-bound semantics.
    """
    kept: list[Excerpt] = []
    hits: list[RedactionHit] = []
    used = 0

    for raw in _redacting_exceptions(raw_excerpts):
        # Redaction happens here, at the evidence layer, before an excerpt can
        # reach a pack, a report, a log or an error message (NFR-010). It runs
        # on the rejected excerpt too — a rejected excerpt is still an excerpt
        # this process has held in memory.
        safe_path, path_hits = _redact_paths((raw.path,))
        # The text that lands on the pack comes from `redact` — the seam T001
        # fixed and that every dimension is written against — while `scan`
        # supplies the hit metadata. They are the same computation (`redact` is
        # defined as `scan(text).text`), so the second pass costs a little CPU
        # inside an already byte-bounded excerpt and buys the property that the
        # seam function stays the single thing governing pack content.
        result = redact_module.scan(raw.text)
        safe = replace(raw, path=safe_path[0], text=redact_module.redact(raw.text))
        hits.extend(path_hits)
        hits.extend(
            replace(hit, path=safe.path, line=raw.start_line + hit.line - 1)
            for hit in result.hits
        )
        size = len(safe.text.encode("utf-8"))

        if used + size > budget_bytes:
            # The rejected excerpt is dropped, but its hits are kept: a secret
            # that only ever appeared in truncated material still happened, and
            # `had_redactions` must fire for it (NFR-011).
            return kept, True, 1, tuple(hits)

        kept.append(safe)
        used += size

    return kept, False, 0, tuple(hits)
