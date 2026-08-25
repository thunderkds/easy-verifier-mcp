"""T013 — ``write_report``: self-contained multi-dimension HTML report.

Every test builds its ``CombinedPack`` literally (DDR-0004): T012 is being
implemented in parallel, and this module must be able to fail for its own
reasons rather than for T012's.

Two habits this suite is deliberately built around, both earned by earlier
tasks in this project:

* The self-containment check (AC #2) **parses** the document and looks at URL
  *attributes* and stylesheet content — not a grep. A grep would fail on a URL
  quoted inside an escaped excerpt (which one fixture here deliberately
  contains) while happily missing a real ``<link>``.
* Every important assertion is written so that it can distinguish the correct
  implementation from a broken one. Where that is not obvious from the
  assertion, the test also pins the *negative* — e.g. AC #6 does not merely
  find a miss list somewhere, it asserts that **no** score exists outside a
  block that carries one.
"""

from __future__ import annotations

import os
import re
import stat
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path

import pytest

from easy_verifier.core import report as report_module
from easy_verifier.core.context import LIMITED_CONTEXT_WARNING
from easy_verifier.core.findings import ValidationError
from easy_verifier.core.models import (
    CombinedPack,
    CoverageSummary,
    DimensionSlot,
    EvidencePack,
    Excerpt,
    RedactionHit,
    SourceMiss,
    TruncationRecord,
)
from easy_verifier.core.report import ReportWriteError, write_report

VERIFIER_REPO = Path(__file__).resolve().parent.parent

SCORE_PATTERN = re.compile(r"\b\d{1,3}\.\d%")
COVERAGE_ENTRY_PATTERN = re.compile(r'<div class="coverage-entry">.*?</div>', re.DOTALL)


# ---------------------------------------------------------------------------
# Fixtures — CombinedPack built by hand, never imported from T012
# ---------------------------------------------------------------------------


def _excerpt(
    path: str = "src/app.py",
    start: int = 1,
    end: int = 3,
    text: str = "def app():\n    return 1\n",
) -> Excerpt:
    return Excerpt(path=path, start_line=start, end_line=end, text=text)


def _pack(
    dimension: str,
    *,
    mode: str = "kit-aware",
    scope: str = "project",
    excerpts: tuple[Excerpt, ...] = (),
    files_read: tuple[str, ...] = ("src/app.py",),
    sources_sought: tuple[str, ...] = ("README.md", "docs/"),
    sources_found: tuple[str, ...] = ("README.md",),
    sources_missing: tuple[SourceMiss, ...] = (),
    coverage_score: float | None = 0.5,
    warnings: tuple[str, ...] = (),
    truncated: bool = False,
    omitted_count: int = 0,
    redactions: tuple[RedactionHit, ...] = (),
    had_redactions: bool = False,
) -> EvidencePack:
    if not excerpts:
        excerpts = (_excerpt(),)
    if not sources_missing:
        sources_missing = (SourceMiss("docs/", "not found in the target repository"),)
    return EvidencePack(
        dimension=dimension,
        mode=mode,
        scope=scope,
        files_read=files_read,
        excerpts=excerpts,
        sources_sought=sources_sought,
        sources_found=sources_found,
        sources_missing=sources_missing,
        coverage_score=coverage_score,
        truncated=truncated,
        omitted_count=omitted_count,
        warnings=warnings,
        redactions=redactions,
        had_redactions=had_redactions,
        truncation=TruncationRecord(truncated=truncated, omitted_count=omitted_count),
    )


def _combined(
    packs: dict[str, EvidencePack],
    *,
    errors: dict[str, str] | None = None,
    combined: float | None = 0.5,
) -> CombinedPack:
    errors = errors or {}
    slots = [
        DimensionSlot(dimension=name, pack=pack, error=None)
        for name, pack in packs.items()
    ]
    slots.extend(
        DimensionSlot(dimension=name, pack=None, error=message)
        for name, message in errors.items()
    )
    return CombinedPack(
        slots=tuple(slots),
        coverage=CoverageSummary(
            per_dimension=tuple(
                (name, pack.coverage_score) for name, pack in packs.items()
            ),
            combined=combined,
            method="unweighted found/sought, per dimension",
            misses=tuple((name, pack.sources_missing) for name, pack in packs.items()),
        ),
        budget_model="per-dimension",
    )


def _finding(dimension: str, **overrides) -> dict:
    finding = {
        "dimension": dimension,
        "title": f"{dimension} title",
        "detail": f"{dimension} detail",
        "evidence_ref": "src/app.py:1-3",
        "confidence": "high",
    }
    finding.update(overrides)
    return finding


@pytest.fixture
def target_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "target"
    repo.mkdir()
    return repo


@pytest.fixture(autouse=True)
def verifier_repo_untouched():
    """AC #3 — nothing this module does may write into the verifier's own repo.

    Snapshotting the tree around *every* test is the point: an accidental
    relative-path write is exactly the failure this guards, and it would land in
    whichever repo the test process happens to be running from.
    """
    before = _tree_snapshot(VERIFIER_REPO)
    yield
    assert _tree_snapshot(VERIFIER_REPO) == before, (
        "a test wrote into the verifier's own repository (FR-017/NFR-007)"
    )


def _tree_snapshot(root: Path) -> dict[str, int]:
    snapshot: dict[str, int] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            d for d in dirnames if d not in {".git", "__pycache__", ".pytest_cache"}
        ]
        for name in filenames:
            path = Path(dirpath) / name
            try:
                snapshot[str(path)] = path.stat().st_size
            except OSError:
                snapshot[str(path)] = -1
    return snapshot


def _write(target: Path, findings, packs) -> tuple[Path, str]:
    result = write_report(findings, packs, target)
    path = target / result.path
    return path, path.read_text(encoding="utf-8")


def _freeze_clock(monkeypatch, moment: datetime) -> None:
    """Pin ``report``'s clock so two writes genuinely share a timestamp."""

    class _FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):  # noqa: ARG003 - signature parity with datetime
            return moment

    monkeypatch.setattr(report_module, "datetime", _FrozenDatetime)


# ---------------------------------------------------------------------------
# Self-containment parser (AC #2)
# ---------------------------------------------------------------------------


class _ExternalReferenceScanner(HTMLParser):
    """Collects everything the browser would fetch: URL attributes and CSS."""

    URL_ATTRS = frozenset(
        {"src", "href", "srcset", "poster", "data", "action", "background"}
    )

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.urls: list[str] = []
        self.css: list[str] = []
        self.script_tags: list[str] = []
        self._in_style = False

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            self.script_tags.append(tag)
        if tag == "style":
            self._in_style = True
        for name, value in attrs:
            if value is None:
                continue
            if name in self.URL_ATTRS:
                self.urls.append(value)
            if name == "style":
                self.css.append(value)

    def handle_endtag(self, tag):
        if tag == "style":
            self._in_style = False

    def handle_data(self, data):
        if self._in_style:
            self.css.append(data)


def _external_references(document: str) -> list[str]:
    scanner = _ExternalReferenceScanner()
    scanner.feed(document)
    offenders: list[str] = []
    for url in scanner.urls:
        stripped = url.strip()
        if stripped.startswith(("http://", "https://", "//")):
            offenders.append(f"url:{stripped}")
    for css in scanner.css:
        if "@import" in css:
            offenders.append("css:@import")
        for match in re.finditer(r"url\(\s*['\"]?([^'\")]+)", css):
            offenders.append(f"css-url:{match.group(1)}")
    offenders.extend(f"tag:{t}" for t in scanner.script_tags)
    return offenders


# ---------------------------------------------------------------------------
# AC #1 — one file, all dimensions, grouped, combined summary
# ---------------------------------------------------------------------------


def test_one_file_covers_all_submitted_dimensions(target_repo: Path):
    packs = _combined(
        {name: _pack(name) for name in ("architecture", "security", "test-strategy")}
    )
    findings = [
        _finding("architecture"),
        _finding("architecture", title="second architecture finding"),
        _finding("security"),
        _finding("test-strategy"),
        _finding("test-strategy", title="second test-strategy finding"),
    ]

    path, document = _write(target_repo, findings, packs)

    assert len(list((target_repo / "reports").glob("*.html"))) == 1
    assert path.name.endswith(".html")
    for dimension in ("architecture", "security", "test-strategy"):
        assert f"<h3>{dimension}</h3>" in document
    assert document.count('<article class="dimension"') == 3
    assert "All dimensions (combined)" in document
    assert document.startswith("<!DOCTYPE html>")


def test_dimension_that_produced_no_pack_renders_its_error(target_repo: Path):
    packs = _combined(
        {"architecture": _pack("architecture")},
        errors={"security": "scope resolution failed"},
    )

    _, document = _write(target_repo, [_finding("architecture")], packs)

    assert "scope resolution failed" in document
    assert "<h3>security</h3>" in document


# ---------------------------------------------------------------------------
# AC #2 — self-contained
# ---------------------------------------------------------------------------


def test_report_requests_nothing_from_the_network(target_repo: Path):
    # The excerpt carries a URL on purpose: a correct implementation escapes it
    # into text, and this test must not confuse that with a fetched resource.
    packs = _combined(
        {
            "architecture": _pack(
                "architecture",
                excerpts=(
                    _excerpt(text='LOGO = "https://cdn.example.com/logo.png"\n'),
                ),
            )
        }
    )

    _, document = _write(target_repo, [_finding("architecture")], packs)

    assert "https://cdn.example.com/logo.png" in document, (
        "the excerpt's URL should still be visible as text"
    )
    assert _external_references(document) == []


def test_the_self_containment_scanner_can_actually_fail():
    """The AC #2 check is only worth anything if it detects a real offender."""
    assert _external_references(
        '<html><head><link href="https://cdn.example.com/x.css"></head></html>'
    ) == ["url:https://cdn.example.com/x.css"]
    assert _external_references(
        "<html><head><style>@import url('https://x/y.css');</style></head></html>"
    ) == ["css:@import", "css-url:https://x/y.css"]
    assert _external_references('<script src="x.js"></script>') == ["tag:script"]


# ---------------------------------------------------------------------------
# AC #3 — written under the target's reports/, nowhere else
# ---------------------------------------------------------------------------


def test_written_under_target_reports_directory(target_repo: Path):
    packs = _combined({"architecture": _pack("architecture")})

    result = write_report([_finding("architecture")], packs, target_repo)

    written = Path(result.absolute_path)
    assert written.parent == target_repo / "reports"
    assert result.path.startswith("reports/")
    assert not Path(result.path).is_absolute()
    assert [p.name for p in target_repo.iterdir()] == ["reports"]


def test_self_evaluation_writes_into_the_target_which_happens_to_be_itself(
    tmp_path: Path,
):
    """The target genuinely being the evaluated repo is correct (FR-017); the
    thing forbidden is writing into the *verifier* while evaluating someone
    else. The autouse snapshot fixture is what separates the two."""
    repo = tmp_path / "self"
    (repo / "src").mkdir(parents=True)
    packs = _combined({"architecture": _pack("architecture")})

    result = write_report([_finding("architecture")], packs, repo)

    assert (repo / result.path).exists()


def test_refuses_to_write_when_reports_escapes_the_repository(
    tmp_path: Path, target_repo: Path
):
    outside = tmp_path / "outside"
    outside.mkdir()
    (target_repo / "reports").symlink_to(outside, target_is_directory=True)
    packs = _combined({"architecture": _pack("architecture")})

    with pytest.raises(ReportWriteError, match="outside the repository"):
        write_report([_finding("architecture")], packs, target_repo)

    assert list(outside.iterdir()) == []


def test_symlinked_target_repo_resolves_consistently(tmp_path: Path):
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real, target_is_directory=True)
    packs = _combined({"architecture": _pack("architecture")})

    result = write_report([_finding("architecture")], packs, link)

    assert (real / "reports").is_dir()
    assert result.path.startswith("reports/")


# ---------------------------------------------------------------------------
# AC #4 / #5 — collision-proof, self-describing, never overwrites
# ---------------------------------------------------------------------------


def test_filename_encodes_scope_and_subsecond_utc(target_repo: Path):
    packs = _combined({"architecture": _pack("architecture", scope="worktree")})

    result = write_report([_finding("architecture")], packs, target_repo)

    assert re.fullmatch(
        r"evidence-report-worktree-\d{8}T\d{6}-\d{6}Z\.html",
        Path(result.path).name,
    ), result.path


def test_two_writes_in_the_same_instant_do_not_collide(target_repo: Path, monkeypatch):
    _freeze_clock(monkeypatch, datetime(2026, 8, 25, 9, 53, 41, 123456, tzinfo=UTC))
    packs = _combined({"architecture": _pack("architecture")})

    first = write_report([_finding("architecture")], packs, target_repo)
    second = write_report([_finding("architecture")], packs, target_repo)

    assert first.path != second.path
    assert len(list((target_repo / "reports").glob("*.html"))) == 2


def test_an_existing_filename_is_never_overwritten(target_repo: Path, monkeypatch):
    _freeze_clock(monkeypatch, datetime(2026, 8, 25, 9, 53, 41, 123456, tzinfo=UTC))
    reports = target_repo / "reports"
    reports.mkdir()
    squatter = reports / "evidence-report-project-20260825T095341-123456Z.html"
    squatter.write_text("PRE-EXISTING CONTENT", encoding="utf-8")
    packs = _combined({"architecture": _pack("architecture")})

    result = write_report([_finding("architecture")], packs, target_repo)

    assert squatter.read_text(encoding="utf-8") == "PRE-EXISTING CONTENT"
    assert Path(result.path).name != squatter.name
    assert (
        (target_repo / result.path)
        .read_text(encoding="utf-8")
        .startswith("<!DOCTYPE html>")
    )


# ---------------------------------------------------------------------------
# AC #6 — no coverage score without its named miss list
# ---------------------------------------------------------------------------


def test_every_rendered_score_sits_with_its_named_miss_list(target_repo: Path):
    packs = _combined(
        {
            "architecture": _pack(
                "architecture",
                sources_missing=(
                    SourceMiss("docs/adr", "not found in the target repository"),
                ),
            ),
            "security": _pack(
                "security",
                sources_missing=(SourceMiss(".env", "excluded: secret-bearing"),),
            ),
        }
    )

    _, document = _write(
        target_repo, [_finding("architecture"), _finding("security")], packs
    )

    body = document.split("</style>", 1)[1]
    entries = COVERAGE_ENTRY_PATTERN.findall(body)
    assert len(entries) == 3  # two dimensions + the combined entry

    scores_in_entries = 0
    for entry in entries:
        assert "miss-list" in entry, f"score rendered without a miss list: {entry}"
        scores_in_entries += len(SCORE_PATTERN.findall(entry))

    all_scores = SCORE_PATTERN.findall(body)
    assert all_scores, "no coverage score was rendered at all"
    assert len(all_scores) == scores_in_entries, (
        "a coverage score appears outside a coverage entry, i.e. without its "
        f"miss list: {all_scores}"
    )
    # The named misses themselves, not just the presence of a container.
    assert "docs/adr" in body
    assert ".env" in body


def test_a_dimension_with_no_misses_still_says_so_next_to_its_score(
    target_repo: Path,
):
    packs = _combined(
        {"architecture": _pack("architecture", sources_missing=(), coverage_score=1.0)}
    )
    packs = CombinedPack(
        slots=packs.slots,
        coverage=CoverageSummary(
            per_dimension=(("architecture", 1.0),),
            combined=1.0,
            method="unweighted found/sought, per dimension",
            misses=(("architecture", ()),),
        ),
        budget_model="per-dimension",
    )

    _, document = _write(target_repo, [_finding("architecture")], packs)

    body = document.split("</style>", 1)[1]
    for entry in COVERAGE_ENTRY_PATTERN.findall(body):
        assert "miss-list" in entry
    assert "No sources missing" in body


def test_a_score_of_none_reads_as_not_applicable_not_as_zero(target_repo: Path):
    pack = _pack(
        "architecture", sources_sought=(), sources_found=(), coverage_score=None
    )
    packs = CombinedPack(
        slots=(DimensionSlot("architecture", pack, None),),
        coverage=CoverageSummary(
            per_dimension=(("architecture", None),),
            combined=None,
            method="unweighted found/sought, per dimension",
            misses=(("architecture", pack.sources_missing),),
        ),
        budget_model="per-dimension",
    )

    _, document = _write(target_repo, [_finding("architecture")], packs)

    # "n/a", not "0.0%" -- and deliberately without a fabricated cause: this
    # renderer cannot tell "sought nothing" from "the dimension crashed".
    assert "n/a" in document
    assert "no sources were sought" not in document
    assert "0.0%" not in document


# ---------------------------------------------------------------------------
# AC #7 — standalone limited-context warning
# ---------------------------------------------------------------------------


def test_standalone_limited_context_warning_is_prominent(target_repo: Path):
    packs = _combined(
        {
            "architecture": _pack(
                "architecture",
                mode="standalone",
                warnings=(LIMITED_CONTEXT_WARNING,),
            )
        }
    )

    _, document = _write(target_repo, [_finding("architecture")], packs)

    assert LIMITED_CONTEXT_WARNING[:60] in document
    banner_at = document.index('class="warning-banner"')
    first_dimension_at = document.index('class="dimensions"')
    assert banner_at < first_dimension_at, "the warning must precede the evidence"


def test_no_warning_banner_when_there_are_no_warnings(target_repo: Path):
    packs = _combined({"architecture": _pack("architecture")})

    _, document = _write(target_repo, [_finding("architecture")], packs)

    assert 'class="warning-banner"' not in document.split("</style>", 1)[1]


# ---------------------------------------------------------------------------
# AC #8 — evidence, confidence, suggestion
# ---------------------------------------------------------------------------


def test_finding_renders_evidence_confidence_and_suggestion(target_repo: Path):
    packs = _combined({"architecture": _pack("architecture")})
    findings = [
        _finding(
            "architecture",
            title="Entry point is undocumented",
            detail="README names no entry point.",
            confidence="medium",
            suggestion="Document the entry point in README.md.",
        )
    ]

    _, document = _write(target_repo, findings, packs)

    assert "Entry point is undocumented" in document
    assert "README names no entry point." in document
    assert "<code>src/app.py:1-3</code>" in document
    assert "medium" in document
    assert "Document the entry point in README.md." in document
    assert "def app():" in document, "the cited excerpt itself should be quoted"


def test_a_finding_without_a_suggestion_renders_no_suggestion_block(
    target_repo: Path,
):
    packs = _combined({"architecture": _pack("architecture")})

    _, document = _write(target_repo, [_finding("architecture")], packs)

    assert "Suggested improvement" not in document


def test_zero_findings_still_produces_a_report_with_coverage(target_repo: Path):
    packs = _combined({"architecture": _pack("architecture")})

    _, document = _write(target_repo, [], packs)

    assert "No findings were submitted for this dimension" in document
    assert SCORE_PATTERN.search(document.split("</style>", 1)[1])


# ---------------------------------------------------------------------------
# AC #9 — invalid findings write nothing
# ---------------------------------------------------------------------------


def test_invalid_findings_write_no_file(target_repo: Path):
    packs = _combined({"architecture": _pack("architecture")})
    invalid = [_finding("architecture")]
    del invalid[0]["confidence"]

    with pytest.raises(ValidationError):
        write_report(invalid, packs, target_repo)

    assert not (target_repo / "reports").exists()
    assert list(target_repo.iterdir()) == []


def test_invalid_findings_write_nothing_even_into_an_existing_reports_dir(
    target_repo: Path,
):
    reports = target_repo / "reports"
    reports.mkdir()
    packs = _combined({"architecture": _pack("architecture")})

    with pytest.raises(ValidationError):
        write_report(
            [_finding("architecture", evidence_ref="src/app.py:99-100")],
            packs,
            target_repo,
        )

    assert list(reports.iterdir()) == []


# ---------------------------------------------------------------------------
# AC #10 / #15 — the NFR-011 sensitivity advisory
# ---------------------------------------------------------------------------


def test_first_write_returns_and_renders_the_advisory(target_repo: Path):
    packs = _combined({"architecture": _pack("architecture")})

    first = write_report([_finding("architecture")], packs, target_repo)
    second = write_report([_finding("architecture")], packs, target_repo)

    assert first.advisory is not None
    assert second.advisory is None, "the advisory marks the first write only"
    first_doc = (target_repo / first.path).read_text(encoding="utf-8")
    assert "first report written into this repository" in first_doc
    second_doc = (target_repo / second.path).read_text(encoding="utf-8")
    assert "Before you share this report" in second_doc


def test_the_advisory_names_both_destinations(target_repo: Path):
    packs = _combined({"architecture": _pack("architecture")})

    result = write_report([_finding("architecture")], packs, target_repo)

    advisory = result.advisory or ""
    lowered = advisory.lower()
    # Destination 1: the report itself travelling out of the repo.
    assert "committed" in lowered
    assert "ticket" in lowered
    assert "pull request" in lowered
    # Destination 2: pack content reaching the calling agent in MCP mode.
    assert "mcp" in lowered
    assert "hosted model" in lowered
    assert advisory in (target_repo / result.path).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# AC #11 — no container-internal paths
# ---------------------------------------------------------------------------


def test_container_internal_paths_never_reach_the_document(target_repo: Path):
    packs = _combined(
        {
            "architecture": _pack(
                "architecture",
                files_read=("/workspace/src/app.py",),
                excerpts=(_excerpt(path="/workspace/src/app.py"),),
                sources_missing=(
                    SourceMiss(
                        "/workspace/docs/adr", "not found in the target repository"
                    ),
                ),
                redactions=(
                    RedactionHit(
                        detector="generic-assignment",
                        fingerprint="FAKEfake…ab12cd34ef56",
                        offset=10,
                        line=2,
                        path="/workspace/src/settings.py",
                    ),
                ),
                had_redactions=True,
            )
        }
    )

    _, document = _write(
        target_repo,
        [_finding("architecture", evidence_ref="/workspace/src/app.py:1-3")],
        packs,
    )

    assert "/workspace" not in document
    assert "app.py" in document


def test_a_relative_path_that_climbs_out_of_the_repo_is_not_printed(
    target_repo: Path,
):
    packs = _combined(
        {
            "architecture": _pack(
                "architecture",
                files_read=("../../etc/passwd",),
                sources_missing=(
                    SourceMiss(
                        "../../../secrets/prod.yml",
                        "not found in the target repository",
                    ),
                ),
            )
        }
    )

    _, document = _write(target_repo, [_finding("architecture")], packs)

    assert ".." not in document
    assert "passwd" in document, (
        "the basename is still reported, only the climb is dropped"
    )


def test_the_repo_prefix_is_scrubbed_from_free_text(target_repo: Path):
    """The container case: the repo *is* mounted at the leaked prefix, so an
    absolute path inside prose is not a path field and must still not survive."""
    packs = _combined(
        {
            "architecture": _pack(
                "architecture",
                excerpts=(_excerpt(text=f"open('{target_repo}/src/app.py')\n"),),
            )
        }
    )

    _, document = _write(
        target_repo,
        [_finding("architecture", detail=f"the file {target_repo}/src/app.py is read")],
        packs,
    )

    assert str(target_repo) not in document


# ---------------------------------------------------------------------------
# AC #12 — escaping
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "field",
    ["title", "detail", "suggestion"],
)
def test_caller_supplied_text_is_escaped(target_repo: Path, field: str):
    packs = _combined({"architecture": _pack("architecture")})
    payload = "<script>alert(1)</script>"

    _, document = _write(
        target_repo, [_finding("architecture", **{field: payload})], packs
    )

    assert payload not in document
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in document
    assert _external_references(document) == []
    scanner = _ExternalReferenceScanner()
    scanner.feed(document)
    assert scanner.script_tags == []


def test_markup_in_excerpts_and_miss_reasons_is_escaped_too(target_repo: Path):
    packs = _combined(
        {
            "architecture": _pack(
                "architecture",
                excerpts=(_excerpt(text='<img src=x onerror="alert(1)">\n'),),
                sources_missing=(SourceMiss("<b>docs</b>", 'not found "<anywhere>"'),),
            )
        }
    )

    _, document = _write(target_repo, [_finding("architecture")], packs)

    assert "<img" not in document
    assert "onerror" not in document.replace("onerror=&quot;", "")
    assert "<b>docs</b>" not in document
    assert "&lt;b&gt;docs&lt;/b&gt;" in document


def test_no_markdown_subset_is_honoured(target_repo: Path):
    packs = _combined({"architecture": _pack("architecture")})

    _, document = _write(
        target_repo,
        [_finding("architecture", detail="**bold** and [link](https://evil.example)")],
        packs,
    )

    assert "<strong>bold</strong>" not in document
    assert "<a href" not in document
    assert "**bold**" in document


def test_non_ascii_survives_intact(target_repo: Path):
    packs = _combined({"architecture": _pack("architecture")})

    path, document = _write(
        target_repo,
        [_finding("architecture", detail="Überprüfung — 検証 — ✅")],
        packs,
    )

    assert '<meta charset="utf-8">' in document
    assert "Überprüfung — 検証 — ✅" in path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# AC #13 — truncation and redaction are visible
# ---------------------------------------------------------------------------


def test_truncation_and_redaction_are_visible(target_repo: Path):
    packs = _combined(
        {
            "architecture": _pack(
                "architecture",
                truncated=True,
                omitted_count=7,
                had_redactions=True,
                redactions=(
                    RedactionHit(
                        detector="entropy",
                        fingerprint="FAKE…9f2c1b",
                        offset=4,
                        line=12,
                        path="src/settings.py",
                    ),
                ),
            )
        }
    )

    _, document = _write(target_repo, [_finding("architecture")], packs)

    assert "Truncated by the evidence budget" in document
    assert "7" in document
    assert "lower bound" in document
    assert "fingerprints" in document
    assert "FAKE…9f2c1b" in document
    assert "src/settings.py" in document


def test_an_untruncated_unredacted_pack_says_so(target_repo: Path):
    packs = _combined({"architecture": _pack("architecture")})

    _, document = _write(target_repo, [_finding("architecture")], packs)

    assert "Not truncated" in document
    assert "No secrets were detected" in document
    assert "Truncated by the evidence budget" not in document


def test_redaction_flag_fires_even_when_no_hit_survived_the_budget(
    target_repo: Path,
):
    """``had_redactions`` is authoritative: a secret redacted out of an excerpt
    the budget then rejected leaves no hit on the pack, and the advisory must
    still fire."""
    packs = _combined(
        {"architecture": _pack("architecture", had_redactions=True, redactions=())}
    )

    _, document = _write(target_repo, [_finding("architecture")], packs)

    assert "Secrets were detected" in document
    assert "No secrets were detected" not in document


# ---------------------------------------------------------------------------
# AC #14 — excluded is visibly distinct from not-found and not-examined
# ---------------------------------------------------------------------------


def test_excluded_secret_bearing_is_distinct_from_missing_and_unexamined(
    target_repo: Path,
):
    packs = _combined(
        {
            "security": _pack(
                "security",
                sources_missing=(
                    SourceMiss(".env", "excluded: secret-bearing"),
                    SourceMiss(
                        "docs/threat-model.md", "not found in the target repository"
                    ),
                    SourceMiss(
                        "SECURITY.md", "not examined: outside the resolved scope"
                    ),
                ),
            )
        }
    )

    _, document = _write(target_repo, [_finding("security")], packs)

    assert 'class="miss-excluded"' in document
    assert 'class="miss-missing"' in document
    assert 'class="miss-unexamined"' in document
    excluded_row = re.search(r'<li class="miss-excluded">.*?</li>', document, re.DOTALL)
    assert excluded_row and "excluded: secret-bearing" in excluded_row.group(0)
    missing_row = re.search(r'<li class="miss-missing">.*?</li>', document, re.DOTALL)
    assert missing_row and "not found" in missing_row.group(0)
    assert "excluded" not in missing_row.group(0)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_read_only_reports_directory_reports_an_actionable_error(target_repo: Path):
    reports = target_repo / "reports"
    reports.mkdir()
    reports.chmod(stat.S_IRUSR | stat.S_IXUSR)
    packs = _combined({"architecture": _pack("architecture")})

    try:
        with pytest.raises(ReportWriteError) as excinfo:
            write_report([_finding("architecture")], packs, target_repo)
    finally:
        reports.chmod(stat.S_IRWXU)

    message = str(excinfo.value)
    assert "read-only" in message
    assert "Traceback" not in message


def test_a_missing_target_repository_is_a_clear_message(tmp_path: Path):
    packs = _combined({"architecture": _pack("architecture")})

    with pytest.raises(ValueError, match="does not exist"):
        write_report([_finding("architecture")], packs, tmp_path / "nope")


def test_many_findings_stay_in_one_document(target_repo: Path):
    packs = _combined({"architecture": _pack("architecture")})
    findings = [_finding("architecture", title=f"finding {i}") for i in range(300)]

    path, document = _write(target_repo, findings, packs)

    assert len(list((target_repo / "reports").glob("*.html"))) == 1
    assert document.count('<li class="finding">') == 300
    assert path.stat().st_size > 0


# --- Stage 4 review regressions (T013) ------------------------------------


def test_a_failed_dimension_is_never_rendered_as_a_clean_all_clear(
    target_repo: Path,
) -> None:
    """A dimension that produced no pack must not render as a benign one.

    ``_format_score(None)`` asserted "no sources were sought" and an empty miss
    list asserted "every declared source on the checklist was reached". Both
    are false for a dimension that crashed, and together they rendered a
    RuntimeError as a clean row -- in a document whose dimension section
    printed the error message a few hundred pixels further down. Found by
    rendering the document and looking at it, not by reading the diff.
    """
    packs = CombinedPack(
        slots=(DimensionSlot("boom", None, "RuntimeError: collector exploded"),),
        coverage=CoverageSummary(
            per_dimension=(("boom", None),),
            combined=None,
            method="pooled found/sought",
            misses=(),
        ),
        budget_model="per-dimension",
    )

    _, document = _write(target_repo, [], packs)

    assert "every declared source on the checklist was reached" not in document
    assert "no sources were sought" not in document
    # the honest signal is still present
    assert "collector exploded" in document


def test_a_dimension_that_genuinely_reached_everything_still_reads_as_clean(
    target_repo: Path,
) -> None:
    """The fix must not turn every empty miss list into a caveat.

    A warning that fires on every report carries no information -- the same
    reason the exclusion note on the aggregate is conditional.
    """
    pack = _pack(
        "architecture",
        sources_sought=("README.md",),
        sources_found=("README.md",),
        coverage_score=1.0,
    )
    packs = CombinedPack(
        slots=(DimensionSlot("architecture", pack, None),),
        coverage=CoverageSummary(
            per_dimension=(("architecture", 1.0),),
            combined=1.0,
            method="pooled found/sought",
            misses=(("architecture", ()),),
        ),
        budget_model="per-dimension",
    )

    _, document = _write(target_repo, [_finding("architecture")], packs)

    assert "every declared source on the checklist was reached" in document


def test_a_secret_quoted_in_a_finding_never_reaches_the_written_report(
    target_repo: Path,
) -> None:
    """Finding text is the calling agent's prose, and it is a real egress path.

    Excerpts are redacted at the evidence layer (T004) before they reach a
    pack, so the report inherited that protection for quoted code. Finding
    titles, details and suggestions inherited nothing -- and an agent reporting
    a hardcoded credential routinely quotes the credential. The value landed
    verbatim in a file written into the evaluated repository, whose own
    advisory says it will be committed, attached to tickets and pasted into
    pull requests.
    """
    secret = "AKIAIOSFODNN7EXAMPLE"
    pack = _pack("security")
    packs = CombinedPack(
        slots=(DimensionSlot("security", pack, None),),
        coverage=CoverageSummary(
            per_dimension=(("security", 1.0),),
            combined=1.0,
            method="pooled found/sought",
            misses=(("security", ()),),
        ),
        budget_model="per-dimension",
    )
    finding = _finding(
        "security",
        title=f"Hardcoded key {secret} in app.py",
        detail=f"The literal value is {secret} and must be rotated.",
        suggestion=f"Replace {secret} with an environment variable.",
    )

    _, document = _write(target_repo, [finding], packs)

    assert secret not in document
    # the finding itself is still rendered -- redaction, not suppression
    assert "Hardcoded key" in document
    assert "must be rotated" in document


def test_ordinary_finding_prose_survives_redaction_unchanged(
    target_repo: Path,
) -> None:
    """Redaction must not eat normal text -- a renderer that mangles prose is
    a different bug, not a fix."""
    pack = _pack("architecture")
    packs = CombinedPack(
        slots=(DimensionSlot("architecture", pack, None),),
        coverage=CoverageSummary(
            per_dimension=(("architecture", 1.0),),
            combined=1.0,
            method="pooled found/sought",
            misses=(("architecture", ()),),
        ),
        budget_model="per-dimension",
    )
    prose = "The module boundary between core and adapters is not enforced."
    finding = _finding("architecture", title="Layering", detail=prose)

    _, document = _write(target_repo, [finding], packs)

    assert prose in document
