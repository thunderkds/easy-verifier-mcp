"""The registry's language knowledge, compiled for ``core/metrics.py`` (T031).

``metrics.py`` must read nothing (FR-027), so it cannot load the reference
registry itself. This module turns an already-loaded
:class:`~easy_verifier.core.registry.Registry` into the plain
:class:`~easy_verifier.core.metrics.LanguageTables` it is handed: one copy of
every language table, the registry's (FR-041).

Every curated language applies to every pack, as the former hard-coded tables
did: a pack is a bounded sample, so manifest detection over it would be
unreliable. Languages outside the registry get only the generic, language-free
rules in ``metrics.py`` (directory evidence); ``extra_source_extensions`` is the
seam through which vendored extension data (T032, Linguist) makes their files
count as source without any language-specific test rule.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from fnmatch import translate
from functools import lru_cache

from .metrics import LanguageTables
from .registry import Registry, RegistryEntry
from .roles import _registry

_NEVER = re.compile(r"(?!)")
_CLASS = re.compile(r"<((?:[A-Za-z0-9]-[A-Za-z0-9]|[A-Za-z0-9_])+)>")
_RANGE = re.compile(r"([A-Za-z0-9])-([A-Za-z0-9])")


def metric_tables(
    registry: Registry, *, extra_source_extensions: Iterable[str] = ()
) -> LanguageTables:
    """Compile ``registry``'s language entries into :class:`LanguageTables`.

    Languages apply in name order; a value two languages share (``@Test``) is
    kept once, so it is never counted twice.
    """
    entries = [registry.languages[name] for name in sorted(registry.languages)]
    suffixes: dict[str, None] = dict.fromkeys(extra_source_extensions)
    candidates: dict[str, dict[str, None]] = {}
    for entry in entries:
        extensions = _values(entry, "source_extensions")
        suffixes.update(dict.fromkeys(extensions))
        for extension in extensions:
            candidates.setdefault(extension, {}).update(
                dict.fromkeys(_values(entry, "test_candidates"))
            )

    assertions = _union(entries, "assertions")
    return LanguageTables(
        source_suffixes=frozenset(suffixes),
        test_name_patterns=tuple(
            re.compile(translate(glob))
            for glob in _union(entries, "test_name_patterns")
        ),
        test_candidates={
            suffix: tuple(templates)
            for suffix, templates in sorted(candidates.items())
            if templates
        },
        test_declarations=tuple(
            re.compile(r"^\s*" + token_regex(token), re.MULTILINE)
            for token in _union(entries, "test_declarations")
        ),
        assertions=re.compile(
            "|".join(
                token_regex(token)
                for token in sorted(assertions, key=len, reverse=True)
            )
        )
        if assertions
        else _NEVER,
    )


@lru_cache(maxsize=1)
def curated_metric_tables() -> LanguageTables:
    """Tables from the curated registry ``roles`` already loaded, once."""
    return metric_tables(_registry())


def token_regex(token: str) -> str:
    """Translate one registry code token (syntax in ``core/registry.py``).

    Only ``\\w*``, ``\\w``, a character class, ``\\s*``/``\\s+``, escaped
    literals and word boundaries can come out, so a token cannot inject regex.
    """
    parts: list[str] = []
    index = 0
    while index < len(token):
        char = token[index]
        klass = _CLASS.match(token, index) if char == "<" else None
        if klass and all(a <= b for a, b in _RANGE.findall(klass[1])):
            parts.append(f"[{klass[1]}]")
            index = klass.end()
            continue
        if char == "*":
            if not parts or parts[-1] != r"\w*":  # "**" would only backtrack
                parts.append(r"\w*")
        elif char == "?":
            parts.append(r"\w")
        elif char == " ":
            before = token[index - 1] if index else ""
            after = token[index + 1] if index + 1 < len(token) else ""
            parts.append(r"\s+" if _word(before) and _word(after) else r"\s*")
        else:
            parts.append(re.escape(char))
        index += 1
    head = r"\b" if _word(token[:1]) else ""
    tail = r"\b" if _word(token[-1:]) else ""
    return head + "".join(parts) + tail


def _word(char: str) -> bool:
    return bool(char) and (char.isalnum() or char == "_")


def _values(entry: RegistryEntry, field: str) -> list[str]:
    return [value for cited in entry.fields.get(field, ()) for value in cited.value]


def _union(entries: list[RegistryEntry], field: str) -> list[str]:
    return list(dict.fromkeys(v for entry in entries for v in _values(entry, field)))


__all__ = ["curated_metric_tables", "metric_tables", "token_regex"]
