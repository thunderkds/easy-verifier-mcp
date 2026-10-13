"""T094 -- Kubernetes manifests, Compose files and cloud templates are
recognised by content when no name pattern places them (FR-076, DDR-0012).

Predicate tests (AC 1-5), role-resolution tests on temp repos (AC 6, 7, 9),
and the edge cases of the guide (BOM, CRLF, nested keys, huge files).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from easy_verifier.core import roles as roles_module
from easy_verifier.core.iac_content import (
    CLOUD,
    COMPOSE,
    K8S,
    classify,
)
from easy_verifier.core.roles import ORIGIN_RULES, resolve, role

K8S_ROLE = "k8s-manifest"
CONTAINER_ROLE = "container-config"
CLOUD_ROLE = "cloud-template"
IAC_ROLES = (role(K8S_ROLE), role(CONTAINER_ROLE), role(CLOUD_ROLE))

DEPLOYMENT = "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: web\n"


def _write(root: Path, files: dict[str, str]) -> Path:
    for relative, text in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


def _filled(root: Path) -> dict[str, tuple[str, ...]]:
    return resolve(root, IAC_ROLES).files


# --- AC 1, 2: Kubernetes by content ------------------------------------


def test_manifest_with_api_version_and_kind_is_k8s():
    assert K8S in classify(DEPLOYMENT)


def test_manifest_without_kind_is_not_k8s():
    assert classify("apiVersion: apps/v1\nmetadata:\n  name: web\n") == frozenset()


def test_manifest_without_api_version_is_not_k8s():
    assert classify("kind: Deployment\nmetadata:\n  name: web\n") == frozenset()


def test_only_second_document_needs_the_keys():
    text = "# header\nfoo: bar\n---\n" + DEPLOYMENT
    assert K8S in classify(text)


def test_keys_split_across_documents_do_not_count():
    assert classify("apiVersion: v1\n---\nkind: Pod\n") == frozenset()


def test_nested_api_version_is_not_a_manifest():
    text = "spec:\n  apiVersion: v1\n  kind: Pod\n"
    assert classify(text) == frozenset()


def test_bom_and_crlf_are_tolerated():
    text = "\ufeff" + DEPLOYMENT.replace("\n", "\r\n")
    assert K8S in classify(text)


def test_secret_manifest_is_placed_and_redacted_by_the_reader():
    text = "apiVersion: v1\nkind: Secret\ndata:\n  password: c2VjcmV0\n"
    assert K8S in classify(text)


def test_resolve_places_k8s_manifest_by_content(tmp_path):
    _write(tmp_path, {"ops/app.yml": DEPLOYMENT, "ops/other.yml": "kind: Deployment\n"})
    files = _filled(tmp_path)
    assert files[K8S_ROLE] == ("ops/app.yml",)


# --- AC 3: Compose by content -------------------------------------------


def test_compose_v2_services_with_image_or_build():
    assert COMPOSE in classify("services:\n  web:\n    image: nginx\n")
    assert COMPOSE in classify("services:\n  web:\n    build: .\n")


def test_compose_services_without_image_or_build_is_not_compose():
    assert classify("services:\n  web:\n    ports:\n      - '80:80'\n") == frozenset()


def test_compose_version_only_is_not_compose():
    assert classify("version: '3'\n") == frozenset()


def test_compose_v1_top_level_service_keys():
    text = 'web:\n  image: nginx\n  ports:\n    - "80:80"\ndb:\n  image: postgres\n'
    assert COMPOSE in classify(text)


def test_compose_v1_with_one_service_among_other_keys():
    text = "version: '1'\nnotes: x\nweb:\n  build: .\n"
    assert COMPOSE in classify(text)


def test_nested_image_key_two_levels_down_is_not_compose_v1():
    text = "web:\n  container:\n    image: nginx\n"
    assert classify(text) == frozenset()


def test_resolve_places_compose_files_by_content(tmp_path):
    _write(
        tmp_path,
        {
            "deploy/stack.yml": "services:\n  web:\n    image: nginx\n",
            "deploy/stack.dev.yml": 'web:\n  image: nginx\n  ports: ["80:80"]\n',
        },
    )
    assert _filled(tmp_path)[CONTAINER_ROLE] == (
        "deploy/stack.dev.yml",
        "deploy/stack.yml",
    )


# --- AC 4: precision ----------------------------------------------------

NEGATIVES = {
    "gitlab-ci": (
        ".gitlab-ci.yml",
        "stages:\n  - build\nbuild:\n  image: node:18\n  script:\n    - npm ci\n",
    ),
    "circleci": (
        "ci/circle.yml",
        "version: 2.1\njobs:\n  build:\n    docker:\n      - image: node:18\n"
        "    steps:\n      - checkout\n",
    ),
    "github-actions": (
        "automation/pipeline.yml",
        "name: ci\non: push\njobs:\n  build:\n    runs-on: ubuntu-latest\n"
        "    container:\n      image: node:18\n    steps:\n"
        "      - uses: actions/checkout@v4\n",
    ),
    "openapi": (
        "spec/api.yml",
        "openapi: 3.0.0\ninfo:\n  title: x\n  version: '1'\npaths:\n  /a:\n"
        "    get:\n      summary: s\n",
    ),
    "eslintrc": (
        ".eslintrc.yml",
        "root: true\nenv:\n  node: true\nrules:\n  semi: error\n",
    ),
    "helm-values": (
        "configs/values.yaml",
        "replicaCount: 2\nimage:\n  repository: nginx\n  tag: '1'\n"
        "service:\n  port: 80\n",
    ),
    "rancher-compose": (
        "elk/rancher-compose.yml",
        "elasticsearch:\n  scale: 1\n  health_check:\n    port: 9200\n",
    ),
}


@pytest.mark.parametrize("name", sorted(NEGATIVES))
def test_negative_fixtures_classify_as_nothing(name):
    assert classify(NEGATIVES[name][1]) == frozenset()


def test_negative_fixtures_fill_no_role_in_a_repo(tmp_path):
    _write(tmp_path, {path: text for path, text in NEGATIVES.values()})
    assert all(not paths for paths in _filled(tmp_path).values())


def test_huge_yaml_is_read_bounded_and_not_placed(tmp_path):
    body = "".join(f"key{i}: value{i}\n" for i in range(200_000))
    _write(tmp_path, {"data/dump.yml": body + DEPLOYMENT})
    assert _filled(tmp_path)[K8S_ROLE] == ()


# --- AC 5: cloud templates ----------------------------------------------


def test_cloud_template_by_format_version():
    assert CLOUD in classify("AWSTemplateFormatVersion: '2010-09-09'\n")


def test_cloud_template_by_resources_with_aws_type():
    text = "Resources:\n  Bucket:\n    Type: AWS::S3::Bucket\n"
    assert CLOUD in classify(text)
    typed = "Resources:\n  Fn:\n    Type: 'AWS::Serverless::Function'\n"
    assert CLOUD in classify(typed)


def test_resources_without_aws_type_is_not_cloud():
    assert classify("Resources:\n  Bucket:\n    Type: Other::Thing\n") == frozenset()
    assert classify("Resources:\n  - a\n  - b\n") == frozenset()


def test_resolve_places_cloud_template_by_content(tmp_path):
    _write(
        tmp_path,
        {"infra/stack.yml": "Resources:\n  B:\n    Type: AWS::S3::Bucket\n"},
    )
    assert _filled(tmp_path)[CLOUD_ROLE] == ("infra/stack.yml",)


# --- AC 6: precedence ----------------------------------------------------


def test_name_match_keeps_its_role_and_origin(tmp_path):
    # Matches container-config by name (docker-compose*.yml) although its
    # content is a manifest: content fills a role only when the name matched none.
    _write(tmp_path, {"docker-compose.yml": DEPLOYMENT, "k8s/app.yaml": DEPLOYMENT})
    resolution = resolve(tmp_path, IAC_ROLES)
    # ``**/k8s/**`` is also a container-config name pattern.
    assert resolution.files[CONTAINER_ROLE] == ("docker-compose.yml", "k8s/app.yaml")
    assert resolution.files[K8S_ROLE] == ("k8s/app.yaml",)
    assert resolution.origins[(CONTAINER_ROLE, "docker-compose.yml")] == ORIGIN_RULES
    assert resolution.origins[(K8S_ROLE, "k8s/app.yaml")] == ORIGIN_RULES


def test_content_placed_file_has_rules_origin(tmp_path):
    _write(tmp_path, {"ops/app.yml": DEPLOYMENT})
    resolution = resolve(tmp_path, IAC_ROLES)
    assert resolution.origins[(K8S_ROLE, "ops/app.yml")] == ORIGIN_RULES


def test_only_requested_roles_are_filled(tmp_path):
    _write(tmp_path, {"ops/app.yml": DEPLOYMENT})
    resolution = resolve(tmp_path, (role(CLOUD_ROLE),))
    assert resolution.files == {CLOUD_ROLE: ()}


# --- AC 7: exclusions ----------------------------------------------------


def test_third_party_and_excluded_directories_are_never_placed(tmp_path):
    _write(
        tmp_path,
        {
            "node_modules/pkg/app.yml": DEPLOYMENT,
            ".gitattributes": "vendor-ish/** linguist-vendored\n",
            "vendor-ish/app.yml": DEPLOYMENT,
            "ops/app.yml": DEPLOYMENT,
        },
    )
    assert _filled(tmp_path)[K8S_ROLE] == ("ops/app.yml",)


def test_secret_bearing_names_are_not_opened(tmp_path):
    _write(tmp_path, {".env.yml": DEPLOYMENT, "ops/app.yml": DEPLOYMENT})
    assert _filled(tmp_path)[K8S_ROLE] == ("ops/app.yml",)


def test_escaping_symlink_is_not_placed(tmp_path):
    outside = tmp_path / "outside"
    repo = tmp_path / "repo"
    _write(outside, {"app.yml": DEPLOYMENT})
    _write(repo, {"ops/real.yml": DEPLOYMENT})
    (repo / "ops" / "link.yml").symlink_to(outside / "app.yml")
    assert _filled(repo)[K8S_ROLE] == ("ops/real.yml",)


# --- AC 9: read once -----------------------------------------------------


def test_each_candidate_is_read_once_and_name_matched_files_not_at_all(
    tmp_path, monkeypatch
):
    _write(
        tmp_path,
        {
            "ops/app.yml": DEPLOYMENT,
            "ops/stack.yml": "services:\n  web:\n    image: nginx\n",
            "ops/plain.yml": "a: b\n",
            "k8s/named.yaml": DEPLOYMENT,
            "docker-compose.yml": "services:\n  web:\n    image: nginx\n",
            "src/code.py": "x = 1\n",
        },
    )
    reads: list[str] = []
    original = roles_module._read_head

    def spy(root, relative):
        reads.append(relative)
        return original(root, relative)

    monkeypatch.setattr(roles_module, "_read_head", spy)
    resolve(tmp_path, IAC_ROLES)
    assert sorted(reads) == ["ops/app.yml", "ops/plain.yml", "ops/stack.yml"]


def test_no_reads_when_no_iac_role_is_requested(tmp_path, monkeypatch):
    _write(tmp_path, {"ops/app.yml": DEPLOYMENT})
    monkeypatch.setattr(
        roles_module,
        "_read_head",
        lambda *_: pytest.fail("read although no IaC role was requested"),
    )
    resolve(tmp_path, (role("readme"),))
