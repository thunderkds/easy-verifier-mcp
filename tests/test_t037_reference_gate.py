"""T037: framework detection + MCP reference gate for missing registry fields."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from easy_verifier.adapters import mcp_server
from easy_verifier.core import gate, metric_tables
from easy_verifier.core import registry as reg
from easy_verifier.core.roles import GENERIC_PATTERNS, _registry
from easy_verifier.core.score import score_repository

SRC = Path(__file__).resolve().parents[1] / "src"

APP_JS = (
    "const express = require('express');\n"
    "const app = express();\n"
    "app.get('/', (req, res) => { res.send(req.query.name); });\n"
    "module.exports = app;\n"
)

# One valid value per required field: a complete local express entry.
EXPRESS_FIELDS = {
    "source_extensions": [".js"],
    "test_name_patterns": ["*.test.js"],
    "test_candidates": ["{stem}.test{ext}"],
    "test_declarations": ["it("],
    "assertions": ["expect("],
    "branch_keywords": ["if"],
    "comment_delimiters": ["//"],
    "string_delimiters": ["'"],
    "function_start": ["function"],
    "import_syntax": ["require("],
    "security_sinks": ["res.send("],
    "interpolating_strings": ["` ${"],
}


def _write(root: Path, files: dict[str, str]) -> Path:
    for relative, text in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return root


def _package(**sections) -> str:
    return json.dumps({"name": "demo", **sections})


@pytest.fixture
def express_repo(tmp_path: Path) -> Path:
    repo = _write(
        tmp_path / "repo",
        {
            "package.json": _package(dependencies={"express": "^4.19.2"}),
            "src/app.js": APP_JS,
            "README.md": "# Demo\n",
        },
    )
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    return repo


def _express_entries(**only) -> list[dict]:
    items = []
    for field, value in EXPRESS_FIELDS.items():
        item = {
            "framework": "express",
            "extends": "js-ts",
            "field": field,
            "value": value,
            "citation_url": "https://expressjs.com/en/4x/api.html",
            "source_tag": "agent-researched",
        }
        if field == "security_sinks":
            item["cwe"] = "CWE-79"
        items.append(item)
    return items


def _save(items: list[dict]) -> None:
    entries, errors = reg.parse_local_entries(items, GENERIC_PATTERNS)
    assert errors == []
    reg.save_local_entries(entries, reg.sot_root(), known_roles=GENERIC_PATTERNS)
    _registry.cache_clear()


# ---------------------------------------------------------------------------
# AC1: deterministic framework detection from manifest dependencies


def test_express_dependency_detects_express_framework(express_repo):
    stack = gate.detect_stack(express_repo, _registry())
    assert stack == {
        "languages": ["js-ts"],
        "frameworks": [{"name": "express", "language": "js-ts"}],
    }


def test_json_manifest_word_outside_dependency_sections_is_not_detected(tmp_path):
    repo = _write(
        tmp_path,
        {
            "package.json": _package(
                description="an express-like react clone",
                scripts={"start": "node express"},
                dependencies={"express-session": "1"},
            )
        },
    )
    assert gate.detect_stack(repo, _registry())["frameworks"] == []


def test_nested_workspace_package_detects_and_node_modules_does_not(tmp_path):
    repo = _write(
        tmp_path,
        {
            "package.json": _package(workspaces=["packages/*"]),
            "packages/web/package.json": _package(devDependencies={"react": "18"}),
            "node_modules/x/package.json": _package(dependencies={"vue": "3"}),
        },
    )
    assert gate.detect_stack(repo, _registry())["frameworks"] == [
        {"name": "react", "language": "js-ts"}
    ]


def test_text_manifests_match_whole_dependency_tokens(tmp_path):
    repo = _write(
        tmp_path,
        {
            "requirements.txt": "Django==4.2\ndjango-environ\nflaskish==1\n",
            "pom.xml": "<groupId>org.springframework.boot</groupId>\n",
        },
    )
    stack = gate.detect_stack(repo, _registry())
    assert stack["languages"] == ["java", "python"]
    assert stack["frameworks"] == [
        {"name": "django", "language": "python"},
        {"name": "spring-boot", "language": "java"},
    ]


def test_detection_keys_are_cited_registry_data():
    keys = dict(_registry().detection_keys("js-ts"))
    assert keys["express"] == "express"
    assert keys["angular"] == "@angular/core"
    for entry in _registry().languages.values():
        for cited in entry.fields.get("frameworks", ()):
            assert cited.citation_url.startswith("https://")
            assert cited.source_tag == reg.CURATED


def test_detected_stack_is_listed_in_score_output(express_repo):
    payload = score_repository(express_repo).to_dict()
    assert payload["detected_stack"]["frameworks"] == [
        {"name": "express", "language": "js-ts"}
    ]


# ---------------------------------------------------------------------------
# AC2/AC3: missing fields only, fixed instructions


def test_required_fields_derive_from_rules(monkeypatch):
    required = gate.required_fields()
    assert "security_sinks" in required
    assert "security.sink_hits_observed" in required["security_sinks"]
    assert "manifests" not in required and "frameworks" not in required
    rules = {dim: dict(r) for dim, r in gate.RATING_RULES.items()}
    rules["security"] = {
        k: v
        for k, v in rules["security"].items()
        if v.metric_name != "sink_hits_observed"
    }
    monkeypatch.setattr(gate, "RATING_RULES", rules)
    required = gate.required_fields()
    assert "security_sinks" not in required
    assert "interpolating_strings" not in required
    assert "sink_hits_observed" not in required["source_extensions"]


def test_express_without_entry_lists_express_fields_only(express_repo):
    result = score_repository(express_repo, detect_gates=True)
    reference = result.reference
    assert reference is not None
    requests = reference["requests"]
    assert {item.get("framework") for item in requests} == {"express"}
    assert [item["field"] for item in requests] == [
        "test_name_patterns",
        "test_declarations",
        "assertions",
        "security_sinks",
    ]
    assert all(item["extends"] == "js-ts" and item["why"] for item in requests)
    assert reference["omitted"] == 0
    assert reference["instructions"] == gate.REFERENCE_INSTRUCTIONS


def test_instructions_carry_the_research_bound():
    text = gate.REFERENCE_INSTRUCTIONS
    for phrase in (
        "at most 2 lookups",
        "official documentation first",
        "clear https link",
        "one question at a time",
        "recommended answer",
        '"user-supplied"',
        "registry_entries",
    ):
        assert phrase in text


@pytest.mark.parametrize(
    "manifest",
    ["package.json", "pyproject.toml", "go.mod", "pom.xml", "Cargo.toml", "Gemfile"],
)
def test_no_framework_and_curated_language_means_no_gate(tmp_path, manifest):
    text = _package() if manifest.endswith(".json") else "\n"
    repo = _write(tmp_path, {manifest: text})
    assert gate.detect_stack(repo, _registry())["frameworks"] == []
    assert score_repository(repo, detect_gates=True).reference is None


def test_mcp_no_framework_no_reference(tmp_path):
    repo = _write(tmp_path, {"package.json": _package(), "a.js": "let a = 1;\n"})
    assert "reference" not in mcp_server.score(repo=str(repo)).get("needs_input", {})


def test_optional_fields_are_never_required():
    assert set(gate.OPTIONAL_FIELDS) == {
        "interpolating_strings",
        "test_candidates",
        "colocated_test_name_patterns",
        "type_stub_names",  # T040: only TypeScript generates code-suffix stubs
    }
    assert not set(gate.OPTIONAL_FIELDS) & set(gate.required_fields())


def test_every_field_metric_is_curated_everywhere_or_declared_optional():
    """A field the metric code reads must be either curated for all nine
    languages or listed in OPTIONAL_FIELDS — otherwise a language missing it
    silently trips the reference gate (T054)."""
    languages = _registry().languages
    assert len(languages) == 9
    for field in metric_tables.FIELD_METRICS:
        curated_everywhere = all(field in entry.fields for entry in languages.values())
        assert curated_everywhere or field in gate.OPTIONAL_FIELDS, (
            f"{field}: not curated for all languages and not in OPTIONAL_FIELDS"
        )


def _without(field: str):
    import dataclasses

    full = _registry()
    return dataclasses.replace(
        full,
        languages={
            name: dataclasses.replace(
                entry, fields={k: v for k, v in entry.fields.items() if k != field}
            )
            for name, entry in full.languages.items()
        },
    )


def _numeric(result, metrics) -> int:
    return sum(
        1
        for item in result.metrics
        if item.name in metrics and isinstance(item.outcome, int | float)
    )


@pytest.mark.parametrize(
    ("field", "optional"),
    [
        ("interpolating_strings", True),
        ("test_candidates", True),
        ("colocated_test_name_patterns", True),
        ("function_start", False),
    ],
)
def test_optional_fields_really_are_optional_in_metric_code(
    tmp_path, monkeypatch, field, optional
):
    from easy_verifier.core import metric_tables, score

    # The test file sits under a directory-evidenced ``test/`` root (not
    # colocated with its source) so directory evidence alone classifies it,
    # independent of colocated_test_name_patterns (T054).
    repo = _write(
        tmp_path,
        {
            "package.json": _package(),
            "src/app.js": "function f(a) {\n  if (a) { return eval(a); }\n}\n",
            "test/app.test.js": "it('f', () => { expect(1).toBe(1); });\n",
        },
    )
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    metrics = set(gate.FIELD_METRICS[field])
    full = _numeric(score_repository(repo, scope="project"), metrics)
    stripped = _without(field)
    monkeypatch.setattr(score, "_registry", lambda: stripped)
    monkeypatch.setattr(metric_tables, "_registry", lambda: stripped)
    after = _numeric(score_repository(repo, scope="project"), metrics)
    assert full > 0
    if optional:
        assert after == full, f"{field}: metrics stop computing without it"
    else:
        assert after < full  # control: a required field does matter


def test_local_express_entry_closes_the_gate(express_repo):
    _save(_express_entries())
    assert score_repository(express_repo, detect_gates=True).reference is None


def test_partial_local_entry_asks_only_the_rest(express_repo):
    _save([i for i in _express_entries() if i["field"] != "security_sinks"])
    requests = score_repository(express_repo, detect_gates=True).reference["requests"]
    assert [(i["framework"], i["field"]) for i in requests] == [
        ("express", "security_sinks")
    ]


def test_framework_entry_extending_another_language_does_not_count(express_repo):
    _save([dict(i, extends="python") for i in _express_entries()])
    assert score_repository(express_repo, detect_gates=True).reference is not None


# ---------------------------------------------------------------------------
# AC2/AC4: cap 20, languages first, deterministic, overflow labelled


FRAMEWORKS = [
    {"name": "express", "language": "js-ts"},
    {"name": "react", "language": "js-ts"},
]


def test_two_frameworks_fit_with_duplicate_fields_and_languages_first():
    stack = {"languages": ["zz-unknown"], "frameworks": FRAMEWORKS}
    required = list(gate.required_fields())
    addable = [f for f in required if f in gate.FRAMEWORK_FIELDS]
    requests = gate.reference_requests(stack, _registry())["requests"]
    n = len(required)
    # T040 raised a language's required fields to 16, so with two frameworks
    # the cap of 20 now truncates the framework duplicates (still in order).
    assert len(requests) == min(n + 2 * len(addable), 20)
    assert [i.get("language") for i in requests[:n]] == ["zz-unknown"] * n
    assert [(i["framework"], i["field"]) for i in requests[n:]] == [
        (name, f) for name in ("express", "react") for f in addable
    ][: len(requests) - n]


def test_cap_order_and_overflow_labelled():
    stack = {"languages": ["zz-a", "zz-b"], "frameworks": FRAMEWORKS}
    required = list(gate.required_fields())
    addable = [f for f in required if f in gate.FRAMEWORK_FIELDS]
    reference = gate.reference_requests(stack, _registry())
    requests = reference["requests"]
    assert len(requests) == gate.MAX_REFERENCE_FIELDS == 20
    assert all("language" in i for i in requests)
    assert [i["language"] for i in requests] == (
        ["zz-a"] * len(required) + ["zz-b"] * len(required)
    )[:20]
    total = 2 * len(required) + 2 * len(addable)
    assert reference["omitted"] == total - 20 > 0
    assert "omitted" in reference["instructions"]
    assert "generic patterns" in reference["instructions"]
    assert gate.reference_requests(stack, _registry()) == reference


# ---------------------------------------------------------------------------
# Answers reach the rules and replay


def _sinks(result) -> int:
    """Sink hits summed over every pack that scanned code (abstentions skip)."""
    return sum(
        item.outcome
        for item in result.metrics
        if item.name == "sink_hits_observed" and isinstance(item.outcome, int)
    )


def test_framework_entry_fields_reach_the_rules_and_replay(express_repo):
    before = score_repository(express_repo, scope="project")
    _save([i for i in _express_entries() if i["field"] == "security_sinks"])
    after = score_repository(express_repo, scope="project")
    assert _sinks(before) == 0 and _sinks(after) > 0
    embedded = after.to_dict()["registry_entries"]
    assert embedded == [
        {
            "framework": "express",
            "extends": "js-ts",
            "field": "security_sinks",
            "value": ["res.send("],
            "citation_url": "https://expressjs.com/en/4x/api.html",
            "source_tag": reg.AGENT_RESEARCHED,
            "cwe": "CWE-79",
        }
    ]


# ---------------------------------------------------------------------------
# Registry validation of the new field


def test_frameworks_field_belongs_to_language_entries_only():
    bad = {
        "framework": "express",
        "extends": "js-ts",
        "field": "frameworks",
        "value": ["x=x"],
        "citation_url": "https://example.org/x",
        "source_tag": "user-supplied",
    }
    assert reg.parse_local_entries([bad], GENERIC_PATTERNS)[1]
    good = dict(bad, field="frameworks", language="js-ts")
    del good["framework"], good["extends"]
    assert reg.parse_local_entries([good], GENERIC_PATTERNS)[1] == []
    assert reg.parse_local_entries(
        [dict(good, value=["no-equals-sign"])], GENERIC_PATTERNS
    )[1]


# ---------------------------------------------------------------------------
# AC5 / FR-040: MCP carries it, CLI never does


def test_mcp_payload_carries_reference_and_cli_never_does(express_repo):
    payload = mcp_server.score(repo=str(express_repo))
    assert payload["needs_input"]["reference"]["requests"][0]["framework"] == "express"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "easy_verifier.adapters.cli",
            "score",
            "--repo",
            str(express_repo),
        ],
        capture_output=True,
        text=True,
        cwd=SRC,
        stdin=subprocess.DEVNULL,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    cli_payload = json.loads(completed.stdout)
    assert "needs_input" not in cli_payload
    assert '"reference"' not in completed.stdout
    assert "instructions" not in completed.stdout
    assert cli_payload["detected_stack"] == payload["detected_stack"]


def test_call_with_gate_evaluations_asks_no_reference(express_repo):
    result = score_repository(
        express_repo, detect_gates=True, agent_input={"gate_evaluations": {}}
    )
    assert result.reference is None


def test_score_tool_description_mentions_reference_gate():
    tool = mcp_server.mcp._tool_manager.get_tool("score")
    assert "needs_input.reference" in tool.description
    assert "registry_entries" in tool.description


def test_reference_never_enters_the_shared_payload(express_repo):
    result = score_repository(express_repo, detect_gates=True)
    assert result.reference is not None
    assert "needs_input" not in result.to_dict()
    assert '"instructions"' not in result.serialize()


def test_hostile_json_manifest_never_crashes_detection(tmp_path):
    repo = _write(tmp_path, {"package.json": "[" * 200_000})
    assert gate.detect_stack(repo, _registry())["frameworks"] == []
