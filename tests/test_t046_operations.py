"""T046: the ``operations`` dimension (areas #14, #25, #26, #29, #30).

Each AC has a positive and a negative test; each rule predicate is flipped
alone (sabotage pairs), so a metric that cannot fail would be caught.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from easy_verifier.core.judge import (
    AREAS,
    COVERAGE_FLOORS,
    DOCUMENTATION_RULES,
    RATING_RULES,
    Citation,
    CoverageFloor,
)
from easy_verifier.core.metric_tables import OPERATIONS_FIELDS, curated_metric_tables
from easy_verifier.core.redact import scan
from easy_verifier.core.roles import GENERIC_PATTERNS, _matcher, role
from easy_verifier.core.score import score_repository
from easy_verifier.dimensions import DIMENSIONS, list_dimensions, operations

ROLES = (
    "codeowners",
    "runbook, incident or SLO documents",
    "observability-config",
    "logging or tracing in source files",
    "agent-config",
    "tool-version-pin",
    "dev-environment",
)
METRICS = (
    "logging_library_missing",
    "audit_log_writes_missing",
    "codeowners_missing",
    "agent_guardrails_missing",
    "agent_config_secrets_observed",
    "tool_version_pin_missing",
    "dev_environment_missing",
)

SERVICE = """import pino from 'pino';

const log = pino();

export function rename(auditLog: { create(e: object): void }, id: string) {
  auditLog.create({ action: 'rename', id });
  log.info('renamed');
}
"""

SETTINGS = '{"hooks": {"PreToolUse": []}, "permissions": {"deny": ["Bash(rm:*)"]}}\n'

GOOD = {
    "CODEOWNERS": "* @acme/platform\n",
    "CLAUDE.md": "# Agent rules\n\nRun `make setup` before tests.\n",
    ".claude/settings.json": SETTINGS,
    ".nvmrc": "20\n",
    "Makefile": "setup:\n\tnpm ci\n",
    "package.json": '{"name": "shop"}\n',
    "src/rename.service.ts": SERVICE,
    "docs/incident-response.md": "# Incident response\n",
    "docs/SLO.md": "# SLOs\n",
    "docs/runbooks/deploy.md": "# Deploy\n",
}


def _secret() -> str:
    # Assembled at run time: never commit a realistic credential shape.
    return "FAKEfake" + "".join("Q7x9" for _ in range(6))


def _repo(tmp_path: Path, files: dict[str, str]) -> Path:
    for relative, text in files.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return tmp_path


def _payload(repo: Path, scope: str = "project", **kwargs) -> dict:
    return json.loads(score_repository(repo, scope=scope, **kwargs).serialize())


def _result(repo: Path, **kwargs) -> dict:
    payload = _payload(repo, **kwargs)
    rating = next(r for r in payload["ratings"] if r["dimension"] == "operations")
    metrics = {
        m["name"]: m
        for m in payload["metrics"]["metrics"]
        if m["dimension"] == "operations"
    }
    return {"rating": rating, "metrics": metrics}


def _values(result: dict) -> dict:
    return {
        name: m["outcome"]["value"]
        if not m["outcome"].get("abstained")
        else m["outcome"]
        for name, m in result["metrics"].items()
    }


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.email=t@example.invalid", "-c", "user.name=t", *args],
        cwd=repo, check=True, capture_output=True,
    )


# ---------------------------------------------------------------------------
# AC 1 - discoverable, purpose and source roles
# ---------------------------------------------------------------------------


def test_dimension_is_discoverable_with_purpose_and_roles() -> None:
    item = next(d for d in list_dimensions() if d.name == "operations")
    assert item.purpose.endswith(".")
    assert "cannot be verified offline" in item.purpose
    assert tuple(r.name for r in item.roles) == ROLES
    assert item.sources_sought == ROLES
    assert DIMENSIONS["operations"] is operations.DESCRIPTOR


def test_role_globs_match_their_files_and_never_source_code() -> None:
    files = {
        "codeowners": ("CODEOWNERS", ".github/CODEOWNERS", "docs/CODEOWNERS"),
        "agent-config": ("CLAUDE.md", "pkg/AGENTS.md", ".claude/settings.json",
                         ".claude/hooks/guard.py", ".mcp.json"),
        "observability-config": ("deploy/otel-collector-config.yaml",
                                 "ops/prometheus.yml"),
        "tool-version-pin": (".tool-versions", "mise.toml"),
        "dev-environment": (".devcontainer/devcontainer.json", "Makefile",
                            "flake.nix"),
    }
    source = ("src/logger.ts", "src/codeowners.service.ts",
              "src/runbook/Runbook.java", "claude.ts", "src/claude.ts",
              "src/agents/AgentsService.java", "src/otel-config.ts",
              "src/makefile.ts", "lib/prometheus.py", "src/slo.service.ts",
              "src/Vagrantfile.ts", "src/flake.nix.ts",
              "app/incident.service.ts", "src/devcontainer.ts")
    for name, paths in files.items():
        match = _matcher(role(name).patterns)
        for path in paths:
            assert match(path), (name, path)
        for path in source:
            assert not match(path), (name, path)
    for rule in DOCUMENTATION_RULES["operations"]:
        match = _matcher(rule.patterns)
        assert not any(match(path) for path in source), rule.area
        assert not match("docs/slow-queries.md"), rule.area


# ---------------------------------------------------------------------------
# AC 2 - cited rules per area; documentation rules; floor 0.25 (user)
# ---------------------------------------------------------------------------


def test_rules_are_cited_per_area_and_weigh_100() -> None:
    rules = RATING_RULES["operations"]
    assert tuple(rules) == METRICS
    assert sum(rule.weight for rule in rules.values()) == 100
    assert {rules[m].area for m in METRICS[:2]} == {AREAS[13]}
    assert rules["codeowners_missing"].area == AREAS[25]
    assert {rules[m].area for m in METRICS[3:5]} == {AREAS[28]}
    assert {rules[m].area for m in METRICS[5:]} == {AREAS[29]}
    for rule in rules.values():
        assert rule.threshold == 0 and rule.comparison == "at_most"
        assert isinstance(rule.threshold_citation, Citation)
        assert rule.threshold_citation.url.startswith("https://")
        assert all(c.url.startswith("https://") for c in rule.metric_citation)
    guardrails = rules["agent_guardrails_missing"].metric_citation[0]
    assert "OWASP Top 10 for LLM" in guardrails.label
    assert "Twelve-Factor" in rules["tool_version_pin_missing"].threshold_citation.label
    assert not any("lockfile" in name for name in rules)  # supply-chain's rule
    assert COVERAGE_FLOORS["operations"] == CoverageFloor(0.25, "inclusive")
    docs = DOCUMENTATION_RULES["operations"]
    assert [d.area for d in docs] == [AREAS[24], AREAS[13], AREAS[25], AREAS[28]]
    # User decision 2026-10-07: instruction files are a documentation rule.
    assert "agent_instructions_missing" not in rules
    assert "800-61" in docs[0].citation[0].label


# ---------------------------------------------------------------------------
# AC 5 - every rule met rates 100; none of the roles abstains with misses
# ---------------------------------------------------------------------------


def test_fixture_where_every_rule_is_met_rates_100(tmp_path: Path) -> None:
    result = _result(_repo(tmp_path, GOOD))
    rating = result["rating"]
    assert rating["kind"] != "rating_abstention", rating
    assert rating["value"] == 100
    inputs = {item["metric_name"]: item for item in rating["inputs"]}
    assert set(inputs) == set(METRICS)
    assert all(item["passed"] for item in inputs.values())
    values = _values(result)
    assert {name: values[name] for name in METRICS} == dict.fromkeys(METRICS, 0)
    serialized = json.dumps(rating)
    for path in ("docs/incident-response.md", "docs/SLO.md", "docs/runbooks/deploy.md"):
        assert path in serialized, path


def test_repository_with_none_of_the_roles_abstains_naming_every_miss(
    tmp_path: Path,
) -> None:
    result = _result(_repo(tmp_path, {"notes.txt": "nothing relevant\n"}))
    rating = result["rating"]
    assert rating["kind"] == "rating_abstention"
    assert rating["reason_code"] == "below_coverage_floor"
    assert "value" not in rating
    assert [m["source"] for m in rating["sources_missing"]] == list(ROLES)


def test_documents_alone_never_reach_the_floor(tmp_path: Path) -> None:
    files = {k: v for k, v in GOOD.items() if k.startswith("docs/")}
    rating = _result(_repo(tmp_path, files))["rating"]
    assert rating["reason_code"] == "below_coverage_floor"


# ---------------------------------------------------------------------------
# Sabotage pairs: each predicate flipped alone flips exactly its metric
# ---------------------------------------------------------------------------


def _without(*paths: str) -> dict:
    return {k: v for k, v in GOOD.items() if k not in paths}


@pytest.mark.parametrize(
    ("files", "metric", "value"),
    [
        ({**GOOD, "src/rename.service.ts": SERVICE.replace("import pino from 'pino';",
                                                           "").replace("pino()", "{}")},
         "logging_library_missing", 1),
        ({**GOOD, "src/rename.service.ts": SERVICE.replace("auditLog", "repo")},
         "audit_log_writes_missing", 1),
        (_without("CODEOWNERS"), "codeowners_missing", 1),
        ({**GOOD, ".claude/settings.json": '{"model": "x"}\n'},
         "agent_guardrails_missing", 1),
        ({**GOOD, "CLAUDE.md": GOOD["CLAUDE.md"] + f'\napi_key = "{_secret()}"\n'},
         "agent_config_secrets_observed", 1),
        (_without(".nvmrc"), "tool_version_pin_missing", 1),
        (_without("Makefile"), "dev_environment_missing", 1),
    ],
)
def test_each_predicate_flips_exactly_its_metric(
    tmp_path: Path, files: dict, metric: str, value: int
) -> None:
    values = _values(_result(_repo(tmp_path / "bad", files)))
    assert values[metric] == value
    flipped = [m for m in METRICS if values[m] != 0]
    assert flipped == [metric], flipped
    good = _values(_result(_repo(tmp_path / "good", GOOD)))
    assert good[metric] == 0


def test_a_logging_dependency_in_a_manifest_counts_without_an_import(
    tmp_path: Path,
) -> None:
    # bryony (T046 real repo): winston declared, no sampled file imports it.
    service = SERVICE.replace("import pino from 'pino';", "").replace("pino()", "{}")
    files = {**GOOD, "src/rename.service.ts": service}
    values = _values(_result(_repo(tmp_path / "a", files)))
    assert values["logging_library_missing"] == 1
    # Declared in a monorepo service's own manifest, as in bryony.
    files["backend/package.json"] = '{"dependencies": {"winston": "^3"}}\n'
    values = _values(_result(_repo(tmp_path / "b", files)))
    assert values["logging_library_missing"] == 0


def test_a_service_makefile_in_a_monorepo_is_a_setup(tmp_path: Path) -> None:
    files = {**_without("Makefile"), "backend/Makefile": "setup:\n\tnpm ci\n"}
    assert _values(_result(_repo(tmp_path, files)))["dev_environment_missing"] == 0


def test_only_exact_pattern_detectors_count_in_agent_config(tmp_path: Path) -> None:
    from easy_verifier.core.redact import _DETECTORS

    assert {name for name, _p in _DETECTORS} == {
        "private_key_pem", "aws_access_key_id", "aws_secret_access_key", "jwt",
        "credential_assignment",
    }
    # Template prose the heuristic detectors fire on (a hyphenated document
    # path with a digit, as in this repository's CLAUDE.md).
    prose = (
        "See [`docs/claude-md/phase0-project-initiation.md`]"
        "(docs/claude-md/phase0-project-initiation.md) for full detail.\n"
    )
    assert {h.detector for h in scan(prose).hits} - {
        "high_entropy_string", "key_material_segment"
    } == set()
    assert scan(prose).hits
    clean = _repo(tmp_path / "prose", {**GOOD, "CLAUDE.md": prose})
    assert _values(_result(clean))["agent_config_secrets_observed"] == 0
    # A planted AWS access key id, assembled at run time, never quoted.
    key = "AKIA" + "".join("QX7Z" for _ in range(4))
    planted = _repo(tmp_path / "key", {**GOOD, "AGENTS.md": f"key: {key}\n"})
    payload = _payload(planted)
    assert key not in json.dumps(payload)
    metric = next(
        m for m in payload["metrics"]["metrics"]
        if m["dimension"] == "operations"
        and m["name"] == "agent_config_secrets_observed"
    )
    assert metric["outcome"]["value"] == 1


def test_secret_in_agent_config_is_counted_and_never_quoted(tmp_path: Path) -> None:
    secret = _secret()
    assert scan(f'api_key = "{secret}"').hits  # the shared scanner sees it
    mcp = f'{{"env": {{"API_KEY": "{secret}"}}}}\n'
    repo = _repo(tmp_path, {**GOOD, ".mcp.json": mcp})
    payload = _payload(repo)
    assert secret not in json.dumps(payload)
    metric = next(
        m for m in payload["metrics"]["metrics"]
        if m["dimension"] == "operations"
        and m["name"] == "agent_config_secrets_observed"
    )
    assert metric["outcome"]["value"] >= 1
    assert ".mcp.json" in metric["derivation"]


def test_no_agent_files_abstains_guardrails_and_secrets(tmp_path: Path) -> None:
    # A repository without coding agents is not penalised (user 2026-10-07):
    # the instruction files are a documentation rule, reported missing only.
    files = _without("CLAUDE.md", ".claude/settings.json")
    values = _values(_result(_repo(tmp_path, files)))
    for name in ("agent_guardrails_missing", "agent_config_secrets_observed"):
        assert values[name].get("abstained"), name


def test_a_narrow_scope_never_reports_presence_as_missing(tmp_path: Path) -> None:
    repo = _repo(tmp_path, GOOD)
    _git(repo, "init", "-q")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "base")
    service = repo / "src/rename.service.ts"
    service.write_text(SERVICE + "// touched\n", encoding="utf-8")
    _git(repo, "commit", "-qam", "touch service")
    values = _values(_result(repo, scope="changes", ref="HEAD~1..HEAD"))
    missing = values["codeowners_missing"]
    assert missing.get("abstained") and "project scope" in missing["reason"]


# ---------------------------------------------------------------------------
# AC 3 - language/tool patterns live in the registry and generic layer
# ---------------------------------------------------------------------------


def test_patterns_come_from_the_registry_and_generic_layer() -> None:
    tables = curated_metric_tables()
    assert OPERATIONS_FIELDS == ("logging_markers",)
    for suffix, line in ((".ts", "import pino from 'pino';"),
                         (".py", "import logging"),
                         (".java", "import org.slf4j.Logger;"),
                         (".go", '\t"log/slog"'),
                         (".php", "use Psr\\Log\\LoggerInterface;")):
        assert tables.logging_markers[suffix].search(line), suffix
    assert not tables.logging_markers[".py"].search("import catalogging")
    # Language pin files are registry roles, not generic patterns.
    generic = " ".join(p for name in GENERIC_PATTERNS for p in GENERIC_PATTERNS[name])
    assert ".nvmrc" not in generic and ".python-version" not in generic
    source = Path(operations.__file__).read_text(encoding="utf-8")
    for token in ("pino", "slf4j", ".nvmrc", "CODEOWNERS\"", "approval_policy"):
        assert token not in source, token
