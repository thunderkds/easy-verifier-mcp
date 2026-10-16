# TASK_GUIDE — T111: Docs — how to read a change score now that `change_risk` exists
**Date**: 2026-10-16
**Complexity Level**: C0
**Risk Level**: Low (documentation only)
**Priority**: P1
**Assigned agent**: backend-developer
**Agent guide**: `.claude/agents/backend.md`

---

## Mandatory Startup (Do Not Skip)

Before writing anything:
1. Read `PROJECT_SPEC.md` (glossary: **Change kind**, **Change risk**, **Context role**, **Matched test**)
2. Read `memory/MEMORY.md`
3. Read this file completely
4. Read `.claude/agents/backend.md`
5. Read `PRD.md` FR-078–FR-083 and `tasks/TASK_REVIEW_T107.md` … `TASK_REVIEW_T110.md` (the real results to quote)

---

## Requirement (Pillar 1 — Adapt the requirement)

Change-risk slice 1 (T107–T110) is merged, but the user-facing guides still describe the old behaviour:
README § "Checking a feature or bugfix" says a bugfix without a regression test "is **not penalised**"
and quotes the old score of 97.

**Restated intent**:
> Update the user-facing docs so a reader checking a feature or bugfix knows: (1) `change_risk` is a
> separate headline next to `overall`, rated only at `changes`/`worktree` scope and never averaged into
> `overall`; (2) the change kind (bugfix/feature/refactor/chore) is detected from branch, commit
> subjects, issue references and file kinds, and through MCP the agent is asked to confirm it (CLI:
> `--agent-input <file>` with `{"change_kind": {"value": …, "reason": …}}`); (3) what each kind requires
> (the FR-082 rule table); (4) context roles are now read repository-wide, so fewer dimensions abstain;
> (5) the measured before/after example (node-monorepo bugfix without a test: overall 97 → 85,
> `change_risk` 0).

**Out of scope**: any code or test change; S2–S5 (mention them only as "not yet").

**Requirement Refs**: FR-078–FR-083, US-022.

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [x] Restated intent confirmed (Supervisor, 2026-10-16)
- [x] Domain terms align with `PROJECT_SPEC.md`
- [x] Every Acceptance Criterion traces to the Requirement
- [x] Requirement Refs exist in `PRD.md`

---

## Dependencies & Reachability

**Depends on**: T110
**Entry point**: `Standalone — N/A: documentation`

---

## Acceptance Criteria

| # | Criterion (testable) |
|---|----------------------|
| 1 | README § "Checking a feature or bugfix": the "Read a change score as partial (2026-10-05)" note is replaced by an accurate section covering points (1)–(5); the commands shown still work verbatim |
| 2 | `docs/DOCKER_MCP_GUIDE.md` and `docs/EVALUATION_GUIDE.md`: every passage about the changes scope agrees with the README (same facts, no contradiction); EVALUATION_GUIDE explains how to read the `change_risk` headline and `change_kind.source` |
| 3 | A CLI example with `--agent-input` uses a file path (the CLI takes a path), with the exact JSON shape |
| 4 | No private repository name or absolute path (aliases only); the T100 guard and the README/doc pin tests (`test_t018_readme`, `test_t035_cited_rules`, `test_t072*` if present) stay green |

---

## Evaluation & Acceptance

### Success Criteria (observable, pass/fail)
- `grep -n "not penalised" README.md docs/*.md` → no match.
- Pin tests and T100 guard pass.

### Verification Command (exact, runnable)

```bash
grep -rn "not penalised\|change score as partial" README.md docs/DOCKER_MCP_GUIDE.md docs/EVALUATION_GUIDE.md; echo "exit=$?"   # expect exit=1
<py312> -m pytest -q tests/test_t018_readme.py tests/test_t035_cited_rules.py tests/test_t100_no_personal_identifiers.py
```

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T111.md`.

---

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T111.md`. BEFORE = the verbatim current README note (lines starting
> "> **Read a change score as partial (2026-10-05).**").

---

## UI / Design Acceptance Criteria

> N/A — documentation. All three UI Evidence rows are ☐ N/A.

---

## Approach

Edit the three docs; quote only numbers recorded in the T107–T110 review files.

## Edge Case Checklist

- [ ] `docs/` is git-ignored except force-added guides: `git add -f` the edited guides, as before

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `README.md` | § Checking a feature or bugfix |
| `docs/DOCKER_MCP_GUIDE.md`, `docs/EVALUATION_GUIDE.md` | matching passages |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| `src/`, `tests/` | docs only |

## Test Plan

Existing doc pin tests + T100 guard; the grep in the verification command.

## Completion Checklist

- [ ] Committed on `docs/T111-change-risk-docs`
- [ ] Verification output pasted into `tasks/TASK_REVIEW_T111.md`
- [ ] Supervisor notified: ready for Stage 4 review
