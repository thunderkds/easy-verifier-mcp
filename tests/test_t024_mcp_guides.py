"""Doc-truth checks for the MCP client setup guides (T024).

docs/DOCKER_MCP_GUIDE.md hand-copies compose.yaml's hardening into plain
``docker run`` flags; these tests fail if the two drift apart, or if the guide
ever allocates a TTY (which breaks stdio). docs/LOCAL_MCP_GUIDE.md must name
the real console entry point and CLI flag. README must link to both.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
GUIDE_PATH = REPO_ROOT / "docs" / "DOCKER_MCP_GUIDE.md"
GUIDE = GUIDE_PATH.read_text(encoding="utf-8")
LOCAL_GUIDE = (REPO_ROOT / "docs" / "LOCAL_MCP_GUIDE.md").read_text(encoding="utf-8")

_FENCE_RE = re.compile(
    r"^```(?P<lang>\w*)\n(?P<body>.*?)\n```$", re.MULTILINE | re.DOTALL
)

_TMPFS = "/tmp:rw,noexec,nosuid,nodev,size=16m"

# compose.yaml key -> the docker run tokens the guide must carry for it.
_HARDENING = {
    "read_only: true": ["--read-only"],
    "network_mode: none": ["--network", "none"],
    "- ALL": ["--cap-drop", "ALL"],
    "- no-new-privileges:true": ["--security-opt", "no-new-privileges:true"],
    "- /tmp:rw,noexec,nosuid,nodev,size=16m": ["--tmpfs", _TMPFS],
    "image: easy-verifier-mcp:0.1.0": ["easy-verifier-mcp:0.1.0"],
}


def _blocks(lang: str, text: str = GUIDE) -> list[str]:
    matches = _FENCE_RE.finditer(text)
    return [m.group("body") for m in matches if m.group("lang") == lang]


def _docker_run_invocations() -> list[list[str]]:
    """Every direct ``docker run`` in the guide, as a flat token list."""
    runs = []
    for body in _blocks("console"):
        tokens = body.replace("\\\n", " ").split()
        if "run" in tokens and "docker" in tokens and "compose" not in tokens:
            runs.append(tokens)
    for body in _blocks("json"):
        server = json.loads(body)["mcpServers"]["easy-verifier"]
        if server["args"][0] == "run":
            runs.append([server["command"], *server["args"]])
    return runs


def _contains_sequence(tokens: list[str], expected: list[str]) -> bool:
    n = len(expected)
    return any(tokens[i : i + n] == expected for i in range(len(tokens) - n + 1))


def test_readme_links_to_both_guides() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "(docs/DOCKER_MCP_GUIDE.md)" in readme
    assert "(docs/LOCAL_MCP_GUIDE.md)" in readme


def test_guide_covers_raw_run_claude_code_and_json_clients() -> None:
    runs = _docker_run_invocations()
    assert len(runs) == 3, "expected raw docker run, claude mcp add, and JSON config"
    assert any(tokens[:3] == ["claude", "mcp", "add"] for tokens in runs)


def test_every_docker_run_mirrors_compose_hardening() -> None:
    compose = (REPO_ROOT / "compose.yaml").read_text(encoding="utf-8")
    for compose_key, expected in _HARDENING.items():
        assert compose_key in compose, f"compose.yaml dropped {compose_key!r}"
        for tokens in _docker_run_invocations():
            assert _contains_sequence(tokens, expected), f"{expected} not in {tokens}"


def test_every_docker_run_mounts_target_read_only_and_reports_writable() -> None:
    for tokens in _docker_run_invocations():
        mounts = [tokens[i + 1] for i, tok in enumerate(tokens) if tok == "-v"]
        assert any(m.endswith(":/workspace:ro") for m in mounts), mounts
        assert any(m.endswith(":/workspace/reports") for m in mounts), mounts


def test_no_invocation_allocates_a_tty() -> None:
    for tokens in _docker_run_invocations():
        assert "-i" in tokens
        assert not {"-t", "-it", "-ti", "--tty"} & set(tokens), tokens


def test_json_configs_are_valid_and_compose_variant_disables_tty() -> None:
    configs = [json.loads(body) for body in _blocks("json")]
    compose_args = [
        c["mcpServers"]["easy-verifier"]["args"]
        for c in configs
        if c["mcpServers"]["easy-verifier"]["args"][0] == "compose"
    ]
    assert len(compose_args) == 1
    assert "--no-tty" in compose_args[0]


def test_local_guide_uses_the_real_entry_point_and_http_flag() -> None:
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'easy-verifier-mcp = "easy_verifier.adapters.mcp_server:main"' in pyproject
    assert "claude mcp add easy-verifier -- easy-verifier-mcp" in LOCAL_GUIDE

    from easy_verifier.adapters.mcp_server import _build_parser

    assert _build_parser().parse_args(["--http"]).http is True
    assert "easy-verifier-mcp --http" in LOCAL_GUIDE


def test_local_guide_json_config_launches_the_entry_point_on_stdio() -> None:
    configs = [json.loads(body) for body in _blocks("json", LOCAL_GUIDE)]
    assert len(configs) == 1
    server = configs[0]["mcpServers"]["easy-verifier"]
    assert server["command"].endswith("/easy-verifier-mcp")
    assert server["args"] == []
