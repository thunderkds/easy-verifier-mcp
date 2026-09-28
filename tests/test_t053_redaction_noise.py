"""T053 — remaining redaction noise: versioned URL paths, commit SHAs, checksum
lines, ``KEY=CONSTANT`` / SPDX shapes; and the ``API_TOKEN = …`` detector gap.

Every exemption is paired with a twin that differs only in the guard it pins, so
forcing that guard open fails a test here (the sabotage check).
"""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pytest

from easy_verifier.core.redact import _shannon_entropy, fingerprint, redact, scan

REPO_ROOT = Path(__file__).resolve().parents[1]

SHA1 = hashlib.sha1(b"t053-fixture").hexdigest()
SHA256 = hashlib.sha256(b"t053-fixture").hexdigest()
SHA512 = hashlib.sha512(b"t053-fixture").hexdigest()
HEX48 = hashlib.sha256(b"t053-other").hexdigest()[:48]
# Synthetic webhook-token shape: mixed case + digits, no vendor prefix.
WEBHOOK_TOKEN = "aB3xK9mQ7rT2vY8wZ1cD"
# A human-chosen password shape: word pieces and a digit run. Only the
# key-material rule covers it, so it is what an over-broad URL exemption leaks.
PASSPHRASE = "Summer-2024-Correct-Horse"
ASVS_FILE = "OWASP_Application_Security_Verification_Standard_5.0.0_en.json"


def _hit(text: str) -> bool:
    return bool(scan(text).hits)


# --- AC 1 — version/release labels in URLs and file names --------------------


@pytest.mark.parametrize(
    "line",
    [
        "https://github.com/OWASP/ASVS/blob/v5.0.0_release/x.json",
        "https://raw.githubusercontent.com/OWASP/ASVS/v5.0.0_release/5.0/docs_en/"
        "OWASP_Application_Security_Verification_Standard_5.0.0_en.flat.json",
        f"[ASVS](https://github.com/OWASP/ASVS/blob/v5.0.0_release/5.0/docs_en/{ASVS_FILE});",
        "http://blog.example.com/2011/07/running-a-nodejs-server-as-a-service-using-forever/",
        "https://example.com/Releases/release-2024-01_Final_Build/Notes",
        "https://example.com/pkg/1.2.3/release-2024-01/",
        f'"{ASVS_FILE}"',
    ],
)
def test_version_labels_in_urls_and_file_names_are_unchanged(line: str) -> None:
    assert redact(line) == line


def test_slack_webhook_token_segment_is_fingerprinted() -> None:
    url = f"https://hooks.slack.com/services/T0A1B2C3/B4D5E6F7/{WEBHOOK_TOKEN}"
    assert fingerprint(WEBHOOK_TOKEN) in redact(url)


@pytest.mark.parametrize(
    ("exempt", "twin", "guard"),
    [
        (
            "https://example.com/Releases/release-2024-01_Final_Build/Notes",
            "example.com/Releases/release-2024-01_Final_Build/Notes",
            "URL anchor",
        ),
        (
            "https://example.com/Releases/release-2024-01_Final_Build/Notes",
            "https://example.com/Releases/release-2024-01_Final_bUild/Notes",
            "piece shape (mixed-case piece)",
        ),
        (
            f"https://db.internal/{PASSPHRASE}/prod",
            f"https://svc:{PASSPHRASE}@db.internal/prod",
            "no exemption in a URL with userinfo",
        ),
        (
            f"https://example.com/login/{PASSPHRASE}",
            f"https://example.com/login?pass={PASSPHRASE}",
            "no exemption in a query string",
        ),
        (
            f'"{ASVS_FILE}"',
            '"OWASP_Application_Security_Verification_Standard_5"',
            "file-suffix anchor",
        ),
        (
            "Release_Notes_Final_Build_Candidate_12345678.md",
            "Release_Notes_Final_Build_Candidate_123456789.md",
            "digit run length",
        ),
    ],
)
def test_each_version_label_guard_keeps_its_twin_fingerprinted(
    exempt: str, twin: str, guard: str
) -> None:
    assert not _hit(exempt), guard
    assert _hit(twin), guard


@pytest.mark.parametrize(
    ("url", "detector"),
    [
        (f"https://example.com/cb?token={WEBHOOK_TOKEN}xQ", "credential_assignment"),
        (f"https://example.com/files/{WEBHOOK_TOKEN}-release", "key_material_segment"),
        (
            "https://example.com/cb/eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0In0.c2lnbmF0dXJl",
            "jwt",
        ),
    ],
)
def test_secrets_embedded_in_urls_stay_caught(url: str, detector: str) -> None:
    assert detector in [hit.detector for hit in scan(url).hits]


# --- AC 2 — commit SHAs and checksum lines ------------------------------------


@pytest.mark.parametrize(
    "line",
    [
        f"Pinned:  commit {SHA1}",
        f"| Local commit | `{SHA1}` |",
        f"- [#{SHA1[:8]}](https://gitlab.example.com/g/p/commit/{SHA1}) Add feature",
        f"https://github.com/o/r/commits/{SHA1}",
        f"Source:  https://raw.githubusercontent.com/o/r/{SHA1}/lib/languages.yml",
        f"https://github.com/o/r/blob/{SHA1}/src/x.py",
        f"https://github.com/o/r/tree/{SHA1}",
        f"{SHA256}  NOTICE",
        f"{SHA256} *asvs.json",
        f"{SHA512}  dist/pkg-1.0.tar.gz",
        # Short SHAs never reach a rule: below the 32-char hex floor, and no
        # upper case for the key-material rule.
        f"commit {SHA1[:7]}",
        f"deployed {SHA1[:12]} to staging",
    ],
)
def test_commit_shas_and_checksum_lines_are_unchanged(line: str) -> None:
    assert scan(line).hits == (), line


def test_a_whole_checksum_file_is_unchanged() -> None:
    text = f"{SHA256}  NOTICE\n{hashlib.sha256(b'x').hexdigest()}  asvs.json\n"
    assert redact(text) == text


@pytest.mark.parametrize(
    ("exempt", "twin", "guard"),
    [
        (f"commit {SHA1}", f"deploy {SHA1}", "commit word"),
        (f"commit {SHA1}", f"commit the release {SHA1}", "commit word adjacent"),
        (f"commit {SHA1}", f"commit {HEX48}", "SHA length"),
        (
            f"Pinned:  v5.0.0_release ({SHA1})",
            f"Pinned  v5.0.0_release ({SHA1})",
            "pinned key position",
        ),
        (f"commit {SHA1}", f"commit {SHA1}  # api token", "secret veto"),
        (f"/blob/{SHA1}/x.py", f"/hooks/{SHA1}/x.py", "blob/tree anchor"),
        (
            f"https://raw.githubusercontent.com/o/r/{SHA1}/x.yml",
            f"https://raw.example.com/o/r/{SHA1}/x.yml",
            "raw.githubusercontent.com host",
        ),
        (f"{SHA256}  NOTICE", SHA256, "checksum needs a file name"),
        (f"{SHA256}  NOTICE", f"{SHA256} NOTICE", "checksum separator"),
        (f"{SHA256}  NOTICE", f"x {SHA256}  NOTICE", "checksum at line start"),
        (f"{SHA256}  NOTICE", f"{HEX48}  NOTICE", "checksum length"),
        (f"{SHA256}  NOTICE", f"{SHA256}  api_token.txt", "checksum veto"),
    ],
)
def test_each_commit_and_checksum_guard_keeps_its_twin_fingerprinted(
    exempt: str, twin: str, guard: str
) -> None:
    assert not _hit(exempt), guard
    assert _hit(twin), guard


@pytest.mark.parametrize(
    "line", [f'API_TOKEN = "{SHA1}"', f"api_key: {SHA256}", f'"secret": "{SHA1}"']
)
def test_hex_under_a_secret_named_key_is_fingerprinted(line: str) -> None:
    assert _hit(line)


# --- AC 3 — KEY=CONSTANT and SPDX licence identifiers -------------------------


@pytest.mark.parametrize(
    "line",
    [
        "SystemMessage(content=QUERY_PLANNING_SYSTEM_PROMPT),",
        "SystemMessage(content=_EXTRACTION_SYSTEM_PROMPT),",
        "plan_rationale=_MIN_PLAN_RATIONALE,",
        "linguist_license=LINGUIST_LICENSE,",
        "SINK_CAP_WARNING.format(path=path, limit=MAX_SINK_EXCERPTS_PER_FILE),",
        '"license": "BSD-3-Clause",',
        'license = "BSD-2-Clause"',
    ],
)
def test_constants_and_spdx_ids_are_unchanged(line: str) -> None:
    assert redact(line) == line


@pytest.mark.parametrize(
    ("exempt", "twin", "guard"),
    [
        (
            "content=PACK_MY_BOX_WITH_FIVE_DOZEN_LIQUOR_JUGS",
            'content="aB3xK9mQ7rT2vY8wZ1cDeF5gH7jK9lM1"',
            "quoted random value",
        ),
        (
            "content=PACK_MY_BOX_WITH_FIVE_DOZEN_LIQUOR_JUGS",
            "content=QKZVXMHJTYBNWPFRLSDGCAEUOI",
            "constant needs at least two pieces",
        ),
        (
            "content=PACK_MY_BOX_WITH_FIVE_DOZEN_LIQUOR_JUGS",
            "content=PACK_MY_BOX_WITH_FIVE_DOZEN_LIQUOR_Jugs",
            "constant pieces are upper case",
        ),
        (
            "content=PACK_MY_BOX_WITH_FIVE_DOZEN_LIQUOR_JUGS",
            "content+PACK_MY_BOX_WITH_FIVE_DOZEN_LIQUOR_JUGS",
            "whole token is key=CONSTANT",
        ),
        (
            "content=PACK_MY_BOX_WITH_FIVE_DOZEN_LIQUOR_JUGS",
            "cOnTeNtXy=PACK_MY_BOX_WITH_FIVE_DOZEN_LIQUOR_JUGS",
            "key is a word-shaped identifier",
        ),
        ('"license": "BSD-3-Clause"', '"flavour": "BSD-3-Clause"', "licence key"),
        ('"license": "BSD-3-Clause"', '"license": "aB3x-K9mQ-7rT2"', "SPDX shape"),
    ],
)
def test_each_constant_guard_keeps_its_twin_fingerprinted(
    exempt: str, twin: str, guard: str
) -> None:
    assert not _hit(exempt), guard
    assert _hit(twin), guard


def test_constant_twins_clear_the_long_token_bar() -> None:
    # The twins above must be caught by the bar, not by being short.
    assert _shannon_entropy("content=QKZVXMHJTYBNWPFRLSDGCAEUOI") >= 4.0


def test_a_secret_named_key_with_a_constant_value_is_still_caught() -> None:
    hits = scan("API_KEY=PACK_MY_BOX_WITH_FIVE_DOZEN_LIQUOR_JUGS").hits
    assert [hit.detector for hit in hits] == ["credential_assignment"]


# --- AC 4 — credential_assignment catches _-joined secret names ---------------


@pytest.mark.parametrize(
    ("line", "value"),
    [
        ('API_TOKEN = "hunter2"', "hunter2"),
        ('api_token = "hunter2"', "hunter2"),
        ("SERVICE_API_KEY=hunter2", "hunter2"),
        ("db_password: hunter2", "hunter2"),
        ("GITHUB_ACCESS_KEY=s3cr3tval", "s3cr3tval"),
    ],
)
def test_underscore_joined_secret_names_are_caught(line: str, value: str) -> None:
    result = scan(line)
    assert [hit.detector for hit in result.hits] == ["credential_assignment"]
    assert value not in result.text
    assert fingerprint(value) in result.text


@pytest.mark.parametrize(
    "line", ['mytoken = "hunter2"', 'API_TOKEN_URL = "hunter2"', "passwords = 3"]
)
def test_secret_word_inside_a_longer_word_is_not_a_credential(line: str) -> None:
    # Sabotage pin: dropping the left boundary altogether would catch these.
    assert scan(line).hits == ()


# --- AC 5 — this repo's vendored snapshots and checksum file ------------------


@pytest.mark.parametrize(
    "relative",
    [
        "src/easy_verifier/registry/vendored/asvs.json",
        "src/easy_verifier/registry/vendored/NOTICE",
        "src/easy_verifier/registry/vendored/CHECKSUMS.sha256",
    ],
)
def test_vendored_snapshot_files_carry_no_fingerprint(relative: str) -> None:
    tracked = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "ls-files", "--error-unmatch", relative],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert tracked == relative
    text = (REPO_ROOT / relative).read_text(encoding="utf-8")
    assert [(hit.line, hit.detector) for hit in scan(text).hits] == []
