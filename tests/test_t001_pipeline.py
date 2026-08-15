"""T001 acceptance tests — the pipeline contract.

Sixteen later tasks are written against ``run_dimension``. These tests are the
oracle for that contract, not merely coverage for this task's code.
"""

from __future__ import annotations

import dataclasses
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from easy_verifier.core import redact as redact_module
from easy_verifier.core.context import MAX_LINE_CHARS, RepoContext, whole_file_excerpt
from easy_verifier.core.models import DimensionDescriptor, EvidencePack, Excerpt, SourceMiss
from easy_verifier.core.pipeline import RepoPathError, run_dimension
from easy_verifier.dimensions import DIMENSIONS
from easy_verifier.dimensions import architecture

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPO_ROOT / "src" / "easy_verifier"


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------


def make_descriptor(collect, *, sources_sought=("a.md",), name="test-dim") -> DimensionDescriptor:
    return DimensionDescriptor(
        name=name, purpose="test", sources_sought=tuple(sources_sought), collect=collect
    )


def fixed_size_excerpt(index: int, size: int = 10) -> Excerpt:
    """An excerpt whose text is exactly ``size`` bytes, so byte caps are exact."""
    text = str(index) * size
    assert len(text.encode("utf-8")) == size
    return Excerpt(path=f"f{index}.md", start_line=1, end_line=1, text=text)


class InstrumentedCollect:
    """A ``collect`` that records exactly how far the pipeline advanced it.

    This is the point of Test Plan item 2: an output-only assertion passes just
    as happily against a fully-materialising implementation, which is the
    precise regression Critical Constraint 3 exists to prevent.
    """

    def __init__(self, count: int, raise_at: int | None = None, size: int = 10) -> None:
        self.count = count
        self.raise_at = raise_at  # 1-indexed item number that explodes
        self.size = size
        self.advanced = 0

    def __call__(self, context) -> object:
        for i in range(1, self.count + 1):
            if self.raise_at is not None and i == self.raise_at:
                raise AssertionError(
                    f"pipeline advanced collect to item {i}; it should have stopped earlier"
                )
            self.advanced = i
            yield fixed_size_excerpt(i, self.size)


# --------------------------------------------------------------------------
# 1. Pack shape (AC #2, #3, #7)
# --------------------------------------------------------------------------

REQUIRED_PACK_FIELDS = {
    "dimension",
    "mode",
    "scope",
    "files_read",
    "excerpts",
    "sources_sought",
    "sources_found",
    "sources_missing",
    "coverage_score",
    "truncated",
    "omitted_count",
}

FORBIDDEN_FIELD_SUBSTRINGS = (
    "verdict",
    "rating",
    "grade",
    "severity",
    "score_label",
    "pass",
    "fail",
    "judgment",
    "judgement",
    "recommendation",
    "risk",
)


def test_pack_has_every_required_field(tmp_path):
    pack = run_dimension(make_descriptor(lambda ctx: iter(())), tmp_path)
    assert isinstance(pack, EvidencePack)
    assert REQUIRED_PACK_FIELDS <= {f.name for f in dataclasses.fields(pack)}


def test_pack_field_types(tmp_path):
    (tmp_path / "a.md").write_text("hello\n", encoding="utf-8")
    pack = run_dimension(make_descriptor(_read_a_md), tmp_path)

    assert isinstance(pack.dimension, str)
    assert isinstance(pack.mode, str)
    assert isinstance(pack.scope, str)
    assert isinstance(pack.files_read, tuple)
    assert isinstance(pack.excerpts, tuple)
    assert isinstance(pack.sources_sought, tuple)
    assert isinstance(pack.sources_found, tuple)
    assert isinstance(pack.sources_missing, tuple)
    assert isinstance(pack.coverage_score, float)
    assert isinstance(pack.truncated, bool)
    assert isinstance(pack.omitted_count, int)


def test_pack_carries_no_verdict_shaped_field():
    """AC #7 — the engine produces evidence, never a judgment (FR-013)."""
    names = {f.name.lower() for f in dataclasses.fields(EvidencePack)}
    names |= {f.name.lower() for f in dataclasses.fields(Excerpt)}
    offenders = {
        name
        for name in names
        for bad in FORBIDDEN_FIELD_SUBSTRINGS
        if bad in name
    }
    assert offenders == set()


def test_every_excerpt_has_path_and_line_range(tmp_path):
    (tmp_path / "a.md").write_text("one\ntwo\nthree\n", encoding="utf-8")
    pack = run_dimension(make_descriptor(_read_a_md), tmp_path)

    assert pack.excerpts
    for excerpt in pack.excerpts:
        assert excerpt.path
        assert excerpt.start_line >= 1
        assert excerpt.end_line >= excerpt.start_line
        assert isinstance(excerpt.text, str)


def _read_a_md(context):
    text = context.read_source("a.md")
    if text is None:
        return
    excerpt = whole_file_excerpt("a.md", text)
    if excerpt is not None:
        yield excerpt


# --------------------------------------------------------------------------
# 2. Laziness + truncation (AC #5, #5a — the load-bearing test)
# --------------------------------------------------------------------------


def test_collect_is_consumed_lazily_and_stops_one_item_past_the_cap(tmp_path):
    """N=3 admitted, item 4 pulled and rejected, item 5 never reached."""
    collect = InstrumentedCollect(count=10, raise_at=5, size=10)
    pack = run_dimension(make_descriptor(collect), tmp_path, budget_bytes=30)

    assert len(pack.excerpts) == 3
    assert pack.truncated is True
    assert pack.omitted_count == 1  # a lower bound, not a total
    assert collect.advanced == 4  # pulled exactly one past the admitted set


def test_pipeline_never_drains_the_remainder_to_count(tmp_path):
    """Success Criterion 3 — 10 excerpts, cap admits 3."""
    collect = InstrumentedCollect(count=10, size=10)
    pack = run_dimension(make_descriptor(collect), tmp_path, budget_bytes=30)

    assert pack.truncated is True
    assert pack.omitted_count == 1
    assert collect.advanced == 4
    assert collect.advanced < collect.count


def test_collect_result_is_an_iterator_not_a_list():
    """Critical Constraint 3 — a list forces full materialisation."""
    result = architecture.DESCRIPTOR.collect(
        RepoContext(repo_path=REPO_ROOT, mode="kit-aware", scope="project")
    )
    assert not isinstance(result, (list, tuple))
    assert iter(result) is result


def test_stream_ending_exactly_at_the_budget_boundary_is_not_truncated(tmp_path):
    """Nothing was pulled and rejected, so `truncated` must be False."""
    collect = InstrumentedCollect(count=3, size=10)
    pack = run_dimension(make_descriptor(collect), tmp_path, budget_bytes=30)

    assert pack.truncated is False
    assert pack.omitted_count == 0
    assert len(pack.excerpts) == 3


def test_budget_smaller_than_first_excerpt(tmp_path):
    collect = InstrumentedCollect(count=10, raise_at=2, size=10)
    pack = run_dimension(make_descriptor(collect), tmp_path, budget_bytes=1)

    assert pack.excerpts == ()
    assert pack.truncated is True
    assert pack.omitted_count == 1
    assert collect.advanced == 1


def test_empty_collect_is_not_truncated(tmp_path):
    pack = run_dimension(make_descriptor(lambda ctx: iter(())), tmp_path)
    assert pack.excerpts == ()
    assert pack.truncated is False
    assert pack.omitted_count == 0


# --------------------------------------------------------------------------
# 3. Coverage arithmetic (AC #6)
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("present", "sought", "expected"),
    [
        (("a.md", "b.md"), ("a.md", "b.md"), 1.0),
        (("a.md",), ("a.md", "b.md"), 0.5),
        ((), ("a.md", "b.md"), 0.0),
        ((), ("a.md", "b.md", "c.md", "d.md"), 0.0),
        (("a.md",), ("a.md", "b.md", "c.md", "d.md"), 0.25),
    ],
)
def test_coverage_is_unweighted_found_over_sought(tmp_path, present, sought, expected):
    for name in present:
        (tmp_path / name).write_text("content\n", encoding="utf-8")

    def collect(context):
        for source in sought:
            text = context.read_source(source)
            if text is None:
                continue
            excerpt = whole_file_excerpt(source, text)
            if excerpt is not None:
                yield excerpt

    pack = run_dimension(make_descriptor(collect, sources_sought=sought), tmp_path)

    assert pack.coverage_score == pytest.approx(expected)
    assert pack.coverage_score == pytest.approx(len(pack.sources_found) / len(sought))
    # FR-016a — the score never travels without the named miss list.
    assert {miss.source for miss in pack.sources_missing} == set(sought) - set(present)
    assert all(miss.reason for miss in pack.sources_missing)


def test_empty_sources_sought_yields_none_not_zero(tmp_path):
    """0.0 would falsely read as total failure; the answer is 'not applicable'."""
    pack = run_dimension(
        make_descriptor(lambda ctx: iter(()), sources_sought=()), tmp_path
    )
    assert pack.coverage_score is None


# --------------------------------------------------------------------------
# 4. No invention (AC #9, FR-005, NFR-002)
# --------------------------------------------------------------------------


def test_empty_repo_produces_empty_pack_and_no_invented_content(tmp_path):
    pack = run_dimension(architecture.DESCRIPTOR, tmp_path)

    assert pack.excerpts == ()
    assert pack.files_read == ()
    assert pack.coverage_score == 0.0
    assert {miss.source for miss in pack.sources_missing} == set(architecture.SOURCES_SOUGHT)
    assert pack.mode == "standalone"


def test_every_cited_path_exists_on_disk(tmp_path):
    (tmp_path / "README.md").write_text("# hi\n", encoding="utf-8")
    pack = run_dimension(architecture.DESCRIPTOR, tmp_path)

    assert pack.excerpts
    for excerpt in pack.excerpts:
        assert (tmp_path / excerpt.path).is_file()
    for name in pack.files_read:
        assert (tmp_path / name).is_file()


def test_missing_source_is_never_substituted(tmp_path):
    pack = run_dimension(architecture.DESCRIPTOR, tmp_path)
    missing = {miss.source for miss in pack.sources_missing}
    cited = {excerpt.path for excerpt in pack.excerpts}
    assert missing & cited == set()


# --------------------------------------------------------------------------
# 5. Redaction seam (AC #8, NFR-010)
# --------------------------------------------------------------------------


def test_seam_sees_every_excerpt_text(tmp_path, monkeypatch):
    seen: list[str] = []

    def spy(text: str) -> str:
        seen.append(text)
        return text

    monkeypatch.setattr(redact_module, "redact", spy)

    (tmp_path / "a.md").write_text("token = FAKE_SECRET_abcdef123456\n", encoding="utf-8")
    pack = run_dimension(make_descriptor(_read_a_md), tmp_path)

    assert seen  # the seam ran
    assert [excerpt.text for excerpt in pack.excerpts] == seen


def test_seam_output_is_what_lands_in_the_pack(tmp_path, monkeypatch):
    """A dimension cannot get text into a pack around the seam."""
    monkeypatch.setattr(redact_module, "redact", lambda text: "REDACTED")

    (tmp_path / "a.md").write_text("a live looking secret\n", encoding="utf-8")
    pack = run_dimension(make_descriptor(_read_a_md), tmp_path)

    assert pack.excerpts
    assert all(excerpt.text == "REDACTED" for excerpt in pack.excerpts)


def test_seam_runs_on_the_rejected_excerpt_too(tmp_path, monkeypatch):
    seen: list[str] = []
    monkeypatch.setattr(redact_module, "redact", lambda text: seen.append(text) or text)

    collect = InstrumentedCollect(count=10, raise_at=5, size=10)
    run_dimension(make_descriptor(collect), tmp_path, budget_bytes=30)

    assert len(seen) == 4  # three kept plus the one pulled and rejected


def test_redact_seam_is_a_documented_passthrough():
    assert redact_module.redact("anything") == "anything"
    assert "SEAM ONLY" in (redact_module.redact.__doc__ or "")


# --------------------------------------------------------------------------
# 6. No LLM anywhere (AC #11, NFR-001)
# --------------------------------------------------------------------------

FORBIDDEN_IMPORT_MARKERS = (
    "import openai",
    "from openai",
    "import anthropic",
    "from anthropic",
    "google.generativeai",
    "import litellm",
    "import cohere",
    "from mistralai",
)

FORBIDDEN_KEY_MARKERS = ("API_KEY", "api_key", "OPENAI", "ANTHROPIC")


def test_package_contains_no_llm_client_or_api_key_read():
    offenders: list[str] = []
    for path in PACKAGE_ROOT.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        for marker in FORBIDDEN_IMPORT_MARKERS + FORBIDDEN_KEY_MARKERS:
            if marker in source:
                offenders.append(f"{path.relative_to(PACKAGE_ROOT)}: {marker}")
    assert offenders == []


def test_package_never_reads_the_environment():
    """No model key can be read from an env var if nothing reads env vars."""
    offenders = [
        str(path.relative_to(PACKAGE_ROOT))
        for path in PACKAGE_ROOT.rglob("*.py")
        if "os.environ" in path.read_text(encoding="utf-8")
        or "getenv" in path.read_text(encoding="utf-8")
    ]
    assert offenders == []


# --------------------------------------------------------------------------
# 7. Adapter thinness (AC #10, FR-021)
# --------------------------------------------------------------------------


def test_cli_does_no_file_reading_or_excerpt_building():
    source = (PACKAGE_ROOT / "adapters" / "cli.py").read_text(encoding="utf-8")
    for marker in ("open(", "read_text", "read_bytes", "rglob", "Excerpt(", "EvidencePack("):
        assert marker not in source, f"cli.py must not contain {marker!r}"


def test_cli_does_no_coverage_arithmetic():
    source = (PACKAGE_ROOT / "adapters" / "cli.py").read_text(encoding="utf-8")
    for marker in ("coverage_score =", "len(sources", "/ len("):
        assert marker not in source


def test_cli_runs_against_this_repo_and_emits_json():
    result = subprocess.run(
        [sys.executable, "-m", "easy_verifier.adapters.cli", "architecture", "--repo", str(REPO_ROOT)],
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    assert payload["dimension"] == "architecture"
    assert payload["mode"] == "kit-aware"
    assert "PROJECT_SPEC.md" in payload["files_read"]


def test_cli_reports_a_bad_repo_path_without_a_traceback(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "easy_verifier.adapters.cli",
            "architecture",
            "--repo",
            str(tmp_path / "does-not-exist"),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert "Traceback" not in result.stderr
    assert "does not exist" in result.stderr


# --------------------------------------------------------------------------
# 8. Real repository (Success Criterion 1)
# --------------------------------------------------------------------------


def test_architecture_pack_against_this_repo():
    pack = run_dimension(architecture.DESCRIPTOR, REPO_ROOT)

    assert pack.dimension == "architecture"
    assert pack.mode == "kit-aware"
    assert pack.scope == "project"
    assert "PROJECT_SPEC.md" in pack.files_read
    assert 0.0 <= pack.coverage_score <= 1.0

    cited = [excerpt for excerpt in pack.excerpts if excerpt.path == "PROJECT_SPEC.md"]
    assert cited


def test_cited_line_numbers_are_1_indexed_and_match_the_file():
    """An off-by-one here poisons every citation downstream."""
    pack = run_dimension(architecture.DESCRIPTOR, REPO_ROOT)
    excerpt = next(e for e in pack.excerpts if e.path == "PROJECT_SPEC.md")

    on_disk = (REPO_ROOT / "PROJECT_SPEC.md").read_text(encoding="utf-8").splitlines()
    quoted = excerpt.text.splitlines()

    assert excerpt.start_line == 1
    assert excerpt.end_line == len(quoted)
    # Line L of the excerpt is line (start_line + L - 1) of the file.
    for offset, line in enumerate(quoted):
        assert line == on_disk[excerpt.start_line - 1 + offset]


def test_registry_is_a_plain_dict_of_descriptors():
    """Option D — explicit wiring, no decorator registry, no base class."""
    assert isinstance(DIMENSIONS, dict)
    assert set(DIMENSIONS) == {"architecture"}
    descriptor = DIMENSIONS["architecture"]
    assert type(descriptor) is DimensionDescriptor
    assert type(descriptor).__mro__ == (DimensionDescriptor, object)
    assert callable(descriptor.collect)


# --------------------------------------------------------------------------
# 9. Edge cases
# --------------------------------------------------------------------------


def test_nonexistent_repo_path_raises_a_clear_error(tmp_path):
    with pytest.raises(RepoPathError, match="does not exist"):
        run_dimension(architecture.DESCRIPTOR, tmp_path / "nope")


def test_repo_path_that_is_a_file_raises_a_clear_error(tmp_path):
    target = tmp_path / "a-file"
    target.write_text("x", encoding="utf-8")
    with pytest.raises(RepoPathError, match="not a directory"):
        run_dimension(architecture.DESCRIPTOR, target)


def test_non_git_directory_still_works_for_project_scope(tmp_path):
    (tmp_path / "README.md").write_text("# plain dir\n", encoding="utf-8")
    assert not (tmp_path / ".git").exists()

    pack = run_dimension(architecture.DESCRIPTOR, tmp_path)
    assert "README.md" in pack.files_read


def test_empty_file_counts_as_found_but_yields_no_excerpt(tmp_path):
    (tmp_path / "README.md").write_text("", encoding="utf-8")
    pack = run_dimension(architecture.DESCRIPTOR, tmp_path)

    assert "README.md" in pack.sources_found
    assert "README.md" in pack.files_read
    assert pack.excerpts == ()


@pytest.mark.skipif(os.geteuid() == 0, reason="root bypasses file permissions")
def test_unreadable_file_is_missing_with_a_reason_and_does_not_crash(tmp_path):
    target = tmp_path / "README.md"
    target.write_text("secret-ish\n", encoding="utf-8")
    target.chmod(0o000)
    try:
        pack = run_dimension(architecture.DESCRIPTOR, tmp_path)
    finally:
        target.chmod(0o644)

    miss = next(m for m in pack.sources_missing if m.source == "README.md")
    assert "unreadable" in miss.reason
    assert "README.md" not in pack.files_read


def test_binary_file_is_skipped_not_decoded_with_replacement_characters(tmp_path):
    (tmp_path / "README.md").write_bytes(b"\xff\xfe\x00binary\x00")
    pack = run_dimension(architecture.DESCRIPTOR, tmp_path)

    miss = next(m for m in pack.sources_missing if m.source == "README.md")
    assert "UTF-8" in miss.reason
    assert pack.excerpts == ()
    assert "�" not in json.dumps(dataclasses.asdict(pack))


def test_symlink_pointing_outside_the_repo_is_not_followed(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    secret = outside / "secret.md"
    secret.write_text("do not read me\n", encoding="utf-8")

    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "README.md").symlink_to(secret)

    pack = run_dimension(architecture.DESCRIPTOR, repo)

    miss = next(m for m in pack.sources_missing if m.source == "README.md")
    assert "outside the repository" in miss.reason
    assert "do not read me" not in json.dumps(dataclasses.asdict(pack))


def test_extremely_long_line_is_bounded(tmp_path):
    (tmp_path / "README.md").write_text("x" * 200_000 + "\n", encoding="utf-8")
    pack = run_dimension(architecture.DESCRIPTOR, tmp_path)

    excerpt = next(e for e in pack.excerpts if e.path == "README.md")
    assert len(excerpt.text) < MAX_LINE_CHARS + 100


def test_source_miss_carries_both_source_and_reason():
    miss = SourceMiss(source="a.md", reason="not found in the target repository")
    assert miss.source == "a.md"
    assert miss.reason


def test_pack_serializes_to_json(tmp_path):
    (tmp_path / "README.md").write_text("# hi\n", encoding="utf-8")
    pack = run_dimension(architecture.DESCRIPTOR, tmp_path)

    payload = json.loads(json.dumps(dataclasses.asdict(pack)))
    assert REQUIRED_PACK_FIELDS <= set(payload)
    # The miss list still reads as a named list to a human consumer (T013).
    assert all("source" in miss and "reason" in miss for miss in payload["sources_missing"])


def test_excerpt_paths_are_repo_relative_never_absolute(tmp_path):
    """Absolute paths would leak container-internal locations (FR-021c)."""
    (tmp_path / "README.md").write_text("# hi\n", encoding="utf-8")
    pack = run_dimension(architecture.DESCRIPTOR, tmp_path)

    for excerpt in pack.excerpts:
        assert not Path(excerpt.path).is_absolute()
        assert str(tmp_path) not in excerpt.path
