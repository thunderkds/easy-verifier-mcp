"""Thin local FastMCP adapter for the easy-verifier core.

The default transport is stdio. Legacy HTTP/SSE exists only behind an explicit
opt-in and is always loopback-bound; callers cannot configure a host address.
"""

from __future__ import annotations

import argparse
import dataclasses
import logging
import sys
from collections.abc import Sequence
from typing import Any

from mcp.server.fastmcp import FastMCP

from ..core.pipeline import DEFAULT_BUDGET_BYTES, DEFAULT_SCOPE, run_dimension
from ..core.report import write_report as core_write_report
from ..core.synthesis import combined_pack
from ..dimensions import DIMENSIONS, dimension_names, list_dimensions

LOOPBACK_HOST = "127.0.0.1"
mcp = FastMCP(
    "easy-verifier",
    instructions="Gather citable repository evidence without making judgments.",
    host=LOOPBACK_HOST,
    log_level="WARNING",
)


def _dimension_handler(descriptor):
    def handle(
        repo: str = ".",
        scope: str = DEFAULT_SCOPE,
        budget_bytes: int = DEFAULT_BUDGET_BYTES,
        ref: str | None = None,
        task_id: str | None = None,
    ) -> dict[str, Any]:
        pack = run_dimension(
            descriptor,
            repo_path=repo,
            scope=scope,
            budget_bytes=budget_bytes,
            ref=ref,
            task_id=task_id,
        )
        return dataclasses.asdict(pack)

    return handle


for _item in list_dimensions():
    mcp.tool(name=_item.name, description=_item.purpose, structured_output=True)(
        _dimension_handler(DIMENSIONS[_item.name])
    )


@mcp.tool(
    name="list_dimensions",
    description="List every evidence dimension, its purpose, and declared sources.",
    structured_output=True,
)
def discover_dimensions() -> list[dict[str, Any]]:
    """Return repository-independent metadata for every dimension."""
    return [dataclasses.asdict(item) for item in list_dimensions()]


@mcp.tool(
    name="combined",
    description="Gather several evidence dimensions into one combined pack.",
    structured_output=True,
)
def gather_combined(
    dimensions: list[str],
    repo: str = ".",
    scope: str = DEFAULT_SCOPE,
    budget_bytes: int = DEFAULT_BUDGET_BYTES,
    ref: str | None = None,
    task_id: str | None = None,
) -> dict[str, Any]:
    """Delegate a multi-dimension request to the shared synthesis core."""
    return dataclasses.asdict(
        combined_pack(
            dimensions,
            repo_path=repo,
            scope=scope,
            budget_bytes=budget_bytes,
            ref=ref,
            task_id=task_id,
        )
    )


@mcp.tool(
    name="write_report",
    description="Validate findings and write a self-contained evidence report.",
    structured_output=True,
)
def render_report(
    findings: list[dict[str, Any]],
    repo: str = ".",
    dimensions: list[str] | None = None,
    scope: str = DEFAULT_SCOPE,
    budget_bytes: int = DEFAULT_BUDGET_BYTES,
    ref: str | None = None,
    task_id: str | None = None,
) -> dict[str, Any]:
    """Gather the cited dimensions, validate findings, and write the report."""
    packs = combined_pack(
        dimensions or dimension_names(),
        repo_path=repo,
        scope=scope,
        budget_bytes=budget_bytes,
        ref=ref,
        task_id=task_id,
    )
    result = core_write_report(findings, packs, repo)
    return {"path": result.path, "advisory": result.advisory}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="easy-verifier-mcp")
    parser.add_argument(
        "--http",
        action="store_true",
        help="opt in to legacy HTTP/SSE on 127.0.0.1; default is stdio",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run stdio by default, or loopback-only SSE after explicit opt-in."""
    args = _build_parser().parse_args(argv)
    logging.basicConfig(stream=sys.stderr)
    if args.http:
        mcp.run(transport="sse")
    else:
        mcp.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
