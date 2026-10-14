"""T097 — name pieces: a letter run of any word length then a digit run survive.

``rancher2/cb-ppl/gateway-prod-ingress.yml`` came back ``ranc…****:bdeabc3ea4ad.yml``:
T091/T095 capped the letter run of a letter-then-digit piece at 6, so ``rancher2``
(7 letters) failed the name-piece shape and the path lost the file-suffix exemption.
"""

from __future__ import annotations

import pytest

from easy_verifier.core.redact import redact

TRIGGER = "rancher2/cb-ppl/gateway-prod-ingress.yml"


def test_trigger_path_survives() -> None:
    assert redact(TRIGGER) == TRIGGER


@pytest.mark.parametrize(
    "piece",
    ["rancher2", "backup2", "python3", "postgres16", "elasticsearch7", "KUBERNETES1"],
)
def test_long_pieces_survive_in_url_path_and_before_suffix(piece: str) -> None:
    url = f"https://example.org/standards/{piece}/understanding-non-text-content-page.html"
    assert redact(url) == url
    name = f"docs/guide_{piece}_understanding_non_text_content_notes_for_all.md"
    assert redact(name) == name
    bare = f"{piece}/cb-ppl/gateway-prod-ingress.yml"
    assert redact(bare) == bare


def test_letter_run_bound_is_thirty() -> None:
    letters = "abcdefghijklmnopqrstuvwxyzabcdefg"
    ok = f"tests/test_{letters[:30]}087_third_party_exclusion.py"
    too_long = f"tests/test_{letters[:31]}087_third_party_exclusion.py"
    assert redact(ok) == ok
    assert redact(too_long) != too_long


@pytest.mark.parametrize(
    "text",
    [
        "A1B2C3D4E5F6G7H8J9K0L1M2N3P4Q5R6",  # interleaved
        "build/main-3f9a2b1c7d8e4a5b6c7d8e9f0a1b2c3d.js",  # digits before letters
        "https://example.org/aB3xK9mQzR7tWvY2pL8nC4dF/rancher2/page.html",  # mixed case
        "docs/aB3xK9mQzR7tWvY2pL8nC4dF-rancher2-ingress.yml",
        "AKIA" + "IOSFODNN7EXAMPLE",
        "https://hooks.slack.com/services/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",
    ],
)
def test_random_shapes_still_fingerprint(text: str) -> None:
    assert redact(text) != text


def test_userinfo_and_query_secrets_still_fingerprint() -> None:
    secret = "Summer2024" + "XqZ"
    assert secret not in redact(f"https://user:{secret}@host.example.org/rancher2/page.html")
    token = "Qx9Zr7Tv3Bn5Lm1Kp8Hs4Dj2Fg6Yc"
    query = f"https://example.org/rancher2/x.html?token=rancher2{token}"
    assert token not in redact(query)
