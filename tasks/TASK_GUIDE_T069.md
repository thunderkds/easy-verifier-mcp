# TASK_GUIDE — T069: Report summary first — engine summary + optional agent paragraph, detail right after
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
6. Read `memory/codebase-map.md`, `src/easy_verifier/core/improve.py`, `tasks/TASK_GUIDE_T066.md` (agent-text pattern) and `tasks/TASK_GUIDE_T067.md` (warnings)

---

## Requirement (Pillar 1 — Adapt the requirement)

User (2026-10-04), after reading the nest-api report: "I saw a lot of information need to care,
so I think should update the report like the rated session, general first, I mean like example. Hey,
I checked from your code, and got 2 of session can evaluated, which weak point I think you should
focus on improve these one following the rules that refer here." Choice: **B** — engine summary plus
an optional LLM paragraph labelled agent. "and in the below, we continue talk about the detail session
right after" — detail follows directly, not folded.

**Restated intent**:
> The report opens with a short plain summary — overall, how many areas were rated, the top weak
> points with the rule and standard behind each and what each is worth, and what to add for the areas
> that could not be rated — optionally followed by the calling LLM's own paragraph (labelled agent);
> the existing detail sections come right after, unchanged.

**Out of scope**:
- Changing any number, plan computation, warning logic, or the detail sections' content.
- Folding/hiding detail sections.
- The scanner false positives seen on nest-api (separate bugfix).

**Requirement Refs**:
- FR-063: engine summary content, order, max 3 focus items, citations, warnings line, detail follows unfolded.
- FR-064: optional agent `summary` via `write_report`, validated, redacted + escaped, labelled agent.
- FR-026: templated presentation only.

### Requirement Fidelity Gate

- [x] Restated intent confirmed (Supervisor; user chose B, 2026-10-04)
- [x] Domain terms align (rated dimension, improvement plan item, evidence-lack warning)
- [x] Every AC traces to the Requirement
- [x] All Requirement Refs exist in `PRD.md`

---

## Dependencies & Reachability

**Depends on**: None
**Entry point**: `_render_summary`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to |
|---|----------------------|-----------|
| 1 | The summary is the first content section of the report (after header/advisory), before warnings and the score panel | FR-063 |
| 2 | It states overall value (or its abstention), "N of M areas rated" with each rated dimension and value | FR-063 |
| 3 | "Focus on these first": up to 3 plan items, P0 then P1 in plan order; each shows dimension, plain metric description, current vs threshold, overall gain, and the rule's cited standard (metric/threshold citation title, linked when it has a URL) | FR-063 |
| 4 | "Could not evaluate": one line per evidence-lack warning with dimension and what is missing (missing roles or unmeasured rules, short) | FR-063 |
| 5 | No gaps and nothing abstained → summary says so plainly; overall abstained → summary says no area could be rated | FR-063 |
| 6 | Detail sections that existed before render after the summary, byte-identical in content to before (only position relative to the summary changes) | FR-063 |
| 7 | `agent_input.summary` (string, stripped, non-empty, ≤ 2000 chars) renders as a paragraph labelled agent inside the summary, redacted then escaped; invalid → ValidationError before any disk write; accepted by `roles.validate_agent_input` | FR-064 |
| 8 | Engine summary text is a pure function of the score (CLI/MCP and replay byte-equal under DDR-0005) | FR-022 |
| 9 | Real repos: reports for nest-api (copy) and node-monorepo (copy) show the summary; screenshot 1280 + true 400px (iframe) | user report |

---

## Evaluation & Acceptance

### Success Criteria

| # | Given | Expect | How |
|---|-------|--------|-----|
| 1 | Score with 2 rated, 3 P1 items, 4 warnings | summary: "2 of 7", 3 focus items with gains + citations, 4 could-not-evaluate lines | automated |
| 2 | 5 P1 items | only the top 3 shown | automated |
| 3 | No items, no warnings | plain "no gaps" sentence | automated |
| 4 | Agent summary with `FAKEfake…` secret + `<script>` | redacted + escaped, labelled agent | automated |
| 5 | Agent summary empty / 2001 chars / non-string | ValidationError, `reports/` untouched | automated |
| 6 | Report HTML before vs after with summary section removed | detail sections identical | automated |
| 7 | nest-api copy | summary reads like the user's example; screenshot | verify |

### Verification Command

```bash
cd <worktree> && PYTHONPATH=src <repo>/.venv/bin/python -m pytest tests/test_t069_report_summary.py -q
cd <worktree> && PYTHONPATH=src <repo>/.venv/bin/python -m pytest -q
```

### Evidence

> Filled by the reviewer in `tasks/TASK_REVIEW_T069.md`.

---

## Demonstration

> See `tasks/TASK_REVIEW_T069.md`.

---

## UI / Design Acceptance Criteria

### 1. Visual Regression

| Screen / Component | Verification method | Expected result |
|---|---|---|
| Report top | headless Chromium screenshot + LLM vision | summary is the first section; readable in under 10 lines; detail follows |

### 2. Design-System Compliance

| Criterion | Verification method | Expected result |
|---|---|---|
| Colors / typography | CSS audit | existing palette and section/card styles; agent label reuses `.fix-source-agent` |

### 3. Layout / Responsiveness

| Viewport | Verification method | Expected result |
|---|---|---|
| 400px (iframe) / 1280px | screenshot | summary has no horizontal overflow |

---

## Approach

**Pattern reference**: `src/easy_verifier/core/report.py` `_render_improvement_plan` / `_render_plan_item` (plan rendering, agent label) and `core/improve.py` `validate_improvements` (agent-input validation, fail closed, redacted echo).

Add `_render_summary(ctx, score, plan, warnings, agent_summary)` placed first in `_render_document`. Build sentences from the score dict only. Citations come from the rule input's `metric_citation`/`threshold_citation` (and `RATING_RULES` for P2). Validate `summary` next to `improvements` in `write_report`.

---

## Edge Case Checklist

- [ ] Partial-dimension report (no score) → no summary section, or a one-line "no score in this report"
- [ ] Citation that is `PROJECT_DEFAULT` → say "project default", no link
- [ ] Gated/agent-rated solution-fit counts as rated, labelled agent-rated
- [ ] Sampled dimension (T068) → "(sample: N of M files)" after its value
- [ ] Agent summary whitespace-only → error

---

## Files to Change (Predicted)

| File | Change |
|---|---|
| `src/easy_verifier/core/report.py` | summary section + agent paragraph + CSS |
| `src/easy_verifier/core/roles.py` | accept `summary` agent-input key |
| `src/easy_verifier/adapters/mcp_server.py` | write_report description mentions `summary` |
| `tests/test_t069_report_summary.py` | new |

## Files Must NOT Touch

| File | Reason |
|---|---|
| `core/judge.py`, `core/improve.py` computation, `core/gate.py` | numbers unchanged |
| `core/redact.py` | reuse only |

---

## Test Plan

Unit tests per AC on synthetic scores; HTML structure assertions; Stage 5 on scratch copies of nest-api and node-monorepo with screenshots.

---

## Completion Checklist

- [ ] Implementation done
- [ ] `Skill({ skill: "code-review" })`
- [ ] `Skill({ skill: "security-review" })` (Medium — new agent-text egress)
- [ ] Lint passes
- [ ] Tests written AND pass — pasted in `tasks/TASK_REVIEW_T069.md`
- [ ] `Skill({ skill: "verify" })` on real repo copies
- [ ] Supervisor notified
