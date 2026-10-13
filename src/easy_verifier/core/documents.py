"""Document roles filled by content or declaration, never by a name alone
(T089, FR-076, DDR-0012 §3).

A role is filled by the first of:

1. **declared**: a ``.easy-verifier.toml`` role glob or an MCP detect-gate
   pick names the file. The project's word is taken without a content check.
2. **content** (``readme-heading`` when it is a README section headed
   "Architecture"): a document whose text has the role's shape.

Every document in the repository file set the role walk already listed is a
candidate (``.md``, ``.rst``, ``.adoc``, ``.txt``); files matching the role's
conventional name patterns are only scanned first. Entry paths are checked
against that same file set, never against the disk. "Missing" is then a
measured fact: no scanned document has the shape.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from pathlib import PurePosixPath

from .context import MAX_DOC_SOURCES, MAX_LINE_CHARS, _is_secret_bearing
from .metrics import (
    ARCHITECTURE_HEADING,
    MIN_DESCRIBED_ENTRIES,
    MIN_DESCRIPTION_WORDS,
    MIN_REQUIREMENT_LIST_ITEMS,
)
from .models import DocumentEvidence
from .roles import MAX_ROLE_FILES, MAX_ROLE_WALK_FILES, ORIGIN_RULES, _is_template
from .structure import context_conventions, convention_values, find_requirement_items

MAX_SCANNED_DOCUMENTS = MAX_DOC_SOURCES
"""Documents whose content one role scan examines; reaching it with the role
unfilled abstains (the rest were never read), it never reads as missing."""

MAX_DOCUMENT_CHARS = 1_000_000
"""Characters of one document scanned (a bounded read): a larger document,
such as a book kept as ``.txt``, is scanned over its first part only."""

MAX_CITED_LINES = 5

DOCUMENT_SUFFIXES = (".md", ".rst", ".adoc", ".txt")

KIND_CONTENT = "content"
KIND_DECLARED = "declared"
KIND_README_HEADING = "readme-heading"
KIND_ARCHITECTURE_HEADING = "architecture-heading"

ARCHITECTURE_DOC = "architecture-doc"
DECISION_RECORD = "decision-record"
REQUIREMENTS_DOC = "requirements-doc"


_CHANGELOG = re.compile(r"^(changelog|changes|history|news|release[-_ ]?notes)", re.I)


def _is_changelog(path: str) -> bool:
    """A changelog lists files with a few words each (``- src/a.ts: fix
    typo``), which is the architecture shape; it is a history, not a map."""
    return bool(_CHANGELOG.match(PurePosixPath(path).name))


_EXCLUDED = {
    # T089 decision C: a template is never a project document, for any role
    ARCHITECTURE_DOC: lambda path: _is_changelog(path) or _is_template(path),
    DECISION_RECORD: _is_template,
    REQUIREMENTS_DOC: _is_template,
}


# ---------------------------------------------------------------------------
# architecture-doc: described entries naming real paths
# ---------------------------------------------------------------------------


def known_paths(files: Iterable[str]) -> frozenset[str]:
    """Every file of ``files`` and every directory above one: the paths an
    entry may name. Secret-bearing files are left out: naming one never
    counts."""
    known: set[str] = set()
    for path in files:
        parts = path.split("/")
        last = len(parts) - 1 if _is_secret_bearing(path) else len(parts)
        known.update("/".join(parts[:end]) for end in range(1, last + 1))
    return frozenset(known)


_LEAD = re.compile(r"^(?:[\s│├└┬┼┃┣┗┡┠─━|+>*`-]|\d{1,3}[.)]\s)*")
_TOKEN = re.compile(r"\[([^\]\n]*)\]\(([^)\s]+)\)|[^\s`*:|#,()\[\]]+")
_SEPARATOR = re.compile(r"^(?:[`*_]*)(?:\s*:[`*_]*\s+|\s+[-–—]+\s+|\s*#+\s*|\s{2,})")
_WORD = re.compile(r"[぀-ヿ㐀-鿿]|[^\W_぀-ヿ㐀-鿿]+")
_TABLE_SEPARATOR = re.compile(r"^[\s|:-]+$")

CHANGE_COLUMNS = frozenset(
    {"change", "changes", "action", "edit", "modification", "status", "todo", "reason"}
)
"""Column titles of a plan of edits (T096): a table with one lists what to
touch and why, a to-do for the files it names, not a description of the system
(``Reason`` covers a "Files Must NOT Touch" table)."""


def normalize_path(token: str) -> str:
    """``./src/``, ``/apps/api/**`` and `` `core/judge.py` `` name the paths
    ``src``, ``apps/api`` and ``core/judge.py``."""
    path = token.strip().strip("`'\"*")
    while path.startswith("./"):
        path = path[2:]
    path = re.sub(r"(?:/\*{1,2})+$", "", path.lstrip("/")).rstrip("/")
    return "" if path in ("", ".", "..") or "../" in path else path


def _words(text: str) -> int:
    return len(_WORD.findall(text))


def described_entries(
    text: str, known: frozenset[str], base: str = ""
) -> list[tuple[int, str, str]]:
    """``(line, path, line text)`` of each described entry, one per distinct
    path, in text order: a list item, tree line (inside a code block too) or
    table row naming a path in ``known``, followed by at least
    :data:`MIN_DESCRIPTION_WORDS` words.

    A name resolves under the nearest less-indented path line above it (a
    tree or nested list), else under ``base`` (the document's directory),
    else from the repository root."""
    found: dict[str, tuple[int, str, str]] = {}
    parents: list[tuple[int, str]] = []
    fenced = False
    header: str | None = None  # the table row just above, until a separator
    change_list = False
    for number, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith(("```", "~~~")):
            fenced = not fenced
            parents.clear()
            header, change_list = None, False
            continue
        if len(line) > MAX_LINE_CHARS or not line.strip():
            header, change_list = None, False
            continue
        if line.lstrip().startswith("|") and line.rstrip().endswith("|"):
            if _TABLE_SEPARATOR.match(line):
                change_list = header is not None and _is_change_header(header)
                header = None
                continue
            header = line
            if change_list:
                continue
            path, described = _table_entry(line, known, base)
        else:
            header, change_list = None, False
            depth = _LEAD.match(line).end()
            while parents and parents[-1][0] >= depth:
                parents.pop()
            if not fenced and not line[:depth].strip():
                # prose: only a list item or tree line is an entry outside
                # a code block
                parents.clear()
                continue
            prefixes = [*(p for _d, p in reversed(parents)), base, ""]
            path, described = _line_entry(line[depth:], known, prefixes)
            if path is not None:
                parents.append((depth, path))
        if described and path not in found:
            found[path] = (number, path, line.strip())
    return list(found.values())


def _is_change_header(row: str) -> bool:
    cells = (
        cell.strip().strip("`*_ ").lower() for cell in row.strip().strip("|").split("|")
    )
    return any(cell in CHANGE_COLUMNS for cell in cells)


def _resolve(name: str, known: frozenset[str], prefixes: Sequence[str]) -> str | None:
    path = normalize_path(name)
    if not path:
        return None
    for prefix in prefixes:
        joined = f"{prefix}/{path}" if prefix else path
        if joined in known:
            return joined
    return None


def _table_entry(line: str, known, base: str) -> tuple[str | None, bool]:
    if _TABLE_SEPARATOR.match(line):
        return None, False
    cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
    for index, cell in enumerate(cells):
        token = cell.strip("`*")
        if not token or any(char.isspace() for char in token):
            continue
        path = _resolve(token, known, (base, ""))
        rest = " ".join(cells[:index] + cells[index + 1 :])
        if path is not None and _words(rest) >= MIN_DESCRIPTION_WORDS:
            return path, True
    return None, False


def _line_entry(rest: str, known, prefixes) -> tuple[str | None, bool]:
    """``(path named at the start of rest, whether it is described)``."""
    token = _TOKEN.match(rest)
    if token is None:
        return None, False
    names = (token[2], token[1]) if token[2] else (token[0],)
    path = next((p for p in (_resolve(n, known, prefixes) for n in names) if p), None)
    if path is None:
        return None, False
    separator = _SEPARATOR.match(rest[token.end() :])
    if separator is None:
        return path, False
    description = rest[token.end() + separator.end() :]
    return path, _words(description) >= MIN_DESCRIPTION_WORDS


def _section_at(lines: list[str], start: int) -> int:
    """End (exclusive) of the section whose ATX heading is ``lines[start]``:
    the next heading of the same or a higher level."""
    level = len(lines[start].lstrip()) - len(lines[start].lstrip().lstrip("#"))
    return next(
        (
            index
            for index in range(start + 1, len(lines))
            if re.match(rf"^\s{{0,3}}#{{1,{level}}}\s", lines[index])
        ),
        len(lines),
    )


def _architecture_section(text: str, min_level: int = 1) -> tuple[int, str] | None:
    """``(first line, text)`` of a section headed "Architecture" at heading
    level ``min_level`` or deeper. A level-1 heading is the document's title,
    whose section is the whole document (T096)."""
    for match in ARCHITECTURE_HEADING.finditer(text):
        hashes = text.index("#", match.start())
        level = len(text[hashes:]) - len(text[hashes:].lstrip("#"))
        if level < min_level:
            continue
        start = text.count("\n", 0, hashes)
        lines = text.splitlines()
        return start, "\n".join(lines[start : _section_at(lines, start)])
    return None


_URL = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*://\S*")
_CODE_SPAN = re.compile(r"`([^`\n]+)`")
_PROSE_TOKEN = re.compile(r"[^\s`*,;:()\[\]|<>\"'=]+")


def prose_paths(
    text: str, known: frozenset[str], base: str = ""
) -> list[tuple[int, str, str]]:
    """``(line, path, line text)`` of each distinct real path ``text`` names,
    at its first mention: an inline code span, or a bare token containing a
    ``/`` (a bare word such as "api" is ordinary prose). URLs name nothing."""
    found: dict[str, tuple[int, str, str]] = {}
    for number, line in enumerate(text.splitlines(), 1):
        if len(line) > MAX_LINE_CHARS:
            continue
        plain = _URL.sub(" ", line)
        spans = _CODE_SPAN.findall(plain)
        bare = [t for t in _PROSE_TOKEN.findall(_CODE_SPAN.sub(" ", plain)) if "/" in t]
        for name in (*spans, *bare):
            path = _resolve(name.rstrip(".").strip(), known, (base, ""))
            if path is not None and path not in found:
                found[path] = (number, path, line.strip())
    return list(found.values())


# ---------------------------------------------------------------------------
# requirements-doc: a heading naming requirements over a list (AC 12)
# ---------------------------------------------------------------------------

_REQUIREMENTS_HEADING = re.compile(
    # T089 decision A: only explicit names; a bare "Requirements" (or
    # "Prerequisites", "System Requirements") heading usually lists install
    # prerequisites
    r"^\s{0,3}#{1,6}\s[^\n]*\b(functional requirements|non-functional requirements"
    r"|nonfunctional requirements|product requirements|business requirements"
    r"|user stories|acceptance criteria|use cases)\b",
    re.I,
)
_LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d{1,3}[.)])\s+\S")


def requirement_list_lines(text: str) -> list[tuple[int, str]]:
    """``(line, text)`` of the first heading naming requirements followed by
    at least :data:`MIN_REQUIREMENT_LIST_ITEMS` list items before the next
    heading of the same or a higher level (its heading line first), or
    ``[]``."""
    lines = text.splitlines()
    for start, line in enumerate(lines):
        if len(line) > MAX_LINE_CHARS or not _REQUIREMENTS_HEADING.match(line):
            continue
        items = [
            (index + 1, lines[index].strip())
            for index in range(start + 1, _section_at(lines, start))
            if len(lines[index]) <= MAX_LINE_CHARS and _LIST_ITEM.match(lines[index])
        ]
        if len(items) >= MIN_REQUIREMENT_LIST_ITEMS:
            return [(start + 1, line.strip()), *items]
    return []


# ---------------------------------------------------------------------------
# decision-record: decision structure
# ---------------------------------------------------------------------------

_HEADING_LEAD = r"^\s{0,3}#{1,6}\s*(?:\d+[.)]?\s*)?(?:[^\w\s]+\s*)?"
_FIELD_LEAD = r"^\s{0,3}(?:[-*+]\s+)?(?:\*\*|__)?"
_FIELD_END = r"(?:\*\*|__)?\s*:"
_DECISION_NAMES = (
    r"(decision outcome|decisions?|recommended path|recommendation"
    r"|chosen(?: option)?|selected(?: option)?|approved direction)\b"
)
_SUPPORT_NAMES = (
    # singular forms too: a kit brainstorming log heads "## Alternative
    # Paths" and "### Option A"
    r"(context|consequences|status|alternatives?(?: considered)?"
    r"|considered options|options?)\b"
)
_DECISION_FIELD = re.compile(
    f"(?:{_HEADING_LEAD}{_DECISION_NAMES}|{_FIELD_LEAD}{_DECISION_NAMES}{_FIELD_END})",
    re.I,
)
_SUPPORT_FIELD = re.compile(
    f"(?:{_HEADING_LEAD}{_SUPPORT_NAMES}|{_FIELD_LEAD}{_SUPPORT_NAMES}{_FIELD_END})",
    re.I,
)
_DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_DECISION_VERB = re.compile(r"\b(decided|chose|chosen|we will)\b", re.I)
_RATIONALE = re.compile(r"\b(because|instead of|trade-?offs?)\b", re.I)
MAX_DATED_ENTRY_LINES = 10


def decision_lines(text: str) -> list[tuple[int, str]]:
    """``(line, text)`` showing a decision structure, or ``[]``."""
    lines = text.splitlines()
    decision = support = None
    for number, line in enumerate(lines, 1):
        if len(line) > MAX_LINE_CHARS:
            continue
        if decision is None and _DECISION_FIELD.match(line):
            decision = (number, line.strip())
        elif support is None and _SUPPORT_FIELD.match(line):
            support = (number, line.strip())
    if decision is not None and support is not None:
        # T089 AC 11: a decision plus its context; Context + Status alone is
        # a status page, not a decision record
        return sorted((decision, support))
    for index, line in enumerate(lines):
        if not _DATE.search(line) or len(line) > MAX_LINE_CHARS:
            continue
        entry = [line]
        for following in lines[index + 1 : index + MAX_DATED_ENTRY_LINES]:
            if not following.strip() or _DATE.search(following):
                break
            entry.append(following)
        joined = " ".join(entry)
        if _DECISION_VERB.search(joined) and _RATIONALE.search(joined):
            return [(index + 1, line.strip())]
    return []


# ---------------------------------------------------------------------------
# the scan
# ---------------------------------------------------------------------------


def scan_document_roles(context: object, roles: Sequence[str]) -> None:
    """Record on ``context.documents`` what fills each of ``roles``, once:
    ``collect`` may run once per budget tier, and this reads no evidence the
    budget could cut (candidates are peeked; only the filling one is read)."""
    if getattr(context, "documents", None) is not None:
        return
    resolution = getattr(context, "role_resolution", None)
    if resolution is None:
        return
    known = known_paths(resolution.walked)
    directories = frozenset(
        "/".join(parts[:end])
        for parts in (path.split("/") for path in resolution.walked)
        for end in range(1, len(parts))
    )
    context.documents = tuple(
        _scan_role(context, resolution, name, known, directories) for name in roles
    )


def _scan_role(context, resolution, name: str, known, directories) -> DocumentEvidence:
    paths = resolution.files.get(name, ())
    for path in paths:
        if resolution.origins.get((name, path)) != ORIGIN_RULES:
            if context.read_source(path) is not None:
                return DocumentEvidence(name, KIND_DECLARED, path)

    named = [p for p in paths if resolution.origins.get((name, p)) == ORIGIN_RULES]
    excluded = _EXCLUDED.get(name, lambda _path: False)
    rest = sorted(
        (
            p
            for p in resolution.walked
            if p.lower().endswith(DOCUMENT_SUFFIXES) and p not in named
        ),
        key=lambda p: (
            not PurePosixPath(p).name.lower().startswith("readme"),
            p.count("/"),
            p,
        ),
    )
    candidates = [p for p in (*named, *rest) if not excluded(p)]

    scanned = 0
    patterns = None
    qualified: list = []
    for path in candidates[:MAX_SCANNED_DOCUMENTS]:
        text = context.peek_source(path)
        if text is None:
            continue
        text = text[:MAX_DOCUMENT_CHARS]
        scanned += 1
        if name == REQUIREMENTS_DOC and patterns is None:
            patterns = convention_values(
                context_conventions(context), "requirement_item_patterns"
            )
        kind, cited, size = _shape(name, path, text, known, patterns, directories)
        if kind is None:
            continue
        if name == DECISION_RECORD:
            # T089 AC 14: every decision record found by content is evidence
            # (solution-fit reads this role), so the scan goes on; the first
            # one in scan priority fills the rule
            qualified.append((0, len(qualified), kind, path, cited))
            continue
        if name != ARCHITECTURE_DOC:
            if context.read_source(path) is not None:
                return _filled(name, kind, path, cited, scanned)
            continue
        # T089 AC 10 (decision B): the document describing the most distinct
        # directories wins, then the most entries, then scan priority
        qualified.append(((-size[0], -size[1]), len(qualified), kind, path, cited))

    if name == DECISION_RECORD and qualified:
        listed = context.role_files.get(name, ())
        found = [path for *_rest, path, _cited in qualified if path not in listed]
        context.role_files[name] = (*listed, *found)[: max(len(listed), MAX_ROLE_FILES)]
    for _size, _order, kind, path, cited in sorted(qualified):
        if context.read_source(path) is not None:
            if name == ARCHITECTURE_DOC:
                # the description that fills the rule is quoted as evidence,
                # as a named role file was (T089 AC 13)
                listed = context.role_files.get(name, ())
                if path not in listed:
                    context.role_files[name] = (path, *listed)
            return _filled(name, kind, path, cited, scanned)

    bounded = None
    if len(candidates) > MAX_SCANNED_DOCUMENTS:
        bounded = (
            f"only the first {MAX_SCANNED_DOCUMENTS} of {len(candidates)} "
            "candidate documents were read; the rest may have the shape"
        )
    elif resolution.walk_truncated:
        bounded = (
            f"the repository walk stopped at {MAX_ROLE_WALK_FILES} files; "
            "documents beyond it were never examined"
        )
    return DocumentEvidence(name, None, None, (), scanned, bounded)


def _size(entries, directories) -> tuple[int, int]:
    """(distinct directories, entries): an entry naming a directory counts
    that directory; one naming a file counts its parent, once."""
    named = {
        path if path in directories else path.rpartition("/")[0]
        for _n, path, _line in entries
    }
    return len(named), len(entries)


def _filled(name, kind, path, cited, scanned) -> DocumentEvidence:
    lines = tuple(dict.fromkeys(f"line {n}: {line}" for n, line in cited))
    return DocumentEvidence(name, kind, path, lines[:MAX_CITED_LINES], scanned)


def _shape(name, path, text, known, patterns, directories=frozenset()):
    """``(kind or None, cited (line, text), size)``; ``size`` ranks
    architecture documents: (distinct directories described, entries)."""
    if name == ARCHITECTURE_DOC:
        parent = PurePosixPath(path).parent.as_posix()
        base = "" if parent == "." else parent
        readme = PurePosixPath(path).name.lower().startswith("readme")
        entries = described_entries(text, known, base)
        if len(entries) >= MIN_DESCRIBED_ENTRIES:
            if readme:
                section = _architecture_section(text)
                if section is not None:
                    start, body = section
                    inside = described_entries(body, known, base)
                    if len(inside) >= MIN_DESCRIBED_ENTRIES:
                        cited = [(start + n, line) for n, _p, line in inside]
                        return KIND_README_HEADING, cited, _size(entries, directories)
            cited = [(n, line) for n, _p, line in entries]
            return KIND_CONTENT, cited, _size(entries, directories)
        # T096: an architecture section in prose names its paths inline
        section = _architecture_section(text, 2)
        if section is not None:
            start, body = section
            named = prose_paths(body, known, base)
            if len(named) >= MIN_DESCRIBED_ENTRIES:
                cited = [(start + n, line) for n, _p, line in named]
                kind = KIND_README_HEADING if readme else KIND_ARCHITECTURE_HEADING
                return kind, cited, _size(named, directories)
        return None, [], 0
    if name == DECISION_RECORD:
        found = decision_lines(text)
        return (KIND_CONTENT, found, 1) if found else (None, [], 0)
    items = find_requirement_items(text, patterns)
    if items:
        lines = text.splitlines()
        cited = [(i.line, lines[i.line - 1].strip()[:MAX_LINE_CHARS]) for i in items]
        return KIND_CONTENT, cited, 1
    found = requirement_list_lines(text)
    return (KIND_CONTENT, found, 1) if found else (None, [], 0)
