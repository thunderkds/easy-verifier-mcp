"""T042: the ``infrastructure`` dimension (areas #11, #23, #24).

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
from easy_verifier.core.roles import GENERIC_INFRASTRUCTURE_FACTS, _matcher, role
from easy_verifier.core.score import score_repository
from easy_verifier.dimensions import DIMENSIONS, infrastructure, list_dimensions

ROLES = ("terraform-file", "k8s-manifest", "cloud-template", "container-config")
METRICS = (
    "iac_wildcard_iam_observed",
    "iac_open_ingress_observed",
    "iac_unencrypted_storage_observed",
    "terraform_locked_remote_state_missing",
    "terraform_environment_separation_missing",
    "database_backup_unconfigured",
    "database_ha_unconfigured",
)

BACKEND = """terraform {
  backend "gcs" {
    bucket = "acme-state"
  }
}
"""

DATABASE = """resource "aws_db_instance" "main" {
  engine                  = "postgres"
  storage_encrypted       = true
  backup_retention_period = 7
  multi_az                = true
}
"""

NETWORK = """resource "aws_security_group" "web" {
  ingress {
    from_port   = 443
    cidr_blocks = ["10.0.0.0/8"]
  }
  egress {
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_route" "out" {
  cidr_block = "0.0.0.0/0"
}
"""

POLICY = """data "aws_iam_policy_document" "read" {
  statement {
    actions   = ["s3:GetObject"]
    resources = ["arn:aws:s3:::acme/*"]
  }
}
"""

RBAC = """apiVersion: rbac.authorization.k8s.io/v1
kind: Role
rules:
  - apiGroups: [""]
    resources: ["pods"]
    verbs:
      - get
      - list
---
spec:
  hosts:
    - "*"
"""

GOOD = {
    "infra/main.tf": BACKEND + DATABASE + NETWORK + POLICY,
    "infra/prod.tfvars": 'region = "eu-west-1"\n',
    "k8s/role.yaml": RBAC,
    "Dockerfile": "FROM python:3.12-slim\n",
    "docs/disaster-recovery.md": "# Disaster recovery\n\nRestore from snapshot.\n",
}


def _repo(tmp_path: Path, files: dict[str, str]) -> Path:
    for relative, text in files.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return tmp_path


def _result(repo: Path, **kwargs) -> dict:
    payload = json.loads(score_repository(repo, **kwargs).serialize())
    rating = next(r for r in payload["ratings"] if r["dimension"] == "infrastructure")
    metrics = {
        m["name"]: m
        for m in payload["metrics"]["metrics"]
        if m["dimension"] == "infrastructure"
    }
    return {"rating": rating, "metrics": metrics}


def _values(result: dict) -> dict:
    return {
        name: m["outcome"]["value"]
        if not m["outcome"].get("abstained")
        else m["outcome"]
        for name, m in result["metrics"].items()
    }


def _main(old: str, new: str) -> dict:
    main = GOOD["infra/main.tf"]
    assert old in main, old
    return {**GOOD, "infra/main.tf": main.replace(old, new)}


# ---------------------------------------------------------------------------
# AC 1 - discoverable, purpose and source roles
# ---------------------------------------------------------------------------


def test_dimension_is_discoverable_with_purpose_and_roles() -> None:
    item = next(d for d in list_dimensions() if d.name == "infrastructure")
    assert item.purpose.endswith(".")
    assert "drift" in item.purpose and "cannot be verified offline" in item.purpose
    assert tuple(r.name for r in item.roles) == ROLES
    assert item.sources_sought == ROLES
    assert DIMENSIONS["infrastructure"] is infrastructure.DESCRIPTOR


def test_role_globs_match_their_files_and_never_source_code() -> None:
    files = {
        "terraform-file": ("main.tf", "infra/prod.tfvars", "x/main.tf.json",
                           "live/terragrunt.hcl"),
        "k8s-manifest": ("k8s/deploy.yaml", "kubernetes-manifests/cart.yaml",
                         "helm-chart/templates/a.yaml", "kustomize/kustomization.yaml",
                         "charts/app/Chart.yaml"),
        "cloud-template": ("stack.template.json", "template.yaml",
                           "cloudformation/db.yml", "Pulumi.dev.yaml"),
    }
    source = ("src/terraform.service.ts", "src/k8s/client.go", "src/main.tf.ts",
              "src/template.ts", "src/kubernetes/Client.java", "lib/pulumi.py",
              "src/cloudformation.ts", "src/helm/chart.go")
    for name, paths in files.items():
        match = _matcher(role(name).patterns)
        for path in paths:
            assert match(path), (name, path)
        for path in source:
            assert not match(path), (name, path)
    for rule in DOCUMENTATION_RULES["infrastructure"]:
        match = _matcher(rule.patterns)
        assert match("docs/disaster-recovery.md") and match("ops/DR.md")
        assert not any(match(path) for path in source)
        assert not match("src/restore.service.ts")


# ---------------------------------------------------------------------------
# AC 2 - cited rules per area; DR documentation rule; floor 0.25 (user)
# ---------------------------------------------------------------------------


def test_rules_are_cited_per_area_and_weigh_100() -> None:
    rules = RATING_RULES["infrastructure"]
    assert tuple(rules) == METRICS
    assert sum(rule.weight for rule in rules.values()) == 100
    assert {rules[m].area for m in METRICS[:3]} == {AREAS[10]}
    assert {rules[m].area for m in METRICS[3:5]} == {AREAS[22]}
    assert {rules[m].area for m in METRICS[5:]} == {AREAS[23]}
    for rule in rules.values():
        assert rule.threshold == 0 and rule.comparison == "at_most"
        assert isinstance(rule.threshold_citation, Citation)
        assert rule.threshold_citation.url.startswith("https://")
        assert all(c.url.startswith("https://") for c in rule.metric_citation)
    assert "CIS" in rules["iac_open_ingress_observed"].threshold_citation.label
    assert "HashiCorp" in rules[METRICS[3]].threshold_citation.label
    assert "Well-Architected" in rules[METRICS[5]].threshold_citation.label
    assert COVERAGE_FLOORS["infrastructure"] == CoverageFloor(0.25, "inclusive")
    (doc,) = DOCUMENTATION_RULES["infrastructure"]
    assert doc.area == AREAS[23] and "REL13" in doc.citation[0].label


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
    assert {n: _values(result)[n] for n in METRICS} == dict.fromkeys(METRICS, 0)
    assert "docs/disaster-recovery.md" in json.dumps(rating)


def test_repository_with_none_of_the_roles_abstains_naming_every_miss(
    tmp_path: Path,
) -> None:
    result = _result(_repo(tmp_path, {"src/app.py": "print('hi')\n"}))
    rating = result["rating"]
    assert rating["kind"] == "rating_abstention"
    assert rating["reason_code"] == "below_coverage_floor"
    assert "value" not in rating
    assert [m["source"] for m in rating["sources_missing"]] == list(ROLES)


def test_container_config_alone_abstains_rather_than_rating(tmp_path: Path) -> None:
    # One role reaches the floor, but no rule has IaC to measure: never a 0.
    rating = _result(_repo(tmp_path, {"Dockerfile": "FROM scratch\n"}))["rating"]
    assert rating["kind"] == "rating_abstention"
    assert "value" not in rating


# ---------------------------------------------------------------------------
# Sabotage pairs: each predicate flipped alone flips exactly its metric
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("files", "metric", "value"),
    [
        (_main('actions   = ["s3:GetObject"]', 'actions   = ["*"]'),
         "iac_wildcard_iam_observed", 1),
        ({**GOOD, "k8s/role.yaml": RBAC.replace("      - get\n", '      - "*"\n')},
         "iac_wildcard_iam_observed", 1),
        ({**GOOD, "cloudformation/iam.json":
          '{"Statement": [{"Effect": "Allow", "Action": "*", "Resource": "x"}]}\n'},
         "iac_wildcard_iam_observed", 1),
        (_main('cidr_blocks = ["10.0.0.0/8"]', 'cidr_blocks = ["0.0.0.0/0"]'),
         "iac_open_ingress_observed", 1),
        (_main("storage_encrypted       = true", "storage_encrypted       = false"),
         "iac_unencrypted_storage_observed", 1),
        (_main("  storage_encrypted       = true\n", ""),
         "iac_unencrypted_storage_observed", 1),
        (_main('backend "gcs"', 'backend "local"'),
         "terraform_locked_remote_state_missing", 1),
        (_main('backend "gcs"', 'backend "s3"'),
         "terraform_locked_remote_state_missing", 1),
        ({k: v for k, v in GOOD.items() if k != "infra/prod.tfvars"},
         "terraform_environment_separation_missing", 1),
        (_main("  backup_retention_period = 7\n", ""),
         "database_backup_unconfigured", 1),
        (_main("  multi_az                = true\n", ""),
         "database_ha_unconfigured", 1),
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


def test_s3_backend_with_a_lock_is_locked_state(tmp_path: Path) -> None:
    files = _main('backend "gcs" {', 'backend "s3" {\n    use_lockfile = true')
    values = _values(_result(_repo(tmp_path, files)))
    assert values["terraform_locked_remote_state_missing"] == 0


def test_a_variable_setting_is_not_verifiable_and_not_counted(tmp_path: Path) -> None:
    files = _main("multi_az                = true", "multi_az = var.ha")
    result = _result(_repo(tmp_path, files))
    assert _values(result)["database_ha_unconfigured"] == 0
    metric = json.dumps(result["metrics"]["database_ha_unconfigured"])
    assert "not verifiable offline" in metric


def test_without_a_database_the_database_rules_abstain(tmp_path: Path) -> None:
    files = _main(DATABASE, "")
    values = _values(_result(_repo(tmp_path, files)))
    for name in METRICS[5:]:
        assert values[name].get("abstained"), name


def test_a_narrow_scope_never_reports_presence_as_missing(tmp_path: Path) -> None:
    # A source file is touched: a diff of only IaC files trips a pre-existing
    # api-dimension citation error (breaking_api_changes_observed), reported
    # by T042 as out of scope.
    repo = _repo(tmp_path, {**GOOD, "src/app.py": "def main():\n    pass\n"})

    def git(*args: str) -> None:
        subprocess.run(
            ["git", "-c", "user.email=t@example.invalid", "-c", "user.name=t", *args],
            cwd=repo, check=True, capture_output=True,
        )

    git("init", "-q")
    git("add", ".")
    git("commit", "-q", "-m", "base")
    (repo / "src/app.py").write_text("def main():\n    return 1\n", encoding="utf-8")
    git("commit", "-qam", "touch source")
    values = _values(_result(repo, scope="changes", ref="HEAD~1..HEAD"))
    for name in METRICS[3:5]:
        missing = values[name]
        assert missing.get("abstained") and "scope" in missing["reason"], name


# ---------------------------------------------------------------------------
# AC 3 - tool-specific patterns live in the generic layer, not this module
# ---------------------------------------------------------------------------


def test_patterns_come_from_the_generic_layer() -> None:
    assert {"wildcard_iam", "open_cidr", "remote_backend", "database_resource"} <= set(
        GENERIC_INFRASTRUCTURE_FACTS
    )
    for items in GENERIC_INFRASTRUCTURE_FACTS.values():
        assert all(item.citation_url.startswith("https://") for item in items)
    source = Path(infrastructure.__file__).read_text(encoding="utf-8")
    for token in ("0.0.0.0", "aws_", "dynamodb", "multi_az", "cidr_blocks",
                  "backup_retention", "verbs", "STANDARD_HA"):
        assert token not in source, token


def test_a_secret_in_an_iac_file_is_never_quoted(tmp_path: Path) -> None:
    # Assembled at run time: never commit a realistic credential shape.
    secret = "FAKEfake" + "".join("Q7x9" for _ in range(6))
    files = _main(
        '  engine                  = "postgres"\n',
        f'  engine                  = "postgres"\n  password = "{secret}"\n',
    )
    payload = score_repository(_repo(tmp_path, files)).serialize()
    assert "infra/main.tf" in payload
    assert secret not in payload
