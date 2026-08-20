"""The bespoke ``test-strategy`` evidence dimension (FR-010).

It reports where a repository's tests live, what framework and configuration
they use, which tests correspond to the files in the active scope, and — in
kit-aware ``task`` scope — the acceptance criteria those tests are meant to
satisfy.

Three things it deliberately does **not** do:

* run the target's tests, test runner or ``conftest.py`` (NFR-007) — nothing
  here imports, executes or subprocesses anything from the target repository;
* compute a coverage percentage or judge adequacy (FR-013). A committed
  coverage artifact is reported as *existing*, never read, and its figures are
  never presented as this engine's own finding;
* guess a source↔test correspondence. Only the conventional per-ecosystem
  name mappings count; anything else is reported as "no test discovered for
  this file". A wrong correspondence tells the calling agent a file is covered
  when it is not, which is the exact class of claim this engine exists to
  prevent.

``EvidencePack.coverage_score`` is unrelated to test coverage: it is this
dimension's own found/sought checklist ratio (FR-016).
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from pathlib import PurePosixPath

from ..core.context import MAX_LINE_CHARS, whole_file_excerpt
from ..core.models import DimensionContext, DimensionDescriptor, Excerpt, SourceMiss

NAME = "test-strategy"

PURPOSE = (
    "Gather citable evidence about where a repository's tests live, what "
    "framework and configuration they use, and which files in the active "
    "scope have a conventionally corresponding test — without running "
    "anything or estimating coverage."
)

#: A declared entry that names a *result* rather than a repository path, so it
#: is always answered in the miss list with the correspondence it established
#: and the scope files it could not match. Same shape as the security
#: dimension's pseudo-source: the reason states why it can never be "found".
CORRESPONDENCE_SOURCE = "source-to-test correspondence for files in the active scope"

SOURCES_SOUGHT: tuple[str, ...] = (
    "pytest.ini",
    "tox.ini",
    "setup.cfg",
    "pyproject.toml",
    "conftest.py",
    "package.json",
    "jest.config.js",
    ".github/workflows/ci.yml",
    CORRESPONDENCE_SOURCE,
)

MAX_TEST_SOURCES = 200
"""Upper bound on files read while sweeping the scope for test evidence.

Candidates are ranked *before* the cap is applied, so the budget is spent on
the tests that correspond to scope files and on framework configuration, not
on whatever happens to sort first."""

MAX_NAMED_FILES = 10
"""Upper bound on paths enumerated inside a single miss reason or warning."""

MAX_CONFIG_SECTION_LINES = 60
_CONTEXT_LINES = 3

UNRESOLVED_SCOPE_WARNING = (
    "The {scope} scope could not be resolved, most likely because its required "
    "selector was not supplied. No evidence was gathered; this pack is not "
    "whole-repository output."
)

UNRESOLVED_SCOPE_REASON = (
    "not examined: the {scope} scope could not be resolved "
    "(its required selector was not supplied)"
)

NARROW_SCOPE_WARNING = (
    "Test discovery was limited to the {count} file(s) in the resolved {scope} "
    "scope. A corresponding test that exists elsewhere in the repository is "
    "reported as not discovered here, which is not the same as absent."
)

COVERAGE_ARTIFACT_WARNING = (
    "Coverage artifacts exist in the repository and were not read: {paths}. "
    "Any figures they contain belong to the target's own tooling and are not a "
    "finding of this engine."
)

DELETED_TEST_WARNING = (
    "Test file(s) in the change set could not be read from the worktree, which "
    "is what a deleted or moved test looks like: {paths}."
)

#: Lines that make a configuration file test-framework evidence. Broad on
#: purpose: a false positive costs a few quoted lines, a false negative loses
#: the only citation of how the target runs its tests.
_CONFIG_MARKER = re.compile(
    r"""(?ix)
    \[tool\.pytest | \[tool:pytest\] | \[pytest\] | \[tool\.coverage
    | \[testenv | testpaths | python_files | pytest | unittest | tox
    | "test" \s* : | \btest: | npm \s+ (run \s+ )?test | yarn \s+ test
    | go \s+ test | cargo \s+ test | jest | vitest | mocha | karma
    | junit | rspec | minitest | phpunit | \bcoverage\b
    """
)

#: Files whose whole purpose is test configuration: cited in full even when no
#: marker line matches, because their mere presence and content is the
#: evidence. ``conftest.py`` is read as text and never imported (NFR-007).
_DEDICATED_CONFIG_NAMES = frozenset({"pytest.ini", "conftest.py"})
_DEDICATED_CONFIG_PATTERNS = (
    re.compile(r"^(jest|vitest|playwright|cypress)\.config\.[cm]?[jt]s$"),
    re.compile(r"^karma\.conf\.[cm]?js$"),
)

_COVERAGE_ARTIFACT_NAMES = frozenset(
    {".coverage", "coverage.xml", "coverage.json", "lcov.info", "cobertura.xml"}
)
_COVERAGE_ARTIFACT_DIRS = frozenset({"htmlcov", "coverage"})

_TEST_DIR_SEGMENTS = frozenset({"test", "tests", "__tests__", "spec", "specs"})

#: Basenames each ecosystem's own test runner would collect, matched anywhere
#: in the tree so a co-located test counts. Known over-inclusion: a production
#: module genuinely named ``test_*.py`` (this dimension's own source, for one)
#: is classified as a test. That is the convention pytest itself applies, and
#: the alternative — demanding a ``tests/`` ancestor — would silently drop every
#: co-located suite, which is the failure mode that matters here.
_TEST_NAME_PATTERNS = (
    re.compile(r"^test_.+\.py$"),
    re.compile(r"^.+_test\.py$"),
    re.compile(r"^.+_test\.go$"),
    re.compile(r"^.+_test\.rs$"),
    re.compile(r"^.+_spec\.rb$"),
    re.compile(r"^test_.+\.rb$"),
    re.compile(r"^.+\.(test|spec)\.[cm]?[jt]sx?$"),
    re.compile(r"^.+Test\.java$"),
    re.compile(r"^Test.+\.java$"),
    re.compile(r"^.+Tests?\.cs$"),
)

_SOURCE_SUFFIXES = frozenset(
    {
        ".cs",
        ".go",
        ".java",
        ".js",
        ".jsx",
        ".kt",
        ".php",
        ".py",
        ".rb",
        ".rs",
        ".ts",
        ".tsx",
    }
)

_CONFIG_SUFFIXES = frozenset({".cfg", ".ini", ".json", ".toml", ".yaml", ".yml"})

#: Candidate categories in descending evidence relevance. The read cap is spent
#: in this order, never in path order.
_RANK_CORRESPONDING_TEST = 0
_RANK_TEST_CONFIG = 1
_RANK_OTHER_TEST = 2


def collect(context: DimensionContext) -> Iterator[Excerpt]:
    """Yield bounded test-surface evidence from the resolved scope, lazily."""
    resolved_scope = context.resolved_scope

    # A *narrow* scope that never resolved is a failure, not an invitation to
    # read the whole repository: `run_dimension` collapses `ScopeError` into
    # `resolved_scope = None`, so "unresolved" and "project" arrive here looking
    # identical, and only the requested scope name tells them apart.
    if resolved_scope is None and context.scope != "project":
        _warn(context, UNRESOLVED_SCOPE_WARNING.format(scope=context.scope))
        reason = UNRESOLVED_SCOPE_REASON.format(scope=context.scope)
        for source in SOURCES_SOUGHT:
            context.sources_missing.append(SourceMiss(source=source, reason=reason))
        return

    scope_files = tuple(getattr(resolved_scope, "files", ()) or ())
    changed_files = frozenset(getattr(resolved_scope, "changed_files", ()) or ())
    scope_kind = getattr(resolved_scope, "kind", None)
    whole_repo = resolved_scope is None or scope_kind == "project"
    reader = _Reader(context)

    # Declared sources are probed explicitly, before anything else. Without this
    # the miss list is guesswork: an absent `jest.config.js` is
    # indistinguishable from one no sweep ever looked at.
    for source in SOURCES_SOUGHT:
        if source == CORRESPONDENCE_SOURCE:
            continue
        if not whole_repo and source not in scope_files:
            context.sources_missing.append(
                SourceMiss(
                    source=source,
                    reason=f"not in the resolved {scope_kind} scope",
                )
            )
            continue
        text = reader.read(source)
        if text is None:
            continue
        excerpt = _config_excerpt(source, text)
        if excerpt is not None:
            yield excerpt

    if resolved_scope is None:
        context.sources_missing.append(
            SourceMiss(
                source=CORRESPONDENCE_SOURCE,
                reason=(
                    "not examined: no resolved file set was available for this run"
                ),
            )
        )
        return

    # The kit-aware `task` scope carries the guide the change is answerable to;
    # its acceptance criteria are what the tests are supposed to satisfy
    # (FR-007), cited from the guide itself so the caller gets real line
    # numbers rather than a restatement.
    task_ref = getattr(resolved_scope, "task_ref", None)
    if task_ref is not None:
        text = reader.read(task_ref.guide_path)
        if text is not None:
            excerpt = _acceptance_criteria_excerpt(task_ref.guide_path, text)
            if excerpt is not None:
                yield excerpt

    # Every non-yield bookkeeping side effect happens before the ranked yields.
    # The byte budget abandons this generator at its first rejection, so a miss
    # or warning recorded after a yield can silently never be recorded at all.
    deleted = _deleted_change_set_tests(reader, changed_files)
    if deleted:
        _warn(context, DELETED_TEST_WARNING.format(paths=_join(deleted)))

    artifacts = sorted(path for path in scope_files if _is_coverage_artifact(path))
    if artifacts:
        _warn(context, COVERAGE_ARTIFACT_WARNING.format(paths=_join(artifacts)))

    if not whole_repo:
        _warn(
            context,
            NARROW_SCOPE_WARNING.format(count=len(scope_files), scope=scope_kind),
        )

    tests = tuple(path for path in scope_files if _is_test_file(path))
    matched, unmatched = _correspondence(scope_files, tests)
    context.sources_missing.append(
        SourceMiss(
            source=CORRESPONDENCE_SOURCE,
            reason=_correspondence_reason(matched, unmatched),
        )
    )

    corresponding = {test for tests_for in matched.values() for test in tests_for}
    for _rank, source in _ranked_candidates(scope_files, tests, corresponding):
        if reader.reads >= MAX_TEST_SOURCES:
            return
        text = reader.read(source)
        if text is None:
            continue
        excerpt = (
            _config_excerpt(source, text)
            if _is_test_config(source)
            else whole_file_excerpt(source, text)
        )
        if excerpt is not None:
            yield excerpt


class _Reader:
    """Reads through ``context.read_source`` once per path, counting reads.

    ``collect`` may be invoked once per relevance tier by the byte budget, and
    the deleted-test pre-pass looks at files the sweep will want too. Caching
    keeps ``files_read`` honest — a file read once is reported once — and keeps
    the cap a bound on distinct files rather than on attempts.
    """

    def __init__(self, context: DimensionContext) -> None:
        self._context = context
        self._cache: dict[str, str | None] = {}
        self.reads = 0

    def read(self, path: str) -> str | None:
        if path in self._cache:
            return self._cache[path]
        # Never opened: a coverage artifact is evidence that it *exists*, and
        # reading it would put its figures one careless step from being quoted
        # as this engine's finding (FR-013).
        if _is_coverage_artifact(path):
            self._cache[path] = None
            return None
        self.reads += 1
        text = self._context.read_source(path)
        self._cache[path] = text
        return text

    def miss_reason(self, path: str) -> str | None:
        for miss in reversed(self._context.sources_missing):
            if miss.source == path:
                return miss.reason
        return None


def _deleted_change_set_tests(
    reader: _Reader, changed_files: frozenset[str]
) -> list[str]:
    """Test files the diff names that are not readable in the worktree.

    A deleted test is the change most worth seeing and the easiest to miss: it
    is simply absent from the working tree, so a scope-file sweep would skip it
    without a word. The absence is derived from the miss ``read_source``
    already recorded — the dimension never touches the filesystem itself.
    """
    deleted: list[str] = []
    for path in sorted(changed_files):
        if not _is_test_file(path):
            continue
        if reader.read(path) is not None:
            continue
        reason = reader.miss_reason(path) or ""
        if "not found" in reason:
            deleted.append(path)
    return deleted


def _correspondence(
    scope_files: tuple[str, ...], tests: tuple[str, ...]
) -> tuple[dict[str, tuple[str, ...]], tuple[str, ...]]:
    """Map each source file in scope to its conventionally named test files.

    Conventional only. Where no convention matches, the file is returned as
    unmatched — reported as "no test discovered" — rather than attached to the
    nearest plausible test.
    """
    by_name: dict[str, list[str]] = {}
    for test in tests:
        by_name.setdefault(PurePosixPath(test).name, []).append(test)

    matched: dict[str, tuple[str, ...]] = {}
    unmatched: list[str] = []
    for source in scope_files:
        if not _is_source_file(source):
            continue
        hits: list[str] = []
        for name in _expected_test_names(source):
            for test in by_name.get(name, ()):
                # Go's convention is same-package, same-directory. Matching a
                # `foo_test.go` from an unrelated package would be a fabricated
                # correspondence.
                if source.endswith(".go") and _parent(test) != _parent(source):
                    continue
                hits.append(test)
        if hits:
            matched[source] = tuple(sorted(set(hits)))
        else:
            unmatched.append(source)
    return matched, tuple(unmatched)


def _expected_test_names(source: str) -> tuple[str, ...]:
    """The conventional test basenames for one source file, by ecosystem."""
    name = PurePosixPath(source).name
    stem = PurePosixPath(name).stem
    suffix = PurePosixPath(name).suffix

    if suffix == ".py":
        return (f"test_{stem}.py", f"{stem}_test.py")
    if suffix == ".go":
        return (f"{stem}_test.go",)
    if suffix in {".js", ".jsx", ".ts", ".tsx"}:
        return (
            f"{stem}.test{suffix}",
            f"{stem}.spec{suffix}",
            f"{stem}_test{suffix}",
        )
    if suffix == ".rb":
        return (f"{stem}_spec.rb", f"test_{stem}.rb")
    if suffix == ".java":
        return (f"{stem}Test.java", f"Test{stem}.java")
    if suffix == ".cs":
        return (f"{stem}Test.cs", f"{stem}Tests.cs")
    # Rust and everything else have no single-file naming convention that can
    # be asserted without guessing; an admitted gap is the honest answer.
    return ()


def _correspondence_reason(
    matched: dict[str, tuple[str, ...]], unmatched: tuple[str, ...]
) -> str:
    """State both sides of the correspondence result in the miss list.

    Always a miss: this declared entry names a per-file result, not a file, so
    it can never be "found" by a read. The reason is where the answer lives.
    """
    parts: list[str] = []
    if matched:
        pairs = [
            f"{source} -> {', '.join(tests)}"
            for source, tests in sorted(matched.items())[:MAX_NAMED_FILES]
        ]
        extra = len(matched) - len(pairs)
        rendered = "; ".join(pairs) + (f" (+{extra} more)" if extra else "")
        parts.append(f"test discovered for {len(matched)} file(s): {rendered}")
    if unmatched:
        parts.append(
            f"no test discovered for {len(unmatched)} file(s): {_join(unmatched)}"
        )
    if not parts:
        return (
            "not applicable: the active scope contains no source files to "
            "correspond to a test"
        )
    return (
        "this entry reports a per-file result rather than a file, so it is "
        "always listed here: " + "; ".join(parts)
    )


def _ranked_candidates(
    scope_files: tuple[str, ...],
    tests: tuple[str, ...],
    corresponding: set[str],
) -> list[tuple[int, str]]:
    """Scope files worth reading, ordered by relevance, ties broken by path.

    Ordering happens before the cap, so a repository with more test files than
    ``MAX_TEST_SOURCES`` still spends its reads on the tests that correspond to
    the scope and on framework configuration.
    """
    test_set = frozenset(tests)
    ranked: list[tuple[int, str]] = []
    for source in scope_files:
        if _is_coverage_artifact(source):
            continue
        if source in corresponding:
            rank = _RANK_CORRESPONDING_TEST
        elif _is_test_config(source):
            rank = _RANK_TEST_CONFIG
        elif source in test_set:
            rank = _RANK_OTHER_TEST
        else:
            continue
        ranked.append((rank, source))
    ranked.sort()
    return ranked


def _config_excerpt(path: str, text: str) -> Excerpt | None:
    """Cite the test-configuration lines of a file, with real line numbers.

    A shared manifest (``pyproject.toml``, ``setup.cfg``, ``package.json``) is
    mostly not about tests, so quoting it whole would spend the byte budget on
    packaging metadata. Only the marker lines and their immediate context are
    cited; a file with nothing test-related yields no excerpt while remaining a
    genuinely read, genuinely found source.
    """
    lines = text.splitlines()
    if not lines:
        return None

    hits = [index for index, line in enumerate(lines) if _CONFIG_MARKER.search(line)]
    if not hits:
        return whole_file_excerpt(path, text) if _is_dedicated_config(path) else None

    start = hits[0]
    limit = min(len(lines) - 1, start + MAX_CONFIG_SECTION_LINES - 1)
    last = max(index for index in hits if index <= limit)
    end = min(limit, last + _CONTEXT_LINES)

    return Excerpt(
        path=path,
        start_line=start + 1,
        end_line=end + 1,
        text="\n".join(_bounded(line) for line in lines[start : end + 1]),
    )


def _acceptance_criteria_excerpt(path: str, text: str) -> Excerpt | None:
    """Cite the guide's ``## Acceptance Criteria`` section (FR-007)."""
    lines = text.splitlines()
    start = next(
        (
            index
            for index, line in enumerate(lines)
            if line.strip().lower() == "## acceptance criteria"
        ),
        None,
    )
    if start is None:
        return None

    end = len(lines) - 1
    for index in range(start + 1, len(lines)):
        if lines[index].startswith("## "):
            end = index - 1
            break
    end = min(end, start + MAX_CONFIG_SECTION_LINES - 1)

    return Excerpt(
        path=path,
        start_line=start + 1,
        end_line=end + 1,
        text="\n".join(_bounded(line) for line in lines[start : end + 1]),
    )


def _bounded(line: str) -> str:
    return (
        line
        if len(line) <= MAX_LINE_CHARS
        else line[:MAX_LINE_CHARS] + " …[line truncated]"
    )


def _join(paths) -> str:
    listed = list(paths)[:MAX_NAMED_FILES]
    extra = len(list(paths)) - len(listed)
    return ", ".join(listed) + (f" (+{extra} more)" if extra else "")


def _parent(path: str) -> str:
    return PurePosixPath(path).parent.as_posix()


def _is_test_file(path: str) -> bool:
    name = PurePosixPath(path).name
    if any(pattern.match(name) for pattern in _TEST_NAME_PATTERNS):
        return True
    parts = PurePosixPath(path).parts[:-1]
    return any(part.lower() in _TEST_DIR_SEGMENTS for part in parts) and (
        PurePosixPath(name).suffix in _SOURCE_SUFFIXES
    )


def _is_source_file(path: str) -> bool:
    """A file the correspondence rule can be asked about: code, not a test."""
    return PurePosixPath(path).suffix in _SOURCE_SUFFIXES and not _is_test_file(path)


def _is_dedicated_config(path: str) -> bool:
    name = PurePosixPath(path).name
    return name in _DEDICATED_CONFIG_NAMES or any(
        pattern.match(name) for pattern in _DEDICATED_CONFIG_PATTERNS
    )


def _is_test_config(path: str) -> bool:
    """Framework or CI configuration that may describe how tests are run."""
    if _is_dedicated_config(path):
        return True
    lower = path.lower()
    name = PurePosixPath(lower).name
    if lower.startswith(".github/workflows/") and name.endswith((".yml", ".yaml")):
        return True
    if name in {"tox.ini", "setup.cfg", "pyproject.toml", "package.json"}:
        return True
    return name in {".gitlab-ci.yml", "makefile"} or (
        "test" in name and PurePosixPath(name).suffix in _CONFIG_SUFFIXES
    )


def _is_coverage_artifact(path: str) -> bool:
    lower = path.lower()
    parts = PurePosixPath(lower).parts
    if PurePosixPath(lower).name in _COVERAGE_ARTIFACT_NAMES:
        return True
    return bool(parts) and parts[0] in _COVERAGE_ARTIFACT_DIRS and len(parts) > 1


def _warn(context: DimensionContext, message: str) -> None:
    """Append a pack warning once, however many budget passes call ``collect``.

    ``run_dimension`` copies ``context.warnings`` onto the pack after the budget
    drain, so appending here reaches the caller without any pipeline change.
    """
    if message not in context.warnings:
        context.warnings = (*context.warnings, message)


DESCRIPTOR = DimensionDescriptor(
    name=NAME,
    purpose=PURPOSE,
    sources_sought=SOURCES_SOUGHT,
    collect=collect,
)
