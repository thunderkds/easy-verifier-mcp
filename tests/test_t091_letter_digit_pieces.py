"""T091 — paths whose name pieces are a letter run then a digit run survive redaction.

``tests/test_t087_third_party_exclusion.py`` came back ``test…****:009fc5eee991.py``:
``t087`` is neither letters-only nor digits-only, so T029's file-name exemption
rejected the name and the 37-character token cleared the 4.0-bit bar.
"""

from __future__ import annotations

import pytest

from easy_verifier.core.redact import redact


@pytest.mark.parametrize(
    "name",
    [
        "tests/test_t087_third_party_exclusion.py",
        "docs/guide_v2_migration_notes_for_operators.md",
        "src/pkg/codec_utf8_roundtrip_fixture_helpers.py",
        "scripts/build_py3_wheels_for_release_candidate.sh",
    ],
)
def test_letter_then_digit_pieces_survive(name: str) -> None:
    assert redact(name) == name


@pytest.mark.parametrize(
    "text",
    [
        "build/main-3f9a2b1c7d8e4a5b6c7d8e9f0a1b2c3d.js",
        "assets/xQzRtWvB_kLmNpQs-TyUiOpAsDfGhJkLz.json",
        "key = pB4kQ9zXmR7tY2wEaB3xK9mQ7rT2vY8wzz.txt",
        "keys/a1b2c3d4e5f6a7b8c9d0a1b2c3d4e5f6.pem",
        "tok_Zx9Qw3Er7Ty1Ui5Op2As8Df4Gh6Jk0LzXcVb.log",
    ],
)
def test_random_shapes_still_fingerprint(text: str) -> None:
    assert redact(text) != text
