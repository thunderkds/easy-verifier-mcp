# TASK_GUIDE — T049: Frontend accessibility pack (#19 accessibility, responsive UX, browser compatibility)
**Date**: 2026-09-28
**Complexity Level**: C2
**Risk Level**: Medium
**Priority**: P2
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

Decided E1/G8: frontend a11y is an optional pack, active when a frontend framework is detected (on demand) or configured; area #19.

**Restated intent**:
> When active, the pack statically checks markup for WCAG 2.2 basics, viewport configuration and declared browser support.

**Out of scope**:
- Rendering or running the UI (no execution)
- Visual contrast checks needing computed styles

**Requirement Refs**:
- FR-053
- FR-044 (framework detection activates)
- FR-043 (cited rules)

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [ ] Restated intent confirmed to match the user's request (by Supervisor / user — not the implementing agent)
- [ ] Domain terms align with `PROJECT_SPEC.md` glossary (`grill-with-docs` run if terminology was fuzzy)
- [ ] Every Acceptance Criterion below traces to a line in the Requirement
- [ ] All Requirement Refs exist in `PRD.md` and are fully covered by the Acceptance Criteria above

> An agent must NOT start implementing until this gate is checked. If anything here is unclear,
> STOP and ask the Supervisor (Karpathy: Think Before Coding).

---

## Dependencies & Reachability

**Depends on**: T047 — pack mechanism

**Entry point**: `frontend-a11y`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | `<img>` without `alt` = 0; form inputs without label/aria-label = 0; `aria-hidden` on focusable elements = 0 (WCAG 2.2 SC 1.1.1, 1.3.1, 4.1.2 cited) | a11y basics |
| 2 | Viewport meta present in HTML entry; `browserslist` (or equivalent) declared | responsive + browser compat |
| 3 | JSX/TSX/Vue/Svelte syntax patterns come from registry framework entries | on-demand frameworks |
| 4 | Pack inactive for backend-only repos | optional |

---

## Evaluation & Acceptance (How we know the agent worked correctly)

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | React component `<img src=x>` | rule unmet with path:line | automated test |
| 2 | `<img alt="" …>` decorative | met (empty alt allowed) | automated test |

### Verification Command (exact, runnable)

```bash
python -m pytest -q
python -m ruff check src tests
```

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T049.md`.

---

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T049.md`.

---

## UI / Design Acceptance Criteria

> N/A — pure backend task (no UI component). All three UI Evidence rows are ☐ N/A.

---

## Approach

**Pattern reference**: T047 healthcare pack

Token patterns over markup after stripping comments; conservative; every hit cited with WCAG SC link.

---

## Edge Case Checklist

- [ ] Spread props that may carry alt (`{...props}`) → not counted as missing, listed as not verifiable
- [ ] Server-rendered templates (Jinja, ERB)

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/registry/packs/frontend-a11y.toml` | new |
| `src/easy_verifier/core/metrics.py` | pack metrics |
| `tests/` |  |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| healthcare/finance packs | separate |

---

## Test Plan

JSX/Vue/HTML fixtures for each rule.

---

## Completion Checklist

- [ ] Implementation done
- [ ] Self-review: `Skill({ skill: "code-review" })` run
- [ ] Security review: `Skill({ skill: "security-review" })` run (Medium risk)
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T049.md`'s Evidence table (Hard-Stop Gate 5)
- [ ] `Skill({ skill: "verify" })` run — feature confirmed working at a real surface
- [ ] `memory/MEMORY.md` updated (if new patterns or feedback learned)
- [ ] Supervisor notified: task ready for Stage 4 review
