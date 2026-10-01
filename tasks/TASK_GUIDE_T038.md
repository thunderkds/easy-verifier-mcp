# TASK_GUIDE — T038: User review gate for researched entries (good / needs improvement / reject)
**Date**: 2026-09-28
**Complexity Level**: C2
**Risk Level**: Medium
**Priority**: P1
**Assigned agent**: backend-developer
**Agent guide**: `.claude/agents/backend.md`

---

## Mandatory Startup (Do Not Skip)

Before writing any code:
1. Read `PROJECT_SPEC.md`
2. Read `memory/MEMORY.md`
3. Read this file completely
4. Read `.claude/agents/backend.md`
5. Note the **Complexity Level** above and apply the matching process from the Complexity matrix in `.claude/agents/general-agent-template.md`
6. Read `memory/codebase-map.md`
7. Read `docs/ddr/0007-cited-reference-registry-and-reference-gate.md` and `BRAINSTORMING_LOG_reference-registry.md` (approved rule table, edge cases)

---

## Requirement (Pillar 1 — Adapt the requirement)

User (2026-09-28): "dont like the thing that users need to copy by hand"; "how about we should ask the user for the result, is it good, need to improve? we depend on that to make the decision".

**Restated intent**:
> Each new local entry is shown to the user once through the calling agent; the answer sets its status, and approved entries are tagged as such from then on.

**Out of scope**:
- Manual promotion to curated (rejected by user)
- Changing weights by status (pending scores immediately, G4)

**Requirement Refs**:
- FR-047: review gate, statuses, pending scores immediately
- FR-048: tag `agent-researched (user-approved)`

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [ ] Restated intent confirmed to match the user's request (by Supervisor / user — not the implementing agent)
- [ ] Domain terms align with `PROJECT_SPEC.md` glossary (`grill-with-docs` run if terminology was fuzzy)
- [ ] Every Acceptance Criterion below traces to a line in the Requirement
- [ ] All Requirement Refs exist in `PRD.md` and are fully covered by the Acceptance Criteria above

> An agent must NOT start implementing until this gate is checked. If anything here is unclear,
> STOP and ask the Supervisor (Karpathy: Think Before Coding).

---

## Dependencies & Reachability

**Depends on**: T037 — reference gate

**Entry point**: `review_status`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | Local entries carry `review_status` ∈ {pending, approved}; new entries start `pending` | statuses |
| 2 | MCP `score` returns `needs_input.review` listing pending entries (value + link) once each; agent input `reviews: {entry_id: good|improve|reject, comment?}` | ask once |
| 3 | good → `approved`, tag `agent-researched (user-approved)`; improve → entry stays pending, comment returned in the next reference gate for that field; reject → entry deleted, its rules abstain | decision semantics |
| 4 | A reviewed entry is never asked again | asked once |

---

## Evaluation & Acceptance (How we know the agent worked correctly)

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | pending entry + review `good` | status approved, tag updated | automated test |
| 2 | pending entry + review `reject` | entry removed, dependent rule abstains | automated test |

### Verification Command (exact, runnable)

```bash
python -m pytest -q
python -m ruff check src tests
```

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T038.md`.

---

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T038.md`.

---

## UI / Design Acceptance Criteria

> N/A — pure backend task (no UI component). All three UI Evidence rows are ☐ N/A.

---

## Approach

**Pattern reference**: `core/gate.py` gate request/response round trip (T027/T028)

Store status beside the entry in the SOT file; review answers are agent input, so replay stays deterministic.

---

## Edge Case Checklist

- [ ] Review for an entry id that no longer exists → ignored with warning
- [ ] `improve` loop bound: after 2 improve rounds, fall back to asking the user for the value directly (grill-style)

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/core/registry.py` | status field |
| `src/easy_verifier/core/gate.py` | review gate |
| `src/easy_verifier/core/roles.py` | agent-input `reviews` |
| `tests/` | review flow |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| registry/curated/* | release-only |

---

## Test Plan

Status transition tests; ask-once test; reject→abstain test.

---

## Completion Checklist

- [ ] Implementation done
- [ ] Self-review: `Skill({ skill: "code-review" })` run
- [ ] Security review: `Skill({ skill: "security-review" })` run (Medium risk)
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T038.md`'s Evidence table (Hard-Stop Gate 5)
- [ ] `Skill({ skill: "verify" })` run — feature confirmed working at a real surface
- [ ] `memory/MEMORY.md` updated (if new patterns or feedback learned)
- [ ] Supervisor notified: task ready for Stage 4 review
