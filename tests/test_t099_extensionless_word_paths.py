"""T099 — an extensionless lower-case word path keeps its file location.

``bin/build-push-kibana-docker-image`` came back ``bin/…****:e169e83f548e``: it has one
relative slash (so :data:`_PATHISH` misses it) and no file suffix (so the name exemption
misses it), and at 34 characters it scores 4.04 bits on the long-token rule.
"""

from __future__ import annotations

import pytest

from easy_verifier.core.redact import redact

TRIGGER = "bin/build-push-kibana-docker-image"


def test_trigger_path_survives() -> None:
    assert redact(TRIGGER) == TRIGGER


@pytest.mark.parametrize(
    "path",
    [
        "scripts/deploy-all-the-things-to-production",
        "rancher2/cb/worker-get-job",
        "bin/build_push_kibana_docker_image_for_prod",
        "ops/release-2024-build-push-kibana-docker-image",
        "tools/py3/build-push-kibana-docker-image",
    ],
)
def test_lower_case_slash_bearing_word_paths_survive(path: str) -> None:
    assert redact(path) == path
    line = f"see {path} for details"
    assert redact(line) == line


def test_bare_identifier_without_slash_is_judged_as_before() -> None:
    bare = "build-push-kibana-docker-image-tool"
    assert redact(bare) != bare


@pytest.mark.parametrize(
    "text",
    [
        "bin/Build-PushKibana-DockerImage-Tool",  # mixed case, no suffix
        "bin/BUILD-PUSH-KIBANA-DOCKER-IMAGE-TOOL",  # upper case, no suffix
        "bin/aB3xK9mQzR7tWvY2pL8nC4dF",
        "bin/aB3xK9mQzR7tWvY2pL8nC4dFeG",
        "bin/a1b2c3d4e5f6g7h8j9k0l1m2n3p4q5r6",  # interleaved digits
        "bin/3f9a2b1c-7d8e4a5b-6c7d8e9f-0a1b2c3d",  # digits before letters
        "AKIA" + "IOSFODNN7EXAMPLE",
        "https://hooks.slack.com/services/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",
        "postgres://admin:aB3xK9mQzR7tWvY2pL8nC4dFeG@db.internal/app",
        "https://example.org/hook?token=aB3xK9mQzR7tWvY2pL8nC4dFeG",
    ],
)
def test_other_shapes_stay_fingerprinted(text: str) -> None:
    assert redact(text) != text
