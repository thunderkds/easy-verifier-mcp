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
from .metrics import ARCHITECTURE_HEADING
from .models import DocumentEvidence
from .roles import MAX_ROLE_WALK_FILES, ORIGIN_RULES, _is_template
from .structure import context_conventions, convention_values, find_requirement_items

MIN_DESCRIBED_ENTRIES = 3
"""An architecture description names at least this many real repository
paths, each followed by at least :data:`MIN_DESCRIPTION_WORDS` words of
description (user sign-off 2026-10-12, G5). Two entries read as an aside
("see ``src/`` and ``tests/``"); three is the smallest map of a structure."""

MIN_DESCRIPTION_WORDS = 2

MIN_DECISION_FIELDS = 2
"""Distinct decision-record fields (Context, Decision, Consequences, Status,
Alternatives) a document must head or label: Nygard's ADR
(https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
and MADR (https://adr.github.io/madr/) both carry at least two."""

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

ARCHITECTURE_DOC = "architecture-doc"
DECISION_RECORD = "decision-record"
REQUIREMENTS_DOC = "requirements-doc"

SHAPES = {
    ARCHITECTURE_DOC: (
        f"describes at least {MIN_DESCRIBED_ENTRIES} real repository paths "
        f"(a list item, table row or tree line naming a path that exists, "
        f"followed by at least {MIN_DESCRIPTION_WORDS} words)"
    ),
    DECISION_RECORD: (
        f"has a decision structure (at least {MIN_DECISION_FIELDS} of the "
        "headings or fields Context, Decision, Consequences, Status, "
        "Alternatives; or a dated entry with a decision verb and a rationale)"
    ),
    REQUIREMENTS_DOC: (
        "has a requirement item under the declared requirement_item_patterns"
    ),
}

_CHANGELOG = re.compile(r"^(changelog|changes|history|news|release[-_ ]?notes)", re.I)


def _is_changelog(path: str) -> bool:
    """A changelog lists files with a few words each (``- src/a.ts: fix
    typo``), which is the architecture shape; it is a history, not a map."""
    return bool(_CHANGELOG.match(PurePosixPath(path).name))


_EXCLUDED = {ARCHITECTURE_DOC: _is_changelog, REQUIREMENTS_DOC: _is_template}


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
    for number, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith(("```", "~~~")):
            fenced = not fenced
            parents.clear()
            continue
        if len(line) > MAX_LINE_CHARS or not line.strip():
            continue
        if line.lstrip().startswith("|") and line.rstrip().endswith("|"):
            path, described = _table_entry(line, known, base)
        else:
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


def _architecture_section(text: str) -> tuple[int, str] | None:
    """``(first line, text)`` of a section headed "Architecture"."""
    match = ARCHITECTURE_HEADING.search(text)
    if match is None:
        return None
    start = text.count("\n", 0, text.index("#", match.start()))
    lines = text.splitlines()
    level = len(lines[start].lstrip()) - len(lines[start].lstrip().lstrip("#"))
    end = next(
        (
            index
            for index in range(start + 1, len(lines))
            if re.match(rf"^\s{{0,3}}#{{1,{level}}}\s", lines[index])
        ),
        len(lines),
    )
    return start, "\n".join(lines[start:end])


# ---------------------------------------------------------------------------
# decision-record: decision structure
# ---------------------------------------------------------------------------

_DECISION_KEYS = r"(context|decisions?|consequences|status|alternatives)\b"
_DECISION_HEADING = re.compile(
    r"^\s{0,3}#{1,6}\s*(?:\d+[.)]?\s*)?" + _DECISION_KEYS, re.I
)
_DECISION_FIELD = re.compile(
    r"^\s{0,3}(?:[-*+]\s+)?(?:\*\*|__)?" + _DECISION_KEYS + r"(?:\*\*|__)?\s*:", re.I
)
_DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_DECISION_VERB = re.compile(r"\b(decided|chose|chosen|we will)\b", re.I)
_RATIONALE = re.compile(r"\b(because|instead of|trade-?offs?)\b", re.I)
MAX_DATED_ENTRY_LINES = 10


def decision_lines(text: str) -> list[tuple[int, str]]:
    """``(line, text)`` showing a decision structure, or ``[]``."""
    lines = text.splitlines()
    fields: dict[str, tuple[int, str]] = {}
    for number, line in enumerate(lines, 1):
        if len(line) > MAX_LINE_CHARS:
            continue
        match = _DECISION_HEADING.match(line) or _DECISION_FIELD.match(line)
        if match is not None:
            key = match[1].lower()
            key = "decision" if key == "decisions" else key
            fields.setdefault(key, (number, line.strip()))
    if len(fields) >= MIN_DECISION_FIELDS:
        return sorted(fields.values())
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
    context.documents = tuple(
        _scan_role(context, resolution, name, known) for name in roles
    )


def _scan_role(context, resolution, name: str, known) -> DocumentEvidence:
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
        kind, cited = _shape(name, path, text, known, patterns)
        if kind is not None and context.read_source(path) is not None:
            return DocumentEvidence(
                name,
                kind,
                path,
                tuple(dict.fromkeys(f"line {n}: {line}" for n, line in cited))[
                    :MAX_CITED_LINES
                ],
                scanned,
            )

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


def _shape(name, path, text, known, patterns) -> tuple[str | None, list]:
    if name == ARCHITECTURE_DOC:
        parent = PurePosixPath(path).parent.as_posix()
        base = "" if parent == "." else parent
        if PurePosixPath(path).name.lower().startswith("readme"):
            section = _architecture_section(text)
            if section is not None:
                start, body = section
                entries = described_entries(body, known, base)
                if len(entries) >= MIN_DESCRIBED_ENTRIES:
                    return KIND_README_HEADING, [
                        (start + n, line) for n, _p, line in entries
                    ]
        entries = described_entries(text, known, base)
        if len(entries) >= MIN_DESCRIBED_ENTRIES:
            return KIND_CONTENT, [(n, line) for n, _p, line in entries]
        return None, []
    if name == DECISION_RECORD:
        found = decision_lines(text)
        return (KIND_CONTENT, found) if found else (None, [])
    items = find_requirement_items(text, patterns)
    lines = text.splitlines()
    if not items:
        return None, []
    return KIND_CONTENT, [
        (item.line, lines[item.line - 1].strip()[:MAX_LINE_CHARS]) for item in items
    ]
