# TASK_GUIDE — T056: Area rule groups needing new evidence: authN/Z and sessions (#8) and strict type config (#17)
**Date**: 2026-09-29
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

Split from T040 (user, 2026-09-29). The user's 2026-09-28 mapping puts #8 authN/Z, sessions and offboarding in security, and #17 type safety in code-quality. T040 covers #17's type-escape density. The strict type config and #8's cookie/session evidence are not in today's packs.

**Restated intent**:
> security gains a cited #8 rule group (session cookie flags, auth code presence, offboarding documentation) and code-quality gains #17's strict-type-config rule, each over evidence the packs are extended to carry, and never reporting a clean result for code they did not read.

**Out of scope**:
- New dimensions (T041–T046); packs (T047+)
- Weight changes without user sign-off (the agent proposes an old-vs-new weight table and stops)

**Requirement Refs**:
- FR-051: area rule groups
- FR-043: cited rules
- FR-052: documentation parts (offboarding)

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [x] Restated intent confirmed to match the user's request (by Supervisor / user — not the implementing agent) — Supervisor 2026-09-29
- [x] Domain terms align with `PROJECT_SPEC.md` glossary (`grill-with-docs` run if terminology was fuzzy) — Supervisor 2026-09-29
- [x] Every Acceptance Criterion below traces to a line in the Requirement — Supervisor 2026-09-29
- [x] All Requirement Refs exist in `PRD.md` and are fully covered by the Acceptance Criteria above — Supervisor 2026-09-29

> Sign-off note (Supervisor, 2026-09-29): scope is the user's 2026-09-29 split of T040 (#8, #17 strict config). ASVS 5.0.0 was decided by the user. AC2 (auth gating) and AC4 (role vs excerpts) are **user** decisions: propose and stop before building those parts. Weight changes need user sign-off before wiring.

> An agent must NOT start implementing until this gate is checked. If anything here is unclear,
> STOP and ask the Supervisor (Karpathy: Think Before Coding).

---

## Dependencies & Reachability

**Depends on**: T040 — T040 area pattern and weight-table flow; T039 — `DocumentationRule`

**Entry point**: `AREAS` (the `area` labels on the new rules)

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | #8: session cookie flags (secure / httponly / samesite) counted where session or cookie code was observed; **the metric abstains when no session/cookie code was read**, never 0 (miss-list rule); OWASP **ASVS 5.0.0** cited — V3.3 cookies, V7 sessions, V8 authorization (user 2026-09-29) | #8 |
| 2 | #8: "auth code presence" — the agent proposes whether it gates the cookie metric or is a scored rule (scoring would penalise CLI-only repos) and STOPS for the user's decision | #8 |
| 3 | #8: offboarding = T039 `DocumentationRule` (present/missing, never scored), with the security pack reading the matching documents | #8, FR-052 |
| 4 | #17: strict type config present (mypy `strict`, tsconfig `strict`, etc.). The agent proposes a new `type-config` source role (which changes code-quality's coverage denominator) vs targeted excerpts, and STOPS for the user's decision before building | #17 |
| 5 | Each dimension's weights still sum to 100; changed weights listed for **user** sign-off before wiring | rule table integrity |

---

## Evaluation & Acceptance (How we know the agent worked correctly)

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | fixture setting a session cookie without `httponly` | #8 rule unmet, cited file and line | automated test |
| 2 | fixture with no session code | #8 cookie metric abstains with a bounded reason | automated test |
| 3 | tsconfig without `strict` | #17 strict-config rule unmet | automated test |

### Verification Command (exact, runnable)

```bash
python -m pytest -q
python -m ruff check src tests
```

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T056.md`.

---

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T056.md`.

---

## UI / Design Acceptance Criteria

> N/A — pure backend task (no UI component). All three UI Evidence rows are ☐ N/A.

---

## Approach

**Pattern reference**: T035 per-dimension rule data in `core/judge.py`; T039 `area` labels and `DocumentationRule`

Extend evidence selection first (with the two design decisions settled by the user), then metrics, then rules. Cookie and session patterns are registry syntax fields, never hard-coded per language.

---

## Edge Case Checklist

- [ ] Cookie flags set by framework defaults (not visible in code)
- [ ] `strict` inherited through tsconfig `extends`
- [ ] mypy config in `setup.cfg` / `mypy.ini` / `pyproject.toml`
- [ ] Secret-bearing config files stay excluded (DDR-0002)

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/dimensions/security.py` | session/cookie evidence, offboarding doc |
| `src/easy_verifier/dimensions/code_quality.py` | type-config evidence |
| `src/easy_verifier/core/metrics.py` | new metrics |
| `src/easy_verifier/core/judge.py` | rules + documentation rule (after sign-off) |
| `src/easy_verifier/registry/curated/*.toml` | cookie/session syntax fields |
| `tests/` | fixtures |

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
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T056.md`'s Evidence table (Hard-Stop Gate 5)
- [ ] `Skill({ skill: "verify" })` run — feature confirmed working at a real surface
- [ ] `memory/MEMORY.md` updated (if new patterns or feedback learned)
- [ ] Supervisor notified: task ready for Stage 4 review
