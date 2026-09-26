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
from .context import _is_secret_bearing, _resolved_repo, _walk
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


def detect_pick_gates(
    repo_path: str | Path,
    config: dict[str, tuple[str, ...]] | None = None,
) -> dict[str, list[dict]] | None:
    """Candidates for the roles the rules left unfilled, grouped by shape.

    Returns ``{"groups": [{"roles": [...], "candidates": [...], "omitted": N},
    ...]}``, or ``None`` when every role is filled or no unfilled role has an
    eligible candidate: the caller then omits ``needs_input`` entirely and
    spends zero extra tokens (FR-035). Grouping by shape (T027 Stage 4 P2)
    means one candidate is listed once per group, not once per unfilled role
    that shares its shape — repeating the same 20 files under every one of
    several unfilled roles cost 4x the payload on a real repository for no
    extra information, since the agent must decide the role-to-file mapping
    itself either way. Never call this for a round that already carries
    ``agent_input.picks`` — that decision belongs to the caller (one round).
    """
    root = _resolved_repo(repo_path)
    roles = tuple(role(name) for name in sorted(GENERIC_PATTERNS))
    resolution = resolve(root, roles, config=config or {})

    assigned = {path for paths in resolution.files.values() for path in paths}
    # `contained_only=True`: a file symlink that escapes the repository is
    # never a candidate. Without it, `_walk(..., contained_only=False)` (used
    # by `roles.resolve` so a role-matched escaping symlink can be reported by
    # name) would let an attacker-planted symlink inside the target repo read
    # an arbitrary host file's first heading straight into the MCP response.
    walked = sorted(
        path
        for path in _walk(root, root, extensions=None, contained_only=True)
        if path not in assigned and _eligible(root, path)
    )

    groups: list[dict] = []
    buckets = ((_DOC_EXTENSIONS, _DOC_ROLES), (_CONFIG_EXTENSIONS, _CONFIG_ROLES))
    for extensions, bucket in buckets:
        unfilled = sorted(
            name for name in bucket if not resolution.files.get(name)
        )
        if not unfilled:
            continue
        pool = [path for path in walked if Path(path).suffix.lower() in extensions]
        if not pool:
            continue
        kept = pool[:MAX_CANDIDATES_PER_ROLE]
        groups.append(
            {
                "roles": unfilled,
                "candidates": [
                    {"path": path, "heading": _heading(root, path)} for path in kept
                ],
                "omitted": max(0, len(pool) - MAX_CANDIDATES_PER_ROLE),
            }
        )
    return {"groups": groups} if groups else None


def _eligible(root: Path, relative_path: str) -> bool:
    """True if ``relative_path`` may ever be surfaced as a candidate.

    Mirrors ``RepoContext.read_source``/``roles._pick_problem``: resolved
    containment (catches a file symlink escaping the repository even under
    ``contained_only=True``'s own resolve, belt-and-suspenders) and
    DDR-0002 secret exclusion checked on **both** the given name and the
    resolved target's name — a safe-looking path that is a symlink to
    ``.env`` must be excluded even though ``.env`` itself is not this path.
    """
    candidate = root / relative_path
    try:
        resolved = candidate.resolve()
    except OSError:
        return False
    if not resolved.is_relative_to(root) or not resolved.is_file():
        return False
    if _is_secret_bearing(relative_path) or _is_secret_bearing(
        resolved.relative_to(root).as_posix()
    ):
        return False
    return True


def _heading(root: Path, relative_path: str) -> str:
    """First markdown heading, else first non-empty line, redacted (NFR-010).

    Bounded to the first few KB so a huge or binary file never gets fully
    read just to produce a one-line hint (Edge Case Checklist). Re-checks
    eligibility, matching the walk-time check: a same-shaped file that
    turned out to be a symlink (escaping, or aliasing a secret-bearing name)
    must never be read, even if it slipped past the caller's own filter.
    """
    if not _eligible(root, relative_path):
        return ""
    resolved = (root / relative_path).resolve()
    try:
        with resolved.open("rb") as handle:
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
