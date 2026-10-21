"""Thin local FastMCP adapter for the easy-verifier core.

The default transport is stdio. Streamable HTTP (one shared server for every
repository, DDR-0013) and legacy HTTP/SSE exist only behind an explicit opt-in
and are always loopback-bound; callers cannot configure a host address.
"""

from __future__ import annotations

import argparse
import dataclasses
import functools
import logging
import os
import sys
import threading
from collections.abc import Callable, Sequence
from typing import Any, Literal

import anyio.to_thread
from mcp.server.fastmcp import FastMCP

from ..core.models import to_json_dict
from ..core.pipeline import DEFAULT_BUDGET_BYTES, DEFAULT_SCOPE, run_dimension
from ..core.report import write_report as core_write_report
from ..core.score import report_dimensions, score_repository
from ..core.synthesis import combined_pack
from ..dimensions import DIMENSIONS, list_dimensions

LOOPBACK_HOST = "127.0.0.1"
DEFAULT_HTTP_PORT = 8766
PORT_ENV = "EASY_VERIFIER_PORT"

_CORE_LOCK = threading.Lock()
"""One process serves many sessions over streamable HTTP. The core is not
made thread-safe; instead every tool call holds this lock (DDR-0013)."""

mcp = FastMCP(
    "easy-verifier",
    instructions="Gather citable repository evidence without making judgments.",
    host=LOOPBACK_HOST,
    log_level="WARNING",
)


def _serialised(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Run ``fn`` in a worker thread while holding the process-wide lock.

    The worker thread keeps the event loop free for other sessions (a second
    client can connect and list tools while a long ``score`` runs); the lock
    keeps two core calls from ever running at once.
    """

    def locked(kwargs: dict[str, Any]) -> Any:
        with _CORE_LOCK:
            return fn(**kwargs)

    @functools.wraps(fn)
    async def call(**kwargs: Any) -> Any:
        return await anyio.to_thread.run_sync(locked, kwargs)

    return call


def _tool(**options: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Register ``fn`` as a serialised tool; the module keeps the plain
    function so in-process callers are unaffected."""

    def register(fn: Callable[..., Any]) -> Callable[..., Any]:
        mcp.tool(**options)(_serialised(fn))
        return fn

    return register


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
        return to_json_dict(pack)

    return handle


for _item in list_dimensions():
    _tool(name=_item.name, description=_item.purpose, structured_output=True)(
        _dimension_handler(DIMENSIONS[_item.name])
    )


@_tool(
    name="list_dimensions",
    description="List every evidence dimension, its purpose, and declared sources.",
    structured_output=True,
)
def discover_dimensions() -> list[dict[str, Any]]:
    """Return repository-independent metadata for every dimension."""
    return [dataclasses.asdict(item) for item in list_dimensions()]


@_tool(
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
    return to_json_dict(
        combined_pack(
            dimensions,
            repo_path=repo,
            scope=scope,
            budget_bytes=budget_bytes,
            ref=ref,
            task_id=task_id,
        )
    )


@_tool(
    name="score",
    description=(
        "Rate all seven dimensions and optionally assess findings. If the "
        "response carries needs_input.picks.groups, some source roles have "
        "no matching file but the repository holds candidates: for the "
        "roles you choose to fill, call score again with "
        'agent_input={"picks": {role: [path, ...]}} to raise their coverage. '
        "If it carries needs_input.gate_evaluations, those dimensions' rules "
        "abstained or sit within 10% of a threshold: read the listed "
        "evidence_refs and call score again with the same agent_input plus "
        '"gate_evaluations": {dimension: {"score": 0-100, "confidence": 0-1, '
        '"evidence_refs": [ref, ...]}}. Each evaluation blends in as '
        "rules x (1 - w) + agent x w with w = 0.5 x confidence, or stands "
        "alone as agent-rated where the rules abstained; parts are always "
        "shown. If it carries needs_input.reference, the detected languages "
        "or frameworks (detected_stack) lack registry fields the rules read: "
        "follow its instructions (at most 2 lookups per field, official docs "
        "first, else ask the user one question at a time) and send the "
        "answers as agent_input.registry_entries on the next call. If it "
        "carries needs_input.review, show each listed registry entry to the "
        "user once (value and link), ask whether it is good, needs "
        "improvement, or should be rejected, and send the answers as "
        "agent_input.reviews on the next call. If it carries "
        "needs_input.continue_batches, the repository has more source files "
        "than one read: only the listed share was read, in priority order. "
        "Ask the user its question -- read the next batch (more tokens) or "
        "stop -- and to continue call score again with the same agent_input "
        'plus "batches": batches_done + 1 (or "all"). If it carries '
        "needs_input.change_kind (changes or worktree scope), the engine "
        "detected what the change is for (proposal, from the listed signals): "
        "read the diff and send agent_input.change_kind = "
        '{"value": one of allowed, "reason": "..."} on the next call to '
        "confirm or override it; the change_risk rules follow that kind. "
        "If it carries needs_input.test_pairs, the engine matched the "
        "change's tests to its changed source files (proposals, by symbol "
        "reference or by name): judge each and send agent_input.test_pairs = "
        '[{"source": ..., "test": ..., "verdict": "confirm" or "reject", '
        '"reason": "..."}] on the next call; to add a pair, confirm it with '
        '"ref": "test-path:line". '
        "Optional domain packs "
        "are never guessed: only if the user confirms the repository handles "
        "patient health information, send agent_input.packs = "
        '["healthcare"] (PHI in test data and logs, BAA and residency '
        "documents), or that it handles money, send agent_input.packs = "
        '["finance"] (float money fields, ledger audit columns and '
        "append-only ledgers), or that it has a web frontend to check for "
        "accessibility, send agent_input.packs = "
        '["frontend-a11y"] (image alt text, form labels, aria-hidden on '
        "focusable elements, viewport, browser support); a repository may "
        "also list them in "
        ".easy-verifier.toml "
        "packs. Otherwise use the response as-is. "
        "budget_bytes limits the evidence excerpts read, not the size of the "
        "reply. By default (detail=\"summary\") the reply leaves out the "
        "per-metric rows (metrics.metrics, most of the full reply's size); "
        'ratings, overall, improvement_plan, warnings and provenance are '
        'unchanged. Pass detail="full" to get every metric row.'
    ),
    structured_output=True,
)
def score(
    repo: str = ".",
    scope: str = DEFAULT_SCOPE,
    budget_bytes: int = DEFAULT_BUDGET_BYTES,
    ref: str | None = None,
    task_id: str | None = None,
    findings: list[dict[str, Any]] | None = None,
    agent_input: dict[str, Any] | None = None,
    detail: Literal["summary", "full"] = "summary",
) -> dict[str, Any]:
    """Delegate the complete rating operation to the shared score core.

    ``detail="summary"`` (T122, FR-089) drops ``metrics.metrics``, the
    per-metric rows that are ~90% of the payload; ``metrics`` keeps
    ``dimensions_without_pack`` (small, and it says which dimensions have no
    rows at all). Gate ``evidence_refs`` are excerpt refs from the packs, never
    metric rows, so ``needs_input`` works unchanged. The filter lives here, so
    the CLI payload and the core are untouched.

    ``needs_input`` (FR-035) is MCP-only: the shared core can compute it, but
    only this adapter asks for it and puts it on the wire (FR-021, FR-034,
    FR-040) — the CLI payload never carries the key, and never pays for the
    extra walk that produces it. At most one of ``picks`` (T027) and
    ``gate_evaluations`` (T028) is asked per response; ``reference`` (T037)
    and ``review`` (T038) ride along with either.
    """
    result = score_repository(
        repo,
        scope=scope,
        budget_bytes=budget_bytes,
        ref=ref,
        task_id=task_id,
        findings=findings,
        agent_input=agent_input,
        detect_gates=True,
    )
    payload = result.to_dict()
    if result.registry_notes:
        payload["registry_notes"] = list(result.registry_notes)
    needs_input: dict[str, Any] = {}
    if result.reference is not None:
        needs_input["reference"] = result.reference
    if result.review is not None:
        needs_input["review"] = result.review
    if result.continue_batches is not None:
        needs_input["continue_batches"] = result.continue_batches
    if result.change_kind_question is not None:
        needs_input["change_kind"] = result.change_kind_question
    if result.test_pairs_question is not None:
        needs_input["test_pairs"] = result.test_pairs_question
    if result.needs_input is not None:
        needs_input["picks"] = result.needs_input
    elif result.gate_requests is not None:
        needs_input["gate_evaluations"] = list(result.gate_requests)
    if needs_input:
        payload["needs_input"] = needs_input
    if detail == "summary":
        payload.get("metrics", {}).pop("metrics", None)
    return payload


@_tool(
    name="write_report",
    description=(
        "Validate findings and write a self-contained evidence report. To "
        "attach a repo-specific fix to an item of score's improvement_plan, "
        "pass the same agent_input plus "
        '"improvements": [{"dimension": ..., "metric_name": ..., '
        '"suggestion": "..."}]; it is shown labelled agent beside the engine '
        "fix. Naming an item not in the plan, or naming one twice, is a "
        "validation error. To add your own short summary for the user, pass "
        '"summary": "..." (one paragraph, at most 2000 characters) in '
        "agent_input; it is shown labelled agent after the engine summary "
        "that opens the report."
    ),
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
    agent_input: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Gather the cited dimensions, validate findings, and write the report."""
    default, active = report_dimensions(repo, agent_input, scope)
    packs = combined_pack(
        dimensions or default,
        repo_path=repo,
        scope=scope,
        budget_bytes=budget_bytes,
        ref=ref,
        task_id=task_id,
        agent_input=agent_input,
        packs=active,
    )
    result = core_write_report(findings, packs, repo, agent_input=agent_input)
    return {"path": result.path, "advisory": result.advisory}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="easy-verifier-mcp")
    transport = parser.add_mutually_exclusive_group()
    transport.add_argument(
        "--http",
        action="store_true",
        help="opt in to legacy HTTP/SSE on 127.0.0.1; default is stdio",
    )
    transport.add_argument(
        "--transport",
        choices=("stdio", "streamable-http"),
        default="stdio",
        help=(
            "streamable-http serves /mcp on 127.0.0.1:$EASY_VERIFIER_PORT "
            f"(default {DEFAULT_HTTP_PORT}) for many sessions; default is stdio"
        ),
    )
    return parser


def _http_port(parser: argparse.ArgumentParser) -> int:
    raw = os.environ.get(PORT_ENV, "").strip()
    if not raw:
        return DEFAULT_HTTP_PORT
    if not (raw.isdigit() and 1 <= int(raw) <= 65535):
        parser.error(f"{PORT_ENV} must be a port number from 1 to 65535, got {raw!r}")
    return int(raw)


def main(argv: Sequence[str] | None = None) -> int:
    """Run stdio by default, or a loopback-only HTTP transport after opt-in."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(stream=sys.stderr)
    # Reasserted at run time: FastMCP's own FASTMCP_* settings never move the
    # bind address off loopback (FR-019b, NFR-012).
    mcp.settings.host = LOOPBACK_HOST
    if args.http:
        mcp.run(transport="sse")
    elif args.transport == "streamable-http":
        mcp.settings.port = _http_port(parser)
        mcp.run(transport="streamable-http")
    else:
        mcp.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
