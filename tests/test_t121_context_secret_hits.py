"""T121 -- secret hits in context files do not lower a narrow-scope score (FR-088).

Field report (HUN-34): a ``changes`` scope whose diff holds no secret scored
security 18, because 116 of 123 redaction hits came from an unchanged
``.claude/harness-lock.json`` (a path -> sha256 manifest), read repo-wide as a
``lockfile`` context role (FR-078). Context files are cited, not measured: at a
narrow scope ``redaction_hits_observed`` and ``redacted_file_share`` count only
the scope's own files, while context-file hits stay redacted and are named in
the derivation. ``project`` scope is unchanged.

No realistic credential shape is committed here: the token is assembled at run
time from a hash, and spelled ``FAKEfake``.
"""

from __future__ import annotations

import base64
import hashlib
import json
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from easy_verifier.core.metric_tables import curated_metric_tables
from easy_verifier.core.metrics import MetricAbstention, compute_metrics
from easy_verifier.core.models import RedactionHit, to_json_dict
from easy_verifier.core.pipeline import run_dimension
from easy_verifier.core.redact import scan
from easy_verifier.dimensions import security, supply_chain

LOCK = ".claude/x-lock.json"
CHANGED = "src/a.py"

#: 64-hex digests, the shape of ``.claude/harness-lock.json``.
DIGESTS = [hashlib.sha256(f"file-{n}".encode()).hexdigest() for n in range(4)]
LOCK_TEXT = json.dumps(
    {f"hooks/h{n}.py": digest for n, digest in enumerate(DIGESTS)}, indent=2
)

#: High-entropy, letter+digit mix, assembled at run time (never committed).
TOKEN = "FAKEfake" + base64.b64encode(hashlib.sha256(b"t121").digest()).decode()[:32]
SECRET_LINE = f'API_TOKEN = "{TOKEN}"\n'


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        env={
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@example.com",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@example.com",
            "PATH": "/usr/bin:/bin",
            "HOME": str(repo),
        },
    )


def _write(root: Path, files: dict[str, str]) -> None:
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def _repo(tmp_path: Path, change: dict[str, str]) -> Path:
    """Commit A holds the lock manifest and ``src/a.py``; commit B is ``change``."""
    _write(tmp_path, {LOCK: LOCK_TEXT, CHANGED: "def a():\n    return 1\n"})
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "base")
    _write(tmp_path, change)
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "change")
    return tmp_path


def _pack(repo: Path, scope: str = "changes"):
    ref = "HEAD" if scope == "changes" else None
    return run_dimension(security.DESCRIPTOR, repo, scope=scope, ref=ref)


def _metric(pack, name: str):
    (metric,) = compute_metrics(pack, curated_metric_tables()).by_name(name)
    return metric


@pytest.fixture
def clean_change(tmp_path: Path) -> Path:
    return _repo(tmp_path, {CHANGED: "def a():\n    return 2\n"})


@pytest.fixture
def secret_change(tmp_path: Path) -> Path:
    return _repo(tmp_path, {CHANGED: "def a():\n    return 2\n" + SECRET_LINE})


def test_fixture_values_are_detected_by_the_real_detectors() -> None:
    # Guards the fixture: without hits there is nothing for the filter to drop.
    assert scan(LOCK_TEXT).hits
    assert scan(SECRET_LINE).hits


def test_hits_only_in_an_unchanged_context_lockfile_are_not_counted(
    clean_change: Path,
) -> None:
    """AC 1 + AC 6 (the HUN-34 shape)."""
    pack = _pack(clean_change)
    assert LOCK in pack.files_read and CHANGED in pack.files_read
    assert any(hit.path == LOCK for hit in pack.redactions)  # still redacted
    assert pack.context_files == (LOCK,)

    hits = _metric(pack, "redaction_hits_observed")
    assert hits.outcome == 0
    assert hits.computed_from == (CHANGED,)
    share = _metric(pack, "redacted_file_share")
    assert share.outcome == 0.0
    assert share.computed_from == (CHANGED,)


def test_a_secret_in_a_changed_file_is_still_counted(secret_change: Path) -> None:
    """AC 2 + AC 4: measured hits count; the share is over measured files."""
    pack = _pack(secret_change)
    own = [hit for hit in pack.redactions if hit.path == CHANGED]
    assert own

    hits = _metric(pack, "redaction_hits_observed")
    assert hits.outcome == len(own)
    assert hits.outcome >= 1
    share = _metric(pack, "redacted_file_share")
    # 1 measured file with a hit / 1 measured file; the lock is in neither.
    assert share.outcome == 1.0
    assert LOCK not in share.derivation.split(" / ")[0]


def test_context_hits_stay_visible_and_redacted(clean_change: Path) -> None:
    """AC 3: the count is in the derivation; the excerpt carries fingerprints."""
    pack = _pack(clean_change)
    context_hits = [hit for hit in pack.redactions if hit.path == LOCK]
    hits = _metric(pack, "redaction_hits_observed")
    assert (
        f"{len(context_hits)} more in 1 context file(s) read from the whole repository"
    ) in hits.derivation
    assert LOCK in hits.derivation
    share = _metric(pack, "redacted_file_share")
    assert LOCK in share.derivation

    lock_text = "".join(e.text for e in pack.excerpts if e.path == LOCK)
    assert lock_text
    for digest in DIGESTS:
        assert digest not in lock_text
    assert context_hits[0].fingerprint in lock_text
    serialized = json.dumps(to_json_dict(pack))
    for digest in DIGESTS:
        assert digest not in serialized


def test_a_changed_lockfile_is_measured(tmp_path: Path) -> None:
    """Edge: a diff that changes the lockfile puts it in scope; its hits count."""
    extra = hashlib.sha256(b"file-new").hexdigest()
    repo = _repo(
        tmp_path,
        {LOCK: LOCK_TEXT.replace("}", f',\n  "hooks/new.py": "{extra}"\n}}')},
    )
    pack = _pack(repo)
    assert pack.context_files is None
    lock_hits = [hit for hit in pack.redactions if hit.path == LOCK]
    assert lock_hits
    assert _metric(pack, "redaction_hits_observed").outcome == len(lock_hits)


def test_project_scope_counts_every_file_and_serializes_as_before(
    clean_change: Path,
) -> None:
    """AC 5: no context split at project scope; no new key in the pack JSON."""
    pack = _pack(clean_change, scope="project")
    assert pack.context_files is None
    assert "context_files" not in to_json_dict(pack)
    hits = _metric(pack, "redaction_hits_observed")
    assert hits.outcome == len(pack.redactions) > 0
    assert "context file" not in hits.derivation


def test_empty_narrow_scope_still_abstains(clean_change: Path) -> None:
    """Edge: a narrow scope that reads nothing abstains as before."""
    pack = run_dimension(security.DESCRIPTOR, clean_change, scope="task", task_id="T9")
    assert pack.files_read == ()
    assert isinstance(
        _metric(pack, "redaction_hits_observed").outcome, MetricAbstention
    )


def test_a_hit_without_a_path_is_counted_as_before(clean_change: Path) -> None:
    """Edge: a path-less hit cannot be placed in a context file, so it counts."""
    pack = _pack(clean_change)
    pathless = RedactionHit(detector="d", fingerprint="f", offset=0, line=1)
    pack = replace(pack, redactions=(*pack.redactions, pathless))
    assert _metric(pack, "redaction_hits_observed").outcome == 1


def test_only_context_files_read_abstains(clean_change: Path) -> None:
    """Edge: when every file read is context, nothing was measured."""
    pack = _pack(clean_change)
    pack = replace(pack, context_files=pack.files_read)
    for name in ("redaction_hits_observed", "redacted_file_share"):
        outcome = _metric(pack, name).outcome
        assert isinstance(outcome, MetricAbstention), name
        assert "context" in outcome.reason


def test_other_dimensions_packs_serialize_as_before(clean_change: Path) -> None:
    """Only the security pack uses the fact, so only it carries the key: a
    supply-chain pack reading the same lockfile as context is unchanged."""
    pack = run_dimension(supply_chain.DESCRIPTOR, clean_change, "changes", ref="HEAD")
    assert LOCK in pack.files_read
    assert pack.context_files is None
    assert "context_files" not in to_json_dict(pack)
