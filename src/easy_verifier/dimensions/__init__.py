"""The dimension descriptors.

``DIMENSIONS`` is an explicit dict, deliberately not a decorator-populated
registry: a registry adds a failure mode flat wiring does not have — a dimension
silently missing because its module was never imported.

One more descriptor (blast-radius) lands in T010.
The security descriptor landed in T008, test-strategy in T009.
"""

from __future__ import annotations

from ..core.models import DimensionDescriptor
from . import (
    architecture,
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
}
