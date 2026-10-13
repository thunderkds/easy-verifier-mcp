"""T096: a change list is not an architecture description; architecture prose
sections count (FR-076, DDR-0012)."""

from __future__ import annotations

from pathlib import Path

import pytest

from easy_verifier.core import documents
from easy_verifier.core.metric_tables import curated_metric_tables
from easy_verifier.core.metrics import compute_metrics
from easy_verifier.core.pipeline import run_dimension
from easy_verifier.dimensions import architecture

ARCH = "architecture_description_missing"

FILES = [
    "src/a.py",
    "src/b.py",
    "lib/c.py",
    "docs/d.md",
    "bin/e.sh",
    "apps/api/main.ts",
    "apps/web/main.ts",
    "packages/shared/index.ts",
]
KNOWN = documents.known_paths(FILES)
ROWS = (
    "| `src/a.py` | adds the new handler |\n"
    "| `src/b.py` | renames the old helper |\n"
    "| `lib/c.py` | drops the dead code |\n"
    "| `docs/d.md` | documents the change |\n"
    "| `bin/e.sh` | wires the launcher up |\n"
)


def _paths(text: str, base: str = "") -> list[str]:
    return [path for _n, path, _l in documents.described_entries(text, KNOWN, base)]


def _repo(tmp_path: Path, files: dict[str, str]) -> Path:
    for name, text in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return tmp_path


def _evidence(repo: Path):
    pack = run_dimension(architecture.DESCRIPTOR, repo, scope="project")
    metric = compute_metrics(pack, curated_metric_tables()).by_name(ARCH)[0]
    return metric, {item.role: item for item in pack.documents or ()}[
        "architecture-doc"
    ]


def _apps(tmp_path: Path) -> dict[str, str]:
    return {
        "apps/api/main.ts": "",
        "apps/web/main.ts": "",
        "packages/shared/index.ts": "",
    }


# --- AC 1, 2: change-list tables ----------------------------------------------


def test_ac1_change_column_makes_the_table_no_source():
    purpose = "| File | Purpose |\n|---|---|\n" + ROWS
    change = "| File | Change |\n|---|---|\n" + ROWS
    assert len(_paths(purpose)) == 5
    assert _paths(change) == []


@pytest.mark.parametrize(
    "title",
    ["Change", "Changes", "Action", "Edit", "Modification", "Status", "Todo", "Reason"],
)
def test_ac1_every_listed_title_skips_the_table(title):
    assert _paths(f"| File | {title} |\n|---|---|\n" + ROWS) == []


@pytest.mark.parametrize("header", ["| **Change** |", "| `CHANGE` |", "|  changes  |"])
def test_ac2_header_match_is_trimmed_and_case_insensitive(header):
    assert _paths(f"| File {header}\n|---|---|\n" + ROWS) == []


def test_ac2_the_header_is_the_row_above_the_separator():
    # "Change" in a body row, or two rows above the separator, is no header
    body = "| File | Purpose |\n|---|---|\n| Change | Change |\n" + ROWS
    assert len(_paths(body)) == 5
    two_above = "| File | Change |\n| File | Purpose |\n|---|---|\n" + ROWS
    assert len(_paths(two_above)) == 5


def test_a_table_without_a_separator_row_behaves_as_before():
    assert len(_paths("| File | Change |\n" + ROWS)) == 5


def test_only_the_change_list_table_is_skipped():
    text = (
        "| File | Change |\n|---|---|\n"
        + ROWS
        + "\nprose between the two tables\n\n"
        + "| File | Purpose |\n|---|---|\n"
        + "| `apps/api/main.ts` | serves the http api |\n"
    )
    assert _paths(text) == ["apps/api/main.ts"]


# --- AC 3, 4: architecture prose sections ------------------------------------

PROSE = (
    "The system has `/apps/api` for the server, `/apps/web` for the client and "
    "`/packages/shared` for common types.\n"
)


def test_ac3_prose_architecture_section_fills_the_role(tmp_path):
    repo = _repo(
        tmp_path,
        {
            "PROJECT_SPEC.md": "# Spec\n\n## Architecture Summary\n" + PROSE,
            **_apps(tmp_path),
        },
    )
    metric, item = _evidence(repo)
    assert metric.outcome == 0
    assert (item.kind, item.path) == ("architecture-heading", "PROJECT_SPEC.md")
    assert item.cited == (f"line 4: {PROSE.strip()}",)


def test_ac3_the_same_paragraph_under_another_heading_does_not(tmp_path):
    repo = _repo(
        tmp_path,
        {"PROJECT_SPEC.md": "# Spec\n\n## Notes\n" + PROSE, **_apps(tmp_path)},
    )
    metric, item = _evidence(repo)
    assert metric.outcome == 1
    assert item.kind is None


def test_ac3_bare_path_tokens_count_but_bare_words_do_not(tmp_path):
    bare = (
        "## Architecture\nServer in apps/api, client in apps/web and packages/shared.\n"
    )
    words = (
        "## Architecture\nThe apps and packages hold the api, web and shared code.\n"
    )
    repo = _repo(tmp_path / "a", {"NOTES.md": bare, **_apps(tmp_path)})
    assert _evidence(repo)[1].kind == "architecture-heading"
    repo = _repo(tmp_path / "b", {"NOTES.md": words, **_apps(tmp_path)})
    assert _evidence(repo)[1].kind is None


@pytest.mark.parametrize(
    "prose",
    [
        "Uses `/apps/api` and `/apps/web` only.",
        "Uses `/apps/api`, `/apps/web` and `/packages/missing`.",
        "Uses `/apps/api`, `/apps/api/` and `apps/api/**` three times.",
    ],
)
def test_ac4_below_threshold_or_unreal_paths_do_not_qualify(tmp_path, prose):
    repo = _repo(
        tmp_path,
        {"PROJECT_SPEC.md": f"## Architecture\n{prose}\n", **_apps(tmp_path)},
    )
    assert _evidence(repo)[1].kind is None


def test_urls_are_not_paths(tmp_path):
    prose = "See https://example.com/apps/api and http://x.io/apps/web and https://y.io/packages/shared."
    repo = _repo(
        tmp_path, {"NOTES.md": f"## Architecture\n{prose}\n", **_apps(tmp_path)}
    )
    assert _evidence(repo)[1].kind is None


def test_fenced_paths_in_the_section_count_once_each(tmp_path):
    text = "## Architecture\n```\napps/api\napps/api\napps/web\n```\n"
    repo = _repo(tmp_path, {"NOTES.md": text, **_apps(tmp_path)})
    assert _evidence(repo)[1].kind is None  # two distinct paths
    repo = _repo(
        tmp_path / "ok", {"NOTES.md": text + "and packages/shared\n", **_apps(tmp_path)}
    )
    assert _evidence(repo)[1].kind == "architecture-heading"


def test_heading_level_any_and_section_ends_at_the_next_same_level(tmp_path):
    text = "#### System architecture\nnothing here\n\n#### Other\n" + PROSE
    repo = _repo(tmp_path, {"NOTES.md": text, **_apps(tmp_path)})
    assert _evidence(repo)[1].kind is None


# --- AC 5: READMEs keep today's kind and lines ---------------------------------


def test_ac5_readme_keeps_its_kind_and_cited_lines(tmp_path):
    entries = (
        "- api: the http layer\n- core: business rules here\n- db: data access code\n"
    )
    repo = _repo(
        tmp_path,
        {
            "README.md": "# App\n\n## Architecture\n" + entries,
            **{f"{n}/x.py": "" for n in ("api", "core", "db")},
        },
    )
    item = _evidence(repo)[1]
    assert item.kind == "readme-heading"
    assert item.cited[0] == "line 4: - api: the http layer"


def test_ac5_readme_prose_section_uses_the_readme_kind(tmp_path):
    repo = _repo(
        tmp_path,
        {"README.md": "# App\n\n## Architecture\n" + PROSE, **_apps(tmp_path)},
    )
    assert _evidence(repo)[1].kind == "readme-heading"


# --- ranking: a plan loses to a prose description -------------------------------


def test_a_change_list_no_longer_beats_the_prose_description(tmp_path):
    plan = "| File | Change |\n|---|---|\n" + "".join(
        f"| `{p}` | edits this file now |\n"
        for p in ("src/a.py", "lib/c.py", "docs/d.md", "bin/e.sh")
    )
    repo = _repo(
        tmp_path,
        {
            "README.md": "# App\n",
            "tasks/PLAN.md": plan,
            "PROJECT_SPEC.md": "## Architecture\n" + PROSE,
            **{p: "" for p in FILES},
        },
    )
    assert _evidence(repo)[1].path == "PROJECT_SPEC.md"


# --- a title is not a section ---------------------------------------------------

READ_LIST = (
    "Read `apps/api/main.ts`, then `apps/web/main.ts`, then "
    "`packages/shared/index.ts`.\n"
)


def test_h1_title_naming_architecture_does_not_open_a_section(tmp_path):
    text = "# Task: the architecture dimension\n\n" + READ_LIST
    repo = _repo(tmp_path, {"TASK.md": text, **_apps(tmp_path)})
    assert _evidence(repo)[1].kind is None


def test_the_same_text_under_a_level_two_architecture_heading_fills(tmp_path):
    text = "# Task\n\n## Architecture\n" + READ_LIST
    repo = _repo(tmp_path, {"TASK.md": text, **_apps(tmp_path)})
    assert _evidence(repo)[1].kind == "architecture-heading"


def test_a_later_level_two_section_is_found_past_an_h1_title(tmp_path):
    text = "# Architecture notes\n\nintro\n\n## System architecture\n" + READ_LIST
    repo = _repo(tmp_path, {"TASK.md": text, **_apps(tmp_path)})
    item = _evidence(repo)[1]
    assert item.kind == "architecture-heading"
    assert item.cited[0].startswith("line 6:")
