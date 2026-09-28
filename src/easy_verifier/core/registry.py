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

The metric fields (T031) are read by ``core/metric_tables.py``:

* ``source_extensions`` — file suffixes that are code, e.g. ``".py"``;
* ``test_name_patterns`` — base-name globs naming a test file, e.g.
  ``"test_?*.py"`` (``fnmatch`` syntax, case-sensitive);
* ``colocated_test_name_patterns`` (T052) — the subset of test names that are
  unambiguous even inside a source root (``"?*.spec.ts"``, ``"?*_test.go"``):
  a match is a test wherever it sits. Prefix-style names (``test_?*.py``)
  stay out, since production modules carry them too;
* ``test_candidates`` — the test base names a source file expects, with
  ``{stem}`` and ``{ext}`` placeholders, e.g. ``"test_{stem}{ext}"``; a leading
  ``./`` means the test must sit in the source file's own directory;
* ``test_declarations`` / ``assertions`` — code tokens, matched textually. In a
  token ``*`` is any identifier characters, ``?`` exactly one, ``<A-Z>`` one
  character of the listed ranges, and a space is optional whitespace (required
  between two identifier characters); everything else is literal. A token
  starting or ending in an identifier character only matches as a whole word.
  Declarations match at the start of a line; assertions anywhere.

The structure fields (T033) are read by ``core/tokens.py`` through
``core/metric_tables.py``:

* ``comment_delimiters`` / ``string_delimiters`` — ``"X"`` runs to the end of
  the line (comment) or the next ``X`` on the same line (string); ``"X Y"``
  runs from ``X`` to the next ``Y`` across lines, e.g. ``"/* */"``;
* ``branch_keywords`` — code tokens counted as decision points (approximate
  CCN), e.g. ``"if"``, ``"&&"``;
* ``function_start`` / ``import_syntax`` — code tokens marking a line that
  starts a function / an import statement; matched anywhere in the line.

The security field (T034) is read by ``core/metric_tables.py``:

* ``security_sinks`` — code tokens marking a dangerous sink; each item also
  carries ``cwe = "CWE-<n>"``, the weakness its tokens are a sink for. Tokens
  are matched after comments and strings are blanked, so a string literal
  shows only as whitespace (``execute( f`` is an f-string passed to
  ``execute``; ``execute( +`` a literal concatenated there). A token starting
  with an identifier character does not match right after ``.``, ``>`` or
  ``$`` (a method of some other object, or a variable). ``<INTERP>`` in a
  token matches a string literal that embeds an expression (below);
* ``interpolating_strings`` — ``"X Y"``: a string literal opened by the
  ``string_delimiters`` opener ``X`` embeds an expression where ``Y`` occurs
  in it, e.g. ``"` ${"``. Such a literal is still blanked, but leaves one
  mark at its start; a ``Y`` ending in ``$`` counts only before a name or
  ``{``.

A malformed entry is dropped with a warning naming the file and field; it never
raises. Nothing here reads a target repository.

The local layer (T036) lives at ``$EASY_VERIFIER_SOT`` or
``~/.easy-verifier-sot/``, one file per entry in the same schema, written only
from validated agent input (:func:`parse_local_entries`,
:func:`save_local_entries`). Its tags are :data:`LOCAL_TAGS`; a symlinked
directory or file is refused. :func:`layered_registry` adds it to the curated
layer, value by value: a value the curated entry already has is dropped and
reported ("curated wins"), so local data can only add. Local values are
shape-bounded tighter than curated ones (:func:`_local_shape_problem`): they
come from a model's research, and globs and tokens become regexes.
"""

from __future__ import annotations

import dataclasses
import json
import os
import re
import tempfile
import tomllib
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from fnmatch import fnmatchcase
from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

from .redact import redact

CURATED = "curated"
"""Source tag of every field shipped in the package."""

MAX_ENTRY_BYTES = 64 * 1024
"""Bytes read from one entry file; larger files are rejected unparsed."""

MAX_VALUES_PER_FIELD = 64
MAX_VALUE_CHARS = 200
MAX_URL_CHARS = 500

AGENT_RESEARCHED = "agent-researched (unreviewed)"
USER_SUPPLIED = "user-supplied"
LOCAL_TAGS = (AGENT_RESEARCHED, USER_SUPPLIED)
"""Source tags a local-layer field may carry; never ``curated``."""

_INPUT_TAGS = {
    "agent-researched": AGENT_RESEARCHED,
    AGENT_RESEARCHED: AGENT_RESEARCHED,
    USER_SUPPLIED: USER_SUPPLIED,
}
"""Accepted agent-input ``source_tag`` spellings, to the tag that is stored."""

SOT_ENV = "EASY_VERIFIER_SOT"
SOT_DIRNAME = ".easy-verifier-sot"

MAX_AGENT_ENTRIES = 20
"""``registry_entries`` items accepted in one agent-input document."""

MAX_LOCAL_FILES = 200
"""Local-layer files loaded; more are reported, never silently dropped."""

MAX_LOCAL_TOKEN_STARS = 2
MAX_LOCAL_GLOB_STARS = 4
MAX_LOCAL_GLOBSTARS = 2
"""Shape bounds on one local value (backtracking guard). A token's ``*`` is a
``\\w*`` in a regex matched over whole files; a role glob's limits are
``.easy-verifier.toml``'s (``roles.MAX_CONFIG_*``)."""

_TOKEN_FIELDS = frozenset(
    {
        "test_declarations",
        "assertions",
        "branch_keywords",
        "function_start",
        "import_syntax",
        "security_sinks",
    }
)

ENTRY_FIELDS = (
    "manifests",
    "source_extensions",
    "test_name_patterns",
    "colocated_test_name_patterns",
    "test_candidates",
    "test_declarations",
    "assertions",
    "branch_keywords",
    "comment_delimiters",
    "string_delimiters",
    "function_start",
    "import_syntax",
    "security_sinks",
    "interpolating_strings",
)
"""Top-level cited fields besides ``roles``. Later tasks extend this tuple."""

_DELIMITER = re.compile(r"^[^\s\\]{1,4}( [^\s\\]{1,4})?$")

_DELIMITER_FIELDS = frozenset(
    {"comment_delimiters", "string_delimiters", "interpolating_strings"}
)
"""Code punctuation such as ``//``, not paths: exempt from the path checks."""

_VALUE_SHAPES = {
    "source_extensions": (
        re.compile(r"^\.[A-Za-z0-9_+-]+$"),
        "a file suffix such as .py",
    ),
    "test_name_patterns": (re.compile(r"^[^/]+$"), "a base-name glob, no /"),
    "colocated_test_name_patterns": (
        re.compile(r"^[^/]+$"),
        "a base-name glob, no /",
    ),
    "test_candidates": (
        re.compile(r"^(\./)?[^/]*\{stem\}[^/]*$"),
        "a base name containing {stem}, optionally prefixed ./",
    ),
    "comment_delimiters": (_DELIMITER, "a delimiter X or an open/close pair X Y"),
    "string_delimiters": (_DELIMITER, "a delimiter X or an open/close pair X Y"),
    "interpolating_strings": (
        re.compile(r"^[^\s\\]{1,4} [^\s\\]{1,4}$"),
        "a string opener X and an interpolation opener Y, as X Y",
    ),
}
"""Per-field value shapes beyond :func:`_pattern_problem`'s generic checks."""

_CITED_KEYS = {"value", "citation_url", "source_tag"}
_CWE = re.compile(r"^CWE-[1-9][0-9]{0,5}$")
_CWE_FIELDS = frozenset({"security_sinks"})
"""Fields whose items also carry a ``cwe`` key (required there, nowhere else)."""
_ENTRY_NAME = re.compile(r"^[a-z0-9][a-z0-9-]*$")


@dataclass(frozen=True)
class CitedValue:
    """One registry field: values plus the link and tag that back them."""

    value: tuple[str, ...]
    citation_url: str
    source_tag: str
    cwe: str | None = None
    """The weakness a ``security_sinks`` item's tokens are a sink for."""


@dataclass(frozen=True)
class RegistryEntry:
    """One language's or framework's fields."""

    name: str
    extends: str | None
    manifests: tuple[CitedValue, ...]
    roles: Mapping[str, tuple[CitedValue, ...]]
    fields: Mapping[str, tuple[CitedValue, ...]] = dataclasses.field(
        default_factory=dict
    )
    """Every other :data:`ENTRY_FIELDS` field present, by name."""


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

    def patterns_for(
        self, role: str, languages: Sequence[str], *, local: bool = False
    ) -> tuple[str, ...]:
        """The registry's globs for ``role`` over ``languages``, in order,
        first occurrence kept: the curated globs, or with ``local`` only the
        local layer's (matched by a bounded matcher, never the combined
        regex)."""
        patterns: dict[str, None] = {}
        for language in languages:
            entry = self.languages.get(language)
            for field in entry.roles.get(role, ()) if entry else ():
                if (field.source_tag != CURATED) == local:
                    patterns.update(dict.fromkeys(field.value))
        return tuple(patterns)

    def local_entries(self) -> tuple[dict[str, object], ...]:
        """Every local-layer field in use, as agent-input ``registry_entries``
        items, sorted: embedded in score output and reports so replaying them
        reproduces the score on a machine with an empty local layer (FR-048).
        """
        found = []
        # Frameworks are stored but not yet applied anywhere (no framework
        # detection before T037), so only language entries are "in use".
        for kind, entries in (("language", self.languages),):
            for entry in entries.values():
                sections = [("manifests", entry.manifests), *entry.fields.items()]
                sections += [(f"roles.{r}", v) for r, v in entry.roles.items()]
                for field, cited_values in sections:
                    for cited in cited_values:
                        if cited.source_tag == CURATED:
                            continue
                        item: dict[str, object] = {kind: entry.name}
                        if kind == "framework":
                            item["extends"] = entry.extends
                        item.update(
                            field=field,
                            value=list(cited.value),
                            citation_url=cited.citation_url,
                            source_tag=cited.source_tag,
                        )
                        if cited.cwe:
                            item["cwe"] = cited.cwe
                        found.append(item)
        return tuple(sorted(found, key=lambda item: json.dumps(item, sort_keys=True)))


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
    others = {name: list(fields) for name, fields in language.fields.items()}
    for framework in sorted(frameworks, key=lambda entry: entry.name):
        if framework.extends != language.name:
            raise ValueError(
                f"framework {framework.name!r} extends {framework.extends!r}, "
                f"not {language.name!r}"
            )
        for target, source in ((roles, framework.roles), (others, framework.fields)):
            for name, fields in source.items():
                merged = target.setdefault(name, [])
                merged.extend(cited for cited in fields if cited not in merged)
    return RegistryEntry(
        name=language.name,
        extends=None,
        manifests=language.manifests,
        roles={name: tuple(fields) for name, fields in sorted(roles.items())},
        fields={name: tuple(fields) for name, fields in sorted(others.items())},
    )


def curated_root() -> Traversable:
    return resources.files("easy_verifier") / "registry" / "curated"


def load_registry(
    root: Traversable | None = None,
    *,
    known_roles: Collection[str],
    local: bool = False,
) -> Registry:
    """Load every ``*.toml`` entry under ``root`` (default: the curated layer).

    ``known_roles`` is the complete role set (``roles.GENERIC_PATTERNS``); an
    entry naming any other role is rejected, since the registry may extend a
    role but never add one.

    ``local`` loads a local-layer directory (a :class:`~pathlib.Path`): tags
    must be :data:`LOCAL_TAGS`, values pass :func:`_local_shape_problem`,
    symlinked files are skipped, and an entry may omit manifests or extend a
    language this layer does not hold — :func:`overlay` checks both against
    the curated layer.
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
    if local and len(files) > MAX_LOCAL_FILES:
        warnings.append(
            f"local layer holds {len(files)} entry files; only the first "
            f"{MAX_LOCAL_FILES} in name order were loaded"
        )
        files = files[:MAX_LOCAL_FILES]
    for item in files:
        if local and Path(str(item)).is_symlink():
            warnings.append(f"{redact(item.name)}: entry rejected: is a symlink")
            continue
        entry, errors = _load_entry(item, known, local=local)
        if errors:
            warnings.append(
                f"{redact(item.name)}: entry rejected: " + "; ".join(errors)
            )
        elif entry.extends is None:
            languages[entry.name] = entry
        else:
            frameworks[entry.name] = entry

    for name in list(frameworks) if not local else ():
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
    item: Traversable, known_roles: frozenset[str], *, local: bool = False
) -> tuple[RegistryEntry | None, list[str]]:
    name = item.name.removesuffix(".toml")
    if not _ENTRY_NAME.fullmatch(name):
        return None, ["file name must be <lowercase-name>.toml"]
    try:
        if local:  # never follow a link swapped in after the listing
            fd = os.open(str(item), os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
            with os.fdopen(fd, "rb") as handle:
                raw = handle.read(MAX_ENTRY_BYTES + 1)
        else:
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
            fields[key] = _cited_values(key, value, errors, local=local)
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
            roles[role] = _cited_values(f"roles.{role}", value, errors, local=local)

    if not local and data.get("extends") is None and not fields.get("manifests"):
        errors.append("manifests: a language entry needs at least one manifest")
    if data.get("extends") is not None and "manifests" in data:
        errors.append("manifests: a framework entry adds to its language only")
    if errors:
        return None, errors
    return (
        RegistryEntry(
            name=name,
            extends=extends,
            manifests=fields.pop("manifests", ()),
            roles=dict(sorted(roles.items())),
            fields=dict(sorted(fields.items())),
        ),
        [],
    )


def _known_fields() -> str:
    return ", ".join(("extends", *ENTRY_FIELDS, "roles"))


def _cited_values(
    field: str, raw: object, errors: list[str], *, local: bool = False
) -> tuple[CitedValue, ...]:
    if not isinstance(raw, list) or not raw:
        errors.append(f"{field}: must be a non-empty array of cited values")
        return ()
    result = []
    for index, item in enumerate(raw):
        where = f"{field}[{index}]"
        problem = _cited_value_problem(item, field, local=local)
        if problem:
            errors.append(f"{where}: {problem}")
        else:
            result.append(
                CitedValue(
                    value=tuple(item["value"]),
                    citation_url=item["citation_url"],
                    source_tag=item["source_tag"],
                    cwe=item.get("cwe"),
                )
            )
    return tuple(result)


def _cited_value_problem(
    item: object, field: str, *, local: bool = False
) -> str | None:
    if not isinstance(item, dict):
        return "must be a table of value, citation_url, source_tag"
    keys = _CITED_KEYS | {"cwe"} if field in _CWE_FIELDS else _CITED_KEYS
    missing = sorted(keys - set(item))
    if missing:
        return f"missing {', '.join(missing)}"
    extra = sorted(set(item) - keys)
    if extra:
        return f"unknown key {', '.join(redact(key) for key in extra)}"
    if "cwe" in keys and not (
        isinstance(item["cwe"], str) and _CWE.fullmatch(item["cwe"])
    ):
        return "cwe: must be a CWE id such as CWE-89"

    values = item["value"]
    if not isinstance(values, list) or not values:
        return "value: must be a non-empty array of strings"
    if len(values) > MAX_VALUES_PER_FIELD:
        return f"value: at most {MAX_VALUES_PER_FIELD} entries"
    for value in values:
        problem = _pattern_problem(value, path=field not in _DELIMITER_FIELDS)
        if problem:
            return f"value: {problem}"
        shape = _VALUE_SHAPES.get(field)
        if shape and not shape[0].fullmatch(value):
            return f"value: {redact(value)!r} is not {shape[1]}"
        problem = _local_shape_problem(field, value) if local else None
        if problem:
            return f"value: {redact(value)!r}: {problem}"

    url = item["citation_url"]
    if not isinstance(url, str) or len(url) > MAX_URL_CHARS or not _is_https(url):
        return "citation_url: must be an https:// link to the source"
    if local and item["source_tag"] not in LOCAL_TAGS:
        return f"source_tag: must be one of {', '.join(LOCAL_TAGS)}"
    if not local and item["source_tag"] != CURATED:
        return f"source_tag: must be {CURATED!r}"
    return None


def _local_shape_problem(field: str, value: str) -> str | None:
    """Bound a local value's shape, not only its length (ReDoS guard).

    Tokens compile to ``\\w*`` runs (``metric_tables.token_regex``) matched
    over whole files, so each ``*`` multiplies backtracking; globs keep
    ``.easy-verifier.toml``'s limits, and local role globs are matched
    segment-wise (``roles._config_matcher``), never by the combined regex.
    """
    if field in _TOKEN_FIELDS:
        if value.count("*") > MAX_LOCAL_TOKEN_STARS:
            return f"at most {MAX_LOCAL_TOKEN_STARS} '*' wildcards in a token"
        return None
    if field in _DELIMITER_FIELDS or field == "test_candidates":
        return None
    segments = value.split("/")
    if any("**" in segment and segment != "**" for segment in segments):
        return "'**' must be a whole path segment (e.g. 'docs/**/*.md')"
    if segments.count("**") > MAX_LOCAL_GLOBSTARS:
        return f"at most {MAX_LOCAL_GLOBSTARS} '**' segments are allowed"
    stars = sum(segment.count("*") for segment in segments if segment != "**")
    if stars > MAX_LOCAL_GLOB_STARS:
        return f"at most {MAX_LOCAL_GLOB_STARS} '*' wildcards are allowed"
    return None


def _pattern_problem(value: object, *, path: bool = True) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return "each entry must be a non-empty string"
    if len(value) > MAX_VALUE_CHARS:
        return f"each entry must be at most {MAX_VALUE_CHARS} characters"
    if not path:
        return None
    pure = PurePosixPath(value)
    if pure.is_absolute() or "\\" in value or ".." in pure.parts:
        return "each entry must be a repository-relative glob"
    return None


# ---------------------------------------------------------------------------
# local layer (T036)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LocalEntry:
    """One validated agent-input ``registry_entries`` item."""

    name: str
    extends: str | None
    field: str
    """An :data:`ENTRY_FIELDS` name or ``roles.<known role>``."""
    cited: CitedValue


_LOCAL_KEYS = frozenset(
    {
        "language",
        "framework",
        "extends",
        "field",
        "value",
        "citation_url",
        "source_tag",
        "cwe",
    }
)


def parse_local_entries(
    raw: object, known_roles: Collection[str]
) -> tuple[tuple[LocalEntry, ...], list[str]]:
    """Validate agent-input ``registry_entries``; return entries and errors.

    Any error means nothing may be saved: the caller rejects the document.
    A value or link that redaction would alter is refused, since entries are
    stored and embedded in reports verbatim.
    """
    if raw is None:
        return (), []
    if not isinstance(raw, list):
        return (), ["registry_entries: must be a list of entries"]
    if len(raw) > MAX_AGENT_ENTRIES:
        return (), [f"registry_entries: at most {MAX_AGENT_ENTRIES} entries per call"]
    known = frozenset(known_roles)
    entries: list[LocalEntry] = []
    errors: list[str] = []
    for index, item in enumerate(raw):
        where = f"registry_entries[{index}]"
        entry, problem = _local_entry(item, known)
        if problem:
            errors.append(f"{where}: {problem}")
        else:
            entries.append(entry)
    return tuple(entries), errors


def _local_entry(
    item: object, known: frozenset[str]
) -> tuple[LocalEntry | None, str | None]:
    if not isinstance(item, dict):
        return None, (
            "must be an object with language or framework, field, value, "
            "citation_url, source_tag"
        )
    extra = sorted(str(key) for key in item if key not in _LOCAL_KEYS)
    if extra:
        return None, f"unknown key {', '.join(redact(key) for key in extra)}"
    if ("language" in item) == ("framework" in item):
        return None, "exactly one of language or framework is required"
    kind = "language" if "language" in item else "framework"
    name = item[kind]
    if not (isinstance(name, str) and len(name) <= 64 and _ENTRY_NAME.fullmatch(name)):
        return None, f"{kind}: must be a lowercase entry name such as kotlin"
    extends = item.get("extends")
    if kind == "framework" and not (
        isinstance(extends, str) and _ENTRY_NAME.fullmatch(extends)
    ):
        return None, "extends: a framework entry names the language it adds to"
    if kind == "language" and "extends" in item:
        return None, "extends: only a framework entry extends a language"
    field = item.get("field")
    role = field.removeprefix("roles.") if isinstance(field, str) else None
    if not (field in ENTRY_FIELDS or (field != role and role in known)):
        return None, (
            f"field {redact(str(field))!r}: unknown field; known: "
            f"{', '.join(ENTRY_FIELDS)}, roles.<role>"
        )
    if kind == "framework" and field == "manifests":
        return None, "manifests: a framework entry adds to its language only"
    tag = item.get("source_tag")
    if not isinstance(tag, str) or tag not in _INPUT_TAGS:
        return None, "source_tag: must be agent-researched or user-supplied"
    cited = {key: item[key] for key in ("value", "citation_url", "cwe") if key in item}
    cited["source_tag"] = _INPUT_TAGS[tag]
    problem = _cited_value_problem(cited, field, local=True)
    if problem:
        return None, problem
    texts = [*cited["value"], cited["citation_url"]]
    if any(redact(text) != text for text in texts):
        return None, (
            "looks like it holds a secret; entries are stored and reported verbatim"
        )
    return (
        LocalEntry(
            name=name,
            extends=extends,
            field=field,
            cited=CitedValue(
                value=tuple(cited["value"]),
                citation_url=cited["citation_url"],
                source_tag=cited["source_tag"],
                cwe=cited.get("cwe"),
            ),
        ),
        None,
    )


def sot_root() -> Path:
    """The local layer directory: ``$EASY_VERIFIER_SOT`` or ``~/.easy-verifier-sot``."""
    configured = os.environ.get(SOT_ENV)
    return Path(configured).expanduser() if configured else Path.home() / SOT_DIRNAME


def local_root_problem(root: Path) -> str | None:
    """Why ``root`` cannot hold the local layer, or ``None``. A missing
    directory is fine (an empty layer)."""
    if not root.is_absolute():
        return f"{SOT_ENV} must be an absolute path"
    if root.is_symlink():
        return "the local layer directory is a symlink; refused"
    if root.exists() and not root.is_dir():
        return "the local layer path is not a directory"
    return None


def local_write_problem(root: Path, repo: Path) -> str | None:
    """Why research cannot be saved under ``root`` for target ``repo``."""
    problem = local_root_problem(root)
    if problem:
        return problem
    try:
        inside = root.resolve().is_relative_to(repo.resolve())
    except OSError:
        return "the local layer directory could not be resolved"
    if inside:
        return "the local layer directory is inside the target repository (NFR-007)"
    existing = next(path for path in (root, *root.parents) if path.exists())
    if not os.access(existing, os.W_OK):
        return "the local layer directory is not writable"
    return None


def layered_registry(*, known_roles: Collection[str]) -> Registry:
    """The curated layer plus the local layer at :func:`sot_root`."""
    curated = load_registry(known_roles=known_roles)
    root = sot_root()
    problem = local_root_problem(root)
    if problem:
        return dataclasses.replace(
            curated,
            warnings=(*curated.warnings, f"local layer ignored: {problem}"),
        )
    if not root.is_dir():
        return curated
    try:
        local = load_registry(root, known_roles=known_roles, local=True)
    except OSError:
        return dataclasses.replace(
            curated,
            warnings=(*curated.warnings, "local layer ignored: could not be read"),
        )
    return overlay(curated, local)


def overlay(curated: Registry, local: Registry) -> Registry:
    """``curated`` with ``local`` added value by value; curated always wins.

    A local value the curated entry already has is dropped and reported; a
    new language needs a manifest; a framework must extend a loaded language.
    """
    warnings = [*curated.warnings, *local.warnings]
    languages = dict(curated.languages)
    for name, entry in local.languages.items():
        base = languages.get(name)
        if base is not None:
            languages[name] = _add_entry(base, entry, warnings)
        elif not entry.manifests:
            warnings.append(
                f"{name}.toml: entry rejected: a language the curated layer does "
                "not hold needs at least one manifest"
            )
        else:
            languages[name] = entry
    frameworks = dict(curated.frameworks)
    for name, entry in local.frameworks.items():
        base = frameworks.get(name)
        if entry.extends not in languages or (base and base.extends != entry.extends):
            warnings.append(
                f"{name}.toml: entry rejected: extends {entry.extends!r}, which "
                "is not a loaded language entry"
            )
        else:
            frameworks[name] = _add_entry(base, entry, warnings) if base else entry
    return Registry(
        languages=languages, frameworks=frameworks, warnings=tuple(warnings)
    )


def _add_entry(
    base: RegistryEntry, extra: RegistryEntry, notes: list[str]
) -> RegistryEntry:
    def add(label, have, more):
        taken = {value for cited in have for value in cited.value}
        result = list(have)
        for cited in more:
            fresh = tuple(value for value in cited.value if value not in taken)
            dropped = [value for value in cited.value if value in taken]
            if dropped:
                notes.append(
                    f"curated wins: {base.name}.{label} already has "
                    f"{', '.join(dropped)}; the local value is not used"
                )
            if fresh:
                result.append(dataclasses.replace(cited, value=fresh))
                taken.update(fresh)
        return tuple(result)

    roles = dict(base.roles)
    for role, more in extra.roles.items():
        roles[role] = add(f"roles.{role}", roles.get(role, ()), more)
    fields = dict(base.fields)
    for field, more in extra.fields.items():
        fields[field] = add(field, fields.get(field, ()), more)
    return dataclasses.replace(
        base,
        manifests=add("manifests", base.manifests, extra.manifests),
        roles=dict(sorted(roles.items())),
        fields=dict(sorted(fields.items())),
    )


def save_local_entries(
    entries: Sequence[LocalEntry], root: Path, *, known_roles: Collection[str]
) -> None:
    """Add ``entries`` to their ``<name>.toml`` under ``root``, atomically.

    Each file is re-read, merged (an identical field is kept once), sorted,
    and replaced via a temp file in the same directory, so concurrent writers
    leave one complete file — the last writer's. Raises :class:`OSError` on
    any refusal; the caller then scores with the data already on disk.
    """
    problem = local_root_problem(root)
    if problem:
        raise OSError(problem)
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    if root.is_symlink() or not root.is_dir():
        raise OSError("the local layer directory is a symlink; refused")
    known = frozenset(known_roles)
    by_name: dict[str, list[LocalEntry]] = {}
    for entry in entries:
        by_name.setdefault(entry.name, []).append(entry)
    for name, group in sorted(by_name.items()):
        path = root / f"{name}.toml"
        if path.is_symlink():
            raise OSError(f"{name}.toml is a symlink; refused")
        extends = group[0].extends
        sections: dict[str, list[CitedValue]] = {}
        if path.exists():
            current, errors = _load_entry(path, known, local=True)
            if errors:
                raise OSError(f"{name}.toml exists but is invalid; not modified")
            extends = current.extends
            sections["manifests"] = list(current.manifests)
            for field, cited_values in current.fields.items():
                sections[field] = list(cited_values)
            for role, cited_values in current.roles.items():
                sections[f"roles.{role}"] = list(cited_values)
        for entry in group:
            if entry.extends != extends:
                raise OSError(f"{name}.toml: conflicting extends; not modified")
            target = sections.setdefault(entry.field, [])
            if entry.cited not in target:
                target.append(entry.cited)
        data = _entry_toml(extends, sections).encode("utf-8")
        if len(data) > MAX_ENTRY_BYTES:
            raise OSError(f"{name}.toml would exceed {MAX_ENTRY_BYTES} bytes")
        _atomic_write(root, path, data)


def _entry_toml(extends: str | None, sections: Mapping[str, list[CitedValue]]) -> str:
    lines = ["# easy-verifier local reference registry entry (T036)."]
    if extends is not None:
        lines.append(f"extends = {json.dumps(extends)}")
    for field in sorted(sections):
        ordered = sorted(
            sections[field],
            key=lambda c: (c.value, c.citation_url, c.source_tag, c.cwe or ""),
        )
        for cited in ordered:
            lines += [
                "",
                f"[[{field}]]",
                "value = [" + ", ".join(json.dumps(v) for v in cited.value) + "]",
                f"citation_url = {json.dumps(cited.citation_url)}",
                f"source_tag = {json.dumps(cited.source_tag)}",
            ]
            if cited.cwe:
                lines.append(f"cwe = {json.dumps(cited.cwe)}")
    return "\n".join(lines) + "\n"


def _atomic_write(root: Path, path: Path, data: bytes) -> None:
    fd, temp = tempfile.mkstemp(prefix=f".{path.stem}.", suffix=".tmp", dir=root)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    except BaseException:
        Path(temp).unlink(missing_ok=True)
        raise


def _is_https(url: str) -> bool:
    if any(char.isspace() for char in url):
        return False
    try:
        parts = urlsplit(url)
    except ValueError:
        return False
    return (
        parts.scheme == "https"
        and bool(parts.hostname)
        and parts.username is None
        and parts.password is None
    )


__all__ = [
    "AGENT_RESEARCHED",
    "CURATED",
    "ENTRY_FIELDS",
    "LOCAL_TAGS",
    "MAX_AGENT_ENTRIES",
    "MAX_ENTRY_BYTES",
    "SOT_ENV",
    "USER_SUPPLIED",
    "CitedValue",
    "LocalEntry",
    "Registry",
    "RegistryEntry",
    "curated_root",
    "layered_registry",
    "load_registry",
    "local_root_problem",
    "local_write_problem",
    "merge",
    "overlay",
    "parse_local_entries",
    "save_local_entries",
    "sot_root",
]
