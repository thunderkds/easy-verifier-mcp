"""T008 acceptance tests for the bespoke security evidence dimension."""

from __future__ import annotations

import ast
import dataclasses
import inspect
import json
import subprocess
from pathlib import Path

from easy_verifier.adapters.cli import main as cli_main
from easy_verifier.core.context import MODE_STANDALONE, detect_context
from easy_verifier.core.models import ApprovalRequest, EvidencePack
from easy_verifier.core.pipeline import run_dimension
from easy_verifier.dimensions import security


def test_standalone_dependency_manifest_produces_citable_pack(
    tmp_path: Path,
) -> None:
    (tmp_path / "requirements.txt").write_text(
        "example-package==1.2.3\n", encoding="utf-8"
    )

    pack = run_dimension(security.DESCRIPTOR, tmp_path)

    assert isinstance(pack, EvidencePack)
    assert pack.dimension == "security"
    assert pack.mode == MODE_STANDALONE
    assert pack.files_read == ("requirements.txt",)
    assert [excerpt.path for excerpt in pack.excerpts] == ["requirements.txt"]
    assert pack.excerpts[0].start_line == 1
    assert pack.excerpts[0].end_line == 1
    assert "example-package==1.2.3" in pack.excerpts[0].text


def _fake_secret(index: int) -> str:
    return f"FAKEfake{index}Aa1Bb2Cc3Dd4"


def test_five_secrets_are_fingerprinted_with_actionable_locations(
    tmp_path: Path,
) -> None:
    secrets = tuple(_fake_secret(index) for index in range(5))
    source_dir = tmp_path / "src"
    source_dir.mkdir()
    (tmp_path / "requirements.txt").write_text(
        f"api_key={secrets[0]}\nclient_secret={secrets[1]}\n",
        encoding="utf-8",
    )
    (source_dir / "auth.py").write_text(
        f"token = '{secrets[2]}'\npassword = '{secrets[3]}'\n",
        encoding="utf-8",
    )
    (tmp_path / "Dockerfile").write_text(
        f"ENV TOKEN={secrets[4]}\n",
        encoding="utf-8",
    )

    pack = run_dimension(security.DESCRIPTOR, tmp_path)
    serialized = json.dumps(dataclasses.asdict(pack))

    for raw in secrets:
        assert raw not in serialized

    assert len(pack.redactions) == 5
    assert {(hit.detector, hit.path, hit.line) for hit in pack.redactions} == {
        ("credential_assignment", "requirements.txt", 1),
        ("credential_assignment", "requirements.txt", 2),
        ("credential_assignment", "src/auth.py", 1),
        ("credential_assignment", "src/auth.py", 2),
        ("credential_assignment", "Dockerfile", 1),
    }


def test_secret_file_defaults_to_refusal_and_surfaces_request(
    tmp_path: Path,
) -> None:
    raw = _fake_secret(9)
    (tmp_path / ".env").write_text(f"TOKEN={raw}\n", encoding="utf-8")

    pack = run_dimension(security.DESCRIPTOR, tmp_path)
    serialized = json.dumps(dataclasses.asdict(pack))

    assert pack.approval_requests == (
        ApprovalRequest(
            path=".env",
            reason=("secret-bearing contents require per-file operator approval"),
        ),
    )
    assert ".env" not in pack.files_read
    assert ".env" not in pack.sources_found
    assert raw not in serialized
    env_miss = next(miss for miss in pack.sources_missing if miss.source == ".env")
    assert env_miss.reason == "excluded: secret-bearing; operator approval required"
    assert ".env" in pack.sources_sought
    assert pack.coverage_score is not None and pack.coverage_score < 1.0


def test_explicit_per_file_approval_allows_security_only_read(
    tmp_path: Path,
) -> None:
    raw = _fake_secret(10)
    (tmp_path / ".env").write_text(f"TOKEN={raw}\n", encoding="utf-8")
    seen: list[str] = []

    def approve(path: str) -> bool:
        seen.append(path)
        return True

    context = detect_context(
        tmp_path,
        secret_approval=approve,
    )

    excerpts = tuple(security.collect(context))

    assert seen == [".env"]
    assert context.files_read == [".env"]
    assert ".env" in context.sources_found
    assert any(excerpt.path == ".env" and raw in excerpt.text for excerpt in excerpts)
    assert context.approval_requests == [
        ApprovalRequest(
            path=".env",
            reason=("secret-bearing contents require per-file operator approval"),
        )
    ]


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=T008", "-c", "user.email=t008@example.test", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )


def test_changes_scope_reads_only_the_explicit_ref_file_set(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "src"
    source_dir.mkdir()
    (tmp_path / "requirements.txt").write_text("base==1.0\n", encoding="utf-8")
    (source_dir / "auth.py").write_text("def authenticate(): ...\n", encoding="utf-8")
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "baseline")

    (source_dir / "auth.py").write_text(
        "def authenticate(): return True\n", encoding="utf-8"
    )
    _git(tmp_path, "add", "src/auth.py")
    _git(tmp_path, "commit", "-qm", "change auth")

    pack = run_dimension(
        security.DESCRIPTOR,
        tmp_path,
        scope="changes",
        ref="HEAD",
    )

    assert set(pack.files_read) == {"src/auth.py"}
    assert {excerpt.path for excerpt in pack.excerpts} == {"src/auth.py"}
    assert "requirements.txt" not in pack.files_read


def test_dependency_crypto_ci_and_excluded_secret_categories_are_covered(
    tmp_path: Path,
) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / "package.json").write_text('{"dependencies": {}}\n', encoding="utf-8")
    (tmp_path / "src" / "crypto_service.py").write_text(
        "def encrypt(data): ...\n", encoding="utf-8"
    )
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text(
        "permissions: read-all\n", encoding="utf-8"
    )
    raw = _fake_secret(11)
    (tmp_path / ".env.sample").write_text(f"TOKEN={raw}\n", encoding="utf-8")

    pack = run_dimension(security.DESCRIPTOR, tmp_path)
    paths = {excerpt.path for excerpt in pack.excerpts}

    assert {
        "package.json",
        "src/crypto_service.py",
        ".github/workflows/ci.yml",
    } <= paths
    assert any(request.path == ".env.sample" for request in pack.approval_requests)
    assert ".env.sample" not in pack.files_read
    assert raw not in json.dumps(dataclasses.asdict(pack))


def test_all_scopes_and_cli_are_reachable_with_explicit_selectors(
    tmp_path: Path, capsys
) -> None:
    tasks = tmp_path / "tasks"
    tasks.mkdir()
    (tasks / "TASK_GUIDE_T123.md").write_text(
        "# Task\n\n## Acceptance Criteria\n\n- [ ] security evidence\n",
        encoding="utf-8",
    )
    (tmp_path / "requirements.txt").write_text("base==1.0\n", encoding="utf-8")
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "baseline")
    (tmp_path / "requirements.txt").write_text("base==2.0\n", encoding="utf-8")

    packs = (
        run_dimension(security.DESCRIPTOR, tmp_path, scope="project"),
        run_dimension(security.DESCRIPTOR, tmp_path, scope="worktree"),
        run_dimension(security.DESCRIPTOR, tmp_path, scope="changes", ref="HEAD"),
        run_dimension(security.DESCRIPTOR, tmp_path, scope="task", task_id="T123"),
    )

    assert tuple(pack.scope for pack in packs) == (
        "project",
        "worktree",
        "changes",
        "task",
    )
    assert all(isinstance(pack, EvidencePack) for pack in packs)

    assert (
        cli_main(
            [
                "security",
                "--repo",
                str(tmp_path),
                "--scope",
                "project",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["dimension"] == "security"
    assert payload["scope"] == "project"


def test_security_module_is_bespoke_lazy_and_has_no_execution_or_network_imports(
    tmp_path: Path,
) -> None:
    source = Path(security.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = {
        node.names[0].name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
    }
    imported.update(
        (node.module or "").split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    )

    assert "_doc_extract" not in source
    assert imported.isdisjoint({"http", "requests", "socket", "subprocess", "urllib"})
    assert inspect.isgenerator(security.collect(detect_context(tmp_path)))


def test_empty_repo_reports_static_misses_without_verdict_fields(
    tmp_path: Path,
) -> None:
    pack = run_dimension(security.DESCRIPTOR, tmp_path)
    payload = dataclasses.asdict(pack)

    assert pack.sources_found == ()
    assert {miss.source for miss in pack.sources_missing} == set(
        security.SOURCES_SOUGHT
    )
    assert pack.coverage_score == 0.0
    assert {"severity", "cvss", "risk_rating", "verdict"}.isdisjoint(payload)


def test_large_lockfile_is_bounded_and_unsafe_or_vendored_paths_are_skipped(
    tmp_path: Path,
) -> None:
    lines = [f'{{"name": "pkg-{index}"}}' for index in range(400)]
    (tmp_path / "package-lock.json").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    vendor = tmp_path / "node_modules"
    vendor.mkdir()
    raw = _fake_secret(12)
    (vendor / "auth.js").write_text(f"token={raw}\n", encoding="utf-8")
    (tmp_path / "image.png").write_bytes(b"\x89PNG\x00\xff")
    outside = tmp_path.parent / f"{tmp_path.name}-outside.py"
    outside.write_text(f"token={raw}\n", encoding="utf-8")
    (tmp_path / "linked_auth.py").symlink_to(outside)

    pack = run_dimension(security.DESCRIPTOR, tmp_path)
    excerpt = next(item for item in pack.excerpts if item.path == "package-lock.json")
    serialized = json.dumps(dataclasses.asdict(pack))

    assert excerpt.end_line == 200
    assert "excerpt clipped" in excerpt.text
    assert "node_modules/auth.js" not in pack.files_read
    assert "image.png" not in pack.files_read
    assert "linked_auth.py" not in pack.files_read
    assert raw not in serialized


def test_security_candidate_reads_are_bounded(tmp_path: Path) -> None:
    for index in range(security.MAX_SECURITY_SOURCES + 5):
        (tmp_path / f"auth_{index:03}.py").write_text(
            "def authenticate(): ...\n", encoding="utf-8"
        )

    pack = run_dimension(security.DESCRIPTOR, tmp_path)

    assert len(set(pack.files_read)) == security.MAX_SECURITY_SOURCES
    assert f"auth_{security.MAX_SECURITY_SOURCES + 4:03}.py" not in pack.files_read


def test_relevant_sources_outrank_alphabetically_earlier_filler(
    tmp_path: Path,
) -> None:
    """The candidate cap must be spent on relevance, not on arrival order.

    Regression for a Stage 4 P1: candidates were read in alphabetical order, so
    on any repo above ``MAX_SECURITY_SOURCES`` the whole cap was consumed by
    whatever sorted first and real evidence was dropped silently.
    """
    for index in range(security.MAX_SECURITY_SOURCES + 5):
        (tmp_path / f"aaa_{index:03}.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("requests==2.0\n", encoding="utf-8")
    container = tmp_path / "zzz"
    container.mkdir()
    (container / "Dockerfile").write_text(
        "FROM python:3.12\nUSER root\n", encoding="utf-8"
    )

    pack = run_dimension(security.DESCRIPTOR, tmp_path, scope="project")

    paths = [excerpt.path for excerpt in pack.excerpts]
    assert "requirements.txt" in paths
    assert "zzz/Dockerfile" in paths
    assert pack.coverage_score is not None and pack.coverage_score > 0.0


def _reasons(pack: EvidencePack) -> dict[str, str]:
    return {miss.source: miss.reason for miss in pack.sources_missing}


def test_declared_sources_are_probed_so_miss_reasons_are_truthful(
    tmp_path: Path,
) -> None:
    """Absent declared sources must read ``not found``, never ``not examined``.

    Regression for a Stage 4 P1: ``collect`` never probed ``SOURCES_SOUGHT``, so
    every declared source fell through to the pipeline's "not examined" default
    and the miss list was fabricated.
    """
    (tmp_path / "requirements.txt").write_text("requests==2.0\n", encoding="utf-8")
    source_dir = tmp_path / "src"
    source_dir.mkdir()
    (source_dir / "auth.py").write_text("def login(): ...\n", encoding="utf-8")
    (tmp_path / ".env").write_text(
        f"API_TOKEN={_fake_secret(31)}\n", encoding="utf-8"
    )

    pack = run_dimension(security.DESCRIPTOR, tmp_path, scope="project")
    reasons = _reasons(pack)

    assert "requirements.txt" in pack.sources_found
    assert "src/auth.py" in pack.sources_found

    # Genuinely absent — the truthful state is "not found".
    for absent in ("package.json", "Dockerfile", "compose.yaml", "poetry.lock"):
        assert reasons[absent] == "not found in the target repository", absent

    # Present but withheld — distinct from both of the above (AC #11/#13).
    assert reasons[".env"] == "excluded: secret-bearing; operator approval required"
    assert ".env" not in pack.sources_found

    # The v1 out-of-scope pseudo-source states its own reason.
    assert "out of scope for v1" in reasons["git history (out of scope for v1)"]

    # Nothing is left claiming it merely was not examined.
    assert not any("not examined" in reason for reason in reasons.values())
