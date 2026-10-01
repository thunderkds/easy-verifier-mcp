# TASK_GUIDE — T035: Per-dimension cited rules for the existing 7 dimensions (replace the 11 shared rules)
**Date**: 2026-09-28
**Complexity Level**: C3
**Risk Level**: Medium
**Priority**: P0
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
8. Read `docs/ddr/0003-abstain-from-rating-below-coverage-floor.md` and `docs/ddr/0006-any-language-roles-and-agent-hard-gates.md`

---

## Requirement (Pillar 1 — Adapt the requirement)

User (2026-09-28): "which best practice did we refer to score … the source of truth to evaluate"; approved the per-dimension rule table (B5) with metric and threshold cited separately and `project-default` where no standard publishes a number; solution-fit abstains by design.

**Restated intent**:
> Each existing dimension is rated by its own approved rules; every rule input shows its metric citation, threshold citation and `curated` source tag.

**Out of scope**:
- New dimensions and area rule groups (T039–T046)
- Local/agent entries (T036)
- Coverage floors (unchanged, 2026-09-26)

**Requirement Refs**:
- FR-043: per-dimension standards, replaces shared rules
- FR-048 (curated half): source tag + citation per rule input
- FR-028: rules as inspectable static data
- FR-036: solution-fit abstention routes to evaluate gate

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [ ] Restated intent confirmed to match the user's request (by Supervisor / user — not the implementing agent)
- [ ] Domain terms align with `PROJECT_SPEC.md` glossary (`grill-with-docs` run if terminology was fuzzy)
- [ ] Every Acceptance Criterion below traces to a line in the Requirement
- [ ] All Requirement Refs exist in `PRD.md` and are fully covered by the Acceptance Criteria above

> An agent must NOT start implementing until this gate is checked. If anything here is unclear,
> STOP and ask the Supervisor (Karpathy: Think Before Coding).

---

## Dependencies & Reachability

**Depends on**: T033 — CCN/cycle/fan-in metrics; T034 — sink metric; T050 — code-quality/architecture packs carry code evidence

**Entry point**: `RATING_RULES`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | `RATING_RULES` becomes per-dimension data exactly matching the approved table in `BRAINSTORMING_LOG_reference-registry.md`; weights per dimension sum to 100 | approved table |
| 2 | Every `RatingInput` in `score` output carries `metric_citation`, `threshold_citation` (URL or `project-default`) and `source_tag` | cited + tagged |
| 3 | solution-fit always returns a `RatingAbstention` with a new reason code (e.g. `no_static_rule`), which triggers the FR-036 evaluate gate | solution-fit by design |
| 4 | CLI/MCP parity (DDR-0005) holds; report renders citations as links | surfaces |
| 5 | HITL: run `score` on this repo and on kitchd/bryony/ai-training (as in T028) and paste before/after per-dimension numbers for Supervisor/user sign-off | user confirms real-repo behaviour |

---

## Evaluation & Acceptance (How we know the agent worked correctly)

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | this repo, `score --scope project` | 7 dimensions rated/abstained per new rules, each input cited | automated + app run |
| 2 | fixture with 30% of functions CCN>10 | code-quality CCN rule unmet (0 of 40) | automated test |

### Verification Command (exact, runnable)

```bash
python -m pytest -q
python -m ruff check src tests
docker compose build && bash scripts/verify_container.sh
```

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T035.md`.

---

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T035.md`.

---

## UI / Design Acceptance Criteria

> N/A — pure backend task (no UI component). All three UI Evidence rows are ☐ N/A.

---

## Approach

**Pattern reference**: `core/judge.py` `rate()` — keep the arithmetic and abstention flow; change only rule lookup and `RatingInput` fields

Minimal change to `rate()`: `RATING_RULES[dimension]`. Validation (`_validate_declared_data`) extended to check per-dimension weight sums and citation presence. Update README 'rating' section and doc-truth test.

---

## Edge Case Checklist

- [ ] A dimension whose every metric abstains → `all_metrics_abstained` unchanged
- [ ] Borderline band (FR-036) with new thresholds — threshold 0 never borderline still holds
- [ ] Report and MCP payload size (NFR-009) with added citation strings

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/core/judge.py` | per-dimension rules + citations |
| `src/easy_verifier/core/report.py` | render citations/tags |
| `README.md` | rating methodology section |
| `tests/` | rule table + parity + doc-truth |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| COVERAGE_FLOORS values | user decision 2026-09-26 |
| capped blend constants | FR-038 |

---

## Test Plan

Rule-table conformance test (data equals approved table); per-dimension rating fixtures; parity test; real-repo run evidence.

---

## Completion Checklist

- [ ] Implementation done
- [ ] Self-review: `Skill({ skill: "code-review" })` run
- [ ] Security review: `Skill({ skill: "security-review" })` run (Medium risk)
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T035.md`'s Evidence table (Hard-Stop Gate 5)
- [ ] `Skill({ skill: "verify" })` run — feature confirmed working at a real surface
- [ ] `memory/MEMORY.md` updated (if new patterns or feedback learned)
- [ ] Supervisor notified: task ready for Stage 4 review
