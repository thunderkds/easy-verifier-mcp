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
from easy_verifier.dimensions import architecture, requirement_fidelity

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
