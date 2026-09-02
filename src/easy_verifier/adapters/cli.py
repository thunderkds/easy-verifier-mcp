"""Thin path-mode CLI over the shared easy-verifier core."""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from ..core.findings import ValidationError
from ..core.pipeline import (
    DEFAULT_BUDGET_BYTES,
    DEFAULT_SCOPE,
    RepoPathError,
    run_dimension,
)
from ..core.report import ReportWriteError
from ..core.report import write_report as core_write_report
from ..core.scope import VALID_KINDS
from ..core.synthesis import combined_pack
from ..dimensions import DIMENSIONS, dimension_names, list_dimensions

VALIDATION_EXIT = 2
OPERATIONAL_EXIT = 3
_COMBINED = "combined"
_DISCOVERY = "list-dimensions"
_WRITE_REPORT = "write-report"


def _dimension_help() -> str:
    lines = ["dimensions:"]
    lines.extend(f"  {item.name}: {item.purpose}" for item in list_dimensions())
    return "\n".join(lines)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="easy-verifier",
        description="Gather citable repository evidence as machine-readable JSON.",
        epilog=_dimension_help(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    commands = parser.add_subparsers(dest="operation", required=True)

    commands.add_parser(
        _DISCOVERY,
        help="list every evidence dimension and its declared sources",
    )

    for descriptor in list_dimensions():
        command = commands.add_parser(descriptor.name, help=descriptor.purpose)
        _add_target_arguments(command)

    combined = commands.add_parser(
        _COMBINED,
        help="gather several dimensions into one combined pack",
    )
    _add_target_arguments(combined)
    combined.add_argument(
        "--dimensions",
        required=True,
        help="comma-separated dimension names",
    )

    report = commands.add_parser(
        _WRITE_REPORT,
        help="validate findings and write an evidence report",
    )
    _add_target_arguments(report)
    report.add_argument(
        "--dimensions",
        help="comma-separated dimensions to gather; defaults to all seven",
    )
    report.add_argument(
        "--findings",
        metavar="PATH",
        help="findings JSON file; takes precedence over piped stdin",
    )
    return parser


def _add_target_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--repo", default=".", help="target repository (default: cwd)")
    parser.add_argument(
        "--scope",
        choices=sorted(VALID_KINDS),
        default=DEFAULT_SCOPE,
        help="repository scope to evaluate",
    )
    parser.add_argument(
        "--range",
        "--ref",
        dest="ref",
        help="local git ref or range for changes scope",
    )
    parser.add_argument(
        "--task",
        "--task-id",
        dest="task_id",
        help="task identifier for task scope",
    )
    parser.add_argument(
        "--budget-bytes",
        type=int,
        default=DEFAULT_BUDGET_BYTES,
        help="byte ceiling for excerpt text",
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if args.operation == _DISCOVERY:
            return _emit([dataclasses.asdict(item) for item in list_dimensions()])
        if args.operation == _COMBINED:
            return _run_combined(args)
        if args.operation == _WRITE_REPORT:
            return _run_report(args)
        return _run_single(args)
    except BrokenPipeError:
        return 0
    except (RepoPathError, ReportWriteError, OSError) as exc:
        print(f"operational error: {exc}", file=sys.stderr)
        return OPERATIONAL_EXIT
    except (ValidationError, ValueError) as exc:
        print(f"validation error: {exc}", file=sys.stderr)
        return VALIDATION_EXIT


def _run_single(args: argparse.Namespace) -> int:
    pack = run_dimension(
        DIMENSIONS[args.operation],
        repo_path=args.repo,
        scope=args.scope,
        budget_bytes=args.budget_bytes,
        ref=args.ref,
        task_id=args.task_id,
    )
    for warning in pack.warnings:
        print(f"warning [{pack.mode}]: {warning}", file=sys.stderr)
    return _emit(dataclasses.asdict(pack))


def _run_combined(args: argparse.Namespace) -> int:
    result = combined_pack(
        _parse_dimensions(args.dimensions),
        repo_path=args.repo,
        scope=args.scope,
        budget_bytes=args.budget_bytes,
        ref=args.ref,
        task_id=args.task_id,
    )
    return _emit(dataclasses.asdict(result))


def _run_report(args: argparse.Namespace) -> int:
    findings = _read_findings(args.findings)
    packs = combined_pack(
        _parse_dimensions(args.dimensions) if args.dimensions else dimension_names(),
        repo_path=args.repo,
        scope=args.scope,
        budget_bytes=args.budget_bytes,
        ref=args.ref,
        task_id=args.task_id,
    )
    result = core_write_report(findings, packs, args.repo)
    return _emit({"path": result.path, "advisory": result.advisory})


def _read_findings(path: str | None) -> bytes:
    if path is not None:
        return Path(path).read_bytes()
    if sys.stdin.isatty():
        raise ValueError(
            "write-report requires --findings PATH or findings JSON on stdin"
        )
    return sys.stdin.buffer.read()


def _parse_dimensions(value: str) -> list[str]:
    return [name.strip() for name in value.split(",") if name.strip()]


def _emit(payload: object) -> int:
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
