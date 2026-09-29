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

import dataclasses
import re
from collections.abc import Iterable, Mapping
from fnmatch import translate
from pathlib import PurePosixPath

from .judge import Citation
from .metrics import LanguageTables, Metric, MetricAbstention, MetricSet, SinkPattern
from .models import CombinedPack
from .registry import (
    AGENT_RESEARCHED,
    CURATED,
    LOCAL_TAGS,
    Registry,
    RegistryEntry,
    _manifest_matches,
)
from .roles import GENERIC_PATTERNS, _config_matcher, _registry
from .tokens import INTERPOLATION_MARK, LanguageSyntax, language_syntax

_NEVER = re.compile(r"(?!)")
_INTERP = "<INTERP>"
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
    syntax: dict[str, LanguageSyntax] = {}
    sinks: dict[str, tuple[SinkPattern, ...]] = {}
    area: dict[str, dict[str, re.Pattern[str]]] = {f: {} for f in _AREA_FIELDS}
    for entry in entries:
        extensions = _values(entry, "source_extensions")
        compiled = _syntax(entry)
        for extension in extensions if compiled else ():
            syntax.setdefault(extension, compiled)
            sinks.setdefault(extension, _sinks(entry))
            for name in _AREA_FIELDS:
                if _values(entry, name):
                    area[name].setdefault(extension, _guarded(_values(entry, name)))
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
        colocated_test_patterns=tuple(
            re.compile(translate(glob))
            for glob in _union(entries, "colocated_test_name_patterns")
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
        syntax=syntax,
        sinks={suffix: found for suffix, found in sinks.items() if found},
        skip_markers=area["skip_markers"],
        network_calls=area["network_calls"],
        type_escapes=area["type_escapes"],
        type_stub_patterns=tuple(
            re.compile(translate(glob)) for glob in _union(entries, "type_stub_names")
        ),
    )


_AREA_FIELDS = ("skip_markers", "network_calls", "type_escapes")


def _guarded(tokens: list[str]) -> re.Pattern[str]:
    """One alternation of ``tokens``, longest first; like a sink token, one
    starting with an identifier character may not follow ``.``, ``>``, ``$``."""
    ordered = sorted(dict.fromkeys(tokens), key=len, reverse=True)
    return re.compile(
        "|".join(
            (r"(?<![.>$])" if _word(token[:1]) else "") + token_regex(token)
            for token in ordered
        )
    )


_STRUCTURE_FIELDS = (
    "branch_keywords",
    "comment_delimiters",
    "string_delimiters",
    "function_start",
    "import_syntax",
)


def _syntax(entry: RegistryEntry) -> LanguageSyntax | None:
    """``entry``'s structure tokens (T033), or ``None`` if any field is absent:
    a language missing one gets no structure metrics rather than wrong ones."""
    if not all(_values(entry, field) for field in _STRUCTURE_FIELDS):
        return None
    return language_syntax(
        entry.name,
        comments=_values(entry, "comment_delimiters"),
        strings=_values(entry, "string_delimiters"),
        branch=_alternation(_values(entry, "branch_keywords")),
        function_start=_alternation(_values(entry, "function_start")),
        imports=_alternation(_values(entry, "import_syntax")),
        interpolations=_values(entry, "interpolating_strings"),
    )


def _sinks(entry: RegistryEntry) -> tuple[SinkPattern, ...]:
    """``entry``'s ``security_sinks`` tokens (T034), one pattern per token.

    A token starting with an identifier character may not follow ``.``,
    ``>`` or ``$``: ``eval(`` is a sink, ``model.eval(`` and ``$eval`` are not.
    """
    return tuple(
        SinkPattern(
            cwe=cited.cwe or "",
            token=token,
            citation_url=cited.citation_url,
            regex=re.compile(
                (r"(?<![.>$])" if _word(token[:1]) else "") + token_regex(token)
            ),
        )
        for cited in entry.fields.get("security_sinks", ())
        for token in cited.value
    )


def _alternation(tokens: list[str]) -> re.Pattern[str]:
    ordered = sorted(dict.fromkeys(tokens), key=len, reverse=True)
    return re.compile("|".join(token_regex(token) for token in ordered))


def curated_metric_tables() -> LanguageTables:
    """Tables from the registry ``roles`` already loaded (curated plus the
    local layer), compiled once per loaded registry: when ``roles._registry``
    is reloaded after a local write (T036), the tables follow."""
    global _compiled  # noqa: PLW0603 - one reference swap, see below
    registry = _registry()
    cached = _compiled
    if cached is None or cached[0] is not registry:
        cached = (registry, metric_tables(registry))
        _compiled = cached  # one reference swap; a racing call recompiles
    return cached[1]


_compiled: tuple[Registry, LanguageTables] | None = None


_TEST_MATCH = (
    "test_to_source_ratio",
    "source_files_without_covering_test",
    "source_files_without_covering_test_share",
    "source_file_share",
)
_ASSERTIONS = ("assertion_density_per_test", "assertions_observed")
_CCN = ("functions_over_ccn_10_share", "max_function_ccn")
_IMPORTS = ("top_level_import_cycles", "max_fan_in_changed")
_AC_TRACE = (
    "acceptance_criteria_traced_to_code_share",
    "acceptance_criteria_traced_to_test_share",
)
_SINKS = ("sink_hits_observed",)
_TEST_AREA = ("tests_without_assertions_share", "skipped_test_share")
_NETWORK = ("network_calls_in_unit_tests_observed",)
_TYPE_ESCAPES = ("type_escapes_per_kloc",)
_TODO = ("todo_without_ticket_share",)

FIELD_METRICS: Mapping[str, tuple[str, ...]] = {
    "source_extensions": _TEST_MATCH + _CCN + _IMPORTS + _SINKS + _AC_TRACE
    + _TYPE_ESCAPES + _TODO,
    "test_name_patterns": _TEST_MATCH + _ASSERTIONS + _AC_TRACE + _TEST_AREA
    + _NETWORK,
    "colocated_test_name_patterns": _TEST_MATCH + _ASSERTIONS + _AC_TRACE
    + _TEST_AREA + _NETWORK,
    "test_candidates": _TEST_MATCH[1:3],
    "test_declarations": _ASSERTIONS[:1] + _TEST_AREA,
    "assertions": _ASSERTIONS + _TEST_AREA[:1],
    "branch_keywords": _CCN,
    "comment_delimiters": _CCN + _IMPORTS + _SINKS + _TEST_AREA + _NETWORK
    + _TYPE_ESCAPES + _TODO,
    "string_delimiters": _CCN + _IMPORTS + _SINKS + _TEST_AREA + _NETWORK
    + _TYPE_ESCAPES + _TODO,
    "interpolating_strings": _SINKS,
    "function_start": _CCN,
    "import_syntax": _IMPORTS,
    "security_sinks": _SINKS,
    "skip_markers": _TEST_AREA[1:],
    "network_calls": _NETWORK,
    "type_escapes": _TYPE_ESCAPES,
    "type_stub_names": _TYPE_ESCAPES,
}
"""Which metrics each registry field feeds (T036, FR-048): a metric computed
over a pack holding a language whose field has local-layer values carries
their tag and links. ``manifests`` feeds no metric directly; it activates a
language's ``roles.*`` globs, which are tracked by :data:`ROLE_METRICS`.
``frameworks`` (T037) feeds none either: it detects framework entries, whose
own fields are merged into their language and tracked here."""

OPTIONAL_FIELDS: Mapping[str, str] = {
    "interpolating_strings": "refines sink matching; tokens.language_syntax "
    "defaults it to () and _syntax does not require it",
    "test_candidates": "refines test matching; expected_test_names falls "
    "back to no templates for a suffix without it",
    "type_stub_names": "refines type-escape scanning: only languages that "
    "generate stubs with a code suffix (TypeScript *.d.ts) declare it (T040)",
    "colocated_test_name_patterns": "refines test matching alongside "
    "test_name_patterns; python/php/rust omit it by design (T052) and the "
    "directory-first rule still applies without it",
}
"""Fields the metric code reads when present but never needs (T037 R1): a
language without one still gets every metric it feeds, so the reference gate
never asks for them."""

ROLE_METRICS: Mapping[str, tuple[str, ...]] = {
    "lint-config": ("lint_config_missing",),
    "format-config": ("format_config_missing",),
    "lockfile": ("lockfile_missing",),
    "test-config": ("test_config_and_ci_missing",),
    "ci-workflow": ("test_config_and_ci_missing",),
    "architecture-doc": ("architecture_description_missing",),
    "decision-record": ("decision_records_missing",),
}
"""Role-presence metrics per role: a local ``roles.<role>`` glob matching a
file in the pack tags them."""

_TAG_ORDER = (AGENT_RESEARCHED, *(tag for tag in LOCAL_TAGS if tag != AGENT_RESEARCHED))
"""Least reviewed first: an input built on several local tags shows this one."""


def registry_sources(
    packs: CombinedPack, registry: Registry
) -> dict[str, dict[str, tuple[str, tuple[Citation, ...]]]]:
    """Per dimension, per metric: the local tag and links it was built on.

    A language counts as present in a pack when a file the pack read or
    quoted has one of its source extensions; a local role glob counts when
    it matches such a file. Metrics with no local data are absent (curated).
    """
    result: dict[str, dict[str, tuple[str, tuple[Citation, ...]]]] = {}
    for slot in packs.slots:
        if slot.pack is None:
            continue
        files = set(slot.pack.files_read) | {e.path for e in slot.pack.excerpts}
        suffixes = {PurePosixPath(path).suffix for path in files}
        # metric -> tag -> {(label, url)}
        used: dict[str, dict[str, set[tuple[str, str]]]] = {}

        def add(used, metrics: tuple[str, ...], cited, label: str) -> None:
            for metric in metrics:
                used.setdefault(metric, {}).setdefault(cited.source_tag, set()).add(
                    (label, cited.citation_url)
                )

        for name, entry in registry.languages.items():
            extensions = set(_values(entry, "source_extensions"))
            present = bool(extensions & suffixes)
            for field, cited_values in entry.fields.items():
                for cited in cited_values:
                    if present and cited.source_tag != CURATED:
                        add(
                            used, FIELD_METRICS.get(field, ()), cited, f"{name}.{field}"
                        )
            for role, cited_values in entry.roles.items():
                for cited in cited_values:
                    if cited.source_tag == CURATED or role not in ROLE_METRICS:
                        continue
                    match = _config_matcher(cited.value)
                    if any(match(path) for path in files):
                        add(used, ROLE_METRICS[role], cited, f"{name}.roles.{role}")
        if used:
            result[slot.dimension] = {
                metric: (
                    next(tag for tag in _TAG_ORDER if tag in tags),
                    tuple(
                        Citation(label=label, url=url)
                        for label, url in sorted(set().union(*tags.values()))
                    ),
                )
                for metric, tags in sorted(used.items())
            }
    return result


def rejected_abstentions(
    metrics: MetricSet, packs: CombinedPack, registry: Registry
) -> MetricSet:
    """``metrics`` with every metric fed by a rejected registry field made
    to abstain (T038, FR-047: "reject -> its rules abstain").

    Applies per dimension, only where the rejected entry's language is
    present in that pack (a file read or quoted with one of its source
    extensions or manifests) and only while the field has no other data —
    curated, other local values, or for a role its generic patterns. The
    rejection records replay through ``registry_entries``, so this is
    reproducible on any machine (DDR-0005).
    """
    reasons: dict[tuple[str, str], str] = {}
    for slot in packs.slots:
        if slot.pack is None:
            continue
        files = set(slot.pack.files_read) | {e.path for e in slot.pack.excerpts}
        suffixes = {PurePosixPath(path).suffix for path in files}
        names = {PurePosixPath(path).name for path in files}
        for name, entry in sorted(registry.languages.items()):
            if not entry.rejected or not _present(entry, suffixes, names):
                continue
            for field in sorted(entry.rejected):
                if _field_has_data(entry, field):
                    continue
                role = field.removeprefix("roles.")
                fed = (
                    ROLE_METRICS.get(role, ())
                    if role != field
                    else FIELD_METRICS.get(field, ())
                )
                reason = (
                    f"registry field {name}.{field} was rejected by the user and "
                    "no other data exists for it; the metric abstains until a "
                    "replacement is researched (reference gate)"
                )
                for metric in fed:
                    reasons.setdefault((slot.dimension, metric), reason)
    if not reasons:
        return metrics
    return dataclasses.replace(
        metrics,
        metrics=tuple(
            _abstained(item, reasons[(item.dimension, item.name)])
            if (item.dimension, item.name) in reasons and not item.abstained
            else item
            for item in metrics
        ),
    )


def _present(entry: RegistryEntry, suffixes: set[str], names: set[str]) -> bool:
    if set(_values(entry, "source_extensions")) & suffixes:
        return True
    manifests = [p for cited in entry.manifests for p in cited.value]
    return any(_manifest_matches(pattern, names) for pattern in manifests)


def _field_has_data(entry: RegistryEntry, field: str) -> bool:
    if field == "manifests":
        return bool(entry.manifests)
    if field.startswith("roles."):
        role = field.removeprefix("roles.")
        return bool(entry.roles.get(role) or GENERIC_PATTERNS.get(role))
    return bool(entry.fields.get(field))


def _abstained(metric: Metric, reason: str) -> Metric:
    return dataclasses.replace(
        metric,
        outcome=MetricAbstention(reason=reason),
        computed_from=(),
        derivation="no value: " + reason,
    )


def token_regex(token: str) -> str:
    """Translate one registry code token (syntax in ``core/registry.py``).

    Only ``\\w*``, ``\\w``, a character class, ``\\s*``/``\\s+``, escaped
    literals, word boundaries and the fixed interpolation mark (``<INTERP>``)
    can come out, so a token cannot inject regex.
    """
    parts: list[str] = []
    index = 0
    while index < len(token):
        char = token[index]
        if token.startswith(_INTERP, index):
            parts.append(re.escape(INTERPOLATION_MARK))
            index += len(_INTERP)
            continue
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


__all__ = [
    "FIELD_METRICS",
    "OPTIONAL_FIELDS",
    "ROLE_METRICS",
    "curated_metric_tables",
    "metric_tables",
    "registry_sources",
    "token_regex",
]
