"""T101: one shared scoring container that every repository points at.

DDR-0013 / FR-019b amended. ``easy-verifier-mcp --transport streamable-http``
serves FastMCP streamable HTTP at ``/mcp`` on ``127.0.0.1:$EASY_VERIFIER_PORT``
(default 8766); every tool call is serialised by one process-wide lock;
``EASY_VERIFIER_REPORTS_DIR`` moves reports out of the evaluated repository;
compose gains a ``scorer`` service that runs it once for every repository.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
from contextlib import contextmanager, nullcontext
from pathlib import Path

import pytest
from integration.conftest import mcp_call, target_repo
from integration.test_adapter_parity import normalize

from easy_verifier.adapters import mcp_server
from easy_verifier.core.report import ReportWriteError

REPO_ROOT = Path(__file__).resolve().parents[1]
README = REPO_ROOT / "README.md"
DOCKER_GUIDE = REPO_ROOT / "docs" / "DOCKER_MCP_GUIDE.md"
SHARED_URL_COMMAND = (
    "claude mcp add --transport http easy-verifier http://127.0.0.1:8766/mcp"
)


# ---------------------------------------------------------------------------
# AC1: transport flag, port, loopback-only host
# ---------------------------------------------------------------------------


def test_parser_offers_streamable_http_and_keeps_stdio_and_http() -> None:
    parser = mcp_server._build_parser()
    assert parser.parse_args([]).transport == "stdio"
    assert parser.parse_args([]).http is False
    assert parser.parse_args(["--http"]).http is True
    assert (
        parser.parse_args(["--transport", "streamable-http"]).transport
        == "streamable-http"
    )


@pytest.mark.parametrize(
    "argv",
    [
        ["--host", "0.0.0.0"],
        ["--transport", "sse"],
        ["--http", "--transport", "streamable-http"],
    ],
)
def test_parser_refuses_a_host_and_conflicting_transports(argv: list[str]) -> None:
    with pytest.raises(SystemExit) as raised:
        mcp_server._build_parser().parse_args(argv)
    assert raised.value.code == 2


@pytest.fixture
def recorded_runs(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str, int]]:
    """Replace ``mcp.run`` and record what each transport would have bound."""
    runs: list[tuple[str, str, int]] = []
    settings = mcp_server.mcp.settings
    monkeypatch.setattr(settings, "host", settings.host)
    monkeypatch.setattr(settings, "port", settings.port)

    def fake_run(transport: str = "stdio", mount_path: str | None = None) -> None:
        runs.append((transport, settings.host, settings.port))

    monkeypatch.setattr(mcp_server.mcp, "run", fake_run)
    monkeypatch.delenv("EASY_VERIFIER_PORT", raising=False)
    return runs


def test_streamable_http_binds_loopback_on_the_default_port(recorded_runs) -> None:
    assert mcp_server.main(["--transport", "streamable-http"]) == 0
    assert recorded_runs == [("streamable-http", "127.0.0.1", 8766)]


def test_port_comes_from_the_environment(recorded_runs, monkeypatch) -> None:
    monkeypatch.setenv("EASY_VERIFIER_PORT", "9123")
    mcp_server.main(["--transport", "streamable-http"])
    assert recorded_runs == [("streamable-http", "127.0.0.1", 9123)]


def test_host_cannot_be_moved_off_loopback(recorded_runs, monkeypatch) -> None:
    """Neither FastMCP's own env settings nor a mutated settings object can
    move the bind address: it is reset to loopback right before serving."""
    monkeypatch.setenv("FASTMCP_HOST", "0.0.0.0")
    monkeypatch.setenv("EASY_VERIFIER_HOST", "0.0.0.0")
    mcp_server.mcp.settings.host = "0.0.0.0"
    mcp_server.main(["--transport", "streamable-http"])
    assert recorded_runs == [("streamable-http", "127.0.0.1", 8766)]


@pytest.mark.parametrize("value", ["abc", "0", "65536", "-1", ""])
def test_invalid_port_is_a_usage_error(recorded_runs, monkeypatch, value) -> None:
    monkeypatch.setenv("EASY_VERIFIER_PORT", value)
    if value == "":
        # Empty means unset: the default port.
        mcp_server.main(["--transport", "streamable-http"])
        assert recorded_runs == [("streamable-http", "127.0.0.1", 8766)]
        return
    with pytest.raises(SystemExit) as raised:
        mcp_server.main(["--transport", "streamable-http"])
    assert raised.value.code == 2
    assert recorded_runs == []


def test_stdio_and_legacy_http_are_unchanged(recorded_runs, monkeypatch) -> None:
    """stdio stays the default; ``--http`` stays SSE on FastMCP's own port --
    EASY_VERIFIER_PORT belongs to the new transport only."""
    monkeypatch.setenv("EASY_VERIFIER_PORT", "9123")
    port_before = mcp_server.mcp.settings.port
    mcp_server.main([])
    mcp_server.main(["--http"])
    assert recorded_runs == [
        ("stdio", "127.0.0.1", port_before),
        ("sse", "127.0.0.1", port_before),
    ]


# ---------------------------------------------------------------------------
# A real server process (AC1 bind, AC2 parity, AC4 concurrency)
# ---------------------------------------------------------------------------


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def _server_env(tmp: Path, **extra: str) -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    env["EASY_VERIFIER_SOT"] = str(tmp / "sot")
    env.pop("EASY_VERIFIER_REPORTS_DIR", None)
    env.update(extra)
    return env


@contextmanager
def _http_server(tmp: Path):
    port = _free_port()
    log = (tmp / "server.log").open("w")
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "easy_verifier.adapters.mcp_server",
            "--transport",
            "streamable-http",
        ],
        env=_server_env(tmp, EASY_VERIFIER_PORT=str(port)),
        stdin=subprocess.DEVNULL,
        stdout=log,
        stderr=subprocess.STDOUT,
    )
    try:
        deadline = time.monotonic() + 30
        while True:
            if process.poll() is not None:
                raise AssertionError((tmp / "server.log").read_text())
            try:
                socket.create_connection(("127.0.0.1", port), timeout=0.5).close()
                break
            except OSError:
                if time.monotonic() > deadline:
                    raise AssertionError("server never started listening") from None
                time.sleep(0.2)
        yield port
    finally:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
        log.close()


@pytest.fixture(scope="module")
def http_server(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("t101-server")
    with _http_server(tmp) as port:
        yield port


def _http_client():
    from mcp.client import streamable_http

    return getattr(streamable_http, "streamable_http_client", None) or (
        streamable_http.streamablehttp_client
    )


async def _over_http(port: int, work):
    from mcp import ClientSession

    async with _http_client()(f"http://127.0.0.1:{port}/mcp") as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            return await work(session)


async def _over_stdio(tmp: Path, work):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "easy_verifier.adapters.mcp_server"],
        env=_server_env(tmp),
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            return await work(session)


def _structured(result) -> dict:
    assert not result.isError, result.content
    return result.structuredContent


def test_listening_socket_is_bound_to_loopback_only(http_server) -> None:
    table = Path("/proc/net/tcp")
    if not table.exists():
        pytest.skip("no /proc/net/tcp to read listening sockets from")
    listening = [
        line.split()[1]
        for line in table.read_text().splitlines()[1:]
        if line.split()[3] == "0A"  # TCP_LISTEN
        and int(line.split()[1].split(":")[1], 16) == http_server
    ]
    assert listening == [f"0100007F:{http_server:04X}"]


@pytest.fixture(scope="module")
def two_repos(tmp_path_factory) -> tuple[Path, Path]:
    root = tmp_path_factory.mktemp("t101-repos")
    first = target_repo(root / "first", kit=True)
    second = target_repo(root / "second")
    (second / "app.py").write_text("def handler():\n    return 1\n", encoding="utf-8")
    for repo in (first, second):
        subprocess.run(["git", "init", "--quiet", str(repo)], check=True)
    return first, second


def test_http_lists_every_tool_and_scores_two_repos_like_stdio(
    http_server, two_repos, tmp_path
) -> None:
    first, second = two_repos

    async def work(session):
        tools = sorted(tool.name for tool in (await session.list_tools()).tools)
        scores = [
            _structured(await session.call_tool("score", {"repo": str(repo)}))
            for repo in (first, second)
        ]
        return tools, scores

    http_tools, http_scores = asyncio.run(_over_http(http_server, work))
    stdio_tools, stdio_scores = asyncio.run(_over_stdio(tmp_path, work))

    expected_tools = sorted(t.name for t in asyncio.run(mcp_server.mcp.list_tools()))
    assert http_tools == stdio_tools == expected_tools
    assert len(expected_tools) == 17
    assert normalize(http_scores[0]) == normalize(stdio_scores[0])
    assert normalize(http_scores[1]) == normalize(stdio_scores[1])
    # Two different repositories really were scored by the one process.
    assert normalize(http_scores[0]) != normalize(http_scores[1])


def test_two_sessions_scoring_concurrently_both_complete_correctly(
    http_server, two_repos
) -> None:
    first, second = two_repos

    def score(repo: Path):
        async def work(session):
            return _structured(await session.call_tool("score", {"repo": str(repo)}))

        return work

    async def concurrently():
        return await asyncio.gather(
            _over_http(http_server, score(first)),
            _over_http(http_server, score(second)),
        )

    together = asyncio.run(concurrently())
    alone = [asyncio.run(_over_http(http_server, score(r))) for r in (first, second)]
    assert [normalize(p) for p in together] == [normalize(p) for p in alone]


# ---------------------------------------------------------------------------
# AC4: one process-wide lock serialises every tool call
# ---------------------------------------------------------------------------


def _slow_core(events: list[str]):
    gate = threading.Lock()

    def fake_score_repository(repo, **_kwargs):
        with gate:
            events.append(f"enter {Path(repo).name}")
        time.sleep(0.3)
        with gate:
            events.append(f"exit {Path(repo).name}")

        class _Result:
            registry_notes = ()
            reference = review = continue_batches = None
            needs_input = gate_requests = None

            def to_dict(self):
                return {"repo": Path(repo).name}

        return _Result()

    return fake_score_repository


async def _two_concurrent_scores() -> list[object]:
    async def call(name: str):
        _content, result = await mcp_server.mcp.call_tool("score", {"repo": name})
        return result

    return await asyncio.gather(call("/r/a"), call("/r/b"))


def test_the_lock_serialises_concurrent_tool_calls(monkeypatch) -> None:
    events: list[str] = []
    monkeypatch.setattr(mcp_server, "score_repository", _slow_core(events))
    started = time.monotonic()
    results = asyncio.run(_two_concurrent_scores())
    assert sorted(r["repo"] for r in results) == ["a", "b"]
    assert [e.split()[0] for e in events] == ["enter", "exit", "enter", "exit"]
    assert events[0].split()[1] == events[1].split()[1]
    assert time.monotonic() - started >= 0.6


def test_without_the_lock_calls_would_interleave(monkeypatch) -> None:
    """Negative control: tool calls really run concurrently (off the event
    loop), so the serialisation above is the lock's doing, not an accident of
    a single-threaded loop."""
    events: list[str] = []
    monkeypatch.setattr(mcp_server, "score_repository", _slow_core(events))
    monkeypatch.setattr(mcp_server, "_CORE_LOCK", nullcontext())
    asyncio.run(_two_concurrent_scores())
    assert [e.split()[0] for e in events] == ["enter", "enter", "exit", "exit"]


def test_every_registered_tool_goes_through_the_lock(monkeypatch) -> None:
    class _Spy:
        entered = 0

        def __enter__(self):
            _Spy.entered += 1

        def __exit__(self, *exc):
            return False

    monkeypatch.setattr(mcp_server, "_CORE_LOCK", _Spy())
    mcp_call("list_dimensions", {})
    assert _Spy.entered == 1
    tools = asyncio.run(mcp_server.mcp.list_tools())
    for tool in tools:
        registered = mcp_server.mcp._tool_manager.get_tool(tool.name)
        assert registered.is_async, tool.name


# ---------------------------------------------------------------------------
# AC3: EASY_VERIFIER_REPORTS_DIR
# ---------------------------------------------------------------------------


def _tree(path: Path) -> list[str]:
    return sorted(p.relative_to(path).as_posix() for p in path.rglob("*"))


def test_reports_dir_receives_the_report_and_repo_is_untouched(
    tmp_path, monkeypatch
) -> None:
    repo = target_repo(tmp_path / "my-service")
    reports = tmp_path / "shared-reports"
    before = _tree(repo)
    monkeypatch.setenv("EASY_VERIFIER_REPORTS_DIR", str(reports))

    first = mcp_call(
        "write_report",
        {"repo": str(repo), "dimensions": ["architecture"], "findings": []},
    )
    second = mcp_call(
        "write_report",
        {"repo": str(repo), "dimensions": ["architecture"], "findings": []},
    )

    assert _tree(repo) == before
    written = Path(first["path"])
    assert written.is_absolute()
    assert written.parent == reports / "my-service"
    assert written.is_file() and written.suffix == ".html"
    assert first["advisory"] is not None
    assert second["advisory"] is None
    assert Path(second["path"]).parent == reports / "my-service"


def test_unset_reports_dir_writes_into_the_repo_as_before(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.delenv("EASY_VERIFIER_REPORTS_DIR", raising=False)
    repo = target_repo(tmp_path / "plain")
    result = mcp_call(
        "write_report",
        {"repo": str(repo), "dimensions": ["architecture"], "findings": []},
    )
    assert result["path"].startswith("reports/evidence-report-")
    assert (repo / result["path"]).is_file()


def test_empty_reports_dir_means_unset(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("EASY_VERIFIER_REPORTS_DIR", "")
    repo = target_repo(tmp_path / "plain")
    result = mcp_call(
        "write_report",
        {"repo": str(repo), "dimensions": ["architecture"], "findings": []},
    )
    assert result["path"].startswith("reports/")


def test_relative_reports_dir_is_refused(tmp_path, monkeypatch) -> None:
    from easy_verifier.core.report import write_report
    from easy_verifier.core.synthesis import combined_pack

    repo = target_repo(tmp_path / "plain")
    monkeypatch.setenv("EASY_VERIFIER_REPORTS_DIR", "relative/reports")
    packs = combined_pack(["architecture"], repo_path=str(repo))
    with pytest.raises(ReportWriteError, match="absolute"):
        write_report([], packs, repo)
    assert not (repo / "reports").exists()


def test_symlinked_repo_dir_out_of_reports_dir_is_refused(
    tmp_path, monkeypatch
) -> None:
    from easy_verifier.core.report import write_report
    from easy_verifier.core.synthesis import combined_pack

    repo = target_repo(tmp_path / "victim")
    reports = tmp_path / "shared-reports"
    outside = tmp_path / "elsewhere"
    outside.mkdir()
    reports.mkdir()
    (reports / "victim").symlink_to(outside, target_is_directory=True)
    monkeypatch.setenv("EASY_VERIFIER_REPORTS_DIR", str(reports))
    packs = combined_pack(["architecture"], repo_path=str(repo))
    with pytest.raises(ReportWriteError):
        write_report([], packs, repo)
    assert list(outside.iterdir()) == []


# ---------------------------------------------------------------------------
# AC5: compose scorer service, verifier unchanged, Dockerfile safe.directory
# ---------------------------------------------------------------------------


def _compose_config(tmp_path: Path, **env: str) -> dict:
    docker = shutil.which("docker")
    if docker is None:
        pytest.skip("Docker CLI is unavailable")
    completed = subprocess.run(
        ["docker", "compose", "config", "--format", "json"],
        cwd=REPO_ROOT,
        env={"PATH": str(Path(docker).parent), "HOME": str(tmp_path), **env},
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)["services"]


def test_compose_scorer_service_is_shared_hardened_and_loopback(tmp_path) -> None:
    workspace = tmp_path / "repos"
    reports = tmp_path / "reports"
    sot = tmp_path / "sot"
    service = _compose_config(
        tmp_path,
        EASY_VERIFIER_WORKSPACE=str(workspace),
        EASY_VERIFIER_REPORTS=str(reports),
        EASY_VERIFIER_SOT=str(sot),
    )["scorer"]

    assert service["image"] == "easy-verifier-mcp:0.1.0"
    assert service["command"] == ["--transport", "streamable-http"]
    assert service["network_mode"] == "host"
    assert service["restart"] == "unless-stopped"
    assert service["init"] is True
    assert service["read_only"] is True
    assert service["cap_drop"] == ["ALL"]
    assert service["security_opt"] == ["no-new-privileges:true"]
    assert service["tmpfs"] == ["/tmp:rw,noexec,nosuid,nodev,size=16m"]
    assert "ports" not in service
    assert "user" not in service  # the image's UID 10001
    assert not service.get("stdin_open")

    volumes = {volume["target"]: volume for volume in service["volumes"]}
    assert volumes[str(workspace)]["source"] == str(workspace)
    assert volumes[str(workspace)]["read_only"] is True
    assert volumes[str(reports)]["source"] == str(reports)
    assert volumes[str(reports)].get("read_only", False) is False
    assert volumes["/sot"]["source"] == str(sot)
    assert set(volumes) == {str(workspace), str(reports), "/sot"}

    environment = service["environment"]
    assert environment["EASY_VERIFIER_REPORTS_DIR"] == str(reports)
    assert environment["EASY_VERIFIER_SOT"] == "/sot"
    assert environment["EASY_VERIFIER_PORT"] == "8766"


def test_compose_scorer_defaults_reports_under_home(tmp_path) -> None:
    service = _compose_config(
        tmp_path, EASY_VERIFIER_WORKSPACE=str(tmp_path / "repos")
    )["scorer"]
    expected = str(tmp_path / ".easy-verifier-reports")
    assert service["environment"]["EASY_VERIFIER_REPORTS_DIR"] == expected
    assert expected in {volume["target"] for volume in service["volumes"]}


def test_compose_verifier_service_is_unchanged(tmp_path) -> None:
    service = _compose_config(
        tmp_path,
        EASY_VERIFIER_REPO=str(tmp_path / "t"),
        EASY_VERIFIER_REPORTS=str(tmp_path / "t" / "reports"),
    )["verifier"]
    assert service["network_mode"] == "none"
    assert service["stdin_open"] is True
    assert service.get("command") is None
    assert service.get("restart") is None
    assert {v["target"] for v in service["volumes"]} == {
        "/workspace",
        "/workspace/reports",
        "/sot",
    }


def test_dockerfile_trusts_repositories_at_any_mounted_path() -> None:
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "git config --system --add safe.directory '*'" in dockerfile
    # core/git.py sets GIT_CONFIG_NOSYSTEM=1 and passes no HOME, so only
    # command-line config reaches the engine's git: a wrapper ahead of
    # /usr/bin/git on PATH supplies it.
    assert 'exec /usr/bin/git -c "safe.directory=*" "$@"' in dockerfile
    assert "> /usr/local/bin/git" in dockerfile


def test_container_verifier_checks_the_engine_git_not_only_plain_git() -> None:
    script = (REPO_ROOT / "scripts/verify_container.sh").read_text(encoding="utf-8")
    assert "from easy_verifier.core.git import run_git" in script
    assert "engine git cannot read the mounted repository" in script


# ---------------------------------------------------------------------------
# AC8: docs lead with the shared container
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", [README, DOCKER_GUIDE], ids=["readme", "guide"])
def test_docs_lead_with_the_shared_container(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    up = text.index("docker compose up -d scorer")
    register = text.index(SHARED_URL_COMMAND)
    stdio = text.index("one container per session")
    assert up < register < stdio, "shared way must come before the stdio way"
    assert "EASY_VERIFIER_WORKSPACE" in text
    assert "docker compose down scorer" in text  # stop
    assert "docker compose build scorer" in text  # upgrade
    assert "any local process" in text.lower()  # exposure stated plainly


def test_documented_port_and_url_match_the_code() -> None:
    assert mcp_server.DEFAULT_HTTP_PORT == 8766
    assert f"http://127.0.0.1:{mcp_server.DEFAULT_HTTP_PORT}/mcp" in SHARED_URL_COMMAND
