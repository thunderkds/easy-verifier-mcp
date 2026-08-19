"""The bespoke security evidence dimension (FR-010).

It selects repository code and configuration directly; it never uses the
document-section extractor and never assigns a verdict.
"""

from __future__ import annotations

from collections.abc import Iterator
from fnmatch import fnmatchcase
from pathlib import PurePosixPath

from ..core.context import SECRET_BEARING_PATTERNS, whole_file_excerpt
from ..core.models import DimensionContext, DimensionDescriptor, Excerpt
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
    if resolved_scope is None:
        candidates = SOURCES_SOUGHT if context.scope == "project" else ()
    else:
        candidates = tuple(sorted(getattr(resolved_scope, "files", ())))

    for index, source in enumerate(candidates):
        if index >= MAX_SECURITY_SOURCES:
            return

        category = _category(source)
        if category is None and not _is_scannable(source):
            continue

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


def _category(source: str) -> str | None:
    lower = source.lower()
    name = PurePosixPath(lower).name

    if any(fnmatchcase(name, pattern) for pattern in SECRET_BEARING_PATTERNS):
        return "credential material"
    if name in _DEPENDENCY_NAMES or fnmatchcase(name, "requirements*.txt"):
        return "dependency manifest"
    if any(marker in lower for marker in _AUTH_MARKERS):
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


def _is_scannable(source: str) -> bool:
    name = PurePosixPath(source).name.lower()
    return name in _CONFIG_NAMES or PurePosixPath(name).suffix in _TEXT_SUFFIXES


DESCRIPTOR = DimensionDescriptor(
    name=NAME,
    purpose=PURPOSE,
    sources_sought=SOURCES_SOUGHT,
    collect=collect,
)
