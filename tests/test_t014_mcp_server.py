"""T014 acceptance tests for the local FastMCP adapter."""

from __future__ import annotations

import ast
import asyncio
import dataclasses
import importlib
import json
import subprocess
import sys
from pathlib import Path

from mcp.server.fastmcp.exceptions import ToolError

from easy_verifier.core.pipeline import run_dimension
from easy_verifier.dimensions import DIMENSIONS, dimension_names, list_dimensions

REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "src/easy_verifier/adapters/mcp_server.py"


def _server_module():
    return importlib.import_module("easy_verifier.adapters.mcp_server")


def _call(name: str, arguments: dict):
    _content, structured = asyncio.run(_server_module().mcp.call_tool(name, arguments))
    if set(structured) == {"result"}:
        return structured["result"]
    return structured


def test_server_registers_the_exact_ten_descriptor_derived_tools() -> None:
    module = _server_module()
    tools = asyncio.run(module.mcp.list_tools())
    by_name = {tool.name: tool for tool in tools}

    assert set(by_name) == {
        *dimension_names(),
        "list_dimensions",
        "combined",
        "write_report",
    }
    for item in list_dimensions():
        assert by_name[item.name].description == item.purpose


def test_dimension_tool_matches_the_shared_core() -> None:
    result = _call(
        "architecture",
        {"repo": str(REPO_ROOT), "scope": "project", "budget_bytes": 120_000},
    )
    expected = json.loads(
        json.dumps(
            dataclasses.asdict(
                run_dimension(DIMENSIONS["architecture"], REPO_ROOT, scope="project")
            )
        )
    )

    assert result == expected


def test_discovery_and_combined_tools_return_structured_data() -> None:
    discovery = _call("list_dimensions", {})
    combined = _call(
        "combined",
        {
            "dimensions": ["security", "architecture"],
            "repo": str(REPO_ROOT),
            "scope": "project",
        },
    )

    assert {item["name"] for item in discovery} == set(dimension_names())
    assert [slot["dimension"] for slot in combined["slots"]] == [
        "architecture",
        "security",
    ]


def test_write_report_returns_no_absolute_container_path(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Target\n", encoding="utf-8")

    result = _call(
        "write_report",
        {
            "findings": [],
            "repo": str(tmp_path),
            "dimensions": ["architecture"],
        },
    )

    assert set(result) == {"path", "advisory"}
    assert result["path"].startswith("reports/")
    assert (tmp_path / result["path"]).is_file()
    assert str(tmp_path) not in json.dumps(result)


def test_default_transport_is_stdio_and_stdout_stays_empty(monkeypatch, capsys) -> None:
    module = _server_module()
    calls = []
    monkeypatch.setattr(
        module.mcp, "run", lambda *args, **kwargs: calls.append((args, kwargs))
    )

    assert module.main([]) == 0

    assert calls == [((), {})]
    assert capsys.readouterr().out == ""


def test_http_requires_opt_in_and_loopback_cannot_be_overridden(
    monkeypatch,
) -> None:
    monkeypatch.setenv("FASTMCP_HOST", "0.0.0.0")
    module = importlib.reload(_server_module())
    calls = []
    monkeypatch.setattr(
        module.mcp, "run", lambda *args, **kwargs: calls.append((args, kwargs))
    )

    assert module.mcp.settings.host == "127.0.0.1"
    assert module.main(["--http"]) == 0
    assert calls == [((), {"transport": "sse"})]


def test_adapter_is_structurally_thin_and_has_no_outbound_client() -> None:
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    imported = {
        alias.name.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imported.update(
        node.module.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    )

    assert not (imported & {"httpx", "requests", "socket", "urllib"})
    forbidden_calls = {"open", "read_text", "read_bytes", "write_text", "write_bytes"}
    assert (
        not {
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        & forbidden_calls
    )
    source = MODULE_PATH.read_text(encoding="utf-8")
    assert "0.0.0.0" not in source
    assert '"::"' not in source


def test_tool_error_is_structured_and_server_survives() -> None:
    async def exercise() -> None:
        try:
            await _server_module().mcp.call_tool(
                "architecture", {"repo": "/nope/does-not-exist"}
            )
        except ToolError as exc:
            assert "does not exist" in str(exc)
        else:  # pragma: no cover - required assertion branch
            raise AssertionError("invalid repository should produce an MCP tool error")

        assert len(await _server_module().mcp.list_tools()) == 10

    asyncio.run(exercise())


def test_module_import_emits_nothing_to_stdout() -> None:
    env = {"PYTHONPATH": str(REPO_ROOT / "src")}
    completed = subprocess.run(
        [sys.executable, "-c", "import easy_verifier.adapters.mcp_server"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )

    assert completed.returncode == 0
    assert completed.stdout == ""
