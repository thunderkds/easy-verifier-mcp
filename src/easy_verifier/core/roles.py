"""Source roles: what fills them, and from where (T026, DDR-0006).

A dimension seeks **roles** (a lockfile, a requirements doc, a CI workflow), not
filenames. This module is the whole mechanism, as plain data plus three
functions — no base class, no registry, no detection classes:

* :data:`GENERIC_PATTERNS` — the language-agnostic globs for every file-backed
  role. Its keys are the complete set of roles a config file or an agent pick
  may name.
* :data:`ECOSYSTEM_PATTERNS` — extra globs for existing roles (Python, JS/TS,
  Rust, Java), switched on when one of the table's manifests is present. A
  table may only *extend* a role; that it cannot add one is checked at import.
* :func:`load_repo_config` / :func:`validate_agent_input` — the two caller
  inputs, both add-only, both validated with every error reported at once.
* :func:`resolve` — one bounded, sorted walk that turns roles into files and
  remembers where each file came from (``rules`` / ``config`` / ``pick``).

Nothing here reads a file's *contents* except the target's own
``.easy-verifier.toml``: roles resolve to paths, and every read still happens
through ``RepoContext.read_source`` with its containment and DDR-0002 checks.
"""

from __future__ import annotations

import json
import re
import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from fnmatch import fnmatchcase
from functools import lru_cache
from pathlib import Path, PurePosixPath

from .context import _EXCLUDED_DIRS, _is_secret_bearing, _resolved_repo, _walk
from .findings import ValidationError
from .models import SourceRole
from .redact import redact

CONFIG_FILENAME = ".easy-verifier.toml"
MAX_CONFIG_BYTES = 64 * 1024

MAX_CONFIG_GLOBSTARS = 2
MAX_CONFIG_STARS = 4
"""Bounds on one ``.easy-verifier.toml`` glob. The file comes from the
repository under evaluation, which is untrusted input (NFR-013)."""

MAX_ROLE_FILES = 50
"""Files kept per role (from rules and config), in sorted path order. Hitting
it is reported as a pack warning, never a silent stop (NFR-009)."""

MAX_ROLE_WALK_FILES = 20_000
"""Files examined by one resolution walk. Hitting it is reported as a warning
and in the miss reason of every role left unfilled."""

ORIGIN_RULES = "rules"
ORIGIN_CONFIG = "config"
ORIGIN_PICK = "pick"

_DOC_SUFFIXES = (".md", ".rst", ".adoc")


def _docs(*keywords: str) -> tuple[str, ...]:
    """Document globs for a name keyword, anywhere, in the three usual cases.

    Matching is case-sensitive on purpose (``*Test.*`` must not match
    ``latest.json``), so the case variants are spelled out here instead.
    """
    return tuple(
        f"**/*{variant}*{suffix}"
        for keyword in keywords
        for variant in (keyword, keyword.capitalize(), keyword.upper())
        for suffix in _DOC_SUFFIXES
    )


def _source_roots(*keywords: str) -> tuple[str, ...]:
    return tuple(
        f"**/{root}/**/*{keyword}*"
        for keyword in keywords
        for root in ("src", "lib", "app", "pkg", "internal")
    )


GENERIC_PATTERNS: dict[str, tuple[str, ...]] = {
    "readme": ("README*", "Readme*", "readme*"),
    "architecture-doc": ("PROJECT_SPEC.md", *_docs("architecture", "design")),
    "decision-record": (
        # Exact name, deliberately not `BRAINSTORMING_LOG*.md`: redact.py's
        # high_entropy_string detector fingerprints names such as
        # `BRAINSTORMING_LOG_source-discovery.md`, which breaks the citation.
        # Temporary narrowing; widen once the separate redaction bugfix lands.
        "BRAINSTORMING_LOG.md",
        "**/adr/**",
        "**/adrs/**",
        "**/ADR/**",
        "**/ddr/**",
        "**/decisions/**",
        *_docs("decision"),
    ),
    "requirements-doc": ("PRD*.md", "**/PRD*.md", *_docs("requirement")),
    "spec-doc": (
        "PROJECT_SPEC.md",
        "**/specs/**/*.md",
        "**/specification/**/*.md",
        *_docs("spec"),
    ),
    "task-breakdown": (
        "tasks/TASK_GUIDE_*.md",
        "**/tasks/**/*.md",
        *_docs("task", "roadmap", "backlog", "acceptance"),
    ),
    "contributing-guide": (
        "**/CONTRIBUTING*",
        "**/contributing*.md",
        *_docs("style", "convention"),
    ),
    "lint-config": (
        ".pre-commit-config.yaml",
        ".pre-commit-config.yml",
        "**/.*lint*",
        "**/*lint*.toml",
        "**/*lint*.json",
        "**/*lint*.yaml",
        "**/*lint*.yml",
        "**/*lint*.xml",
        "**/*lint.config.*",
    ),
    "format-config": (
        "**/.editorconfig",
        "**/.*format*",
        "**/.*fmt*",
        "**/*format*.toml",
        "**/*fmt*.toml",
    ),
    "package-manifest": (
        "**/mix.exs",
        "**/go.mod",
        "**/Gemfile",
        "**/*.gemspec",
        "**/composer.json",
        "**/*.csproj",
        "**/*.fsproj",
        "**/pubspec.yaml",
        "**/Package.swift",
        "**/build.sbt",
        "**/*.cabal",
        "**/deno.json",
        "**/deps.edn",
        "**/project.clj",
        "**/rebar.config",
        "**/CMakeLists.txt",
        "**/meson.build",
        "**/dune-project",
    ),
    "lockfile": (
        "**/*.lock",
        "**/*-lock.*",
        "**/*.sum",
        "**/*.lockb",
        "**/*.lockfile",
    ),
    "auth-code": (*_source_roots("auth", "crypt", "permission"), "**/auth/**"),
    "container-config": (
        "**/Dockerfile",
        "**/Dockerfile.*",
        "**/*.Dockerfile",
        "**/*.dockerfile",
        "**/Containerfile*",
        "**/compose.yaml",
        "**/compose.yml",
        "**/docker-compose*.yaml",
        "**/docker-compose*.yml",
        "**/k8s/**",
        "**/kubernetes/**",
    ),
    "ci-workflow": (
        ".github/workflows/*.yml",
        ".github/workflows/*.yaml",
        ".gitlab-ci.yml",
        ".circleci/**",
        ".buildkite/**",
        ".woodpecker/**",
        ".woodpecker.yml",
        ".drone.yml",
        ".travis.yml",
        "Jenkinsfile",
        "azure-pipelines.yml",
        "bitbucket-pipelines.yml",
    ),
    "credential-file": ("**/.env*",),
    "test-config": (
        "**/test_helper.*",
        "**/spec_helper.*",
        "**/*test*.config.*",
        "**/*test*.ini",
        "**/*test*.toml",
        "**/*test*.cfg",
    ),
    "test-file": (
        "**/test/**",
        "**/tests/**",
        "**/spec/**",
        "**/__tests__/**",
        "**/*_test.*",
        "**/*.test.*",
        "**/*.spec.*",
        "**/*Test.*",
        "**/*Tests.*",
        "**/test_*",
    ),
}
"""Language-agnostic patterns for every file-backed role (FR-032).

Directory and naming conventions shared across ecosystems. A repository in a
language with no ecosystem table is evaluated by these alone."""

ECOSYSTEM_PATTERNS: dict[str, dict] = {
    "python": {
        "manifests": (
            "pyproject.toml",
            "setup.py",
            "setup.cfg",
            "requirements.txt",
            "Pipfile",
        ),
        "roles": {
            "package-manifest": (
                "**/pyproject.toml",
                "**/setup.py",
                "**/setup.cfg",
                "**/requirements*.txt",
                "**/Pipfile",
            ),
            "lint-config": (
                "**/ruff.toml",
                "**/.ruff.toml",
                "**/.flake8",
                "**/pylintrc",
                "**/mypy.ini",
                "**/pyproject.toml",
                "**/setup.cfg",
            ),
            "test-config": (
                "**/pytest.ini",
                "**/tox.ini",
                "**/conftest.py",
                "**/noxfile.py",
                "**/pyproject.toml",
                "**/setup.cfg",
            ),
        },
    },
    "js-ts": {
        "manifests": ("package.json",),
        "roles": {
            "package-manifest": ("**/package.json", "**/pnpm-workspace.yaml"),
            "lint-config": (
                "**/eslint.config.*",
                "**/.eslintrc*",
                "**/biome.json",
                "**/biome.jsonc",
            ),
            "format-config": (
                "**/.prettierrc*",
                "**/prettier.config.*",
                "**/biome.json",
            ),
            "lockfile": ("**/npm-shrinkwrap.json",),
            "test-config": (
                "**/jest.config.*",
                "**/vitest.config.*",
                "**/vitest.workspace.*",
                "**/playwright.config.*",
                "**/cypress.config.*",
                "**/karma.conf.*",
                "**/.mocharc*",
                "package.json",
            ),
        },
    },
    "rust": {
        "manifests": ("Cargo.toml",),
        "roles": {
            "package-manifest": ("**/Cargo.toml",),
            "lint-config": ("**/clippy.toml", "**/.clippy.toml"),
            "format-config": ("**/rustfmt.toml", "**/.rustfmt.toml"),
            "test-config": ("**/Cargo.toml", "**/.config/nextest.toml"),
        },
    },
    "java": {
        "manifests": ("pom.xml", "build.gradle", "build.gradle.kts"),
        "roles": {
            "package-manifest": (
                "**/pom.xml",
                "**/build.gradle",
                "**/build.gradle.kts",
                "**/settings.gradle",
                "**/settings.gradle.kts",
            ),
            "lint-config": ("**/checkstyle*.xml", "**/pmd*.xml", "**/spotbugs*.xml"),
            "test-config": ("**/pom.xml", "**/build.gradle", "**/build.gradle.kts"),
            "test-file": ("**/src/test/**",),
        },
    },
}
"""Extra patterns for existing roles, active when a listed manifest exists
anywhere outside an excluded directory (FR-032). Data, never a boundary."""

for _ecosystem, _table in ECOSYSTEM_PATTERNS.items():
    _extra = set(_table["roles"]) - set(GENERIC_PATTERNS)
    if _extra:
        raise RuntimeError(
            f"ecosystem table {_ecosystem!r} names roles that do not exist: "
            f"{sorted(_extra)}; a table may extend a role, never add one"
        )


def role(name: str) -> SourceRole:
    """The declared role ``name`` with its generic patterns."""
    return SourceRole(name=name, patterns=GENERIC_PATTERNS[name])


class RoleInputError(ValidationError):
    """A rejected ``.easy-verifier.toml`` or agent-input document.

    A :class:`ValidationError` so both adapters already treat it as one (CLI
    exit 2, MCP tool error), carrying every problem at once like findings do.
    """

    def __init__(self, source: str, errors: Sequence[str]) -> None:
        self.errors = tuple(errors)
        Exception.__init__(
            self,
            f"{source}: {len(self.errors)} error(s): " + "; ".join(self.errors),
        )


# ---------------------------------------------------------------------------
# caller inputs
# ---------------------------------------------------------------------------


def load_repo_config(repo: str | Path) -> dict[str, tuple[str, ...]]:
    """Read and validate the target's optional ``.easy-verifier.toml``.

    Absent file → ``{}``: nothing changes (NFR-005). The only accepted shape
    is ``[roles] <role> = ["glob", …]``, adding globs to an existing role.
    """
    root = Path(repo)
    path = root / CONFIG_FILENAME
    if not path.exists() and not path.is_symlink():
        return {}

    def fail(reason: str) -> RoleInputError:
        return RoleInputError(CONFIG_FILENAME, [reason])

    resolved = path.resolve()
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise fail("must be a regular file inside the repository")
    raw = resolved.read_bytes()
    if len(raw) > MAX_CONFIG_BYTES:
        raise fail(f"larger than {MAX_CONFIG_BYTES} bytes")
    try:
        data = tomllib.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise fail(f"not valid TOML: {redact(str(exc))}") from None

    errors: list[str] = []
    for key in data:
        if key != "roles":
            errors.append(
                f"{redact(key)}: unknown key; only [roles] is accepted, and it may "
                "only add paths to existing roles (no floors, rules or removals)"
            )
    configured = data.get("roles", {})
    if not isinstance(configured, dict):
        errors.append("roles: must be a table of role = [globs]")
        configured = {}

    result: dict[str, tuple[str, ...]] = {}
    for name, globs in configured.items():
        field = f"roles.{redact(name)}"
        if name not in GENERIC_PATTERNS:
            errors.append(f"{field}: unknown role; known roles: {_known_roles()}")
        elif not isinstance(globs, list):
            errors.append(f"{field}: must be a list of path globs")
        elif not globs:
            errors.append(
                f"{field}: empty list; roles cannot be removed, only extended"
            )
        else:
            valid = []
            for index, glob in enumerate(globs):
                problem = _config_glob_problem(glob)
                if problem:
                    errors.append(f"{field}[{index}] {_quote(glob)}: {problem}")
                else:
                    valid.append(glob)
            result[name] = tuple(valid)
    if errors:
        raise RoleInputError(CONFIG_FILENAME, errors)
    return dict(sorted(result.items()))


def parse_agent_input(document: object) -> dict:
    """The agent-input document as a dict, from a parsed object or JSON text."""
    if isinstance(document, bytes | str):
        try:
            document = json.loads(document)
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise RoleInputError("agent input", ["not valid JSON"]) from None
    if not isinstance(document, dict):
        raise RoleInputError("agent input", ["must be a JSON object"])
    return document


def validate_agent_input(
    document: object, repo: str | Path
) -> dict[str, tuple[str, ...]]:
    """Validate an agent-input document; return its picks, role → paths.

    Accepts a parsed object or its JSON text. ``gate_evaluations`` is only
    shape-checked here: whether each one is valid depends on this call's
    ratings and packs, so ``gate.apply_gate_evaluations`` validates it (T028).
    """
    document = parse_agent_input(document)

    root = _resolved_repo(repo)
    errors: list[str] = []
    for key in document:
        if key not in ("picks", "gate_evaluations"):
            errors.append(
                f"{redact(str(key))}: unknown key; only picks and "
                "gate_evaluations are accepted"
            )
    if not isinstance(document.get("gate_evaluations", {}), dict):
        errors.append(
            "gate_evaluations: must be an object mapping a dimension to an evaluation"
        )
    picks = document.get("picks", {})
    if not isinstance(picks, dict):
        errors.append("picks: must be an object mapping a role to a list of paths")
        picks = {}

    result: dict[str, tuple[str, ...]] = {}
    for name, paths in picks.items():
        field = f"picks.{redact(str(name))}"
        if name not in GENERIC_PATTERNS:
            errors.append(f"{field}: unknown role; known roles: {_known_roles()}")
            continue
        if not isinstance(paths, list):
            errors.append(f"{field}: must be a list of repository-relative paths")
            continue
        valid: set[str] = set()
        for index, value in enumerate(paths):
            problem = _pick_problem(root, value)
            if problem:
                errors.append(f"{field}[{index}] {_quote(value)}: {problem}")
            else:
                valid.add(PurePosixPath(value).as_posix())
        if valid:
            result[name] = tuple(sorted(valid))
    if errors:
        raise RoleInputError("agent input", errors)
    return dict(sorted(result.items()))


def _known_roles() -> str:
    return ", ".join(sorted(GENERIC_PATTERNS))


def _quote(value: object) -> str:
    return f"'{redact(value)}'" if isinstance(value, str) else ""


def _relative_path_problem(value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return "must be a non-empty string"
    pure = PurePosixPath(value)
    if pure.is_absolute() or re.match(r"^[A-Za-z]:", value) or "\\" in value:
        return "absolute or non-POSIX path; must be repository-relative"
    if ".." in pure.parts:
        return "'..' escapes the repository"
    return None


def _config_glob_problem(value: object) -> str | None:
    """Reject config globs that are unbounded in shape, not only in place."""
    problem = _relative_path_problem(value)
    if problem:
        return problem
    segments = str(value).split("/")
    if any("**" in segment and segment != "**" for segment in segments):
        return "'**' must be a whole path segment (e.g. 'docs/**/*.md')"
    if segments.count("**") > MAX_CONFIG_GLOBSTARS:
        return f"at most {MAX_CONFIG_GLOBSTARS} '**' segments are allowed"
    stars = sum(segment.count("*") for segment in segments if segment != "**")
    if stars > MAX_CONFIG_STARS:
        return f"at most {MAX_CONFIG_STARS} '*' wildcards are allowed"
    return None


def _pick_problem(root: Path, value: object) -> str | None:
    problem = _relative_path_problem(value)
    if problem:
        return problem
    if _in_excluded_dir(str(value)):
        return "inside an excluded vendor/build directory; it can never fill a role"
    try:
        resolved = (root / str(value)).resolve()
    except OSError:
        return "could not be resolved"
    if not resolved.is_relative_to(root):
        return "resolves outside the repository"
    if not resolved.exists():
        return "does not exist"
    if not resolved.is_file():
        return "not a regular file"
    relative = resolved.relative_to(root).as_posix()
    if _is_secret_bearing(str(value)) or _is_secret_bearing(relative):
        return "secret-bearing file (DDR-0002); its contents are never read"
    if _in_excluded_dir(relative):
        return "resolves into an excluded vendor/build directory"
    return None


def _in_excluded_dir(relative: str) -> bool:
    return any(part in _EXCLUDED_DIRS for part in PurePosixPath(relative).parts[:-1])


# ---------------------------------------------------------------------------
# resolution
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RoleResolution:
    """Which files fill which role, and where each came from."""

    files: dict[str, tuple[str, ...]]
    """Every file-backed role requested, sorted paths (possibly empty)."""

    origins: dict[tuple[str, str], str]
    """``(role, path)`` → ``rules`` / ``config`` / ``pick``. A file matched by
    rules is ``rules`` even if config or a pick also names it."""

    ecosystems: tuple[str, ...]
    truncated_roles: tuple[str, ...]
    walk_truncated: bool


def resolve(
    repo: str | Path,
    roles: Sequence[SourceRole],
    *,
    config: Mapping[str, Sequence[str]] | None = None,
    picks: Mapping[str, Sequence[str]] | None = None,
) -> RoleResolution:
    """Resolve file-backed ``roles`` in one bounded, deterministic walk.

    Reuses ``context._walk`` so excluded vendor/build directories, directory
    symlink escapes and cycles are handled exactly as discovery handles them.
    A file symlink escaping the repository is listed, never followed: reading
    it through ``read_source`` records why it cannot fill its role. Picks are
    assumed validated by :func:`validate_agent_input`.
    """
    root = Path(repo)
    config = config or {}
    picks = picks or {}

    walked: list[str] = []
    walk_truncated = False
    for path in _walk(root, root, extensions=None, contained_only=False):
        if len(walked) >= MAX_ROLE_WALK_FILES:
            walk_truncated = True
            break
        walked.append(path)

    names = {PurePosixPath(path).name for path in walked}
    ecosystems = tuple(
        ecosystem
        for ecosystem, table in ECOSYSTEM_PATTERNS.items()
        if names & set(table["manifests"])
    )

    files: dict[str, tuple[str, ...]] = {}
    origins: dict[tuple[str, str], str] = {}
    truncated: list[str] = []
    for item in roles:
        if not item.patterns:
            continue
        rule_patterns = item.patterns + tuple(
            pattern
            for ecosystem in ecosystems
            for pattern in ECOSYSTEM_PATTERNS[ecosystem]["roles"].get(item.name, ())
        )
        rules_match = _matcher(rule_patterns)
        config_patterns = tuple(config.get(item.name, ()))
        # Config globs are untrusted: matched segment-wise with a bounded
        # matcher, never compiled into the combined backtracking regex.
        config_match = _config_matcher(config_patterns) if config_patterns else None

        matched: dict[str, str] = {}
        for path in walked:
            if rules_match(path):
                matched[path] = ORIGIN_RULES
            elif config_match is not None and config_match(path):
                matched[path] = ORIGIN_CONFIG
        kept = sorted(matched)
        if len(kept) > MAX_ROLE_FILES:
            truncated.append(item.name)
            kept = kept[:MAX_ROLE_FILES]
        chosen = {path: matched[path] for path in kept}
        for path in picks.get(item.name, ()):
            chosen.setdefault(path, ORIGIN_PICK)

        files[item.name] = tuple(sorted(chosen))
        for path, origin in chosen.items():
            origins[(item.name, path)] = origin

    return RoleResolution(
        files=files,
        origins=origins,
        ecosystems=ecosystems,
        truncated_roles=tuple(truncated),
        walk_truncated=walk_truncated,
    )


def source_provenance(resolution: RoleResolution) -> str:
    """The one-line sources provenance (FR-039): which inputs added files."""
    config = {path for (_, path), o in resolution.origins.items() if o == ORIGIN_CONFIG}
    picked = {path for (_, path), o in resolution.origins.items() if o == ORIGIN_PICK}
    parts = [ORIGIN_RULES]
    if config:
        parts.append("config")
    if picked:
        parts.append(
            f"agent picks ({len(picked)} file{'' if len(picked) == 1 else 's'})"
        )
    return " + ".join(parts)


def resolution_warnings(resolution: RoleResolution) -> tuple[str, ...]:
    """State every bound the resolution hit (NFR-009: never a silent stop)."""
    warnings = [
        f"Source role '{name}' matched more than {MAX_ROLE_FILES} files; only the "
        f"first {MAX_ROLE_FILES} in sorted path order were considered."
        for name in resolution.truncated_roles
    ]
    if resolution.walk_truncated:
        warnings.append(
            f"Source-role resolution was bounded at {MAX_ROLE_WALK_FILES} walked "
            "files; files beyond it were never examined, so an unfilled role here "
            "is not a repository-wide absence."
        )
    return tuple(warnings)


def unfilled_reason(resolution: RoleResolution, name: str) -> str | None:
    """Why a role with no read file is unfilled, when resolution alone says.

    ``None`` means candidates existed and were not secret-bearing: the reason
    then depends on what reading did, which the pipeline knows.
    """
    paths = resolution.files.get(name)
    if paths is None:
        return None
    if not paths:
        if resolution.walk_truncated:
            return (
                "not found within the first "
                f"{MAX_ROLE_WALK_FILES} files walked: role resolution was bounded, "
                "so files beyond it were never examined"
            )
        return "not found: no file in the repository matched this role's patterns"
    if all(_is_secret_bearing(path) for path in paths):
        return "excluded: secret-bearing"
    return None


@lru_cache(maxsize=512)
def _matcher(patterns: tuple[str, ...]):
    compiled = re.compile("|".join(f"(?:{_translate(p)})" for p in patterns))
    return lambda path: compiled.fullmatch(path) is not None


@lru_cache(maxsize=512)
def _config_matcher(patterns: tuple[str, ...]):
    """Match untrusted globs with the same semantics as :func:`_translate`,
    in O(pattern segments x path segments) time.

    ``**`` (a whole segment, enforced by validation) spans zero or more path
    segments, or one or more when it ends the glob; any other segment is
    matched against exactly one path segment by ``fnmatchcase``, with ``[``
    escaped so it stays literal as in the built-in translation.
    """
    parsed = tuple(
        tuple(segment.replace("[", "[[]") for segment in pattern.split("/"))
        for pattern in patterns
    )
    return lambda path: any(
        _segments_match(pattern, tuple(path.split("/"))) for pattern in parsed
    )


def _segments_match(pattern: tuple[str, ...], parts: tuple[str, ...]) -> bool:
    memo: dict[tuple[int, int], bool] = {}

    def match(i: int, j: int) -> bool:
        key = (i, j)
        if key not in memo:
            if i == len(pattern):
                result = j == len(parts)
            elif pattern[i] == "**":
                if i == len(pattern) - 1:
                    result = j < len(parts)
                else:
                    result = match(i + 1, j) or (j < len(parts) and match(i, j + 1))
            else:
                result = (
                    j < len(parts)
                    and fnmatchcase(parts[j], pattern[i])
                    and match(i + 1, j + 1)
                )
            memo[key] = result
        return memo[key]

    return match(0, 0)


def _translate(pattern: str) -> str:
    """Glob → regex: ``**/`` any directories, ``**`` anything, ``*``/``?``
    within one path segment. Every other character is literal."""
    out: list[str] = []
    index = 0
    while index < len(pattern):
        if pattern.startswith("**/", index):
            out.append("(?:[^/]+/)*")
            index += 3
        elif pattern.startswith("**", index):
            out.append(".*")
            index += 2
        elif pattern[index] == "*":
            out.append("[^/]*")
            index += 1
        elif pattern[index] == "?":
            out.append("[^/]")
            index += 1
        else:
            out.append(re.escape(pattern[index]))
            index += 1
    return "".join(out)


__all__ = [
    "CONFIG_FILENAME",
    "ECOSYSTEM_PATTERNS",
    "GENERIC_PATTERNS",
    "MAX_ROLE_FILES",
    "MAX_ROLE_WALK_FILES",
    "RoleInputError",
    "RoleResolution",
    "load_repo_config",
    "resolution_warnings",
    "resolve",
    "role",
    "source_provenance",
    "unfilled_reason",
    "parse_agent_input",
    "validate_agent_input",
]
