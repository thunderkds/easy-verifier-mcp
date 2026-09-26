"""MCP-only detect gate: candidate files for unfilled source roles (T027).

Pure functions, no state. ``detect_pick_gates`` decides, from one repository
walk, which declared source roles the rules left unfilled *and* which
unmatched files could plausibly fill them (FR-035). The core computes this;
whether it reaches the wire is an adapter decision (``mcp_server.py`` includes
it, the CLI never does — FR-021, FR-034, FR-040).

A candidate is only ever ``{path, heading}``: a repository-relative path and a
short, redacted first heading or line. Nothing here calls a model (NFR-001).
"""

from __future__ import annotations

from pathlib import Path

from ..dimensions import _doc_extract
from .context import _is_secret_bearing, _walk
from .redact import redact
from .roles import GENERIC_PATTERNS, resolve, role

MAX_CANDIDATES_PER_ROLE = 20
"""FR-035, NFR-009: bounded payload; overflow is disclosed, never silent."""

_MAX_HEADING_READ_BYTES = 4096
"""Heading extraction never reads more than this from any one candidate."""

_MAX_HEADING_LENGTH = 200

_DOC_EXTENSIONS = frozenset({".md", ".rst", ".adoc"})
_CONFIG_EXTENSIONS = frozenset(
    {".yaml", ".yml", ".toml", ".json", ".ini", ".cfg", ".xml"}
)

_DOC_ROLES = frozenset(
    {
        "readme",
        "architecture-doc",
        "decision-record",
        "requirements-doc",
        "spec-doc",
        "task-breakdown",
        "contributing-guide",
    }
)
"""Roles a document could plausibly fill, whatever its name (matches AC1)."""

_CONFIG_ROLES = frozenset(
    {
        "lint-config",
        "format-config",
        "package-manifest",
        "lockfile",
        "container-config",
        "ci-workflow",
        "test-config",
    }
)
"""Roles a config-shaped file could plausibly fill.

``credential-file`` (secret-bearing by definition), ``auth-code`` and
``test-file`` (source code, not a distinct file shape) are deliberately
excluded: a generic-shape guess there would be a low-confidence coin flip,
not a candidate worth a round trip."""


def _role_shapes() -> dict[str, frozenset[str]]:
    shapes: dict[str, frozenset[str]] = dict.fromkeys(_DOC_ROLES, _DOC_EXTENSIONS)
    shapes.update(dict.fromkeys(_CONFIG_ROLES, _CONFIG_EXTENSIONS))
    return shapes


def detect_pick_gates(
    repo_path: str | Path,
    config: dict[str, tuple[str, ...]] | None = None,
) -> dict[str, dict] | None:
    """Candidates for every role the rules left unfilled, or ``None``.

    ``None`` means every role is filled, or no unfilled role has an eligible
    candidate: the caller then omits ``needs_input`` entirely and spends zero
    extra tokens (FR-035). Never call this for a round that already carries
    ``agent_input.picks`` — that decision belongs to the caller (one round).
    """
    root = Path(repo_path)
    roles = tuple(role(name) for name in sorted(GENERIC_PATTERNS))
    resolution = resolve(root, roles, config=config or {})

    assigned = {path for paths in resolution.files.values() for path in paths}
    walked = sorted(
        path
        for path in _walk(root, root, extensions=None, contained_only=False)
        if path not in assigned and not _is_secret_bearing(path)
    )

    gates: dict[str, dict] = {}
    for name, extensions in _role_shapes().items():
        if resolution.files.get(name):
            continue  # already filled: AC5, never a gate
        pool = [path for path in walked if Path(path).suffix.lower() in extensions]
        if not pool:
            continue
        kept = pool[:MAX_CANDIDATES_PER_ROLE]
        gates[name] = {
            "candidates": [
                {"path": path, "heading": _heading(root, path)} for path in kept
            ],
            "omitted": max(0, len(pool) - MAX_CANDIDATES_PER_ROLE),
        }
    return gates or None


def _heading(root: Path, relative_path: str) -> str:
    """First markdown heading, else first non-empty line, redacted (NFR-010).

    Bounded to the first few KB so a huge or binary file never gets fully
    read just to produce a one-line hint (Edge Case Checklist).
    """
    try:
        with (root / relative_path).open("rb") as handle:
            raw = handle.read(_MAX_HEADING_READ_BYTES)
    except OSError:
        return ""
    if b"\x00" in raw:
        return ""  # binary: never surfaced as a candidate line

    lines = raw.decode("utf-8", errors="replace").splitlines()
    heading = ""
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        atx = _doc_extract._ATX_HEADING.match(stripped)
        if atx:
            heading = atx.group(2)
        elif index + 1 < len(lines) and _doc_extract._SETEXT_UNDERLINE.match(
            lines[index + 1].strip()
        ):
            heading = stripped
        else:
            heading = stripped
        break
    return redact(heading[:_MAX_HEADING_LENGTH])


__all__ = ["MAX_CANDIDATES_PER_ROLE", "detect_pick_gates"]
