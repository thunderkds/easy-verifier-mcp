"""T051 — redaction counts real secret shapes, not content hashes or identifiers.

T035's sign-off found security's ``redaction_hits_observed`` dominated by false
positives: sha256 values in lock files, long ``def test_…`` names, and files git
ignores. Each exemption below has a twin that differs in exactly one predicate
and must still fingerprint — the sabotage check for that guard.

No realistic credential is committed: every digest and token is built at
runtime (``memory/MEMORY.md`` — never commit credential shapes).
"""

from __future__ import annotations

import base64
import hashlib
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from easy_verifier.core.context import _walk, git_ignore_filter
from easy_verifier.core.pipeline import run_dimension
from easy_verifier.core.redact import _shannon_entropy, fingerprint, redact, scan
from easy_verifier.core.scope import resolve_scope
from easy_verifier.dimensions import DIMENSIONS

REPO_ROOT = Path(__file__).resolve().parents[1]

SHA1 = hashlib.sha1(b"t051-fixture").hexdigest()
SHA256 = hashlib.sha256(b"t051-fixture").hexdigest()
SHA512 = hashlib.sha512(b"t051-fixture").hexdigest()
SRI = "sha512-" + base64.b64encode(hashlib.sha512(b"t051-fixture").digest()).decode()
HEX48 = hashlib.sha256(b"t051-other").hexdigest()[:48]
# Synthetic key material (T029's shape): mixed case + digits, no vendor prefix.
MIXED_TOKEN = "pB4kQ9zXmR7tY2wEaB3xK9mQ7rT2vY8w"

_LETTERS_TEST_NAME = re.compile(r"\bdef test_[a-z_]{27,}\(")

needs_git = pytest.mark.skipif(shutil.which("git") is None, reason="git not on PATH")


def _hit(text: str) -> bool:
    return bool(scan(text).hits)


# --- AC 1 — hex digests in a hash context are not fingerprinted --------------


def test_sha256_value_in_a_lock_json_is_unchanged() -> None:
    text = f'{{\n  "sha256": "{SHA256}"\n}}\n'
    assert redact(text) == text


def test_hex_under_a_secret_named_key_is_fingerprinted() -> None:
    text = f'API_TOKEN = "{SHA256}"'
    assert fingerprint(SHA256) in redact(text)


@pytest.mark.parametrize(
    "line",
    [
        f'"sha512": "{SHA512}"',
        f'sha256 = "{SHA256}"',
        f"checksum: {SHA256}",
        f'"shasum": "{SHA1}"',
        f"content_hash: {SHA256}",
        f'"integrity": "{SRI}",',
        f"  integrity {SRI}",
        f'"rev": "{SHA1}",',
        f'{{ url = "https://files.pythonhosted.org/packages/ab/cd/{SHA256[:60]}'
        f'/pkg-1.0.tar.gz", hash = "sha256:{SHA256}" }}',
        f'  resolved "https://registry.yarnpkg.com/a/-/a-1.0.0.tgz#{SHA1}"',
        f'source = "git+https://github.com/owner/repo?rev=v1#{SHA1}"',
    ],
)
def test_digest_in_a_hash_context_is_unchanged(line: str) -> None:
    assert scan(line).hits == (), line


@pytest.mark.parametrize(
    ("exempt", "twin", "guard"),
    [
        (f'"sha256": "{SHA256}"', f'"shape": "{SHA256}"', "hash-named key"),
        (f"checksum: {SHA256}", f"checksum {SHA256}", "key position"),
        (f'"file_sha256": "{SHA256}"', f'"token_sha256": "{SHA256}"', "secret veto"),
        (f'"integrity": "{SRI}"', f'"payload": "{SRI}"', "SRI value needs the key"),
        (f"a-1.0.0.tgz#{SHA1}", f"a-1.0.0.txt#{SHA1}", "fragment anchor"),
        (f"a-1.0.0.tgz#{SHA1}", f"a-1.0.0.tgz#{HEX48}", "fragment length"),
        (f"a-1.0.0.tgz#{SHA1}", f"secret a-1.0.0.tgz#{SHA1}", "fragment veto"),
    ],
)
def test_each_hash_context_guard_keeps_its_twin_fingerprinted(
    exempt: str, twin: str, guard: str
) -> None:
    assert not _hit(exempt), guard
    assert _hit(twin), guard


def test_secret_veto_covers_the_whole_line() -> None:
    # The `api_token_hash` key is not caught by credential_assignment (the word
    # is not followed by `=`/`:`), so only the veto keeps both digests covered.
    text = f'"sha256": "{SHA256}", "api_token_hash": "{SHA512}"'
    assert [hit.detector for hit in scan(text).hits] == ["high_entropy_hex"] * 2


def test_hash_context_is_one_line_only() -> None:
    text = f'"sha256": "{SHA256}",\n"blob": "{SHA512}"\n'
    assert [hit.line for hit in scan(text).hits] == [2]


def test_named_detectors_ignore_hash_context() -> None:
    aws_key_id = "AKIA" + "FAKE" * 4
    jwt = "eyJ" + "hbGciOi" + "." + "eyJzdWIi" + "." + "c2lnbmF0dXJl"
    result = scan(f'"digest": "{aws_key_id}"\n"digest": "{jwt}"\n')
    assert [hit.detector for hit in result.hits] == ["aws_access_key_id", "jwt"]


# --- AC 2 — word-only identifiers are not fingerprinted ----------------------


@pytest.mark.parametrize(
    "identifier",
    [
        "test_quick_brown_fox_jumps_over_lazy_dog",
        "PACK_MY_BOX_WITH_FIVE_DOZEN_LIQUOR_JUGS",
        "Quick_Brown_Fox_Jumps_Over_Lazy_Dog",
    ],
)
def test_word_only_identifier_is_unchanged(identifier: str) -> None:
    # Precondition: the identifier clears the long-token bar on its own, so it
    # is the exemption — not a low score — that keeps it readable.
    assert _shannon_entropy(identifier) >= 4.0
    line = f"def {identifier}():"
    assert redact(line) == line


@pytest.mark.parametrize(
    ("twin", "guard"),
    [
        ("test_quick_brown_fox_jumps_over_lazy_dog_2x", "digit piece"),
        ("test_quick_brown_fox_jumpsOver_lazy_dog", "mixed-case piece"),
        ("test_quick_brown_fox_wqzkxvbnmjhgfdsaplokiujyhtgrfedcv", "piece length"),
        ("test-quick-brown-fox-jumps-over-lazy-dog", "joiner is _ only"),
        ("content=PACK_MY_BOX_WITH_FIVE_DOZEN_LIQUOR_JUGS", "whole token only"),
    ],
)
def test_each_identifier_guard_keeps_its_twin_fingerprinted(
    twin: str, guard: str
) -> None:
    assert _shannon_entropy(twin) >= 4.0, "twin must clear the bar to be a real test"
    assert [hit.detector for hit in scan(twin).hits] == ["high_entropy_string"], guard


def test_mixed_case_letters_only_token_still_fingerprints_without_a_suffix() -> None:
    token = "xQzRtWvB_kLmNpQs_TyUiOpAs_DfGhJkLz"
    assert fingerprint(token) in redact(token)


def test_credential_assignment_still_catches_an_identifier_shaped_value() -> None:
    value = "kqzvxm_hjtybn_wpfrls_dgcaeu_oiqzvx"
    assert [hit.detector for hit in scan(f"password = {value}").hits] == [
        "credential_assignment"
    ]


# --- AC 3 — the evidence walk skips files git ignores ------------------------


def _git_repo(root: Path) -> Path:
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / ".gitignore").write_text("cache/\n*.log\n", encoding="utf-8")
    (root / "pkg").mkdir()
    (root / "pkg" / ".gitignore").write_text("local/\n", encoding="utf-8")
    for relative in (
        "app.py",
        "run.log",
        "cache/lock.json",
        "cache/.env",
        "pkg/mod.py",
        "pkg/local/notes.txt",
    ):
        (root / relative).parent.mkdir(parents=True, exist_ok=True)
        (root / relative).write_text("x = 1\n", encoding="utf-8")
    (root / "tracked.log").write_text("x = 1\n", encoding="utf-8")
    subprocess.run(
        ["git", "-C", str(root), "add", "-f", "tracked.log", "app.py"], check=True
    )
    return root


@needs_git
def test_project_scope_drops_git_ignored_files(tmp_path: Path) -> None:
    files = set(resolve_scope("project", _git_repo(tmp_path), None).files)
    assert {"app.py", "pkg/mod.py", ".gitignore", "pkg/.gitignore"} <= files
    # Ignored by the root and by a nested .gitignore.
    assert not files & {"run.log", "cache/lock.json", "pkg/local/notes.txt"}
    # Tracked wins over a matching pattern; a secret-bearing name stays visible.
    assert {"tracked.log", "cache/.env"} <= files


@needs_git
def test_context_walk_drops_git_ignored_files(tmp_path: Path) -> None:
    repo = _git_repo(tmp_path)
    walked = set(_walk(repo, repo, extensions=None))
    assert "cache/lock.json" not in walked
    assert {"app.py", "tracked.log", "cache/.env"} <= walked


def test_non_git_directory_is_unchanged_behaviour(tmp_path: Path) -> None:
    (tmp_path / ".gitignore").write_text("cache/\n", encoding="utf-8")
    (tmp_path / "cache").mkdir()
    (tmp_path / "cache" / "lock.json").write_text("{}\n", encoding="utf-8")
    assert "cache/lock.json" in resolve_scope("project", tmp_path, None).files


@needs_git
def test_target_ignored_by_an_enclosing_repo_is_unchanged_behaviour(
    tmp_path: Path,
) -> None:
    repo = _git_repo(tmp_path)
    target = repo / "cache"
    assert "lock.json" in resolve_scope("project", target, None).files


@needs_git
def test_security_pack_does_not_scan_a_git_ignored_file(tmp_path: Path) -> None:
    repo = _git_repo(tmp_path)
    (repo / "cache" / "lock.json").write_text(
        f'{{"blob": "{MIXED_TOKEN}"}}\n', encoding="utf-8"
    )
    pack = run_dimension(DIMENSIONS["security"], repo)
    assert not [hit for hit in pack.redactions if hit.path == "cache/lock.json"]

    # Twin: the same file, no longer ignored, is scanned and fingerprinted.
    (repo / ".gitignore").write_text("*.log\n", encoding="utf-8")
    pack = run_dimension(DIMENSIONS["security"], repo)
    assert [hit for hit in pack.redactions if hit.path == "cache/lock.json"]


@needs_git
def test_ignore_decision_is_one_git_call_per_walk(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _git_repo(tmp_path)
    for index in range(50):
        (repo / f"m{index}.py").write_text("x = 1\n", encoding="utf-8")
    calls: list[list[str]] = []
    real_run = subprocess.run

    def counting_run(args, *rest, **kwargs):
        calls.append(list(args))
        return real_run(args, *rest, **kwargs)

    monkeypatch.setattr("easy_verifier.core.git.subprocess.run", counting_run)
    list(_walk(repo, repo, extensions=None))
    assert len([call for call in calls if "ls-files" in call]) == 1


@needs_git
def test_ignore_check_never_runs_the_target_repos_fsmonitor(tmp_path: Path) -> None:
    repo = _git_repo(tmp_path)
    marker = tmp_path.parent / f"{tmp_path.name}-fsmonitor-ran"
    hook = tmp_path.parent / f"{tmp_path.name}-fsmonitor.sh"
    hook.write_text(f"#!/bin/sh\ntouch '{marker}'\n", encoding="utf-8")
    hook.chmod(0o755)
    subprocess.run(
        ["git", "-C", str(repo), "config", "core.fsmonitor", str(hook)], check=True
    )

    skip = git_ignore_filter(repo)

    assert skip("cache/lock.json") is True
    assert not marker.exists(), "git ran a program named by the target repo's config"


# --- AC 4 — this repo's tracked files carry none of the exempted shapes ------


def test_no_tracked_file_fingerprints_a_hash_keyed_digest_or_test_name() -> None:
    listed = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    assert len(listed) > 100, "expected the real repo's file list"
    offenders = []
    for relative in listed:
        try:
            text = (REPO_ROOT / relative).read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        lines = text.split("\n")
        for hit in scan(text).hits:
            line = lines[hit.line - 1]
            if hit.detector.startswith("high_entropy") and (
                '"sha256":' in line or _LETTERS_TEST_NAME.search(line)
            ):
                offenders.append(f"{relative}:{hit.line}")
    assert offenders == []
