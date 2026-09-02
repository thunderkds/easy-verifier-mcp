"""T011 acceptance tests for dimension discovery (FR-013a)."""

from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path

import pytest

from easy_verifier import dimensions
from easy_verifier.adapters.cli import main as cli_main
from easy_verifier.dimensions import DIMENSIONS, list_dimensions

EXPECTED_NAMES = {
    "architecture",
    "solution-fit",
    "requirement-fidelity",
    "test-strategy",
    "security",
    "blast-radius",
    "code-quality",
}


def test_discovery_returns_all_seven_descriptor_records() -> None:
    discovered = list_dimensions()

    assert {item.name for item in discovered} == EXPECTED_NAMES
    assert len(discovered) == 7
    for item in discovered:
        descriptor = DIMENSIONS[item.name]
        assert item.purpose == descriptor.purpose
        assert item.sources_sought == descriptor.sources_sought
        assert item.purpose.endswith(".")
        assert len(item.purpose.split()) >= 8
        assert item.sources_sought


def test_discovery_is_deterministic() -> None:
    assert list_dimensions() == list_dimensions()
    assert tuple(item.name for item in list_dimensions()) == tuple(
        sorted(EXPECTED_NAMES)
    )


def test_discovery_takes_no_repository_argument() -> None:
    assert not inspect.signature(list_dimensions).parameters


def test_a_new_public_dimension_module_is_discovered_without_registry_edit(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module_name = "easy_verifier.dimensions.dynamic_probe"
    module_path = tmp_path / "dynamic_probe.py"
    module_path.write_text(
        """
from easy_verifier.core.models import DimensionDescriptor

DESCRIPTOR = DimensionDescriptor(
    name="dynamic-probe",
    purpose="Gather declared probe evidence so callers can inspect dynamic discovery.",
    sources_sought=("PROBE.md",),
    collect=lambda context: iter(()),
)
""".lstrip(),
        encoding="utf-8",
    )
    monkeypatch.setattr(dimensions, "__path__", [*dimensions.__path__, str(tmp_path)])
    sys.modules.pop(module_name, None)

    discovered = list_dimensions()

    assert "dynamic-probe" not in DIMENSIONS
    assert "dynamic-probe" in {item.name for item in discovered}
    sys.modules.pop(module_name, None)


def test_private_helper_module_is_explicitly_excluded() -> None:
    assert "_doc_extract" not in {item.name for item in list_dimensions()}


def test_a_public_module_without_a_descriptor_fails_loudly(
    tmp_path: Path, monkeypatch
) -> None:
    (tmp_path / "broken_probe.py").write_text("VALUE = 1\n", encoding="utf-8")
    monkeypatch.setattr(dimensions, "__path__", [*dimensions.__path__, str(tmp_path)])
    sys.modules.pop("easy_verifier.dimensions.broken_probe", None)

    with pytest.raises(RuntimeError, match="broken_probe.*DESCRIPTOR"):
        list_dimensions()

    sys.modules.pop("easy_verifier.dimensions.broken_probe", None)


def test_an_empty_sources_list_is_surfaced_honestly(
    tmp_path: Path, monkeypatch
) -> None:
    module_name = "easy_verifier.dimensions.empty_probe"
    (tmp_path / "empty_probe.py").write_text(
        """
from easy_verifier.core.models import DimensionDescriptor

DESCRIPTOR = DimensionDescriptor(
    name="empty-probe",
    purpose=(
        "Gather no declared sources while transparently exposing that empty "
        "contract."
    ),
    sources_sought=(),
    collect=lambda context: iter(()),
)
""".lstrip(),
        encoding="utf-8",
    )
    monkeypatch.setattr(dimensions, "__path__", [*dimensions.__path__, str(tmp_path)])
    sys.modules.pop(module_name, None)

    by_name = {item.name: item for item in list_dimensions()}

    assert by_name["empty-probe"].sources_sought == ()
    sys.modules.pop(module_name, None)


def test_cli_list_dimensions_prints_the_rich_records_deterministically(capsys) -> None:
    assert cli_main(["list-dimensions"]) == 0
    first = capsys.readouterr().out
    assert cli_main(["list-dimensions"]) == 0
    second = capsys.readouterr().out

    assert first == second
    payload = json.loads(first)
    assert {item["name"] for item in payload} == EXPECTED_NAMES
    assert all(item["purpose"] and item["sources_sought"] for item in payload)
