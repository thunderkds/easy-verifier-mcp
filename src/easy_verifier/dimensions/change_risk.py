"""The ``change-risk`` dimension (T108, FR-079, FR-080, FR-082; DDR-0014).

It rates a *change*, not the repository: only at ``changes`` and ``worktree``
scope. At ``project`` and ``task`` scope it abstains with a stated reason, and
``score`` leaves it out of a ``project`` payload altogether. Its rating is the
separate ``change_risk`` headline beside ``overall``, never averaged into it.

Slice 1: the change kind (``bugfix``, ``feature``, ``refactor``, ``chore``) is
*detected* from the branch name, the commit subjects and issue references of
the scope's range, and the kinds of the changed files; the most demanding kind
wins and every signal is disclosed. Only the bugfix rule exists yet:
``bugfix_without_regression_test`` counts the test files added or changed in
the scope that match changed source code by the naming correspondence
test-strategy uses, inside one project. Other kinds abstain until T110.

Nothing here runs target code; git is read through ``core.git.run_git`` only.
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterator, Sequence
from pathlib import Path, PurePosixPath

from ..core.git import run_git_text
from ..core.metric_tables import curated_metric_tables
from ..core.metrics import PACK_METRICS, code_kind
from ..core.models import (
    ChangeKind,
    ChangeSignal,
    DimensionContext,
    DimensionDescriptor,
    Excerpt,
    SampledMetric,
    SourceMiss,
    SourceRole,
)
from ..core.redact import redact
from ..core.scope import _EMPTY_TREE, MAX_DIFF_CHARS, _is_contained, _normalize_range
from ..core.structure import context_conventions, convention_values, find_issue_references
from .test_strategy import _MANIFEST_NAMES, _correspondence

NAME = "change-risk"

PURPOSE = (
    "Rate a change (changes or worktree scope), not the repository: detect "
    "whether it is a bugfix, feature, refactor or chore from its branch name, "
    "commit subjects, issue references and file kinds, and check that a bugfix "
    "adds or changes a test matching the changed code. Reported as the separate "
    "change_risk headline, never averaged into the overall."
)

CHANGE_SET = "the change under evaluation (changes or worktree scope)"

ROLES: tuple[SourceRole, ...] = (SourceRole(name=CHANGE_SET, patterns=()),)
"""One pseudo-role, credited when the scope carries a readable change."""

SOURCES_SOUGHT: tuple[str, ...] = tuple(item.name for item in ROLES)

(METRIC,) = PACK_METRICS[NAME]

RATED_SCOPES = frozenset({"changes", "worktree"})

SCOPE_ONLY = "change risk is rated at changes/worktree scope only"
NO_SOURCE = "no changed source code"
LATER_RULES = "rules for {kind} arrive in T110"
ROOT_COMMIT = (
    "the change is a root commit, with no parent to compare it against, so it "
    "is not rated"
)
CLIPPED = (
    f"the diff was clipped at its ceiling of {MAX_DIFF_CHARS} characters, so "
    "the change could not be read completely"
)

KINDS: tuple[str, ...] = ("bugfix", "feature", "refactor", "chore")
"""Most demanding first: a mixed change takes the first kind it has."""

PREFIX_KINDS: dict[str, str] = {
    "fix": "bugfix",
    "bugfix": "bugfix",
    "hotfix": "bugfix",
    "feat": "feature",
    "feature": "feature",
    "refactor": "refactor",
    "chore": "chore",
    "docs": "chore",
    "ci": "chore",
    "build": "chore",
    "deps": "chore",
}
"""One vocabulary for branch prefixes (``fix/…``) and commit subject types
(``fix:``, ``fix(api):``, ``Bugfix/ …``), compared case-insensitively."""

_BRANCH = re.compile(r"^([a-z]+)/")
_SUBJECT = re.compile(r"^\s*([A-Za-z]+)(?:\([^)]*\))?!?\s*[:/]")
_FIX_REFERENCE = re.compile(r"^(?:fix|fixes|fixed)\s", re.IGNORECASE)

MAX_COMMITS = 200
"""Commits of a range whose messages are read, newest first."""

MAX_SIGNALS = 20
"""Signals listed; the rest are counted in ``signals_omitted``."""

MAX_SUBJECT_CHARS = 120

COMMIT_CAP_WARNING = (
    "change-risk read the messages of the newest {cap} commits of the range only"
)

_COMMIT_MARK = "\x1e"
_BODY_MARK = "\x1f"


def collect(context: DimensionContext) -> Iterator[Excerpt]:
    """Assess the change once (the budget may call ``collect`` per tier) and
    record its facts on the context; the evidence is the files read."""
    if not getattr(context, "change_assessed", False):
        context.change_assessed = True
        _assess(context)
    yield from ()


def detect_change_kind(
    *,
    branch: str | None,
    commits: Sequence[tuple[str, str]],
    changed_files: Sequence[str],
    issue_patterns: Sequence[str] | None = None,
    issue_exclusions: Sequence[str] | None = None,
) -> ChangeKind:
    """The change kind and every signal it came from (FR-080), deterministic.

    ``commits`` are ``(sha, full message)`` of the scope's range, newest first
    (none at worktree scope). Signals are listed in evidence order: branch,
    then per commit its subject and its fix references, then file kinds. No
    signal means ``feature``.
    """
    signals: list[ChangeSignal] = []
    if branch:
        match = _BRANCH.match(branch.lower())
        if match and match.group(1) in PREFIX_KINDS:
            signals.append(
                ChangeSignal("branch", redact(branch), PREFIX_KINDS[match.group(1)])
            )
    for sha, message in commits:
        subject = message.strip().split("\n", 1)[0].strip()
        label = f"{sha[:8]} "
        match = _SUBJECT.match(subject)
        if match and match.group(1).lower() in PREFIX_KINDS:
            signals.append(
                ChangeSignal(
                    "commit subject",
                    redact(label + subject[:MAX_SUBJECT_CHARS]),
                    PREFIX_KINDS[match.group(1).lower()],
                )
            )
        for reference in find_issue_references(
            message, issue_patterns, issue_exclusions
        ):
            if _FIX_REFERENCE.match(reference):
                signals.append(
                    ChangeSignal("issue reference", redact(label + reference), "bugfix")
                )
    tables = curated_metric_tables()
    if changed_files and all(code_kind(path, tables) is None for path in changed_files):
        signals.append(
            ChangeSignal(
                "file kinds",
                f"{len(changed_files)} changed file(s), none of them source or "
                "test code (documentation, configuration or lockfiles)",
                "chore",
            )
        )
    found = {signal.kind for signal in signals}
    value = next((kind for kind in KINDS if kind in found), "feature")
    return ChangeKind(
        value=value,
        source="detected",
        signals=tuple(signals[:MAX_SIGNALS]),
        signals_omitted=max(0, len(signals) - MAX_SIGNALS),
    )


def _assess(context: DimensionContext) -> None:
    if context.scope not in RATED_SCOPES:
        _abstain(context, SCOPE_ONLY)
        return
    scope = context.resolved_scope
    if scope is None:
        _abstain(
            context,
            f"not examined: the {context.scope} scope could not be resolved "
            "(its required selector was not supplied)",
        )
        return
    changed = tuple(getattr(scope, "changed_files", ()) or ())
    notes = tuple(getattr(scope, "notes", ()) or ())
    if not changed:
        why = "; ".join(notes) or "the scope has no changed files"
        _abstain(context, redact(f"no change to rate: {why}"))
        return

    repo = Path(context.repo_path)
    ref = getattr(context, "ref", None)
    if scope.kind == "changes" and ref:
        git_range = _normalize_range(repo, ref)
        tip = ref.rsplit("..", 1)[-1].lstrip(".") or "HEAD"
        commits = _commits(context, repo, git_range, ref)
        statuses = _statuses(repo, [git_range] if git_range else None)
        root = bool(git_range and git_range.startswith(_EMPTY_TREE))
    else:
        tip, commits, root = "HEAD", (), False
        statuses = _statuses(repo, ["HEAD"])
    conventions = context_conventions(context)
    context.change_kind = detect_change_kind(
        branch=_branch(repo, tip),
        commits=commits,
        changed_files=changed,
        issue_patterns=convention_values(conventions, "issue_reference_patterns"),
        issue_exclusions=convention_values(conventions, "issue_reference_exclusions"),
    )
    if root:
        _abstain(context, ROOT_COMMIT)
        return
    if any("clipped" in note for note in notes):
        _abstain(context, CLIPPED)
        return
    context.sources_found.append(CHANGE_SET)
    kind = context.change_kind.value
    if kind != "bugfix":
        context.whole_file = (_no_value(LATER_RULES.format(kind=kind)),)
        return
    context.whole_file = (_bugfix_metric(context, repo, changed, statuses),)


def _bugfix_metric(
    context: DimensionContext,
    repo: Path,
    changed: tuple[str, ...],
    statuses: dict[str, str],
) -> SampledMetric:
    """``bugfix_without_regression_test``: test files added or changed in the
    scope that match changed source code (FR-082). A deleted test, or a pure
    rename (``R100``), is not part of the change's code."""
    tables = curated_metric_tables()
    live = [
        path
        for path in changed
        if statuses.get(path, "M") != "D" and statuses.get(path) != "R100"
    ]
    sources = [path for path in live if code_kind(path, tables) == "source"]
    if not sources:
        return _no_value(NO_SOURCE)
    tests = [
        path
        for path in live
        if code_kind(path, tables) == "test" and context.read_source(path) is not None
    ]
    readable = [path for path in sources if context.read_source(path) is not None]
    manifests = _manifest_paths(repo, (*sources, *tests))
    matched, _unmatched = _correspondence((*sources, *manifests, *tests), tuple(tests))
    pairs = {source: matched[source] for source in sources if source in matched}
    hits = sorted({test for found in pairs.values() for test in found})
    method = (
        "a test file counts when it is added or changed in this change and its "
        "name is a conventional test name of a changed source file in the same "
        "project (test-strategy's correspondence; project boundaries read from "
        "manifests anywhere above the files); a deleted test never counts"
    )
    if hits:
        listed = "; ".join(
            f"{redact(source)} -> {', '.join(redact(t) for t in found)}"
            for source, found in sorted(pairs.items())
        )
        return SampledMetric(
            name=METRIC,
            value=len(hits),
            abstention=None,
            computed_from=tuple(redact(path) for path in hits),
            derivation=f"{len(hits)} matched test file(s): {listed}; {method}",
        )
    if not readable:
        return _no_value("no changed source file could be read, so none can be cited")
    unmatched = ", ".join(redact(path) for path in tests) or "none"
    return SampledMetric(
        name=METRIC,
        value=0,
        abstention=None,
        computed_from=tuple(redact(path) for path in readable),
        derivation=(
            f"0 matched test files: none of the test files added or changed "
            f"({unmatched}) matches the {len(sources)} changed source file(s) "
            f"cited; {method}"
        ),
    )


def _abstain(context: DimensionContext, reason: str) -> None:
    context.sources_missing.append(SourceMiss(source=CHANGE_SET, reason=reason))
    context.whole_file = (_no_value(reason),)


def _no_value(reason: str) -> SampledMetric:
    return SampledMetric(
        name=METRIC, value=None, abstention=reason, computed_from=(), derivation=""
    )


def _commits(
    context: DimensionContext, repo: Path, git_range: str | None, ref: str
) -> tuple[tuple[str, str], ...]:
    """``(sha, message)`` of the range the scope diffed, newest first, merges
    left out; a root commit is read alone. Never history outside the range."""
    if git_range is None or git_range.startswith("-"):
        return ()
    if git_range.startswith(_EMPTY_TREE):
        selector = ["-1", ref]
    else:
        # `git diff A...B` diffs from the merge base: the commits are A..B.
        selector = [git_range.replace("...", "..")]
    ok, out, _ = run_git_text(
        repo,
        [
            "log",
            "--no-merges",
            f"--format={_COMMIT_MARK}%H{_BODY_MARK}%B",
            "-n",
            str(MAX_COMMITS),
            *selector,
            "--",
        ],
    )
    if not ok:
        return ()
    commits = tuple(
        tuple(chunk.split(_BODY_MARK, 1))
        for chunk in out.split(_COMMIT_MARK)[1:]
        if _BODY_MARK in chunk
    )
    if len(commits) >= MAX_COMMITS:
        message = COMMIT_CAP_WARNING.format(cap=MAX_COMMITS)
        if message not in context.warnings:
            context.warnings = (*context.warnings, message)
    return commits


def _statuses(repo: Path, selector: list[str] | None) -> dict[str, str]:
    """Path -> ``git diff --name-status -M`` status (``R100`` is a pure
    rename, ``D`` a deletion); empty when git cannot say."""
    if selector is None or selector[0].startswith("-"):
        return {}
    ok, out, _ = run_git_text(repo, ["diff", "--name-status", "-M", *selector, "--"])
    if not ok:
        return {}
    statuses: dict[str, str] = {}
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            statuses[parts[-1]] = parts[0]
    return statuses


def _branch(repo: Path, tip: str) -> str | None:
    """The branch ``tip`` names (``HEAD``: the checked-out one), else ``None``
    -- a commit hash or a detached ``HEAD`` has no branch name."""
    if tip.startswith("-"):
        return None
    ok, out, _ = run_git_text(repo, ["rev-parse", "--symbolic-full-name", tip])
    name = out.strip() if ok else ""
    if name.startswith("refs/heads/"):
        return name[len("refs/heads/") :]
    if name.startswith("refs/remotes/") and name.count("/") >= 3:
        return name.split("/", 3)[3]
    return None


def _manifest_paths(repo: Path, paths: Sequence[str]) -> tuple[str, ...]:
    """Project manifests in any directory above ``paths``, read from the
    working tree (a manifest is rarely in the diff), so a test in another
    project of a monorepo never matches. Only names are listed, nothing is
    read, and a directory resolving outside the repository is skipped."""
    directories = {""}
    for path in paths:
        parts = PurePosixPath(path).parent.parts
        directories.update("/".join(parts[:index]) for index in range(1, len(parts) + 1))
    found: list[str] = []
    for directory in sorted(directories):
        absolute = repo / directory if directory else repo
        if not absolute.is_dir() or not _is_contained(absolute, repo):
            continue
        try:
            names = sorted(os.listdir(absolute))
        except OSError:
            continue
        found.extend(
            f"{directory}/{name}" if directory else name
            for name in names
            if name.lower() in _MANIFEST_NAMES and (absolute / name).is_file()
        )
    return tuple(found)


DESCRIPTOR = DimensionDescriptor(
    name=NAME,
    purpose=PURPOSE,
    sources_sought=SOURCES_SOUGHT,
    collect=collect,
    roles=ROLES,
)
