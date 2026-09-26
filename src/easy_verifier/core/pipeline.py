"""The pipeline choke point.

``run_dimension`` owns redaction, budgeting, truncation reporting and coverage
arithmetic. A dimension supplies only ``sources_sought`` data and a ``collect``
callable, so it never gets the chance to bypass any of those (Option D).

Every later dimension is written against this function's contract. Changing the
contract is a broad, cross-cutting rewrite — treat it accordingly.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace
from pathlib import Path

from . import redact as redact_module
from .budget import DEFAULT_BUDGET_BYTES
from .budget import budget as _run_budget
from .context import DEFAULT_SCOPE, RepoPathError, detect_context
from .models import (
    DimensionDescriptor,
    EvidencePack,
    RedactionHit,
    SourceMiss,
)
from .roles import (
    load_repo_config,
    resolution_warnings,
    resolve,
    source_provenance,
    unfilled_reason,
)
from .scope import ScopeError, resolve_scope

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
    *,
    ref: str | None = None,
    task_id: str | None = None,
    picks: Mapping[str, Sequence[str]] | None = None,
) -> EvidencePack:
    """Run one dimension against a repository and return its evidence pack.

    Works on any directory; git is not required for ``project`` scope (only
    ``changes`` will need it, in T003). ``picks`` are agent-input picks already
    validated by :func:`easy_verifier.core.roles.validate_agent_input`.
    """
    # Path validation lives in `detect_context` (T002), which raises
    # `RepoPathError` for a path that is absent or is not a directory. T004's
    # redaction of that message moved with it — the path itself is content, a
    # directory or file name can carry a secret, and an exception message is one
    # of the leak paths NFR-010 names.
    context = detect_context(repo_path, scope=scope)

    # Source roles resolve once, before `collect`, so every dimension -- the
    # bespoke three included -- reads from the same role -> files map, and the
    # coverage below can be counted by role (FR-016 amended, DDR-0006). A bad
    # `.easy-verifier.toml` raises here, before anything is read.
    resolution = None
    if descriptor.roles:
        resolution = resolve(
            context.repo_path,
            descriptor.roles,
            config=load_repo_config(context.repo_path),
            picks=picks,
        )
        context.role_files = dict(resolution.files)

    # Scope resolution remains centralized; narrow scopes receive only the
    # explicit selector their resolver requires and never widen on failure.
    try:
        resolved_scope = resolve_scope(
            scope,
            context.repo_path,
            context,
            ref=ref,
            task_id=task_id,
        )
    except ScopeError:
        resolved_scope = None
    context.resolved_scope = resolved_scope

    # The *call* is handed over, not its result: a conforming dimension can
    # still read and parse eagerly before returning its lazy iterator, and an
    # exception raised in that window must be redacted like any other. Passed
    # as a callable, not a single iterable, because `budget()` may invoke it
    # up to once per relevance tier.
    result = _run_budget(
        lambda: _redacting_exceptions(lambda: descriptor.collect(context)),
        scope=resolved_scope,
        limit_bytes=budget_bytes,
    )
    kept = result.excerpts
    truncated = result.truncation.truncated
    omitted_count = result.truncation.omitted_count
    hits = result.redactions

    sought = tuple(descriptor.sources_sought)
    # Clamped to the declared checklist. A file-backed role is filled only when
    # one of its resolved files was actually read -- a match that was never
    # read (budget, secret-bearing, unreadable) fills nothing. A pseudo-role,
    # or an entry of a role-less checklist, is filled when the dimension
    # recorded it found. Undeclared reads stay visible in `files_read`.
    read = frozenset(context.files_read)
    role_files = context.role_files
    found = tuple(
        source
        for source in sought
        if (
            any(path in read for path in role_files[source])
            if source in role_files
            else source in context.sources_found
        )
    )
    missing = _missing_sources(
        sought,
        found,
        context.sources_missing,
        truncated,
        _role_reasons(resolution, sought, found, context.sources_missing),
    )
    coverage_score = (len(found) / len(sought)) if sought else None
    warnings = context.warnings
    if resolution is not None:
        warnings = (*warnings, *resolution_warnings(resolution))

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
        truncation=result.truncation,
        # Unconditional: the pack is the only way evidence leaves the engine, so
        # copying the context's warnings here is what makes FR-004 hold for
        # every response and every report without any adapter opting in.
        warnings=warnings,
        approval_requests=tuple(context.approval_requests),
        source_provenance=(
            source_provenance(resolution) if resolution is not None else "rules"
        ),
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


def _role_reasons(
    resolution,
    sought: tuple[str, ...],
    found: tuple[str, ...],
    attempted_misses: list[SourceMiss],
) -> dict[str, str]:
    """Why each unfilled file-backed role is unfilled, from resolution + reads.

    A role with no match, or matched only by secret-bearing files, says so. A
    role whose matches were tried and failed carries the first failure. A role
    whose matches were never tried gets no entry here and falls through to
    *not examined*.
    """
    if resolution is None:
        return {}
    file_misses: dict[str, str] = {}
    for miss in attempted_misses:
        file_misses.setdefault(miss.source, miss.reason)
    reasons: dict[str, str] = {}
    for source in sought:
        if source in found or source not in resolution.files:
            continue
        # What reading established is the most specific account; resolution
        # alone (no match, secret-bearing by name) covers what was never tried.
        reason = None
        paths = resolution.files[source]
        failed = [path for path in paths if path in file_misses]
        if failed:
            distinct = {file_misses[path] for path in failed}
            if (
                len(failed) == len(paths)
                and len(distinct) == 1
                and file_misses[failed[0]].startswith("excluded: secret-bearing")
            ):
                # Every match is (or resolves to) a secret-bearing file: the
                # role is excluded, exactly as DDR-0002 words it.
                reason = file_misses[failed[0]]
            else:
                reason = (
                    f"matched file could not be used: {failed[0]}: "
                    f"{file_misses[failed[0]]}"
                )
        if reason is None:
            reason = unfilled_reason(resolution, source)
        if reason is not None:
            reasons[source] = reason
    return reasons


def _missing_sources(
    sought: tuple[str, ...],
    found: tuple[str, ...],
    attempted_misses: list[SourceMiss],
    truncated: bool,
    derived: Mapping[str, str] | None = None,
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
    # A reason the dimension recorded against the role itself (unresolved
    # scope, out-of-scope, pseudo-source) is the most specific; then what role
    # resolution and reading established; only then "not examined".
    reasons = {**(derived or {})}
    reasons.update(
        {miss.source: miss.reason for miss in attempted_misses if miss.source in sought}
    )
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
