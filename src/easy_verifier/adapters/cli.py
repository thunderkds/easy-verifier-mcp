"""Path-mode CLI adapter (FR-020, FR-021).

Parses arguments, calls the core, serializes the result. It reads no files,
builds no excerpts and does no coverage arithmetic — all of that belongs to
``run_dimension``/``combined_pack``, so that this adapter and the MCP adapter
(T009) cannot drift apart (FR-022).

    python -m easy_verifier.adapters.cli architecture --repo .
    python -m easy_verifier.adapters.cli combined --repo . \\
        --dimensions architecture,security
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from collections.abc import Sequence

from ..core.pipeline import DEFAULT_BUDGET_BYTES, RepoPathError, run_dimension
from ..core.scope import VALID_KINDS
from ..core.synthesis import combined_pack
from ..dimensions import DIMENSIONS

_COMBINED = "combined"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="easy-verifier",
        description="Print an evidence pack for one dimension of a repository, "
        "or several combined.",
    )
    parser.add_argument(
        "dimension",
        choices=sorted((*DIMENSIONS, _COMBINED)),
        help="dimension to run, or 'combined' to run several at once",
    )
    parser.add_argument("--repo", default=".", help="path to the target repository")
    parser.add_argument(
        "--scope",
        choices=sorted(VALID_KINDS),
        default="project",
        help="repository scope to evaluate",
    )
    parser.add_argument("--ref", help="local git ref/range for changes scope")
    parser.add_argument(
        "--task-id",
        help="task identifier for task scope",
    )
    parser.add_argument(
        "--budget-bytes",
        type=int,
        default=DEFAULT_BUDGET_BYTES,
        help="byte ceiling for excerpt text",
    )
    parser.add_argument(
        "--dimensions",
        help="comma-separated dimension names, required with 'combined', "
        "e.g. architecture,security",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.dimension == _COMBINED:
        if not args.dimensions:
            parser.error("'combined' requires --dimensions")
        return _run_combined(args)
    return _run_single(args)


def _run_single(args: argparse.Namespace) -> int:
    try:
        pack = run_dimension(
            DIMENSIONS[args.dimension],
            repo_path=args.repo,
            scope=args.scope,
            budget_bytes=args.budget_bytes,
            ref=args.ref,
            task_id=args.task_id,
        )
    except RepoPathError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    # `mode` and `warnings` are fields of the pack, so they are already in the
    # JSON. They are echoed on stderr as well because a standalone run's caveat
    # has to be visible to a human reading a terminal, not only to a parser
    # (FR-004) — stderr keeps stdout a clean JSON document.
    for warning in pack.warnings:
        print(f"warning [{pack.mode}]: {warning}", file=sys.stderr)

    print(json.dumps(dataclasses.asdict(pack), indent=2))
    return 0


def _run_combined(args: argparse.Namespace) -> int:
    names = [name.strip() for name in args.dimensions.split(",") if name.strip()]
    try:
        result = combined_pack(
            names,
            repo_path=args.repo,
            scope=args.scope,
            budget_bytes=args.budget_bytes,
            ref=args.ref,
            task_id=args.task_id,
        )
    except (RepoPathError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(dataclasses.asdict(result), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
