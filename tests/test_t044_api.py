"""T044: the ``api`` dimension (area #7 API contracts, validation, versioning).

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
    RATING_RULES,
    Citation,
    CoverageFloor,
)
from easy_verifier.core.metric_tables import curated_metric_tables
from easy_verifier.core.roles import GENERIC_API_FACTS, _matcher, role
from easy_verifier.core.score import score_repository
from easy_verifier.dimensions import DIMENSIONS, api, list_dimensions

ROLES = (
    "api-spec",
    "route definitions in source files",
    "request validation in source files",
)

SPEC = """openapi: 3.1.0
info:
  title: Shop
  version: 1.0.0
paths:
  /v1/users:
    get:
      summary: list users
"""

ROUTES = """import { Router } from 'express';
const router = Router();
router.get('/v1/users', listUsers);
router.post('/v1/users', createUser);
export default router;
"""

VALIDATION = """import { z } from 'zod';
export const createUserBody = z.object({ name: z.string() });
"""

GOOD = {
    "openapi.yaml": SPEC,
    "src/routes.ts": ROUTES,
    "src/schemas.ts": VALIDATION,
}


def _repo(tmp_path: Path, files: dict[str, str]) -> Path:
    for relative, text in files.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return tmp_path


def _result(repo: Path, **kwargs) -> dict:
    scope = kwargs.pop("scope", "project")
    payload = json.loads(score_repository(repo, scope=scope, **kwargs).serialize())
    rating = next(r for r in payload["ratings"] if r["dimension"] == "api")
    metrics = {
        m["name"]: m for m in payload["metrics"]["metrics"] if m["dimension"] == "api"
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
# AC 1 - discoverable, purpose and three source roles
# ---------------------------------------------------------------------------


def test_dimension_is_discoverable_with_purpose_and_three_roles() -> None:
    item = next(d for d in list_dimensions() if d.name == "api")
    assert item.purpose.endswith(".")
    assert "cannot be verified" in item.purpose
    assert tuple(r.name for r in item.roles) == ROLES
    assert item.sources_sought == ROLES
    assert DIMENSIONS["api"] is api.DESCRIPTOR
    assert item.roles[0].patterns  # the spec role is a file role


# ---------------------------------------------------------------------------
# AC 2 - four cited rules on area #7; AC 4 - floor 0.25 inclusive
# ---------------------------------------------------------------------------


def test_four_rules_are_cited_on_area_7_and_weigh_100() -> None:
    rules = RATING_RULES["api"]
    assert set(rules) == {
        "api_spec_missing",
        "api_version_missing",
        "request_validation_missing",
        "breaking_api_changes_observed",
    }
    assert sum(rule.weight for rule in rules.values()) == 100
    assert {rule.area for rule in rules.values()} == {AREAS[6]}
    assert AREAS[6] == "API contracts, validation, versioning"
    for rule in rules.values():
        assert isinstance(rule.threshold_citation, Citation)
        assert all(c.url.startswith("https://") for c in rule.metric_citation)
    assert COVERAGE_FLOORS["api"] == CoverageFloor(0.25, "inclusive")


# ---------------------------------------------------------------------------
# AC 5 - every rule met rates 100 (changes scope, so all four compute)
# ---------------------------------------------------------------------------


def test_fixture_where_every_rule_is_met_rates_100(tmp_path: Path) -> None:
    repo = _repo(tmp_path, GOOD)
    _git(repo, "init", "-q")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "base")
    # The change touches the spec, a route and a schema: under a narrow scope
    # presence is judged only from the changed files.
    health = "router.get('/v1/health', health);\nexport default"
    (repo / "src/routes.ts").write_text(
        ROUTES.replace("export default", health), encoding="utf-8"
    )
    (repo / "openapi.yaml").write_text(
        SPEC + "  /v1/health:\n    get: {}\n", encoding="utf-8"
    )
    (repo / "src/schemas.ts").write_text(
        VALIDATION + "export const q = z.object({});\n", encoding="utf-8"
    )
    _git(repo, "commit", "-qam", "add health route")
    result = _result(repo, scope="changes", ref="HEAD~1..HEAD")
    rating = result["rating"]
    assert rating["kind"] != "rating_abstention", rating
    assert rating["value"] == 100
    inputs = {item["metric_name"]: item for item in rating["inputs"]}
    assert set(inputs) == set(RATING_RULES["api"])
    assert all(item["passed"] for item in inputs.values())


def test_project_scope_rates_100_with_breaking_change_abstaining(
    tmp_path: Path,
) -> None:
    result = _result(_repo(tmp_path, GOOD))
    assert result["rating"]["value"] == 100
    values = _values(result)
    assert values["api_spec_missing"] == 0
    assert values["api_version_missing"] == 0
    assert values["request_validation_missing"] == 0
    assert "changes-scope diff" in str(values["breaking_api_changes_observed"])


def test_repository_with_none_of_the_roles_abstains_naming_every_miss(
    tmp_path: Path,
) -> None:
    result = _result(_repo(tmp_path, {"notes.txt": "nothing relevant\n"}))
    rating = result["rating"]
    assert rating["kind"] == "rating_abstention"
    assert rating["reason_code"] == "below_coverage_floor"
    assert "value" not in rating
    assert [m["source"] for m in rating["sources_missing"]] == list(ROLES)


def test_library_with_validation_but_no_api_abstains_never_zero(
    tmp_path: Path,
) -> None:
    """Edge case: an internal library (no route, no spec) is not rated 0."""
    result = _result(_repo(tmp_path, {"src/schemas.ts": VALIDATION}))
    rating = result["rating"]
    assert rating["kind"] == "rating_abstention"
    assert rating["reason_code"] == "all_metrics_abstained"
    assert "value" not in rating


# ---------------------------------------------------------------------------
# sabotage pairs: each predicate flipped alone
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("files", "metric"),
    [
        ({k: v for k, v in GOOD.items() if k != "openapi.yaml"}, "api_spec_missing"),
        (
            {**GOOD, "openapi.yaml": SPEC.replace("/v1", ""),
             "src/routes.ts": ROUTES.replace("/v1", "")},
            "api_version_missing",
        ),
        (
            {k: v for k, v in GOOD.items() if k != "src/schemas.ts"},
            "request_validation_missing",
        ),
    ],
)
def test_each_predicate_flips_exactly_its_metric(
    tmp_path: Path, files: dict[str, str], metric: str
) -> None:
    values = _values(_result(_repo(tmp_path, files)))
    assert values[metric] == 1
    presence = ("api_spec_missing", "api_version_missing", "request_validation_missing")
    for other in presence:
        if other != metric:
            assert values[other] == 0, other


def test_removed_route_and_spec_path_are_breaking_changes(tmp_path: Path) -> None:
    repo = _repo(tmp_path, GOOD)
    _git(repo, "init", "-q")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "base")
    (repo / "src/routes.ts").write_text(
        ROUTES.replace("router.post('/v1/users', createUser);\n", ""), encoding="utf-8"
    )
    (repo / "openapi.yaml").write_text(
        SPEC.replace("  /v1/users:", "  /v1/people:"), encoding="utf-8"
    )
    _git(repo, "commit", "-qam", "drop create")
    metric = _result(repo, scope="changes", ref="HEAD~1..HEAD")["metrics"][
        "breaking_api_changes_observed"
    ]
    assert metric["outcome"]["value"] == 2, metric
    assert "POST /v1/users" in metric["derivation"]
    assert "/v1/users" in metric["derivation"]


def test_a_spec_generated_from_code_counts_as_a_spec(tmp_path: Path) -> None:
    """Edge case: a spec generated at run time (not committed) is credited,
    and the derivation says it is generated."""
    files = {k: v for k, v in GOOD.items() if k != "openapi.yaml"}
    files["src/main.ts"] = (
        "const document = SwaggerModule.createDocument(app, config);\n"
    )
    metric = _result(_repo(tmp_path, files))["metrics"]["api_spec_missing"]
    assert metric["outcome"]["value"] == 0
    assert "generates one" in metric["derivation"]


def test_a_narrow_scope_never_reports_presence_as_missing(tmp_path: Path) -> None:
    """Edge case: a change touching only routes does not make the spec or the
    validation 'missing'; they abstain and say presence is a project fact."""
    repo = _repo(tmp_path, GOOD)
    _git(repo, "init", "-q")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "base")
    (repo / "src/routes.ts").write_text(ROUTES + "// touch\n", encoding="utf-8")
    _git(repo, "commit", "-qam", "touch routes")
    values = _values(_result(repo, scope="changes", ref="HEAD~1..HEAD"))
    for name in ("api_spec_missing", "request_validation_missing"):
        assert values[name]["abstained"], name
        assert "project scope" in str(values[name]), name
    assert values["api_version_missing"] == 0  # the changed routes are versioned


def test_external_and_import_version_strings_are_not_api_versioning(
    tmp_path: Path,
) -> None:
    routes = ROUTES.replace("/v1", "") + (
        "import { v4 } from 'uuid/v4';\n"
        "const OPENAI = 'https://api.openai.com/v1/chat';\n"
        "const release = 'v1.2.3';\n"
    )
    files = {"src/routes.ts": routes, "src/schemas.ts": VALIDATION}
    assert _values(_result(_repo(tmp_path, files)))["api_version_missing"] == 1


def test_proto_package_version_counts_as_versioning(tmp_path: Path) -> None:
    files = {
        "src/routes.ts": ROUTES.replace("/v1", ""),
        "src/schemas.ts": VALIDATION,
        "proto/shop.proto": 'syntax = "proto3";\npackage shop.v1;\n',
    }
    assert _values(_result(_repo(tmp_path, files)))["api_version_missing"] == 0


def test_a_versioned_client_url_outside_route_files_is_not_versioning(
    tmp_path: Path,
) -> None:
    files = {
        "src/routes.ts": ROUTES.replace("/v1", ""),
        "src/schemas.ts": VALIDATION,
        "src/client.ts": "const url = `${BASE}/v1/website/${site}`;\n",
    }
    assert _values(_result(_repo(tmp_path, files)))["api_version_missing"] == 1


def test_version_prefix_literal_counts_as_versioning(tmp_path: Path) -> None:
    routes = ROUTES.replace("/v1", "") + "app.use('/api/v2', router);\n"
    files = {"src/routes.ts": routes, "src/schemas.ts": VALIDATION}
    assert _values(_result(_repo(tmp_path, files)))["api_version_missing"] == 0


# ---------------------------------------------------------------------------
# AC 3 and review gotchas: patterns live in the registry / generic layer
# ---------------------------------------------------------------------------


def test_spec_role_matches_spec_files_never_source_code() -> None:
    match = _matcher(role("api-spec").patterns)
    for path in ("openapi.yaml", "docs/openapi.json", "api/swagger.yml",
                 "schema.graphql", "proto/shop/v1/shop.proto", "api.openapi.yaml"):
        assert match(path), path
    for path in ("src/configs/swagger.config.ts", "src/openapi.ts",
                 "src/swaggerService.ts", "src/graphql/resolver.ts", "src/proto.py"):
        assert not match(path), path


def test_patterns_come_from_the_registry_and_generic_layer() -> None:
    tables = curated_metric_tables()
    assert tables.request_validation[".ts"].search("z.object({")
    assert tables.request_validation[".py"].search("class Body(BaseModel):")
    assert tables.api_spec_generators[".py"].search("app = FastAPI(")
    assert tables.api_version_markers[".ts"].search("app.enableVersioning({")
    for facts in GENERIC_API_FACTS.values():
        assert all(item.citation_url.startswith("https://") for item in facts)
    source = Path(api.__file__).read_text(encoding="utf-8")
    for literal in ("zod", "z.object", "BaseModel", "SwaggerModule", "enableVersioning",
                    "openapi.yaml", ".proto\"", "IsString"):
        assert literal not in source, literal
