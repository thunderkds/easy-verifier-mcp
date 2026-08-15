"""Repository access for dimensions.

A dimension never calls ``open()``. If it did, it would own symlink escape,
invalid UTF-8, permission errors and empty-file semantics — and Option D's whole
point is that a dimension cannot bypass a cross-cutting rule because it never
owns one. Reading through :meth:`RepoContext.read_source` also means
``files_read`` / ``sources_found`` / ``sources_missing`` are recorded as a *side
effect of actually reading*, so a dimension cannot claim it read something it
did not (FR-005, NFR-002).

T002 extends this module with real kit-aware/standalone detection. T001 probes
for ``PROJECT_SPEC.md`` only.
"""

from __future__ import annotations

from pathlib import Path

from .models import Excerpt, SourceMiss

MAX_EXCERPT_LINES = 200
"""Upper bound on lines in a single whole-file excerpt."""

MAX_LINE_CHARS = 500
"""Upper bound on a single line, so a minified file yields a bounded excerpt
rather than a multi-megabyte string."""

_TRUNCATION_MARK = " …[line truncated]"

MODE_KIT_AWARE = "kit-aware"
MODE_STANDALONE = "standalone"


def detect_mode(repo_path: Path) -> str:
    """Probe for kit artifacts. T001 checks ``PROJECT_SPEC.md`` only (T002 owns
    the real detection over the full artifact list)."""
    return MODE_KIT_AWARE if (repo_path / "PROJECT_SPEC.md").is_file() else MODE_STANDALONE


class RepoContext:
    """Read-only view of the target repository handed to ``collect``.

    Never writes, and never executes anything from the target repo (NFR-007).
    """

    def __init__(self, repo_path: Path, mode: str, scope: str) -> None:
        self.repo_path = repo_path
        self.mode = mode
        self.scope = scope
        self.files_read: list[str] = []
        self.sources_found: list[str] = []
        self.sources_missing: list[SourceMiss] = []

    def read_source(self, relative_path: str) -> str | None:
        """Return the text of a declared source, or ``None`` if unusable.

        Records the source as found or missing either way. A missing source is
        reported as missing — never substituted with plausible content.
        Returning ``""`` (an existing but empty file) counts as **found** and
        simply contributes no excerpt.
        """
        candidate = self.repo_path / relative_path

        try:
            resolved = candidate.resolve()
        except OSError as exc:
            return self._miss(relative_path, f"path could not be resolved: {exc.strerror}")

        # Symlinks pointing outside the repository are not followed.
        if not resolved.is_relative_to(self.repo_path):
            return self._miss(relative_path, "resolves outside the repository; not followed")

        if not resolved.exists():
            return self._miss(relative_path, "not found in the target repository")

        if not resolved.is_file():
            return self._miss(relative_path, "not a regular file")

        try:
            raw = resolved.read_bytes()
        except OSError as exc:
            return self._miss(relative_path, f"unreadable: {exc.strerror}")

        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            # Skipped rather than decoded with replacement characters, which
            # would put mojibake into a citation.
            return self._miss(relative_path, "not valid UTF-8 text; skipped")

        self.sources_found.append(relative_path)
        self.files_read.append(relative_path)
        return text

    def _miss(self, relative_path: str, reason: str) -> None:
        self.sources_missing.append(SourceMiss(source=relative_path, reason=reason))
        return None


def whole_file_excerpt(relative_path: str, text: str) -> Excerpt | None:
    """Build one bounded, 1-indexed excerpt from a file's text.

    Returns ``None`` for an empty file: it counts as found, but there is nothing
    to cite.
    """
    lines = text.splitlines()
    if not lines:
        return None

    kept = lines[:MAX_EXCERPT_LINES]
    bounded = [
        line if len(line) <= MAX_LINE_CHARS else line[:MAX_LINE_CHARS] + _TRUNCATION_MARK
        for line in kept
    ]
    return Excerpt(
        path=relative_path,
        start_line=1,
        end_line=len(kept),
        text="\n".join(bounded),
    )
