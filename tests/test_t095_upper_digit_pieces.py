"""T095 — URL path / file-name pieces: upper-case run then digit run survive.

``https://www.w3.org/WAI/WCAG22/Understanding/non-text-content.html`` came back
``https://www.w3.org/…****:458fc23ebb1e.html``: T091 admitted lower-case
letter-then-digit pieces only, so ``WCAG22`` failed the name-piece shape.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from easy_verifier.core.redact import redact, scan

README = Path(__file__).resolve().parent.parent / "README.md"


def test_trigger_line_survives() -> None:
    text = "See https://www.w3.org/WAI/WCAG22/Understanding/non-text-content.html ok"
    assert redact(text) == text


@pytest.mark.parametrize("piece", ["WCAG22", "HTTP2", "ES2015", "UTF8", "ISO27001"])
def test_upper_digit_pieces_survive_in_url_path_and_before_suffix(piece: str) -> None:
    url = f"https://example.org/standards/{piece}/understanding-non-text-content-page.html"
    assert redact(url) == url
    name = f"docs/guide_{piece}_understanding_non_text_content_notes_for_all.md"
    assert redact(name) == name
    bare = f"{piece}-understanding-non-text-content-notes-for-all-readers.md"
    assert redact(bare) == bare


@pytest.mark.parametrize(
    "text",
    [
        "A1B2C3D4E5F6G7H8J9K0L1M2N3P4Q5R6",  # interleaved
        "https://example.org/build/main-3F9A2B1C.js",  # digits before letters
        "https://example.org/services/T01ABCDE/B02FGHIJ/aB3xK9mQ7rT2vY8wLpN4cD6fGh1JkZxCv",  # noqa: E501
    ],
)
def test_random_shapes_still_fingerprint(text: str) -> None:
    assert redact(text) != text


def test_base64url_token_still_fingerprints() -> None:
    token = "pB4kQ9zXmR7tY2wEaB3xK9mQ7rT2vY8w-_Lp4Nc6"
    assert len(token) == 40
    assert redact(f"value {token}") != f"value {token}"


def test_userinfo_and_query_secrets_still_fingerprint() -> None:
    secret = "Summer2024" + "XqZ"
    userinfo = (
        f"https://user:{secret}@host.example.org/WAI/WCAG22/Understanding/page.html"
    )
    assert secret not in redact(userinfo)
    query = (
        "https://example.org/WAI/WCAG22/Understanding/x.html?token="
        + "WCAG22"
        + "Qx9Zr7Tv3Bn5Lm1Kp8Hs4Dj2Fg6Yc"
    )
    assert "Qx9Zr7Tv3Bn5Lm1Kp8Hs4Dj2Fg6Yc" not in redact(query)


@pytest.mark.parametrize(
    "name",
    [
        "tests/test_ABCDEFG087_third_party_exclusion_fixture.py",  # noqa: E501
        "tests/test_ABC3F9A2B1C_third_party_exclusion_fixture.py",  # noqa: E501
    ],
)
def test_piece_shape_boundary_still_fingerprints(name: str) -> None:
    assert redact(name) != name


def test_readme_has_no_entropy_hit_on_the_w3c_link() -> None:
    text = README.read_text(encoding="utf-8")
    assert "WCAG22" in text
    hits = [h for h in scan(text).hits if h.detector == "high_entropy_string"]
    assert (
        "https://www.w3.org/WAI/WCAG22/Understanding/non-text-content.html"
        in redact(text)
    )
    assert hits == []
