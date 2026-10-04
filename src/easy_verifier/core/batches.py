"""Priority batches for code-tier sources above the read cap (T068, DDR-0010 §3–§5).

Above a dimension's source cap, sources are not skipped. They are ordered by
**purpose class** (declared below), then **git churn** descending, then path,
and read in batches of the cap. The caller names only how many batches to read
(FR-062): the engine re-derives the order and reads batches 1…N afresh on every
call, so nothing here keeps state and the same repository and batch count
always give the same plan.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from fnmatch import fnmatchcase
from pathlib import Path, PurePosixPath

from .findings import ValidationError
from .git import run_git_text

CHURN_COMMITS = 400
"""Non-merge local commits counted for churn; mirrors blast-radius's hotspot
window (``blast_radius._HOTSPOT_COMMITS``)."""

ALL = "all"

_LINGUIST = (
    "https://github.com/github-linguist/linguist/blob/"
    "d0921d10bb68a1249fc9eac64e472759f36e2fd8/lib/linguist/"
)


@dataclass(frozen=True)
class PurposeClass:
    """One purpose class: matched on any lower-cased directory segment or on
    the lower-cased file name (``fnmatch`` patterns)."""

    name: str
    rank: int
    directories: frozenset[str]
    names: tuple[str, ...]
    basis: str
    """A citation URL, or ``project-default`` when no standard names these."""


PURPOSE_CLASSES: tuple[PurposeClass, ...] = (
    PurposeClass(
        "application/server source",
        0,
        frozenset(
            {
                "server",
                "servers",
                "backend",
                "api",
                "service",
                "services",
                "internal",
                "cmd",
                "handlers",
                "controllers",
                "routes",
            }
        ),
        (),
        "project-default",
    ),
    PurposeClass("other application source", 1, frozenset(), (), "project-default"),
    PurposeClass(
        "scripts/tooling",
        2,
        frozenset(
            {
                "scripts",
                "script",
                "tools",
                "tooling",
                "bin",
                "bench",
                "benchmarks",
                "example",
                "examples",
                "fixtures",
            }
        ),
        (
            "gruntfile.js",
            "gulpfile.js",
            "*.config.js",
            "*.config.ts",
            "*.config.mjs",
            "*.config.cjs",
            "setup.py",
            "noxfile.py",
            "fabfile.py",
        ),
        "project-default",
    ),
    PurposeClass(
        "generated/vendored",
        3,
        frozenset(
            {
                "vendor",
                "vendors",
                "third_party",
                "third-party",
                "thirdparty",
                "node_modules",
                "bower_components",
                "dist",
                "generated",
                "__generated__",
            }
        ),
        (
            "*.min.js",
            "*-min.js",
            "*.pb.go",
            "*_pb2.py",
            "*_pb2_grpc.py",
            "*.generated.*",
            "*_generated.go",
            "*.g.cs",
            "*.designer.cs",
        ),
        _LINGUIST + "vendor.yml and " + _LINGUIST + "generated.rb (a subset)",
    ),
)
"""Purpose classes in rank order (user, DDR-0010 §3). Generated/vendored files
are ordered last, never dropped."""

_MATCH_ORDER = (3, 2, 0)
"""Most specific first: a vendored file under ``server/`` is vendored, a script
under ``backend/`` is tooling. Anything unmatched is rank 1."""

_OTHER_RANK = 1


def purpose_rank(path: str) -> int:
    """The purpose-class rank of a repository-relative path."""
    pure = PurePosixPath(path)
    segments = {part.lower() for part in pure.parts[:-1]}
    name = pure.name.lower()
    for rank in _MATCH_ORDER:
        item = PURPOSE_CLASSES[rank]
        if segments & item.directories or any(
            fnmatchcase(name, pattern) for pattern in item.names
        ):
            return rank
    return _OTHER_RANK


class BatchInputError(ValidationError):
    """``batches`` is malformed or out of range.

    A :class:`ValidationError`, so ``combined_pack`` re-raises it and both
    adapters report it as one (CLI exit 2, MCP tool error). Built from one
    message so ``pipeline._redacting_exceptions`` can rebuild it unchanged
    when it is raised inside a dimension's ``collect``.
    """

    def __init__(self, message: str) -> None:
        self.errors = (message,)
        Exception.__init__(self, message)


def parse_batches(value: object) -> int | str:
    """``value`` as a batch count: an int ≥ 1 or ``"all"``; else an error."""
    if value == ALL or (type(value) is int and value >= 1):
        return value  # type: ignore[return-value]
    raise BatchInputError(
        f'batches: must be a whole number of at least 1, or "all"; got {_shape(value)}'
    )


def _shape(value: object) -> str:
    """A short, safe description of a rejected value (never echoes text)."""
    if type(value) is int:
        return str(value)
    return type(value).__name__


def batches_total(count: int, size: int) -> int:
    return max(1, math.ceil(count / size))


def resolve_count(requested: int | str, total: int) -> int:
    """The number of batches to read; out of range is an error, never clamped."""
    if requested == ALL:
        return total
    if not 1 <= requested <= total:  # type: ignore[operator]
        raise BatchInputError(
            f"batches: {requested} is out of range; this scope has {total} "
            f"batch{'' if total == 1 else 'es'} of source files"
        )
    return requested  # type: ignore[return-value]


@dataclass(frozen=True)
class BatchPlan:
    """Every candidate in priority order, and how many batches are read."""

    ordered: tuple[str, ...]
    batch_size: int
    batches_done: int
    batches_total: int
    order: str
    """How ``ordered`` was ordered, for disclosure."""

    @property
    def selected(self) -> tuple[str, ...]:
        """The files of batches 1…``batches_done``."""
        return self.ordered[: self.batches_done * self.batch_size]


def plan(
    repo: str | Path, candidates, batch_size: int, requested: int | str
) -> BatchPlan:
    """Order ``candidates`` (purpose class → churn → path) and select batches
    1…``requested``. Raises :class:`BatchInputError` if out of range."""
    total = batches_total(len(candidates), batch_size)
    done = resolve_count(requested, total)
    churn, unavailable = _churn(Path(repo))
    ordered = tuple(
        sorted(set(candidates), key=lambda p: (purpose_rank(p), -churn[p], p))
    )
    classes = ", ".join(item.name for item in PURPOSE_CLASSES)
    if unavailable is None:
        order = (
            f"purpose class ({classes}), then git churn: commits touching the "
            f"file in the last {CHURN_COMMITS} non-merge local commits (most "
            "first), then path"
        )
    else:
        order = (
            f"purpose class ({classes}), then path; git churn was not used: "
            f"{unavailable}"
        )
    return BatchPlan(ordered, batch_size, done, total, order)


def _churn(repo: Path) -> tuple[Counter[str], str | None]:
    """Commits naming each file in the last :data:`CHURN_COMMITS` non-merge
    commits, and why there is no count (``None`` when there is one).

    ``--relative`` keeps paths relative to the target even when it is a
    subdirectory of its repository; ``-z`` keeps them unquoted.
    """
    ok, out, _ = run_git_text(
        repo,
        [
            "log",
            "-z",
            "--no-merges",
            "--relative",
            "--name-only",
            "--format=",
            "-n",
            str(CHURN_COMMITS),
        ],
    )
    if not ok:
        return Counter(), "not a git repository, or git history could not be read"
    names = (name.strip("\n") for name in out.split("\0"))
    return Counter(name for name in names if name), None


__all__ = [
    "ALL",
    "CHURN_COMMITS",
    "PURPOSE_CLASSES",
    "BatchInputError",
    "BatchPlan",
    "PurposeClass",
    "batches_total",
    "parse_batches",
    "plan",
    "purpose_rank",
    "resolve_count",
]
