"""T036: local registry layer, ``registry_entries`` agent input, replay parity.

Every negative case is paired with a positive one that differs only in the
predicate under test, so each guard is pinned from both sides.
"""

from __future__ import annotations

import html
import json
import os
import re
import subprocess
import sys
import threading
import tomllib
from pathlib import Path

import pytest

from easy_verifier.adapters import mcp_server
from easy_verifier.core import registry as reg
from easy_verifier.core.metric_tables import curated_metric_tables
from easy_verifier.core.report import write_report
from easy_verifier.core.roles import (
    GENERIC_PATTERNS,
    MAX_ERROR_LINES,
    RoleInputError,
    _registry,
    apply_registry_entries,
    registry_notes,
    resolve,
    role,
    validate_agent_input,
)
from easy_verifier.core.score import score_repository
from easy_verifier.core.synthesis import combined_pack
from easy_verifier.dimensions import dimension_names

SRC = Path(__file__).resolve().parent.parent / "src"
KOTEST = "https://kotest.io/docs/assertions/assertions.html"


def entry(**overrides) -> dict:
    item = {
        "language": "kotlin",
        "field": "assertions",
        "value": ["shouldBe"],
        "citation_url": KOTEST,
        "source_tag": "agent-researched",
    }
    item.update(overrides)
    return {key: value for key, value in item.items() if value is not None}


def problems(*items: dict) -> list[str]:
    return reg.parse_local_entries(list(items), GENERIC_PATTERNS)[1]


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


def tree(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file() and ".git" not in path.relative_to(root).parts
    }


# --------------------------------------------------------------------------
# AC 2: validation, each guard pinned from both sides
# --------------------------------------------------------------------------


def test_valid_entry_is_accepted_and_tag_is_normalised():
    entries, errors = reg.parse_local_entries([entry()], GENERIC_PATTERNS)
    assert errors == []
    assert entries[0].cited.source_tag == "agent-researched (unreviewed)"
    user = reg.parse_local_entries(
        [entry(source_tag="user-supplied")], GENERIC_PATTERNS
    )
    assert user[0][0].cited.source_tag == "user-supplied"


def test_http_citation_rejected_https_accepted():
    assert problems(entry(citation_url=KOTEST)) == []
    (error,) = problems(entry(citation_url=KOTEST.replace("https", "http", 1)))
    assert "citation_url: must be an https:// link" in error
    (error,) = problems(entry(citation_url="https://user:pw@kotest.io/docs"))
    assert "citation_url" in error
    (error,) = problems(entry(citation_url="https:///no-host"))
    assert "citation_url" in error


def test_token_wildcards_bounded_backtracking_guard():
    stars = reg.MAX_LOCAL_TOKEN_STARS
    ok = "should" + "*x" * stars
    assert problems(entry(value=[ok])) == []
    (error,) = problems(entry(value=[ok + "*y"]))
    assert f"at most {stars} '*' wildcards in a token" in error


def test_role_glob_shape_bounded_like_repo_config():
    base = {"field": "roles.test-file"}
    assert problems(entry(value=["**/checks/**"], **base)) == []
    (error,) = problems(entry(value=["**/a/**/b/**"], **base))
    assert "at most 2 '**' segments" in error
    (error,) = problems(entry(value=["checks**/x"], **base))
    assert "'**' must be a whole path segment" in error
    (error,) = problems(entry(value=["../outside/*"], **base))
    assert "repository-relative glob" in error


def test_unknown_or_traversal_field_and_name_rejected():
    assert problems(entry(field="roles.test-file", value=["checks/*"])) == []
    for field in ("../etc/passwd", "roles.nope", "roles.", "extends", 7):
        (error,) = problems(entry(field=field))
        assert "unknown field" in error, field
    (error,) = problems(entry(language="../kotlin"))
    assert "language: must be a lowercase entry name" in error


def test_value_size_and_count_bounded():
    assert problems(entry(value=["x"] * reg.MAX_VALUES_PER_FIELD)) == []
    (error,) = problems(entry(value=["x"] * (reg.MAX_VALUES_PER_FIELD + 1)))
    assert f"at most {reg.MAX_VALUES_PER_FIELD} entries" in error
    (error,) = problems(entry(value=["x" * (reg.MAX_VALUE_CHARS + 1)]))
    assert f"at most {reg.MAX_VALUE_CHARS} characters" in error


def test_secret_shaped_value_refused():
    secret = "AKIA" + "Q" * 16  # assembled at runtime: never a literal shape
    (error,) = problems(entry(value=[secret]))
    assert "secret" in error


def test_source_tag_and_keys_restricted():
    (error,) = problems(entry(source_tag="curated"))
    assert "source_tag: must be agent-researched or user-supplied" in error
    (error,) = problems(entry(extra="x"))
    assert "unknown key extra" in error
    (error,) = problems(entry(framework="kotest"))
    assert "exactly one of language or framework" in error
    fw = entry(language=None, framework="kotest", extends="kotlin")
    assert problems(fw) == []
    (error,) = problems(dict(fw, field="manifests", value=["x.kts"]))
    assert "framework entry adds to its language only" in error


def test_error_list_capped_at_twenty_lines(kotlin_repo):
    bad = [entry(citation_url="http://x.example")] * reg.MAX_AGENT_ENTRIES
    document = {"registry_entries": bad, "junk": 1, "more": 2}
    with pytest.raises(RoleInputError) as caught:
        validate_agent_input(document, kotlin_repo)
    assert len(caught.value.errors) == MAX_ERROR_LINES + 1
    assert caught.value.errors[-1] == "…and 2 more"
    with pytest.raises(RoleInputError) as caught:
        validate_agent_input({"registry_entries": bad + [entry()]}, kotlin_repo)
    assert caught.value.errors == (
        f"registry_entries: at most {reg.MAX_AGENT_ENTRIES} entries per call",
    )


# --------------------------------------------------------------------------
# AC 1, 3, 4: saved, used immediately, tagged; curated wins
# --------------------------------------------------------------------------


def test_valid_kotlin_assertion_saved_used_and_tagged(sot, kotlin_repo):
    assert not curated_metric_tables().assertions.search("x shouldBe 1")
    apply_registry_entries({"registry_entries": [entry()]}, kotlin_repo)

    saved = tomllib.loads((sot / "kotlin.toml").read_text())
    assert saved["assertions"] == [
        {
            "value": ["shouldBe"],
            "citation_url": KOTEST,
            "source_tag": "agent-researched (unreviewed)",
            "review_status": "pending",  # T038: new entries start pending
        }
    ]
    # Used in the same process without a restart: every cache followed.
    assert curated_metric_tables().assertions.search("x shouldBe 1")
    assert _registry().local_entries() == (
        {
            "language": "kotlin",
            "field": "assertions",
            "value": ["shouldBe"],
            "citation_url": KOTEST,
            "source_tag": "agent-researched (unreviewed)",
        },
    )


def test_score_payload_shows_tag_and_link_and_uses_entry(sot, kotlin_repo):
    before = score_repository(kotlin_repo, scope="project")
    after = score_repository(
        kotlin_repo, scope="project", agent_input={"registry_entries": [entry()]}
    )

    def observed(result):
        (metric,) = [
            m
            for m in result.metrics
            if m.dimension == "test-strategy" and m.name == "assertions_observed"
        ]
        return metric

    assert "registry_entries" not in before.to_dict()
    payload = after.to_dict()
    assert payload["registry_entries"][0]["source_tag"] == (
        "agent-researched (unreviewed)"
    )
    assert payload["registry_entries"][0]["citation_url"] == KOTEST
    assert observed(before).outcome == 0
    assert observed(after).outcome == 1
    assert after.registry_notes == ()


def test_curated_value_wins_and_is_reported(sot, kotlin_repo):
    curated = "assert<A-Z>*"  # kotlin.toml's own assertion token
    document = {"registry_entries": [entry(value=[curated, "shouldBe"])]}
    apply_registry_entries(document, kotlin_repo)
    (used,) = _registry().local_entries()
    assert used["value"] == ["shouldBe"]
    kotlin = _registry().languages["kotlin"]
    curated_tags = [
        c.source_tag for c in kotlin.fields["assertions"] if curated in c.value
    ]
    assert curated_tags == ["curated"]
    notes = registry_notes(document, kotlin_repo)
    assert any(
        "curated wins: kotlin.assertions already has assert<A-Z>*" in n for n in notes
    )


def test_local_role_glob_fills_role_through_bounded_matcher(sot, kotlin_repo):
    (kotlin_repo / "checks").mkdir()
    (kotlin_repo / "checks/smoke.kts").write_text("x\n")
    request = [role("test-file")]
    assert "checks/smoke.kts" not in resolve(kotlin_repo, request).files["test-file"]
    apply_registry_entries(
        {"registry_entries": [entry(field="roles.test-file", value=["checks/*"])]},
        kotlin_repo,
    )
    assert _registry().patterns_for("test-file", ["kotlin"], local=True) == (
        "checks/*",
    )
    assert "checks/*" not in _registry().patterns_for("test-file", ["kotlin"])
    assert "checks/smoke.kts" in resolve(kotlin_repo, request).files["test-file"]


def test_new_language_needs_manifest(sot, kotlin_repo):
    scala = entry(language="scala", value=["shouldEqual"])
    apply_registry_entries({"registry_entries": [scala]}, kotlin_repo)
    assert "scala" not in _registry().languages
    assert any("needs at least one manifest" in w for w in _registry().warnings)
    manifest = entry(language="scala", field="manifests", value=["build.sbt"])
    apply_registry_entries({"registry_entries": [manifest]}, kotlin_repo)
    assert "scala" in _registry().languages


# --------------------------------------------------------------------------
# refusal paths: symlinks, unwritable, inside the target repo (AC 6, 7)
# --------------------------------------------------------------------------


def test_symlinked_sot_dir_refused(tmp_path, monkeypatch, kotlin_repo):
    real = tmp_path / "elsewhere"
    real.mkdir()
    link = tmp_path / "sot-link"
    link.symlink_to(real, target_is_directory=True)
    monkeypatch.setenv("EASY_VERIFIER_SOT", str(link))
    _registry.cache_clear()
    document = {"registry_entries": [entry()]}
    apply_registry_entries(document, kotlin_repo)
    assert list(real.iterdir()) == []
    notes = registry_notes(document, kotlin_repo)
    assert any("research cannot be saved" in n and "symlink" in n for n in notes)
    # Same call against the real directory: saved. Only the link differs.
    monkeypatch.setenv("EASY_VERIFIER_SOT", str(real))
    apply_registry_entries(document, kotlin_repo)
    assert (real / "kotlin.toml").is_file()


def test_symlinked_entry_file_skipped(sot, tmp_path, kotlin_repo):
    apply_registry_entries({"registry_entries": [entry()]}, kotlin_repo)
    outside = tmp_path / "planted.toml"
    outside.write_text((sot / "kotlin.toml").read_text())
    (sot / "java.toml").symlink_to(outside)
    _registry.cache_clear()
    assert any(
        "java.toml: entry rejected: is a symlink" in w for w in _registry().warnings
    )
    with pytest.raises(OSError, match="symlink"):
        reg.save_local_entries(
            [reg.parse_local_entries([entry(language="java")], GENERIC_PATTERNS)[0][0]],
            sot,
            known_roles=GENERIC_PATTERNS,
        )


def test_unwritable_sot_scores_curated_only_and_says_so(sot, kotlin_repo):
    if os.geteuid() == 0:
        pytest.skip("root ignores directory permissions")
    sot.mkdir(parents=True)
    sot.chmod(0o500)
    try:
        result = score_repository(
            kotlin_repo, scope="project", agent_input={"registry_entries": [entry()]}
        )
        assert "registry_entries" not in result.to_dict()
        assert any(
            "research cannot be saved" in n and "not writable" in n
            for n in result.registry_notes
        )
        mcp = mcp_server.score(
            repo=str(kotlin_repo),
            scope="project",
            agent_input={"registry_entries": [entry()]},
        )
        assert any("research cannot be saved" in n for n in mcp["registry_notes"])
    finally:
        sot.chmod(0o700)


def test_sot_inside_target_repo_refused(tmp_path, monkeypatch, kotlin_repo):
    before = tree(kotlin_repo)
    monkeypatch.setenv("EASY_VERIFIER_SOT", str(kotlin_repo / ".sot"))
    _registry.cache_clear()
    document = {"registry_entries": [entry()]}
    apply_registry_entries(document, kotlin_repo)
    assert tree(kotlin_repo) == before
    assert any(
        "inside the target repository" in n
        for n in registry_notes(document, kotlin_repo)
    )


def test_only_reports_written_under_target_repo(sot, kotlin_repo):
    before = tree(kotlin_repo)
    document = {"registry_entries": [entry()]}
    packs = combined_pack(
        dimension_names(), kotlin_repo, "project", agent_input=document
    )
    write_report([], packs, kotlin_repo, agent_input=document)
    after = tree(kotlin_repo)
    changed = {p for p in after if before.get(p) != after[p]} | (
        before.keys() - after.keys()
    )
    assert changed and all(p.startswith("reports/") for p in changed)
    assert (sot / "kotlin.toml").is_file()


# --------------------------------------------------------------------------
# writes: atomic, deterministic, concurrent
# --------------------------------------------------------------------------


def test_write_is_deterministic_regardless_of_order(tmp_path, kotlin_repo):
    items = [
        entry(value=["shouldBe"]),
        entry(value=["shouldNotBe"]),
        entry(field="test_declarations", value=["test("], source_tag="user-supplied"),
    ]
    parsed = reg.parse_local_entries(items, GENERIC_PATTERNS)[0]
    for name, order in (("a", parsed), ("b", tuple(reversed(parsed)))):
        reg.save_local_entries(order, tmp_path / name, known_roles=GENERIC_PATTERNS)
    first = (tmp_path / "a/kotlin.toml").read_bytes()
    assert first == (tmp_path / "b/kotlin.toml").read_bytes()
    # Saving the same entries again changes nothing (identical field kept once).
    reg.save_local_entries(parsed, tmp_path / "a", known_roles=GENERIC_PATTERNS)
    assert (tmp_path / "a/kotlin.toml").read_bytes() == first
    loaded = reg.load_registry(tmp_path / "a", known_roles=GENERIC_PATTERNS, local=True)
    assert loaded.warnings == ()


def test_concurrent_writers_leave_one_complete_file(tmp_path):
    root = tmp_path / "sot"
    parsed = [
        reg.parse_local_entries([entry(value=[f"should{n}"])], GENERIC_PATTERNS)[0]
        for n in range(8)
    ]
    failures: list[BaseException] = []

    def write(items):
        try:
            for _ in range(10):
                reg.save_local_entries(items, root, known_roles=GENERIC_PATTERNS)
        except BaseException as exc:  # noqa: BLE001 - collected for the assert
            failures.append(exc)

    threads = [threading.Thread(target=write, args=(p,)) for p in parsed]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert failures == []
    assert [p.name for p in root.iterdir()] == ["kotlin.toml"]  # no temp left
    data = tomllib.loads((root / "kotlin.toml").read_text())
    assert data["assertions"]  # parseable; last writer's complete content


def test_invalid_existing_file_is_not_modified(tmp_path):
    root = tmp_path / "sot"
    root.mkdir()
    (root / "kotlin.toml").write_text("not = [valid\n")
    parsed = reg.parse_local_entries([entry()], GENERIC_PATTERNS)[0]
    with pytest.raises(OSError, match="invalid; not modified"):
        reg.save_local_entries(parsed, root, known_roles=GENERIC_PATTERNS)
    assert (root / "kotlin.toml").read_text() == "not = [valid\n"


def test_toml_round_trip_of_quotes(tmp_path):
    parsed = reg.parse_local_entries(
        [entry(field="test_declarations", value=['it("', "té*st"])], GENERIC_PATTERNS
    )[0]
    reg.save_local_entries(parsed, tmp_path, known_roles=GENERIC_PATTERNS)
    loaded = reg.load_registry(tmp_path, known_roles=GENERIC_PATTERNS, local=True)
    (cited,) = loaded.languages["kotlin"].fields["test_declarations"]
    assert cited.value == ('it("', "té*st")


# --------------------------------------------------------------------------
# AC 5: replay from the report on a machine with an empty local layer
# --------------------------------------------------------------------------


def cli(*args: str, sot_dir: Path) -> subprocess.CompletedProcess:
    env = dict(os.environ, EASY_VERIFIER_SOT=str(sot_dir), PYTHONPATH=str(SRC))
    return subprocess.run(
        [sys.executable, "-m", "easy_verifier.adapters.cli", *args],
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=False,
    )


def test_replay_from_report_is_byte_equal_on_empty_machine(tmp_path, kotlin_repo):
    machine_a = tmp_path / "a-sot"
    machine_b = tmp_path / "b-sot"
    # Machine A already holds earlier research, and this call adds more.
    earlier = reg.parse_local_entries(
        [entry(field="test_declarations", value=["test("], source_tag="user-supplied")],
        GENERIC_PATTERNS,
    )[0]
    reg.save_local_entries(earlier, machine_a, known_roles=GENERIC_PATTERNS)
    first_input = tmp_path / "first.json"
    first_input.write_text(json.dumps({"registry_entries": [entry()]}))
    common = ("--repo", str(kotlin_repo), "--scope", "project")

    original = cli(
        "score", *common, "--agent-input", str(first_input), sot_dir=machine_a
    )
    assert original.returncode == 0, original.stderr
    report = subprocess.run(  # write-report reads findings from stdin
        [
            sys.executable,
            "-m",
            "easy_verifier.adapters.cli",
            "write-report",
            *common,
            "--agent-input",
            str(first_input),
        ],
        env=dict(os.environ, EASY_VERIFIER_SOT=str(machine_a), PYTHONPATH=str(SRC)),
        input=b"[]",
        capture_output=True,
        check=False,
    )
    assert report.returncode == 0, report.stderr
    document = (kotlin_repo / json.loads(report.stdout)["path"]).read_text()
    (embedded,) = re.findall(
        r'<pre class="registry-replay">(.*?)</pre>', document, re.S
    )
    replay_input = tmp_path / "replay.json"
    replay_input.write_text(html.unescape(embedded))
    assert len(json.loads(replay_input.read_text())["registry_entries"]) == 2
    assert "agent-researched (unreviewed)" in document and KOTEST in document
    assert f'registry data: <a href="{KOTEST}" rel="noreferrer">' in document

    replayed = cli(
        "score", *common, "--agent-input", str(replay_input), sot_dir=machine_b
    )
    assert replayed.returncode == 0, replayed.stderr
    assert replayed.stdout == original.stdout  # byte-equal, no normalization needed
    assert b"registry_entries" in original.stdout
    # Machine B without the replay entries scores differently: the replay did it.
    bare = cli("score", *common, sot_dir=tmp_path / "c-sot")
    assert bare.stdout != original.stdout


# --------------------------------------------------------------------------
# AC 4: per rule input tag + link (field -> metric provenance)
# --------------------------------------------------------------------------


def rating_inputs(result, dimension: str) -> dict[str, dict]:
    (rating,) = [r for r in result.to_dict()["ratings"] if r["dimension"] == dimension]
    return {item["metric_name"]: item for item in rating["inputs"]}


def test_input_built_on_local_assertion_is_tagged_with_link(sot, kotlin_repo):
    result = score_repository(
        kotlin_repo, scope="project", agent_input={"registry_entries": [entry()]}
    )
    inputs = rating_inputs(result, "test-strategy")
    tagged = inputs["assertion_density_per_test"]
    assert tagged["source_tag"] == "agent-researched (unreviewed)"
    assert tagged["registry_citations"] == [
        {"label": "kotlin.assertions", "url": KOTEST}
    ]
    # The rule's own citations are still shown beside the local data.
    assert tagged["metric_citation"]
    unrelated = inputs["test_config_and_ci_missing"]
    assert unrelated["source_tag"] == "curated"
    assert "registry_citations" not in unrelated


def test_without_local_data_every_input_stays_curated(sot, kotlin_repo):
    result = score_repository(kotlin_repo, scope="project")
    tags = {
        item["source_tag"]
        for rating in result.to_dict()["ratings"]
        for item in rating.get("inputs", ())
    }
    assert tags == {"curated"}


def test_least_reviewed_tag_wins_and_all_links_listed(sot, kotlin_repo):
    user_url = "https://kotest.io/docs/assertions/core-matchers.html"
    items = [
        entry(
            value=["shouldContain"], source_tag="user-supplied", citation_url=user_url
        ),
        entry(),
    ]
    result = score_repository(
        kotlin_repo, scope="project", agent_input={"registry_entries": items}
    )
    tagged = rating_inputs(result, "test-strategy")["assertion_density_per_test"]
    assert tagged["source_tag"] == "agent-researched (unreviewed)"
    assert [c["url"] for c in tagged["registry_citations"]] == sorted(
        [KOTEST, user_url]
    )
    only_user = score_repository(
        kotlin_repo, scope="project", agent_input={"registry_entries": items[:1]}
    )
    # machine A still holds the agent entry from the call above
    assert (
        rating_inputs(only_user, "test-strategy")["assertion_density_per_test"][
            "source_tag"
        ]
        == "agent-researched (unreviewed)"
    )


def test_language_absent_from_pack_does_not_tag(sot, tmp_path):
    repo = tmp_path / "pyrepo"
    (repo / "tests").mkdir(parents=True)
    (repo / "pyproject.toml").write_text("[project]\nname='x'\n")
    (repo / "tests/test_a.py").write_text("def test_a():\n    assert 1\n")
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    result = score_repository(
        repo, scope="project", agent_input={"registry_entries": [entry()]}
    )
    tagged = rating_inputs(result, "test-strategy")["assertion_density_per_test"]
    assert tagged["source_tag"] == "curated"


def test_provenance_map_covers_registry_fields_and_real_metrics():
    from easy_verifier.core import judge
    from easy_verifier.core.metric_tables import FIELD_METRICS, ROLE_METRICS
    from easy_verifier.core.metrics import METRIC_NAMES

    # manifests and frameworks (T037) only activate entries; they feed no metric.
    assert set(FIELD_METRICS) == set(reg.ENTRY_FIELDS) - {"manifests", "frameworks"}
    named = {m for ms in (*FIELD_METRICS.values(), *ROLE_METRICS.values()) for m in ms}
    assert named <= set(METRIC_NAMES)
    assert set(ROLE_METRICS) <= set(GENERIC_PATTERNS)
    assert judge.LOCAL_TAGS == reg.LOCAL_TAGS


def test_judge_pins_tag_and_citations_together(sot, kotlin_repo):
    import dataclasses

    from easy_verifier.core.judge import Citation, RatingInput

    result = score_repository(
        kotlin_repo, scope="project", agent_input={"registry_entries": [entry()]}
    )
    (rating,) = [r for r in result.ratings if r.dimension == "test-strategy"]
    tagged = next(i for i in rating.inputs if i.registry_citations)
    assert type(tagged) is RatingInput
    with pytest.raises(ValueError, match="needs its registry_citations"):
        dataclasses.replace(tagged, registry_citations=())
    with pytest.raises(ValueError, match="need a local-layer source_tag"):
        dataclasses.replace(tagged, source_tag="curated")
    with pytest.raises(ValueError, match="does not match its declared rule"):
        dataclasses.replace(tagged, source_tag="made-up")
    with pytest.raises(ValueError, match="https"):
        dataclasses.replace(
            tagged, registry_citations=(Citation("x", "http://kotest.io"),)
        )
