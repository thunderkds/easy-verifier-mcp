# TASK_GUIDE — T052: Make requirement-fidelity and blast-radius rate: AC tracing and churn-hotspot evidence
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
7. Read `docs/ddr/0007-cited-reference-registry-and-reference-gate.md` and `BRAINSTORMING_LOG_reference-registry.md` (approved rule table, edge cases)
8. Read `tasks/TASK_REVIEW_T035.md` (why these dimensions always abstain)

---

## Requirement (Pillar 1 — Adapt the requirement)

User sign-off of T035 (2026-09-28, 'Merge + fix tasks'): requirement-fidelity always ends `all_metrics_abstained` (acceptance criteria are never extracted, so `acceptance_criteria_traced_to_code/test_share` are not derivable) and blast-radius abstains at project scope (`max_fan_in_changed` needs a reference search; `changed_files_in_churn_hotspots_share` is 10% by construction at project scope). The overall then averages only 4/7.

**Restated intent**:
> In kit-aware mode requirement-fidelity measures how many acceptance criteria are traced to code and to tests, and blast-radius measures fan-in and churn-hotspot share for the changed files, so both dimensions rate on real repos instead of always abstaining.

**Out of scope**:
- Standalone-mode AC inference (no ACs → honest abstention stays)
- Rule weights/thresholds (T035)
- Data-flow analysis

**Requirement Refs**:
- FR-043: requirement-fidelity ISO/IEC/IEEE 29148 traceability; blast-radius fan-in + churn
- FR-027/027a: metrics from the pack; truncation abstains
- NFR-002: no invented traces

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [ ] Restated intent confirmed to match the user's request (by Supervisor / user — not the implementing agent)
- [ ] Domain terms align with `PROJECT_SPEC.md` glossary (`grill-with-docs` run if terminology was fuzzy)
- [ ] Every Acceptance Criterion below traces to a line in the Requirement
- [ ] All Requirement Refs exist in `PRD.md` and are fully covered by the Acceptance Criteria above

> An agent must NOT start implementing until this gate is checked. If anything here is unclear,
> STOP and ask the Supervisor (Karpathy: Think Before Coding).

---

## Dependencies & Reachability

**Depends on**: T035 — rules exist; metrics currently abstain

**Entry point**: `acceptance_criteria_traced_to_code_share`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | Kit-aware: ACs are extracted from `tasks/TASK_GUIDE_*.md` Acceptance Criteria tables (and PRD FR IDs) into the requirement-fidelity pack with path:line citations | AC extraction |
| 2 | A trace = the AC's task ID / FR ID / distinctive identifier appearing in a source file (code) or a test file (test), found by a bounded search; each trace cited path:line; `…_share` metrics compute from these; standalone mode abstains with its stated reason | honest traces |
| 3 | Blast-radius at changes/worktree scope: `max_fan_in_changed` computes from a bounded reverse-reference search over the repo; hotspot share uses a repo-wide churn ranking (top 10% by local git history) independent of the scope, so it is no longer 10% by construction | blast-radius rates |
| 4 | Real CLI on this repo (kit-aware) and on one external repo: requirement-fidelity rates at project scope; blast-radius rates at `--scope changes --ref <base>`; before/after recorded | real surface |
| 5 | Bounded: searches capped, truncation reported, deterministic order (DDR-0005) | NFR-009 |

---

## Evaluation & Acceptance (How we know the agent worked correctly)

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | kit repo where 3 of 4 ACs' IDs appear in code | `acceptance_criteria_traced_to_code_share` = 0.75 | automated test |
| 2 | changes scope touching a file imported by 25 files | `max_fan_in_changed` = 25 → rule unmet | automated test |

### Verification Command (exact, runnable)

```bash
python -m pytest -q
python -m ruff check src tests
```

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T052.md`.

---

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T052.md`.

---

## UI / Design Acceptance Criteria

> N/A — pure backend task (no UI component). All three UI Evidence rows are ☐ N/A.

---

## Approach

**Pattern reference**: `dimensions/blast_radius.py` `_reference_pattern` single-pass search; `dimensions/_doc_extract.py`

Keep traces textual and cited (no inference). AC IDs: `T\d{3}` task IDs, `FR-\d{3}` IDs, and AC row numbers qualified by task. Churn ranking from existing git co-change mining.

---

## Edge Case Checklist

- [ ] AC IDs mentioned only in docs (not code) must not count as code traces
- [ ] Huge repos: search cap with truncation
- [ ] Shallow clones with little history → hotspot metric abstains with reason

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/dimensions/requirement_fidelity.py` | AC evidence |
| `src/easy_verifier/dimensions/blast_radius.py` | reverse refs + repo-wide churn |
| `src/easy_verifier/core/metrics.py` | replace not-derivable abstentions with real computations |
| `tests/` |  |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| src/easy_verifier/core/judge.py | rules fixed by T035 |

---

## Test Plan

Fixture kit repos with known traces; blast-radius fixtures with known fan-in/churn; real CLI before/after.

---

## Completion Checklist

- [ ] Implementation done
- [ ] Self-review: `Skill({ skill: "code-review" })` run
- [ ] Security review: `Skill({ skill: "security-review" })` run (Medium risk)
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T052.md`'s Evidence table (Hard-Stop Gate 5)
- [ ] `Skill({ skill: "verify" })` run — feature confirmed working at a real surface
- [ ] `memory/MEMORY.md` updated (if new patterns or feedback learned)
- [ ] Supervisor notified: task ready for Stage 4 review
