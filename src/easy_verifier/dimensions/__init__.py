"""The dimension descriptors.

``DIMENSIONS`` is an explicit dict, deliberately not a decorator-populated
registry: a registry adds a failure mode flat wiring does not have — a dimension
silently missing because its module was never imported.

Six more descriptors land in T006–T008.
"""

from __future__ import annotations

from ..core.models import DimensionDescriptor
from . import architecture

DIMENSIONS: dict[str, DimensionDescriptor] = {
    architecture.NAME: architecture.DESCRIPTOR,
}
