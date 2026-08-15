# TASK_GUIDE — T011: dimension discovery operation
**Date**: 2026-08-15
**Complexity Level**: C0
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
5. **C0** — smallest viable process; single-purpose change, no decomposition needed
6. C0 — `memory/codebase-map.md` may be skipped

---

## Requirement (Pillar 1 — Adapt the requirement)

Let a calling agent find out what dimensions exist and what each one looks for, without reading the
verifier's source code.

**Restated intent**:
> `list_dimensions()` returns every available dimension with its name, human-readable purpose, and
> declared `sources_sought` list. Both adapters expose it. A caller can therefore choose the right
> dimensions for its question from the tool surface alone.

**Out of scope**:
- Any per-repo information — discovery describes the *engine*, not a target. It takes no repo path.
- Recommending which dimension to use (that is the caller's reasoning, FR-013).

**Requirement Refs**:
- FR-013a: expose a discovery operation listing every dimension with its purpose and `sources_sought`, available in both adapters
- US-011: a reviewing agent can discover dimensions without reading the source

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [ ] Restated intent confirmed to match the user's request (by Supervisor / user)
- [ ] Domain terms align with `PROJECT_SPEC.md` glossary
- [ ] Every Acceptance Criterion below traces to a line in the Requirement
- [ ] All Requirement Refs exist in `PRD.md` and are fully covered by the Acceptance Criteria above

---

## Dependencies & Reachability

**Depends on**: T007, T008, T009, T010 — all seven descriptors must exist for discovery to be complete and for AC #2 to be assertable.

**Entry point**: `list_dimensions`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | `list_dimensions()` returns, per dimension: `name`, `purpose`, `sources_sought` | FR-013a |
| 2 | Exactly **seven** entries: architecture, solution-fit, requirement-fidelity, test-strategy, security, blast-radius, code-quality | FR-010, FR-013a |
| 3 | Output is derived from the dimension descriptors themselves — **not** a hand-maintained list that can drift | FR-013a |
| 4 | A test fails if a new dimension module is added and does not appear in discovery | FR-013a |
| 5 | Takes no repo path and touches no filesystem outside the package | FR-013a |
| 6 | Order is deterministic across runs and adapters | FR-022 |
| 7 | Every `purpose` is a real sentence a caller can act on, not a restatement of the name | US-011 |

---

## Evaluation & Acceptance

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | `list_dimensions()` | 7 entries, each with a non-empty purpose and a non-empty `sources_sought` | automated test |
| 2 | Called twice | Identical order and content | automated test |
| 3 | A dimension module added to the package in a test | Appears in discovery without any other edit | automated test |

### Verification Command (exact, runnable)

```bash
pytest tests/test_t011_discovery.py -q && python -m easy_verifier.adapters.cli list-dimensions
```

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T011.md`.

---

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T011.md`.

---

## Approach

**Pattern reference**: `src/easy_verifier/dimensions/architecture.py` (T001) — the descriptor is already the data discovery needs; this task only surfaces it.

Derive the list by enumerating the descriptor objects in `easy_verifier.dimensions` (AC #3). A
hand-written list is the obvious shortcut and the obvious future bug: it drifts the first time
someone adds a dimension, and the drift is invisible because discovery still returns a plausible
answer.

Note that Option D forbids a registry — enumerate the modules' descriptors at call time; do not
introduce an `@register` decorator or an import-time registry dict to make this convenient.

Sort by a fixed key for AC #6. The MCP adapter (T014) and CLI (T015) both call this one function; do
not implement it twice.

---

## Edge Case Checklist

- [ ] A module in `dimensions/` that is not a dimension (`_doc_extract.py`) → excluded, by an explicit rule rather than by luck of naming
- [ ] A descriptor with an empty `sources_sought` → surfaced honestly rather than hidden
- [ ] Import errors in one dimension module → discovery fails loudly naming the module, rather than silently returning six
- [ ] Deterministic order under a different filesystem enumeration order (AC #6)
- [ ] Name formatting consistency: the CLI uses `solution-fit` while the module is `solution_fit` → one canonical external name, mapped in one place

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/dimensions/__init__.py` | Add `list_dimensions()` — descriptor enumeration |
| `src/easy_verifier/adapters/cli.py` | `list-dimensions` subcommand (serialization only) |
| `tests/test_t011_discovery.py` | New |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| `.claude/hooks/**` | Must-not-touch |
| `src/easy_verifier/core/**` | No core change is needed for this task |
| Individual dimension modules | Owned by T001/T007–T010; if a `purpose` string is weak, report it to the Supervisor rather than editing |
| `memory/**`, `PROJECT_KANBAN.md` | Supervisor-only |

---

## Test Plan

`tests/test_t011_discovery.py` — assert the exact set of seven names, assert derivation rather than
hand-maintenance by adding a throwaway dimension module in a `tmp_path`-based package fixture and
confirming it appears (AC #3, #4), and assert determinism by comparing two serialized calls.

---

## Completion Checklist

- [ ] Implementation done
- [ ] Self-review: `Skill({ skill: "code-review" })` run
- [ ] Security review: N/A (Low risk)
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T011.md`'s Evidence table (Hard-Stop Gate 5)
- [ ] `Skill({ skill: "verify" })` run
- [ ] `memory/MEMORY.md` updated (if new patterns or feedback learned)
- [ ] Supervisor notified: task ready for Stage 4 review
