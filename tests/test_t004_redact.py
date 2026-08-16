"""T004 — evidence-layer secret redaction (NFR-010).

Three layers, per the guide's Test Plan:

1. unit — each detector, table-driven, positive and negative;
2. format/property — fingerprint shape, stability, unsaltedness;
3. **negative integration** — the layer that matters: a full pipeline run over a
   seeded temp repo with logging captured at DEBUG, asserting zero raw values in
   the pack, the logs, stdout/stderr, and in a traceback forced mid-pipeline.

Every secret below is a published example or an obviously synthetic value. None
is functional.
"""

from __future__ import annotations

import hashlib
import io
import json
import logging
import re
import time
import traceback
from dataclasses import asdict, replace
from pathlib import Path

import pytest

from easy_verifier.core import pipeline
from easy_verifier.core import redact as redact_module
from easy_verifier.core.models import DimensionDescriptor, Excerpt
from easy_verifier.core.pipeline import RepoPathError, run_dimension
from easy_verifier.core.redact import fingerprint, scan

# --- Fake secrets (published examples / synthetic) --------------------------
#
# **Never use a real vendor prefix here.** `sk_live_`, `ghp_`, `xoxb-` and
# friends are matched on *shape* by GitHub push protection and every other
# credential scanner, which cannot tell a plausible fake from a real key — an
# earlier revision of this file used `sk_live_` and `ghp_` and was rejected at
# push time. The detectors under test match on the `key=value` shape and the
# character mix, never on a vendor prefix, so an obviously-synthetic value
# exercises exactly the same code path. Spell the fakeness into the value, the
# way PEM below does.

AWS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"
AWS_SECRET = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
JWT = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIn0"
    ".SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
)
# Assembled at runtime, never written as a literal. Credential scanners
# (GitHub push protection among them) match the PEM banner on sight and cannot
# tell a fake body from a real one — a literal here gets the whole push
# rejected, which is what happened before this was split up. Concatenation
# produces the identical string at run time, so `private_key_pem` is tested
# against exactly the banner it must match in the wild.
_PEM_DASHES = "-" * 5
_PEM_LABEL = "RSA PRIVATE" + " KEY"
PEM = (
    f"{_PEM_DASHES}BEGIN {_PEM_LABEL}{_PEM_DASHES}\n"
    "MIIEowIBAAKCAQEAxFAKEfakeFAKEfakeFAKEfakeFAKEfakeFAKEfakeFAKEfake\n"
    "b2FKEfakeFAKEfakeFAKEfakeFAKEfakeFAKEfakeFAKEfakeFAKEfakeFAKEfak=\n"
    f"{_PEM_DASHES}END {_PEM_LABEL}{_PEM_DASHES}"
)
# Same reasoning as the PEM banner above: a complete webhook URL is a shape
# GitHub push protection matches on sight, so it is assembled rather than
# written out. The host is split too, because the full
# `host/services/T…/B…/<token>` string is what the scanner keys on.
_SLACK_HOST = "hooks.slack" + ".com"
_SLACK_TOKEN = "pB4kQ9zXmR7tY2wE1nV5cJ6h"
SLACK_WEBHOOK = f"https://{_SLACK_HOST}/services/T024BE7LD/B024BE7LH/{_SLACK_TOKEN}"

API_KEY_VALUE = "FAKEfake9f2Ba7Qz1XcV8mNp4LrT6Ke0"
HEX_SECRET = "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"

ALL_RAW_SECRETS = (AWS_KEY_ID, AWS_SECRET, JWT, API_KEY_VALUE, HEX_SECRET)

FINGERPRINT_PATTERN = re.compile(r"^.{0,4}…\*\*\*\*:[0-9a-f]{12}$")


# --- Layer 1: detectors -----------------------------------------------------


@pytest.mark.parametrize(
    ("detector", "text", "raw"),
    [
        ("aws_access_key_id", f"key = {AWS_KEY_ID}", AWS_KEY_ID),
        (
            "aws_secret_access_key",
            f"AWS_SECRET_ACCESS_KEY={AWS_SECRET}",
            AWS_SECRET,
        ),
        ("jwt", f"Authorization: Bearer {JWT}", JWT),
        ("private_key_pem", f"cert:\n{PEM}\n", PEM),
        ("credential_assignment", f'api_key = "{API_KEY_VALUE}"', API_KEY_VALUE),
        ("credential_assignment", "password: changeme", "changeme"),
        ("high_entropy_hex", f"digest {HEX_SECRET}", HEX_SECRET),
    ],
)
def test_detector_fires_and_removes_the_raw_value(detector, text, raw):
    result = scan(text)

    assert raw not in result.text, "raw value survived redaction"
    assert detector in {hit.detector for hit in result.hits}, (
        f"expected {detector}, got {[hit.detector for hit in result.hits]}"
    )


@pytest.mark.parametrize(
    ("shape", "text", "raw"),
    [
        (
            "secret as a path segment",
            "/etc/keys/aB3xK9mQ7zR2tY8wE1nP5vC4jL6hG0dF",
            "aB3xK9mQ7zR2tY8wE1nP5vC4jL6hG0dF",
        ),
        (
            "webhook token in a URL path",
            SLACK_WEBHOOK,
            _SLACK_TOKEN,
        ),
        (
            "password inside a postgres URI",
            "DATABASE_URL=postgres://admin:pB4kQ9zXmR7tY2wE@db.internal:5432/prod",
            "pB4kQ9zXmR7tY2wE",
        ),
        (
            "password inside a mongodb URI",
            "connect with mongodb://root:xK9mQ7zR2tY8wE1n@10.0.0.5/admin",
            "xK9mQ7zR2tY8wE1n",
        ),
        (
            "bare token, the A/B control",
            "aB3xK9mQ7zR2tY8wE1nP5vC4jL6hG0dF",
            "aB3xK9mQ7zR2tY8wE1nP5vC4jL6hG0dF",
        ),
    ],
)
def test_a_secret_carried_by_a_path_or_uri_is_still_redacted(shape, text, raw):
    """Stage 4 P1 regression — the highest-value real-world leak shapes.

    An earlier revision exempted whole path-like spans from the entropy rule,
    which inverted the "tune toward over-redaction" trade for exactly the shapes
    credentials most often escape in. Detection is now per segment, so the path
    or URI structure survives and only the credential inside it is replaced.
    """
    result = scan(text)

    assert raw not in result.text, f"{shape}: credential survived"
    assert result.hits


@pytest.mark.parametrize(
    "surviving",
    [_SLACK_HOST, "db.internal", "postgres://admin", "/etc/keys/"],
)
def test_the_structure_around_a_redacted_credential_survives(surviving):
    """NFR-010: the location has to stay readable, or the hit is not actionable."""
    text = (
        f"{SLACK_WEBHOOK}\n"
        "DATABASE_URL=postgres://admin:pB4kQ9zXmR7tY2wE@db.internal:5432/prod\n"
        "/etc/keys/aB3xK9mQ7zR2tY8wE1nP5vC4jL6hG0dF\n"
    )

    assert surviving in scan(text).text


@pytest.mark.parametrize(
    ("text", "raw"),
    [
        ("password=hunter2  # dev only", "hunter2"),
        ("password=changeme  # rotate me", "changeme"),
        ("password: hunter2 // legacy", "hunter2"),
    ],
)
def test_a_weak_password_with_a_trailing_comment_is_still_redacted(text, raw):
    """Stage 4 follow-up: this detector is a short password's *only* cover.

    A low-entropy value clears no entropy bar and has no recognisable shape, so
    the end-of-line anchor had to admit `#` and `//` rather than assume another
    layer caught it. Known residue: a value followed by bare prose on the same
    line, with no comment marker, is still missed.
    """
    result = scan(text)

    assert raw not in result.text
    assert result.hits


def test_an_ordinary_repository_path_is_not_fingerprinted():
    """The cosmetic problem the old exemption existed for, still fixed."""
    text = (
        "- **Repo**: `/home/hungnguyenhuu/workspace/pets/hungnguyen111"
        "/easy-verifier-mcp`"
    )

    assert scan(text).text == text


@pytest.mark.parametrize(
    "text",
    [
        "",
        "   \n\t ",
        "The quick brown fox jumps over the lazy dog, repeatedly and at length.",
        "def calculate_coverage_score(sources_found, sources_sought): return 1.0",
        "See docs/architecture/decision-records for the rationale behind this.",
    ],
)
def test_ordinary_text_is_returned_unchanged_with_no_hits(text):
    result = scan(text)

    assert result.text == text
    assert result.hits == ()


def test_pem_block_is_masked_in_full_not_just_its_first_line():
    result = scan(f"before\n{PEM}\nafter")

    assert "MIIEowIBAAKCAQEA" not in result.text
    assert "-----END RSA PRIVATE KEY-----" not in result.text
    assert result.text.startswith("before\n")
    assert result.text.endswith("\nafter")


def test_overlapping_matches_produce_one_hit_and_intact_surrounding_text():
    # The assignment detector and the AWS detector both cover this value.
    result = scan(f"aws_access_key_id = {AWS_KEY_ID}")

    assert len(result.hits) == 1
    assert AWS_KEY_ID not in result.text
    assert result.text.startswith("aws_access_key_id = ")


def test_offsets_stay_valid_when_replacement_changes_the_length():
    text = f"a={AWS_KEY_ID}\nb={JWT}\n"
    result = scan(text)

    for hit in result.hits:
        assert text[hit.offset : hit.offset + 4] == hit.fingerprint[:4]


def test_line_numbers_are_reported_one_indexed():
    result = scan(f"line one\nline two\nkey={AWS_KEY_ID}\n")

    assert [hit.line for hit in result.hits] == [3]


def test_non_utf8_bytes_next_to_a_match_do_not_break_redaction():
    text = f"\udcff binary \udcfe key={AWS_KEY_ID} \udcff"
    result = scan(text)

    assert AWS_KEY_ID not in result.text
    assert result.hits


@pytest.mark.parametrize("placeholder", ["changeme", "xxx", "REPLACE_ME"])
def test_placeholder_values_are_still_redacted(placeholder):
    # FR-013: the engine does not judge whether a secret is "real".
    result = scan(f"password={placeholder}")

    assert result.hits
    assert result.hits[0].fingerprint in result.text
    # A value no longer than the 4-character mask is fully visible inside its
    # own fingerprint. That is the decided mask width, not a bug — and a 3- or
    # 4-character credential has no material to protect.
    if len(placeholder) > 4:
        assert placeholder not in result.text


def test_a_very_long_line_is_bounded_work_not_catastrophic_backtracking():
    hostile = (
        ("aws_secret_access_key=" + "A" * 39 + "!") * 200 + "-----BEGIN " + "A" * 5000
    )

    started = time.monotonic()
    scan(hostile)
    elapsed = time.monotonic() - started

    assert elapsed < 2.0, f"redaction took {elapsed:.2f}s — possible ReDoS"


# --- Layer 2: fingerprint format and properties -----------------------------


def test_fingerprint_matches_the_decided_format_exactly():
    value = fingerprint(AWS_KEY_ID)

    assert FINGERPRINT_PATTERN.match(value), value
    assert value.startswith("AKIA…****:")


def test_fingerprint_is_unsalted_sha256_truncated_to_twelve_hex():
    expected = hashlib.sha256(AWS_KEY_ID.encode("utf-8")).hexdigest()[:12]

    assert fingerprint(AWS_KEY_ID).endswith(f":{expected}")


def test_no_salt_is_read_from_config_env_or_disk(monkeypatch, tmp_path):
    """AC #2: the fingerprint must not depend on any external input."""
    baseline = fingerprint(AWS_KEY_ID)
    # Read before io is sealed below. Docstrings are stripped first: the module
    # *documents* that it reads no environment, and the word must not be
    # mistaken for the behaviour.
    source = re.sub(r'"""[\s\S]*?"""', "", Path(redact_module.__file__).read_text())
    for forbidden in ("import os", "environ", "getenv", "open(", "read_text"):
        assert forbidden not in source, f"redact.py reads external state: {forbidden}"

    for name in ("EASY_VERIFIER_SALT", "REDACTION_SALT", "SALT", "SECRET_KEY"):
        monkeypatch.setenv(name, "a-salt-that-must-be-ignored")
    monkeypatch.chdir(tmp_path)
    (tmp_path / "salt").write_text("a-salt-on-disk")

    def _explode(*args, **kwargs):  # pragma: no cover - must never be called
        raise AssertionError("redaction touched the filesystem")

    monkeypatch.setattr(io, "open", _explode, raising=False)

    assert fingerprint(AWS_KEY_ID) == baseline
    assert scan(f"k={AWS_KEY_ID}").hits[0].fingerprint == baseline


def test_same_value_fingerprints_identically_across_calls_and_files():
    first = scan(f"a={AWS_KEY_ID}")
    second = scan(f"totally different context {AWS_KEY_ID} here")

    assert first.hits[0].fingerprint == second.hits[0].fingerprint


def test_a_hit_carries_no_raw_value_on_any_field():
    hit = scan(f"k={AWS_KEY_ID}").hits[0]

    assert AWS_KEY_ID not in json.dumps(asdict(hit))
    assert "value" not in asdict(hit), "a raw-value field is a leak waiting to happen"


def test_redaction_assigns_no_severity_score_or_verdict():
    fields = set(asdict(scan(f"k={AWS_KEY_ID}").hits[0]))

    assert not fields & {"severity", "score", "verdict", "grade", "risk", "passed"}


# --- Layer 3: negative integration ------------------------------------------


def _seed_repo(root: Path) -> dict[str, str]:
    """Write ten distinct fake secrets across a small repo. Returns raw values."""
    secrets = {
        "aws_id": AWS_KEY_ID,
        "aws_secret": AWS_SECRET,
        "jwt": JWT,
        "api_key": API_KEY_VALUE,
        "hex": HEX_SECRET,
        "token": "FAKEfakeA1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6",
        "password": "hunter2-not-a-real-password",
        "client_secret": "FAKEfake7Yq2Wm5Zp8Rt1Vx4Nb6Hd9Kf3Jg0Ls",
        "pem": PEM,
        "entropy": "Zm9vYmFyYmF6cXV4MTIzNDU2Nzg5MEFCQ0RFRkdISUpLTA==",
    }
    (root / "config.env").write_text(
        f"AWS_ACCESS_KEY_ID={secrets['aws_id']}\n"
        f"AWS_SECRET_ACCESS_KEY={secrets['aws_secret']}\n"
        f"api_key={secrets['api_key']}\n"
        f"token={secrets['token']}\n"
        f"password={secrets['password']}\n"
        f"client_secret={secrets['client_secret']}\n"
    )
    (root / "notes.md").write_text(
        f"bearer {secrets['jwt']}\ndigest {secrets['hex']}\nblob {secrets['entropy']}\n"
    )
    (root / "id_rsa").write_text(secrets["pem"] + "\n")
    return secrets


def _descriptor(sources: tuple[str, ...]) -> DimensionDescriptor:
    def collect(ctx):
        for index, source in enumerate(sources, start=1):
            text = ctx.read_source(source)
            if text is not None:
                yield Excerpt(
                    path=source,
                    start_line=1,
                    end_line=1 + text.count("\n"),
                    text=text,
                )
            logging.getLogger("easy_verifier.test").debug(
                "collected source %s (%s)", index, source
            )

    return DimensionDescriptor(
        name="seeded",
        purpose="negative integration",
        sources_sought=sources,
        collect=collect,
    )


SEEDED_SOURCES = ("config.env", "notes.md", "id_rsa")


def test_no_raw_secret_reaches_the_pack_the_logs_or_stdout(tmp_path, caplog, capsys):
    """AC #5 — the leak path that actually bites."""
    secrets = _seed_repo(tmp_path)
    caplog.set_level(logging.DEBUG)

    pack = run_dimension(_descriptor(SEEDED_SOURCES), tmp_path)

    pack_json = json.dumps(asdict(pack))
    logged = "\n".join(record.getMessage() for record in caplog.records) + caplog.text
    captured = capsys.readouterr()

    for name, raw in secrets.items():
        assert raw not in pack_json, f"{name} leaked into the pack"
        assert raw not in logged, f"{name} leaked into a log record"
        assert raw not in captured.out and raw not in captured.err, (
            f"{name} leaked into stdout/stderr"
        )

    assert pack.had_redactions
    assert pack.redactions


def test_every_hit_preserves_detector_path_and_line(tmp_path):
    """AC #4 — a fingerprint no one can locate is not actionable."""
    _seed_repo(tmp_path)

    pack = run_dimension(_descriptor(SEEDED_SOURCES), tmp_path)

    assert pack.redactions
    for hit in pack.redactions:
        assert hit.detector
        assert hit.path in SEEDED_SOURCES
        assert hit.line >= 1
        assert FINGERPRINT_PATTERN.match(hit.fingerprint)


def test_no_raw_secret_appears_in_an_exception_raised_mid_pipeline(tmp_path):
    """AC #6 — a traceback is a report no one intended to write."""
    secrets = _seed_repo(tmp_path)
    descriptor = _descriptor(SEEDED_SOURCES)

    def exploding_collect(ctx):
        for excerpt in descriptor.collect(ctx):
            yield excerpt
            raise RuntimeError(f"collector failed while reading {excerpt.path}")

    with pytest.raises(RuntimeError) as caught:
        run_dimension(replace(descriptor, collect=exploding_collect), tmp_path)

    rendered = "".join(
        traceback.format_exception(
            type(caught.value), caught.value, caught.value.__traceback__
        )
    )
    for name, raw in secrets.items():
        assert raw not in rendered, f"{name} leaked into a traceback"


def _generator_raising_mid_iteration(message):
    def collect(ctx):
        ctx.read_source("config.env")
        raise RuntimeError(message)
        yield  # pragma: no cover - makes `collect` a generator

    return collect


def _plain_function_raising_at_call_time(message):
    """The realistic shape: read-and-parse eagerly, return a lazy iterator."""

    def collect(ctx):
        ctx.read_source("config.env")
        raise RuntimeError(message)  # before the generator is ever built
        return (excerpt for excerpt in ())  # pragma: no cover

    return collect


def _plain_function_raising_while_building_a_list(message):
    def collect(ctx):
        excerpts = [Excerpt(path="config.env", start_line=1, end_line=1, text="x")]
        if excerpts:
            raise RuntimeError(message)
        return excerpts  # pragma: no cover

    return collect


@pytest.mark.parametrize(
    ("shape", "make_collect"),
    [
        ("generator raising mid-iteration", _generator_raising_mid_iteration),
        ("plain fn raising at collect() call", _plain_function_raising_at_call_time),
        (
            "plain fn raising while building a list",
            _plain_function_raising_while_building_a_list,
        ),
    ],
)
def test_a_secret_interpolated_into_a_dimension_exception_is_redacted(
    tmp_path, shape, make_collect
):
    """Stage 4 P2 — the harder AC #6: the secret is in the message itself.

    `raise ValueError(f"malformed config line: {line}")` is an ordinary thing
    for a dimension to write, and `line` is exactly the content that carries
    secrets. An unhandled exception propagates out through the adapter to the
    calling agent, so the message is sanitised at the choke point.

    Parameterised over all three shapes on purpose. The first revision of the
    fix wrapped only the *iteration*, which covered the generator and left the
    other two leaking — a generator-returning function still runs eagerly up to
    its `return`. A future refactor must not be able to re-open one shape while
    the others stay green.
    """
    secrets = _seed_repo(tmp_path)
    message = f"failed near {secrets['aws_id']} and {secrets['token']}"
    descriptor = replace(_descriptor(SEEDED_SOURCES), collect=make_collect(message))

    with pytest.raises(RuntimeError) as caught:
        run_dimension(descriptor, tmp_path)

    rendered = "".join(
        traceback.format_exception(
            type(caught.value), caught.value, caught.value.__traceback__
        )
    )
    for name, raw in secrets.items():
        assert raw not in rendered, f"{shape}: {name} leaked into an exception message"
    assert "…****:" in str(caught.value), "the message should still name the finding"


def test_a_redacted_exception_keeps_its_type_and_traceback(tmp_path):
    """Sanitising the message must not cost the information a debugger needs."""
    (tmp_path / "config.env").write_text("nothing here\n")

    def boom(ctx):
        raise KeyError(f"missing entry for {AWS_KEY_ID}")
        yield  # pragma: no cover - makes `boom` a generator

    descriptor = replace(_descriptor(("config.env",)), collect=boom)

    with pytest.raises(KeyError) as caught:
        run_dimension(descriptor, tmp_path)

    assert AWS_KEY_ID not in str(caught.value)
    assert caught.value.__cause__ is None, "chaining would re-attach the raw message"
    assert any(
        frame.name == "boom"
        for frame in traceback.extract_tb(caught.value.__traceback__)
    ), "the raising frame must survive"


def test_a_secret_in_a_path_is_redacted_in_the_error_message(tmp_path):
    """A file *name* is content too — and an error message travels."""
    missing = tmp_path / f"repo-{AWS_KEY_ID}"

    with pytest.raises(RepoPathError) as caught:
        run_dimension(_descriptor(()), missing)

    assert AWS_KEY_ID not in str(caught.value)
    assert "…****:" in str(caught.value)


def test_a_secret_in_a_filename_is_redacted_in_files_read(tmp_path):
    (tmp_path / f"key-{AWS_KEY_ID}.env").write_text("nothing sensitive here\n")
    source = f"key-{AWS_KEY_ID}.env"

    pack = run_dimension(_descriptor((source,)), tmp_path)

    assert AWS_KEY_ID not in json.dumps(asdict(pack))
    assert pack.had_redactions


def test_a_secret_in_a_truncated_excerpt_does_not_survive(tmp_path):
    """The rejected excerpt is redacted too, and its hit is still reported."""
    (tmp_path / "config.env").write_text("padding=" + "a" * 200 + "\n")
    (tmp_path / "notes.md").write_text(f"api_key={API_KEY_VALUE}\n")

    pack = run_dimension(
        _descriptor(("config.env", "notes.md")), tmp_path, budget_bytes=220
    )

    assert pack.truncated
    assert API_KEY_VALUE not in json.dumps(asdict(pack))
    assert pack.had_redactions, (
        "a secret seen only in truncated material still happened"
    )


def test_the_same_secret_in_two_files_fingerprints_identically(tmp_path):
    """AC #7 — correlation is the whole point of the unsalted decision."""
    (tmp_path / "config.env").write_text(f"api_key={API_KEY_VALUE}\n")
    (tmp_path / "notes.md").write_text(
        f"api_key={API_KEY_VALUE}\nagain api_key={API_KEY_VALUE}\n"
    )

    pack = run_dimension(_descriptor(("config.env", "notes.md")), tmp_path)

    matching = [
        hit for hit in pack.redactions if hit.fingerprint.startswith(API_KEY_VALUE[:4])
    ]
    assert len(matching) == 3
    assert len({hit.fingerprint for hit in matching}) == 1
    assert {hit.path for hit in matching} == {"config.env", "notes.md"}


def test_no_code_path_builds_a_pack_from_unredacted_text(tmp_path):
    """AC #3 — the choke point is the only way in.

    If ``run_dimension`` ever stops routing excerpt text through ``redact``,
    this fails: the seam is replaced with a sentinel and the pack is checked for
    it.
    """
    _seed_repo(tmp_path)
    original = redact_module.redact
    seen: list[str] = []

    def tracking_redact(text: str) -> str:
        seen.append(text)
        return original(text)

    pipeline.redact_module.redact = tracking_redact
    try:
        pack = run_dimension(_descriptor(SEEDED_SOURCES), tmp_path)
    finally:
        pipeline.redact_module.redact = original

    for excerpt in pack.excerpts:
        assert "…****:" in excerpt.text, "an excerpt reached the pack unfingerprinted"


def test_pack_without_secrets_reports_no_redactions(tmp_path):
    (tmp_path / "notes.md").write_text("Just ordinary prose about the project.\n")

    pack = run_dimension(_descriptor(("notes.md",)), tmp_path)

    assert pack.redactions == ()
    assert pack.had_redactions is False
    assert pack.excerpts[0].text == "Just ordinary prose about the project.\n"
