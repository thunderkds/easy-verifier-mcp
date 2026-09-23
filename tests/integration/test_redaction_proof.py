"""AC #5: raw secrets never cross an adapter or report boundary."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from .conftest import mcp_call, require_docker, run_cli, target_repo


def _seeded_target(tmp_path: Path) -> tuple[Path, tuple[str, ...]]:
    target = target_repo(tmp_path / "secret-target")
    values = (
        "AKIA" + "A1B2C3D4E5F6G7H8",
        "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0In0.signature-value",
        "pB4kQ9zXmR7tY2wE",
    )
    (target / "README.md").write_text(
        f"# Seeded\napi_key = {values[0]}\ntoken = {values[1]}\nsecret = {values[2]}\n",
        encoding="utf-8",
    )
    return target, values


def test_cli_pack_report_stderr_and_errors_contain_no_raw_secret(
    tmp_path: Path,
) -> None:
    target, secrets = _seeded_target(tmp_path)
    packed = run_cli("architecture", "--repo", str(target), "--scope", "project")
    assert packed.returncode == 0, packed.stderr
    assert all(secret not in packed.stdout + packed.stderr for secret in secrets)

    report = run_cli(
        "write-report",
        "--repo",
        str(target),
        "--dimensions",
        "architecture",
        "--findings",
        "/dev/stdin",
        input_text="[]",
    )
    assert report.returncode == 0, report.stderr
    document = (target / json.loads(report.stdout)["path"]).read_text(encoding="utf-8")
    assert all(secret not in document for secret in secrets)


def test_mcp_pack_contains_fingerprints_but_no_raw_secret(tmp_path: Path) -> None:
    target, secrets = _seeded_target(tmp_path)
    payload = mcp_call("architecture", {"repo": str(target), "scope": "project"})
    serialized = json.dumps(payload)
    assert all(secret not in serialized for secret in secrets)
    assert payload["had_redactions"] is True
    assert payload["redactions"]
    expected = {
        f"{secret[:4]}…****:{hashlib.sha256(secret.encode()).hexdigest()[:12]}"
        for secret in secrets
    }
    assert {hit["fingerprint"] for hit in payload["redactions"]} >= expected


def test_container_redaction_proof_is_not_silent_when_docker_is_missing() -> None:
    require_docker()
    completed = subprocess.run(
        ["bash", "scripts/verify_container.sh"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr + completed.stdout
