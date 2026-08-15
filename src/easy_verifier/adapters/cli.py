"""Path-mode CLI adapter (FR-020, FR-021).

Parses arguments, calls the core, serializes the result. It reads no files,
builds no excerpts and does no coverage arithmetic — all of that belongs to
``run_dimension``, so that this adapter and the MCP adapter (T009) cannot drift
apart (FR-022).

    python -m easy_verifier.adapters.cli architecture --repo .
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from collections.abc import Sequence

from ..core.pipeline import DEFAULT_BUDGET_BYTES, RepoPathError, run_dimension
from ..dimensions import DIMENSIONS


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="easy-verifier",
        description="Print an evidence pack for one dimension of a repository.",
    )
    parser.add_argument(
        "dimension", choices=sorted(DIMENSIONS), help="dimension to run"
    )
    parser.add_argument("--repo", default=".", help="path to the target repository")
    parser.add_argument(
        "--budget-bytes",
        type=int,
        default=DEFAULT_BUDGET_BYTES,
        help="byte ceiling for excerpt text",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    try:
        pack = run_dimension(
            DIMENSIONS[args.dimension],
            repo_path=args.repo,
            budget_bytes=args.budget_bytes,
        )
    except RepoPathError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(dataclasses.asdict(pack), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
