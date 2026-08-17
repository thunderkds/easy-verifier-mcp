"""T005 acceptance tests — ``budget.py``: relevance ordering, lazy consumption,
explicit truncation (FR-011a, FR-011b, NFR-009).

The laziness tests are the load-bearing ones (Test Plan): an instrumented
generator records exactly how far ``budget()`` advanced it, so a fully
materialising implementation cannot pass these by accident — the same
discipline ``test_t001_pipeline.py``'s ``InstrumentedCollect`` established.
"""

from __future__ import annotations

import pytest

from easy_verifier.core.budget import (
    DEFAULT_BUDGET_BYTES,
    BudgetError,
    budget,
)
from easy_verifier.core.models import Excerpt
from easy_verifier.core.scope import Scope, TaskRef


def excerpt(index: int, *, path: str | None = None, size: int = 2000) -> Excerpt:
    """An excerpt whose text is exactly ``size`` bytes."""
    text = str(index % 10) * size
    assert len(text.encode("utf-8")) == size
    return Excerpt(
        path=path or f"f{index}.md", start_line=1, end_line=1, text=text
    )


class InstrumentedExcerpts:
    """Records exactly how far ``budget()`` advanced this generator."""

    def __init__(self, items, raise_after: int | None = None) -> None:
        self.items = items
        self.raise_after = raise_after
        self.advanced = 0

    def __iter__(self):
        for i, item in enumerate(self.items, start=1):
            if self.raise_after is not None and i > self.raise_after:
                raise RuntimeError("collect exploded")
            self.advanced = i
            yield item


# --------------------------------------------------------------------------
# AC #1 — default + overridable limit
# --------------------------------------------------------------------------


def test_default_limit_is_120_kb_bytes():
    assert DEFAULT_BUDGET_BYTES == 120_000


def test_limit_is_overridable_per_call():
    items = [excerpt(i) for i in range(5)]
    result = budget(items, scope=None, limit_bytes=2000)
    assert len(result.excerpts) == 1
    assert result.truncation.truncated is True


# --------------------------------------------------------------------------
# AC #2 — relevance order: changed -> spec-referenced -> everything else
# --------------------------------------------------------------------------


def test_changed_files_are_admitted_first_and_survive_a_late_arrival():
    """Mirrors the guide's Success Criterion 1: 100 x 2KB excerpts, limit 10KB,
    3 from changed files. The changed-file excerpts are admitted first even
    though they are not first in the stream, `truncated=True`, `omitted_count`
    is a lower bound of 1, and the stream is advanced exactly one item past
    the admitted set."""
    changed = ("changed0.md", "changed1.md", "changed2.md")
    items = (
        [excerpt(i, path=f"other{i}.md") for i in range(3)]  # tier 3, arrives first
        + [excerpt(100 + i, path=changed[i]) for i in range(3)]  # tier 1
        # tier 3, never reached:
        + [excerpt(200 + i, path=f"more{i}.md") for i in range(94)]
    )
    stream = InstrumentedExcerpts(items)
    scope = Scope(kind="changes", changed_files=changed)

    result = budget(stream, scope=scope, limit_bytes=10_000)

    admitted_paths = [e.path for e in result.excerpts]
    assert admitted_paths[:3] == list(changed)
    assert len(result.excerpts) == 5
    assert result.truncation.truncated is True
    assert result.truncation.omitted_count == 1  # a lower bound, not a total
    assert stream.advanced == 6  # pulled exactly one item past the admitted set


def test_spec_referenced_file_outranks_remainder_but_not_changed_files():
    guide = "tasks/TASK_GUIDE_T005.md"
    items = [
        excerpt(0, path="remainder.md"),
        excerpt(1, path=guide),
        excerpt(2, path="changed.md"),
    ]
    scope = Scope(
        kind="task",
        changed_files=("changed.md",),
        task_ref=TaskRef(task_id="T005", guide_path=guide, acceptance_criteria=()),
    )

    result = budget(items, scope=scope, limit_bytes=DEFAULT_BUDGET_BYTES)

    assert [e.path for e in result.excerpts] == ["changed.md", guide, "remainder.md"]


def test_a_file_in_both_tier_1_and_tier_2_is_admitted_once_at_the_higher_tier():
    path = "PROJECT_SPEC.md"
    items = [excerpt(0, path=path)]
    scope = Scope(kind="changes", changed_files=(path,))

    result = budget(items, scope=scope, limit_bytes=DEFAULT_BUDGET_BYTES)

    assert len(result.excerpts) == 1
    assert result.excerpts[0].path == path


# --------------------------------------------------------------------------
# AC #3 — lazy consumption
# --------------------------------------------------------------------------


def test_stream_is_advanced_no_further_than_it_must_be():
    """A limit admitting 3 excerpts must not advance a 3+K-item generator past
    the 4th item, whatever K is."""
    stream = InstrumentedExcerpts([excerpt(i) for i in range(50)])

    result = budget(stream, scope=None, limit_bytes=6000)

    assert len(result.excerpts) == 3
    assert stream.advanced == 4
    assert stream.advanced < 50


def test_a_generator_that_raises_after_the_admitted_set_still_returns_a_valid_pack():
    """The exception sits on the item *after* the one that triggers the real
    rejection (6500 admits 3 x 2000 bytes, the 4th does not fit and stops the
    run), so it is never reached — the same shape as T001's ``raise_at``
    tests."""
    stream = InstrumentedExcerpts([excerpt(i) for i in range(50)], raise_after=4)

    result = budget(stream, scope=None, limit_bytes=6500)

    assert len(result.excerpts) == 3
    assert result.truncation.truncated is True
    assert stream.advanced == 4


# --------------------------------------------------------------------------
# AC #4, #6 — truncation is explicit, never a silent guess
# --------------------------------------------------------------------------


def test_no_truncation_when_everything_fits():
    items = [excerpt(i) for i in range(3)]
    result = budget(items, scope=None, limit_bytes=DEFAULT_BUDGET_BYTES)

    assert result.truncation.truncated is False
    assert result.truncation.omitted_count == 0
    assert len(result.excerpts) == 3


def test_stream_ending_exactly_at_the_boundary_is_not_a_false_positive():
    items = [excerpt(i, size=10) for i in range(3)]  # 30 bytes total
    result = budget(items, scope=None, limit_bytes=30)

    assert result.truncation.truncated is False
    assert result.truncation.omitted_count == 0


def test_truncation_fields_are_never_none():
    result = budget(iter(()), scope=None, limit_bytes=DEFAULT_BUDGET_BYTES)
    assert result.truncation.truncated is False
    assert result.truncation.omitted_count == 0
    assert result.truncation.truncated is not None
    assert result.truncation.omitted_count is not None


# --------------------------------------------------------------------------
# AC #7 — a single excerpt bigger than the whole budget
# --------------------------------------------------------------------------


def test_a_lone_oversized_excerpt_is_omitted_with_truncation_stated_not_silent():
    items = [excerpt(0, size=100)]
    result = budget(items, scope=None, limit_bytes=10)

    assert result.excerpts == ()
    assert result.truncation.truncated is True
    assert result.truncation.omitted_count == 1


def test_an_oversized_excerpt_does_not_infinite_loop_on_an_infinite_stream():
    def infinite():
        i = 0
        while True:
            yield excerpt(i, size=100)
            i += 1

    result = budget(infinite(), scope=None, limit_bytes=10)

    assert result.truncation.truncated is True
    assert result.excerpts == ()


# --------------------------------------------------------------------------
# AC #8 — byte accounting, non-ASCII content
# --------------------------------------------------------------------------


def test_byte_accounting_uses_utf8_bytes_not_characters():
    # Each "é" is 1 char but 2 UTF-8 bytes: 10 chars -> 20 bytes.
    text = "é" * 10
    assert len(text) == 10
    assert len(text.encode("utf-8")) == 20

    wide = Excerpt(path="wide.md", start_line=1, end_line=1, text=text)
    narrow = Excerpt(path="narrow.md", start_line=1, end_line=1, text="a" * 20)

    result = budget([wide], scope=None, limit_bytes=19)
    assert result.excerpts == ()
    assert result.truncation.truncated is True

    result = budget([narrow], scope=None, limit_bytes=20)
    assert len(result.excerpts) == 1
    assert result.truncation.truncated is False


# --------------------------------------------------------------------------
# AC #9 — determinism
# --------------------------------------------------------------------------


def test_same_input_run_twice_is_byte_identical():
    items = [excerpt(i) for i in range(10)]
    scope = Scope(kind="changes", changed_files=("f3.md", "f7.md"))

    first = budget(list(items), scope=scope, limit_bytes=6000)
    second = budget(list(items), scope=scope, limit_bytes=6000)

    assert first.excerpts == second.excerpts
    assert [e.text for e in first.excerpts] == [e.text for e in second.excerpts]


# --------------------------------------------------------------------------
# Edge cases
# --------------------------------------------------------------------------


def test_empty_input_is_a_valid_empty_pack():
    result = budget(iter(()), scope=None, limit_bytes=DEFAULT_BUDGET_BYTES)
    assert result.excerpts == ()
    assert result.truncation.truncated is False


@pytest.mark.parametrize("bad_limit", [0, -1, -1000])
def test_non_positive_limit_raises_a_structured_error(bad_limit):
    with pytest.raises(BudgetError):
        budget([excerpt(0)], scope=None, limit_bytes=bad_limit)


def test_empty_excerpt_text_contributes_overhead_only_no_zero_progress_loop():
    items = [
        Excerpt(path="empty.md", start_line=1, end_line=1, text=""),
        excerpt(1),
    ]
    result = budget(items, scope=None, limit_bytes=DEFAULT_BUDGET_BYTES)
    assert len(result.excerpts) == 2


def test_duplicate_excerpts_are_deduplicated():
    same = excerpt(0, path="dup.md")
    duplicate_again = Excerpt(
        path=same.path,
        start_line=same.start_line,
        end_line=same.end_line,
        text=same.text,
    )
    items = [same, duplicate_again, excerpt(1, path="other.md")]

    result = budget(items, scope=None, limit_bytes=DEFAULT_BUDGET_BYTES)

    assert len(result.excerpts) == 2
    assert {e.path for e in result.excerpts} == {"dup.md", "other.md"}


def test_scope_none_falls_back_to_arrival_order():
    items = [excerpt(i) for i in range(3)]
    result = budget(items, scope=None, limit_bytes=DEFAULT_BUDGET_BYTES)
    assert [e.path for e in result.excerpts] == [e.path for e in items]
