"""T041 - the ``supply-chain`` dimension (FR-050..052, NFR-009).

Areas #20 dependencies and licences, #21 CI reproducibility, #22 provenance,
SBOM and signing. Each sabotage pair varies one predicate, so a metric that
ignored the predicate would fail here.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from easy_verifier.core.judge import (
    AREAS,
    DOCUMENTATION_RULES,
    RATING_RULES,
    Citation,
)
from easy_verifier.core.metric_tables import curated_metric_tables
from easy_verifier.core.roles import GENERIC_CI_FACTS, GENERIC_PATTERNS
from easy_verifier.core.score import score_repository
from easy_verifier.dimensions import DIMENSIONS, list_dimensions, supply_chain

SHA = "a" * 40
ROLES = (
    "package-manifest",
    "lockfile",
    "ci-workflow",
    "licence-file",
    "release-config",
)

CI = f"""name: ci
on: push
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@{SHA} # v4
      - run: npm ci
"""
RELEASE = f"""name: release
on: push
jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/attest-build-provenance@{SHA}
"""
GOOD = {
    "package.json": '{"name": "x", "version": "1.0.0", "license": "MIT"}\n',
    "package-lock.json": '{"lockfileVersion": 3}\n',
    "LICENSE": "MIT License\n\nCopyright (c) 2026 x\n",
    ".github/workflows/ci.yml": CI,
    ".github/workflows/release.yml": RELEASE,
    ".releaserc.json": '{"branches": ["main"]}\n',
    "docs/rollback.md": "# Rollback\nRedeploy the previous tag.\n",
}


def _repo(tmp_path: Path, files: dict[str, str]) -> Path:
    for relative, text in files.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return tmp_path


def _result(repo: Path) -> dict:
    payload = json.loads(score_repository(repo, scope="project").serialize())
    rating = next(r for r in payload["ratings"] if r["dimension"] == "supply-chain")
    metrics = {
        m["name"]: m["outcome"]
        for m in payload["metrics"]["metrics"]
        if m["dimension"] == "supply-chain"
    }
    return {"rating": rating, "metrics": metrics}


def _inputs(result: dict) -> dict[str, dict]:
    return {item["metric_name"]: item for item in result["rating"]["inputs"]}


# ---------------------------------------------------------------------------
# AC 1 - discoverable, with purpose and the five source roles
# ---------------------------------------------------------------------------


def test_dimension_is_discoverable_with_purpose_and_five_roles() -> None:
    item = next(d for d in list_dimensions() if d.name == "supply-chain")
    assert item.purpose.endswith(".")
    assert (
        "not verifiable offline" in item.purpose or "cannot be verified" in item.purpose
    )
    assert tuple(role.name for role in item.roles) == ROLES
    assert item.sources_sought == ROLES
    assert DIMENSIONS["supply-chain"] is supply_chain.DESCRIPTOR
    assert all(role.patterns for role in item.roles)


# ---------------------------------------------------------------------------
# AC 2 - every rule cites its metric and threshold, and names its area
# ---------------------------------------------------------------------------


def test_rules_are_cited_labelled_by_area_and_weigh_100() -> None:
    rules = RATING_RULES["supply-chain"]
    assert sum(rule.weight for rule in rules.values()) == 100
    assert {rule.area for rule in rules.values()} == {AREAS[19], AREAS[20], AREAS[21]}
    for rule in rules.values():
        assert rule.metric_citation
        assert isinstance(rule.threshold_citation, Citation)
        assert all(c.url.startswith("https://") for c in rule.metric_citation)


def test_rollback_is_a_documentation_rule_never_a_number() -> None:
    (rule,) = DOCUMENTATION_RULES["supply-chain"]
    assert rule.area == AREAS[21]
    assert not hasattr(rule, "weight")
    assert rule.citation[0].url.startswith("https://")


# ---------------------------------------------------------------------------
# AC 5 - all rules met rates 100; no roles abstains with named misses
# ---------------------------------------------------------------------------


def test_fixture_where_every_rule_is_met_rates_100_with_rollback_present(
    tmp_path: Path,
) -> None:
    result = _result(_repo(tmp_path, GOOD))
    rating = result["rating"]
    assert rating["kind"] != "rating_abstention", rating
    assert rating["value"] == 100
    inputs = _inputs(result)
    assert set(inputs) == set(RATING_RULES["supply-chain"])
    assert all(item["passed"] for item in inputs.values())
    assert all(item["computed_from"] for item in inputs.values())
    (documentation,) = rating["documentation"]
    assert documentation["status"] == "present"
    assert documentation["file"] == "docs/rollback.md"


def test_repository_with_none_of_the_roles_abstains_naming_every_miss(
    tmp_path: Path,
) -> None:
    result = _result(_repo(tmp_path, {"notes.txt": "nothing relevant\n"}))
    rating = result["rating"]
    assert rating["kind"] == "rating_abstention"
    assert rating["reason_code"] == "below_coverage_floor"
    assert "value" not in rating
    assert [miss["source"] for miss in rating["sources_missing"]] == list(ROLES)
    assert rating["achieved_coverage"] == 0.0
    (documentation,) = rating["documentation"]
    assert documentation["status"] == "missing"


# ---------------------------------------------------------------------------
# sabotage pairs: one predicate each
# ---------------------------------------------------------------------------


def _without(*names: str) -> dict[str, str]:
    return {k: v for k, v in GOOD.items() if k not in names}


@pytest.mark.parametrize(
    ("changed", "metric", "expected"),
    [
        (_without("package-lock.json"), "lockfile_missing", 1),
        (_without("LICENSE"), "licence_file_missing", 1),
        (
            {**GOOD, ".github/workflows/ci.yml": CI.replace(f"@{SHA}", "@v4")},
            "ci_actions_unpinned_share",
            0.5,  # the release workflow's reference is still pinned
        ),
        (
            {**GOOD, ".github/workflows/ci.yml": CI.replace("npm ci", "npm install")},
            "ci_lockfile_install_missing",
            1,
        ),
        (
            {
                **GOOD,
                ".github/workflows/release.yml": RELEASE.replace(
                    "attest-build-provenance", "create-tag"
                ),
            },
            "ci_provenance_step_missing",
            1,
        ),
    ],
)
def test_each_predicate_flips_exactly_its_metric(
    tmp_path: Path, changed: dict[str, str], metric: str, expected: float
) -> None:
    result = _result(_repo(tmp_path, changed))
    inputs = _inputs(result)
    assert inputs[metric]["metric_value"] == expected
    assert inputs[metric]["passed"] is False
    others = {n: i["passed"] for n, i in inputs.items() if n != metric}
    assert all(others.values()), others
    assert (
        result["rating"]["value"] == 100 - RATING_RULES["supply-chain"][metric].weight
    )


def test_a_tag_reference_in_a_comment_is_not_a_reference(tmp_path: Path) -> None:
    ci = CI + "      # - uses: actions/setup-node@v4\n"
    result = _result(_repo(tmp_path, {**GOOD, ".github/workflows/ci.yml": ci}))
    assert _inputs(result)["ci_actions_unpinned_share"]["metric_value"] == 0


def test_local_and_digest_references_are_not_unpinned(tmp_path: Path) -> None:
    digest = "sha256:" + "b" * 64
    ci = CI + (
        "      - uses: ./.github/actions/local\n"
        f"      - uses: docker://alpine@{digest}\n"
    )
    result = _result(_repo(tmp_path, {**GOOD, ".github/workflows/ci.yml": ci}))
    assert _inputs(result)["ci_actions_unpinned_share"]["metric_value"] == 0


def test_step_images_are_external_references_in_any_ci_system(
    tmp_path: Path,
) -> None:
    # bryony (2026-10-07, user decision D1): a Drone pipeline references its
    # steps by container image, never `uses:`; the pin rule judges them.
    drone = (
        "kind: pipeline\nsteps:\n- name: lint\n"
        "  image: acme/backend-base:master\n  commands:\n    - npm ci\n"
        f"- name: test\n  image: node@sha256:{'c' * 64}\n"
    )
    files = _without(".github/workflows/ci.yml")
    files[".drone.yml"] = drone
    result = _result(_repo(tmp_path, files))
    # the tag is unpinned; the digest and release.yml's SHA action are pinned
    assert _inputs(result)["ci_actions_unpinned_share"]["metric_value"] == 1 / 3


def test_github_service_image_counts_as_an_external_reference(
    tmp_path: Path,
) -> None:
    ci = CI + "    services:\n      db:\n        image: postgres:16-alpine\n"
    result = _result(_repo(tmp_path, {**GOOD, ".github/workflows/ci.yml": ci}))
    # the service image is unpinned; both SHA-pinned actions are pinned
    assert _inputs(result)["ci_actions_unpinned_share"]["metric_value"] == 1 / 3


def test_workflow_without_external_references_abstains_the_pin_rule(
    tmp_path: Path,
) -> None:
    ci = "name: ci\non: push\njobs:\n  b:\n    steps:\n      - run: npm ci\n"
    result = _result(
        _repo(
            tmp_path,
            {
                **GOOD,
                ".github/workflows/ci.yml": ci,
                ".github/workflows/release.yml": "name: r\n",
            },
        )
    )
    assert result["metrics"]["ci_actions_unpinned_share"]["abstained"] is True
    assert "ci_actions_unpinned_share" not in _inputs(result)
    # the remaining rules still rate; the abstained one is named, not scored
    unavailable = [name for name, _reason in result["rating"]["unavailable_metrics"]]
    assert "ci_actions_unpinned_share" in unavailable


def test_no_ci_workflow_abstains_the_ci_rules_instead_of_scoring_them(
    tmp_path: Path,
) -> None:
    files = _without(
        ".github/workflows/ci.yml", ".github/workflows/release.yml", ".releaserc.json"
    )
    result = _result(_repo(tmp_path, files))
    for name in (
        "ci_actions_unpinned_share",
        "ci_lockfile_install_missing",
        "ci_provenance_step_missing",
    ):
        assert result["metrics"][name]["abstained"] is True, name
    # T067 (DDR-0010): the CI rules hold 65 of 100 rule weight, so with them
    # unmeasured the dimension gets no number rather than a 35-weight score.
    rating = result["rating"]
    assert rating["kind"] == "rating_abstention"
    assert rating["reason_code"] == "insufficient_measured_weight"
    assert rating["measured_share"] == "0.35"


def test_provenance_step_in_release_configuration_counts(tmp_path: Path) -> None:
    files = _without(".github/workflows/release.yml")
    files[".goreleaser.yaml"] = (
        "sboms:\n  - artifacts: archive\nsigns:\n  - cmd: cosign\n"
    )
    result = _result(_repo(tmp_path, files))
    assert _inputs(result)["ci_provenance_step_missing"]["metric_value"] == 0


def test_metrics_only_compute_over_the_supply_chain_pack(tmp_path: Path) -> None:
    payload = json.loads(
        score_repository(_repo(tmp_path, GOOD), scope="project").serialize()
    )
    for metric in payload["metrics"]["metrics"]:
        if metric["dimension"] != "supply-chain" and metric["name"].startswith("ci_"):
            assert metric["outcome"]["abstained"] is True


# ---------------------------------------------------------------------------
# AC 3 - patterns live in the registry / generic layer, not the module
# ---------------------------------------------------------------------------


def test_licence_role_matches_licence_files_never_source_code() -> None:
    # Stage 4 P1: a stem glob (**/License*) matched licensing source code.
    from easy_verifier.core.roles import _matcher

    matches = _matcher(GENERIC_PATTERNS["licence-file"])
    for path in ("LICENSE", "LICENSE.md", "LICENSE-MIT", "LICENSES/MIT.txt",
                 "design/LICENSE.md", "license.txt", "COPYING"):
        assert matches(path), path
    for path in ("src/licenseService.ts", "app/Models/License.php",
                 "web/src/components/LicenseBadge.tsx"):
        assert not matches(path), path


def test_a_hyphenated_image_key_is_not_an_image_reference() -> None:
    # Stage 4 P2: `base-image:` must not read as `image:`; list items still do.
    pattern = curated_metric_tables().action_reference
    assert pattern.search("    base-image: acme/x:1") is None
    assert pattern.search("  - image: acme/x:1")[1] == "acme/x:1"
    uses = pattern.search("      - uses: actions/checkout@v4")
    assert uses[1] == "actions/checkout@v4"


def test_ecosystem_patterns_come_from_the_registry_and_generic_layer() -> None:
    tables = curated_metric_tables()
    for command in ("npm ci", "pnpm install --frozen-lockfile", "cargo build --locked"):
        assert tables.lockfile_install.search(command), command
    assert not tables.lockfile_install.search("npm install")
    assert tables.provenance_steps.search("run: cosign sign image")
    assert tables.ci_files(".github/workflows/ci.yml")
    assert tables.release_files(".goreleaser.yaml")
    # every generic CI fact carries its link
    for facts in GENERIC_CI_FACTS.values():
        assert all(item.citation_url.startswith("https://") for item in facts)
    assert {"licence-file", "release-config"} <= set(GENERIC_PATTERNS)

    source = Path(supply_chain.__file__).read_text(encoding="utf-8")
    for literal in (
        "npm ci",
        "frozen-lockfile",
        "cosign",
        "syft",
        "package-lock",
        ".goreleaser",
    ):
        assert literal not in source, literal


# ---------------------------------------------------------------------------
# edge cases: monorepo budget per role
# ---------------------------------------------------------------------------


def test_many_lockfiles_in_a_monorepo_are_capped_shallowest_first_with_a_warning(
    tmp_path: Path,
) -> None:
    files = dict(GOOD)
    for index in range(supply_chain.MAX_FILES_PER_ROLE + 5):
        files[f"services/s{index:02d}/package-lock.json"] = "{}\n"
    from easy_verifier.core.pipeline import run_dimension

    pack = run_dimension(
        DIMENSIONS["supply-chain"], _repo(tmp_path, files), scope="project"
    )
    quoted = [e.path for e in pack.excerpts if e.path.endswith("package-lock.json")]
    assert len(quoted) == supply_chain.MAX_FILES_PER_ROLE
    assert "package-lock.json" in quoted  # the root file is never the one cut
    assert any("exceed the cap" in warning for warning in pack.warnings)
