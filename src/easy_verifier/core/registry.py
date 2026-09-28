"""The reference registry: cited language patterns as data (T030, DDR-0007).

One TOML file per entry, named ``<entry>.toml``. Every field is an array of
cited values, so each pattern stays next to the link that justifies it::

    [[manifests]]                       # language entries only; activates it
    value = ["go.mod"]
    citation_url = "https://go.dev/ref/mod#go-mod-file"
    source_tag = "curated"

    [[roles.lint-config]]               # extra globs for an existing role
    value = ["**/.golangci.yml"]
    citation_url = "https://golangci-lint.run/"
    source_tag = "curated"

A framework entry carries ``extends = "<language>"`` and no manifests; it may
only add to its language (:func:`merge`). A new field is added by naming it in
:data:`ENTRY_FIELDS` — existing files stay valid.

A malformed entry is dropped with a warning naming the file and field; it never
raises. Nothing here reads a target repository.
"""

from __future__ import annotations

import re
import tomllib
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from fnmatch import fnmatchcase
from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import PurePosixPath
from urllib.parse import urlsplit

from .redact import redact

CURATED = "curated"
"""Source tag of every field shipped in the package."""

MAX_ENTRY_BYTES = 64 * 1024
"""Bytes read from one entry file; larger files are rejected unparsed."""

MAX_VALUES_PER_FIELD = 64
MAX_VALUE_CHARS = 200
MAX_URL_CHARS = 500

ENTRY_FIELDS = ("manifests",)
"""Top-level cited fields besides ``roles``. Later tasks extend this tuple."""

_CITED_KEYS = {"value", "citation_url", "source_tag"}
_ENTRY_NAME = re.compile(r"^[a-z0-9][a-z0-9-]*$")


@dataclass(frozen=True)
class CitedValue:
    """One registry field: values plus the link and tag that back them."""

    value: tuple[str, ...]
    citation_url: str
    source_tag: str


@dataclass(frozen=True)
class RegistryEntry:
    """One language's or framework's fields."""

    name: str
    extends: str | None
    manifests: tuple[CitedValue, ...]
    roles: Mapping[str, tuple[CitedValue, ...]]


@dataclass(frozen=True)
class Registry:
    languages: Mapping[str, RegistryEntry]
    frameworks: Mapping[str, RegistryEntry]
    warnings: tuple[str, ...]

    def active_languages(self, filenames: Collection[str]) -> tuple[str, ...]:
        """Languages with a manifest among ``filenames`` (base names), sorted.

        Manifests match case-sensitively; a manifest may be a glob such as
        ``*.csproj``.
        """
        names = set(filenames)
        return tuple(
            name
            for name, entry in self.languages.items()
            if any(
                _manifest_matches(pattern, names)
                for field in entry.manifests
                for pattern in field.value
            )
        )

    def patterns_for(self, role: str, languages: Sequence[str]) -> tuple[str, ...]:
        """The registry's globs for ``role`` over ``languages``, in order,
        first occurrence kept."""
        patterns: dict[str, None] = {}
        for language in languages:
            entry = self.languages.get(language)
            for field in entry.roles.get(role, ()) if entry else ():
                patterns.update(dict.fromkeys(field.value))
        return tuple(patterns)


def _manifest_matches(pattern: str, names: set[str]) -> bool:
    if not any(char in pattern for char in "*?["):
        return pattern in names
    return any(fnmatchcase(name, pattern) for name in names)


def merge(
    language: RegistryEntry, frameworks: Sequence[RegistryEntry]
) -> RegistryEntry:
    """``language`` with each framework's fields added (union, never removal).

    Frameworks apply in name order whatever order they are given in, so the
    result is deterministic; a field already present is not repeated.
    """
    roles = {name: list(fields) for name, fields in language.roles.items()}
    for framework in sorted(frameworks, key=lambda entry: entry.name):
        if framework.extends != language.name:
            raise ValueError(
                f"framework {framework.name!r} extends {framework.extends!r}, "
                f"not {language.name!r}"
            )
        for name, fields in framework.roles.items():
            merged = roles.setdefault(name, [])
            merged.extend(field for field in fields if field not in merged)
    return RegistryEntry(
        name=language.name,
        extends=None,
        manifests=language.manifests,
        roles={name: tuple(fields) for name, fields in sorted(roles.items())},
    )


def curated_root() -> Traversable:
    return resources.files("easy_verifier") / "registry" / "curated"


def load_registry(
    root: Traversable | None = None, *, known_roles: Collection[str]
) -> Registry:
    """Load every ``*.toml`` entry under ``root`` (default: the curated layer).

    ``known_roles`` is the complete role set (``roles.GENERIC_PATTERNS``); an
    entry naming any other role is rejected, since the registry may extend a
    role but never add one.
    """
    root = curated_root() if root is None else root
    known = frozenset(known_roles)
    warnings: list[str] = []
    languages: dict[str, RegistryEntry] = {}
    frameworks: dict[str, RegistryEntry] = {}

    files = sorted(
        (item for item in root.iterdir() if item.name.endswith(".toml")),
        key=lambda item: item.name,
    )
    for item in files:
        entry, errors = _load_entry(item, known)
        if errors:
            warnings.append(
                f"{redact(item.name)}: entry rejected: " + "; ".join(errors)
            )
        elif entry.extends is None:
            languages[entry.name] = entry
        else:
            frameworks[entry.name] = entry

    for name in list(frameworks):
        if frameworks[name].extends not in languages:
            warnings.append(
                f"{name}.toml: entry rejected: extends "
                f"{frameworks[name].extends!r}, which is not a loaded language entry"
            )
            del frameworks[name]

    return Registry(
        languages=languages, frameworks=frameworks, warnings=tuple(warnings)
    )


def _load_entry(
    item: Traversable, known_roles: frozenset[str]
) -> tuple[RegistryEntry | None, list[str]]:
    name = item.name.removesuffix(".toml")
    if not _ENTRY_NAME.fullmatch(name):
        return None, ["file name must be <lowercase-name>.toml"]
    try:
        with item.open("rb") as handle:
            raw = handle.read(MAX_ENTRY_BYTES + 1)
    except OSError:
        return None, ["could not be read"]
    if len(raw) > MAX_ENTRY_BYTES:
        return None, [f"larger than {MAX_ENTRY_BYTES} bytes"]
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None, ["not valid UTF-8"]
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as exc:
        return None, [f"not valid TOML: {redact(str(exc))}"]
    if not data:
        return None, ["empty entry"]

    errors: list[str] = []
    extends = data.get("extends")
    if extends is not None and not (
        isinstance(extends, str) and _ENTRY_NAME.fullmatch(extends)
    ):
        errors.append("extends: must be a lowercase entry name")
        extends = None

    fields: dict[str, tuple[CitedValue, ...]] = {}
    for key, value in data.items():
        if key in ("extends", "roles"):
            continue
        if key in ENTRY_FIELDS:
            fields[key] = _cited_values(key, value, errors)
        elif isinstance(value, list):
            errors.append(f"{redact(key)}: unknown field; known: {_known_fields()}")
        else:
            errors.append(f"{redact(key)}: unknown key; known: {_known_fields()}")

    roles: dict[str, tuple[CitedValue, ...]] = {}
    table = data.get("roles", {})
    if not isinstance(table, dict):
        errors.append("roles: must be a table of role arrays")
        table = {}
    for role, value in table.items():
        if role not in known_roles:
            errors.append(f"roles.{redact(role)}: unknown role")
        else:
            roles[role] = _cited_values(f"roles.{role}", value, errors)

    if data.get("extends") is None and not fields.get("manifests"):
        errors.append("manifests: a language entry needs at least one manifest")
    if data.get("extends") is not None and "manifests" in data:
        errors.append("manifests: a framework entry adds to its language only")
    if errors:
        return None, errors
    return (
        RegistryEntry(
            name=name,
            extends=extends,
            manifests=fields.get("manifests", ()),
            roles=dict(sorted(roles.items())),
        ),
        [],
    )


def _known_fields() -> str:
    return ", ".join(("extends", *ENTRY_FIELDS, "roles"))


def _cited_values(field: str, raw: object, errors: list[str]) -> tuple[CitedValue, ...]:
    if not isinstance(raw, list) or not raw:
        errors.append(f"{field}: must be a non-empty array of cited values")
        return ()
    result = []
    for index, item in enumerate(raw):
        where = f"{field}[{index}]"
        problem = _cited_value_problem(item)
        if problem:
            errors.append(f"{where}: {problem}")
        else:
            result.append(
                CitedValue(
                    value=tuple(item["value"]),
                    citation_url=item["citation_url"],
                    source_tag=item["source_tag"],
                )
            )
    return tuple(result)


def _cited_value_problem(item: object) -> str | None:
    if not isinstance(item, dict):
        return "must be a table of value, citation_url, source_tag"
    missing = sorted(_CITED_KEYS - set(item))
    if missing:
        return f"missing {', '.join(missing)}"
    extra = sorted(set(item) - _CITED_KEYS)
    if extra:
        return f"unknown key {', '.join(redact(key) for key in extra)}"

    values = item["value"]
    if not isinstance(values, list) or not values:
        return "value: must be a non-empty array of strings"
    if len(values) > MAX_VALUES_PER_FIELD:
        return f"value: at most {MAX_VALUES_PER_FIELD} entries"
    for value in values:
        problem = _pattern_problem(value)
        if problem:
            return f"value: {problem}"

    url = item["citation_url"]
    if not isinstance(url, str) or len(url) > MAX_URL_CHARS or not _is_https(url):
        return "citation_url: must be an https:// link to the source"
    if item["source_tag"] != CURATED:
        return f"source_tag: must be {CURATED!r}"
    return None


def _pattern_problem(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return "each entry must be a non-empty string"
    if len(value) > MAX_VALUE_CHARS:
        return f"each entry must be at most {MAX_VALUE_CHARS} characters"
    pure = PurePosixPath(value)
    if pure.is_absolute() or "\\" in value or ".." in pure.parts:
        return "each entry must be a repository-relative glob"
    return None


def _is_https(url: str) -> bool:
    if any(char.isspace() for char in url):
        return False
    try:
        parts = urlsplit(url)
    except ValueError:
        return False
    return parts.scheme == "https" and bool(parts.hostname)


__all__ = [
    "CURATED",
    "ENTRY_FIELDS",
    "MAX_ENTRY_BYTES",
    "CitedValue",
    "Registry",
    "RegistryEntry",
    "curated_root",
    "load_registry",
    "merge",
]
