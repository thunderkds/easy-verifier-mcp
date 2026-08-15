# TASK_GUIDE — T005: budget.py — relevance ordering, lazy consumption, explicit truncation
**Date**: 2026-08-15
**Complexity Level**: C2
**Risk Level**: Medium
**Priority**: P0
**Assigned agent**: Backend-Implementer
**Agent guide**: `.claude/agents/backend.md`

---

## Mandatory Startup (Do Not Skip)

1. Read `PROJECT_SPEC.md`
2. Read `memory/MEMORY.md`
3. Read this file completely
4. Read `.claude/agents/backend.md`
5. **C2** — apply the C2 process from the Complexity matrix in `.claude/agents/general-agent-template.md`
6. **C2** — read `memory/codebase-map.md`

---

## Requirement (Pillar 1 — Adapt the requirement)

Keep an evidence pack small enough not to exhaust the calling agent's context, drop only the least
useful material, and say out loud what was dropped.

**Restated intent**:
> `budget(excerpts, scope, limit_bytes)` consumes a lazy `Iterable[Excerpt]`, admits excerpts in
> relevance order until the byte limit is reached, and returns the admitted set plus an explicit
> truncation record. It never materialises the full candidate set, and it never drops anything
> silently.

**Out of scope**:
- Deciding *which* excerpts a dimension offers (each dimension's `collect`).
- Per-dimension vs. total budget in a combined call — that is T012's open question, resolved there.

**Requirement Refs**:
- FR-011a: per-dimension byte budget, default 120 KB, overridable per call; relevance order = changed files → spec-referenced files → remainder
- FR-011b: truncation reported as a structured field stating that it occurred and how many items were omitted; silent truncation prohibited; omitted items appear in the coverage list
- FR-016a: coverage never rendered without the miss list
- NFR-009: packs bounded so whole-project evaluation does not exhaust context

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [ ] Restated intent confirmed to match the user's request (by Supervisor / user)
- [ ] Domain terms align with `PROJECT_SPEC.md` glossary
- [ ] Every Acceptance Criterion below traces to a line in the Requirement
- [ ] All Requirement Refs exist in `PRD.md` and are fully covered by the Acceptance Criteria above

---

## Dependencies & Reachability

**Depends on**: T001 — pipeline contract and the naive cap this task replaces; T003 — `Scope` supplies the changed-file set that drives relevance tier 1.

**Entry point**: `budget`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | Default limit is 120 KB, **measured in bytes** (not characters), and is overridable per call | FR-011a |
| 2 | Relevance order is exactly: (1) excerpts from files changed in the active scope, (2) excerpts from files referenced by the loaded spec/kit artifacts, (3) everything else — stable and deterministic within each tier | FR-011a |
| 3 | The input is consumed **lazily**: a test proves that with a limit admitting N excerpts, a generator yielding N+K items is advanced no further than it must be, and a generator that raises after N items still returns a valid pack | Critical Constraint 3, NFR-009 |
| 4 | On truncation, the result carries `truncated=True` and `omitted_count` equal to the number of excerpts not admitted | FR-011b |
| 5 | Omitted items are reflected in the coverage/miss list so a reader can audit what is absent | FR-011b, FR-016a |
| 6 | With no truncation, `truncated=False` and `omitted_count=0` — never `None`, never absent | FR-011b |
| 7 | A single excerpt larger than the whole limit is handled explicitly (admitted-and-clipped with a stated clip, or omitted with a stated reason) — never an infinite loop, never silently zero excerpts with `truncated=False` | FR-011b |
| 8 | Byte accounting matches the serialized pack's actual size within a documented tolerance — a limit that lies is worse than no limit | NFR-009 |
| 9 | Ordering is deterministic across runs and across adapters (no set/dict iteration order dependence, no unsorted `os.listdir`) | FR-022 |

---

## Evaluation & Acceptance

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | 100 excerpts of 2 KB each, limit 10 KB, 3 of them from changed files | The 3 changed-file excerpts are admitted first; `truncated=True`; `omitted_count` correct | automated test |
| 2 | Generator raising `RuntimeError` on item 50, limit admitting 10 | Valid pack of 10; exception never raised | automated test |
| 3 | Total candidate size under the limit | All admitted, `truncated=False`, `omitted_count=0` | automated test |
| 4 | One 500 KB excerpt, limit 120 KB | Documented behaviour from AC #7, stated in the truncation field | automated test |
| 5 | Same input run twice | Byte-identical ordering | automated test |

### Verification Command (exact, runnable)

```bash
pytest tests/test_t005_budget.py -q
```

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T005.md`.

---

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T005.md`.

---

## Approach

**Pattern reference**: `src/easy_verifier/core/pipeline.py` (T001) — this task replaces the naive cap there; keep the same call shape so no dimension changes.

The design tension is real and worth naming: perfect relevance ordering wants the whole candidate
set in hand (to sort it), while laziness forbids exactly that. Resolve it by **tiering rather than
sorting**: the changed-file and spec-referenced sets are known from `Scope` and `RepoContext`
*before* any excerpt is produced, so `collect` can be consumed in tier passes — tier 1 first, then
tier 2, then tier 3 — and each pass stops the moment the budget is exhausted. Never sort the full
stream.

Measure bytes with `len(text.encode("utf-8"))` plus a per-excerpt overhead constant for the
surrounding structure, and document the constant. AC #8 exists because a budget computed on
character counts under-counts by up to 4× on non-ASCII content, which is exactly the case where a
context blow-up is least recoverable.

---

## Edge Case Checklist

- [ ] Empty input iterable → valid empty pack, `truncated=False`
- [ ] Limit of 0 or a negative limit → structured error, not silent empty output
- [ ] Single excerpt exceeding the limit (AC #7)
- [ ] Non-ASCII / multibyte content → byte accounting correct
- [ ] An excerpt whose text is empty → contributes overhead only, does not cause a zero-progress loop
- [ ] Duplicate excerpts from the same file and line range → deduplicated, and dedup does not force materialisation
- [ ] A file appearing in both tier 1 and tier 2 → admitted once, in the higher tier
- [ ] The generator is infinite → the budget still terminates the run
- [ ] Truncation interacting with redaction: a clipped excerpt must not expose a secret that the unclipped form had redacted (coordinate with T004 — redact before clipping, and re-check the clip boundary)
- [ ] `omitted_count` when the stream is lazy and never fully consumed → must be honest about being a lower bound if the remainder was not counted, and say so in the field rather than guessing a number

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/core/budget.py` | New — tiered lazy admission, byte accounting, truncation record |
| `src/easy_verifier/core/models.py` | Add `TruncationRecord`; wire onto `EvidencePack` |
| `src/easy_verifier/core/pipeline.py` | Replace the T001 naive cap with `budget()` |
| `tests/test_t005_budget.py` | New |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| `.claude/hooks/**` | Must-not-touch |
| `src/easy_verifier/core/redact.py` | Owned by T004 — coordinate, do not edit |
| `memory/**`, `PROJECT_KANBAN.md` | Supervisor-only |

---

## Test Plan

`tests/test_t005_budget.py`. The laziness tests (AC #3) are the load-bearing ones and must use
instrumented generators that record how far they were advanced — a test that merely checks output
correctness passes just as happily against a fully-materialising implementation, which is precisely
the regression this constraint exists to prevent. Add a determinism test running the same input
twice and comparing serialized output byte-for-byte, since T017's parity test depends on it.

---

## Completion Checklist

- [ ] Implementation done
- [ ] Self-review: `Skill({ skill: "code-review" })` run
- [ ] Security review: `Skill({ skill: "security-review" })` run (Medium risk — required)
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T005.md`'s Evidence table (Hard-Stop Gate 5)
- [ ] `Skill({ skill: "verify" })` run
- [ ] `memory/MEMORY.md` updated (if new patterns or feedback learned)
- [ ] Supervisor notified: task ready for Stage 4 review
