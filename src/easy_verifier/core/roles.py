"""Source roles: what fills them, and from where (T026, DDR-0006).

A dimension seeks **roles** (a lockfile, a requirements doc, a CI workflow), not
filenames. This module is the whole mechanism, as plain data plus three
functions — no base class, no detection classes:

* :data:`GENERIC_PATTERNS` — the language-agnostic globs for every file-backed
  role. Its keys are the complete set of roles a config file or an agent pick
  may name.
* the reference registry (:mod:`.registry`) — cited extra globs for existing
  roles per language, switched on when one of the language's manifests is
  present. An entry may only *extend* a role; the loader rejects one that
  names any other.
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
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from fnmatch import fnmatchcase
from functools import lru_cache
from pathlib import Path, PurePosixPath

from .batches import BatchInputError, parse_batches
from .context import _EXCLUDED_DIRS, _is_secret_bearing, _resolved_repo, _walk
from .findings import ValidationError
from .judge import PACK_FLOORS, DocumentationResult, DocumentationRule
from .models import SourceRole
from .redact import redact
from .registry import (
    CONVENTION_FIELDS,
    REJECTED,
    Registry,
    apply_reviews,
    convention_value_problem,
    layered_registry,
    local_write_problem,
    parse_local_entries,
    parse_reviews,
    review_problems,
    save_local_entries,
    sot_root,
)

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
    "architecture-doc": (
        "PROJECT_SPEC.md",
        "ARCHITECTURE.md",
        "**/docs/architecture*",
        "**/docs/architecture/**",
        *_docs("architecture", "design"),
    ),
    "decision-record": (
        "BRAINSTORMING_LOG*.md",
        "**/adr/**",
        "**/adrs/**",
        "**/ADR/**",
        "**/ddr/**",
        "**/decisions/**",
        *_docs("decision"),
    ),
    "requirements-doc": (
        "PRD*.md",
        "**/PRD*.md",
        *_docs("requirement"),
        # T075 (FR-068): a requirements directory, e.g. docs/requirements/x.md
        "docs/requirements*/**",
        "**/docs/requirements*/**",
    ),
    "spec-doc": (
        "PROJECT_SPEC.md",
        "**/specs/**/*.md",
        "**/specification/**/*.md",
        *_docs("spec"),
        # T075 (FR-068): OpenAPI / Swagger contracts, anywhere
        *(
            f"{prefix}{name}*.{suffix}"
            for prefix in ("", "**/")
            for name in ("openapi", "swagger")
            for suffix in ("yaml", "yml", "json")
        ),
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
    # T041 supply-chain roles. Licence files: SPDX "Other licensing
    # information" and the REUSE spec's LICENSES/ directory
    # (https://spdx.dev/learn/handling-license-info/,
    # https://reuse.software/spec/). Release configuration: the declared
    # config files of goreleaser (https://goreleaser.com/customization/),
    # semantic-release (https://semantic-release.gitbook.io/semantic-release/usage/configuration),
    # release-please (https://github.com/googleapis/release-please/blob/main/docs/manifest-releaser.md),
    # changesets (https://github.com/changesets/changesets/blob/main/docs/config-file-options.md),
    # cargo-release (https://github.com/crate-ci/cargo-release/blob/master/docs/reference.md)
    # and jreleaser (https://jreleaser.org/guide/latest/configuration/index.html).
    "licence-file": (
        "**/LICENSE*",
        "**/LICENCE*",
        "**/License*",
        "**/Licence*",
        "**/license*",
        "**/licence*",
        "**/COPYING*",
        "**/UNLICENSE*",
        "LICENSES/**",
    ),
    "release-config": (
        "**/.goreleaser.yml",
        "**/.goreleaser.yaml",
        "**/goreleaser.yml",
        "**/goreleaser.yaml",
        "**/.releaserc",
        "**/.releaserc.*",
        "**/release.config.*",
        "**/release-please-config.json",
        "**/.release-please-manifest.json",
        "**/.changeset/config.json",
        "**/release.toml",
        "**/jreleaser.yml",
        "**/jreleaser.yaml",
    ),
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


@dataclass(frozen=True)
class GenericTokens:
    """Language-neutral CI facts, each with the link that backs it (T041).

    The registry holds per-language data; these are true of any ecosystem, so
    they sit in the generic layer beside :data:`GENERIC_PATTERNS`, never in a
    dimension module."""

    value: tuple[str, ...]
    citation_url: str


GENERIC_CI_FACTS: dict[str, tuple[GenericTokens, ...]] = {
    # Lines that reference an external GitHub Actions step: ``uses: x/y@ref``,
    # or a container image of a step or service in any CI system
    # (``image: node:20``; Drone, GitLab, Woodpecker, GitHub services).
    # User decision 2026-10-07 (T041 D1).
    "action_reference": (
        GenericTokens(
            ("uses:",),
            "https://docs.github.com/en/actions/writing-workflows/workflow-syntax-for-github-actions#jobsjob_idstepsuses",
        ),
        GenericTokens(
            ("image:",),
            "https://github.com/ossf/scorecard/blob/main/docs/checks.md#pinned-dependencies",
        ),
    ),
    # A reference is pinned when it ends in a full 40-hex commit SHA (an
    # action) or an ``@sha256:`` digest (a container image); regexes over the
    # reference text, never over code.
    "pinned_reference": (
        GenericTokens(
            ("@[0-9a-f]{40}$", "@sha256:[0-9a-f]{64}$"),
            "https://github.com/ossf/scorecard/blob/main/docs/checks.md#pinned-dependencies",
        ),
    ),
    # A reference that never leaves the repository or the runner is not a
    # supply-chain dependency (Scorecard skips local actions).
    "local_reference": (
        GenericTokens(
            ("./",),
            "https://github.com/ossf/scorecard/blob/main/docs/checks.md#pinned-dependencies",
        ),
    ),
    # Tokens showing an SBOM, signing or provenance step in CI or release
    # configuration (code tokens, registry token syntax).
    "provenance_steps": (
        GenericTokens(
            ("slsa", "provenance", "attest"),
            "https://slsa.dev/spec/v1.0/provenance",
        ),
        GenericTokens(
            ("sbom", "cyclonedx"),
            "https://cyclonedx.org/specification/overview/",
        ),
        GenericTokens(("spdx",), "https://spdx.dev/use/specifications/"),
        GenericTokens(
            ("cosign", "sigstore"),
            "https://docs.sigstore.dev/cosign/signing/overview/",
        ),
        GenericTokens(("syft",), "https://github.com/anchore/syft"),
    ),
}
"""Cited language-neutral CI tokens for the supply-chain dimension (T041)."""


@lru_cache(maxsize=1)
def _registry() -> Registry:
    """The reference registry (DDR-0007): curated plus the local layer.

    It holds each language's manifests and extra role globs; a language is
    active when one of its manifests exists (FR-032). Data, never a boundary:
    an entry naming a role outside :data:`GENERIC_PATTERNS` is rejected.
    Cached; :func:`apply_registry_entries` clears it on every call carrying
    agent input so a long-running server sees local writes (T036).
    """
    return layered_registry(known_roles=GENERIC_PATTERNS)


def role(name: str) -> SourceRole:
    """The declared role ``name`` with its generic patterns."""
    return SourceRole(name=name, patterns=GENERIC_PATTERNS[name])


MAX_ERROR_LINES = 20
"""Error lines kept in one :class:`RoleInputError`; the rest are counted."""


class RoleInputError(ValidationError):
    """A rejected ``.easy-verifier.toml`` or agent-input document.

    A :class:`ValidationError` so both adapters already treat it as one (CLI
    exit 2, MCP tool error), carrying every problem at once like findings do.
    """

    def __init__(self, source: str, errors: Sequence[str]) -> None:
        # Bounded: the message goes back to an untrusted caller, so a hostile
        # document cannot inflate it without limit (T028 Stage 4 P2).
        errors = list(errors)
        if len(errors) > MAX_ERROR_LINES:
            extra = len(errors) - MAX_ERROR_LINES
            errors = errors[:MAX_ERROR_LINES] + [f"…and {extra} more"]
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

    Absent file → ``{}``: nothing changes (NFR-005). The accepted shapes are
    ``[roles] <role> = ["glob", …]``, adding globs to an existing role, and
    ``[conventions] <field> = ["value", …]`` (T073), adding convention
    patterns; the latter is validated here and returned by
    :func:`load_repo_conventions`.
    """
    return _repo_config(repo)[0]


def load_repo_conventions(repo: str | Path) -> dict[str, tuple[str, ...]]:
    """The validated ``[conventions]`` table of the target's optional
    ``.easy-verifier.toml``: :data:`~easy_verifier.core.registry.CONVENTION_FIELDS`
    field → values to add (``registry.with_config_conventions``)."""
    return _repo_config(repo)[1]


def load_repo_packs(repo: str | Path) -> tuple[str, ...]:
    """The pack names the target's optional ``.easy-verifier.toml`` lists in
    ``packs = [...]`` (T047), as written: :func:`active_packs` keeps the known
    ones. Absent file or key → ``()``."""
    return _repo_config(_resolved_repo(repo))[2]


def active_packs(
    repo: str | Path, document: Mapping | None
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """The optional packs this call runs (T047, FR-053), in declared order,
    and one note per unknown name (ignored, never an error).

    A pack is active only when ``.easy-verifier.toml`` lists it or the agent
    picks it (``agent_input.packs``); nothing is ever guessed from the
    repository's contents."""
    requested = list(load_repo_packs(repo))
    if document is not None:
        requested.extend(_agent_packs(document.get("packs", []), []))
    known = tuple(name for name in PACK_FLOORS if name in requested)
    notes = tuple(
        f"unknown pack {_quote(name)} ignored; known packs: {', '.join(PACK_FLOORS)}"
        for name in dict.fromkeys(requested)
        if name not in PACK_FLOORS
    )
    return known, notes


def _agent_packs(value: object, errors: list[str]) -> tuple[str, ...]:
    """``packs``: a list of pack names (strings); shape errors join ``errors``."""
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item for item in value
    ):
        errors.append("packs: must be a list of pack names, e.g. [\"healthcare\"]")
        return ()
    return tuple(value)


def _repo_config(
    repo: str | Path,
) -> tuple[dict[str, tuple[str, ...]], dict[str, tuple[str, ...]], tuple[str, ...]]:
    root = Path(repo)
    path = root / CONFIG_FILENAME
    if not path.exists() and not path.is_symlink():
        return {}, {}, ()

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
        if key not in ("roles", "conventions", "packs"):
            errors.append(
                f"{redact(key)}: unknown key; only [roles], [conventions] and "
                "packs are accepted, and they may only add paths to existing "
                "roles, patterns to conventions or optional packs (no floors, "
                "rules or removals)"
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
    conventions = _config_conventions(data.get("conventions", {}), errors)
    packs = _agent_packs(data.get("packs", []), errors)
    if errors:
        raise RoleInputError(CONFIG_FILENAME, errors)
    return dict(sorted(result.items())), conventions, packs


def _config_conventions(
    table: object, errors: list[str]
) -> dict[str, tuple[str, ...]]:
    """``[conventions]``: each field a non-empty list of values that pass the
    local layer's checks (``registry.convention_value_problem``)."""
    if not isinstance(table, dict):
        errors.append("conventions: must be a table of field = [values]")
        return {}
    result: dict[str, tuple[str, ...]] = {}
    for name, values in table.items():
        field = f"conventions.{redact(str(name))}"
        if name not in CONVENTION_FIELDS:
            errors.append(
                f"{field}: unknown field; known: {', '.join(CONVENTION_FIELDS)}"
            )
        elif not isinstance(values, list) or not values:
            errors.append(f"{field}: must be a non-empty list of patterns")
        else:
            for index, value in enumerate(values):
                problem = convention_value_problem(name, value)
                if problem:
                    errors.append(f"{field}[{index}]: {problem}")
            result[name] = tuple(values)
    return dict(sorted(result.items()))


_AGENT_INPUT_KEYS = (
    "picks",
    "packs",
    "gate_evaluations",
    "registry_entries",
    "reviews",
    "improvements",
    "batches",
    "summary",
)


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
    ``registry_entries`` and ``reviews`` (T038) are fully validated here and
    applied by :func:`apply_registry_entries`. ``improvements`` (T066) is only
    shape-checked too: its items are named against the report's own plan, so
    ``improve.validate_improvements`` validates it in ``write_report``.
    ``summary`` (T069) is shape-checked here and fully validated in
    ``write_report``.
    """
    document = parse_agent_input(document)

    root = _resolved_repo(repo)
    errors: list[str] = []
    for key in document:
        if key not in _AGENT_INPUT_KEYS:
            errors.append(
                f"{redact(str(key))}: unknown key; only picks, packs, "
                "gate_evaluations, registry_entries, reviews, improvements, "
                "batches and summary are accepted"
            )
    errors.extend(
        parse_local_entries(document.get("registry_entries"), GENERIC_PATTERNS)[1]
    )
    errors.extend(parse_reviews(document.get("reviews"))[1])
    if not isinstance(document.get("improvements", []), list):
        errors.append(
            "improvements: must be a list of {dimension, metric_name, suggestion}"
        )
    if not isinstance(document.get("summary", ""), str):
        errors.append("summary: must be a string")
    _agent_packs(document.get("packs", []), errors)
    if "batches" in document:
        try:
            parse_batches(document["batches"])
        except BatchInputError as exc:
            errors.extend(exc.errors)
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


def apply_registry_entries(document: Mapping, repo: str | Path) -> None:
    """Apply a validated document's ``reviews`` (T038), then save its
    ``registry_entries`` (T036), and reload the registry, so this call
    already scores with both. Reviews go first: a replacement sent with an
    ``improve`` or ``reject`` answer then supersedes the answered item.

    Called once per agent-input call, before any dimension runs. A layer that
    cannot be written is not an error: scoring continues on the data already
    on this machine and :func:`registry_notes` says what was not saved.
    """
    entries, _ = parse_local_entries(document.get("registry_entries"), GENERIC_PATTERNS)
    answers, _ = parse_reviews(document.get("reviews"))
    if (entries or answers) and local_write_problem(sot_root(), Path(repo)) is None:
        try:
            apply_reviews(answers, sot_root(), known_roles=GENERIC_PATTERNS)
            save_local_entries(entries, sot_root(), known_roles=GENERIC_PATTERNS)
        except OSError:
            pass  # reported by registry_notes: not in the registry
    _registry.cache_clear()


def review_notes(document: Mapping | None) -> tuple[str, ...]:
    """Answers in ``document`` that will be ignored (unknown or already
    reviewed ids). Call before :func:`apply_registry_entries` changes the
    layer; the result joins :func:`registry_notes`."""
    raw = document.get("reviews") if document is not None else None
    answers, _ = parse_reviews(raw)
    return tuple(review_problems(answers, sot_root(), GENERIC_PATTERNS))


def registry_notes(document: Mapping | None, repo: str | Path) -> tuple[str, ...]:
    """What the caller must be told about the registry this call used:
    registry warnings (e.g. "curated wins") and entries that could not be
    saved. Never part of the byte-compared score payload: it describes this
    machine's layer, not the score (DDR-0005)."""
    registry = _registry()
    notes = list(registry.warnings)
    raw = document.get("registry_entries") if document is not None else None
    entries, _ = parse_local_entries(raw, GENERIC_PATTERNS)
    refused = [
        entry
        for entry in entries
        if entry.cited.review_status != REJECTED
        and _in_registry(registry, entry, rejected=True)
    ]
    for entry in refused:
        notes.append(
            f"registry entry {entry.name}.{entry.field} = "
            f"{', '.join(entry.cited.value)} was rejected by the user earlier; "
            "it is not used (research a different value)"
        )
    unsaved = [
        entry
        for entry in entries
        if entry not in refused and not _in_registry(registry, entry)
    ]
    answers = parse_reviews(document.get("reviews") if document else None)[0]
    write_problem = local_write_problem(sot_root(), Path(repo))
    if answers and write_problem:
        notes.append(
            f"reviews cannot be saved: {len(answers)} answer(s) not applied "
            f"({write_problem}); the entries stay pending"
        )
    if unsaved:
        reason = local_write_problem(sot_root(), Path(repo)) or "the write was refused"
        notes.append(
            f"research cannot be saved: {len(unsaved)} registry "
            f"entr{'y' if len(unsaved) == 1 else 'ies'} not saved ({reason}); "
            "scoring used only the registry data already on this machine"
        )
    return tuple(notes)


def _in_registry(registry: Registry, entry, *, rejected: bool = False) -> bool:
    """Whether ``entry``'s values are in ``registry``: among the live data,
    or with ``rejected`` among the rejection records (T038). A replayed
    rejection record is looked up among the records."""
    found = registry.languages.get(entry.name) or registry.frameworks.get(entry.name)
    if found is None:
        return False
    if rejected or entry.cited.review_status == REJECTED:
        cited_values = found.rejected.get(entry.field, ())
    elif entry.field == "manifests":
        cited_values = found.manifests
    elif entry.field.startswith("roles."):
        cited_values = found.roles.get(entry.field.removeprefix("roles."), ())
    else:
        cited_values = found.fields.get(entry.field, ())
    have = {value for cited in cited_values for value in cited.value}
    return set(entry.cited.value) <= have


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


_TEMPLATE_DIRS = frozenset({"template", "templates"})
_TEMPLATE_NAME = re.compile(r"[._-]template\.", re.IGNORECASE)


def _is_template(path: str) -> bool:
    """A file under a ``template(s)/`` directory, or named ``*_template.*``,
    ``*.template.*`` or ``*-template.*``."""
    pure = PurePosixPath(path)
    return bool(_TEMPLATE_NAME.search(pure.name)) or any(
        part.lower() in _TEMPLATE_DIRS for part in pure.parts[:-1]
    )


RULE_EXCLUSIONS: Mapping[str, Callable[[str], bool]] = {
    "requirements-doc": _is_template,
}
"""Paths a role's rule (and local-layer) patterns never fill (T055, user
2026-09-29): a template is not a competing requirements source. Config globs
and agent picks are explicit choices and are not filtered."""


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

    registry = _registry()
    ecosystems = registry.active_languages(
        {PurePosixPath(path).name for path in walked}
    )

    files: dict[str, tuple[str, ...]] = {}
    origins: dict[tuple[str, str], str] = {}
    truncated: list[str] = []
    for item in roles:
        if not item.patterns:
            continue
        rule_patterns = item.patterns + registry.patterns_for(item.name, ecosystems)
        rules_match = _matcher(rule_patterns)
        # Local-layer globs came from a model's research: bounded matcher.
        local_patterns = registry.patterns_for(item.name, ecosystems, local=True)
        local_match = _config_matcher(local_patterns) if local_patterns else None
        config_patterns = tuple(config.get(item.name, ()))
        # Config globs are untrusted: matched segment-wise with a bounded
        # matcher, never compiled into the combined backtracking regex.
        config_match = _config_matcher(config_patterns) if config_patterns else None

        excluded = RULE_EXCLUSIONS.get(item.name)
        matched: dict[str, str] = {}
        for path in walked:
            if (
                rules_match(path) or (local_match is not None and local_match(path))
            ) and not (excluded is not None and excluded(path)):
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
    warnings.extend(
        f"Reference registry: {warning}" for warning in _registry().warnings
    )
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


def documentation_present(
    rule: DocumentationRule, files_read: Sequence[str]
) -> DocumentationResult:
    """Check a documentation rule (FR-052) against the files a dimension's
    evidence pack read, with this module's glob semantics.

    The first match in sorted order is cited. ``missing`` is bounded by those
    reads and says so: it is not a repository-wide absence."""
    match = _matcher(rule.patterns)
    found = sorted(path for path in files_read if match(path))
    if found:
        return DocumentationResult(
            rule.area, "present", found[0], rule.citation, "matched a file read"
        )
    return DocumentationResult(
        rule.area,
        "missing",
        None,
        rule.citation,
        "no file matching "
        + ", ".join(rule.patterns)
        + " was among the files this dimension read",
    )


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
    "GENERIC_PATTERNS",
    "MAX_ROLE_FILES",
    "MAX_ROLE_WALK_FILES",
    "RoleInputError",
    "RoleResolution",
    "apply_registry_entries",
    "review_notes",
    "registry_notes",
    "load_repo_config",
    "resolution_warnings",
    "resolve",
    "role",
    "source_provenance",
    "unfilled_reason",
    "parse_agent_input",
    "validate_agent_input",
]
