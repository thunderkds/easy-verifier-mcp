"""The bespoke security evidence dimension (FR-010).

It selects repository code and configuration directly; it never uses the
document-section extractor and never assigns a verdict.
"""

from __future__ import annotations

from collections.abc import Iterator
from fnmatch import fnmatchcase
from pathlib import PurePosixPath

from ..core.context import SECRET_BEARING_PATTERNS, whole_file_excerpt
from ..core.models import DimensionContext, DimensionDescriptor, Excerpt, SourceMiss
from ..core.redact import scan

NAME = "security"

PURPOSE = (
    "Gather citable evidence about credential material, dependencies, "
    "authentication and cryptography code, and permission, container, and CI "
    "configuration without judging whether any evidence is a vulnerability."
)

SOURCES_SOUGHT: tuple[str, ...] = (
    "requirements.txt",
    "pyproject.toml",
    "package.json",
    "package-lock.json",
    "poetry.lock",
    "src/auth.py",
    "Dockerfile",
    "compose.yaml",
    ".github/workflows/ci.yml",
    ".env",
    "git history (out of scope for v1)",
)

MAX_SECURITY_SOURCES = 200

#: Declared entries that name a body of evidence rather than a repository path.
#: Probing them as paths would report a truthful-looking "not found" for
#: something that was never a file, so each states its own reason instead.
PSEUDO_SOURCES: dict[str, str] = {
    "git history (out of scope for v1)": (
        "out of scope for v1: git history is not searched by this dimension"
    ),
}

#: Emitted when a narrow scope never resolved. Stated rather than silently
#: widened: ``resolve_scope`` raises when ``task``/``changes`` is asked for
#: without its required selector, and ``run_dimension`` turns that into
#: ``resolved_scope = None``. Reading that as "whole repository" would return
#: project-scope evidence under a narrow scope's label.
UNRESOLVED_SCOPE_WARNING = (
    "The {scope} scope could not be resolved, most likely because its required "
    "selector was not supplied. No evidence was gathered; this pack is not "
    "whole-repository output."
)

UNRESOLVED_SCOPE_REASON = (
    "not examined: the {scope} scope could not be resolved "
    "(its required selector was not supplied)"
)

#: Category names in descending evidence relevance. The candidate cap is spent
#: in this order, not in path order — an alphabetical cap drops a manifest or a
#: Dockerfile on any repository larger than the cap.
_CATEGORY_RANK: tuple[str, ...] = (
    "credential material",
    "dependency manifest",
    "permission, container, or CI configuration",
    "auth or crypto code",
)
_GENERIC_RANK = len(_CATEGORY_RANK)

_DEPENDENCY_NAMES = frozenset(
    {
        "cargo.lock",
        "cargo.toml",
        "composer.json",
        "composer.lock",
        "gemfile",
        "gemfile.lock",
        "go.mod",
        "go.sum",
        "package-lock.json",
        "package.json",
        "pipfile",
        "pipfile.lock",
        "pnpm-lock.yaml",
        "poetry.lock",
        "pom.xml",
        "pyproject.toml",
        "yarn.lock",
    }
)
_CONFIG_NAMES = frozenset(
    {
        "codeowners",
        "compose.yaml",
        "compose.yml",
        "docker-compose.yaml",
        "docker-compose.yml",
        "dockerfile",
        "jenkinsfile",
    }
)
_AUTH_MARKERS = (
    "auth",
    "crypto",
    "cipher",
    "encrypt",
    "decrypt",
    "jwt",
    "oauth",
    "permission",
    "policy",
    "rbac",
    "security",
)
_TEST_SEGMENTS = frozenset({"test", "tests", "fixtures", "testdata", "__tests__"})
_TEXT_SUFFIXES = frozenset(
    {
        ".c",
        ".conf",
        ".cpp",
        ".cs",
        ".go",
        ".h",
        ".ini",
        ".java",
        ".js",
        ".json",
        ".jsx",
        ".kt",
        ".md",
        ".php",
        ".properties",
        ".py",
        ".rb",
        ".rs",
        ".sh",
        ".sql",
        ".toml",
        ".ts",
        ".tsx",
        ".txt",
        ".xml",
        ".yaml",
        ".yml",
    }
)


def collect(context: DimensionContext) -> Iterator[Excerpt]:
    """Yield bounded security evidence from the resolved scope, lazily."""
    resolved_scope = context.resolved_scope
    scope_files = frozenset(getattr(resolved_scope, "files", ()) or ())
    scope_kind = getattr(resolved_scope, "kind", None)

    # A *narrow* scope that never resolved is a failure, not an invitation to
    # read the whole repository. `run_dimension` collapses `ScopeError` into
    # `resolved_scope = None`, so "unresolved" and "project" arrive here looking
    # identical; the requested scope name is what tells them apart. Reporting
    # this rather than widening is the same requirement as the miss list:
    # the pack must not assert more than was actually checked.
    if resolved_scope is None and context.scope != "project":
        _warn(context, UNRESOLVED_SCOPE_WARNING.format(scope=context.scope))
        reason = UNRESOLVED_SCOPE_REASON.format(scope=context.scope)
        for source in SOURCES_SOUGHT:
            context.sources_missing.append(SourceMiss(source=source, reason=reason))
        return

    # `project` (and its no-resolution fallback) covers the whole repository, so
    # every declared source is in bounds. A narrow scope is not allowed to reach
    # outside its own file set just because a name is declared.
    whole_repo = resolved_scope is None or scope_kind == "project"

    probed: set[str] = set()

    # Declared sources are probed explicitly, before anything else. Without this
    # the miss list is guesswork: an absent `package.json` is indistinguishable
    # from one the budget never reached, and coverage counts only the declared
    # names that happen to collide with a scope entry.
    for source in SOURCES_SOUGHT:
        pseudo_reason = PSEUDO_SOURCES.get(source)
        if pseudo_reason is not None:
            context.sources_missing.append(
                SourceMiss(source=source, reason=pseudo_reason)
            )
            continue

        if not whole_repo and source not in scope_files:
            context.sources_missing.append(
                SourceMiss(
                    source=source,
                    reason=f"not in the resolved {scope_kind} scope",
                )
            )
            continue

        probed.add(source)
        text = context.request_secret_source(source)
        if text is None:
            continue
        excerpt = whole_file_excerpt(source, text)
        if excerpt is not None:
            yield excerpt

    if resolved_scope is None:
        return

    reads = 0
    for rank, source in _ranked_candidates(scope_files):
        if reads >= MAX_SECURITY_SOURCES:
            return
        if source in probed:
            continue

        category = None if rank == _GENERIC_RANK else _CATEGORY_RANK[rank]
        reads += 1
        text = context.request_secret_source(source)
        if text is None:
            continue

        # Reuse T004's detectors to decide whether an otherwise ordinary text
        # file carries credential evidence. The pipeline scans again at the
        # evidence boundary and owns the actual replacement + hit metadata.
        if category is None and not scan(text).hits:
            continue

        excerpt = whole_file_excerpt(source, text)
        if excerpt is not None:
            yield excerpt


def _warn(context: DimensionContext, message: str) -> None:
    """Append a pack warning once, however many budget passes call ``collect``.

    ``run_dimension`` copies ``context.warnings`` onto the pack after the budget
    drain, so appending here reaches the caller without any pipeline change.
    """
    if message not in context.warnings:
        context.warnings = (*context.warnings, message)


def _ranked_candidates(files) -> list[tuple[int, str]]:
    """Scope files ordered by category relevance, ties broken by path.

    Ordering happens before the cap so the bounded read budget goes to
    credential material, manifests and configuration first, and only then to
    generic scannable text.
    """
    ranked: list[tuple[int, str]] = []
    for source in files:
        category = _category(source)
        if category is None:
            if not _is_scannable(source):
                continue
            rank = _GENERIC_RANK
        else:
            rank = _CATEGORY_RANK.index(category)
        ranked.append((rank, source))
    ranked.sort()
    return ranked


def _category(source: str) -> str | None:
    lower = source.lower()
    name = PurePosixPath(lower).name

    if any(fnmatchcase(name, pattern) for pattern in SECRET_BEARING_PATTERNS):
        return "credential material"
    if name in _DEPENDENCY_NAMES or fnmatchcase(name, "requirements*.txt"):
        return "dependency manifest"
    if _has_auth_marker(lower):
        return "auth or crypto code"
    if (
        name in _CONFIG_NAMES
        or lower.startswith(".github/workflows/")
        or lower == ".gitlab-ci.yml"
        or lower.startswith(".circleci/")
        or "kubernetes" in lower
        or "/k8s/" in f"/{lower}/"
    ):
        return "permission, container, or CI configuration"
    return None


def _has_auth_marker(lower_path: str) -> bool:
    """True when a *non-test* path segment carries an auth or crypto marker.

    Matching the whole path meant a repository's own test tree scored as auth
    code and was emitted as whole-file excerpts. Test paths still reach the
    generic tier and are surfaced when a detector actually hits.
    """
    segments = PurePosixPath(lower_path).parts
    if any(segment in _TEST_SEGMENTS for segment in segments):
        return False
    return any(marker in segment for segment in segments for marker in _AUTH_MARKERS)


def _is_scannable(source: str) -> bool:
    name = PurePosixPath(source).name.lower()
    return name in _CONFIG_NAMES or PurePosixPath(name).suffix in _TEXT_SUFFIXES


DESCRIPTOR = DimensionDescriptor(
    name=NAME,
    purpose=PURPOSE,
    sources_sought=SOURCES_SOUGHT,
    collect=collect,
)
