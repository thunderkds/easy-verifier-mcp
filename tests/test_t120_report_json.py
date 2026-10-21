"""T120 -- every report gets a JSON score summary next to its HTML (FR-087).

The sidecar is for programs (easy-personal reads scores over time), so it holds
numbers only. These tests pin the pair, the agreement with the HTML, and the
absence of any agent-authored prose.
"""

from __future__ import annotations

import errno
import json
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest
from test_t013_report import _combined, _finding, _freeze_clock, _pack

from easy_verifier.core.findings import ValidationError
from easy_verifier.core.report import REPORTS_DIR_ENV, ReportWriteError, write_report
from easy_verifier.core.synthesis import combined_pack
from easy_verifier.dimensions import dimension_names

# Plain words: a credential-shaped canary would be redacted out of the HTML too.
CANARY = "quokka marker sentence unique to this test"


@pytest.fixture(autouse=True)
def _no_reports_dir(monkeypatch):
    monkeypatch.delenv(REPORTS_DIR_ENV, raising=False)


def _repo(tmp_path: Path, name: str = "target") -> Path:
    repo = tmp_path / name
    (repo / "src").mkdir(parents=True)
    (repo / "README.md").write_text("# Target\n", encoding="utf-8")
    (repo / "src/app.py").write_text("def main():\n    return 1\n", encoding="utf-8")
    return repo


def _full_packs(repo: Path):
    return combined_pack(dimension_names(), repo_path=str(repo), scope="project")


def _sidecar(html_path: Path) -> dict:
    return json.loads(html_path.with_suffix(".json").read_text(encoding="utf-8"))


def test_report_json_sibling_matches_the_html(tmp_path: Path):
    repo = _repo(tmp_path)
    result = write_report([], _full_packs(repo), repo)
    html_path = Path(result.absolute_path)
    json_path = html_path.with_suffix(".json")

    assert json_path.is_file() and json_path.parent == html_path.parent
    data = json.loads(json_path.read_text(encoding="utf-8"))
    document = html_path.read_text(encoding="utf-8")

    assert data["schema_version"] == 1
    assert data["scope"] == "project"
    stamp = datetime.strptime(data["generated_at"], "%Y-%m-%dT%H:%M:%SZ")
    assert abs((datetime.now(UTC).replace(tzinfo=None) - stamp).total_seconds()) < 60
    assert [d["dimension"] for d in data["dimensions"]] == [
        n for n in dimension_names() if n != "change-risk"
    ]  # not gathered at project scope
    if data["overall"]["abstained"]:
        assert data["overall"]["value"] is None
        assert "Overall rating withheld" in document
    else:
        assert f'{data["overall"]["value"]}/100' in document
    for item in data["dimensions"]:
        assert item["abstained"] == (item["rating"] is None)
        assert (item["reason_code"] is not None) == item["abstained"]


def test_report_json_states_abstention_never_zero(tmp_path: Path):
    """Handbuilt one-dimension packs cannot be scored: no overall, no numbers."""
    repo = tmp_path / "target"
    repo.mkdir()
    packs = _combined({"architecture": _pack("architecture")})
    result = write_report([_finding("architecture")], packs, repo)
    data = _sidecar(Path(result.absolute_path))

    assert data["overall"] == {
        "abstained": True,
        "reason_code": "incomplete_dimensions",
        "value": None,
    }
    assert data["dimensions"] == []


def test_report_json_holds_no_agent_prose_or_file_contents(tmp_path: Path):
    repo = tmp_path / "target"
    repo.mkdir()
    packs = _combined({"architecture": _pack("architecture")})
    finding = _finding("architecture", title=CANARY, detail=CANARY)
    result = write_report([finding], packs, repo)
    raw = Path(result.absolute_path).with_suffix(".json").read_text(encoding="utf-8")
    assert CANARY in Path(result.absolute_path).read_text(encoding="utf-8")
    assert CANARY not in raw

    full = tmp_path / "full"
    (full / "src").mkdir(parents=True)
    (full / "src/app.py").write_text(f"# {CANARY}\ndef f():\n    return 1\n")
    result = write_report([], _full_packs(full), full, agent_input={"summary": CANARY})
    raw = Path(result.absolute_path).with_suffix(".json").read_text(encoding="utf-8")
    assert CANARY not in raw
    assert set(json.loads(raw)) == {
        "schema_version", "scope", "generated_at", "overall", "dimensions",
    }


def test_report_json_is_deterministic_sorted_ascii(tmp_path: Path, monkeypatch):
    repo = _repo(tmp_path)
    packs = _full_packs(repo)
    _freeze_clock(monkeypatch, datetime(2026, 10, 21, 12, 0, 0, tzinfo=UTC))
    first = write_report([], packs, repo)
    second = write_report([], packs, repo)
    a = Path(first.absolute_path).with_suffix(".json").read_text(encoding="utf-8")
    b = Path(second.absolute_path).with_suffix(".json").read_text(encoding="utf-8")

    assert a == b
    assert a.rstrip("\n") == json.dumps(
        json.loads(a), sort_keys=True, separators=(",", ":")
    )
    assert a.isascii()


def test_report_json_not_written_when_validation_fails(tmp_path: Path):
    repo = tmp_path / "target"
    repo.mkdir()
    packs = _combined({"architecture": _pack("architecture")})
    bad = _finding("architecture", evidence_ref="nowhere.py:1-2")
    with pytest.raises(ValidationError):
        write_report([bad], packs, repo)
    assert not (repo / "reports").exists()


def test_report_json_failure_leaves_no_half_pair(tmp_path: Path, monkeypatch):
    repo = _repo(tmp_path)
    packs = _full_packs(repo)
    real_open = os.open

    def deny_json(path, flags, *args, **kwargs):
        if str(path).endswith(".json"):
            raise OSError(errno.EACCES, "Permission denied")
        return real_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(os, "open", deny_json)
    with pytest.raises(ReportWriteError):
        write_report([], packs, repo)
    monkeypatch.undo()
    assert list((repo / "reports").iterdir()) == []


def test_report_json_goes_to_the_env_reports_dir_for_a_non_ascii_repo(
    tmp_path: Path, monkeypatch
):
    repo = _repo(tmp_path, "projet-été")
    base = tmp_path / "shared"
    monkeypatch.setenv(REPORTS_DIR_ENV, str(base))
    result = write_report([], _full_packs(repo), repo)

    out = base / "projet-été"
    assert sorted(p.suffix for p in out.iterdir()) == [".html", ".json"]
    assert Path(result.absolute_path).with_suffix(".json").parent == out
    assert not (repo / "reports").exists()


def test_report_json_never_overwrites_an_existing_json(tmp_path: Path, monkeypatch):
    repo = _repo(tmp_path)
    packs = _full_packs(repo)
    _freeze_clock(monkeypatch, datetime(2026, 10, 21, 12, 0, 0, tzinfo=UTC))
    stray = repo / "reports" / "evidence-report-project-20261021T120000-000000Z.json"
    stray.parent.mkdir()
    stray.write_text("stray", encoding="utf-8")

    result = write_report([], packs, repo)
    html_path = Path(result.absolute_path)

    assert stray.read_text(encoding="utf-8") == "stray"
    assert html_path.name.endswith("-2.html")
    assert html_path.with_suffix(".json").is_file()


def test_report_json_respects_the_reports_dir_guard(tmp_path: Path):
    repo = _repo(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    (repo / "reports").symlink_to(outside, target_is_directory=True)
    with pytest.raises(ReportWriteError):
        write_report([], _full_packs(repo), repo)
    assert list(outside.iterdir()) == []
