"""Evidence-layer secret redaction (NFR-010, DDR-0001).

Every string that leaves the engine passes through :func:`redact` (or
:func:`scan`, which additionally reports *what* was replaced). A detected secret
is replaced by a **non-reversible fingerprint** built from a masked prefix and a
hash prefix::

    FAKEfake9f2Ba7Qz1XcV8mNp  ->  FAKE…****:a3f9c2e18b04

Format, fixed by the HITL decision recorded in ``memory/decisions.md`` §
"Redaction fingerprint is unsalted": ``<first 4 chars>…****:<12 hex chars>`` of
an **unsalted** SHA-256 digest.

Why unsalted — and when to revisit
----------------------------------
Unsalted means the same raw value fingerprints identically everywhere, so a
reader can see "this one key appears in three files". It also means a
*low-entropy* secret (``changeme``, ``admin123``) is recoverable from its
fingerprint by dictionary search. That trade is accepted **only** because a
report stays inside the repository it describes: whoever can read the
fingerprint can already ``grep`` the raw value out of the same checkout, so
reversing it discloses nothing new.

**Revisit condition** — if reports ever start travelling outside the evaluated
repo (committed to a shared branch, attached to a ticket, pasted into a PR),
the reasoning above no longer holds and salting must be reconsidered. NFR-011's
first-write advisory is the standing mitigation. No salt is read from config,
from the environment, or from disk; this module reads nothing but its argument,
and a test asserts that.

Tuned toward over-redaction
---------------------------
Entropy-based detection *will* fire on hashes, UUIDs, minified assets and
base64 blobs. That is the intended direction: a false positive costs a reader
one confusing fingerprint, a false negative costs a credential.

The raw value is never stored. :class:`RedactionHit` carries the detector name,
the location and the fingerprint only — deliberately no ``value`` field, because
every such field is a leak waiting for a future serializer to find it. Nothing
here assigns a severity, score or verdict (FR-013).

Every pattern below is linear — no nested or adjacent unbounded quantifiers, and
every ``{n,m}`` is bounded — so no input can trigger catastrophic backtracking
(ReDoS). This module reads attacker-influenceable content.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Iterator

from .models import RedactionHit, RedactionResult

MASK_CHARS = 4
"""Characters of the raw value kept, so ``AKIA…`` still reads as an AWS key."""

HASH_CHARS = 12
"""Hex characters of the SHA-256 digest kept."""

_MIN_ENTROPY_BITS = 4.0
"""Shannon entropy (bits/char) above which a long token is treated as a secret.

Ordinary English prose and identifiers sit well below this; base64 key material
sits above it. Hex candidates use a lower bar because hex tops out at 4.0.
"""

_MIN_HEX_ENTROPY_BITS = 3.2

# --- Detectors -------------------------------------------------------------
#
# Expressed as data so the list is auditable at a glance. Each entry is
# (name, compiled pattern). Group "secret" — when present — narrows the redacted
# span to the value, so surrounding context ("apikey=") survives and the hit
# stays readable.

_PEM_BODY_LIMIT = 20_000

_DETECTORS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "private_key_pem",
        re.compile(
            r"-----BEGIN[ A-Z]{0,40}PRIVATE KEY-----"
            rf"[^-]{{0,{_PEM_BODY_LIMIT}}}"
            r"-----END[ A-Z]{0,40}PRIVATE KEY-----"
        ),
    ),
    (
        "aws_access_key_id",
        re.compile(
            r"\b(?:AKIA|ASIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ABIA|ACCA)[A-Z0-9]{16}\b"
        ),
    ),
    (
        "aws_secret_access_key",
        re.compile(
            r"(?i)aws_secret_access_key[\"']?\s*[:=]\s*[\"']?"
            r"(?P<secret>[A-Za-z0-9/+=]{40})"
        ),
    ),
    (
        "jwt",
        re.compile(
            r"\beyJ[A-Za-z0-9_-]{4,2000}\.[A-Za-z0-9_-]{4,2000}\.[A-Za-z0-9_-]{4,2000}"
        ),
    ),
    (
        "credential_assignment",
        re.compile(
            r"(?i)\b(?:api[_-]?key|apikey|secret[_-]?key|secret|token|password|passwd|"
            r"pwd|access[_-]?key|client[_-]?secret|auth[_-]?token|authorization)"
            r"[\"']?\s*[:=]\s*[\"']?"
            r"(?P<secret>[^\s\"',;)}\]]{3,200})"
            # The value must run to the end of its line — or to a closing quote,
            # a delimiter, or the start of a trailing comment. Without this,
            # ordinary prose ("…the secret: masked prefix + hash prefix…", which
            # is how this project's own docs are written, and this repo is its
            # own test fixture) fingerprints the next English word. Config and
            # code write credentials as `key=value` at end of line; prose does
            # not.
            #
            # `#` and `//` are in the terminator set because Stage 4 asked
            # whether `password=hunter2  # dev` was covered elsewhere: it was
            # not. A short, low-entropy password clears no entropy bar and has
            # no recognisable shape, so this detector is its *only* cover, and
            # the anchor had to admit the comment forms rather than rest on an
            # assumption. Residue, stated plainly: a value followed by further
            # prose on the same line and no comment marker is still missed here.
            r"(?=[\"']?[ \t]*(?:[\r\n;,)}\]]|\#|//|$))"
        ),
    ),
)

_ENTROPY_CANDIDATE = re.compile(r"[A-Za-z0-9+/=_-]{32,512}")
_HEX_CANDIDATE = re.compile(r"\b[0-9a-fA-F]{32,512}\b")

_PATHISH = re.compile(r"^[~/]|/[a-z]{1,20}/")
"""A long slash-bearing token that is plainly a filesystem path.

Applies to the *long-token* entropy rule only, and it exists for one reason: a
deep absolute path clears the 32-character entropy bar as a whole, and
fingerprinting the path would destroy the file location that makes a finding
actionable (NFR-010 requires the path to *survive*). T001's line-fidelity check
is what pinned it — `/home/<user>/…/easy-verifier-mcp` in an ordinary prose line
came back fingerprinted.

It is **not** a hole through which a secret escapes, because it exempts a span
from one rule, not from detection. The named detectors ignore it entirely
(`/home/user/keys/FAKEfake9f2Ba7Qz1XcV8mNp` still fingerprints), and
:data:`_KEY_MATERIAL_CANDIDATE` below is path-blind by design: it scans the
segments *between* the separators, so the last segment of `/etc/keys/aB3xK9m…`,
the token in a webhook URL path, and the password inside a
`postgres://user:pw@host` URI are each caught on their own.
"""

_KEY_MATERIAL_CANDIDATE = re.compile(r"[A-Za-z0-9_-]{12,512}")
"""A word-ish run, scanned per segment — the rule that makes paths and URIs safe.

Deliberately independent of any surrounding punctuation: `/`, `:`, `@` and `.`
are *not* in the class, so a path, a URL and a connection URI all decompose into
segments and each segment is judged alone. That is what closes the class of leak
where the credential is a path segment or a URI password — near the top of the
list of ways credentials actually escape a repository.

A segment qualifies as key material only if it mixes lower case, upper case and
digits and clears :data:`_MIN_SEGMENT_ENTROPY_BITS`. Mixed case *plus* digits is
what separates `pB4kQ9zXmR7tY2wE` from the identifiers and filenames that share
its length — `test_t004_redact` (no upper case), `RedactionDescriptor` (no
digit), `easy-verifier-mcp` (neither) are all left alone, which is what keeps
this project's own paths readable when the tool evaluates itself.
"""

_MIN_SEGMENT_ENTROPY_BITS = 3.0
"""Bar for a short segment. A 12-character string cannot exceed log2(12) ≈ 3.58,
so the long-token bar of 4.0 is unreachable here and would silently disable the
rule. 3.0 admits random-looking material and rejects the repetitive
(`Abc123Abc123` ≈ 2.58)."""

_KEY_MATERIAL_CLASSES = (
    re.compile(r"[a-z]"),
    re.compile(r"[A-Z]"),
    re.compile(r"[0-9]"),
)


def fingerprint(value: str) -> str:
    """Return the non-reversible fingerprint of ``value``.

    Unsalted SHA-256 by decision (see module docstring): stable across files and
    across runs, which is what lets a reader correlate occurrences.
    """
    digest = hashlib.sha256(value.encode("utf-8", "surrogatepass")).hexdigest()
    return f"{value[:MASK_CHARS]}…****:{digest[:HASH_CHARS]}"


def redact(text: str) -> str:
    """Return ``text`` with every detected secret replaced by a fingerprint.

    The signature T001 fixed, and the one every dimension is written against.
    Use :func:`scan` when the caller also needs to report *what* was replaced.
    """
    return scan(text).text


def scan(text: str) -> RedactionResult:
    """Redact ``text`` and report each replacement.

    Offsets on the returned hits are into the **original** ``text``, which is
    what makes them checkable against the source; replacement builds a new
    string left to right rather than mutating in place, so a length change can
    never invalidate a later span.
    """
    if not text:
        return RedactionResult(text=text, hits=())

    spans = _resolve_overlaps(_named_spans(text), _entropy_spans(text))
    if not spans:
        return RedactionResult(text=text, hits=())

    pieces: list[str] = []
    hits: list[RedactionHit] = []
    cursor = 0
    for start, end, detector in spans:
        raw = text[start:end]
        pieces.append(text[cursor:start])
        pieces.append(fingerprint(raw))
        hits.append(
            RedactionHit(
                detector=detector,
                fingerprint=fingerprint(raw),
                offset=start,
                line=text.count("\n", 0, start) + 1,
            )
        )
        cursor = end
    pieces.append(text[cursor:])

    return RedactionResult(text="".join(pieces), hits=tuple(hits))


def _named_spans(text: str) -> Iterator[tuple[int, int, str]]:
    """Yield ``(start, end, detector)`` for every named-pattern match."""
    for name, pattern in _DETECTORS:
        for match in pattern.finditer(text):
            if "secret" in pattern.groupindex:
                start, end = match.span("secret")
            else:
                start, end = match.span()
            if end > start:
                yield start, end, name


def _entropy_spans(text: str) -> Iterator[tuple[int, int, str]]:
    """Yield the catch-all entropy candidates — the deliberately noisy layer."""
    for match in _ENTROPY_CANDIDATE.finditer(text):
        if _PATHISH.search(match.group()):
            continue
        if _shannon_entropy(match.group()) >= _MIN_ENTROPY_BITS:
            yield match.start(), match.end(), "high_entropy_string"

    for match in _KEY_MATERIAL_CANDIDATE.finditer(text):
        segment = match.group()
        if not all(pattern.search(segment) for pattern in _KEY_MATERIAL_CLASSES):
            continue
        if _shannon_entropy(segment) >= _MIN_SEGMENT_ENTROPY_BITS:
            yield match.start(), match.end(), "key_material_segment"

    for match in _HEX_CANDIDATE.finditer(text):
        if _shannon_entropy(match.group()) >= _MIN_HEX_ENTROPY_BITS:
            yield match.start(), match.end(), "high_entropy_hex"


def _resolve_overlaps(
    named: Iterator[tuple[int, int, str]],
    entropy: Iterator[tuple[int, int, str]],
) -> list[tuple[int, int, str]]:
    """Choose one span per overlapping group; named detectors win outright.

    Named detectors are resolved first, and an entropy span is admitted only if
    it overlaps none of them. Otherwise an entropy candidate — which greedily
    swallows ``apikey=`` along with its value, since ``=`` and ``_`` are in its
    character class — would out-rank the specific detector purely by starting
    earlier, and the hit would lose the detector name that makes it readable.

    Within each layer the rule is earliest start, then longest, then detector
    name: deterministic, and never double-masking a span (which would corrupt
    the offsets of everything after it).
    """

    def _sweep(
        spans: list[tuple[int, int, str]], taken: list[tuple[int, int, str]]
    ) -> list[tuple[int, int, str]]:
        # Linear: both lists are traversed in order, so the cost stays
        # proportional to the number of matches even on a large excerpt.
        chosen: list[tuple[int, int, str]] = []
        reached = 0
        index = 0
        for start, end, detector in sorted(
            spans, key=lambda span: (span[0], -span[1], span[2])
        ):
            if start < reached:
                continue
            while index < len(taken) and taken[index][1] <= start:
                index += 1
            if index < len(taken) and taken[index][0] < end:
                continue
            chosen.append((start, end, detector))
            reached = end
        return chosen

    named_spans = _sweep(list(named), [])
    return sorted(named_spans + _sweep(list(entropy), named_spans))


def _shannon_entropy(value: str) -> float:
    """Bits of entropy per character. 0.0 for the empty string."""
    if not value:
        return 0.0
    length = len(value)
    return -sum(
        (count / length) * math.log2(count / length)
        for count in _char_counts(value).values()
    )


def _char_counts(value: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for char in value:
        counts[char] = counts.get(char, 0) + 1
    return counts
