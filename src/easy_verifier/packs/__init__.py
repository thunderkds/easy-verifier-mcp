"""Optional packs (T047, DDR-0008 §4, FR-053).

A pack is a group of rules for one domain that a repository opts into through
``.easy-verifier.toml`` ``packs = [...]`` or an agent pick at the MCP detect
gate; it is never guessed. Each pack has a descriptor like a dimension's, its
rules in ``judge.RATING_RULES`` / ``judge.DOCUMENTATION_RULES``, its floor in
``judge.PACK_FLOORS`` and its patterns in ``registry/packs/<pack>.toml``.
"""

from __future__ import annotations

from ..core.models import DimensionDescriptor
from . import finance, healthcare

PACKS: dict[str, DimensionDescriptor] = {
    healthcare.NAME: healthcare.DESCRIPTOR,
    finance.NAME: finance.DESCRIPTOR,
}
