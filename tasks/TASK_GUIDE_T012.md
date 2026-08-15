# TASK_GUIDE — T012: synthesis.py — combined pack + aggregate coverage
**Date**: 2026-08-15
**Complexity Level**: C1
**Risk Level**: Low
**Priority**: P1
**Assigned agent**: Backend-Implementer
**Agent guide**: `.claude/agents/backend.md`

---

## Mandatory Startup (Do Not Skip)

1. Read `PROJECT_SPEC.md`
2. Read `memory/MEMORY.md`
3. Read this file completely
4. Read `.claude/agents/backend.md`
5. **C1** — apply the C1 process from the Complexity matrix in `.claude/agents/general-agent-template.md`
6. Skim `memory/codebase-map.md` for layout

---

## Requirement (Pillar 1 — Adapt the requirement)

Let a caller get several dimensions in one call, with the coverage picture aggregated — without the
engine ever interpreting what the dimensions mean together.

**Restated intent**:
> `combined_pack(dimension_names, repo_path, scope, ...)` runs the named dimensions and returns
> their packs together with an aggregate coverage summary. The engine's contribution to synthesis is
> **aggregation and presentation only**. Deciding what the findings mean together remains the
> calling agent's job.

**Out of scope**:
- Any cross-dimension interpretation, correlation, ranking or narrative (FR-026, FR-013, NFR-001).
- Rendering (T013).

**Requirement Refs**:
- FR-025: combined-pack operation running several named dimensions in one call, with an aggregate coverage summary
- FR-026: cross-dimension synthesis is the caller's, not the engine's — aggregation and presentation only
- FR-013: no verdict from the engine
- FR-016a: coverage never presented without the miss list
- FR-011a/b: budgeting and explicit truncation still apply
- NFR-009: bounded so a multi-dimension call does not exhaust the caller's context

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [ ] **Open design question closed** (see Approach): per-dimension vs. total byte budget in a combined call — decided and recorded before implementation
- [ ] Restated intent confirmed to match the user's request (by Supervisor / user)
- [ ] Domain terms align with `PROJECT_SPEC.md` glossary
- [ ] Every Acceptance Criterion below traces to a line in the Requirement
- [ ] All Requirement Refs exist in `PRD.md` and are fully covered by the Acceptance Criteria above

---

## Dependencies & Reachability

**Depends on**: T007, T008, T009, T010 — all seven dimensions must exist to be combinable.

**Entry point**: `combined_pack`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | `combined_pack(names, ...)` runs each named dimension via `run_dimension()` and returns their packs keyed by dimension | FR-025 |
| 2 | Returns an aggregate coverage summary: per-dimension scores **plus** a combined figure, with the combining method stated in the output | FR-025, FR-016 |
| 3 | The aggregate is always accompanied by the **union of miss lists**, named per dimension | FR-016a |
| 4 | Output contains no cross-dimension narrative, correlation, ranking, priority, or "these findings suggest" text | FR-026, FR-013 |
| 5 | Budget behaviour in a combined call is explicit and documented, and truncation is reported **per dimension**, not merged into one opaque count | FR-011a/b |
| 6 | A dimension that fails does not abort the whole call — its slot carries a structured error and the others still return | Robustness |
| 7 | An unknown dimension name is rejected naming the valid names (which come from `list_dimensions()`, not a duplicated list) | FR-013a |
| 8 | Requesting all seven works and stays bounded | NFR-009 |
| 9 | Requesting one dimension yields a result equivalent to calling `run_dimension()` directly for it | FR-022 consistency |
| 10 | Dimension order in the output is deterministic regardless of the order requested | FR-022 |

---

## Evaluation & Acceptance

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | This repo, all 7 dimensions, `project` scope | 7 packs, per-dimension + aggregate coverage, full union miss list, bounded total size | automated test |
| 2 | `["security"]` only | Pack equivalent to the direct `run_dimension()` call | automated test |
| 3 | `["security", "not-a-dimension"]` | Rejected, naming valid dimensions | automated test |
| 4 | A dimension monkeypatched to raise | Its slot carries the error; the other packs are intact | automated test |
| 5 | `["a","b"]` vs `["b","a"]` | Identical serialized output | automated test |

### Verification Command (exact, runnable)

```bash
pytest tests/test_t012_synthesis.py -q && \
  python -m easy_verifier.adapters.cli combined --repo . --dimensions architecture,security | head -40
```

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T012.md`.

---

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T012.md`.

---

## Approach

**Pattern reference**: `src/easy_verifier/core/pipeline.py` (T001) — `combined_pack` is a thin orchestrator over `run_dimension()`; it must not reimplement any pipeline concern.

**The open design question this task closes** (carried from `memory/NEXT-SESSION.md`): is the byte
budget per-dimension or total across a combined call?

> **Recommendation**: keep the budget **per-dimension** (120 KB each), and report the resulting
> total plainly so a caller requesting all seven knows it is asking for up to ~840 KB. A total
> budget divided across dimensions sounds tidier but makes each pack's contents depend on how many
> other dimensions were requested — the same dimension would return different evidence in a
> combined call than alone, which breaks AC #9 and makes results irreproducible. Add an optional
> `total_budget_bytes` override for callers with a hard ceiling, applied by dropping whole
> dimensions from the tail with an explicit statement, never by silently shrinking each pack.

Decide this with the Supervisor and record it in `memory/decisions.md` before implementing.

AC #4 is the requirement most at risk here: "synthesis" invites summarising, and a helpful-sounding
sentence like "security and test-strategy both show gaps in the auth module" is exactly the engine
reasoning that NFR-001 forbids. Aggregate numbers and grouped packs only.

---

## Edge Case Checklist

- [ ] Empty dimension list → structured error, or a documented "all dimensions" default; decide and test, do not leave it ambiguous
- [ ] Duplicate names in the request (`["security","security"]`) → deduplicated, run once
- [ ] All dimensions fail → a result carrying seven errors, not an exception
- [ ] Aggregate coverage when one dimension has empty `sources_sought` (score `None` from T001) → must not poison the aggregate into `None` or silently count as 0.0
- [ ] Aggregate arithmetic: mean of per-dimension ratios vs. pooled found/sought — these differ; pick one, name it in the output (AC #2)
- [ ] Combined call in standalone mode → the limited-context warning appears once at the top level and is not lost from the individual packs
- [ ] Redaction hits across several dimensions → the `had_redactions` signal for NFR-011 aggregates correctly
- [ ] The same file read by several dimensions → duplicated excerpts across packs are acceptable and expected; do not deduplicate across dimensions, since each pack must stand alone
- [ ] Very large combined result → bounded per AC #8, with per-dimension truncation visible

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/core/synthesis.py` | New — `combined_pack()`, aggregate coverage |
| `src/easy_verifier/core/models.py` | Add `CombinedPack`, `CoverageSummary` |
| `src/easy_verifier/adapters/cli.py` | `combined` subcommand (parsing/serialization only) |
| `tests/test_t012_synthesis.py` | New |
| `memory/decisions.md` | **Supervisor writes** the budget decision — not the agent |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| `.claude/hooks/**` | Must-not-touch |
| `src/easy_verifier/core/pipeline.py`, `budget.py`, `redact.py` | Fixed contracts — orchestrate them, do not modify |
| Dimension modules | Owned by T001/T007–T010 |
| `memory/**`, `PROJECT_KANBAN.md` | Supervisor-only |

---

## Test Plan

`tests/test_t012_synthesis.py` — this repo as the fixture for the realistic all-seven call, and
monkeypatched dimensions for the failure and ordering cases. Include a negative test for AC #4
asserting the combined output contains no free-text narrative field at all — the structural absence
of such a field is a stronger guarantee than checking that it happens to be empty.

---

## Completion Checklist

- [ ] Budget decision recorded in `memory/decisions.md`
- [ ] Implementation done
- [ ] Self-review: `Skill({ skill: "code-review" })` run
- [ ] Security review: N/A (Low risk)
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T012.md`'s Evidence table (Hard-Stop Gate 5)
- [ ] `Skill({ skill: "verify" })` run
- [ ] `memory/MEMORY.md` updated (if new patterns or feedback learned)
- [ ] Supervisor notified: task ready for Stage 4 review
