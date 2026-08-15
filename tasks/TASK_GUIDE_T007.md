# TASK_GUIDE — T007: Shared doc-extraction helper + solution-fit, requirement-fidelity, code-quality
**Date**: 2026-08-15
**Complexity Level**: C2
**Risk Level**: Low
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
7. Read `BRAINSTORMING_LOG.md` § the Option A post-mortem — it explains precisely why this helper's scope is capped at four dimensions

---

## Requirement (Pillar 1 — Adapt the requirement)

Complete the four **document-shaped** dimensions — the ones whose evidence is "find the relevant
passages in the project's documents and cite them" — behind one shared extraction helper.
`architecture` shipped in T001; this task adds the other three and factors the common part out.

**Restated intent**:
> `solution-fit`, `requirement-fidelity` and `code-quality` each ship as a descriptor plus a
> `collect` callable, and all four doc-shaped dimensions draw their extraction logic from one
> helper. Each declares its own `sources_sought`, so their coverage scores differ meaningfully.

**Out of scope**:
- `security`, `test-strategy`, `blast-radius` (T008–T010) — these stay **bespoke**. Do not widen the
  helper to fit them; that is the mistake that sank Option A.
- Discovery (T011), synthesis (T012), reporting (T013).

**Requirement Refs**:
- FR-009: each dimension a separate callable unit
- FR-010: four of the seven v1 dimensions (with `architecture` from T001, this closes the doc-shaped set)
- FR-011: structured pack — files read, citable excerpts, sources sought but not found
- FR-013: no verdict, score or judgment from the engine
- FR-016: per-dimension declared `sources_sought`
- FR-002/FR-003: kit-aware ground truth, standalone doc-first fallback

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [ ] Restated intent confirmed to match the user's request (by Supervisor / user)
- [ ] Domain terms align with `PROJECT_SPEC.md` glossary
- [ ] Every Acceptance Criterion below traces to a line in the Requirement
- [ ] All Requirement Refs exist in `PRD.md` and are fully covered by the Acceptance Criteria above

---

## Dependencies & Reachability

**Depends on**: T002 — `RepoContext` supplies mode and document inventory; T005 — `budget()` must exist so `collect` can stay lazy under a real budget.

**Entry point**: `collect` (per dimension module: `solution_fit`, `requirement_fidelity`, `code_quality`)

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | Three new dimension modules exist, each a descriptor (`name`, `purpose`, `sources_sought`) + `collect` — no base class, no registry, no subclassing | Option D, FR-009 |
| 2 | All four doc-shaped dimensions (incl. `architecture`, refactored) call the shared helper; the helper is used by **exactly** those four | Constraint 8 |
| 3 | Each dimension's `sources_sought` is distinct and appropriate: e.g. `solution-fit` seeks `PRD.md` user stories + `BRAINSTORMING_LOG.md`; `requirement-fidelity` seeks FR/NFR tables + task acceptance criteria; `code-quality` seeks conventions/lint config/`CONTRIBUTING*` | FR-016 |
| 4 | Every `collect` returns `Iterable[Excerpt]` and is lazily consumed | Critical Constraint 3 |
| 5 | Each produces a valid pack in **both** kit-aware and standalone mode, with standalone falling back to docs then code, and carrying the limited-context warning | FR-002, FR-003, FR-004 |
| 6 | No dimension emits a verdict, score, grade or severity — `code-quality` in particular returns evidence about conventions, never a quality judgment | FR-013 |
| 7 | Coverage scores differ across the four for the same repo (proving the `sources_sought` lists are genuinely distinct, not copy-pasted) | FR-016 |
| 8 | Refactoring `architecture` onto the helper changes its pack output in no observable way beyond what the task documents | Surgical Changes |
| 9 | The helper contains no dimension-specific branching (`if name == "code-quality"`) — divergence goes in the dimension, not in the helper | Simplicity First |

---

## Evaluation & Acceptance

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | This repo (kit fixture), each of the 4 dimensions | 4 packs with distinct `files_read`, distinct coverage scores, all excerpts citing real lines | automated test |
| 2 | An installed pip package (standalone fixture), each of the 4 | 4 valid packs, standalone mode, warning present, docs preferred over code | automated test |
| 3 | Each pack | No field name matching a verdict vocabulary (`score` excepted for coverage, `verdict`/`grade`/`severity`/`rating`/`pass` forbidden) | automated test |
| 4 | `architecture` before vs. after the refactor | Equivalent packs | automated test comparing against a committed snapshot |

### Verification Command (exact, runnable)

```bash
pytest tests/test_t007_doc_dimensions.py -q && \
  for d in architecture solution-fit requirement-fidelity code-quality; do \
    python -m easy_verifier.adapters.cli "$d" --repo . | head -5; done
```

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T007.md`.

---

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T007.md`.

---

## Approach

**Pattern reference**: `src/easy_verifier/dimensions/architecture.py` (T001) — the reference shape for every dimension in this project. Match it exactly; the three new modules should read as siblings, not as a framework.

Build the three dimensions **first**, duplicating freely, then extract the helper from what the four
actually share. Extracting first guesses at the abstraction; extracting last observes it. Given that
Option A died from a premature shared abstraction, the ordering here is a deliberate correction, not
a style preference.

The helper's likely real shape is narrow: locate candidate documents from `RepoContext`, find
sections matching a dimension's declared markers, and yield bounded excerpts with accurate line
numbers. Everything genuinely dimension-specific — *which* markers, *which* documents, *what*
counts as a source found — stays as descriptor data.

If the helper starts growing a parameter that only one dimension passes, that is the signal to stop
and leave that logic in the dimension (AC #9).

---

## Edge Case Checklist

- [ ] A source document exists but contains none of the dimension's markers → source counted as found, zero excerpts (found ≠ useful, and conflating them corrupts coverage)
- [ ] Markdown heading variants (`#`/`##`, setext, emoji-prefixed) → section detection is not brittle to formatting
- [ ] A document with no headings at all → whole-file bounded excerpt, not a crash
- [ ] Very large document (`PRD.md` scale and beyond) → bounded excerpts, laziness preserved
- [ ] The same file serving as a source for several dimensions → each reads it independently; no cross-dimension cache that leaks one dimension's budget into another
- [ ] Standalone repo where `README.md` is a stub, or is only a badge wall
- [ ] Standalone repo with docs in a non-Markdown format (`.rst`, `.adoc`, `.txt`)
- [ ] `code-quality` in a repo with no lint config → all sources missing, coverage 0.0, no invented conventions
- [ ] `requirement-fidelity` in standalone mode where there are no FRs to be faithful to → the miss list must make that plain rather than implying compliance
- [ ] Line numbers correct in files with CRLF line endings
- [ ] A document that is a symlink to outside the repo → not followed

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/dimensions/_doc_extract.py` | New — the shared helper (underscore-prefixed: internal, four callers only) |
| `src/easy_verifier/dimensions/solution_fit.py` | New |
| `src/easy_verifier/dimensions/requirement_fidelity.py` | New |
| `src/easy_verifier/dimensions/code_quality.py` | New |
| `src/easy_verifier/dimensions/architecture.py` | Refactor onto the helper — behaviour-preserving |
| `tests/test_t007_doc_dimensions.py` | New |
| `tests/snapshots/architecture_pack.json` | New — the pre-refactor snapshot for AC #8 |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| `.claude/hooks/**` | Must-not-touch |
| `src/easy_verifier/core/pipeline.py` | The contract is fixed; if a dimension seems to need a pipeline change, STOP and ask the Supervisor |
| `src/easy_verifier/core/redact.py`, `budget.py` | Owned by T004/T005 |
| `memory/**`, `PROJECT_KANBAN.md` | Supervisor-only |

---

## Test Plan

`tests/test_t007_doc_dimensions.py` — parameterised across the four dimensions × two modes, using
this repo and an installed pip package as fixtures. Capture the `architecture` pack **before**
starting the refactor and commit it as a snapshot, so AC #8 is a real regression test rather than an
assertion written after the fact. Add a structural test for AC #2 asserting the helper's importers
are exactly the four expected modules — that is what keeps constraint 8 from eroding as T008–T010
land beside it.

---

## Completion Checklist

- [ ] Implementation done
- [ ] Self-review: `Skill({ skill: "code-review" })` run
- [ ] Security review: N/A (Low risk)
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T007.md`'s Evidence table (Hard-Stop Gate 5)
- [ ] `Skill({ skill: "verify" })` run
- [ ] `memory/MEMORY.md` updated (if new patterns or feedback learned)
- [ ] Supervisor notified: task ready for Stage 4 review
