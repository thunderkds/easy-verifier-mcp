"""The dimension descriptors.

``DIMENSIONS`` is an explicit dict, deliberately not a decorator-populated
registry: a registry adds a failure mode flat wiring does not have — a dimension
silently missing because its module was never imported.

The security descriptor landed in T008, test-strategy in T009, blast-radius in
T010 — all seven of FR-010's dimensions are wired here explicitly.
"""

from __future__ import annotations

from ..core.models import DimensionDescriptor
from . import (
    architecture,
    blast_radius,
    code_quality,
    requirement_fidelity,
    security,
    solution_fit,
    test_strategy,
)

DIMENSIONS: dict[str, DimensionDescriptor] = {
    architecture.NAME: architecture.DESCRIPTOR,
    solution_fit.NAME: solution_fit.DESCRIPTOR,
    requirement_fidelity.NAME: requirement_fidelity.DESCRIPTOR,
    code_quality.NAME: code_quality.DESCRIPTOR,
    security.NAME: security.DESCRIPTOR,
    test_strategy.NAME: test_strategy.DESCRIPTOR,
    blast_radius.NAME: blast_radius.DESCRIPTOR,
}
