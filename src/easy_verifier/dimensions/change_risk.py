"""The ``change-risk`` dimension (T108, FR-079, FR-080, FR-082; DDR-0014).

It rates a *change*, not the repository: only at ``changes`` and ``worktree``
scope. At ``project`` and ``task`` scope it abstains with a stated reason, and
``score`` leaves it out of a ``project`` payload altogether. Its rating is the
separate ``change_risk`` headline beside ``overall``, never averaged into it.

Slice 1: the change kind (``bugfix``, ``feature``, ``refactor``, ``chore``) is
*detected* from the branch name, the commit subjects and issue references of
the scope's range, and the kinds of the changed files; the most demanding kind
wins and every signal is disclosed. Only the active kind's rules are
evaluated (T110): a bugfix needs a matched test (``bugfix_without_regression_test``),
a feature leaves few changed source files without one
(``new_code_without_test_share``), a refactor deletes no test
(``refactor_tests_deleted``) and leaves few changed source files without a
covering test anywhere in the repository (``refactor_uncovered_share``); a
chore has no rule. Refactor matching is the naming correspondence
test-strategy uses, inside one project.

Slice 2 (T112, FR-084): for a bugfix or feature, a changed test is *matched*
to a changed source file when it references one of that file's changed
symbols as a whole word (``basis: "symbol"``) or, failing that, when the names
correspond (``basis: "name"``). The calling agent may confirm, reject or add
pairs (``agent_input.test_pairs``); the rules use the final pair set.

Nothing here runs target code; git is read through ``core.git.run_git`` only.
"""

from __future__ import annotations

import dataclasses
import os
import re
from collections.abc import Iterator, Sequence
from pathlib import Path, PurePosixPath

from ..core.git import run_git_text
from ..core.judge import NOT_THIS_KIND
from ..core.metric_tables import curated_metric_tables
from ..core.metrics import PACK_METRICS, code_kind
from ..core.models import (
    ChangeKind,
    ChangeSignal,
    DimensionContext,
    DimensionDescriptor,
    Excerpt,
    MatchedPair,
    PairFacts,
    SampledMetric,
    SourceMiss,
    SourceRole,
)
from ..core.redact import redact
from ..core.scope import _EMPTY_TREE, MAX_DIFF_CHARS, _is_contained, _normalize_range
from ..core.structure import (
    context_conventions,
    convention_values,
    find_issue_references,
)
from ..core.tokens import MAX_LINE_CHARS
from .blast_radius import _IDENT, _declared_name, _diff_files
from .test_strategy import (
    _MANIFEST_NAMES,
    _correspondence,
    _is_ancestor,
    _manifest_dirs,
)

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

METRICS = PACK_METRICS[NAME]
METRIC, FEATURE_METRIC, DELETED_METRIC, UNCOVERED_METRIC = METRICS

RATED_SCOPES = frozenset({"changes", "worktree"})

SCOPE_ONLY = "change risk is rated at changes/worktree scope only"
NO_SOURCE = "no changed source code"
CHORE = "chore: no test expectation"
UNREADABLE = "no changed source file could be read, so none can be cited"
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

MIN_SYMBOL_CHARS = 4
COMMON_SYMBOLS = frozenset(
    {
        "__init__",
        "call",
        "config",
        "constructor",
        "create",
        "data",
        "default",
        "delete",
        "handle",
        "handler",
        "index",
        "init",
        "item",
        "items",
        "list",
        "main",
        "name",
        "render",
        "self",
        "setup",
        "start",
        "stop",
        "teardown",
        "test",
        "this",
        "type",
        "update",
        "value",
    }
)
"""A changed symbol shorter than :data:`MIN_SYMBOL_CHARS` characters
(``get``, ``run``) or in this list is too common to pair a test on its own
(T112 edge rule); compared case-insensitively."""

MAX_SYMBOLS_PER_FILE = 50
"""Changed symbols read per source file, in name order."""

AGENT_CHECKS = (
    "agent_input.test_pairs entries answer the proposals: a rejected pair "
    "stops counting, an added one must cite an existing line of a live "
    "changed test in the same project"
)


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
    # T109 (FR-081): the calling agent's validated answer replaces the
    # detected value; the signals stay disclosed beside it.
    confirmed = getattr(context, "confirmed_kind", None)
    if confirmed is not None:
        context.change_kind = dataclasses.replace(
            context.change_kind, value=confirmed, source="confirmed"
        )
    if root:
        _abstain(context, ROOT_COMMIT)
        return
    if any("clipped" in note for note in notes):
        _abstain(context, CLIPPED)
        return
    context.sources_found.append(CHANGE_SET)
    kind = context.change_kind.value
    if kind == "chore":
        context.whole_file = tuple(_no_value(CHORE, name) for name in METRICS)
        return
    if kind in ("bugfix", "feature"):
        name = METRIC if kind == "bugfix" else FEATURE_METRIC
        sources, tests, readable = _changed_code(context, changed, statuses)
        if not sources:
            own = (_no_value(NO_SOURCE, name),)
        else:
            pairs, context.test_pairs = _pair_facts(
                context, repo, scope, statuses, sources, tests
            )
            metric = _bugfix_metric if kind == "bugfix" else _feature_metric
            own = (metric(sources, tests, readable, pairs, context.test_pairs),)
    else:
        own = _refactor_metrics(context, repo, changed, statuses)
    # Another kind's rule is not evaluated: the judge drops it (T110).
    by_name = {item.name: item for item in own}
    context.whole_file = tuple(
        by_name.get(name) or _no_value(NOT_THIS_KIND, name) for name in METRICS
    )


def _changed_code(
    context: DimensionContext, changed: tuple[str, ...], statuses: dict[str, str]
) -> tuple[list[str], list[str], list[str]]:
    """Changed source files, readable changed test files, and the readable
    changed sources. A deleted file, or a pure rename (``R100``), is not part
    of the change's code."""
    tables = curated_metric_tables()
    live = [
        path
        for path in changed
        if statuses.get(path, "M") != "D" and statuses.get(path) != "R100"
    ]
    sources = [path for path in live if code_kind(path, tables) == "source"]
    tests = [
        path
        for path in live
        if code_kind(path, tables) == "test" and context.read_source(path) is not None
    ]
    readable = [path for path in sources if context.read_source(path) is not None]
    return sources, tests, readable


def _pairs(pairs: dict[str, tuple[str, ...]]) -> str:
    return "; ".join(
        f"{redact(source)} -> {', '.join(redact(t) for t in found)}"
        for source, found in sorted(pairs.items())
    ) or "none"


def _listed(paths: Sequence[str]) -> str:
    return ", ".join(redact(path) for path in paths) or "none"


def _refactor_metrics(
    context: DimensionContext,
    repo: Path,
    changed: tuple[str, ...],
    statuses: dict[str, str],
) -> tuple[SampledMetric, ...]:
    """``refactor_tests_deleted`` (test files the diff deletes; a rename git
    detects is not a deletion) and ``refactor_uncovered_share`` (changed source
    files with no covering test anywhere in the repository's working tree,
    changed or not, in the same project; a deleted test never covers)."""
    tables = curated_metric_tables()
    sources, tests, readable = _changed_code(context, changed, statuses)
    deleted = sorted(
        path
        for path, status in statuses.items()
        if status == "D" and code_kind(path, tables) == "test"
    )
    resolution = getattr(context, "role_resolution", None)
    walked = tuple(getattr(resolution, "walked", ()) or ())
    truncated = (
        "; the repository walk stopped at its file cap, so tests beyond it were "
        "not searched"
        if getattr(resolution, "walk_truncated", False)
        else ""
    )

    cited = readable or [
        path
        for path in changed
        if statuses.get(path) != "D" and context.read_source(path) is not None
    ]
    if cited:
        deleted_metric = SampledMetric(
            name=DELETED_METRIC,
            value=len(deleted),
            abstention=None,
            computed_from=tuple(redact(path) for path in cited),
            derivation=(
                f"{len(deleted)} test file(s) deleted by the change: "
                f"{_listed(deleted)} (git diff --name-status -M: a rename git "
                "detects is not a deletion); cited are the changed files read"
            ),
        )
    else:
        deleted_metric = _no_value(
            f"no changed file could be read, so the {len(deleted)} deleted test "
            f"file(s) ({_listed(deleted)}) cannot be cited",
            DELETED_METRIC,
        )

    if not sources:
        return deleted_metric, _no_value(NO_SOURCE, UNCOVERED_METRIC)
    if not readable:
        return deleted_metric, _no_value(UNREADABLE, UNCOVERED_METRIC)
    gone = set(deleted)
    repo_tests = sorted(
        {
            *(
                path
                for path in walked
                if code_kind(path, tables) == "test" and path not in gone
            ),
            *tests,
        }
    )
    manifests = sorted(
        {
            *(
                path
                for path in walked
                if PurePosixPath(path).name.lower() in _MANIFEST_NAMES
            ),
            *_manifest_paths(repo, sources),
        }
    )
    matched, _unmatched = _correspondence(
        (*sources, *manifests, *repo_tests), tuple(repo_tests)
    )
    pairs = {source: matched[source] for source in sources if source in matched}
    uncovered = [source for source in sources if source not in pairs]
    uncovered_metric = SampledMetric(
        name=UNCOVERED_METRIC,
        value=len(uncovered) / len(sources),
        abstention=None,
        computed_from=tuple(
            redact(path)
            for path in ([p for p in uncovered if p in readable] or readable)
        ),
        derivation=(
            f"{len(uncovered)} of {len(sources)} changed source file(s) have no "
            f"covering test in the repository: {_listed(uncovered)}; covered: "
            f"{_pairs(pairs)}; a test covers when its name is a conventional test "
            "name of the source file in the same project, wherever it sits in the "
            "working tree and whether or not the change touched it; a deleted "
            f"test never covers{truncated}"
        ),
    )
    return deleted_metric, uncovered_metric


def _feature_metric(
    sources: list[str],
    tests: list[str],
    readable: list[str],
    pairs: tuple[tuple[str, str], ...],
    facts: PairFacts,
) -> SampledMetric:
    """``new_code_without_test_share``: the share of changed source files
    with no matched test in the final pair set (FR-082, FR-084)."""
    if not readable:
        return _no_value(UNREADABLE, FEATURE_METRIC)
    covered = {source for source, _test in pairs}
    uncovered = [source for source in sources if source not in covered]
    hits = sorted({test for _source, test in pairs})
    cited = [path for path in uncovered if path in readable] or hits or readable
    return SampledMetric(
        name=FEATURE_METRIC,
        value=len(uncovered) / len(sources),
        abstention=None,
        computed_from=tuple(redact(path) for path in cited),
        derivation=(
            f"{len(uncovered)} of {len(sources)} changed source file(s) have no "
            f"matched test: {_listed(uncovered)}; matched: "
            f"{_pair_list(facts.pairs)}; {PAIR_METHOD}{_pair_notes(facts)}"
        ),
    )


def _bugfix_metric(
    sources: list[str],
    tests: list[str],
    readable: list[str],
    pairs: tuple[tuple[str, str], ...],
    facts: PairFacts,
) -> SampledMetric:
    """``bugfix_without_regression_test``: test files added or changed in the
    scope matched to changed source code in the final pair set (FR-082,
    FR-084). A deleted test, or a pure rename (``R100``), is not part of the
    change's code."""
    hits = sorted({test for _source, test in pairs})
    if hits:
        return SampledMetric(
            name=METRIC,
            value=len(hits),
            abstention=None,
            computed_from=tuple(redact(path) for path in hits),
            derivation=(
                f"{len(hits)} matched test file(s): {_pair_list(facts.pairs)}; "
                f"{PAIR_METHOD}{_pair_notes(facts)}"
            ),
        )
    if not readable:
        return _no_value(UNREADABLE)
    unmatched = ", ".join(redact(path) for path in tests) or "none"
    return SampledMetric(
        name=METRIC,
        value=0,
        abstention=None,
        computed_from=tuple(redact(path) for path in readable),
        derivation=(
            f"0 matched test files: none of the test files added or changed "
            f"({unmatched}) matches the {len(sources)} changed source file(s) "
            f"cited; {PAIR_METHOD}{_pair_notes(facts)}"
        ),
    )


PAIR_METHOD = (
    "a test file counts when it is added or changed in this change and "
    "references one of the source file's changed symbols as a whole word "
    "(basis symbol: declarations on added or removed lines and the enclosing "
    "declaration of each changed line, read with the registry's "
    "public_declarations pattern; same project by manifest; symbols under "
    f"{MIN_SYMBOL_CHARS} characters or common words never pair, nor does a "
    "name the test declares itself), else when its name is a conventional "
    "test name of the source file in the same project (basis name, "
    "test-strategy's correspondence); the calling agent may confirm, reject "
    "or add pairs (agent_input.test_pairs); a deleted test never counts"
)


def _pair_list(pairs: Sequence[MatchedPair]) -> str:
    """``source -> test (basis[ symbol][ at ref], status)``, one per pair."""
    return (
        "; ".join(
            f"{item.source} -> {item.test} ({item.basis}"
            + (f" {item.symbol}" if item.symbol else "")
            + (f" at {item.ref}" if item.ref else "")
            + f", {item.status})"
            for item in pairs
        )
        or "none"
    )


def _pair_notes(facts: PairFacts) -> str:
    notes = ""
    if facts.dropped:
        notes += f"; rejected by the agent: {_pair_list(facts.dropped)}"
    if facts.rejected:
        notes += (
            f"; {len(facts.rejected)} invalid agent_input.test_pairs entr"
            f"{'y' if len(facts.rejected) == 1 else 'ies'} ignored"
        )
    if facts.no_symbols:
        notes += (
            "; no changed symbols read for "
            f"{_listed(facts.no_symbols)} (no public_declarations pattern for "
            "the language, or no diff read), so only names match there"
        )
    return notes


def _pair_facts(
    context: DimensionContext,
    repo: Path,
    scope: object,
    statuses: dict[str, str],
    sources: list[str],
    tests: list[str],
) -> tuple[tuple[tuple[str, str], ...], PairFacts]:
    """The final ``(source, test)`` pairs (raw paths, for the rules) and the
    redacted :class:`PairFacts` for the payload (T112, FR-084)."""
    tables = curated_metric_tables()
    manifests = _manifest_paths(repo, (*sources, *tests))
    named, _unmatched = _correspondence((*sources, *manifests, *tests), tuple(tests))
    projects = _manifest_dirs(manifests)
    diff = _diff_text(repo, scope)
    items = {
        item["path"]: item
        for item in (_diff_files(diff) if diff else ())
        if not item["secret"]
    }
    symbols, no_symbols = _symbol_map(context, scope, sources, items, diff is not None)
    texts = {test: context.peek_source(test) or "" for test in tests}
    references = {
        test: _references(
            texts[test],
            tables.public_declarations.get(PurePosixPath(test).suffix),
            {
                number
                for sign, number, _text, _hunk in items.get(test, {}).get("lines", ())
                if sign == "+"
            },
        )
        for test in tests
    }

    proposals: dict[tuple[str, str], MatchedPair] = {}
    for source in sorted(sources):
        for test in sorted(tests):
            found = None
            if _project(source, projects) == _project(test, projects):
                found = min(
                    (
                        (*references[test][name], name)
                        for name in symbols[source]
                        if name in references[test]
                    ),
                    default=None,
                )
            if found is not None:
                _rank, line, name = found
                proposals[source, test] = MatchedPair(
                    source, test, "symbol", name, f"{test}:{line}", "detected"
                )
            elif test in named.get(source, ()):
                proposals[source, test] = MatchedPair(
                    source, test, "name", None, None, "detected"
                )

    deleted = {
        path
        for path, status in statuses.items()
        if status == "D" and code_kind(path, tables) == "test"
    }
    answers = getattr(context, "pair_answers", None)
    final = dict(proposals)
    dropped: list[MatchedPair] = []
    rejected: list[tuple[int, str]] = list(answers[1]) if answers else []
    applied = False
    seen: set[tuple[str, str]] = set()
    for index, entry in answers[0] if answers else ():
        source, test, verdict = entry["source"], entry["test"], entry["verdict"]
        reason = redact(entry["reason"])
        key = (source, test)
        label = f"test_pairs[{index}]"
        problem = None
        if key in seen:
            problem = "a duplicate answer for this pair; the first one counts"
        elif source not in sources:
            problem = "source is not a live source file changed by this change"
        elif test in deleted:
            problem = "test is deleted by this change, so it never matches"
        elif test not in tests:
            problem = "test is not a readable test file added or changed by this change"
        elif key in proposals:
            if verdict == "reject":
                final.pop(key)
                dropped.append(
                    dataclasses.replace(
                        proposals[key], status="rejected", reason=reason
                    )
                )
            else:
                final[key] = dataclasses.replace(
                    proposals[key], status="confirmed", reason=reason
                )
        elif verdict == "reject":
            problem = "not a proposed pair, so there is nothing to reject"
        elif _project(source, projects) != _project(test, projects):
            problem = "source and test are in different projects"
        elif "ref" not in entry:
            problem = "a pair that was not proposed needs a ref (test-path:line)"
        elif (line := _ref_line(entry["ref"], test, texts[test])) is None:
            problem = "ref does not name an existing line of that test (test-path:line)"
        else:
            final[key] = MatchedPair(
                source, test, "agent", None, f"{test}:{line}", "added", reason
            )
        if problem is None:
            seen.add(key)
            applied = True
        else:
            rejected.append((index, f"{label}: {problem}"))

    ordered = [final[key] for key in sorted(final)]
    paired_tests = {item.test for item in ordered}
    paired_sources = {item.source for item in ordered}
    facts = PairFacts(
        proposals=tuple(_redacted(proposals[key]) for key in sorted(proposals)),
        pairs=tuple(_redacted(item) for item in ordered),
        dropped=tuple(_redacted(item) for item in dropped),
        rejected=tuple(
            message for _index, message in sorted(rejected, key=lambda x: x[0])
        ),
        unpaired_tests=tuple(
            redact(path) for path in sorted(tests) if path not in paired_tests
        ),
        unpaired_sources=tuple(
            redact(path) for path in sorted(sources) if path not in paired_sources
        ),
        no_symbols=tuple(redact(path) for path in no_symbols),
        answered=applied,
    )
    return tuple(sorted(final)), facts


def _redacted(item: MatchedPair) -> MatchedPair:
    ref = item.ref
    if ref is not None:
        path, _, line = ref.rpartition(":")
        ref = f"{redact(path)}:{line}"
    return dataclasses.replace(
        item, source=redact(item.source), test=redact(item.test), ref=ref
    )


def _ref_line(ref: str, test: str, text: str) -> int | None:
    """The line ``ref`` (``test-path:line``) names in ``test``, if it exists."""
    path, _, number = ref.rpartition(":")
    if path != test or not number.isdigit():
        return None
    line = int(number)
    return line if 1 <= line <= len(text.splitlines()) else None


def _project(path: str, projects: frozenset[str]) -> str:
    """The deepest directory above ``path`` holding a project manifest
    (the repository root when none does)."""
    directory = str(PurePosixPath(path).parent).strip(".")
    return max(
        (item for item in projects if _is_ancestor(item, directory)),
        key=len,
        default="",
    )


def changed_symbols(item: dict, pattern: re.Pattern[str]) -> tuple[str, ...]:
    """The names one file's diff touches (T112): a declaration on an added or
    removed line, and the enclosing declaration of every other changed line
    -- the nearest declaration above it in its hunk, else the one git names
    in the hunk header. A hunk with neither yields nothing."""
    enclosing = {
        hunk: _declared_name(pattern, text)
        for hunk, text in item.get("headers", {}).items()
    }
    found: set[str] = set()
    for sign, _number, text, hunk in item["lines"]:
        name = _declared_name(pattern, text)
        if name is not None:
            enclosing[hunk] = name
        if sign != " " and (name or enclosing.get(hunk)):
            found.add(name or enclosing[hunk])
    return tuple(sorted(found))


def _symbol_map(
    context: DimensionContext,
    scope: object,
    sources: list[str],
    items: dict[str, dict],
    diff_read: bool,
) -> tuple[dict[str, tuple[str, ...]], list[str]]:
    """Changed symbols per changed source file that may pair (long enough,
    not common), and the files that yield none because their language has no
    ``public_declarations`` pattern or no diff of them was read."""
    tables = curated_metric_tables()
    symbols: dict[str, tuple[str, ...]] = {}
    missing: list[str] = []
    for source in sources:
        pattern = tables.public_declarations.get(PurePosixPath(source).suffix)
        item = items.get(source)
        if item is None and diff_read and scope.kind != "changes":
            # Worktree: an untracked file is not in `git diff HEAD`; every one
            # of its lines is an added line.
            text = context.peek_source(source)
            if text is not None:
                item = {
                    "lines": [
                        ("+", number, line, 1)
                        for number, line in enumerate(text.splitlines(), 1)
                    ]
                }
        if pattern is None or item is None:
            missing.append(source)
            symbols[source] = ()
            continue
        symbols[source] = tuple(
            name for name in changed_symbols(item, pattern) if _may_pair(name)
        )[:MAX_SYMBOLS_PER_FILE]
    return symbols, sorted(missing)


def _may_pair(name: str) -> bool:
    return len(name) >= MIN_SYMBOL_CHARS and name.lower() not in COMMON_SYMBOLS


def _diff_text(repo: Path, scope: object) -> str | None:
    """The scope's diff: ``changes`` carries it; at ``worktree`` scope it is
    ``git diff HEAD``, read whole or not at all (its ceiling is the
    ``changes`` diff's)."""
    if scope.kind == "changes":
        return getattr(scope, "diff", None)
    ok, out, _ = run_git_text(repo, ["diff", "HEAD", "--"])
    if not ok or len(out) > MAX_DIFF_CHARS:
        return None
    return out


def _references(
    text: str, pattern: re.Pattern[str] | None, added: set[int]
) -> dict[str, tuple[int, int]]:
    """Identifier -> ``(rank, line)`` of the line citing it in a test's text,
    whole words only: the first line the diff added (rank 0), else the first
    line (rank 1). Every name the test declares itself is left out (a
    same-named helper is not a reference to the changed source)."""
    first: dict[str, tuple[int, int]] = {}
    declared: set[str] = set()
    for number, line in enumerate(text.splitlines(), 1):
        if len(line) > MAX_LINE_CHARS:
            continue
        if pattern is not None and (name := _declared_name(pattern, line)):
            declared.add(name)
        rank = 0 if number in added else 1
        for word in _IDENT.findall(line):
            if word not in first or rank < first[word][0]:
                first[word] = (rank, number)
    return {word: found for word, found in first.items() if word not in declared}


def _abstain(context: DimensionContext, reason: str) -> None:
    context.sources_missing.append(SourceMiss(source=CHANGE_SET, reason=reason))
    context.whole_file = tuple(_no_value(reason, name) for name in METRICS)


def _no_value(reason: str, name: str = METRIC) -> SampledMetric:
    return SampledMetric(
        name=name, value=None, abstention=reason, computed_from=(), derivation=""
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
        directories.update(
            "/".join(parts[:index]) for index in range(1, len(parts) + 1)
        )
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
