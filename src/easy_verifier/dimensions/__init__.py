"""The dimension descriptors.

``DIMENSIONS`` is an explicit dict, deliberately not a decorator-populated
registry: a registry adds a failure mode flat wiring does not have — a dimension
silently missing because its module was never imported.

The security descriptor landed in T008, test-strategy in T009, blast-radius in
T010 — all seven of FR-010's dimensions are wired here explicitly.
"""

from __future__ import annotations

import pkgutil
from dataclasses import dataclass
from importlib import import_module

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


@dataclass(frozen=True)
class DimensionDiscovery:
    """Caller-facing static metadata for one available dimension."""

    name: str
    purpose: str
    sources_sought: tuple[str, ...]


def list_dimensions() -> tuple[DimensionDiscovery, ...]:
    """Discover public dimension modules and return their descriptor metadata.

    Modules beginning with ``_`` are package helpers, not dimensions. Every
    other module must expose ``DESCRIPTOR``; import or contract errors remain
    visible instead of silently producing an incomplete discovery response.
    """
    discovered: list[DimensionDiscovery] = []
    for module_info in pkgutil.iter_modules(__path__, prefix=f"{__name__}."):
        short_name = module_info.name.rsplit(".", 1)[-1]
        if short_name.startswith("_"):
            continue
        module = import_module(module_info.name)
        try:
            descriptor = module.DESCRIPTOR
        except AttributeError as exc:
            raise RuntimeError(
                f"dimension module {module_info.name!r} has no DESCRIPTOR"
            ) from exc
        discovered.append(
            DimensionDiscovery(
                name=descriptor.name,
                purpose=descriptor.purpose,
                sources_sought=descriptor.sources_sought,
            )
        )
    return tuple(sorted(discovered, key=lambda item: item.name))


def dimension_names() -> tuple[str, ...]:
    """The single source of valid dimension names, sorted for determinism.

    Any caller that needs to validate a requested name, or present the set of
    choices to a user, reads this — never a second, hand-maintained list
    (precedent: a duplicated list is how a checklist and its enforcement drift
    apart, per T003/T008/T010).
    """
    return tuple(item.name for item in list_dimensions())
