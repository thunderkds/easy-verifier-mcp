"""Static T016 checks that do not require access to a Docker daemon."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_dockerfile_pins_runtime_and_drops_root() -> None:
    dockerfile = (REPO_ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert dockerfile.startswith("FROM python:3.12.14-slim-bookworm\n")
    assert 'python -m pip install "mcp==1.29.1" .' in dockerfile
    assert "apt-get install --yes --no-install-recommends git" in dockerfile
    assert "USER 10001:10001" in dockerfile
    assert 'ENTRYPOINT ["easy-verifier-mcp"]' in dockerfile
    assert "EXPOSE" not in dockerfile


def test_compose_applies_kernel_level_runtime_boundaries(
    tmp_path: Path,
) -> None:
    if shutil.which("docker") is None:
        pytest.skip("Docker CLI is unavailable")

    target = tmp_path / "target"
    reports = target / "reports"
    reports.mkdir(parents=True)
    completed = subprocess.run(
        ["docker", "compose", "config", "--format", "json"],
        cwd=REPO_ROOT,
        env={
            "PATH": str(Path(shutil.which("docker")).parent),
            "EASY_VERIFIER_REPO": str(target),
            "EASY_VERIFIER_REPORTS": str(reports),
        },
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    service = json.loads(completed.stdout)["services"]["verifier"]
    assert service["network_mode"] == "none"
    assert service["read_only"] is True
    assert service["cap_drop"] == ["ALL"]
    assert "ports" not in service
    assert service["security_opt"] == ["no-new-privileges:true"]
    volumes = {volume["target"]: volume for volume in service["volumes"]}
    assert volumes["/workspace"]["read_only"] is True
    assert volumes["/workspace/reports"].get("read_only", False) is False


def test_container_verifier_is_valid_shell_and_checks_the_real_mcp_surface() -> None:
    script = REPO_ROOT / "scripts/verify_container.sh"
    completed = subprocess.run(
        ["bash", "-n", str(script)], capture_output=True, text=True, check=False
    )

    assert completed.returncode == 0, completed.stderr
    source = script.read_text(encoding="utf-8")
    for witness in (
        "tools/list",
        "tools/call",
        "write_report",
        "id -u",
        "touch /workspace/NOPE",
        "touch /workspace/reports/ok",
        "HostConfig.NetworkMode",
        "CapDrop",
        "PortBindings",
        "git -C /workspace",
        "timeout 90s",
    ):
        assert witness in source


def test_build_context_excludes_development_and_repository_state() -> None:
    ignored = set(
        (REPO_ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
    )

    assert {".git", ".venv", "tests", "tasks", "memory", "reports"} <= ignored
