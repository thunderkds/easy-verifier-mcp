#!/usr/bin/env python3
"""Maintainer script: refresh pinned, version-locked snapshots of the three
external reference sources used by the registry (T032, DDR-0007 item 9).

Sources (all pinned to an exact version/commit, never "latest"):
    - GitHub Linguist ``lib/linguist/languages.yml``            (MIT)
    - OWASP ASVS flat JSON export from a tagged release          (CC BY-SA 4.0)
    - MITRE CWE XML catalogue from a versioned release zip       (MITRE terms)

Only the fields the registry actually consumes are kept — see ``KEEP_*``
below. Output lands in ``src/easy_verifier/registry/vendored/``, committed to
the repo; nothing under ``src/`` ever performs a network call, and this
script is never imported by runtime code.

Usage:
    python scripts/vendor_sources.py            # re-fetch and refresh snapshots
    python scripts/vendor_sources.py --check    # verify committed snapshots
                                                 # against recorded checksums,
                                                 # no network access
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
VENDORED_DIR = REPO_ROOT / "src" / "easy_verifier" / "registry" / "vendored"
CHECKSUMS_FILE = VENDORED_DIR / "CHECKSUMS.sha256"
NOTICE_FILE = VENDORED_DIR / "NOTICE"

# --- Pins -------------------------------------------------------------
# Every source is pinned to an exact commit or release tag. Bumping a pin is
# a deliberate maintainer action: edit the constant below, re-run this
# script without --check, and commit the new snapshot + checksums.

LINGUIST_COMMIT = "d0921d10bb68a1249fc9eac64e472759f36e2fd8"
LINGUIST_URL = (
    f"https://raw.githubusercontent.com/github-linguist/linguist/"
    f"{LINGUIST_COMMIT}/lib/linguist/languages.yml"
)
LINGUIST_LICENSE = "MIT"
LINGUIST_ATTRIBUTION = "GitHub Linguist contributors (github-linguist/linguist)"

ASVS_TAG = "v5.0.0_release"
ASVS_COMMIT = "5cf9b032440be53ce345ab3c130fda46ba1ce7a2"
ASVS_URL = (
    f"https://raw.githubusercontent.com/OWASP/ASVS/{ASVS_TAG}/5.0/docs_en/"
    "OWASP_Application_Security_Verification_Standard_5.0.0_en.flat.json"
)
ASVS_SOURCE_DOC_URL = (
    f"https://github.com/OWASP/ASVS/blob/{ASVS_TAG}/5.0/docs_en/"
    "OWASP_Application_Security_Verification_Standard_5.0.0_en.json"
)
ASVS_LICENSE = "CC-BY-SA-4.0"
ASVS_ATTRIBUTION = "OWASP Application Security Verification Standard (OWASP ASVS) 5.0.0"

CWE_VERSION = "4.20"
CWE_URL = f"https://cwe.mitre.org/data/xml/cwec_v{CWE_VERSION}.xml.zip"
CWE_LICENSE = "MITRE-CWE-Terms-of-Use"
CWE_ATTRIBUTION = (
    "This product uses the Common Weakness Enumeration (CWE) and is not "
    "sponsored or endorsed by The MITRE Corporation. Copyright (c) MITRE."
)

MAX_TOTAL_BYTES = 500 * 1024


class UpstreamFormatError(RuntimeError):
    """Raised when a fetched source no longer matches its expected shape.

    Fails loudly, before any file is written, so a silent upstream format
    change can never produce a quietly degraded committed snapshot.
    """


def _validate_linguist(languages: dict[str, dict[str, list[str]]]) -> None:
    if len(languages) < 500:
        raise UpstreamFormatError(
            f"Linguist: expected >= 500 languages, parsed only {len(languages)} "
            "— languages.yml may have changed structure"
        )
    required = {
        "Python": ".py",
        "Kotlin": ".kt",
        "Go": ".go",
        "C++": ".cpp",
    }
    for name, extension in required.items():
        entry = languages.get(name)
        if entry is None:
            raise UpstreamFormatError(f"Linguist: missing expected language {name!r}")
        if not entry["extensions"]:
            raise UpstreamFormatError(f"Linguist: {name!r} has no extensions")
        if extension not in entry["extensions"]:
            raise UpstreamFormatError(
                f"Linguist: {name!r} extensions do not include {extension!r}: "
                f"{entry['extensions']}"
            )


def _validate_asvs(requirements: list[dict[str, str]]) -> None:
    if len(requirements) < 300:
        raise UpstreamFormatError(
            f"ASVS: expected >= 300 requirements, got {len(requirements)} "
            "— export format may have changed"
        )
    for req in requirements:
        if not req.get("id") or not req.get("title") or not req.get("chapter"):
            raise UpstreamFormatError(
                f"ASVS: requirement missing id/title/chapter: {req}"
            )


def _validate_cwe(weaknesses: list[dict[str, str]]) -> None:
    if len(weaknesses) < 900:
        raise UpstreamFormatError(
            f"CWE: expected >= 900 weaknesses, got {len(weaknesses)} "
            "— catalogue format may have changed"
        )
    ids = {w["id"] for w in weaknesses}
    required_ids = {"78", "89", "95", "798"}
    missing = required_ids - ids
    if missing:
        raise UpstreamFormatError(
            f"CWE: missing expected weakness ids {sorted(missing)}"
        )


def _retrieved_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fetch(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=30) as resp:  # noqa: S310 - pinned https URLs only
        return resp.read()


# --- Linguist: minimal, purpose-built languages.yml reader --------------
# Not a general YAML parser. It relies on the file's stable, documented
# structure (top-level "Language Name:" keys, 2-space indented scalar
# fields, "  extensions:"/"  filenames:" followed by "  - value" list
# items) which the Linguist maintainers describe explicitly in the file's
# own header comment. Anything else in the file is ignored.

_LANG_HEADER = re.compile(r"^(\S.*):\s*$")
_FIELD_HEADER = re.compile(r"^  (\w+):\s*$")
_LIST_ITEM = re.compile(r'^  - (?:"([^"]*)"|(\S+))\s*$')


def _parse_languages_yml(text: str) -> dict[str, dict[str, list[str]]]:
    languages: dict[str, dict[str, list[str]]] = {}
    current_lang: str | None = None
    current_field: str | None = None

    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        if not raw_line.startswith(" "):
            match = _LANG_HEADER.match(raw_line)
            if match:
                current_lang = match.group(1)
                languages[current_lang] = {"extensions": [], "filenames": []}
                current_field = None
            continue
        field_match = _FIELD_HEADER.match(raw_line)
        if field_match:
            current_field = field_match.group(1)
            continue
        item_match = _LIST_ITEM.match(raw_line)
        if item_match and current_lang and current_field in ("extensions", "filenames"):
            quoted, bare = item_match.group(1), item_match.group(2)
            value = quoted if quoted is not None else bare
            languages[current_lang][current_field].append(value)

    return {
        name: fields
        for name, fields in languages.items()
        if fields["extensions"] or fields["filenames"]
    }


def fetch_linguist() -> dict:
    raw = _fetch(LINGUIST_URL)
    languages = _parse_languages_yml(raw.decode("utf-8"))
    _validate_linguist(languages)
    return {
        "meta": {
            "source_url": LINGUIST_URL,
            "pinned_commit": LINGUIST_COMMIT,
            "retrieved": _retrieved_now(),
            "license": LINGUIST_LICENSE,
            "attribution": LINGUIST_ATTRIBUTION,
        },
        "languages": languages,
    }


# --- OWASP ASVS ------------------------------------------------------


def fetch_asvs() -> dict:
    raw = _fetch(ASVS_URL)
    data = json.loads(raw.decode("utf-8"))
    requirements = [
        {
            "id": req["req_id"],
            "title": req["req_description"],
            "chapter": req["chapter_name"],
            "url": ASVS_SOURCE_DOC_URL,
        }
        for req in data["requirements"]
    ]
    _validate_asvs(requirements)
    return {
        "meta": {
            "source_url": ASVS_URL,
            "pinned_version": ASVS_TAG,
            "pinned_commit": ASVS_COMMIT,
            "retrieved": _retrieved_now(),
            "license": ASVS_LICENSE,
            "attribution": ASVS_ATTRIBUTION,
        },
        "requirements": requirements,
    }


# --- MITRE CWE ---------------------------------------------------------

_CWE_NS = {"c": "http://cwe.mitre.org/cwe-7"}


def fetch_cwe() -> dict:
    raw = _fetch(CWE_URL)
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        xml_names = [n for n in zf.namelist() if n.endswith(".xml")]
        if len(xml_names) != 1:
            raise RuntimeError(
                f"expected exactly one XML in {CWE_URL}, found {xml_names}"
            )
        xml_bytes = zf.read(xml_names[0])

    weaknesses = []
    for _event, elem in ET.iterparse(io.BytesIO(xml_bytes), events=("end",)):
        tag = elem.tag.split("}")[-1]
        if tag == "Weakness":
            cwe_id = elem.get("ID")
            name = elem.get("Name")
            weaknesses.append(
                {
                    "id": cwe_id,
                    "name": name,
                    "url": f"https://cwe.mitre.org/data/definitions/{cwe_id}.html",
                }
            )
            elem.clear()
    weaknesses.sort(key=lambda w: int(w["id"]))
    _validate_cwe(weaknesses)
    return {
        "meta": {
            "source_url": CWE_URL,
            "pinned_version": CWE_VERSION,
            "retrieved": _retrieved_now(),
            "license": CWE_LICENSE,
            "attribution": CWE_ATTRIBUTION,
        },
        "weaknesses": weaknesses,
    }


NOTICE_TEMPLATE = """\
This directory contains pinned, filtered snapshots of three external
reference sources, vendored offline (no runtime network access — DDR-0007
item 9). Refresh via `python scripts/vendor_sources.py`.

## linguist.json
Source:  {linguist_url}
Pinned:  commit {linguist_commit}
License: {linguist_license}
Attribution: {linguist_attribution}

## asvs.json
Source:  {asvs_url}
Pinned:  {asvs_version} ({asvs_commit})
License: {asvs_license} — https://creativecommons.org/licenses/by-sa/4.0/
Attribution: {asvs_attribution}. This project is not affiliated with or
endorsed by OWASP.

## cwe.json
Source:  {cwe_url}
Pinned:  version {cwe_version}
License: {cwe_license}
Attribution: {cwe_attribution}
"""


def write_notice() -> None:
    NOTICE_FILE.write_text(
        NOTICE_TEMPLATE.format(
            linguist_url=LINGUIST_URL,
            linguist_commit=LINGUIST_COMMIT,
            linguist_license=LINGUIST_LICENSE,
            linguist_attribution=LINGUIST_ATTRIBUTION,
            asvs_url=ASVS_URL,
            asvs_version=ASVS_TAG,
            asvs_commit=ASVS_COMMIT,
            asvs_license=ASVS_LICENSE,
            asvs_attribution=ASVS_ATTRIBUTION,
            cwe_url=CWE_URL,
            cwe_version=CWE_VERSION,
            cwe_license=CWE_LICENSE,
            cwe_attribution=CWE_ATTRIBUTION,
        ),
        encoding="utf-8",
    )


def _sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_checksums(files: list[Path]) -> None:
    lines = [f"{_sha256_of(f)}  {f.name}" for f in sorted(files, key=lambda p: p.name)]
    CHECKSUMS_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def check() -> int:
    """Verify committed snapshots against recorded checksums. No network."""
    if not CHECKSUMS_FILE.exists():
        print(f"FAIL: {CHECKSUMS_FILE} does not exist", file=sys.stderr)
        return 1
    expected = {}
    for line in CHECKSUMS_FILE.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, name = line.split("  ", 1)
        expected[name] = digest

    ok = True
    for name, digest in expected.items():
        path = VENDORED_DIR / name
        if not path.exists():
            print(f"FAIL: {path} is missing", file=sys.stderr)
            ok = False
            continue
        actual = _sha256_of(path)
        if actual != digest:
            print(
                f"FAIL: {path} checksum mismatch (expected {digest}, got {actual})",
                file=sys.stderr,
            )
            ok = False
    if ok:
        print(f"OK: {len(expected)} vendored file(s) match recorded checksums")
        return 0
    return 1


def refresh() -> int:
    VENDORED_DIR.mkdir(parents=True, exist_ok=True)

    linguist = fetch_linguist()
    asvs = fetch_asvs()
    cwe = fetch_cwe()

    files = []
    for name, payload in (
        ("linguist.json", linguist),
        ("asvs.json", asvs),
        ("cwe.json", cwe),
    ):
        path = VENDORED_DIR / name
        text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        path.write_text(text, encoding="utf-8")
        files.append(path)

    write_notice()
    files.append(NOTICE_FILE)
    write_checksums(files)

    total_bytes = sum(f.stat().st_size for f in files) + CHECKSUMS_FILE.stat().st_size
    print(f"Wrote {len(files)} vendored files, {total_bytes} bytes total.")
    if total_bytes > MAX_TOTAL_BYTES:
        print(
            f"WARNING: vendored snapshot total ({total_bytes} bytes) exceeds "
            f"the {MAX_TOTAL_BYTES}-byte target.",
            file=sys.stderr,
        )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify committed snapshots against recorded checksums; no network access",
    )
    args = parser.parse_args()
    return check() if args.check else refresh()


if __name__ == "__main__":
    sys.exit(main())
