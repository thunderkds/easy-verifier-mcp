# TASK_GUIDE — T055: Area rule groups needing git evidence: backward compatibility (#5) and documentation source of truth (#27)
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

Split from T040 (user, 2026-09-29). The user's 2026-09-28 mapping puts #5 backward compatibility in blast-radius and #27 documentation source of truth in requirement-fidelity. Neither dimension's pack carries the evidence today: #5 needs the diff content of the change, and #27 needs git co-change history.

**Restated intent**:
> blast-radius gains a cited #5 rule group over removed or renamed public symbols and destructive migration operations in the change, and requirement-fidelity gains a cited #27 rule group over a single spec/PRD source and docs co-changed with code, each from read-only git evidence the collectors now record.

**Out of scope**:
- New dimensions (T041–T046); packs (T047+)
- Weight changes without user sign-off (the agent proposes an old-vs-new weight table and stops)

**Requirement Refs**:
- FR-051: area rule groups
- FR-043: cited rules

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [ ] Restated intent confirmed to match the user's request (by Supervisor / user — not the implementing agent)
- [ ] Domain terms align with `PROJECT_SPEC.md` glossary (`grill-with-docs` run if terminology was fuzzy)
- [ ] Every Acceptance Criterion below traces to a line in the Requirement
- [ ] All Requirement Refs exist in `PRD.md` and are fully covered by the Acceptance Criteria above

> An agent must NOT start implementing until this gate is checked. If anything here is unclear,
> STOP and ask the Supervisor (Karpathy: Think Before Coding).

---

## Dependencies & Reachability

**Depends on**: T040 — T040 area pattern and weight-table flow; T051 — hardened git runner

**Entry point**: `AREAS` (the `area` labels on the new rules)

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | #5 (changes scope): removed/renamed public symbols and destructive migration ops (drop table/column, rename) counted from the read-only git diff of the scoped change; SemVer 2.0 cited; area `Backward compatibility & upgrade safety` | #5 |
| 2 | #5 outside a change scope (no diff): the metric abstains with a reason naming the scope, never 0 | miss-list rule |
| 3 | #27: single spec/PRD source (one canonical requirements doc, not several competing ones) and docs co-changed with code (share of code-changing commits in a bounded window that also touch docs); ISO/IEC/IEEE 26514 cited; area `Documentation source-of-truth governance` | #27 |
| 4 | New collector evidence goes through the existing read-only git runner (hardened in T051), is bounded, and says what bounded it; `models.py` pack changes are additive, and existing pack JSON is byte-identical when unused | NFR / DDR-0005 |
| 5 | Each dimension's weights still sum to 100; changed weights listed for **user** sign-off before wiring | rule table integrity |

---

## Evaluation & Acceptance (How we know the agent worked correctly)

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | fixture repo whose change removes a public function | #5 metric counts 1, cited file and line | automated test |
| 2 | `--scope project` (no diff) | #5 abstains, reason names the scope | automated test |
| 3 | repo with two competing PRD files, or code commits never touching docs | #27 rule unmet | automated test |

### Verification Command (exact, runnable)

```bash
python -m pytest -q
python -m ruff check src tests
```

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T055.md`.

---

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T055.md`.

---

## UI / Design Acceptance Criteria

> N/A — pure backend task (no UI component). All three UI Evidence rows are ☐ N/A.

---

## Approach

**Pattern reference**: T035 per-dimension rule data in `core/judge.py`; T039 `area` labels and `DocumentationRule`

Record the new facts in the collectors through the existing safe git runner; compute the metrics in `metrics.py`; label the rules with `judge.AREAS`. Public-symbol detection is textual (registry syntax fields), like T010's blast-radius, and says so.

---

## Edge Case Checklist

- [ ] Rename vs remove-and-add
- [ ] Migration file added vs edited
- [ ] Shallow clone or no git history (abstain, with a reason)
- [ ] Merge commits in the co-change window

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/dimensions/blast_radius.py` | diff facts for #5 |
| `src/easy_verifier/dimensions/requirement_fidelity.py` | co-change facts for #27 |
| `src/easy_verifier/models.py` | additive pack fields |
| `src/easy_verifier/core/metrics.py` | new metrics |
| `src/easy_verifier/core/judge.py` | rules (after weight sign-off) |
| `tests/` | fixtures with git history |

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
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T055.md`'s Evidence table (Hard-Stop Gate 5)
- [ ] `Skill({ skill: "verify" })` run — feature confirmed working at a real surface
- [ ] `memory/MEMORY.md` updated (if new patterns or feedback learned)
- [ ] Supervisor notified: task ready for Stage 4 review
