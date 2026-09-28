"""T029 — ordinary file names survive redaction; secrets still fingerprint.

Found by T026: ``high_entropy_string`` rewrote ``BRAINSTORMING_LOG_source-discovery.md``
to ``BRAI…****:54e5675171d4.md``, so a citation to that file could not resolve.
Mixed-case words joined by ``_``/``-``/``/`` clear the 4.0-bit bar as one token.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from easy_verifier.core.findings import validate_findings
from easy_verifier.core.pipeline import run_dimension
from easy_verifier.core.redact import fingerprint, redact, scan
from easy_verifier.core.roles import GENERIC_PATTERNS
from easy_verifier.dimensions import DIMENSIONS

REPO_ROOT = Path(__file__).resolve().parents[1]

# Synthetic, no vendor prefix. Mixed case + digits: the key-material shape.
MIXED_TOKEN = "pB4kQ9zXmR7tY2wEaB3xK9mQ7rT2vY8w"
# Letters only, random case, joined by `_`/`-`: a base64url-style token that
# carries no digit, so only the long-token entropy rule can catch it. This is
# the case the filename exemption must NOT swallow.
LETTERS_URLSAFE_TOKEN = "xQzRtWvB_kLmNpQs-TyUiOpAsDfGhJkLz"


# --- AC 1 — the reported defect ---------------------------------------------


def test_the_reported_filename_survives_redaction() -> None:
    name = "BRAINSTORMING_LOG_source-discovery.md"
    assert redact(name) == name


@pytest.mark.parametrize(
    "path",
    [
        "BRAINSTORMING_LOG_evaluation-areas.md",
        "BRAINSTORMING_LOG_reference-registry.md",
        "templates/BRAINSTORMING_LOG_template.md",
        "templates/LEARNING-RECORD-FORMAT.md",
        "templates/PROJECT_KANBAN_template.md",
        "See BRAINSTORMING_LOG_source-discovery.md:12-30 for the options.",
    ],
)
def test_word_joined_filenames_survive_redaction(path: str) -> None:
    assert scan(path).hits == ()


# --- AC 2 — every tracked path of this repo ---------------------------------


def test_every_tracked_path_of_this_repo_survives_redaction() -> None:
    listed = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    assert len(listed) > 100, "expected the real repo's file list"
    changed = [path for path in listed if redact(path) != path]
    assert changed == []


# --- AC 3 — secrets still fingerprint ---------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        MIXED_TOKEN,
        f"docs/{MIXED_TOKEN}.md",
        f"build/app-{MIXED_TOKEN}.min.js",
        f"BRAINSTORMING_LOG_{MIXED_TOKEN}.md",
        f"{LETTERS_URLSAFE_TOKEN}.json",
        f"keys/{LETTERS_URLSAFE_TOKEN}.txt",
    ],
)
def test_random_tokens_still_fingerprint_inside_a_filename(text: str) -> None:
    result = scan(text)
    assert result.hits, text
    assert result.text != text


def test_letters_only_urlsafe_token_is_caught_by_the_long_token_rule() -> None:
    # Pins the word-shape guard itself: no digit, so key_material_segment is
    # blind to this token and high_entropy_string is its only cover.
    result = scan(f"{LETTERS_URLSAFE_TOKEN}.json")
    assert [hit.detector for hit in result.hits] == ["high_entropy_string"]
    assert fingerprint(LETTERS_URLSAFE_TOKEN) in result.text


def test_word_joined_identifier_without_a_file_suffix_is_unchanged_behaviour() -> None:
    # Decision (edge case "long snake_case identifiers in code"): the exemption
    # is anchored to a file suffix, so a bare identifier is judged exactly as
    # before — over-redaction is this module's chosen direction.
    identifier = "BRAINSTORMING_LOG_source-discovery"
    assert [hit.detector for hit in scan(identifier).hits] == ["high_entropy_string"]


# --- AC 4 — decision-record role widened, citation resolves -----------------


def test_decision_record_role_is_widened_back() -> None:
    assert "BRAINSTORMING_LOG*.md" in GENERIC_PATTERNS["decision-record"]
    assert "BRAINSTORMING_LOG.md" not in GENERIC_PATTERNS["decision-record"]


def test_a_citation_to_a_suffixed_brainstorming_log_resolves(tmp_path: Path) -> None:
    name = "BRAINSTORMING_LOG_source-discovery.md"
    (tmp_path / name).write_text(
        "# Source discovery\n\n## Recommended Path\n\nOption B chosen.\n",
        encoding="utf-8",
    )
    pack = run_dimension(DIMENSIONS["architecture"], tmp_path)

    assert "decision-record" in pack.sources_found
    cited = [excerpt for excerpt in pack.excerpts if excerpt.path == name]
    assert cited, [excerpt.path for excerpt in pack.excerpts]

    result = validate_findings(
        [
            {
                "dimension": "architecture",
                "title": "Decision recorded",
                "detail": "The source-discovery log records the chosen option.",
                "evidence_ref": cited[0].ref,
                "confidence": "high",
            }
        ],
        {"architecture": pack},
    )
    assert result.findings[0].evidence_ref.startswith(f"{name}:")
