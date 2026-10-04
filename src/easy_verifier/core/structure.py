"""Code-structure convention finders (T073, DDR-0011, FR-068).

Pure string work over text and paths a caller already holds; nothing here
reads a target repository. Every form recognised comes from a declared, cited
pattern list in the reference registry (``core/registry.py``): ``layer_paths``,
``requirement_item_patterns`` and ``issue_reference_patterns`` in the
``conventions`` entry, ``route_tokens`` per language. A repository extends
any of them through the local layer or ``.easy-verifier.toml``; callers pass
the extended lists, and each function defaults to the curated one.

Patterns are code tokens in the registry token syntax (compiled by
``metric_tables.token_regex``, so a value cannot inject regex). Every match is
textual, never parsed: a derivation built on these says so.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache
from pathlib import PurePosixPath

from .metric_tables import curated_metric_tables, token_regex
from .metrics import LanguageTables, _is_test_file
from .registry import Registry, RegistryEntry, load_conventions
from .roles import _config_matcher
from .tokens import LanguageSyntax, strip

MAX_HANDLER_LINES = 10
"""Lines after a route decorator searched for the handler's declaration."""

MAX_ARGUMENT_CHARS = 2000
"""Characters of a route call's or decorator's argument list examined."""

_DECORATOR_STARTS = ("@", "[", "#[")
_PATH_LITERAL = re.compile(r"\s*\(?\s*(?:\w+\s*[=:]\s*)?([\"'`])([^\"'`\n]{0,200})\1")
_DECLARED_NAME = re.compile(r"([A-Za-z_]\w*)\s*\(")
_IDENTIFIER = re.compile(r"[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*")
_KEYWORD_ARGUMENT = re.compile(r"[A-Za-z_]\w*\s*=(?!=)")
_CLOSERS = {"(": ")", "[": "]", "{": "}"}


@dataclass(frozen=True)
class Route:
    """One route handler found in source text."""

    line: int
    method: str
    """The token's declared method, ``ANY`` when the token does not fix one."""
    path: str | None
    """The string literal right after the token, if there is one."""
    handler: str | None


@dataclass(frozen=True)
class RequirementItem:
    """One requirement statement: an identifier, or a line's text."""

    line: int
    kind: str
    """``id`` (an identifier such as ``AC-3``) or ``line`` (the text after a
    line-start marker such as ``Scenario:``)."""
    text: str


def convention_values(entry: RegistryEntry | None, field: str) -> tuple[str, ...]:
    """Every value of ``field`` in ``entry``, in order, duplicates dropped."""
    if entry is None:
        return ()
    return tuple(
        dict.fromkeys(v for cited in entry.fields.get(field, ()) for v in cited.value)
    )


@lru_cache(maxsize=1)
def _curated() -> RegistryEntry:
    return load_conventions()[0]


def route_tokens_for(
    registry: Registry, language: str, conventions: RegistryEntry | None = None
) -> tuple[str, ...]:
    """``language``'s ``route_tokens`` plus the repository-wide ones in
    ``conventions``; ``()`` for a language the registry does not hold."""
    tokens = convention_values(registry.languages.get(language), "route_tokens")
    return tuple(dict.fromkeys(tokens + convention_values(conventions, "route_tokens")))


# ---------------------------------------------------------------------------
# layers
# ---------------------------------------------------------------------------


def layer_of(
    path: str,
    layer_paths: Sequence[str] | None = None,
    *,
    tables: LanguageTables | None = None,
) -> str | None:
    """``api``, ``service``, ``data`` or ``shared`` (cross-cutting, T074) for a
    repository-relative source file, or ``None`` when it is unclassified.

    ``layer_paths`` are ``<layer>=<glob>`` values (default: curated). ``\\``
    separators are normalised. A file that is not source, is a test (the
    metrics rule over ``tables``, default curated), or matches globs of two
    different layers is unclassified: a layer is never guessed.
    """
    patterns = (
        convention_values(_curated(), "layer_paths")
        if layer_paths is None
        else tuple(layer_paths)
    )
    tables = curated_metric_tables() if tables is None else tables
    path = path.replace("\\", "/").removeprefix("./")
    if PurePosixPath(path).suffix not in tables.source_suffixes:
        return None
    if _is_test_file(path, tables):
        return None
    layers = {layer for layer, matches in _layer_matchers(patterns) if matches(path)}
    return layers.pop() if len(layers) == 1 else None


@lru_cache(maxsize=32)
def _layer_matchers(patterns: tuple[str, ...]):
    by_layer: dict[str, list[str]] = {}
    for value in patterns:
        layer, _, glob = value.partition("=")
        by_layer.setdefault(layer, []).append(glob)
    return tuple(
        (layer, _config_matcher(tuple(globs))) for layer, globs in by_layer.items()
    )


# ---------------------------------------------------------------------------
# routes
# ---------------------------------------------------------------------------


def find_routes(
    text: str, route_tokens: Sequence[str], syntax: LanguageSyntax | None
) -> tuple[Route, ...]:
    """Route handlers in one source file's ``text``.

    ``route_tokens`` are ``<METHOD>=<token>`` values (:func:`route_tokens_for`).
    Tokens are code, so they match only after comments and strings are blanked
    with ``syntax``; with no tokens or no syntax (an unknown language) nothing
    is found. Where two tokens match at one place the longest wins. The path is
    the string literal right after the token (a named argument such as
    ``value =`` is skipped), read from the original text. A token starting
    with ``@``, ``[`` or ``#[`` is a decorator: its handler is the first
    identifier before ``(`` on the next declaration line. Any other token is a
    call: its handler is the last positional argument when that is a (dotted)
    identifier, else ``None``.
    """
    if not route_tokens or syntax is None:
        return ()
    code = strip(text, syntax)
    found = [
        (match.start(), match.end(), method, token)
        for method, token, regex in _route_patterns(tuple(route_tokens))
        for match in regex.finditer(code)
    ]
    routes: list[Route] = []
    taken = -1
    for start, end, method, token in sorted(found, key=lambda f: (f[0], f[0] - f[1])):
        if start < taken:
            continue
        taken = end
        literal = _PATH_LITERAL.match(text, end)
        decorator = token.startswith(_DECORATOR_STARTS)
        routes.append(
            Route(
                line=code.count("\n", 0, start) + 1,
                method=method,
                path=literal[2] if literal else None,
                handler=(_decorated_name if decorator else _call_handler)(code, end),
            )
        )
    return tuple(routes)


@lru_cache(maxsize=64)
def _route_patterns(values: tuple[str, ...]):
    patterns = []
    for value in values:
        method, _, token = value.partition("=")
        if token:
            patterns.append((method, token, re.compile(token_regex(token))))
    return tuple(patterns)


def _arguments(code: str, position: int) -> tuple[str, int]:
    """The bracketed argument text opened at or right after ``position`` (or
    just before it, when the token itself ends in ``(``) and the index after
    its close; ``("", position)`` when there is none."""
    if code[position - 1 : position] == "(":
        start = position - 1
    else:
        skipped = len(code[position:]) - len(code[position:].lstrip())
        start = position + skipped
        if code[start : start + 1] != "(":
            return "", position
    stack: list[str] = []
    limit = min(len(code), start + MAX_ARGUMENT_CHARS)
    for index in range(start, limit):
        char = code[index]
        if char in _CLOSERS:
            stack.append(_CLOSERS[char])
        elif stack and char == stack[-1]:
            stack.pop()
            if not stack:
                return code[start + 1 : index], index + 1
    return code[start + 1 : limit], limit


def _decorated_name(code: str, position: int) -> str | None:
    _, after = _arguments(code, position)
    rest_of_line, _, following = code[after:].partition("\n")
    lines = [rest_of_line.lstrip(" ])\t"), *following.split("\n")[:MAX_HANDLER_LINES]]
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith(_DECORATOR_STARTS):
            continue
        match = _DECLARED_NAME.search(stripped)
        return match[1] if match else None
    return None


def _call_handler(code: str, position: int) -> str | None:
    arguments, _ = _arguments(code, position)
    parts: list[str] = []
    depth, current = 0, []
    for char in arguments:
        if char in _CLOSERS:
            depth += 1
        elif char in _CLOSERS.values():
            depth -= 1
        if char == "," and depth == 0:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(char)
    parts.append("".join(current).strip())
    positional = [p for p in parts if p and not _KEYWORD_ARGUMENT.match(p)]
    if positional and _IDENTIFIER.fullmatch(positional[-1]):
        return positional[-1].rsplit(".", 1)[-1]
    return None


# ---------------------------------------------------------------------------
# requirement items and issue references (prose: matched on raw text)
# ---------------------------------------------------------------------------


def find_requirement_items(
    text: str, patterns: Sequence[str] | None = None
) -> tuple[RequirementItem, ...]:
    """Requirement items in a document's raw ``text`` (prose: nothing is
    blanked), in text order, each distinct ``(kind, text)`` once.

    ``patterns`` are ``id=<token>`` values, matched anywhere as a whole
    identifier (not right after a letter, digit or ``_``), and
    ``line=<token>`` values, matched at a line start after indentation, the
    item being the rest of that line without surrounding quotes or a trailing
    comma (an empty rest is no item). Default: curated.
    """
    values = (
        convention_values(_curated(), "requirement_item_patterns")
        if patterns is None
        else tuple(patterns)
    )
    found: list[tuple[int, RequirementItem]] = []
    for kind, regex in _item_patterns(values):
        for match in regex.finditer(text):
            if kind == "id":
                item_text = match[0]
            else:
                item_text = match[1].strip().rstrip(",").strip().strip("\"'").strip()
            if item_text:
                line = text.count("\n", 0, match.start()) + 1
                found.append((match.start(), RequirementItem(line, kind, item_text)))
    seen: set[tuple[str, str]] = set()
    items = []
    for _, item in sorted(found, key=lambda pair: pair[0]):
        if (item.kind, item.text) not in seen:
            seen.add((item.kind, item.text))
            items.append(item)
    return tuple(items)


@lru_cache(maxsize=32)
def _item_patterns(values: tuple[str, ...]):
    patterns = []
    for value in values:
        kind, _, token = value.partition("=")
        if not token:
            continue
        if kind == "id":
            patterns.append((kind, re.compile(r"(?<!\w)" + token_regex(token))))
        elif kind == "line":
            patterns.append(
                (
                    kind,
                    re.compile(
                        r"^[ \t]*" + token_regex(token) + r"[ \t]*([^\n]*)$",
                        re.MULTILINE,
                    ),
                )
            )
    return tuple(patterns)


def find_issue_references(
    message: str, patterns: Sequence[str] | None = None
) -> tuple[str, ...]:
    """Issue references in one commit message's raw text (prose: nothing is
    blanked), distinct, in text order.

    ``patterns`` are tokens (default: curated), matched not right after a
    letter, digit or ``_``. Where two match at one place the longest wins, so
    ``Fixes #4`` is one reference, not two.
    """
    values = (
        convention_values(_curated(), "issue_reference_patterns")
        if patterns is None
        else tuple(patterns)
    )
    found = [
        (match.start(), match.end())
        for regex in _reference_patterns(values)
        for match in regex.finditer(message)
    ]
    references: list[str] = []
    taken = -1
    for start, end in sorted(found, key=lambda span: (span[0], span[0] - span[1])):
        if start >= taken:
            taken = end
            references.append(message[start:end])
    return tuple(dict.fromkeys(references))


@lru_cache(maxsize=32)
def _reference_patterns(values: tuple[str, ...]):
    return tuple(re.compile(r"(?<!\w)" + token_regex(token)) for token in values)


__all__ = [
    "RequirementItem",
    "Route",
    "convention_values",
    "find_issue_references",
    "find_requirement_items",
    "find_routes",
    "layer_of",
    "route_tokens_for",
]
