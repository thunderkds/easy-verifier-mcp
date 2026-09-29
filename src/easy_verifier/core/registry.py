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

The area fields (T040, FR-051) are read by ``core/metric_tables.py``:

* ``skip_markers`` / ``network_calls`` — code tokens, matched in test-file
  excerpts after comments and strings are blanked: an unconditional
  skip/disable marker, and a call that reaches the network;
* ``type_escapes`` — tokens that opt out of the type checker, matched in
  source-file excerpts after strings (not comments) are blanked, so a
  ``type: ignore`` comment counts and a string saying so does not;
* ``type_stub_names`` — base-name globs of generated type stubs (``*.d.ts``),
  never scanned for type escapes. Optional.

The compatibility field (T055, area #5) is read by the ``blast-radius``
dimension through ``core/metric_tables.py``:

* ``public_declarations`` — code tokens matched at the start of a line (after
  indentation) that declare a symbol visible outside its module, e.g.
  ``"pub fn"`` or ``"def <a-zA-Z>"``. The declared name is the identifier the
  token ends inside, else the next identifier after it; a token ending in
  ``(`` names the last identifier it matched.

The cookie fields (T056, area #8) are read by the ``security`` dimension
through ``core/metric_tables.py``:

* ``cookie_calls`` — code tokens starting a statement that sets a cookie,
  matched after comments and strings are blanked (``".set_cookie ("``). The
  statement runs to a ``;`` or line end outside brackets; a next line
  starting with ``.`` continues it;
* ``cookie_secure`` / ``cookie_httponly`` / ``cookie_samesite`` — tokens that
  set that flag inside such a statement, matched with comments blanked and
  strings kept (PHP option keys are strings), e.g. ``"httponly = True"``.

The detection field (T037) is read by ``core/gate.py``'s ``detect_stack``:

* ``frameworks`` — language entries only: ``"<framework>=<dependency>"``, e.g.
  ``"spring-boot=org.springframework.boot"``: the framework is detected when
  one of the language's manifests declares that dependency. Its framework
  entry, if any, is ``<framework>.toml`` with ``extends = "<language>"``.

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

The review gate (T038, FR-047) adds ``review_status`` to every local item:
``pending`` (new, scores immediately), ``approved`` (the user said good; an
agent-researched item is retagged :data:`USER_APPROVED`) or ``rejected``. A
rejected item stays in its file as a remembered record but is loaded into
:attr:`RegistryEntry.rejected`, never into the live fields; a new entry for
the same field clears it. ``improve`` keeps an item pending with its
``review_comment`` and ``improve_rounds``; a new entry for the field replaces
it and inherits the round count. Items are addressed by :func:`entry_id`.
"""

from __future__ import annotations

import dataclasses
import hashlib
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
USER_APPROVED = "agent-researched (user-approved)"
LOCAL_TAGS = (AGENT_RESEARCHED, USER_SUPPLIED, USER_APPROVED)
"""Source tags a local-layer field may carry; never ``curated``."""

_INPUT_TAGS = {
    "agent-researched": AGENT_RESEARCHED,
    AGENT_RESEARCHED: AGENT_RESEARCHED,
    USER_SUPPLIED: USER_SUPPLIED,
    USER_APPROVED: USER_APPROVED,
}
"""Accepted agent-input ``source_tag`` spellings, to the tag that is stored.
:data:`USER_APPROVED` is how a report's embedded entries replay (T038): the
review answer itself is agent input too, so this grants nothing new."""

PENDING, APPROVED, REJECTED = "pending", "approved", "rejected"
REVIEW_STATUSES = (PENDING, APPROVED, REJECTED)
REVIEW_ANSWERS = ("good", "improve", "reject")
MAX_REVIEWS = 20
"""``reviews`` answers accepted in one agent-input document."""
MAX_COMMENT_CHARS = 500
MAX_IMPROVE_ROUNDS_STORED = 100
"""Highest ``improve_rounds`` a file item may carry. Counting stops here
rather than past it: an item over the bound would make its whole file fail
to load (T038 security review P3)."""
MAX_ENTRY_ID_CHARS = 200
_REVIEW_KEYS = frozenset({"review_status", "review_comment", "improve_rounds"})
"""Optional keys of a local-layer file item (T038)."""

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
        "skip_markers",
        "network_calls",
        "type_escapes",
        "public_declarations",
        "cookie_calls",
        "cookie_secure",
        "cookie_httponly",
        "cookie_samesite",
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
    "frameworks",
    "skip_markers",
    "network_calls",
    "type_escapes",
    "type_stub_names",
    "public_declarations",
    "cookie_calls",
    "cookie_secure",
    "cookie_httponly",
    "cookie_samesite",
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
    "type_stub_names": (re.compile(r"^[^/]+$"), "a base-name glob, no /"),
    "frameworks": (
        re.compile(r"^[a-z0-9][a-z0-9-]*=[A-Za-z0-9@][A-Za-z0-9@/._:+-]*$"),
        "<framework>=<dependency>, e.g. express=express",
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
    review_status: str | None = None
    """``None`` for curated data; a :data:`REVIEW_STATUSES` value for local."""
    review_comment: str | None = None
    """The user's ``improve`` comment; set only while that answer is open."""
    improve_rounds: int = 0


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
    rejected: Mapping[str, tuple[CitedValue, ...]] = dataclasses.field(
        default_factory=dict
    )
    """Local items the user rejected (T038), by field (``roles.<role>`` for a
    role): remembered, never used as data."""


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

    def local_entries(
        self, frameworks: Collection[str] = ()
    ) -> tuple[dict[str, object], ...]:
        """Every local-layer field in use, as agent-input ``registry_entries``
        items, sorted: embedded in score output and reports so replaying them
        reproduces the score on a machine with an empty local layer (FR-048).
        A framework entry is in use only when detected (``frameworks``).
        Rejection records are included with ``review_status: "rejected"``,
        since they make metrics abstain (T038).
        """
        found = []
        used = {n: self.frameworks[n] for n in frameworks if n in self.frameworks}
        for kind, entries in (("language", self.languages), ("framework", used)):
            for entry in entries.values():
                sections = [("manifests", entry.manifests), *entry.fields.items()]
                sections += [(f"roles.{r}", v) for r, v in entry.roles.items()]
                sections += list(entry.rejected.items())
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
                        if cited.review_status == REJECTED:
                            item["review_status"] = REJECTED
                        found.append(item)
        return tuple(sorted(found, key=lambda item: json.dumps(item, sort_keys=True)))


    def detection_keys(self, language: str) -> tuple[tuple[str, str], ...]:
        """``(framework, dependency)`` pairs from ``language``'s ``frameworks``
        field (curated and local), in declared order."""
        entry = self.languages.get(language)
        pairs = (
            tuple(value.split("=", 1))
            for cited in (entry.fields.get("frameworks", ()) if entry else ())
            for value in cited.value
        )
        return tuple(dict.fromkeys(pairs))

    def applied(self, frameworks: Sequence[tuple[str, str]]) -> Registry:
        """This registry with each detected ``(framework, language)`` entry
        merged into its language (:func:`merge`, add-only); ``self`` when no
        detected framework has an entry extending that language."""
        by_language: dict[str, list[RegistryEntry]] = {}
        for name, language in frameworks:
            entry = self.frameworks.get(name)
            if (
                entry is not None
                and entry.extends == language
                and language in self.languages
            ):
                by_language.setdefault(language, []).append(entry)
        if not by_language:
            return self
        return dataclasses.replace(
            self,
            languages={
                name: merge(entry, by_language[name]) if name in by_language else entry
                for name, entry in self.languages.items()
            },
        )


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
    rejected = {name: list(fields) for name, fields in language.rejected.items()}
    for framework in sorted(frameworks, key=lambda entry: entry.name):
        if framework.extends != language.name:
            raise ValueError(
                f"framework {framework.name!r} extends {framework.extends!r}, "
                f"not {language.name!r}"
            )
        for target, source in (
            (roles, framework.roles),
            (others, framework.fields),
            (rejected, framework.rejected),
        ):
            for name, fields in source.items():
                merged = target.setdefault(name, [])
                merged.extend(cited for cited in fields if cited not in merged)
    return RegistryEntry(
        name=language.name,
        extends=None,
        manifests=language.manifests,
        roles={name: tuple(fields) for name, fields in sorted(roles.items())},
        fields={name: tuple(fields) for name, fields in sorted(others.items())},
        rejected={name: tuple(fields) for name, fields in sorted(rejected.items())},
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
    if data.get("extends") is not None and "frameworks" in data:
        errors.append("frameworks: detection keys belong to the language entry")
    if errors:
        return None, errors
    rejected: dict[str, tuple[CitedValue, ...]] = {}
    for key, table in [*fields.items(), *((f"roles.{r}", v) for r, v in roles.items())]:
        gone = tuple(cited for cited in table if cited.review_status == REJECTED)
        if gone:
            rejected[key] = gone
    fields = _live(fields)
    roles = _live(roles)
    return (
        RegistryEntry(
            name=name,
            extends=extends,
            manifests=fields.pop("manifests", ()),
            roles=dict(sorted(roles.items())),
            fields=dict(sorted(fields.items())),
            rejected=dict(sorted(rejected.items())),
        ),
        [],
    )


def _live(
    table: Mapping[str, tuple[CitedValue, ...]],
) -> dict[str, tuple[CitedValue, ...]]:
    """``table`` without rejected items; a field left empty is dropped."""
    kept = {
        key: tuple(c for c in values if c.review_status != REJECTED)
        for key, values in table.items()
    }
    return {key: values for key, values in kept.items() if values}


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
                    review_status=_review_status(item) if local else None,
                    review_comment=item.get("review_comment"),
                    improve_rounds=item.get("improve_rounds", 0),
                )
            )
    return tuple(result)


def _review_status(item: Mapping) -> str:
    """A local item's status; absent means pending, except that the
    approved tag implies approved."""
    default = APPROVED if item["source_tag"] == USER_APPROVED else PENDING
    return item.get("review_status", default)


def _cited_value_problem(
    item: object, field: str, *, local: bool = False
) -> str | None:
    if not isinstance(item, dict):
        return "must be a table of value, citation_url, source_tag"
    keys = _CITED_KEYS | {"cwe"} if field in _CWE_FIELDS else _CITED_KEYS
    missing = sorted(keys - set(item))
    if missing:
        return f"missing {', '.join(missing)}"
    extra = sorted(set(item) - keys - (_REVIEW_KEYS if local else set()))
    if extra:
        return f"unknown key {', '.join(redact(key) for key in extra)}"
    if local:
        problem = _review_problem(item)
        if problem:
            return problem
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


def _review_problem(item: Mapping) -> str | None:
    """Shape of a local item's optional review keys (T038)."""
    status = item.get("review_status", PENDING)
    if status not in REVIEW_STATUSES:
        return f"review_status: must be one of {', '.join(REVIEW_STATUSES)}"
    if item.get("source_tag") == USER_APPROVED and _review_status(item) != APPROVED:
        return f"review_status: an item tagged {USER_APPROVED!r} is approved"
    comment = item.get("review_comment")
    if comment is not None and not (
        isinstance(comment, str)
        and len(comment) <= MAX_COMMENT_CHARS
        and not _has_surrogate(comment)
    ):
        return f"review_comment: must be a string of at most {MAX_COMMENT_CHARS}"
    rounds = item.get("improve_rounds", 0)
    if type(rounds) is not int or not 0 <= rounds <= MAX_IMPROVE_ROUNDS_STORED:
        return (
            "improve_rounds: must be an integer from 0 through "
            f"{MAX_IMPROVE_ROUNDS_STORED}"
        )
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
    if _has_surrogate(value):
        return "each entry must not hold a lone surrogate character"
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
        "review_status",
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
    if kind == "framework" and field == "frameworks":
        return None, "frameworks: detection keys belong to the language entry"
    tag = item.get("source_tag")
    if not isinstance(tag, str) or tag not in _INPUT_TAGS:
        return None, (
            "source_tag: must be agent-researched or user-supplied (a replayed "
            f"report may also carry {USER_APPROVED!r})"
        )
    if "review_status" in item and item["review_status"] != REJECTED:
        return None, (
            'review_status: only "rejected" is accepted (a replayed rejection '
            "record); answer the review gate with agent_input.reviews"
        )
    if "review_status" in item and tag == USER_APPROVED:
        return None, f"review_status: an item tagged {USER_APPROVED!r} is approved"
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
                review_status=item.get("review_status") or _review_status(cited),
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
    rejected = dict(base.rejected)
    for field, more in extra.rejected.items():
        rejected[field] = (*rejected.get(field, ()), *more)
    return dataclasses.replace(
        base,
        manifests=add("manifests", base.manifests, extra.manifests),
        roles=dict(sorted(roles.items())),
        fields=dict(sorted(fields.items())),
        rejected=dict(sorted(rejected.items())),
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
            current = _read_local(path, known)
            extends = current.extends
            sections = _sections(current)
        for entry in group:
            if entry.extends != extends:
                raise OSError(f"{name}.toml: conflicting extends; not modified")
            target = sections.setdefault(entry.field, [])
            if any(_same_value(entry.cited, cited) for cited in target):
                continue  # already here, reviewed or not: never reset (T038)
            cited = entry.cited
            if cited.review_status != REJECTED:
                # A new entry replaces the field's rejection records and its
                # open "improve" items, inheriting their round count.
                closed = [c for c in target if _superseded(c)]
                rounds = min(
                    max((c.improve_rounds for c in closed), default=0),
                    MAX_IMPROVE_ROUNDS_STORED,
                )
                target[:] = [c for c in target if not _superseded(c)]
                cited = dataclasses.replace(cited, improve_rounds=rounds)
            target.append(cited)
        data = _entry_toml(extends, sections).encode("utf-8")
        if len(data) > MAX_ENTRY_BYTES:
            raise OSError(f"{name}.toml would exceed {MAX_ENTRY_BYTES} bytes")
        _atomic_write(root, path, data)


def _read_local(path: Path, known: frozenset[str]) -> RegistryEntry:
    current, errors = _load_entry(path, known, local=True)
    if errors:
        raise OSError(f"{path.name} exists but is invalid; not modified")
    return current


def _sections(entry: RegistryEntry) -> dict[str, list[CitedValue]]:
    """Every item of a local entry by field key, rejection records included."""
    sections: dict[str, list[CitedValue]] = {}
    if entry.manifests:
        sections["manifests"] = list(entry.manifests)
    for field, cited_values in entry.fields.items():
        sections[field] = list(cited_values)
    for role, cited_values in entry.roles.items():
        sections[f"roles.{role}"] = list(cited_values)
    for field, cited_values in entry.rejected.items():
        sections.setdefault(field, []).extend(cited_values)
    return sections


def _same_value(a: CitedValue, b: CitedValue) -> bool:
    return (a.value, a.citation_url, a.cwe) == (b.value, b.citation_url, b.cwe)


def _superseded(cited: CitedValue) -> bool:
    return cited.review_status == REJECTED or cited.review_comment is not None


def entry_id(name: str, field: str, cited: CitedValue) -> str:
    """A local item's stable id: ``<name>.<field>.<12 hex>`` over its value,
    link and CWE, never its tag or status, so an answer keeps it."""
    digest = hashlib.sha256(
        json.dumps([list(cited.value), cited.citation_url, cited.cwe or ""]).encode()
    ).hexdigest()
    return f"{name}.{field}.{digest[:12]}"


def parse_reviews(
    raw: object,
) -> tuple[dict[str, tuple[str, str | None]], list[str]]:
    """Validate agent-input ``reviews``: ``{entry_id: answer}`` where an
    answer is ``"good" | "improve" | "reject"`` or ``{"answer": ...,
    "comment": ...}``. Returns ``{entry_id: (answer, comment)}`` and errors;
    any error rejects the document. An unknown id is not an error here: it is
    ignored with a note (:func:`review_problems`)."""
    if raw is None:
        return {}, []
    if not isinstance(raw, dict):
        return {}, [
            "reviews: must be an object mapping an entry_id to good, improve "
            "or reject"
        ]
    if len(raw) > MAX_REVIEWS:
        return {}, [f"reviews: at most {MAX_REVIEWS} answers per call"]
    answers: dict[str, tuple[str, str | None]] = {}
    errors: list[str] = []
    for key, raw_answer in raw.items():
        if not isinstance(key, str) or not key or len(key) > MAX_ENTRY_ID_CHARS:
            errors.append(
                f"reviews: an entry id must be 1 to {MAX_ENTRY_ID_CHARS} characters"
            )
            continue
        where = f"reviews.{redact(key)}"
        value, comment = raw_answer, None
        if isinstance(raw_answer, dict):
            extra = sorted(str(k) for k in raw_answer if k not in ("answer", "comment"))
            if extra:
                errors.append(f"{where}: unknown key {', '.join(map(redact, extra))}")
                continue
            value, comment = raw_answer.get("answer"), raw_answer.get("comment")
        if not isinstance(value, str) or value not in REVIEW_ANSWERS:
            errors.append(f"{where}: answer must be good, improve or reject")
            continue
        if comment is not None:
            if not isinstance(comment, str) or len(comment) > MAX_COMMENT_CHARS:
                errors.append(
                    f"{where}.comment: must be a string of at most "
                    f"{MAX_COMMENT_CHARS} characters"
                )
                continue
            if _has_surrogate(comment):
                errors.append(
                    f"{where}.comment: holds a lone surrogate character, which "
                    "cannot be stored"
                )
                continue
            if redact(comment) != comment:
                errors.append(
                    f"{where}.comment: looks like it holds a secret; comments "
                    "are stored verbatim"
                )
                continue
        answers[key] = (value, comment)
    return answers, errors


def local_items(root: Path, known_roles: Collection[str]) -> list[dict]:
    """Every item of the local layer at ``root`` with its :func:`entry_id`,
    identity and :class:`CitedValue` (``cited``), sorted by id; ``[]`` when
    there is no usable layer."""
    if local_root_problem(root) or not root.is_dir():
        return []
    local = load_registry(root, known_roles=known_roles, local=True)
    items = []
    layers = (("language", local.languages), ("framework", local.frameworks))
    for kind, entries in layers:
        for entry in entries.values():
            for field, cited_values in _sections(entry).items():
                for cited in cited_values:
                    item: dict = {"entry_id": entry_id(entry.name, field, cited)}
                    item[kind] = entry.name
                    if kind == "framework":
                        item["extends"] = entry.extends
                    item.update(field=field, cited=cited)
                    items.append(item)
    return sorted(items, key=lambda item: item["entry_id"])


def awaiting_review(cited: CitedValue) -> bool:
    """Pending and never answered: the only items the review gate lists."""
    return cited.review_status == PENDING and cited.review_comment is None


def review_problems(
    answers: Mapping[str, tuple[str, str | None]],
    root: Path,
    known_roles: Collection[str],
) -> list[str]:
    """Notes for answers that will be ignored: unknown or already-reviewed
    ids. Computed before :func:`apply_reviews` changes anything."""
    if not answers:
        return []
    by_id = {item["entry_id"]: item["cited"] for item in local_items(root, known_roles)}
    notes = []
    for key in sorted(answers):
        if key not in by_id:
            notes.append(
                f"review for {redact(key)} ignored: no local registry entry has "
                "that id (it may have been replaced or deleted)"
            )
        elif not awaiting_review(by_id[key]):
            notes.append(
                f"review for {redact(key)} ignored: that entry was already "
                "reviewed, and a reviewed entry is never asked again"
            )
    return notes


def apply_reviews(
    answers: Mapping[str, tuple[str, str | None]],
    root: Path,
    *,
    known_roles: Collection[str],
) -> None:
    """Apply the user's answers to the local layer at ``root`` (T038).

    ``good`` approves (agent-researched items are retagged
    :data:`USER_APPROVED`); ``improve`` keeps the item pending with the
    comment and one more round; ``reject`` turns it into a rejection record.
    Only items awaiting review change; each changed file is rewritten
    atomically. Raises :class:`OSError` on any refusal, like
    :func:`save_local_entries`.
    """
    problem = local_root_problem(root)
    if problem:
        raise OSError(problem)
    if not answers or not root.is_dir():
        return
    known = frozenset(known_roles)
    for path in sorted(root.glob("*.toml"))[:MAX_LOCAL_FILES]:
        if path.is_symlink():
            continue
        entry, errors = _load_entry(path, known, local=True)
        if errors:
            continue
        sections = _sections(entry)
        changed = False
        for field, cited_values in sections.items():
            for index, cited in enumerate(cited_values):
                answer = answers.get(entry_id(entry.name, field, cited))
                if answer is not None and awaiting_review(cited):
                    cited_values[index] = _answered(cited, *answer)
                    changed = True
        if changed:
            data = _entry_toml(entry.extends, sections).encode("utf-8")
            if len(data) > MAX_ENTRY_BYTES:
                raise OSError(f"{path.name} would exceed {MAX_ENTRY_BYTES} bytes")
            _atomic_write(root, path, data)


def _answered(cited: CitedValue, answer: str, comment: str | None) -> CitedValue:
    if answer == "good":
        tag = cited.source_tag
        if tag == AGENT_RESEARCHED:
            tag = USER_APPROVED
        return dataclasses.replace(cited, review_status=APPROVED, source_tag=tag)
    if answer == "reject":
        return dataclasses.replace(cited, review_status=REJECTED)
    rounds = min(cited.improve_rounds + 1, MAX_IMPROVE_ROUNDS_STORED)
    return dataclasses.replace(
        cited, review_comment=comment or "", improve_rounds=rounds
    )


def _toml_str(text: str) -> str:
    """``text`` as a TOML basic string. ``json.dumps`` output is TOML only
    with ``ensure_ascii=False``: its ``\\uD83D\\uDE00`` surrogate-pair escapes
    are invalid TOML (T038 Stage 4 P1). JSON leaves DEL raw, which TOML
    forbids, so it is escaped here. Lone surrogates never get this far:
    validation refuses them (:func:`_has_surrogate`)."""
    return json.dumps(text, ensure_ascii=False).replace("\x7f", "\\u007f")


def _has_surrogate(text: str) -> bool:
    """A lone surrogate cannot be written as UTF-8 or TOML."""
    return any("\ud800" <= char <= "\udfff" for char in text)


def _entry_toml(extends: str | None, sections: Mapping[str, list[CitedValue]]) -> str:
    lines = ["# easy-verifier local reference registry entry (T036)."]
    if extends is not None:
        lines.append(f"extends = {_toml_str(extends)}")
    for field in sorted(sections):
        ordered = sorted(
            sections[field],
            key=lambda c: (c.value, c.citation_url, c.source_tag, c.cwe or ""),
        )
        for cited in ordered:
            lines += [
                "",
                f"[[{field}]]",
                "value = [" + ", ".join(_toml_str(v) for v in cited.value) + "]",
                f"citation_url = {_toml_str(cited.citation_url)}",
                f"source_tag = {_toml_str(cited.source_tag)}",
            ]
            if cited.cwe:
                lines.append(f"cwe = {_toml_str(cited.cwe)}")
            status = cited.review_status or PENDING
            lines.append(f"review_status = {_toml_str(status)}")
            if cited.review_comment is not None:
                lines.append(f"review_comment = {_toml_str(cited.review_comment)}")
            if cited.improve_rounds:
                lines.append(f"improve_rounds = {cited.improve_rounds}")
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
    if any(char.isspace() for char in url) or _has_surrogate(url):
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
    "APPROVED",
    "CURATED",
    "ENTRY_FIELDS",
    "LOCAL_TAGS",
    "MAX_AGENT_ENTRIES",
    "MAX_ENTRY_BYTES",
    "MAX_REVIEWS",
    "PENDING",
    "REJECTED",
    "SOT_ENV",
    "USER_APPROVED",
    "USER_SUPPLIED",
    "apply_reviews",
    "awaiting_review",
    "entry_id",
    "local_items",
    "parse_reviews",
    "review_problems",
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
