# TASK_GUIDE — T045: New dimension: data (#4 data model, constraints, migrations)
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
7. Read `docs/ddr/0008-thirteen-dimensions-rule-groups-and-optional-packs.md` and `BRAINSTORMING_LOG_evaluation-areas.md` (32-area mapping table)
8. Read `docs/ddr/0007-cited-reference-registry-and-reference-gate.md` and `BRAINSTORMING_LOG_reference-registry.md` (approved rule table, edge cases)

---

## Requirement (Pillar 1 — Adapt the requirement)

User (2026-09-28) 32-area list; decided E2: add the `data` dimension holding areas #4 data model, constraints, migrations. Mapping and standards per `BRAINSTORMING_LOG_evaluation-areas.md`.

**Restated intent**:
> A `data` dimension gathers bounded evidence from its roles and rates the areas #4 data model, constraints, migrations with cited registry rules; unverifiable parts show documentation present/missing.

**Out of scope**:
- Other new dimensions
- Live-system facts (cloud state, CVE feeds, running services) — reported as not verifiable offline

**Requirement Refs**:
- FR-050: new dimension with roles, floor, cited rules
- FR-051: area rule groups
- FR-052: documentation rule for unverifiable parts
- NFR-009: bounded pack

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [ ] Restated intent confirmed to match the user's request (by Supervisor / user — not the implementing agent)
- [ ] Domain terms align with `PROJECT_SPEC.md` glossary (`grill-with-docs` run if terminology was fuzzy)
- [ ] Every Acceptance Criterion below traces to a line in the Requirement
- [ ] All Requirement Refs exist in `PRD.md` and are fully covered by the Acceptance Criteria above

> An agent must NOT start implementing until this gate is checked. If anything here is unclear,
> STOP and ask the Supervisor (Karpathy: Think Before Coding).

---

## Dependencies & Reachability

**Depends on**: T039 — rule groups, doc rule, N-dimension overall

**Entry point**: `data`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | Dimension `data` is discoverable (FR-013a) with purpose and source roles: migration dirs, schema files (SQL, Prisma, Alembic, ActiveRecord, Flyway/Liquibase) | discoverable |
| 2 | Rules (area → metric → threshold, each with metric/threshold citation): migrations present when a schema exists; each migration has a down/rollback (project `migration-safety` checklist); FK/NOT NULL/unique constraints declared in schema (ISO/IEC 5055); destructive ops (DROP/ALTER ... DROP) flagged for the evaluate gate | cited rules |
| 3 | Language/tool-specific patterns live in the registry, not in the dimension module | one source of truth |
| 4 | **HITL — coverage floor.** Propose this dimension's coverage floor with a one-line rationale and STOP for Supervisor/user approval before committing it (floors are user decisions; see `memory/decisions.md` 2026-09-26). | floor is a user decision |
| 5 | Fixture repo where every rule is met rates 100; fixture with none of the roles abstains with named misses | boundaries |

---

## Evaluation & Acceptance (How we know the agent worked correctly)

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | positive fixture repo | all rules met, cited | automated test |
| 2 | repo with no matching files | abstains below floor with misses | automated test |

### Verification Command (exact, runnable)

```bash
python -m pytest -q
python -m ruff check src tests
```

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T045.md`.

---

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T045.md`.

---

## UI / Design Acceptance Criteria

> N/A — pure backend task (no UI component). All three UI Evidence rows are ☐ N/A.

---

## Approach

**Pattern reference**: `dimensions/security.py` / `dimensions/test_strategy.py` — bespoke dimension with roles + bounded collect

Follow the existing dimension contract (static descriptor + `collect`). Keep rules few and conservative; anything needing judgment goes to the evaluate gate rather than a guessed rule.

---

## Edge Case Checklist

- [ ] ORM-managed schema without migration files
- [ ] Irreversible data migrations marked explicitly
- [ ] Monorepo with several services — evidence budget per dimension, not pooled
- [ ] No files for this dimension at all (e.g. library repo) → abstain, never 0

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/dimensions/data.py` | new dimension |
| `src/easy_verifier/registry/curated/*.toml` | patterns this dimension needs |
| `src/easy_verifier/core/judge.py` | rules + floor (after approval) |
| `README.md` | dimension table |
| `tests/` | fixtures |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| other dimensions' modules | surgical scope |

---

## Test Plan

Positive/negative fixture repos; abstention test; discovery test; doc-truth test for README table.

---

## Completion Checklist

- [ ] Implementation done
- [ ] Self-review: `Skill({ skill: "code-review" })` run
- [ ] Security review: `Skill({ skill: "security-review" })` run (Medium risk)
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T045.md`'s Evidence table (Hard-Stop Gate 5)
- [ ] `Skill({ skill: "verify" })` run — feature confirmed working at a real surface
- [ ] `memory/MEMORY.md` updated (if new patterns or feedback learned)
- [ ] Supervisor notified: task ready for Stage 4 review
