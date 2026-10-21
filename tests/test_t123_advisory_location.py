"""T123: the sensitivity notice names where the report was actually written."""

from __future__ import annotations

import html
import re
from pathlib import Path

import pytest

from easy_verifier.core.report import (
    REPORTS_DIR_ENV,
    SENSITIVITY_ADVISORY,
    SHARED_DIR_SENSITIVITY_ADVISORY,
    write_report,
)
from easy_verifier.core.synthesis import combined_pack
from easy_verifier.dimensions import dimension_names


@pytest.fixture(autouse=True)
def _no_reports_dir(monkeypatch):
    monkeypatch.delenv(REPORTS_DIR_ENV, raising=False)


def _write(tmp_path: Path):
    repo = tmp_path / "target"
    (repo / "src").mkdir(parents=True)
    (repo / "README.md").write_text("# Target\n", encoding="utf-8")
    (repo / "src/app.py").write_text("def main():\n    return 1\n", encoding="utf-8")
    packs = combined_pack(dimension_names(), repo_path=str(repo), scope="project")
    result = write_report([], packs, repo)
    document = Path(result.absolute_path).read_text(encoding="utf-8")
    marker = re.search(r'<p class="first-write">(.*?)</p>', document, re.S)
    assert marker is not None
    folded = re.search(r"<details><summary>.*?</summary><p>(.*?)</p>", document, re.S)
    assert folded is not None
    _write.marker = html.unescape(marker.group(1))
    return result.advisory, html.unescape(folded.group(1))


def test_report_advisory_default_keeps_the_in_repository_text(tmp_path):
    advisory, in_html = _write(tmp_path)
    assert advisory == in_html == SENSITIVITY_ADVISORY
    assert "inside the evaluated repository" in advisory


@pytest.mark.parametrize("value", [None, ""])
def test_report_advisory_unset_or_empty_env_is_the_default(
    tmp_path, monkeypatch, value
):
    if value is not None:
        monkeypatch.setenv(REPORTS_DIR_ENV, value)
    assert _write(tmp_path)[0] == SENSITIVITY_ADVISORY


def test_report_advisory_with_reports_dir_env_says_outside_the_repository(
    tmp_path, monkeypatch
):
    monkeypatch.setenv(REPORTS_DIR_ENV, str(tmp_path / "shared"))
    advisory, in_html = _write(tmp_path)
    assert advisory == in_html == SHARED_DIR_SENSITIVITY_ADVISORY
    assert "inside the evaluated repository" not in advisory
    assert "outside the evaluated repository" in advisory
    assert "shared reports directory" in advisory


@pytest.mark.parametrize(
    "text", [SENSITIVITY_ADVISORY, SHARED_DIR_SENSITIVITY_ADVISORY]
)
def test_report_advisory_keeps_the_nfr011_exposures(text):
    assert "hosted model" in text
    assert "excerpts still quote real source code and file paths" in text


def test_report_first_write_marker_default_is_unchanged(tmp_path):
    _write(tmp_path)
    assert _write.marker == (
        "This is the first report written into this repository's reports/ directory."
    )


def test_report_first_write_marker_names_the_shared_directory(tmp_path, monkeypatch):
    monkeypatch.setenv(REPORTS_DIR_ENV, str(tmp_path / "shared"))
    _write(tmp_path)
    assert _write.marker == (
        "This is the first report written into this repository's folder in the "
        "shared reports directory."
    )


def test_report_env_dir_inside_the_repo_gets_the_inside_text(tmp_path, monkeypatch):
    monkeypatch.setenv(REPORTS_DIR_ENV, str(tmp_path / "target" / "out"))
    assert _write(tmp_path)[0] == SENSITIVITY_ADVISORY
    assert "reports/ directory" in _write.marker
