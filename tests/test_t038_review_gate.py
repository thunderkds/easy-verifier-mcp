"""T038: user review gate for local registry entries (good / improve / reject).

A local entry starts ``pending`` and scores immediately (G4). The MCP ``score``
tool lists each unreviewed pending entry once under ``needs_input.review``; the
agent relays the user's answer as ``agent_input.reviews``. ``good`` approves
(tag ``agent-researched (user-approved)``), ``improve`` keeps it pending and
returns the comment through the reference gate, ``reject`` deletes it and
leaves a remembered record under which the dependent metrics abstain until a
replacement arrives (Supervisor decision, option A, 2026-09-29).

Every guard is pinned from both sides where a one-sided test could pass for
the wrong reason.
"""

from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path

import pytest

from easy_verifier.adapters import mcp_server
from easy_verifier.core import gate
from easy_verifier.core import registry as reg
from easy_verifier.core.report import write_report
from easy_verifier.core.roles import (
    GENERIC_PATTERNS,
    RoleInputError,
    _registry,
    validate_agent_input,
)
from easy_verifier.core.score import score_repository
from easy_verifier.core.synthesis import combined_pack
from easy_verifier.dimensions import dimension_names

KOTEST = "https://kotest.io/docs/assertions/assertions.html"
ZIG = "https://ziglang.org/documentation/0.13.0/#Zig-Test"
APPROVED = "agent-researched (user-approved)"
UNREVIEWED = "agent-researched (unreviewed)"


def kotlin_entry(**overrides) -> dict:
    item = {
        "language": "kotlin",
        "field": "assertions",
        "value": ["shouldBe"],
        "citation_url": KOTEST,
        "source_tag": "agent-researched",
    }
    item.update(overrides)
    return item


def zig_entries(assertion: str = "expect(") -> list[dict]:
    """A local-only language: no curated data exists for any of its fields."""
    fields = {
        "manifests": ["build.zig"],
        "source_extensions": [".zig"],
        "test_name_patterns": ["?*_test.zig"],
        "test_declarations": ['test "'],
        "assertions": [assertion],
    }
    return [
        {
            "language": "zig",
            "field": field,
            "value": value,
            "citation_url": ZIG,
            "source_tag": "agent-researched",
        }
        for field, value in fields.items()
    ]


@pytest.fixture
def sot(tmp_path, monkeypatch) -> Path:
    root = tmp_path / "machine-a" / "sot"
    monkeypatch.setenv("EASY_VERIFIER_SOT", str(root))
    _registry.cache_clear()
    return root


@pytest.fixture
def kotlin_repo(tmp_path) -> Path:
    repo = tmp_path / "repo"
    (repo / "src/test/kotlin").mkdir(parents=True)
    (repo / "build.gradle.kts").write_text('plugins { kotlin("jvm") }\n')
    (repo / "src/test/kotlin/FooTest.kt").write_text(
        "class FooTest {\n  @Test fun a() { x shouldBe 1 }\n}\n"
    )
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    return repo


@pytest.fixture
def zig_repo(tmp_path) -> Path:
    repo = tmp_path / "zigrepo"
    (repo / "src").mkdir(parents=True)
    (repo / "tests").mkdir()
    (repo / "build.zig").write_text("const std = @import(\"std\");\n")
    (repo / "src/main.zig").write_text(
        "pub fn add(a: i32, b: i32) i32 {\n  return a + b;\n}\n"
    )
    (repo / "tests/main_test.zig").write_text(
        'test "add" {\n  try expect(add(1, 2) == 3);\n}\n'
    )
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    return repo


def mcp(repo: Path, **agent_input) -> dict:
    return mcp_server.score(repo=str(repo), agent_input=agent_input or None)


def review_ids(payload: dict) -> list[str]:
    review = payload.get("needs_input", {}).get("review")
    return [item["entry_id"] for item in review["entries"]] if review else []


def saved(sot: Path, name: str) -> dict:
    return tomllib.loads((sot / f"{name}.toml").read_text())


def metric(result, dimension: str, name: str):
    (found,) = [
        m for m in result.metrics if m.dimension == dimension and m.name == name
    ]
    return found


def rating_input(result, dimension: str, name: str) -> dict:
    (rating,) = [r for r in result.to_dict()["ratings"] if r["dimension"] == dimension]
    (item,) = [i for i in rating["inputs"] if i["metric_name"] == name]
    return item


# --------------------------------------------------------------------------
# AC 1: statuses; new entries start pending
# --------------------------------------------------------------------------


def test_new_local_entry_starts_pending_in_the_file(sot, kotlin_repo):
    score_repository(kotlin_repo, agent_input={"registry_entries": [kotlin_entry()]})
    (item,) = saved(sot, "kotlin")["assertions"]
    assert item["review_status"] == "pending"
    assert item["source_tag"] == UNREVIEWED


def test_file_without_status_loads_pending_and_bad_status_is_rejected(sot):
    sot.mkdir(parents=True)
    body = (
        '[[assertions]]\nvalue = ["shouldBe"]\n'
        f'citation_url = "{KOTEST}"\nsource_tag = "{UNREVIEWED}"\n'
    )
    (sot / "kotlin.toml").write_text(body)
    local = reg.load_registry(sot, known_roles=GENERIC_PATTERNS, local=True)
    (cited,) = local.languages["kotlin"].fields["assertions"]
    assert cited.review_status == "pending"

    (sot / "kotlin.toml").write_text(body + 'review_status = "maybe"\n')
    local = reg.load_registry(sot, known_roles=GENERIC_PATTERNS, local=True)
    assert "kotlin" not in local.languages
    assert any("review_status" in warning for warning in local.warnings)


def test_curated_entries_carry_no_review_status():
    kotlin = _registry().languages["kotlin"]
    assert {c.review_status for c in kotlin.fields["assertions"]} == {None}


def test_pending_entry_scores_immediately(sot, kotlin_repo):
    result = score_repository(
        kotlin_repo, agent_input={"registry_entries": [kotlin_entry()]}
    )
    assert metric(result, "test-strategy", "assertions_observed").outcome == 1


# --------------------------------------------------------------------------
# AC 2: needs_input.review lists pending entries once, value + link
# --------------------------------------------------------------------------


def test_mcp_lists_each_pending_entry_once_with_value_and_link(sot, kotlin_repo):
    other = kotlin_entry(value=["shouldContain"])
    payload = mcp(kotlin_repo, registry_entries=[kotlin_entry(), other, kotlin_entry()])
    review = payload["needs_input"]["review"]
    assert [item["value"] for item in review["entries"]] == [
        ["shouldBe"],
        ["shouldContain"],
    ]
    first = review["entries"][0]
    assert first["language"] == "kotlin"
    assert first["field"] == "assertions"
    assert first["citation_url"] == KOTEST
    assert first["source_tag"] == UNREVIEWED
    assert first["entry_id"].startswith("kotlin.assertions.")
    assert review["omitted"] == 0
    assert review["instructions"] == gate.REVIEW_INSTRUCTIONS
    assert len(set(review_ids(payload))) == 2


def test_no_pending_entry_means_no_review_key(sot, kotlin_repo):
    assert "review" not in mcp(kotlin_repo).get("needs_input", {})


def test_review_is_mcp_only(sot, kotlin_repo):
    result = score_repository(
        kotlin_repo, agent_input={"registry_entries": [kotlin_entry()]}
    )
    assert result.review is None
    gated = score_repository(kotlin_repo, detect_gates=True)
    assert gated.review is not None
    assert "review" not in gated.to_dict()
    assert '"instructions"' not in gated.serialize()


def test_review_list_is_capped_and_overflow_counted(sot, kotlin_repo):
    items = [kotlin_entry(value=[f"should{chr(65 + i)}x"]) for i in range(20)]
    items += [kotlin_entry(value=["shouldZz"], field="test_declarations")]
    score_repository(kotlin_repo, agent_input={"registry_entries": items[:20]})
    score_repository(kotlin_repo, agent_input={"registry_entries": items[20:]})
    review = score_repository(kotlin_repo, detect_gates=True).review
    assert len(review["entries"]) == gate.MAX_REVIEW_ENTRIES == 20
    assert review["omitted"] == 1


def test_instructions_name_all_three_answers():
    text = gate.REVIEW_INSTRUCTIONS
    phrases = ("once", "good", "improve", "reject", "comment", "agent_input.reviews")
    for phrase in phrases:
        assert phrase in text


def test_score_tool_description_mentions_review_gate():
    tool = mcp_server.mcp._tool_manager.get_tool("score")
    assert "needs_input.review" in tool.description
    assert "reviews" in tool.description


# --------------------------------------------------------------------------
# AC 3 + Success criterion 1: good -> approved, tag updated
# --------------------------------------------------------------------------


def test_good_approves_and_retags_everywhere(sot, kotlin_repo):
    (entry_id,) = review_ids(mcp(kotlin_repo, registry_entries=[kotlin_entry()]))
    result = score_repository(
        kotlin_repo, detect_gates=True, agent_input={"reviews": {entry_id: "good"}}
    )
    (item,) = saved(sot, "kotlin")["assertions"]
    assert item["review_status"] == "approved"
    assert item["source_tag"] == APPROVED
    tagged = rating_input(result, "test-strategy", "assertion_density_per_test")
    assert tagged["source_tag"] == APPROVED
    assert result.to_dict()["registry_entries"][0]["source_tag"] == APPROVED
    assert result.review is None  # AC 4: never asked again
    # Still used: approval changes no number (weights by status out of scope).
    assert metric(result, "test-strategy", "assertions_observed").outcome == 1


def test_good_on_user_supplied_keeps_its_tag(sot, kotlin_repo):
    supplied = kotlin_entry(source_tag="user-supplied")
    (entry_id,) = review_ids(mcp(kotlin_repo, registry_entries=[supplied]))
    mcp(kotlin_repo, reviews={entry_id: {"answer": "good"}})
    (item,) = saved(sot, "kotlin")["assertions"]
    assert (item["review_status"], item["source_tag"]) == ("approved", "user-supplied")


# --------------------------------------------------------------------------
# AC 3: improve -> stays pending, comment in the next reference gate
# --------------------------------------------------------------------------


def test_improve_keeps_scoring_and_returns_comment_in_reference_gate(sot, kotlin_repo):
    (entry_id,) = review_ids(mcp(kotlin_repo, registry_entries=[kotlin_entry()]))
    comment = "use the matcher list page, not the overview"
    result = score_repository(
        kotlin_repo,
        detect_gates=True,
        agent_input={"reviews": {entry_id: {"answer": "improve", "comment": comment}}},
    )
    (item,) = saved(sot, "kotlin")["assertions"]
    assert item["review_status"] == "pending"
    assert (item["review_comment"], item["improve_rounds"]) == (comment, 1)
    assert metric(result, "test-strategy", "assertions_observed").outcome == 1
    assert result.review is None  # reviewed: never asked again
    (request,) = [
        r
        for r in result.reference["requests"]
        if r.get("language") == "kotlin" and r["field"] == "assertions"
    ]
    assert request["improve"] == {
        "value": ["shouldBe"],
        "comment": comment,
        "rounds": 1,
    }
    assert "ask_user" not in request


def test_replacement_supersedes_improved_entry_and_second_round_asks_user(
    sot, kotlin_repo
):
    (first,) = review_ids(mcp(kotlin_repo, registry_entries=[kotlin_entry()]))
    mcp(kotlin_repo, reviews={first: {"answer": "improve", "comment": "wrong page"}})
    replacement = kotlin_entry(value=["shouldBeEqual"])
    (second,) = review_ids(mcp(kotlin_repo, registry_entries=[replacement]))
    assert second != first
    (item,) = saved(sot, "kotlin")["assertions"]  # the improved one is gone
    assert item["value"] == ["shouldBeEqual"]
    assert item["improve_rounds"] == 1
    assert "review_comment" not in item

    result = score_repository(
        kotlin_repo,
        detect_gates=True,
        agent_input={"reviews": {second: {"answer": "improve", "comment": "still"}}},
    )
    (request,) = [
        r
        for r in result.reference["requests"]
        if r.get("language") == "kotlin" and r["field"] == "assertions"
    ]
    assert request["improve"]["rounds"] == 2
    assert request["ask_user"] is True
    assert "ask the user" in gate.REFERENCE_INSTRUCTIONS


# --------------------------------------------------------------------------
# AC 3 + Success criterion 2: reject -> deleted, dependent rule abstains
# --------------------------------------------------------------------------


def _reject_zig_assertion(repo: Path) -> dict:
    payload = mcp(repo, registry_entries=zig_entries())
    (entry_id,) = [i for i in review_ids(payload) if i.startswith("zig.assertions.")]
    return mcp(repo, reviews={entry_id: "reject"})


def test_reject_removes_entry_and_dependent_rule_abstains(sot, zig_repo):
    pending = score_repository(
        zig_repo, agent_input={"registry_entries": zig_entries()}
    )
    assert metric(pending, "test-strategy", "assertions_observed").outcome == 1
    assert not metric(pending, "test-strategy", "assertion_density_per_test").abstained

    _reject_zig_assertion(zig_repo)
    assert "assertions" not in _registry().languages["zig"].fields
    (record,) = saved(sot, "zig")["assertions"]
    assert record["review_status"] == "rejected"

    after = score_repository(zig_repo)
    observed = metric(after, "test-strategy", "assertions_observed")
    assert observed.abstained
    assert "zig.assertions" in observed.outcome.reason
    assert "rejected by the user" in observed.outcome.reason
    (rating,) = [r for r in after.ratings if r.dimension == "test-strategy"]
    unavailable = dict(getattr(rating, "unavailable_metrics", ()))
    assert "zig.assertions" in unavailable["assertion_density_per_test"]
    # Unrelated metrics still compute.
    assert not metric(after, "test-strategy", "test_to_source_ratio").abstained


def test_rejection_does_not_touch_a_repo_without_that_language(
    sot, zig_repo, kotlin_repo
):
    _reject_zig_assertion(zig_repo)
    result = score_repository(kotlin_repo)
    assert not metric(result, "test-strategy", "assertions_observed").abstained


def test_rejection_with_other_data_for_the_field_does_not_abstain(sot, kotlin_repo):
    (entry_id,) = review_ids(mcp(kotlin_repo, registry_entries=[kotlin_entry()]))
    mcp(kotlin_repo, reviews={entry_id: "reject"})
    result = score_repository(kotlin_repo)  # curated kotlin assertions remain
    observed = metric(result, "test-strategy", "assertions_observed")
    assert not observed.abstained
    assert observed.outcome == 0  # the rejected shouldBe is no longer used


def test_rejected_field_is_reasked_by_reference_gate(sot, zig_repo):
    payload = _reject_zig_assertion(zig_repo)
    (request,) = [
        r
        for r in payload["needs_input"]["reference"]["requests"]
        if r.get("language") == "zig" and r["field"] == "assertions"
    ]
    assert request["rejected"] == ["expect("]


def test_new_entry_clears_the_rejection_record(sot, zig_repo):
    _reject_zig_assertion(zig_repo)
    replacement = [e for e in zig_entries("expect(") if e["field"] == "assertions"]
    replacement[0]["value"] = ["try expect("]
    result = score_repository(
        zig_repo, agent_input={"registry_entries": replacement}
    )
    (item,) = saved(sot, "zig")["assertions"]
    assert (item["value"], item["review_status"]) == (["try expect("], "pending")
    assert not metric(result, "test-strategy", "assertions_observed").abstained


def test_reject_and_replacement_in_one_call_leave_only_the_replacement(
    sot, kotlin_repo
):
    (entry_id,) = review_ids(mcp(kotlin_repo, registry_entries=[kotlin_entry()]))
    replacement = kotlin_entry(value=["shouldBeEqual"])
    mcp(kotlin_repo, reviews={entry_id: "reject"}, registry_entries=[replacement])
    (item,) = saved(sot, "kotlin")["assertions"]  # answers apply first
    assert (item["value"], item["review_status"]) == (["shouldBeEqual"], "pending")


def test_rejection_record_replays_byte_equal_on_empty_machine(
    sot, zig_repo, tmp_path, monkeypatch
):
    _reject_zig_assertion(zig_repo)
    original = score_repository(zig_repo)
    embedded = original.to_dict()["registry_entries"]
    assert {
        "language": "zig",
        "field": "assertions",
        "value": ["expect("],
        "citation_url": ZIG,
        "source_tag": UNREVIEWED,
        "review_status": "rejected",
    } in embedded

    monkeypatch.setenv("EASY_VERIFIER_SOT", str(tmp_path / "machine-b"))
    _registry.cache_clear()
    replayed = score_repository(zig_repo, agent_input={"registry_entries": embedded})
    assert replayed.serialize() == original.serialize()


def test_report_marks_the_rejection_record_as_not_used(sot, zig_repo):
    _reject_zig_assertion(zig_repo)
    packs = combined_pack(dimension_names(), repo_path=zig_repo, scope="project")
    written = write_report([], packs, zig_repo)
    document = Path(written.absolute_path).read_text()
    marker = "rejected by the user: not used"
    assert document.count(marker) == 1  # only the assertions record
    assert '&quot;review_status&quot;: &quot;rejected&quot;' in document


def test_approved_entry_replays_as_approved(sot, kotlin_repo, tmp_path, monkeypatch):
    (entry_id,) = review_ids(mcp(kotlin_repo, registry_entries=[kotlin_entry()]))
    score_repository(kotlin_repo, agent_input={"reviews": {entry_id: "good"}})
    original = score_repository(kotlin_repo)
    embedded = original.to_dict()["registry_entries"]

    monkeypatch.setenv("EASY_VERIFIER_SOT", str(tmp_path / "machine-b"))
    _registry.cache_clear()
    replayed = score_repository(
        kotlin_repo, detect_gates=True, agent_input={"registry_entries": embedded}
    )
    assert replayed.serialize() == original.serialize()
    assert replayed.review is None  # arrived approved: nothing to ask


def test_replay_status_key_accepts_rejected_only():
    ok = dict(kotlin_entry(), review_status="rejected")
    assert reg.parse_local_entries([ok], GENERIC_PATTERNS)[1] == []
    for bad in ("approved", "pending", 1):
        errors = reg.parse_local_entries(
            [dict(ok, review_status=bad)], GENERIC_PATTERNS
        )[1]
        assert errors and "review_status" in errors[0], bad


# --------------------------------------------------------------------------
# AC 4: a reviewed entry is never asked again
# --------------------------------------------------------------------------


@pytest.mark.parametrize("answer", ["good", "improve", "reject"])
def test_reviewed_entry_never_asked_again_even_if_resubmitted(
    sot, kotlin_repo, answer
):
    (entry_id,) = review_ids(mcp(kotlin_repo, registry_entries=[kotlin_entry()]))
    mcp(kotlin_repo, reviews={entry_id: answer})
    again = mcp(kotlin_repo, registry_entries=[kotlin_entry()])
    assert entry_id not in review_ids(again)
    statuses = [item["review_status"] for item in saved(sot, "kotlin")["assertions"]]
    expected = {"good": "approved", "improve": "pending", "reject": "rejected"}
    assert statuses == [expected[answer]]


def test_second_answer_for_a_reviewed_entry_is_ignored_with_note(sot, kotlin_repo):
    (entry_id,) = review_ids(mcp(kotlin_repo, registry_entries=[kotlin_entry()]))
    mcp(kotlin_repo, reviews={entry_id: "good"})
    payload = mcp(kotlin_repo, reviews={entry_id: "reject"})
    (item,) = saved(sot, "kotlin")["assertions"]
    assert item["review_status"] == "approved"
    assert any("already reviewed" in note for note in payload["registry_notes"])


# --------------------------------------------------------------------------
# Edge cases and validation
# --------------------------------------------------------------------------


def test_unknown_entry_id_is_ignored_with_warning(sot, kotlin_repo):
    result = score_repository(
        kotlin_repo, agent_input={"reviews": {"kotlin.assertions.0123456789ab": "good"}}
    )
    assert any(
        "kotlin.assertions.0123456789ab" in note and "ignored" in note
        for note in result.registry_notes
    )
    assert "registry_notes" not in result.to_dict()  # never in the parity payload


def test_valid_review_shapes_accepted(kotlin_repo):
    document = {
        "reviews": {
            "a.assertions.0123456789ab": "good",
            "b.assertions.0123456789ab": {"answer": "improve", "comment": "x"},
            "c.assertions.0123456789ab": {"answer": "reject"},
        }
    }
    assert validate_agent_input(document, kotlin_repo) == {}


@pytest.mark.parametrize(
    ("reviews", "message"),
    [
        ([], "reviews: must be an object"),
        ({"a.b.0123456789ab": "fine"}, "good, improve or reject"),
        ({"a.b.0123456789ab": {"answer": "good", "extra": 1}}, "unknown key extra"),
        ({"a.b.0123456789ab": {"answer": "improve", "comment": 5}}, "comment"),
        ({"a.b.0123456789ab": {"comment": "x"}}, "good, improve or reject"),
        ({"x" * 201: "good"}, "entry id"),
        ({"a.b.0123456789ab": {"answer": "improve", "comment": "x" * 501}}, "500"),
    ],
)
def test_invalid_reviews_rejected(kotlin_repo, reviews, message):
    with pytest.raises(RoleInputError, match="reviews") as caught:
        validate_agent_input({"reviews": reviews}, kotlin_repo)
    assert message in str(caught.value)


def test_too_many_reviews_rejected(kotlin_repo):
    ok = {f"a.b.{i:012x}": "good" for i in range(reg.MAX_REVIEWS)}
    assert validate_agent_input({"reviews": ok}, kotlin_repo) == {}
    over = dict(ok, **{"a.b.ffffffffffff": "good"})
    with pytest.raises(RoleInputError, match=f"at most {reg.MAX_REVIEWS}"):
        validate_agent_input({"reviews": over}, kotlin_repo)


def test_secret_shaped_comment_refused(kotlin_repo):
    secret = "AKIA" + "Q" * 16  # assembled at runtime: never a literal shape
    with pytest.raises(RoleInputError, match="secret"):
        validate_agent_input(
            {"reviews": {"a.b.0123456789ab": {"answer": "improve", "comment": secret}}},
            kotlin_repo,
        )


def test_unwritable_layer_reports_reviews_not_saved(sot, kotlin_repo):
    (entry_id,) = review_ids(mcp(kotlin_repo, registry_entries=[kotlin_entry()]))
    sot.chmod(0o500)
    try:
        payload = mcp(kotlin_repo, reviews={entry_id: "good"})
    finally:
        sot.chmod(0o700)
    (item,) = saved(sot, "kotlin")["assertions"]
    assert item["review_status"] == "pending"
    assert any("reviews cannot be saved" in n for n in payload["registry_notes"])


# --------------------------------------------------------------------------
# Stage 4 P1: every string written to a local file must stay valid TOML
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "comment",
    ["wrong page \U0001f600", "tab\there, del\x7f, nul\x00, é,   end"],
)
def test_improve_comment_round_trips_through_the_toml_file(sot, kotlin_repo, comment):
    (entry_id,) = review_ids(mcp(kotlin_repo, registry_entries=[kotlin_entry()]))
    mcp(kotlin_repo, reviews={entry_id: {"answer": "improve", "comment": comment}})
    (item,) = saved(sot, "kotlin")["assertions"]  # tomllib parses the file
    assert item["review_comment"] == comment
    # The entry still loads, and later writes to the same file still work.
    local = reg.load_registry(sot, known_roles=GENERIC_PATTERNS, local=True)
    assert local.warnings == ()
    mcp(kotlin_repo, registry_entries=[kotlin_entry(value=["shouldBeEqual"])])
    assert saved(sot, "kotlin")["assertions"][0]["value"] == ["shouldBeEqual"]


def test_non_ascii_value_round_trips_through_the_toml_file(sot, kotlin_repo):
    value = "should\U0001f600"
    score_repository(
        kotlin_repo, agent_input={"registry_entries": [kotlin_entry(value=[value])]}
    )
    (item,) = saved(sot, "kotlin")["assertions"]
    assert item["value"] == [value]


def test_ascii_file_bytes_are_unchanged_by_the_encoder(tmp_path):
    entries, _ = reg.parse_local_entries(
        [kotlin_entry(value=['say "hi"'])], GENERIC_PATTERNS
    )
    reg.save_local_entries(entries, tmp_path, known_roles=GENERIC_PATTERNS)
    text = (tmp_path / "kotlin.toml").read_text()
    assert 'value = ["say \\"hi\\""]' in text


def test_lone_surrogate_in_comment_is_a_validation_error(kotlin_repo):
    review = {"answer": "improve", "comment": "bad \ud800 half"}
    with pytest.raises(RoleInputError, match="comment") as caught:
        validate_agent_input({"reviews": {"a.b.0123456789ab": review}}, kotlin_repo)
    assert "surrogate" in str(caught.value)
    ok = {"answer": "improve", "comment": "fine \U0001f600"}
    document = {"reviews": {"a.b.0123456789ab": ok}}
    assert validate_agent_input(document, kotlin_repo) == {}


def test_lone_surrogate_in_entry_value_is_a_validation_error(kotlin_repo):
    errors = reg.parse_local_entries(
        [kotlin_entry(value=["should\udfff"])], GENERIC_PATTERNS
    )[1]
    assert errors and "surrogate" in errors[0]
    errors = reg.parse_local_entries(
        [kotlin_entry(citation_url=KOTEST + "#\ud800")], GENERIC_PATTERNS
    )[1]
    assert errors and "citation_url" in errors[0]


# --------------------------------------------------------------------------
# Security review P3: the improve round count is bounded where it is stored
# --------------------------------------------------------------------------


def test_improve_past_the_round_cap_keeps_the_file_loadable(sot, kotlin_repo):
    cap = reg.MAX_IMPROVE_ROUNDS_STORED
    sot.mkdir(parents=True)
    (sot / "kotlin.toml").write_text(  # a replacement that inherited the cap
        '[[assertions]]\nvalue = ["shouldBe"]\n'
        f'citation_url = "{KOTEST}"\nsource_tag = "{UNREVIEWED}"\n'
        f'review_status = "pending"\nimprove_rounds = {cap}\n'
    )
    _registry.cache_clear()
    (entry_id,) = review_ids(mcp(kotlin_repo))
    result = score_repository(
        kotlin_repo,
        detect_gates=True,
        agent_input={"reviews": {entry_id: {"answer": "improve", "comment": "x"}}},
    )
    local = reg.load_registry(sot, known_roles=GENERIC_PATTERNS, local=True)
    assert local.warnings == ()
    (item,) = saved(sot, "kotlin")["assertions"]
    assert item["improve_rounds"] == cap
    (request,) = [
        r
        for r in result.reference["requests"]
        if r.get("language") == "kotlin" and r["field"] == "assertions"
    ]
    assert request["ask_user"] is True
    # A replacement inherits the clamped count and still loads.
    mcp(kotlin_repo, registry_entries=[kotlin_entry(value=["shouldBeEqual"])])
    (item,) = saved(sot, "kotlin")["assertions"]
    assert item["improve_rounds"] == cap
    local = reg.load_registry(sot, known_roles=GENERIC_PATTERNS, local=True)
    assert local.warnings == ()
