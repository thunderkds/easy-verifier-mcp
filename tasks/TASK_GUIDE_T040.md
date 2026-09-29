# TASK_GUIDE — T040: Area rule groups inside existing dimensions (#5, #8, #16, #17, #27, #31)
**Date**: 2026-09-28
**Complexity Level**: C3
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
7. Read `docs/ddr/0008-thirteen-dimensions-rule-groups-and-optional-packs.md` and `BRAINSTORMING_LOG_evaluation-areas.md` (32-area mapping table)
8. Read `docs/ddr/0007-cited-reference-registry-and-reference-gate.md` and `BRAINSTORMING_LOG_reference-registry.md` (approved rule table, edge cases)

---

## Requirement (Pillar 1 — Adapt the requirement)

User (2026-09-28) 32-area list; mapping puts #5 backward compatibility (blast-radius), #8 authN/Z & sessions (security), #16 false confidence & isolation (test-strategy), #17 type safety and #31 tech-debt lifecycle (code-quality), #27 documentation source of truth (requirement-fidelity) into existing dimensions.

**Restated intent**:
> Existing dimensions gain the cited rule groups for these six areas, labelled by area.

**Out of scope**:
- New dimensions (T041–T046)
- Packs (T047+)

**Requirement Refs**:
- FR-051: area rule groups
- FR-043: cited rules
- FR-052: documentation parts (e.g. offboarding in #8)

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [x] Restated intent confirmed to match the user's request (by Supervisor / user — not the implementing agent) — Supervisor 2026-09-29
- [x] Domain terms align with `PROJECT_SPEC.md` glossary (`grill-with-docs` run if terminology was fuzzy) — Supervisor 2026-09-29
- [x] Every Acceptance Criterion below traces to a line in the Requirement — Supervisor 2026-09-29
- [x] All Requirement Refs exist in `PRD.md` and are fully covered by the Acceptance Criteria above — Supervisor 2026-09-29

> Sign-off note (Supervisor, 2026-09-29): the six areas and their dimensions are the user's 2026-09-28 mapping, verbatim. "Rule group" = the T039 `area` label (FR-051). AC7 weight changes alter existing scores, so they need **user** sign-off before they are wired into `RATING_RULES`.

> An agent must NOT start implementing until this gate is checked. If anything here is unclear,
> STOP and ask the Supervisor (Karpathy: Think Before Coding).

---

## Dependencies & Reachability

**Depends on**: T039 — rule groups + doc rule

**Entry point**: `AREAS` (corrected by Supervisor 2026-09-29: T039 implemented a rule group as the `area` label on rule data, taken from `judge.AREAS`, per FR-051. There is no separate `rule_group` structure; do not invent one)

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | #5 (changes scope): removed/renamed public symbols and destructive migration ops counted; SemVer 2.0 cited | #5 |
| 2 | #8: session cookie flags (secure/httponly/samesite) and auth code presence; offboarding = documentation present/missing; OWASP ASVS V2–V4 cited | #8 |
| 3 | #16: tests without assertions, skipped/disabled tests, network calls in unit tests counted; ISO/IEC/IEEE 29119 cited | #16 |
| 4 | #17: strict type config present (mypy strict, tsconfig `strict`, etc.) and `any`/type-ignore density; ISO/IEC 5055 cited | #17 |
| 5 | #27: single spec/PRD source + docs co-changed with code (git history); ISO/IEC/IEEE 26514 cited | #27 |
| 6 | #31: TODO/FIXME share with vs without a ticket reference; SQALE/ISO 5055 cited | #31 |
| 7 | Each dimension's weights still sum to 100; changed weights listed for Supervisor sign-off | rule table integrity |

---

## Evaluation & Acceptance (How we know the agent worked correctly)

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | fixture test file with a test lacking assertions | #16 rule reports it | automated test |
| 2 | tsconfig without strict | #17 rule unmet | automated test |

### Verification Command (exact, runnable)

```bash
python -m pytest -q
python -m ruff check src tests
```

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T040.md`.

---

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T040.md`.

---

## UI / Design Acceptance Criteria

> N/A — pure backend task (no UI component). All three UI Evidence rows are ☐ N/A.

---

## Approach

**Pattern reference**: T035 per-dimension rule data in `core/judge.py`

Add metrics and rules only; reuse T033 tokenizer for comment/TODO scanning. Language-specific syntax (type-ignore markers, skip decorators) goes to the registry.

---

## Edge Case Checklist

- [ ] `@pytest.mark.skip` with reason vs without
- [ ] Generated type stubs
- [ ] TODO inside string literals

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/core/metrics.py` | new metrics |
| `src/easy_verifier/core/judge.py` | rule groups |
| `src/easy_verifier/registry/curated/*.toml` | syntax fields |
| `tests/` |  |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| dimension evidence budgets | NFR-009 decisions |

---

## Test Plan

Fixture per area; weight-sum validation test.

---

## Completion Checklist

- [ ] Implementation done
- [ ] Self-review: `Skill({ skill: "code-review" })` run
- [ ] Security review: `Skill({ skill: "security-review" })` run (Medium risk)
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T040.md`'s Evidence table (Hard-Stop Gate 5)
- [ ] `Skill({ skill: "verify" })` run — feature confirmed working at a real surface
- [ ] `memory/MEMORY.md` updated (if new patterns or feedback learned)
- [ ] Supervisor notified: task ready for Stage 4 review
