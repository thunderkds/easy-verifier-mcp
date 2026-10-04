# TASK_GUIDE — T070: Report readability — summary, plan cards, merged unknowns, progressive disclosure
**Date**: 2026-10-04
**Complexity Level**: C2
**Risk Level**: Medium
**Priority**: P1
**Assigned agent**: backend-developer
**Agent guide**: `.claude/agents/backend.md`

---

## Mandatory Startup (Do Not Skip)

1. Read `PROJECT_SPEC.md`
2. Read `memory/MEMORY.md`
3. Read this file completely
4. Read `.claude/agents/backend.md`
5. Apply the C2 process from `.claude/agents/general-agent-template.md`
6. Read `memory/codebase-map.md`, then `src/easy_verifier/core/report.py` render functions (`_render_document` and everything it calls)

---

## Requirement (Pillar 1 — Adapt the requirement)

User brief (2026-10-04, approved plan): make the HTML report usable so a human can answer in < 30 s:
overall health (one number + short status), how much evidence exists, the 3–5 highest-leverage fixes,
and what is still unknown. Keep the T069 summary first; improvement plan next, P0/P1/P2 groups with top
items highlighted; aggressive progressive disclosure (`<details>`) for cited files, metric tables, raw
evidence; clear visual hierarchy; narrow-viewport friendly (cards); "No gaps" and full-abstention cases
look intentional. Philosophy unchanged: no inference, all numbers cited, no network/external assets,
adapter parity, agent text redacted + escaped.

**Restated intent**:
> Reorder and fold the report so the first screen answers health, evidence, top fixes and unknowns,
> while every existing number, citation and warning stays in the document one click away.

**Out of scope**:
- Any change to ratings, weights, thresholds, plan/gain computation, warnings logic, or payload JSON.
- JavaScript, external CSS/fonts, a quality label ("good/poor") — status is factual only.
- Docs (T071).

**Requirement Refs**:
- FR-065 (order, cards, merged unknowns, folding, 400px, content preserved).
- FR-063/FR-064 (summary stays first; agent paragraph unchanged), FR-018 (self-contained), FR-022 (parity).

### Requirement Fidelity Gate

- [x] Restated intent confirmed (user "yes, go ahead" to the plan, 2026-10-04)
- [x] Domain terms align (summary, improvement plan item, evidence-lack warning, context warning, score card)
- [x] Every AC traces to the Requirement
- [x] All Requirement Refs exist in `PRD.md`

---

## Dependencies & Reachability

**Depends on**: None
**Entry point**: `_render_document`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to |
|---|----------------------|-----------|
| 1 | Section order: header → share notice (one visible line + `<details>` full text) → summary → improvement plan → "What we couldn't measure" → quality score → checklist coverage → raw dimension evidence | FR-065 |
| 2 | Summary gains one factual evidence-status line: rated count, lowest measured share among rated/insufficient dimensions when known, warning count. No quality adjective anywhere in engine text | FR-065 |
| 3 | Improvement plan renders cards (no `<table>`): P0 and P1 groups open, P2 group in a closed `<details>`; the first 3 items overall carry a highlight class; each card shows dimension · area, gain badge (overall / dimension), now → rule, one fix line (agent fix above engine fix when present), cited files and unmeasured reason inside `<details>` | FR-065 |
| 4 | Context warnings + evidence-lack warnings render in one section, one summary line per item, full text in `<details>` | FR-065 |
| 5 | Quality score: one compact row/card per dimension (value or "no number" + reason code, rules met x/y, sample note); all rule inputs, citations and cited files inside a closed `<details>` | FR-065 |
| 6 | Checklist coverage and raw dimension evidence each inside a closed `<details>` with a one-line summary (counts) | FR-065 |
| 7 | Content preservation: for bryony and coffee-shop-api, the set of visible text tokens (tags stripped, whitespace normalized) of the AFTER report ⊇ the BEFORE report's tokens, excluding the new status line/section titles; every number and citation href present before is present after (automated check script + unit test on a synthetic score) | FR-065 |
| 8 | No `<script>`, no external `href`/`src` except existing citation links; parity tests and DDR-0005 replay unchanged | FR-018, FR-022 |
| 9 | "No gaps" plan and all-abstained report render an intentional message block (styled), not empty sections | FR-065 |
| 10 | At a true 400px viewport (iframe) no section causes horizontal page scroll (fixes the pre-existing Context-warnings overflow) | FR-065 |

---

## Evaluation & Acceptance

### Success Criteria

| # | Given | Expect | How |
|---|-------|--------|-----|
| 1 | Synthetic score with P0, P1×4, P2×2, 3 warnings | order per AC1; P2 closed; 3 highlighted cards | automated (HTML structure) |
| 2 | Same with agent improvements + summary | agent fix above engine fix; redacted/escaped | automated |
| 3 | All rules met, no warnings | styled "No gaps" block | automated |
| 4 | All dimensions abstained | styled "no number for any dimension" block; unknowns listed | automated |
| 5 | BEFORE vs AFTER real reports | token/number/href preservation check passes | Supervisor script |
| 6 | 1280 / 400px screenshots | first screen shows summary + top fixes; no horizontal scroll at 400 | Supervisor Stage 5 |

### Verification Command

```bash
cd <worktree> && PYTHONPATH=src /home/hungnguyenhuu/workspace/pets/hungnguyen111/easy-verifier-mcp/.venv/bin/python -m pytest tests/test_t070_report_readability.py -q
cd <worktree> && PYTHONPATH=src /home/hungnguyenhuu/workspace/pets/hungnguyen111/easy-verifier-mcp/.venv/bin/python -m pytest -q
```

### Evidence

> Filled by the reviewer in `tasks/TASK_REVIEW_T070.md`.

---

## Demonstration

> See `tasks/TASK_REVIEW_T070.md`. BEFORE is captured by the Supervisor before spawn (real reports for
> bryony and coffee-shop-api saved in the scratchpad `t070/`).

---

## UI / Design Acceptance Criteria

### 1. Visual Regression

| Screen / Component | Verification method | Expected result |
|---|---|---|
| First screen at 1280 | headless Chromium + LLM vision | summary, evidence status and top fixes visible without scrolling past the plan header |
| Plan cards | screenshot | P0/P1 visually distinct; P2 collapsed |

### 2. Design-System Compliance

| Criterion | Verification method | Expected result |
|---|---|---|
| Colors | CSS audit | only existing palette values; P0/P1/abstention accents from existing tokens |
| Typography / spacing | computed style | consistent with existing sections |

### 3. Layout / Responsiveness

| Viewport | Verification method | Expected result |
|---|---|---|
| 400px (iframe) | screenshot + scrollWidth | no horizontal page scroll |
| 768 / 1280px | screenshot | cards wrap cleanly |

---

## Approach

**Pattern reference**: `src/easy_verifier/core/report.py` existing `<details>` use in `_render_plan_item` (cited files) and `_render_summary` (T069 structure); `_Ctx.esc` / `_Ctx.agent_text` for all text.

Restructure `_render_document` and the section renderers; prefer wrapping existing renderers' output in `<details>` over rewriting them, so content stays identical. Replace the plan table with card markup reusing the plan dict. Merge warnings by composing the two existing renderers' items. Keep commits small: (1) order + folding, (2) plan cards, (3) merged unknowns, (4) score rows, (5) CSS/400px.

Budget your tool calls: the `pre_agent_step_limit` hook stops a task at 90 calls. Do unit tests + one real render for your own check; the Supervisor does the real-repo before/after, preservation script and screenshots at Stage 5.

---

## Edge Case Checklist

- [ ] Report without score (partial dimensions) still renders, summary one-liner kept
- [ ] Findings present (agent findings) still render with their evidence and suggestions
- [ ] Gated / agent-rated solution-fit row shows its blend parts
- [ ] Sampled dimensions keep the sample note in the compact row
- [ ] Very long metric names / paths wrap inside cards at 400px
- [ ] `<details>` nesting stays valid HTML

---

## Files to Change (Predicted)

| File | Change |
|---|---|
| `src/easy_verifier/core/report.py` | order, folding, plan cards, merged unknowns, compact score rows, CSS |
| `tests/test_t070_report_readability.py` | new |
| existing report tests (`test_t013_report.py`, `test_t065`, `test_t066`, `test_t067`, `test_t069`) | update only structure assertions that pin the old table/order; never weaken content assertions |

## Files Must NOT Touch

| File | Reason |
|---|---|
| `core/judge.py`, `core/improve.py`, `core/score.py`, `core/gate.py` | numbers and payload unchanged |
| `core/redact.py` | reuse only |

---

## Test Plan

Unit tests on synthetic scores for each AC; existing report tests kept green; Supervisor Stage 5 on bryony + coffee-shop-api copies with preservation script and screenshots.

---

## Completion Checklist

- [ ] Implementation done
- [ ] `Skill({ skill: "code-review" })`
- [ ] `Skill({ skill: "security-review" })` (Medium)
- [ ] Lint passes
- [ ] Tests written AND pass — pasted in `tasks/TASK_REVIEW_T070.md`
- [ ] `Skill({ skill: "verify" })` (Supervisor, real-repo copies)
- [ ] Supervisor notified
