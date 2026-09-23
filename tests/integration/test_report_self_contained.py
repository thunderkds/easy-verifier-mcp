"""AC #7: generated reports do not ask a browser to fetch anything."""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

from .conftest import run_cli, target_repo


class _FetchScanner(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.refs: list[str] = []
        self.script_tags = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag == "script":
            self.script_tags += 1
        for name, value in attrs:
            if name in {"src", "href", "srcset", "poster", "data", "action"} and value:
                self.refs.append(value)

    def handle_data(self, data: str) -> None:
        if "@import" in data or re.search(r"url\s*\(", data):
            self.refs.append("css-fetch")


def test_report_has_no_external_fetches(tmp_path: Path) -> None:
    target = target_repo(tmp_path / "target")
    completed = run_cli(
        "write-report",
        "--repo",
        str(target),
        "--dimensions",
        "architecture",
        input_text="[]",
    )
    assert completed.returncode == 0, completed.stderr
    report = target / __import__("json").loads(completed.stdout)["path"]
    scanner = _FetchScanner()
    scanner.feed(report.read_text(encoding="utf-8"))
    assert scanner.refs == []
    assert scanner.script_tags == 0


def test_self_containment_scanner_detects_a_real_external_reference() -> None:
    scanner = _FetchScanner()
    scanner.feed('<link href="https://cdn.example.invalid/x.css">')
    assert scanner.refs == ["https://cdn.example.invalid/x.css"]
