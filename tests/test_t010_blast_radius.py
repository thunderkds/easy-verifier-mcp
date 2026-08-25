"""T010 acceptance tests for the bespoke ``blast-radius`` dimension.

*Code-dependency* blast radius — what else a change could reach. Not the kit's
``blast-radius`` skill, which analyses data-breach impact.
"""

from __future__ import annotations

import inspect
import subprocess
import sys
from pathlib import Path

from easy_verifier.core.budget import budget
from easy_verifier.core.context import detect_context
from easy_verifier.core.models import EvidencePack
from easy_verifier.core.pipeline import run_dimension
from easy_verifier.dimensions import DIMENSIONS, blast_radius

REPO_ROOT = Path(__file__).resolve().parent.parent


def _reasons(pack: EvidencePack) -> dict[str, str]:
    return {miss.source: miss.reason for miss in pack.sources_missing}


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


def _init_repo(repo: Path) -> None:
    _git(repo, "init", "-q", "-b", "main")


# ---------------------------------------------------------------------------
# Success Criterion 1 / AC #2 — referencing files, with the citing line
# ---------------------------------------------------------------------------


def test_referencing_files_are_surfaced_with_the_citing_line(tmp_path: Path) -> None:
    (tmp_path / "b.py").write_text("import a\n\nprint(a.VALUE)\n")
    (tmp_path / "c.py").write_text("# unrelated\nfrom a import VALUE\n")
    _init_repo(tmp_path)
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "referrers")
    # `a.py` alone is the change set, so `b.py`/`c.py` are outside it.
    (tmp_path / "a.py").write_text("VALUE = 1\n")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "add a")

    pack = run_dimension(blast_radius.DESCRIPTOR, tmp_path, scope="changes", ref="HEAD")

    cited = [(item.path, item.start_line, item.text) for item in pack.excerpts]
    assert ("b.py", 1, "import a") in cited
    assert ("b.py", 3, "print(a.VALUE)") in cited
    assert ("c.py", 2, "from a import VALUE") in cited
    # AC #2 — a file never cites itself as its own referrer, and the unrelated
    # comment line in `c.py` is not evidence of anything.
    assert not [item for item in cited if item[0] == "a.py"]
    assert ("c.py", 1, "# unrelated") not in cited
    assert blast_radius.REFERENCES_SOURCE in pack.sources_found


# ---------------------------------------------------------------------------
# AC #3 — git co-change evidence, from local git only
# ---------------------------------------------------------------------------


def test_co_change_history_names_files_committed_alongside_the_scope_file(
    tmp_path: Path,
) -> None:
    (tmp_path / "a.py").write_text("VALUE = 1\n")
    (tmp_path / "partner.py").write_text("X = 1\n")
    _init_repo(tmp_path)
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "a and partner")

    (tmp_path / "stranger.py").write_text("Y = 1\n")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "stranger only")

    (tmp_path / "a.py").write_text("VALUE = 2\n")
    (tmp_path / "partner.py").write_text("X = 2\n")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "a and partner again")

    (tmp_path / "a.py").write_text("VALUE = 3\n")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "a alone")

    pack = run_dimension(blast_radius.DESCRIPTOR, tmp_path, scope="changes", ref="HEAD")

    assert blast_radius.CO_CHANGE_SOURCE in pack.sources_found
    note = next(
        w for w in pack.warnings if w.startswith("Files that changed alongside")
    )
    assert "partner.py (2)" in note
    assert "stranger.py" not in note


def test_a_repo_with_no_git_history_states_the_absence_and_still_finds_references(
    tmp_path: Path,
) -> None:
    (tmp_path / "a.py").write_text("VALUE = 1\n")
    (tmp_path / "b.py").write_text("import a\n")

    # A file set with no git behind it: the reference search must still work.
    context = detect_context(tmp_path, scope="changes")
    context.resolved_scope = _ScopeStub(files=("a.py",), changed_files=("a.py",))
    excerpts = list(blast_radius.collect(context))

    assert [item.path for item in excerpts] == ["b.py"]
    reasons = {miss.source: miss.reason for miss in context.sources_missing}
    assert "not a git repository" in reasons[blast_radius.CO_CHANGE_SOURCE]


class _ScopeStub:
    kind = "changes"

    def __init__(self, files: tuple[str, ...], changed_files: tuple[str, ...]) -> None:
        self.files = files
        self.changed_files = changed_files
        self.task_ref = None
        self.diff = None
        self.notes = ()


# ---------------------------------------------------------------------------
# AC #4 — downstream entry points, and what was looked for and not found
# ---------------------------------------------------------------------------


def test_entry_point_declarations_are_cited_and_absent_manifests_are_listed(
    tmp_path: Path,
) -> None:
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname = 'demo'\n\n[project.scripts]\ndemo = 'demo.cli:main'\n"
    )
    _init_repo(tmp_path)
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "manifest")
    (tmp_path / "a.py").write_text("VALUE = 1\n")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "add a")

    pack = run_dimension(blast_radius.DESCRIPTOR, tmp_path, scope="changes", ref="HEAD")

    entry = next(item for item in pack.excerpts if item.path == "pyproject.toml")
    assert "[project.scripts]" in entry.text
    assert "pyproject.toml" in pack.sources_found
    reasons = _reasons(pack)
    assert "not found" in reasons["package.json"]
    assert any(w.startswith("Entry points were looked for") for w in pack.warnings)


# ---------------------------------------------------------------------------
# Success Criterion 3 / AC #3 — zero is stated, never implied by silence
# ---------------------------------------------------------------------------


def test_a_file_nothing_references_yields_an_explicit_zero(tmp_path: Path) -> None:
    (tmp_path / "b.py").write_text("X = 1\n")
    _init_repo(tmp_path)
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "unrelated")
    (tmp_path / "lonely_module.py").write_text("VALUE = 1\n")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "add lonely")

    pack = run_dimension(blast_radius.DESCRIPTOR, tmp_path, scope="changes", ref="HEAD")

    assert blast_radius.REFERENCES_SOURCE not in pack.sources_found
    reason = _reasons(pack)[blast_radius.REFERENCES_SOURCE]
    assert reason.startswith("examined:")
    assert "no referencing" in reason
    # "checked and found nothing" must not read as "not checked".
    assert "not examined" not in reason


# ---------------------------------------------------------------------------
# AC #5 — the method is stated in the pack, not merely in a docstring
# ---------------------------------------------------------------------------


def test_the_pack_states_that_reference_discovery_is_textual(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("VALUE = 1\n")
    _init_repo(tmp_path)
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "one")

    pack = run_dimension(blast_radius.DESCRIPTOR, tmp_path, scope="changes", ref="HEAD")

    method = next(w for w in pack.warnings if "textual" in w)
    assert "not a resolved import graph" in method
    assert "over-reporting" in method


# ---------------------------------------------------------------------------
# AC #6 — evidence only, no verdict
# ---------------------------------------------------------------------------


def test_no_risk_score_severity_or_verdict_anywhere_in_the_module() -> None:
    source = inspect.getsource(blast_radius)
    lowered = source.lower()
    for banned in ("risk_score", "severity", "danger", "verdict", "is_risky"):
        assert banned not in lowered
    assert not [name for name in vars(blast_radius) if name.lower().startswith("risk")]


# ---------------------------------------------------------------------------
# AC #7 — project scope is a meaningful pack, not an error
# ---------------------------------------------------------------------------


def test_project_scope_reports_repo_wide_hotspots(tmp_path: Path) -> None:
    (tmp_path / "hot.py").write_text("V = 0\n")
    (tmp_path / "cold.py").write_text("V = 0\n")
    _init_repo(tmp_path)
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "one")
    for index in range(3):
        (tmp_path / "hot.py").write_text(f"V = {index + 1}\n")
        _git(tmp_path, "add", "-A")
        _git(tmp_path, "commit", "-qm", f"hot {index}")

    pack = run_dimension(blast_radius.DESCRIPTOR, tmp_path, scope="project")

    assert blast_radius.HOTSPOT_SOURCE in pack.sources_found
    note = next(w for w in pack.warnings if w.startswith("Repository change hotspots"))
    assert "hot.py" in note
    reasons = _reasons(pack)
    # Project scope must not attempt every-file-against-every-file, and must
    # say so rather than leaving the reference source looking unchecked.
    assert "project scope" in reasons[blast_radius.REFERENCES_SOURCE]


# ---------------------------------------------------------------------------
# Success Criterion 4 / AC #8 — lazily consumed, and provably not drained
# ---------------------------------------------------------------------------


class _InstrumentedCollect:
    """Counts what the budget pulls, per pass, and whether a pass ran out.

    ``budget`` may invoke ``collect`` once per relevance tier, so laziness is a
    per-pass property: ``drained`` records, for each pass, whether the stream
    reached its end or was abandoned.
    """

    def __init__(self, context) -> None:
        self._context = context
        self.pulled = 0
        self.drained: list[bool] = []

    def __call__(self):
        self.drained.append(False)
        index = len(self.drained) - 1
        for excerpt in blast_radius.collect(self._context):
            self.pulled += 1
            yield excerpt
        self.drained[index] = True


def _large_repo(root: Path) -> None:
    (root / "target_module.py").write_text("VALUE = 1\n")
    for index in range(5_000):
        (root / f"m{index:05d}.py").write_text(
            "import target_module\n\nprint(target_module.VALUE)\n"
        )


def test_a_small_budget_abandons_the_generator_on_a_five_thousand_file_repo(
    tmp_path: Path,
) -> None:
    """Success Criterion 4 — the budget stops the work, and it is *asserted*
    that the generator was abandoned rather than inferred from elapsed time."""
    _large_repo(tmp_path)
    context = detect_context(tmp_path, scope="changes")
    context.resolved_scope = _ScopeStub(
        files=("target_module.py",), changed_files=("target_module.py",)
    )
    collect = _InstrumentedCollect(context)

    # A single relevance pass, which is what a caller with no resolved scope
    # gets: the budget is then the only thing that can stop the sweep.
    result = budget(collect, scope=None, limit_bytes=120)

    assert result.truncation.truncated is True
    assert result.excerpts
    assert collect.drained == [False]
    assert collect.pulled < 20
    assert len(context.files_read) < 20


def test_the_last_relevance_pass_is_abandoned_and_reads_stay_bounded(
    tmp_path: Path,
) -> None:
    """The same repo under a resolved ``changes`` scope.

    ``budget`` runs a tier-1 pass before the tier-3 one, and a tier-1 pass that
    never meets a misfit drains its stream by construction (``core/budget.py``
    documents this) — so what this dimension owns is that the drain is bounded
    (``MAX_SCAN_FILES``, never the repository's 5,000 files) and that the pass
    which does meet the budget is abandoned.
    """
    _large_repo(tmp_path)
    context = detect_context(tmp_path, scope="changes")
    context.resolved_scope = _ScopeStub(
        files=("target_module.py",), changed_files=("target_module.py",)
    )
    collect = _InstrumentedCollect(context)

    result = budget(collect, scope=context.resolved_scope, limit_bytes=120)

    assert result.truncation.truncated is True
    assert collect.drained[-1] is False
    assert len(set(context.files_read)) <= blast_radius.MAX_SCAN_FILES
    assert len(set(context.files_read)) < 500


def test_collect_returns_a_generator_rather_than_a_materialised_list() -> None:
    assert inspect.isgeneratorfunction(blast_radius.collect)


# ---------------------------------------------------------------------------
# Success Criterion 2 — this repo, changes scope over the last commit
# ---------------------------------------------------------------------------


def test_this_repo_changes_scope_produces_bounded_reachability_evidence() -> None:
    pack = run_dimension(
        blast_radius.DESCRIPTOR, REPO_ROOT, scope="changes", ref="HEAD~1..HEAD"
    )

    assert pack.dimension == "blast-radius"
    assert pack.coverage_score is not None
    assert any("textual" in warning for warning in pack.warnings)
    # AC #3/#4 cross-check: nothing may be reported missing that the same pack
    # also claims to have read or cited.
    missing = {miss.source for miss in pack.sources_missing}
    cited = {excerpt.path for excerpt in pack.excerpts}
    assert not missing & set(pack.files_read)
    assert not missing & cited


# ---------------------------------------------------------------------------
# AC #9 — standalone mode keeps the limited-context warning
# ---------------------------------------------------------------------------


def test_standalone_mode_carries_the_limited_context_warning(tmp_path: Path) -> None:
    (tmp_path / "b.py").write_text("import a\n")
    _init_repo(tmp_path)
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "referrer")
    (tmp_path / "a.py").write_text("VALUE = 1\n")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "add a")

    pack = run_dimension(blast_radius.DESCRIPTOR, tmp_path, scope="changes", ref="HEAD")

    assert pack.mode == "standalone"
    assert any("Limited context" in warning for warning in pack.warnings)
    assert [item.path for item in pack.excerpts] == ["b.py"]


# ---------------------------------------------------------------------------
# AC #10 — nothing from the target repo is executed; git stays read-only
# ---------------------------------------------------------------------------


def test_only_read_only_git_subcommands_are_ever_invoked(
    tmp_path: Path, monkeypatch
) -> None:
    """Asserted on the calls actually made, not on the module's text.

    Every git invocation goes through ``_run_git``; recording its argument
    lists during a real run is what shows no subcommand contacts a remote
    (NFR-012).
    """
    (tmp_path / "a.py").write_text("VALUE = 1\n")
    (tmp_path / "b.py").write_text("import a\n")
    _init_repo(tmp_path)
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "one")

    seen: list[str] = []
    real = blast_radius._run_git

    def recording(repo, args):
        seen.append(args[0])
        return real(repo, args)

    monkeypatch.setattr(blast_radius, "_run_git", recording)

    run_dimension(blast_radius.DESCRIPTOR, tmp_path, scope="changes", ref="HEAD")
    run_dimension(blast_radius.DESCRIPTOR, tmp_path, scope="project")

    assert seen
    assert set(seen) <= {"log", "rev-parse"}


def test_subprocess_is_reached_only_through_the_single_read_only_helper() -> None:
    source = inspect.getsource(blast_radius)
    assert source.count("subprocess.run(") == 1
    assert "shell=True," not in source
    assert "exec(" not in source
    assert "eval(" not in source
    assert "importlib" not in source


def test_an_executable_in_the_target_repo_is_never_run(tmp_path: Path) -> None:
    marker = tmp_path / "ran.txt"
    (tmp_path / "a.py").write_text(
        f"import pathlib\npathlib.Path({str(marker)!r}).write_text('ran')\n"
    )
    (tmp_path / "b.py").write_text("import a\n")
    _init_repo(tmp_path)
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "one")

    run_dimension(blast_radius.DESCRIPTOR, tmp_path, scope="changes", ref="HEAD")

    assert not marker.exists()


# ---------------------------------------------------------------------------
# AC #1 — bespoke descriptor, wired into the CLI
# ---------------------------------------------------------------------------


def test_descriptor_is_bespoke_and_registered() -> None:
    assert DIMENSIONS["blast-radius"] is blast_radius.DESCRIPTOR
    assert blast_radius.DESCRIPTOR.collect is blast_radius.collect
    source = inspect.getsource(blast_radius)
    assert "_doc_extract" not in source


def test_the_cli_exposes_the_dimension() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "easy_verifier.adapters.cli",
            "blast-radius",
            "--repo",
            str(REPO_ROOT),
            "--scope",
            "changes",
            "--ref",
            "HEAD~1..HEAD",
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
        env={"PYTHONPATH": str(REPO_ROOT / "src"), "PATH": "/usr/bin:/bin"},
    )

    assert result.returncode == 0, result.stderr
    assert '"dimension": "blast-radius"' in result.stdout


def test_a_cap_truncated_sweep_never_reports_a_repository_wide_zero(
    tmp_path: Path,
) -> None:
    """A referencing file beyond ``MAX_SCAN_FILES`` must not read as absence.

    Regression for the Stage 4 P1: with the only consumer sorting past the scan
    ceiling, the pack reported "examined: no referencing line was found in the
    400 repository file(s) scanned" and carried no warning about the ceiling —
    a bounded sweep asserting an unbounded result. Same relevance-blind-cap
    class as T008's alphabetical candidate cap.
    """
    (tmp_path / "aaa").mkdir()
    (tmp_path / "zzz").mkdir()
    (tmp_path / "aaa" / "target.py").write_text("def thing():\n    return 1\n")
    for index in range(blast_radius.MAX_SCAN_FILES + 100):
        (tmp_path / "aaa" / f"filler_{index:05d}.py").write_text(f"x = {index}\n")
    (tmp_path / "zzz" / "consumer.py").write_text(
        "from aaa.target import thing\n\nprint(thing())\n"
    )
    _init_repo(tmp_path)

    context = detect_context(tmp_path, scope="worktree")

    class _Scope:
        kind = "worktree"
        files = ("aaa/target.py",)
        changed_files = ()

    context.resolved_scope = _Scope()
    list(blast_radius.collect(context))

    reason = {miss.source: miss.reason for miss in context.sources_missing}[
        blast_radius.REFERENCES_SOURCE
    ]
    assert "ceiling" in reason
    assert str(blast_radius.MAX_SCAN_FILES) in reason
    assert any("ceiling" in warning for warning in context.warnings)
