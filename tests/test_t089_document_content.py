"""T089 (FR-076, DDR-0012 §3): document roles are filled by content or
declaration, never by a file name alone."""

from __future__ import annotations

from pathlib import Path

import pytest

from easy_verifier.core import documents
from easy_verifier.core.metric_tables import curated_metric_tables
from easy_verifier.core.metrics import MetricAbstention, compute_metrics
from easy_verifier.core.pipeline import run_dimension
from easy_verifier.core.roles import GENERIC_PATTERNS
from easy_verifier.dimensions import architecture, requirement_fidelity, solution_fit

ARCH = "architecture_description_missing"
DECISION = "decision_records_missing"
REQUIREMENTS = "requirements_doc_missing"

FOLDERS = (
    "# Ops\n\n## Folder structures\n"
    " - bin: helper scripts\n - elk: logs stack\n - vagrant: vm files\n"
)


def _repo(tmp_path: Path, files: dict[str, str]) -> Path:
    for name, text in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return tmp_path


def _dirs(*names: str) -> dict[str, str]:
    return {f"{name}/run.sh": "" for name in names}


def _metric(repo: Path, name: str, descriptor=architecture.DESCRIPTOR):
    pack = run_dimension(descriptor, repo, scope="project")
    metric = compute_metrics(pack, curated_metric_tables()).by_name(name)[0]
    evidence = {item.role: item for item in pack.documents or ()}
    return metric, evidence


# --- SC 1-3: architecture-doc content shape ----------------------------------


def test_sc1_folder_list_with_real_dirs_fills_architecture_doc(tmp_path):
    repo = _repo(tmp_path, {"README.md": FOLDERS, **_dirs("bin", "elk", "vagrant")})
    metric, evidence = _metric(repo, ARCH)

    assert metric.outcome == 0
    item = evidence["architecture-doc"]
    assert (item.kind, item.path) == ("content", "README.md")
    assert item.cited == (
        "line 4: - bin: helper scripts",
        "line 5: - elk: logs stack",
        "line 6: - vagrant: vm files",
    )
    assert "README.md (content: line 4: - bin: helper scripts" in metric.derivation


def test_sc2_only_two_real_entries_is_missing_with_a_measured_reason(tmp_path):
    repo = _repo(tmp_path, {"README.md": FOLDERS, **_dirs("bin", "vagrant")})
    metric, evidence = _metric(repo, ARCH)

    assert metric.outcome == 1
    assert evidence["architecture-doc"].kind is None
    assert "documents read; none describes at least 3 real repository paths" in (
        metric.derivation
    )


def test_sc3_a_conventional_name_without_structure_does_not_fill(tmp_path):
    repo = _repo(
        tmp_path,
        {
            "README.md": "# App\n",
            "docs/design-tokens.md": "# Design tokens\n\nColours and spacing.\n",
            **_dirs("bin", "elk", "vagrant"),
        },
    )
    metric, evidence = _metric(repo, ARCH)

    assert metric.outcome == 1
    # the name only raised scan priority: it was read first, then rejected
    assert evidence["architecture-doc"].scanned == 2


# --- SC 4: decision-record ----------------------------------------------------


def test_sc4_nygard_structure_fills_decision_record(tmp_path):
    repo = _repo(
        tmp_path,
        {
            "README.md": "# App\n",
            "docs/decisions/use-pg.md": (
                "# Use Postgres\n\n## Context\nWe need a store.\n\n"
                "## Decision\nPostgres.\n\n## Consequences\nOps cost.\n"
            ),
        },
    )
    metric, evidence = _metric(repo, DECISION)

    assert metric.outcome == 0
    item = evidence["decision-record"]
    assert (item.kind, item.path) == ("content", "docs/decisions/use-pg.md")
    assert item.cited[0] == "line 3: ## Context"


def test_a_dated_decision_with_rationale_fills_decision_record(tmp_path):
    repo = _repo(
        tmp_path,
        {
            "README.md": "# App\n",
            "NOTES.md": (
                "## 2026-01-02\nWe decided on Redis because the queue is small.\n"
            ),
        },
    )
    assert _metric(repo, DECISION)[0].outcome == 0


def test_one_field_or_an_undated_decision_does_not_fill(tmp_path):
    repo = _repo(
        tmp_path,
        {
            "README.md": (
                "## Status\nBeta.\n\nWe decided on Redis because it is small.\n"
            ),
            "docs/decisions/empty.md": "# Nothing decided here\n",
        },
    )
    assert _metric(repo, DECISION)[0].outcome == 1


# --- SC 5 / AC 5: declaration --------------------------------------------------


def test_sc5_toml_declaration_fills_without_content_check(tmp_path):
    repo = _repo(
        tmp_path,
        {
            ".easy-verifier.toml": '[roles]\narchitecture-doc = ["NOTES.md"]\n',
            "NOTES.md": "no structure at all\n",
        },
    )
    metric, evidence = _metric(repo, ARCH)

    assert metric.outcome == 0
    assert (evidence["architecture-doc"].kind, evidence["architecture-doc"].path) == (
        "declared",
        "NOTES.md",
    )
    assert "(declared: named by the project)" in metric.derivation


# --- SC 6: the threshold pinned at both extremes --------------------------------


@pytest.mark.parametrize(
    ("minimum", "expected"),
    [(3, (0, 1, 1)), (0, (0, 0, 0)), (999, (1, 1, 1))],
)
def test_sc6_threshold_flips_sc1_to_sc3(tmp_path, monkeypatch, minimum, expected):
    monkeypatch.setattr(documents, "MIN_DESCRIBED_ENTRIES", minimum)
    real = _dirs("bin", "elk", "vagrant")
    sc1 = _repo(tmp_path / "a", {"README.md": FOLDERS, **real})
    sc2 = _repo(tmp_path / "b", {"README.md": FOLDERS, **_dirs("bin", "vagrant")})
    sc3 = _repo(
        tmp_path / "c",
        {"README.md": "# App\n", "docs/design-tokens.md": "# Tokens\n"},
    )
    assert tuple(_metric(repo, ARCH)[0].outcome for repo in (sc1, sc2, sc3)) == expected


# --- AC 3: requirements-doc ---------------------------------------------------


def test_requirement_items_fill_requirements_doc_under_any_name(tmp_path):
    repo = _repo(
        tmp_path,
        {
            "README.md": "# App\n",
            "notes/plan.md": "| US-001 | As a chef, I want recipes |\n",
        },
    )
    metric, evidence = _metric(repo, REQUIREMENTS, requirement_fidelity.DESCRIPTOR)

    assert metric.outcome == 0
    assert evidence["requirements-doc"].path == "notes/plan.md"
    assert evidence["requirements-doc"].cited == (
        "line 1: | US-001 | As a chef, I want recipes |",
    )


def test_a_requirements_name_without_items_is_missing(tmp_path):
    repo = _repo(
        tmp_path,
        {"README.md": "# App\n", "PRD.md": "# Product\n\nIt should be nice.\n"},
    )
    metric, _ = _metric(repo, REQUIREMENTS, requirement_fidelity.DESCRIPTOR)
    assert metric.outcome == 1
    assert "none has a requirement item" in metric.derivation


# --- AC 4: kit names are no longer generic --------------------------------------


def test_kit_names_left_generic_patterns_and_never_fill_by_name(tmp_path):
    assert "PROJECT_SPEC.md" not in GENERIC_PATTERNS["architecture-doc"]
    assert "BRAINSTORMING_LOG*.md" not in GENERIC_PATTERNS["decision-record"]
    repo = _repo(
        tmp_path,
        {
            "README.md": "# App\n",
            "ARCHITECTURE.md": "# Architecture\n\nIt is layered.\n",
            "docs/adr/0001.md": "# A note\n",
        },
    )
    assert _metric(repo, ARCH)[0].outcome == 1
    assert _metric(repo, DECISION)[0].outcome == 1


# --- AC 6: a cut scan abstains --------------------------------------------------


def test_scan_cut_by_the_cap_abstains(tmp_path, monkeypatch):
    monkeypatch.setattr(documents, "MAX_SCANNED_DOCUMENTS", 1)
    repo = _repo(tmp_path, {"README.md": "# App\n", "z/README.md": FOLDERS})
    metric, _ = _metric(repo, ARCH)

    assert isinstance(metric.outcome, MetricAbstention)
    assert "only the first 1 of 2 candidate documents were read" in (
        metric.outcome.reason
    )


# --- AC 7: README heading kept only with the shape -------------------------------


def test_readme_architecture_heading_needs_the_shape(tmp_path):
    entries = (
        "- api: the http layer\n- core: business rules here\n- db: data access code\n"
    )
    filled = _repo(
        tmp_path / "a",
        {
            "README.md": "# App\n\n## Architecture\n" + entries,
            **_dirs("api", "core", "db"),
        },
    )
    metric, evidence = _metric(filled, ARCH)
    assert metric.outcome == 0
    assert evidence["architecture-doc"].kind == "readme-heading"
    assert evidence["architecture-doc"].cited[0] == "line 4: - api: the http layer"

    bare = _repo(tmp_path / "b", {"README.md": "# App\n\n## Architecture\nLayered.\n"})
    assert _metric(bare, ARCH)[0].outcome == 1


# --- AC 9: changelogs ---------------------------------------------------------


def test_changelog_has_the_shape_but_is_not_a_candidate(tmp_path):
    log = (
        "# Changes\n- src/a.ts: fix typo here\n- src/b.ts: new export added\n"
        "- src/c.ts: rename the thing\n"
    )
    files = {
        "CHANGELOG.md": log,
        "src/a.ts": "",
        "src/b.ts": "",
        "src/c.ts": "",
    }
    repo = _repo(tmp_path, files)
    known = documents.known_paths(files)
    assert len(documents.described_entries(log, known)) == 3
    assert _metric(repo, ARCH)[0].outcome == 1


# --- entry forms and edge cases ------------------------------------------------

KNOWN = documents.known_paths(
    [
        "src/easy_verifier/core/judge.py",
        "src/easy_verifier/adapters/cli.py",
        "travel/app/agents/a.py",
        "travel/eval/x.json",
        "bin/run.sh",
        "elk/x.yml",
        "docs/a.md",
        "config/.env",
        "test/x.spec.ts",
    ]
)


def _paths(text: str, base: str = "") -> list[str]:
    return [path for _n, path, _l in documents.described_entries(text, KNOWN, base)]


def test_table_row_tree_line_and_code_block_forms():
    table = (
        "| Module | Role |\n|---|---|\n"
        "| `src/easy_verifier/core/judge.py` | declared rules engine |\n"
    )
    tree = (
        "```\ntravel/\n├── app/\n│   ├── agents/   # agent identity loading\n"
        "├── eval/       # evaluation set and runner\n```\n"
    )
    block = "```\nsrc/easy_verifier/\n  adapters/cli.py     path mode, no server\n```\n"
    assert _paths(table) == ["src/easy_verifier/core/judge.py"]
    assert _paths(tree) == ["travel/app/agents", "travel/eval"]
    assert _paths(block) == ["src/easy_verifier/adapters/cli.py"]


def test_paths_normalize_before_lookup():
    text = (
        "- `./bin/`: helper scripts\n- /elk/**: logs stack\n"
        "- **docs/a.md**: the guide here\n"
    )
    assert _paths(text) == ["bin", "elk", "docs/a.md"]


def test_doc_directory_resolves_relative_entries():
    assert _paths("- `/agents`: identity loading code\n", base="travel/app") == [
        "travel/app/agents"
    ]


def test_non_entries_do_not_count():
    assert _paths("bin — helper scripts in prose, not a list\n") == []
    assert _paths("- test → vitest run\n") == []  # an npm script, not a separator
    assert _paths("- bin: helpers\n") == []  # one word of description
    assert _paths("- nowhere: helper scripts\n") == []  # not a real path
    assert _paths("- config/.env: secret values here\n") == []  # secret-bearing


def test_non_english_descriptions_count():
    assert _paths("- bin: các tập lệnh hỗ trợ\n- elk: 日志\n") == ["bin", "elk"]


def test_third_party_paths_never_count(tmp_path):
    repo = _repo(
        tmp_path,
        {
            "README.md": (
                "- node_modules: installed packages here\n"
                "- bin: helper scripts\n- elk: logs stack\n"
            ),
            "node_modules/x/index.js": "",
            **_dirs("bin", "elk"),
        },
    )
    assert _metric(repo, ARCH)[0].outcome == 1


# --- AC 10: the best document wins ---------------------------------------------


def _list(*names: str) -> str:
    return "".join(f"- {name}: describes this part well\n" for name in names)


@pytest.mark.parametrize(
    ("other", "winner"),
    [(("a", "b", "c", "d"), "docs/structure.md"), (("a", "b", "c"), "README.md")],
)
def test_ac10_most_entries_wins_and_a_tie_goes_to_scan_priority(
    tmp_path, other, winner
):
    repo = _repo(
        tmp_path,
        {
            "README.md": _list("a", "b", "c"),
            "docs/structure.md": _list(*other),
            **_dirs("a", "b", "c", "d"),
        },
    )
    assert _metric(repo, ARCH)[1]["architecture-doc"].path == winner


# --- AC 11: a decision record needs a decision ----------------------------------

DECISION_CASES = [
    # python-ml shape: a requirements doc with Status + Context, no decision
    ("**Status**: Architecture approved\n\n## Context\nTravel search.\n", 1),
    ("## Decision\nUse Postgres.\n", 1),  # a decision with no context
    ("## Context\nStore.\n\n## Consequences\nCost.\n", 1),
    ("**Decision**: Postgres\n**Status**: Accepted\n", 0),
    ("## Options\nA or B.\n\n## 🚀 Recommended Path\nOption B.\n", 0),
    ("## Context and Problem Statement\nX.\n\n## Decision Outcome\nY.\n", 0),
    # kit brainstorming log: singular "Alternative" / "Option" headings
    ("## Alternative Paths\n### Option A — inline\n## Recommended Path\nA.\n", 0),
    ("## Alternative Paths\n### Option A — inline\n", 1),  # no decision
]


@pytest.mark.parametrize(("text", "expected"), DECISION_CASES)
def test_ac11_decision_field_plus_one_more(tmp_path, text, expected):
    repo = _repo(tmp_path, {"README.md": "# App\n", "notes/doc.md": text})
    assert _metric(repo, DECISION)[0].outcome == expected


def test_ac11_brainstorming_log_reaches_solution_fit_by_content(tmp_path):
    log = "# Log\n\n## Options\nA, B.\n\n## Recommended Path\nB.\n"
    repo = _repo(tmp_path, {"README.md": "# App\n", "BRAINSTORMING_LOG.md": log})
    pack = run_dimension(solution_fit.DESCRIPTOR, repo, scope="project")
    filled = {item.role: item for item in pack.documents}["decision-record"]
    assert (filled.kind, filled.path) == ("content", "BRAINSTORMING_LOG.md")
    assert "BRAINSTORMING_LOG.md" in pack.files_read
    # read as role evidence, so solution-fit quotes its sections
    assert any(e.path == "BRAINSTORMING_LOG.md" for e in pack.excerpts)
    assert "decision-record" in pack.sources_found


# --- AC 12: requirements by heading and list ------------------------------------

REQUIREMENT_CASES = [
    # python-ml shape: plain bullets under a requirements heading
    ("## Functional Requirements\n- search flights\n- search hotels\n- book\n", 0),
    ("## User Stories\n1. a chef plans\n2. staff check off\n3. owner sees\n", 0),
    ("## Functional Requirements\n- search flights\n- search hotels\n", 1),
    ("## Functional Requirements\n- one\n- two\n## Other\n- three\n- four\n", 1),
    ("## Installation\n- one\n- two\n- three\n", 1),
    # decision A: install prerequisites are not requirements
    ("## Requirements\n- Node\n- Npm\n- Docker\n", 1),
    ("## System Requirements\n- Node\n- Npm\n- Docker\n", 1),
    ("## Product Requirements\n- one\n- two\n- three\n", 0),
]


@pytest.mark.parametrize(("text", "expected"), REQUIREMENT_CASES)
def test_ac12_requirements_heading_over_three_list_items(tmp_path, text, expected):
    repo = _repo(tmp_path, {"README.md": "# App\n", "notes/doc.md": text})
    metric, evidence = _metric(repo, REQUIREMENTS, requirement_fidelity.DESCRIPTOR)
    assert metric.outcome == expected
    if expected == 0:
        assert evidence["requirements-doc"].cited[0].startswith("line 1: ## ")


@pytest.mark.parametrize(("minimum", "expected"), [(0, 0), (3, 0), (4, 1)])
def test_ac12_list_threshold_pinned(tmp_path, monkeypatch, minimum, expected):
    monkeypatch.setattr(documents, "MIN_REQUIREMENT_LIST_ITEMS", minimum)
    text = "## User Stories\n- one\n- two\n- three\n"
    repo = _repo(tmp_path, {"README.md": "# App\n", "notes/doc.md": text})
    metric, _ = _metric(repo, REQUIREMENTS, requirement_fidelity.DESCRIPTOR)
    assert metric.outcome == expected


def test_decision_b_distinct_directories_outrank_a_file_list(tmp_path):
    files = "".join(f"- src/app/f{i}.ts: changes this file here\n" for i in range(6))
    dirs = _list("a", "b", "c")  # 3 directories beat 6 files in one directory
    repo = _repo(
        tmp_path,
        {
            "README.md": "# App\n",
            "docs/plan.md": files,
            "docs/structure.md": dirs,
            **{f"src/app/f{i}.ts": "" for i in range(6)},
            **_dirs("a", "b", "c"),
        },
    )
    assert _metric(repo, ARCH)[1]["architecture-doc"].path == "docs/structure.md"


@pytest.mark.parametrize("role", [ARCH, DECISION])
def test_decision_c_templates_never_fill(tmp_path, role):
    adr = "## Decision\nX.\n## Status\nAccepted.\n"
    repo = _repo(
        tmp_path,
        {
            "README.md": "# App\n",
            "templates/doc.md": _list("a", "b", "c") + adr,
            **_dirs("a", "b", "c"),
        },
    )
    assert _metric(repo, role)[0].outcome == 1
