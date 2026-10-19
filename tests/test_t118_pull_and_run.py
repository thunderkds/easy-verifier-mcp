"""T118: the pull-and-run quick start and the guarded image publish script.

The guide's ``docker run -d`` block must be the exact equivalent of the compose
``scorer`` service (AC 4); README copies it verbatim (AC 3). The publish script's
guards are driven against a stubbed ``docker`` on ``PATH`` in a scratch git repo,
so nothing here reaches the network or the Docker daemon (AC 5).
"""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import textwrap
import tomllib
from pathlib import Path

import pytest

from easy_verifier.adapters import mcp_server

REPO_ROOT = Path(__file__).resolve().parents[1]
GUIDE = (REPO_ROOT / "docs" / "DOCKER_MCP_GUIDE.md").read_text(encoding="utf-8")
README = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
RELEASE_GUIDE = (REPO_ROOT / "docs" / "RELEASE_GUIDE.md").read_text(encoding="utf-8")
SCRIPT = REPO_ROOT / "scripts" / "publish_image.sh"
VERSION = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))[
    "project"
]["version"]
IMAGE = f"temvar/easy-verifier-mcp:{VERSION}"
REGISTER = "claude mcp add --transport http easy-verifier http://127.0.0.1:8766/mcp"
QUICK_START = "Quick start: pull and run"

# Placeholder host paths the documented command uses; compose is rendered with
# the same values so both sides resolve to identical mounts.
DOC_HOME = "/home/you"
DOC_WORKSPACE = "/home/you/code"

# Fences may be indented (inside a numbered step); the body is dedented.
_FENCE_RE = re.compile(
    r"^(?P<indent> *)```(?P<lang>\w*)\n(?P<body>.*?)\n(?P=indent)```$",
    re.MULTILINE | re.DOTALL,
)
_IMAGE_REF = re.compile(r"[\w./-]*easy-verifier-mcp:[\w.-]+")


def _console_blocks(text: str) -> list[str]:
    return [
        textwrap.dedent(m.group("body"))
        for m in _FENCE_RE.finditer(text)
        if m.group("lang") == "console"
    ]


def _quick_start(text: str) -> str:
    start = text.index(QUICK_START)
    end = text.index("\n### ", start + len(QUICK_START))
    return text[start:end]


def _run_block(text: str) -> str:
    runs = [
        b for b in _console_blocks(_quick_start(text)) if b.startswith("docker run -d")
    ]
    assert len(runs) == 1, runs
    return runs[0]


# ---------------------------------------------------------------------------
# AC 4: the documented docker run is the compose scorer service
# ---------------------------------------------------------------------------

_BOOL_FLAGS = {"-d", "--init", "--read-only"}
_VALUE_FLAGS = {
    "--name",
    "--restart",
    "--network",
    "--cap-drop",
    "--security-opt",
    "--tmpfs",
    "-e",
    "-v",
}


def _parse_run(block: str) -> dict:
    """Parse one ``docker run`` block into the fields compose describes.

    Strict: an unknown flag (``-p``, ``-i``, ``--user``, ...) is an error, so a
    flag added to the doc but absent from compose cannot pass silently.
    """
    tokens = shlex.split(block.replace("\\\n", " ").replace("$HOME", DOC_HOME))
    assert tokens[:3] == ["docker", "run", "-d"], tokens[:3]
    parsed: dict = {"bool": set(), "multi": {}}
    i = 2
    while i < len(tokens) and tokens[i].startswith("-"):
        flag = tokens[i]
        if flag in _BOOL_FLAGS:
            parsed["bool"].add(flag)
            i += 1
        elif flag in _VALUE_FLAGS:
            parsed["multi"].setdefault(flag, []).append(tokens[i + 1])
            i += 2
        else:
            raise AssertionError(f"flag not in the compose scorer service: {flag}")
    parsed["image"] = tokens[i]
    parsed["command"] = tokens[i + 1 :]
    return parsed


def _compose_scorer() -> dict:
    docker = shutil.which("docker")
    if docker is None:
        pytest.skip("Docker CLI is unavailable")
    completed = subprocess.run(
        ["docker", "compose", "config", "--format", "json"],
        cwd=REPO_ROOT,
        env={
            "PATH": str(Path(docker).parent),
            "HOME": DOC_HOME,
            "EASY_VERIFIER_WORKSPACE": DOC_WORKSPACE,
            "EASY_VERIFIER_REPORTS": f"{DOC_HOME}/.easy-verifier-reports",
            "EASY_VERIFIER_SOT": f"{DOC_HOME}/.easy-verifier-sot",
        },
        capture_output=True,
        text=True,
        check=False,
        stdin=subprocess.DEVNULL,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)["services"]["scorer"]


def _mismatches(service: dict, block: str) -> list[str]:
    """Every way ``block`` differs from the compose ``scorer`` service."""
    try:
        run = _parse_run(block)
    except AssertionError as exc:
        return [str(exc)]
    multi = run["multi"]
    problems = []

    def check(name: str, documented: object, expected: object) -> None:
        if documented != expected:
            problems.append(f"{name}: doc {documented!r} != compose {expected!r}")

    check("--read-only", "--read-only" in run["bool"], service.get("read_only") is True)
    check("--init", "--init" in run["bool"], service.get("init") is True)
    check("--network", multi.get("--network"), [service["network_mode"]])
    check("--restart", multi.get("--restart"), [service["restart"]])
    check("--cap-drop", multi.get("--cap-drop"), service["cap_drop"])
    check("--security-opt", multi.get("--security-opt"), service["security_opt"])
    check("--tmpfs", multi.get("--tmpfs"), service["tmpfs"])
    check("image", run["image"], service["image"])
    check("command", run["command"], service["command"])
    check("ports", "ports" in service, False)

    mounts = set()
    for value in multi.get("-v", []):
        source, target, *mode = value.split(":")
        mounts.add((source, target, mode == ["ro"]))
    expected_mounts = {
        (v["source"], v["target"], v.get("read_only", False) is True)
        for v in service["volumes"]
    }
    check("-v", mounts, expected_mounts)

    # PYTHONUNBUFFERED is already the image's ENV and the port is the server's
    # default, so the documented command does not repeat them; both are pinned
    # below so that omission stays true.
    environment = dict(service["environment"])
    environment.pop("PYTHONUNBUFFERED")
    environment.pop("EASY_VERIFIER_PORT")
    documented_env = dict(item.split("=", 1) for item in multi.get("-e", []))
    check("-e", documented_env, environment)
    return problems


def test_omitted_env_is_already_the_image_and_server_default() -> None:
    service = _compose_scorer()
    assert service["environment"]["EASY_VERIFIER_PORT"] == str(
        mcp_server.DEFAULT_HTTP_PORT
    )
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "PYTHONUNBUFFERED=1" in dockerfile
    assert service["environment"]["PYTHONUNBUFFERED"] == "1"


def test_documented_docker_run_equals_compose_scorer_service() -> None:
    service = _compose_scorer()
    block = _run_block(GUIDE)
    assert _mismatches(service, block) == []
    # Spelled out as well, so a doc and compose drifting together still fails.
    run = _parse_run(block)
    assert {"-d", "--init", "--read-only"} <= run["bool"]
    assert run["multi"]["--network"] == ["host"]
    assert run["multi"]["--cap-drop"] == ["ALL"]
    assert run["multi"]["-e"] == [
        f"EASY_VERIFIER_REPORTS_DIR={DOC_HOME}/.easy-verifier-reports",
        "EASY_VERIFIER_SOT=/sot",
    ]


@pytest.mark.parametrize(
    "removed",
    [
        "--read-only ",
        "--cap-drop ALL ",
        "--init ",
        "--security-opt no-new-privileges:true ",
        "--restart unless-stopped ",
        ":ro ",
        "-e EASY_VERIFIER_SOT=/sot ",
        " --transport streamable-http",
    ],
)
def test_dropping_any_hardening_from_the_doc_fails(removed: str) -> None:
    service = _compose_scorer()
    flat = _run_block(GUIDE).replace("\\\n", " ") + " "
    assert removed in flat, removed
    assert _mismatches(service, flat.replace(removed, " ", 1)) != []


@pytest.mark.parametrize("added", ["-p 8766:8766", "-i", "--user 1000:1000"])
def test_adding_a_flag_compose_lacks_fails(added: str) -> None:
    service = _compose_scorer()
    block = _run_block(GUIDE).replace("docker run -d", f"docker run -d {added}", 1)
    assert _mismatches(service, block) != []


def test_quick_start_pulls_prepares_runs_and_registers_in_order() -> None:
    section = _quick_start(GUIDE)
    pull = section.index(f"docker pull {IMAGE}")
    mkdir = section.index("mkdir -p ~/.easy-verifier-reports ~/.easy-verifier-sot")
    chown = section.index(
        "sudo chown 10001:10001 ~/.easy-verifier-reports ~/.easy-verifier-sot"
    )
    run = section.index("docker run -d")
    register = section.index(REGISTER)
    assert pull < mkdir < chown < run < register
    assert "docker rm -f easy-verifier" in GUIDE  # restart / upgrade


def test_guide_puts_pull_first_then_build_from_source_then_stdio() -> None:
    quick = GUIDE.index(QUICK_START)
    source = GUIDE.index("### Build from source")
    compose_up = GUIDE.index("docker compose up -d scorer", source)
    stdio = GUIDE.index("## Alternative: one container per session")
    assert quick < source < compose_up < stdio


def test_readme_leads_with_verbatim_pull_run_register() -> None:
    guide_blocks = _console_blocks(_quick_start(GUIDE))
    readme_blocks = _console_blocks(_quick_start(README))
    assert len(guide_blocks) == 4  # pull, prepare, run, register
    assert readme_blocks[:4] == guide_blocks
    assert not any("docker compose" in block for block in guide_blocks)
    # Build from source follows the quick start, never precedes it.
    assert readme_blocks[4].startswith("docker compose build scorer")
    section = README[
        README.index("### Docker") : README.index("### Final release gate")
    ]
    assert section.index(QUICK_START) < section.index("docs/DOCKER_MCP_GUIDE.md")


def test_one_image_name_everywhere() -> None:
    compose = (REPO_ROOT / "compose.yaml").read_text(encoding="utf-8")
    assert re.findall(r"^\s*image:\s*(\S+)\s*$", compose, re.MULTILINE) == [
        IMAGE,
        IMAGE,
    ]
    for name, text in {"guide": GUIDE, "README": README}.items():
        refs = set(_IMAGE_REF.findall(text))
        assert refs == {IMAGE}, (name, sorted(refs))


def test_release_guide_has_operator_publish_and_digest_check() -> None:
    assert "bash scripts/publish_image.sh --push --replace-existing" in RELEASE_GUIDE
    assert f"docker buildx imagetools inspect {IMAGE}" in RELEASE_GUIDE
    section = RELEASE_GUIDE[RELEASE_GUIDE.index("## Publish the Docker image") :]
    assert "2026-10-19" in section  # the user's decision to replace the old 0.1.0
    assert "--replace-existing" in section


# ---------------------------------------------------------------------------
# AC 5: publish script guards, against a stubbed docker
# ---------------------------------------------------------------------------

_STUB = """#!/bin/sh
printf '%s\\n' "$*" >> "$STUB_LOG"
case "$1 $2" in
  "buildx version") exit 0 ;;
  "buildx inspect")
    echo "Platforms: ${STUB_PLATFORMS:-linux/amd64, linux/386}"; exit 0 ;;
  "buildx imagetools") [ "${STUB_TAG_EXISTS:-0}" = 1 ] && exit 0; exit 1 ;;
  "buildx build") exit 0 ;;
esac
exit 99
"""


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        stdin=subprocess.DEVNULL,
    )


def _commit(repo: Path, *args: str) -> None:
    _git(
        repo, "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", *args
    )


@pytest.fixture
def scratch(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "scripts").mkdir(parents=True)
    shutil.copy2(SCRIPT, repo / "scripts" / "publish_image.sh")
    shutil.copy2(REPO_ROOT / "compose.yaml", repo / "compose.yaml")
    shutil.copy2(REPO_ROOT / "pyproject.toml", repo / "pyproject.toml")
    _git(repo, "init", "-q")
    _git(repo, "add", ".")
    _commit(repo, "-qm", "x")
    stub_dir = tmp_path / "bin"
    stub_dir.mkdir()
    (stub_dir / "docker").write_text(_STUB, encoding="utf-8")
    (stub_dir / "docker").chmod(0o755)
    return repo


def _publish(
    repo: Path, *args: str, **env: str
) -> tuple[subprocess.CompletedProcess, list[str]]:
    log = repo.parent / "docker.log"
    log.write_text("", encoding="utf-8")
    completed = subprocess.run(
        ["bash", str(repo / "scripts" / "publish_image.sh"), *args],
        env={
            "PATH": f"{repo.parent / 'bin'}:{os.environ['PATH']}",
            "STUB_LOG": str(log),
            "HOME": str(repo.parent),
            **env,
        },
        capture_output=True,
        text=True,
        check=False,
        stdin=subprocess.DEVNULL,
    )
    return completed, log.read_text(encoding="utf-8").splitlines()


def _builds(calls: list[str]) -> list[str]:
    return [call for call in calls if call.startswith("buildx build")]


def test_script_without_flags_builds_locally_and_loads(scratch: Path) -> None:
    completed, calls = _publish(scratch)
    assert completed.returncode == 0, completed.stderr
    (build,) = _builds(calls)
    assert (
        f"--platform linux/amd64 -t {IMAGE} -t temvar/easy-verifier-mcp:latest" in build
    )
    assert "--load" in build.split() and "--push" not in build.split()
    assert not any("imagetools" in call for call in calls)
    assert "nothing was published" in completed.stdout


def test_script_refuses_a_dirty_tree(scratch: Path) -> None:
    (scratch / "untracked.txt").write_text("x", encoding="utf-8")
    completed, calls = _publish(scratch)
    assert completed.returncode != 0
    assert "dirty" in completed.stderr
    assert _builds(calls) == []


@pytest.mark.parametrize("which", [1, 2])
def test_script_refuses_a_compose_image_other_than_the_version(
    scratch: Path, which: int
) -> None:
    compose = scratch / "compose.yaml"
    parts = compose.read_text(encoding="utf-8").split(f"image: {IMAGE}")
    assert len(parts) == 3
    images = [f"image: {IMAGE}", f"image: {IMAGE}"]
    images[which - 1] = "image: easy-verifier-mcp:0.1.0"
    compose.write_text(
        parts[0] + images[0] + parts[1] + images[1] + parts[2], encoding="utf-8"
    )
    _commit(scratch, "-qam", "y")
    completed, calls = _publish(scratch)
    assert completed.returncode != 0
    assert "compose.yaml image" in completed.stderr
    assert _builds(calls) == []


def test_script_refuses_a_builder_without_amd64(scratch: Path) -> None:
    completed, calls = _publish(scratch, STUB_PLATFORMS="linux/arm64")
    assert completed.returncode != 0
    assert "does not support linux/amd64" in completed.stderr
    assert _builds(calls) == []


def test_push_refuses_an_existing_tag_without_replace_existing(scratch: Path) -> None:
    completed, calls = _publish(scratch, "--push", STUB_TAG_EXISTS="1")
    assert completed.returncode != 0
    assert (
        "already exists" in completed.stderr
        and "--replace-existing" in completed.stderr
    )
    assert _builds(calls) == []


def test_push_with_replace_existing_pushes_over_an_existing_tag(scratch: Path) -> None:
    completed, calls = _publish(
        scratch, "--push", "--replace-existing", STUB_TAG_EXISTS="1"
    )
    assert completed.returncode == 0, completed.stderr
    (build,) = _builds(calls)
    assert "--push" in build.split() and "--load" not in build.split()
    assert f"-t {IMAGE} -t temvar/easy-verifier-mcp:latest" in build


def test_push_of_a_new_tag_needs_no_replace_existing(scratch: Path) -> None:
    completed, calls = _publish(scratch, "--push")
    assert completed.returncode == 0, completed.stderr
    (build,) = _builds(calls)
    assert "--push" in build.split()


@pytest.mark.parametrize("args", [["--replace-existing"], ["--force"], ["push"]])
def test_script_rejects_bad_arguments_before_building(
    scratch: Path, args: list[str]
) -> None:
    completed, calls = _publish(scratch, *args)
    assert completed.returncode != 0
    assert _builds(calls) == []
