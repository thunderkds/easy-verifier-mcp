"""Registry-driven code tokens: approximate CCN and import statements (T033).

Pure string work over text a caller already holds (an excerpt); nothing here
reads a file. All language knowledge -- comment and string delimiters, branch
keywords, function-start and import tokens -- arrives as a
:class:`LanguageSyntax` compiled from the reference registry by
``core/metric_tables.py`` (DDR-0007, decision B1).

**Approximate CCN (lizard-style), McCabe 1976.** Comments and strings are
blanked first (every character but newline becomes a space, so line numbers
and indentation survive), then each function scores 1 + the branch-keyword
matches on its own lines. The rules, stated once:

* a **function** starts on a line where a ``function_start`` token matches,
  unless that line's code ends in ``;`` (a declaration with no body);
* it **ends** before the next non-blank line indented no deeper than its start
  line; a line beginning with a bracket ``)``, ``]``, ``}`` or ``{``
  continues it (a wrapped signature, a brace on its own line);
* a line belongs to the **innermost** function containing it, so a nested
  function's decisions are not also counted in its parent;
* lines longer than :data:`MAX_LINE_CHARS` (generated or minified code) are
  ignored entirely.

Anything the registry does not declare as a function start (a lambda, a Ruby
block, a JavaScript class method) is not a function: its decisions count
toward the enclosing function, or toward none at top level.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

MAX_LINE_CHARS = 500
"""Longer lines are treated as generated/minified and ignored."""

MAX_IMPORT_LINES = 100
"""An import statement spanning more lines than this is cut off."""

INTERPOLATION_MARK = "\x00"
"""Left by ``strip(..., mark_interpolation=True)`` in place of the first
character of a string literal that interpolates (T034). One fixed character,
so the stripped text keeps its length; registry tokens name it ``<INTERP>``."""

_BLANK = re.compile(r"[^\n]")
_NAME_START = re.compile(r"[A-Za-z_{]")
_CONTINUES = frozenset(")]}{")


@dataclass(frozen=True)
class Delimiter:
    """One comment or string delimiter, parsed from a registry value.

    ``"X"`` runs to the end of the line (a comment) or to the next ``X`` on
    the same line (a string); ``"X Y"`` runs from ``X`` to the next ``Y``,
    across lines. Strings honour backslash escapes; comments do not.
    """

    opener: str
    string: bool
    end: re.Pattern[str]
    interpolation: tuple[str, ...] = ()
    """Openers of an embedded expression, e.g. ``${`` (T034); empty when the
    literal never interpolates."""

    @classmethod
    def parse(cls, value: str, *, string: bool) -> Delimiter:
        opener, _, closer = value.partition(" ")
        if string:
            close = re.escape(closer or opener)
            tail = "" if closer else r"|\n"
            end = re.compile(r"\\.|" + close + tail, re.DOTALL)
        else:
            end = re.compile(re.escape(closer) if closer else r"\n")
        return cls(opener=opener, string=string, end=end)


@dataclass(frozen=True)
class LanguageSyntax:
    """One language's structure tokens, compiled."""

    language: str
    opener: re.Pattern[str]
    """Alternation of every delimiter opener, longest first."""
    delimiters: Mapping[str, Delimiter]
    branch: re.Pattern[str]
    function_start: re.Pattern[str]
    imports: re.Pattern[str]


def language_syntax(
    language: str,
    *,
    comments: Sequence[str],
    strings: Sequence[str],
    branch: re.Pattern[str],
    function_start: re.Pattern[str],
    imports: re.Pattern[str],
    interpolations: Sequence[str] = (),
) -> LanguageSyntax:
    """Build a :class:`LanguageSyntax`; delimiters are escaped, never regex.

    ``interpolations`` holds ``"X Y"`` values: a string literal opened by
    ``X`` embeds an expression where ``Y`` occurs in it (T034).
    """
    embedded: dict[str, list[str]] = {}
    for value in interpolations:
        opener, _, inner = value.partition(" ")
        if inner:
            embedded.setdefault(opener, []).append(inner)
    delimiters: dict[str, Delimiter] = {}
    for value in strings:
        delimiter = Delimiter.parse(value, string=True)
        delimiter = replace(
            delimiter, interpolation=tuple(embedded.get(delimiter.opener, ()))
        )
        delimiters.setdefault(delimiter.opener, delimiter)
    for value in comments:
        delimiter = Delimiter.parse(value, string=False)
        delimiters.setdefault(delimiter.opener, delimiter)
    ordered = sorted(delimiters, key=lambda opener: (-len(opener), opener))
    return LanguageSyntax(
        language=language,
        opener=re.compile("|".join(re.escape(opener) for opener in ordered)),
        delimiters=delimiters,
        branch=branch,
        function_start=function_start,
        imports=imports,
    )


def strip(
    text: str,
    syntax: LanguageSyntax,
    *,
    keep_strings: bool = False,
    mark_interpolation: bool = False,
) -> str:
    """``text`` with comments (and strings, unless ``keep_strings``) blanked.

    The result has the same length and the same newlines as ``text``. An
    unterminated literal runs to the end of the text (a single-line string:
    to the end of its line). With ``mark_interpolation``, a blanked string
    literal that embeds an expression starts with :data:`INTERPOLATION_MARK`
    instead of a space; one without an embedded expression stays all blank.
    """
    parts: list[str] = []
    position = 0
    while True:
        match = syntax.opener.search(text, position)
        if match is None:
            break
        delimiter = syntax.delimiters[match.group()]
        end = _literal_end(text, match.end(), delimiter)
        literal = text[match.start() : end]
        parts.append(text[position : match.start()])
        if delimiter.string and keep_strings:
            parts.append(literal)
        elif mark_interpolation and _interpolates(literal, delimiter):
            parts.append(INTERPOLATION_MARK + _BLANK.sub(" ", literal[1:]))
        else:
            parts.append(_BLANK.sub(" ", literal))
        position = end
    parts.append(text[position:])
    return "".join(parts)


def _interpolates(literal: str, delimiter: Delimiter) -> bool:
    """Whether ``literal`` embeds an expression: an unescaped opener, and an
    opener ending in ``$`` only before a name or ``{`` (``"$5"`` is text)."""
    body = literal[len(delimiter.opener) :]
    for opener in delimiter.interpolation:
        index = body.find(opener)
        while index != -1:
            after = body[index + len(opener) : index + len(opener) + 1]
            escaped = index > 0 and body[index - 1] == "\\"
            if not escaped and (not opener.endswith("$") or _NAME_START.match(after)):
                return True
            index = body.find(opener, index + 1)
    return False


def _literal_end(text: str, index: int, delimiter: Delimiter) -> int:
    while True:
        match = delimiter.end.search(text, index)
        if match is None:
            return len(text)
        token = match.group()
        if token == "\n":
            return match.start()
        if delimiter.string and token.startswith("\\"):
            index = match.end()
            continue
        return match.end()


@dataclass(frozen=True)
class FunctionCcn:
    """One observed function: 1-indexed lines within the text, and its CCN."""

    line: int
    end_line: int
    ccn: int


def approximate_ccn(text: str, syntax: LanguageSyntax) -> tuple[FunctionCcn, ...]:
    """Approximate CCN of every function starting in ``text`` (rules above)."""
    lines = strip(text, syntax).split("\n")
    usable = [len(line) <= MAX_LINE_CHARS for line in lines]

    spans: list[tuple[int, int]] = []
    for start, line in enumerate(lines):
        if not usable[start] or not syntax.function_start.search(line):
            continue
        if line.rstrip().endswith(";"):
            continue
        indent = _indent(line)
        end = start
        for index in range(start + 1, len(lines)):
            candidate = lines[index]
            if not candidate.strip() or not usable[index]:
                continue
            if _indent(candidate) <= indent:
                if candidate.lstrip()[0] not in _CONTINUES:
                    break
            end = index
        spans.append((start, end))

    owner: list[int | None] = [None] * len(lines)
    for number, (start, end) in enumerate(spans):
        owner[start : end + 1] = [number] * (end - start + 1)  # inner overwrites
    decisions = [0] * len(spans)
    for index, line in enumerate(lines):
        if usable[index] and owner[index] is not None:
            decisions[owner[index]] += len(syntax.branch.findall(line))

    return tuple(
        FunctionCcn(line=start + 1, end_line=end + 1, ccn=1 + count)
        for (start, end), count in zip(spans, decisions, strict=True)
    )


def import_statements(text: str, syntax: LanguageSyntax) -> tuple[tuple[int, str], ...]:
    """``(1-indexed line, statement text)`` for each import in ``text``.

    The import token is found in code (comments and strings blanked); the
    statement text runs from the token to the end of its line, strings kept,
    and continues onto following lines while brackets stay open.
    """
    code = strip(text, syntax).split("\n")
    kept = strip(text, syntax, keep_strings=True).split("\n")
    found: list[tuple[int, str]] = []
    index = 0
    while index < len(code):
        line = code[index]
        match = syntax.imports.search(line) if len(line) <= MAX_LINE_CHARS else None
        if match is None:
            index += 1
            continue
        start = index
        statement = [kept[index][match.start() :]]
        depth = _depth(line[match.start() :])
        while depth > 0 and index + 1 < len(code) and index - start < MAX_IMPORT_LINES:
            index += 1
            statement.append(kept[index])
            depth += _depth(code[index])
        found.append((start + 1, "\n".join(statement)))
        index += 1
    return tuple(found)


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def _depth(code: str) -> int:
    return sum(code.count(c) for c in "({[") - sum(code.count(c) for c in ")}]")


__all__ = [
    "INTERPOLATION_MARK",
    "MAX_IMPORT_LINES",
    "MAX_LINE_CHARS",
    "Delimiter",
    "FunctionCcn",
    "LanguageSyntax",
    "approximate_ccn",
    "import_statements",
    "language_syntax",
    "strip",
]
