"""The bespoke ``infrastructure`` evidence dimension (T042, FR-050..052).

Areas #11 infra security (IAM, networking, KMS, secrets), #23 Terraform state,
environment, account and drift, #24 database HA, backups, restore and DR. It
quotes the files of four source roles (Terraform files, Kubernetes manifests,
CloudFormation/Pulumi templates, container configuration), the lines that
break a rule and the first disaster-recovery document; it never judges. Its
seven rule metrics are computed over whole files and stored on
``pack.whole_file`` (the T045 path), so the byte budget never makes them
abstain.

Which files fill a role and which tokens show a wildcard permission, an open
ingress, disabled encryption, a state backend or a database setting are the
generic layer's data (``core/roles.py`` ``GENERIC_INFRASTRUCTURE_FACTS``),
never this module's: IaC files belong to no registry language. Only literal
values count; a setting taken from a variable is reported as not verifiable.
Live drift and whether a backup restores cannot be verified offline: only the
disaster-recovery document is checked.
"""

from __future__ import annotations

import re
from collections.abc import Iterator

from ..core.context import MAX_LINE_CHARS, whole_file_excerpt
from ..core.judge import DOCUMENTATION_RULES
from ..core.models import (
    DimensionContext,
    DimensionDescriptor,
    Excerpt,
    SampledMetric,
    SourceMiss,
    SourceRole,
)
from ..core.redact import redact
from ..core.roles import (
    GENERIC_INFRASTRUCTURE_FACTS,
    _matcher,
    note_context_roles,
    role,
    role_files_in_scope,
)
from . import _code_extract

NAME = "infrastructure"

PURPOSE = (
    "Gather citable evidence about IAM wildcards, internet-open ingress, "
    "storage encryption, Terraform state backends and locking, per-environment "
    "separation and database backup and high-availability settings from "
    "Terraform files, Kubernetes manifests, CloudFormation and Pulumi templates "
    "and container configuration, and whether a disaster-recovery document "
    "exists, without judging them; live drift and whether backups restore "
    "cannot be verified offline and are not examined."
)

TERRAFORM = "terraform-file"
K8S = "k8s-manifest"
CLOUD = "cloud-template"
CONTAINER = "container-config"

ROLES: tuple[SourceRole, ...] = (
    role(TERRAFORM),
    role(K8S),
    role(CLOUD),
    role(CONTAINER),
)
"""Source roles (T026): filled by any matching file in any language."""

SOURCES_SOUGHT: tuple[str, ...] = tuple(item.name for item in ROLES)

_IAC_ROLES = (TERRAFORM, K8S, CLOUD)

MAX_FILES_PER_ROLE = 50
"""Files read per role, shallowest path first, so a monorepo's root files are
never the ones cut; the rest are warned about (NFR-009)."""

PROOF_LINES = 20
"""Lines quoted from each role file: proof it exists and what it is."""

MAX_QUOTED = 10
"""Rule-breaking lines quoted, per metric."""

MAX_BLOCK_LINES = 400
"""Lines followed from a Terraform block header to its closing brace."""

LOOKBACK = 15
"""Lines searched above an open CIDR for its ingress/egress direction, and
above a lone ``- "*"`` list item for its key."""

MAX_EXAMPLES = 5
"""Paths named in a derivation."""

CAP_WARNING = (
    "{count} {role} files exceed the cap of {cap}; the shallowest are read, so "
    "metrics over this role describe only those"
)

UNRESOLVED_SCOPE_WARNING = (
    "The {scope} scope could not be resolved, most likely because its required "
    "selector was not supplied. No evidence was gathered; this pack is not "
    "whole-repository output."
)

UNRESOLVED_SCOPE_REASON = (
    "not examined: the {scope} scope could not be resolved "
    "(its required selector was not supplied)"
)


def _regex(key: str) -> re.Pattern[str]:
    return re.compile(
        "|".join(v for item in GENERIC_INFRASTRUCTURE_FACTS[key] for v in item.value)
    )


_WILDCARD = _regex("wildcard_iam")
_WILDCARD_KEY = _regex("wildcard_list_key")
_LONE_STAR = re.compile(r"""^\s*-\s*['"]?\*['"]?\s*$""")
_OPEN_CIDR = _regex("open_cidr")
_EGRESS = _regex("egress_marker")
_INGRESS = _regex("ingress_marker")
_UNENCRYPTED = _regex("unencrypted_storage")
_ENCRYPTION_RESOURCE = _regex("encryption_required_resource")
_ENCRYPTION_KEY = _regex("encryption_key")
_REMOTE_BACKEND = _regex("remote_backend")
_S3_BACKEND = _regex("s3_backend")
_S3_LOCK = _regex("s3_lock")
_ENV_PATH = _matcher(
    tuple(v for item in GENERIC_INFRASTRUCTURE_FACTS["environment_paths"]
          for v in item.value)
)
_ENV_TOKEN = _regex("environment_token")
_DATABASE = _regex("database_resource")
_BACKUP = _regex("database_backup")
_BACKUP_KEY = _regex("database_backup_key")
_HA = _regex("database_ha")
_HA_KEY = _regex("database_ha_key")
_LITERAL = re.compile(r"""\s*(?:["'\d\[{]|true|false)""")
"""A value that starts as a literal; anything else (``var.x``, ``local.y``,
a function call) is not verifiable offline."""

_PRESENCE = frozenset(
    {
        "terraform_locked_remote_state_missing",
        "terraform_environment_separation_missing",
    }
)


def collect(context: DimensionContext) -> Iterator[Excerpt]:
    """Yield rule-breaking lines, the DR document and role files, lazily; the
    metrics are stored before the first yield."""
    resolved_scope = context.resolved_scope
    if resolved_scope is None and context.scope != "project":
        message = UNRESOLVED_SCOPE_WARNING.format(scope=context.scope)
        if message not in context.warnings:
            context.warnings = (*context.warnings, message)
        reason = UNRESOLVED_SCOPE_REASON.format(scope=context.scope)
        for source in SOURCES_SOUGHT:
            context.sources_missing.append(SourceMiss(source=source, reason=reason))
        return

    facts = getattr(context, "infrastructure_facts", None)
    if facts is None:
        facts = _facts(context)
        context.infrastructure_facts = facts
    for key in ("wildcard", "open", "unencrypted"):
        for path, lines, number in facts[key][:MAX_QUOTED]:
            excerpt = _code_extract._excerpt(path, lines, number - 1, number - 1)
            if excerpt is not None:
                yield excerpt
    for path, text in facts["docs"] + [
        item for name in SOURCES_SOUGHT for item in facts["files"][name]
    ]:
        excerpt = whole_file_excerpt(path, "\n".join(text.splitlines()[:PROOF_LINES]))
        if excerpt is not None:
            yield excerpt


def _facts(context: DimensionContext) -> dict:
    """Read every input once and store the seven metrics on
    ``context.whole_file``; idempotent across the budget's tier passes."""
    scope = context.resolved_scope
    scope_files = tuple(getattr(scope, "files", ()) or ())
    kind = getattr(scope, "kind", None)
    whole_repo = scope is None or kind == "project"
    scope_set = frozenset(scope_files)

    files: dict[str, list[tuple[str, str]]] = {}
    seen: set[str] = set()
    note_context_roles(context, SOURCES_SOUGHT, scope_set, kind, whole_repo)
    for name in SOURCES_SOUGHT:
        paths = context.role_files.get(name, ())
        in_bounds = role_files_in_scope(name, paths, scope_set, whole_repo)
        if paths and not in_bounds:
            context.sources_missing.append(
                SourceMiss(source=name, reason=f"not in the resolved {kind} scope")
            )
        ranked = sorted(in_bounds, key=lambda p: (p.count("/"), p))
        if len(ranked) > MAX_FILES_PER_ROLE:
            message = CAP_WARNING.format(
                count=len(ranked), role=name, cap=MAX_FILES_PER_ROLE
            )
            context.capped[name] = (len(ranked), MAX_FILES_PER_ROLE)
            if message not in context.warnings:
                context.warnings = (*context.warnings, message)
        files[name] = []
        for path in ranked[:MAX_FILES_PER_ROLE]:
            text = context.read_source(path)
            if text is not None and path not in seen:
                seen.add(path)
                files[name].append((path, text))

    # The documentation rule is checked against the files this pack read, so
    # the first readable in-scope match is read here (T041 precedent).
    docs: list[tuple[str, str]] = []
    for rule in DOCUMENTATION_RULES.get(NAME, ()):
        match = _matcher(rule.patterns)
        for path in sorted(p for p in scope_files if match(p)):
            text = context.read_source(path)
            if text is not None:
                docs.append((path, text))
                break

    iac = [item for name in _IAC_ROLES for item in files[name]]
    terraform = files[TERRAFORM]
    scan = _scan(iac)
    state = _state(terraform)
    databases = _databases(terraform)

    context.whole_file = (
        _count_metric(
            "iac_wildcard_iam_observed", scan["wildcard"], iac,
            "line(s) grant a \"*\" IAM action or resource or RBAC verb, "
            "resource or API group",
        ),
        _count_metric(
            "iac_open_ingress_observed", scan["open"], iac,
            "ingress rule source(s) are any address on the internet (an egress rule is "
            "not counted)",
        ),
        _count_metric(
            "iac_unencrypted_storage_observed",
            scan["unencrypted"] + databases["unencrypted"], iac,
            "storage setting(s) switch encryption off, or an RDS/EBS resource "
            "never sets it (its default is off)",
            unresolved=databases["encryption_unresolved"],
        ),
        state["backend"],
        _environment_metric(terraform, scan["environment"]),
        _database_metric("database_backup_unconfigured", databases, "backup"),
        _database_metric("database_ha_unconfigured", databases, "ha"),
    )
    if not whole_repo:
        # Presence is a repository property: a narrow scope can show it, but
        # its absence among the scope's files is not the repository's.
        context.whole_file = tuple(
            _metric(
                m.name,
                abstention=f"not found among the {len(scope_files)} file(s) of the "
                f"{kind} scope; whether the repository has it is judged only under "
                "project scope",
            )
            if m.value == 1 and m.name in _PRESENCE
            else m
            for m in context.whole_file
        )
    return {
        "files": files,
        "docs": docs,
        "wildcard": scan["wildcard"],
        "open": scan["open"],
        "unencrypted": scan["unencrypted"] + databases["unencrypted"],
    }


def _lines(text: str) -> list[str]:
    return text.splitlines()


def _scan(items) -> dict[str, list]:
    """Line rules over every IaC file. Each search is bounded to the excerpt
    line cap, so an adversarial long line cannot make it expensive."""
    hits: dict[str, list] = {"wildcard": [], "open": [], "unencrypted": []}
    environment: list[str] = []
    for path, text in items:
        lines = _lines(text)
        for number, line in enumerate(lines, 1):
            if _WILDCARD.search(line, 0, MAX_LINE_CHARS) or (
                _LONE_STAR.match(line, 0, MAX_LINE_CHARS)
                and _list_key(lines, number - 1)
            ):
                hits["wildcard"].append((path, lines, number))
            if _OPEN_CIDR.search(line, 0, MAX_LINE_CHARS) and not _egress(
                lines, number - 1
            ):
                hits["open"].append((path, lines, number))
            if _UNENCRYPTED.search(line, 0, MAX_LINE_CHARS):
                hits["unencrypted"].append((path, lines, number))
            if _ENV_TOKEN.search(line, 0, MAX_LINE_CHARS):
                environment.append(path)
    hits["environment"] = environment
    return hits


def _list_key(lines: list[str], index: int) -> bool:
    """The key of the YAML block list holding a lone ``- "*"`` item."""
    for j in range(index - 1, max(-1, index - LOOKBACK), -1):
        if lines[j].lstrip().startswith("-"):
            continue
        return bool(_WILDCARD_KEY.match(lines[j], 0, MAX_LINE_CHARS))
    return False


def _egress(lines: list[str], index: int) -> bool:
    """The nearest direction word at or above the line names egress."""
    for j in range(index, max(-1, index - LOOKBACK), -1):
        line = lines[j][:MAX_LINE_CHARS]
        egress = [m.start() for m in _EGRESS.finditer(line)]
        ingress = [m.start() for m in _INGRESS.finditer(line)]
        if egress or ingress:
            return max(egress, default=-1) > max(ingress, default=-1)
    return False


def _block(lines: list[str], start: int) -> list[str]:
    """From a block header to its closing brace (brace count, bounded)."""
    depth = 0
    opened = False
    end = min(len(lines), start + MAX_BLOCK_LINES)
    for j in range(start, end):
        depth += lines[j].count("{") - lines[j].count("}")
        opened = opened or "{" in lines[j]
        if opened and depth <= 0:
            return lines[start : j + 1]
    return lines[start:end]


def _state(terraform) -> dict:
    name = "terraform_locked_remote_state_missing"
    if not terraform:
        return {"backend": _no_terraform(name)}
    locked: list[str] = []
    unlocked: list[str] = []
    for path, text in terraform:
        lines = _lines(text)
        for index, line in enumerate(lines):
            if not _REMOTE_BACKEND.search(line, 0, MAX_LINE_CHARS):
                continue
            if _S3_BACKEND.search(line, 0, MAX_LINE_CHARS) and not any(
                _S3_LOCK.search(ln, 0, MAX_LINE_CHARS) for ln in _block(lines, index)
            ):
                unlocked.append(path)
            else:
                locked.append(path)
    paths = [p for p, _t in terraform]
    if locked:
        derivation = (
            f"a remote backend with state locking is declared in {_paths(locked)}"
        )
    elif unlocked:
        derivation = (
            f"a backend that locks only with a lock setting (the generic layer's "
            f"s3_lock) states none in "
            f"{_paths(unlocked)}, so state is not locked"
        )
    else:
        derivation = (
            f"no remote backend or cloud block in the {len(paths)} Terraform "
            "file(s) read, so state is local"
        )
    return {
        "backend": _metric(
            name, 0 if locked else 1, locked or unlocked or paths, derivation
        )
    }


def _environment_metric(terraform, tokens) -> SampledMetric:
    name = "terraform_environment_separation_missing"
    if not terraform:
        return _no_terraform(name)
    paths = [p for p, _t in terraform]
    by_path = [p for p in paths if _ENV_PATH(p)]
    found = list(dict.fromkeys(by_path + [p for p in tokens if p in paths]))
    return _metric(
        name,
        0 if found else 1,
        found or paths,
        (
            "per-environment Terraform files or terraform.workspace in: "
            + _paths(found)
            if found
            else f"no environment folder, per-environment tfvars or "
            f"terraform.workspace in the {len(paths)} Terraform file(s) read"
        ),
    )


def _databases(terraform) -> dict:
    """Database and encryption-required resource blocks, with what each states."""
    out: dict = {
        "blocks": [],
        "backup": [],
        "ha": [],
        "backup_unresolved": [],
        "ha_unresolved": [],
        "unencrypted": [],
        "encryption_unresolved": [],
    }
    for path, text in terraform:
        lines = _lines(text)
        for index, line in enumerate(lines):
            database = _DATABASE.search(line, 0, MAX_LINE_CHARS)
            encrypted = _ENCRYPTION_RESOURCE.search(line, 0, MAX_LINE_CHARS)
            if not (database or encrypted):
                continue
            block = [ln[:MAX_LINE_CHARS] for ln in _block(lines, index)]
            if encrypted:
                keys = [k for ln in block for k in _ENCRYPTION_KEY.finditer(ln)]
                if not keys:
                    out["unencrypted"].append((path, lines, index + 1))
                elif not all(_LITERAL.match(k.string, k.end()) for k in keys):
                    out["encryption_unresolved"].append(path)
            if database:
                out["blocks"].append(path)
                for key, flag, flag_key in (
                    ("backup", _BACKUP, _BACKUP_KEY),
                    ("ha", _HA, _HA_KEY),
                ):
                    if any(flag.search(ln) for ln in block):
                        continue
                    keys = [k for ln in block for k in flag_key.finditer(ln)]
                    literal = all(_LITERAL.match(k.string, k.end()) for k in keys)
                    if keys and not literal:
                        out[f"{key}_unresolved"].append(path)
                    else:
                        out[key].append(path)
    return out


def _database_metric(name: str, databases: dict, key: str) -> SampledMetric:
    blocks = databases["blocks"]
    if not blocks:
        return _metric(
            name,
            abstention="no managed database resource (the generic layer's "
            "database_resource types) in the Terraform files read, so there is "
            "no database whose settings could be examined",
        )
    missing = databases[key]
    unresolved = databases[f"{key}_unresolved"]
    what = (
        "backup retention, point-in-time recovery or snapshot setting"
        if key == "backup"
        else "multi-AZ, regional or high-availability setting"
    )
    return _metric(
        name,
        len(missing),
        blocks,
        f"{len(missing)} of {len(blocks)} database resource(s) state no {what}"
        + (f": {_paths(missing)}" if missing else "")
        + _unresolved_note(unresolved),
    )


def _count_metric(name, hits, files, what, unresolved=()) -> SampledMetric:
    if not files:
        return _metric(
            name,
            abstention="no Terraform file, Kubernetes manifest or CloudFormation/"
            "Pulumi template in scope, so there is no infrastructure code to "
            "examine",
        )
    paths = [p for p, _l, _n in hits]
    return _metric(
        name,
        len(hits),
        [p for p, _t in files],
        f"{len(hits)} {what} in the {len(files)} IaC file(s) read"
        + (f": {_paths(dict.fromkeys(paths))}" if paths else "")
        + "; literal values only"
        + _unresolved_note(unresolved),
    )


def _unresolved_note(paths) -> str:
    if not paths:
        return ""
    return (
        f"; {len(paths)} setting(s) come from a variable or expression and are "
        f"not verifiable offline: {_paths(dict.fromkeys(paths))}"
    )


def _no_terraform(name: str) -> SampledMetric:
    return _metric(
        name,
        abstention="no Terraform file in scope, so there is no Terraform state "
        "or layout to examine",
    )


def _paths(paths) -> str:
    paths = list(paths)
    shown = ", ".join(paths[:MAX_EXAMPLES])
    extra = len(paths) - MAX_EXAMPLES
    return shown + (f" and {extra} more" if extra > 0 else "")


def _metric(name, value=None, refs=(), derivation="", abstention=None) -> SampledMetric:
    return SampledMetric(
        name=name,
        value=value,
        abstention=None if abstention is None else redact(abstention),
        computed_from=tuple(sorted({redact(path) for path in refs})),
        derivation=redact(derivation),
    )


DESCRIPTOR = DimensionDescriptor(
    name=NAME,
    purpose=PURPOSE,
    sources_sought=SOURCES_SOUGHT,
    collect=collect,
    roles=ROLES,
)
