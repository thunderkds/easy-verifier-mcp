"""T005 acceptance tests — ``budget.py``: relevance ordering, lazy consumption,
explicit truncation (FR-011a, FR-011b, NFR-009).

``budget()`` invokes its ``collect`` callable once per non-empty relevance
tier (Stage 4 P1 resolution), so laziness is a **per-pass** property:
``InstrumentedCollect`` below records one advancement count per call, and the
regression test at the bottom pins the exact failure mode Stage 4 review
caught — a tier-3 prefix long enough to fill the budget before any tier-1
excerpt is ever reached.
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
    return Excerpt(path=path or f"f{index}.md", start_line=1, end_line=1, text=text)


class InstrumentedCollect:
    """A ``collect`` callable that records, per call, exactly how far
    ``budget()`` advanced that call's generator.

    Every call replays ``items`` from the start — this is what a real
    dimension's ``collect(context)`` does too (a fresh generator each time it
    is invoked) — so ``history`` has one entry per invocation, live-updated as
    that invocation's generator is pulled.
    """

    def __init__(self, items, raise_after: int | None = None) -> None:
        self.items = list(items)
        self.raise_after = raise_after
        self.history: list[int] = []
        self.calls = 0

    def __call__(self):
        self.calls += 1
        self.history.append(0)
        return self._generate(len(self.history) - 1)

    def _generate(self, call_index: int):
        for i, item in enumerate(self.items, start=1):
            if self.raise_after is not None and i > self.raise_after:
                raise RuntimeError("collect exploded")
            self.history[call_index] = i
            yield item


def constant(items) -> InstrumentedCollect:
    return InstrumentedCollect(items)


# --------------------------------------------------------------------------
# AC #1 — default + overridable limit
# --------------------------------------------------------------------------


def test_default_limit_is_120_kb_bytes():
    assert DEFAULT_BUDGET_BYTES == 120_000


def test_limit_is_overridable_per_call():
    items = [excerpt(i) for i in range(5)]
    result = budget(constant(items), scope=None, limit_bytes=2000)
    assert len(result.excerpts) == 1
    assert result.truncation.truncated is True


# --------------------------------------------------------------------------
# AC #2 — relevance order: changed -> spec-referenced -> everything else
# --------------------------------------------------------------------------


def test_changed_files_are_admitted_first_even_after_a_long_tier_3_prefix():
    """Stage 4 P1 regression: 6 tier-3 excerpts (2KB each = 12KB, enough to
    fill a 10KB budget on their own) arrive in the stream *before* 3 tier-1
    (changed-file) excerpts. A single-pass, arrival-order admission scheme
    admits zero changed-file excerpts here — pinned by this test so that
    regression can never land again."""
    changed = ("changed0.md", "changed1.md", "changed2.md")
    items = (
        [excerpt(i, path=f"other{i}.md") for i in range(6)]  # tier 3, first
        + [excerpt(100 + i, path=changed[i]) for i in range(3)]  # tier 1, last
    )
    collect = constant(items)
    scope = Scope(kind="changes", changed_files=changed)

    result = budget(collect, scope=scope, limit_bytes=10_000)

    admitted_paths = [e.path for e in result.excerpts]
    assert admitted_paths[:3] == list(changed)
    assert set(changed) <= set(admitted_paths)
    assert result.truncation.truncated is True


def test_changed_files_are_admitted_first_and_survive_a_late_arrival():
    """Mirrors the guide's Success Criterion 1: 100 x 2KB excerpts, limit
    10KB, 3 from changed files scattered mid-stream. The changed-file
    excerpts are admitted first, `truncated=True`, `omitted_count` is a lower
    bound of 1."""
    changed = ("changed0.md", "changed1.md", "changed2.md")
    items = (
        [excerpt(i, path=f"other{i}.md") for i in range(3)]
        + [excerpt(100 + i, path=changed[i]) for i in range(3)]
        + [excerpt(200 + i, path=f"more{i}.md") for i in range(94)]
    )
    collect = constant(items)
    scope = Scope(kind="changes", changed_files=changed)

    result = budget(collect, scope=scope, limit_bytes=10_000)

    admitted_paths = [e.path for e in result.excerpts]
    assert admitted_paths[:3] == list(changed)
    assert len(result.excerpts) == 5
    assert result.truncation.truncated is True
    assert result.truncation.omitted_count == 1  # a lower bound, not a total


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

    result = budget(constant(items), scope=scope, limit_bytes=DEFAULT_BUDGET_BYTES)

    assert [e.path for e in result.excerpts] == ["changed.md", guide, "remainder.md"]


def test_a_file_in_both_tier_1_and_tier_2_is_admitted_once_at_the_higher_tier():
    guide = "tasks/TASK_GUIDE_T005.md"
    items = [excerpt(0, path=guide)]
    scope = Scope(
        kind="task",
        changed_files=(guide,),
        task_ref=TaskRef(task_id="T005", guide_path=guide, acceptance_criteria=()),
    )

    result = budget(constant(items), scope=scope, limit_bytes=DEFAULT_BUDGET_BYTES)

    assert len(result.excerpts) == 1
    assert result.excerpts[0].path == guide


# --------------------------------------------------------------------------
# AC #3 — lazy consumption, per pass
# --------------------------------------------------------------------------


def test_single_tier_pass_is_advanced_no_further_than_it_must_be():
    """No scope -> a single tier-3 pass, same shape as the pre-T005 cap."""
    collect = InstrumentedCollect([excerpt(i) for i in range(50)])

    result = budget(collect, scope=None, limit_bytes=6000)

    assert len(result.excerpts) == 3
    assert collect.calls == 1
    assert collect.history == [4]  # pulled exactly one item past the admitted set


def test_tier_1_pass_stops_at_its_own_misfit_without_ever_reaching_tier_3():
    """A tier-1 pass that itself gets truncated ends the whole run: the
    tier-3 pass's `collect()` call never happens. A raise injected further
    into the same stream (AC #3, "the raise happens in any pass") never
    fires, because the misfit ends the pass first."""
    changed = tuple(f"changed{i}.md" for i in range(50))
    collect = InstrumentedCollect(
        [excerpt(i, path=changed[i], size=2000) for i in range(50)],
        raise_after=5,
    )
    scope = Scope(kind="changes", changed_files=changed)

    result = budget(collect, scope=scope, limit_bytes=6000)

    assert len(result.excerpts) == 3
    assert result.truncation.truncated is True
    assert collect.calls == 1  # only the tier-1 pass ever ran
    assert collect.history == [4]


def test_a_generator_that_raises_after_the_admitted_set_still_returns_a_valid_pack():
    """The exception sits on the item *after* the one that triggers the real
    rejection (6500 admits 3 x 2000 bytes, the 4th does not fit and stops the
    pass), so it is never reached."""
    collect = InstrumentedCollect([excerpt(i) for i in range(50)], raise_after=4)

    result = budget(collect, scope=None, limit_bytes=6500)

    assert len(result.excerpts) == 3
    assert result.truncation.truncated is True
    assert collect.history == [4]


def test_a_raise_in_a_later_pass_still_returns_a_valid_pack():
    """The tier-1 pass fully drains its short stream without ever reaching
    the injected exception (it sits past the stream's end for that pass);
    the tier-3 pass then hits its own misfit — at position 4, same as
    `test_a_generator_that_raises_after_the_admitted_set_still_returns_a_valid_pack`
    — before it would ever reach the raise either."""
    changed = ("changed.md",)
    items = [excerpt(0, path="changed.md", size=10)] + [
        excerpt(i, size=10) for i in range(1, 50)
    ]
    collect = InstrumentedCollect(items, raise_after=len(items) + 1)
    scope = Scope(kind="changes", changed_files=changed)

    result = budget(collect, scope=scope, limit_bytes=30)

    assert [e.path for e in result.excerpts] == ["changed.md", "f1.md", "f2.md"]
    assert result.truncation.truncated is True
    # tier 1 pass drains fully (only 1 item, no misfit, 50 items scanned);
    # tier 3 pass stops exactly one item past its own admitted set.
    assert collect.calls == 2
    assert collect.history == [50, 4]


# --------------------------------------------------------------------------
# AC #4, #6 — truncation is explicit, never a silent guess
# --------------------------------------------------------------------------


def test_no_truncation_when_everything_fits():
    items = [excerpt(i) for i in range(3)]
    result = budget(constant(items), scope=None, limit_bytes=DEFAULT_BUDGET_BYTES)

    assert result.truncation.truncated is False
    assert result.truncation.omitted_count == 0
    assert len(result.excerpts) == 3


def test_stream_ending_exactly_at_the_boundary_is_not_a_false_positive():
    items = [excerpt(i, size=10) for i in range(3)]  # 30 bytes total
    result = budget(constant(items), scope=None, limit_bytes=30)

    assert result.truncation.truncated is False
    assert result.truncation.omitted_count == 0


def test_truncation_fields_are_never_none():
    result = budget(constant(()), scope=None, limit_bytes=DEFAULT_BUDGET_BYTES)
    assert result.truncation.truncated is False
    assert result.truncation.omitted_count == 0
    assert result.truncation.truncated is not None
    assert result.truncation.omitted_count is not None


# --------------------------------------------------------------------------
# AC #7 — a single excerpt bigger than the whole budget
# --------------------------------------------------------------------------


def test_a_lone_oversized_excerpt_is_omitted_with_truncation_stated_not_silent():
    items = [excerpt(0, size=100)]
    result = budget(constant(items), scope=None, limit_bytes=10)

    assert result.excerpts == ()
    assert result.truncation.truncated is True
    assert result.truncation.omitted_count == 1


def test_an_oversized_excerpt_does_not_infinite_loop_on_an_infinite_stream():
    def infinite():
        i = 0
        while True:
            yield excerpt(i, size=100)
            i += 1

    result = budget(infinite, scope=None, limit_bytes=10)

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

    result = budget(constant([wide]), scope=None, limit_bytes=19)
    assert result.excerpts == ()
    assert result.truncation.truncated is True

    result = budget(constant([narrow]), scope=None, limit_bytes=20)
    assert len(result.excerpts) == 1
    assert result.truncation.truncated is False


# --------------------------------------------------------------------------
# AC #9 — determinism
# --------------------------------------------------------------------------


def test_same_input_run_twice_is_byte_identical():
    items = [excerpt(i) for i in range(10)]
    scope = Scope(kind="changes", changed_files=("f3.md", "f7.md"))

    first = budget(constant(items), scope=scope, limit_bytes=6000)
    second = budget(constant(items), scope=scope, limit_bytes=6000)

    assert first.excerpts == second.excerpts
    assert [e.text for e in first.excerpts] == [e.text for e in second.excerpts]


# --------------------------------------------------------------------------
# Edge cases
# --------------------------------------------------------------------------


def test_empty_input_is_a_valid_empty_pack():
    result = budget(constant(()), scope=None, limit_bytes=DEFAULT_BUDGET_BYTES)
    assert result.excerpts == ()
    assert result.truncation.truncated is False


@pytest.mark.parametrize("bad_limit", [0, -1, -1000])
def test_non_positive_limit_raises_a_structured_error(bad_limit):
    with pytest.raises(BudgetError):
        budget(constant([excerpt(0)]), scope=None, limit_bytes=bad_limit)


def test_empty_excerpt_text_contributes_overhead_only_no_zero_progress_loop():
    items = [
        Excerpt(path="empty.md", start_line=1, end_line=1, text=""),
        excerpt(1),
    ]
    result = budget(constant(items), scope=None, limit_bytes=DEFAULT_BUDGET_BYTES)
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

    result = budget(constant(items), scope=None, limit_bytes=DEFAULT_BUDGET_BYTES)

    assert len(result.excerpts) == 2
    assert {e.path for e in result.excerpts} == {"dup.md", "other.md"}


def test_duplicate_across_tier_1_and_tier_3_is_admitted_once_at_tier_1():
    """The same (path, line range) can be offered by a dimension more than
    once; the tier-1 pass admits it, and a later tier-3 pass re-encountering
    it must not duplicate it."""
    changed = ("changed.md",)
    items = [
        excerpt(0, path="changed.md"),
        excerpt(1, path="other.md"),
        excerpt(0, path="changed.md"),  # duplicate ref, offered again
    ]
    scope = Scope(kind="changes", changed_files=changed)

    result = budget(constant(items), scope=scope, limit_bytes=DEFAULT_BUDGET_BYTES)

    assert [e.path for e in result.excerpts] == ["changed.md", "other.md"]


def test_scope_none_falls_back_to_arrival_order():
    items = [excerpt(i) for i in range(3)]
    result = budget(constant(items), scope=None, limit_bytes=DEFAULT_BUDGET_BYTES)
    assert [e.path for e in result.excerpts] == [e.path for e in items]


def test_scope_with_no_changed_files_and_no_task_ref_skips_extra_passes():
    """Neither tier 1 nor tier 2 has any membership, so both passes are
    skipped and `collect` is called exactly once (the pre-T005 shape)."""
    collect = InstrumentedCollect([excerpt(i) for i in range(5)])
    scope = Scope(kind="project", files=("f0.md", "f1.md"))

    budget(collect, scope=scope, limit_bytes=DEFAULT_BUDGET_BYTES)

    assert collect.calls == 1
