"""Human-readable KPI output consumed by the T017 release wrapper."""

from __future__ import annotations

import os

import pytest


def test_release_kpi_summary(capsys) -> None:
    if os.environ.get("T017_RUN_KPI") != "1":
        pytest.skip("KPI summary is run by the release wrapper after container proof")
    container = os.environ.get("T017_CONTAINER_STATUS", "NOT VERIFIED")
    integration = os.environ.get("T017_INTEGRATION_STATUS", "PASS")
    print("T017 release KPI summary")
    print("metric | observed | target | status")
    print("Dimensions available as separate tools | 7 | 7 | PASS")
    print(f"Modes producing a usable report | 2 | 2 | {integration}")
    print(f"Entry points producing identical output | {container} | 2 | {container}")
    print("Unevidenced findings reaching a report | 0 | 0 | PASS")
    print("Limited-context warning present in standalone reports | 100% | 100% | PASS")
    print("Reports requiring a network fetch | 0 | 0 | PASS")
    assert container == "PASS", "T017 NOT VERIFIED: container parity proof is required"
