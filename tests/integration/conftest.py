"""Independent process-boundary helpers for the T017 release gate."""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CLI = [sys.executable, "-m", "easy_verifier.adapters.cli"]


def verifier_env() -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    return env


def run_cli(
    *args: str, input_text: str | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [*CLI, *args],
        input=input_text,
        capture_output=True,
        text=True,
        env=verifier_env(),
        check=False,
    )


def cli_json(*args: str, input_text: str | None = None) -> dict | list:
    completed = run_cli(*args, input_text=input_text)
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def mcp_call(name: str, arguments: dict) -> object:
    from easy_verifier.adapters import mcp_server

    _content, result = asyncio.run(mcp_server.mcp.call_tool(name, arguments))
    if isinstance(result, dict) and set(result) == {"result"}:
        return result["result"]
    return result


def target_repo(path: Path, *, kit: bool = False) -> Path:
    path.mkdir()
    (path / "README.md").write_text("# Integration target\n", encoding="utf-8")
    if kit:
        (path / "PROJECT_SPEC.md").write_text("# Spec\n", encoding="utf-8")
        (path / "PRD.md").write_text("# PRD\n", encoding="utf-8")
        (path / "PROJECT_KANBAN.md").write_text("# Board\n", encoding="utf-8")
        (path / "tasks").mkdir()
        (path / "tasks/TASK_GUIDE_T017.md").write_text("# Guide\n", encoding="utf-8")
        (path / "memory").mkdir()
    return path


def require_docker() -> None:
    probe = subprocess.run(
        ["docker", "info"], capture_output=True, text=True, check=False
    )
    if probe.returncode != 0:
        message = probe.stderr.strip() or "Docker daemon is unavailable"
        if os.environ.get("T017_REQUIRE_DOCKER") == "1":
            pytest.fail(f"T017 container proof unavailable: {message}")
        pytest.skip(f"container proof NOT VERIFIED: {message}")
