"""Finding schema + `validate_findings` — the last gate before a report.

An unevidenced, confident-sounding claim from the calling LLM agent must not
be publishable. This module is that gate (NFR-004: enforcement lives in
validation, not caller convention). It never writes anything to disk — it
only validates and, on success, returns a structured result for a renderer
(T013) to consume.

Canonical forms (documented, not negotiable):
- ``evidence_ref``: ``"path:start_line-end_line"`` — matches
  :attr:`easy_verifier.core.models.Excerpt.ref` exactly (1-indexed,
  inclusive). A lone line number or any other shape is rejected.
- ``confidence``: one of :data:`CONFIDENCE_DOMAIN`. An empty string or
  ``None`` is not a confidence value.

Decided, undocumented-elsewhere edge cases (FR-015/FR-015a):
- An empty findings list is **accepted** — it is a real result ("no findings
  were made"), not a failure.
- Duplicate findings (identical content) are accepted as-is; this module does
  not deduplicate or flag them.
- Unknown fields on a finding are rejected, naming the field — a caller
  mistake should surface immediately, not be silently dropped.
- A dangling ref into a pack that was truncated gets a specific error saying
  so, because the caller may have seen that excerpt before truncation and
  otherwise loops trying to re-cite it.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from easy_verifier.core.models import EvidencePack

CONFIDENCE_DOMAIN = ("low", "medium", "high")
"""The documented confidence domain (FR-015). No numeric scale — this engine
renders no verdict, so confidence is a coarse, caller-supplied qualifier."""

MAX_FINDINGS = 500
"""Bound on a single submission, so parsing stays O(findings) and bounded —
not a claim about report quality."""

_ALLOWED_FIELDS = frozenset(
    {"dimension", "title", "detail", "evidence_ref", "confidence", "suggestion"}
)
_REQUIRED_STRING_FIELDS = ("dimension", "title", "detail")

# Canonical evidence_ref: "path:start-end", 1-indexed inclusive, matching
# Excerpt.ref. Path may itself contain colons in theory, so anchor on the
# trailing "<digits>-<digits>" rather than assuming the path has none.
_EVIDENCE_REF_PATTERN = re.compile(r"^(?P<path>.+):(?P<start>\d+)-(?P<end>\d+)$")


@dataclass(frozen=True)
class Finding:
    """One validated, evidence-backed finding (FR-014, FR-023)."""

    dimension: str
    title: str
    detail: str
    evidence_ref: str
    confidence: str
    suggestion: str | None = None
    """Advisory text only (FR-024) — never written, patched, or executed by
    anything in this engine, including this module."""


@dataclass(frozen=True)
class FindingError:
    """One rejection reason, tied to the finding and field that caused it."""

    index: int
    """Position in the submitted list, or -1 for a submission-level error."""

    title: str | None
    field: str
    reason: str

    def __str__(self) -> str:
        return f"finding[{self.index}] ({self.title!r}) [{self.field}]: {self.reason}"


class ValidationError(Exception):
    """Raised with **every** offending field across **every** finding
    (AC #8) — the caller is an LLM agent; a one-error-per-round-trip loop
    burns its context for no reason."""

    def __init__(self, errors: list[FindingError]) -> None:
        self.errors: tuple[FindingError, ...] = tuple(errors)
        super().__init__(
            f"{len(self.errors)} finding(s) failed validation: "
            + "; ".join(str(e) for e in self.errors)
        )


@dataclass(frozen=True)
class ValidationResult:
    """The structured, accepted result. Rendering is out of scope (T013)."""

    findings: tuple[Finding, ...]
    by_dimension: dict[str, tuple[Finding, ...]]
    """FR-018a: a single submission can span several dimensions."""


def validate_findings(
    findings: list[dict[str, Any]] | str | bytes, packs: dict[str, EvidencePack]
) -> ValidationResult:
    """Validate `findings` against the evidence in `packs`.

    Raises :class:`ValidationError` naming every offending finding and field
    if any check fails — nothing is partially accepted (AC #9: the caller
    must not proceed to write a report on a raised error).
    """
    findings = _parse_payload(findings)

    if len(findings) > MAX_FINDINGS:
        raise ValidationError(
            [
                FindingError(
                    -1,
                    None,
                    "<payload>",
                    f"submission has {len(findings)} findings, exceeding the "
                    f"{MAX_FINDINGS} limit",
                )
            ]
        )

    errors: list[FindingError] = []
    parsed: list[Finding] = []

    for index, raw in enumerate(findings):
        finding, finding_errors = _validate_one(index, raw, packs)
        errors.extend(finding_errors)
        if finding is not None:
            parsed.append(finding)

    if errors:
        raise ValidationError(errors)

    by_dimension: dict[str, list[Finding]] = {}
    for f in parsed:
        by_dimension.setdefault(f.dimension, []).append(f)

    return ValidationResult(
        findings=tuple(parsed),
        by_dimension={k: tuple(v) for k, v in by_dimension.items()},
    )


def _parse_payload(
    findings: list[dict[str, Any]] | str | bytes,
) -> list[dict[str, Any]]:
    if isinstance(findings, (str, bytes)):
        try:
            findings = json.loads(findings)
        except json.JSONDecodeError as exc:
            raise ValidationError(
                [
                    FindingError(
                        -1,
                        None,
                        "<payload>",
                        f"malformed JSON at line {exc.lineno}, column "
                        f"{exc.colno} (char {exc.pos}): {exc.msg}",
                    )
                ]
            ) from exc

    if not isinstance(findings, list):
        raise ValidationError(
            [
                FindingError(
                    -1,
                    None,
                    "<payload>",
                    "findings must be a JSON array of finding objects",
                )
            ]
        )
    return findings


def _validate_one(
    index: int, raw: Any, packs: dict[str, EvidencePack]
) -> tuple[Finding | None, list[FindingError]]:
    errors: list[FindingError] = []

    if not isinstance(raw, dict):
        return None, [
            FindingError(index, None, "<finding>", "finding must be a JSON object")
        ]

    title = raw.get("title") if isinstance(raw.get("title"), str) else None

    unknown = set(raw) - _ALLOWED_FIELDS
    if unknown:
        errors.append(
            FindingError(
                index,
                title,
                "<unknown>",
                f"unknown field(s): {', '.join(sorted(unknown))}",
            )
        )

    for field_name in _REQUIRED_STRING_FIELDS:
        value = raw.get(field_name)
        if not isinstance(value, str) or not value:
            errors.append(
                FindingError(
                    index, title, field_name, f"missing required field '{field_name}'"
                )
            )

    evidence_ref = raw.get("evidence_ref")
    has_evidence = isinstance(evidence_ref, str) and evidence_ref != ""
    if not has_evidence:
        errors.append(
            FindingError(index, title, "evidence_ref", "missing evidence reference")
        )

    confidence = raw.get("confidence")
    has_confidence = confidence in CONFIDENCE_DOMAIN
    if not has_confidence:
        if confidence is None or confidence == "":
            errors.append(
                FindingError(index, title, "confidence", "missing confidence value")
            )
        else:
            errors.append(
                FindingError(
                    index,
                    title,
                    "confidence",
                    f"confidence {confidence!r} is not in the allowed domain "
                    f"{CONFIDENCE_DOMAIN}",
                )
            )

    suggestion = raw.get("suggestion")
    if suggestion is not None and not isinstance(suggestion, str):
        errors.append(
            FindingError(
                index, title, "suggestion", "suggestion must be a string when present"
            )
        )

    # A malformed finding cannot safely resolve a dimension/ref, so stop here
    # rather than risk a confusing secondary error on top of a primary one.
    if errors:
        return None, errors

    dimension = raw["dimension"]

    match = _EVIDENCE_REF_PATTERN.match(evidence_ref)
    if not match:
        return None, [
            FindingError(
                index,
                title,
                "evidence_ref",
                f"evidence_ref {evidence_ref!r} is not in the canonical "
                "'path:start-end' form",
            )
        ]

    pack = packs.get(dimension)
    if pack is None:
        return None, [
            FindingError(
                index,
                title,
                "dimension",
                f"dimension {dimension!r} was not run; no evidence pack exists for it",
            )
        ]

    if not any(excerpt.ref == evidence_ref for excerpt in pack.excerpts):
        if pack.truncated:
            reason = (
                f"evidence_ref {evidence_ref!r} not found in the {dimension!r} "
                "pack — the pack was truncated by the evidence budget, so this "
                "excerpt may have existed before truncation and is no longer "
                "available; re-cite a surviving excerpt instead"
            )
        else:
            reason = (
                f"evidence_ref {evidence_ref!r} not found in the {dimension!r} pack"
            )
        return None, [FindingError(index, title, "evidence_ref", reason)]

    return (
        Finding(
            dimension=dimension,
            title=raw["title"],
            detail=raw["detail"],
            evidence_ref=evidence_ref,
            confidence=confidence,
            suggestion=suggestion,
        ),
        [],
    )
