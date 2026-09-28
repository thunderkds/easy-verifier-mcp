"""MCP-only hard gates: detect (T027) and evaluate (T028).

Pure functions, no state. ``detect_pick_gates`` decides, from one repository
walk, which declared source roles the rules left unfilled *and* which
unmatched files could plausibly fill them (FR-035). The core computes this;
whether it reaches the wire is an adapter decision (``mcp_server.py`` includes
it, the CLI never does — FR-021, FR-034, FR-040).

A candidate is only ever ``{path, heading}``: a repository-relative path and a
short, redacted first heading or line. Nothing here calls a model (NFR-001).

The evaluate gate (FR-036 to FR-038) names the dimensions whose rules
abstained or sit within the declared band of a threshold, and applies the
caller's validated gate evaluations as :class:`GatedRating` values. The
agent input is untrusted: every field is type-checked, and every cited ref
must resolve in that dimension's own pack (FR-015a).

The reference gate (T037, FR-044 to FR-046) names, per detected language and
framework, the registry fields the rating rules consume that neither the
curated nor the local layer holds — at most :data:`MAX_REFERENCE_FIELDS`,
languages first — with fixed research instructions. Stack detection itself
(:func:`detect_stack`) is shared: both adapters list the detected stack.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath

from ..dimensions import _doc_extract
from .context import _is_secret_bearing, _resolved_repo, _walk
from .judge import (
    BORDERLINE_BAND,
    COVERAGE_FLOORS,
    RATING_RULES,
    GatedRating,
    Rating,
    RatingAbstention,
    within_band,
)
from .metric_tables import FIELD_METRICS, ROLE_METRICS
from .redact import redact
from .registry import ENTRY_FIELDS, Registry, _manifest_matches
from .roles import (
    GENERIC_PATTERNS,
    MAX_ROLE_WALK_FILES,
    RoleInputError,
    resolve,
    role,
)

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


# ---------------------------------------------------------------------------
# evaluate gate


MAX_EVIDENCE_REFS_PER_GATE = 20
"""Refs offered per gated dimension; overflow is counted, never silent. Any
ref in the pack still resolves — the list is a starting point, not a cap
on what may be cited."""

_EVALUATION_FIELDS = frozenset({"score", "confidence", "evidence_refs", "rationale"})


def detect_evaluate_gates(
    ratings: Sequence[Rating | RatingAbstention],
) -> dict[str, str]:
    """Dimension -> gate reason, in canonical order (FR-036, AC1).

    ``abstained`` when the rules abstained; ``borderline: <metric>, ...``
    when any rule input's value lies within the declared band of its
    threshold. Every other dimension is absent: outside a gate the agent
    never changes a number.
    """
    gates: dict[str, str] = {}
    for item in ratings:
        if type(item) is RatingAbstention:
            gates[item.dimension] = "abstained"
        elif type(item) is Rating:
            near = [
                entry.metric_name
                for entry in item.inputs
                if within_band(entry.metric_value, entry.threshold)
            ]
            if near:
                gates[item.dimension] = "borderline: " + ", ".join(near)
    return gates


def gate_requests(
    gates: Mapping[str, str], packs: Mapping[str, object]
) -> list[dict] | None:
    """The ``needs_input.gate_evaluations`` entries: refs only, never excerpt
    text, capped per dimension. A gated dimension with nothing to cite is
    left out — FR-037 requires a resolving ref, so asking would be a round
    trip no answer could satisfy. ``None`` when nothing is left to ask."""
    requests = []
    for dimension, reason in gates.items():
        refs = _pack_refs(packs.get(dimension))
        if not refs:
            continue
        requests.append(
            {
                "dimension": dimension,
                "reason": reason,
                "evidence_refs": refs[:MAX_EVIDENCE_REFS_PER_GATE],
                "omitted": max(0, len(refs) - MAX_EVIDENCE_REFS_PER_GATE),
            }
        )
    return requests or None


def apply_gate_evaluations(
    document: object,
    ratings: Sequence[Rating | RatingAbstention],
    packs: Mapping[str, object],
) -> tuple[Rating | RatingAbstention | GatedRating, ...]:
    """Validate ``gate_evaluations`` and return ``ratings`` with each gated,
    evaluated dimension replaced by its :class:`GatedRating`.

    Raises :class:`RoleInputError` naming every offending field at once and
    applies nothing if any evaluation is invalid. ``rationale`` is checked
    for shape and then dropped: it never reaches a payload or report.
    """
    errors: list[str] = []
    if not isinstance(document, dict):
        raise RoleInputError(
            "agent input",
            [
                "gate_evaluations: must be an object mapping a dimension to "
                "an evaluation"
            ],
        )
    gates = detect_evaluate_gates(ratings)
    accepted: dict[str, tuple[int | float, int | float, tuple[str, ...]]] = {}
    for name, entry in document.items():
        field = f"gate_evaluations.{redact(str(name))}"
        if name not in COVERAGE_FLOORS:
            errors.append(f"{field}: unknown dimension")
            continue
        if name not in gates:
            errors.append(
                f"{field}: not at a hard gate on this call (the rules rated it "
                f"with no input within {BORDERLINE_BAND * 100:.0f}% of a "
                "threshold); outside a gate the agent never changes a number"
            )
            continue
        problems = _evaluation_problems(field, entry, packs.get(name))
        if problems:
            errors.extend(problems)
            continue
        accepted[name] = (
            entry["score"],
            entry["confidence"],
            tuple(entry["evidence_refs"]),
        )
    if errors:
        raise RoleInputError("agent input", errors)
    return tuple(
        GatedRating(item, *accepted[item.dimension])
        if item.dimension in accepted
        else item
        for item in ratings
    )


def _evaluation_problems(field: str, entry: object, pack: object) -> list[str]:
    if not isinstance(entry, dict):
        return [f"{field}: must be an object with score, confidence, evidence_refs"]
    problems = [
        f"{field}.{redact(str(key))}: unknown field"
        for key in entry
        if key not in _EVALUATION_FIELDS
    ]
    if not _is_number_in(entry.get("score"), 0, 100):
        problems.append(f"{field}.score: must be a number from 0 through 100")
    if not _is_number_in(entry.get("confidence"), 0, 1):
        problems.append(f"{field}.confidence: must be a number from 0 through 1")
    if "rationale" in entry and not isinstance(entry["rationale"], str):
        problems.append(f"{field}.rationale: must be a string when present")
    refs = entry.get("evidence_refs")
    if not isinstance(refs, list) or not refs:
        problems.append(f"{field}.evidence_refs: at least one evidence ref required")
        return problems
    if len(refs) > MAX_EVIDENCE_REFS_PER_GATE:
        problems.append(
            f"{field}.evidence_refs: {len(refs)} refs; at most "
            f"{MAX_EVIDENCE_REFS_PER_GATE} are accepted"
        )
        return problems
    available = set(_pack_refs(pack))
    truncated = bool(getattr(pack, "truncated", False))
    for index, ref in enumerate(refs):
        label = f"{field}.evidence_refs[{index}]"
        if not isinstance(ref, str) or not ref:
            problems.append(f"{label}: must be a non-empty string")
        elif ref not in available:
            reason = f"{label} '{redact(ref)}': not found in the dimension's pack"
            if truncated:
                reason += (
                    " — the pack was truncated by the evidence budget; re-cite "
                    "a surviving excerpt instead"
                )
            problems.append(reason)
    return problems


def _is_number_in(value: object, low: int, high: int) -> bool:
    """A finite int or float within [low, high]; ``bool`` and strings never."""
    if type(value) not in (int, float) or not math.isfinite(value):
        return False
    return low <= value <= high


def _pack_refs(pack: object) -> list[str]:
    if pack is None:
        return []
    return list(dict.fromkeys(excerpt.ref for excerpt in pack.excerpts))


# ---------------------------------------------------------------------------
# stack detection and reference gate (T037)

MAX_MANIFESTS = 100
"""Manifests read for framework detection, in path order; the rest are
counted in ``manifests_omitted``, never silently skipped."""

MAX_MANIFEST_BYTES = 256 * 1024
"""Bytes read from one manifest; a larger one is read up to this bound."""

MAX_REFERENCE_FIELDS = 20
"""FR-045: fields asked per call; the rest are counted in ``omitted``."""

_JSON_DEPENDENCY_SECTIONS = (
    "dependencies",
    "devDependencies",
    "peerDependencies",
    "optionalDependencies",
    "require",
    "require-dev",
)
"""Where a JSON manifest declares dependencies: npm ``package.json``
(https://docs.npmjs.com/cli/v10/configuring-npm/package-json#dependencies)
and Composer ``composer.json`` (https://getcomposer.org/doc/04-schema.md#require).
Only these keys count, so a word in ``description`` or ``scripts`` never
detects a framework. Other manifests are matched textually (a whole
dependency token, case-insensitive)."""

REFERENCE_INSTRUCTIONS = (
    "Each request names a registry field the rating rules read that this "
    "language or framework lacks. For each, in order: do at most 2 lookups, "
    "official documentation first. If found, send it on the next score call "
    "as an agent_input.registry_entries item: {language or framework (with "
    "extends), field, value: [...], citation_url: a clear https link to the "
    'primary source, source_tag: "agent-researched"}. If 2 lookups do not '
    "find it, ask the user, one question at a time, giving your recommended "
    'answer, and send their answer with source_tag "user-supplied" and the '
    "https link they confirm. Until answered, every listed field and the "
    "omitted count of further missing fields are scored with generic "
    "patterns only; omitted fields are listed once these are answered."
)
"""Fixed text sent with every reference gate (FR-046, decision B2)."""


def detect_stack(repo_path: str | Path, registry: Registry) -> dict:
    """Languages and frameworks detected from manifests, deterministically.

    A language is detected by a manifest anywhere in the (bounded, excluded
    directories skipped) walk, as ``roles.resolve`` does; a framework when
    one of its language's manifests — nested workspace packages included —
    declares one of the language's ``frameworks`` detection keys. Returns
    ``{"languages": [...], "frameworks": [{"name", "language"}, ...]}`` plus
    ``manifests_omitted`` when :data:`MAX_MANIFESTS` was exceeded.
    """
    root = _resolved_repo(repo_path)
    walked = []
    for path in _walk(root, root, extensions=None, contained_only=True):
        if len(walked) >= MAX_ROLE_WALK_FILES:
            break
        walked.append(path)
    languages = registry.active_languages({PurePosixPath(p).name for p in walked})

    patterns = {
        language: [
            pattern
            for cited in registry.languages[language].manifests
            for pattern in cited.value
        ]
        for language in languages
    }
    manifests = [
        path
        for path in walked
        if any(
            _manifest_matches(pattern, {PurePosixPath(path).name})
            for found in patterns.values()
            for pattern in found
        )
        and _eligible(root, path)
    ]
    omitted = max(0, len(manifests) - MAX_MANIFESTS)
    texts = {path: _read_manifest(root, path) for path in manifests[:MAX_MANIFESTS]}

    frameworks: dict[tuple[str, str], None] = {}
    for language in languages:
        keys = registry.detection_keys(language)
        if not keys:
            continue
        declared: set[str] = set()
        for path, text in texts.items():
            name = PurePosixPath(path).name
            if any(_manifest_matches(p, {name}) for p in patterns[language]):
                declared |= _declared(name, text, [key for _, key in keys])
        for framework, key in keys:
            if key in declared:
                frameworks[(framework, language)] = None
    stack: dict = {
        "languages": list(languages),
        "frameworks": [
            {"name": name, "language": language}
            for name, language in sorted(frameworks)
        ],
    }
    if omitted:
        stack["manifests_omitted"] = omitted
    return stack


def _read_manifest(root: Path, relative_path: str) -> str:
    try:
        with (root / relative_path).resolve().open("rb") as handle:
            raw = handle.read(MAX_MANIFEST_BYTES)
    except OSError:
        return ""
    return raw.decode("utf-8", errors="replace")


def _declared(name: str, text: str, keys: Sequence[str]) -> set[str]:
    """The detection ``keys`` that manifest ``name`` declares."""
    if name.endswith(".json"):
        try:
            data = json.loads(text)
        except ValueError:
            return set()
        if not isinstance(data, dict):
            return set()
        names = {
            dependency
            for section in _JSON_DEPENDENCY_SECTIONS
            if isinstance(data.get(section), dict)
            for dependency in data[section]
        }
        return {key for key in keys if key in names}
    return {
        key
        for key in keys
        if re.search(
            r"(?<![\w.@/-])" + re.escape(key) + r"(?![\w./-])", text, re.IGNORECASE
        )
    }


def required_fields() -> dict[str, str]:
    """Registry field -> the rules that consume it, derived from the rule
    table and the field/role -> metric maps (never hand-listed).

    A ``roles.<role>`` field counts only when the role has no generic,
    language-free pattern: otherwise the generic patterns already serve it.
    """
    consumers: dict[str, list[str]] = {}
    for dimension, rules in RATING_RULES.items():
        for rule in rules.values():
            consumers.setdefault(rule.metric_name, []).append(
                f"{dimension}.{rule.metric_name}"
            )
    fields = {field: FIELD_METRICS.get(field, ()) for field in ENTRY_FIELDS}
    fields.update(
        {
            f"roles.{name}": metrics
            for name, metrics in ROLE_METRICS.items()
            if not GENERIC_PATTERNS.get(name)
        }
    )
    result = {}
    for field, metrics in fields.items():
        rules = sorted({r for metric in metrics for r in consumers.get(metric, ())})
        if rules:
            result[field] = "rules: " + ", ".join(rules)
    return result


def reference_requests(stack: Mapping, registry: Registry) -> dict | None:
    """``needs_input.reference``: missing fields only, languages first, at
    most :data:`MAX_REFERENCE_FIELDS`; ``None`` when nothing is missing."""
    required = required_fields()
    missing: list[dict] = []
    for language in stack["languages"]:
        entry = registry.languages.get(language)
        for field, why in required.items():
            if entry is None or not _has(entry, field):
                missing.append({"language": language, "field": field, "why": why})
    for item in stack["frameworks"]:
        entry = registry.frameworks.get(item["name"])
        if entry is not None and entry.extends != item["language"]:
            entry = None
        for field, why in required.items():
            if entry is None or not _has(entry, field):
                missing.append(
                    {
                        "framework": item["name"],
                        "extends": item["language"],
                        "field": field,
                        "why": why,
                    }
                )
    if not missing:
        return None
    return {
        "requests": missing[:MAX_REFERENCE_FIELDS],
        "omitted": max(0, len(missing) - MAX_REFERENCE_FIELDS),
        "instructions": REFERENCE_INSTRUCTIONS,
    }


def _has(entry, field: str) -> bool:
    if field.startswith("roles."):
        return bool(entry.roles.get(field.removeprefix("roles.")))
    return bool(entry.fields.get(field))


__all__ = [
    "MAX_CANDIDATES_PER_ROLE",
    "MAX_MANIFESTS",
    "MAX_REFERENCE_FIELDS",
    "REFERENCE_INSTRUCTIONS",
    "MAX_EVIDENCE_REFS_PER_GATE",
    "apply_gate_evaluations",
    "detect_evaluate_gates",
    "detect_pick_gates",
    "detect_stack",
    "gate_requests",
    "reference_requests",
    "required_fields",
]
