# TASK_GUIDE — T066: Improvement plan (agent) — repo-specific fix text through `write_report`
**Date**: 2026-10-03
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
6. Read `memory/codebase-map.md`, `docs/ddr/0009-improvement-plan-ordered-by-recomputed-gain.md`, `tasks/TASK_GUIDE_T065.md`, and `memory/learnings.md` "A new egress path invalidates upstream redaction"

---

## Requirement (Pillar 1 — Adapt the requirement)

User (2026-10-02), fix text answer: **"both"** — the engine gives a standard fix line, and the calling
agent may replace it with a repo-specific one; the report shows which.

**Restated intent**:
> The calling agent can attach a repo-specific suggestion to any item of T065's improvement plan
> through `write_report`; the report shows it labelled `agent` (the engine line stays visible as
> fallback), and nothing the agent writes can name a non-existent item or leak a secret.

**Out of scope**:
- Changing how the plan is computed, grouped or ordered (T065).
- Agents changing any number (FR-038 still: numbers move only at hard gates).
- Auto-fixing the target repo (FR-024).

**Requirement Refs**:
- FR-057: agent suggestion per named plan item; unknown item = validation error; `engine`/`agent` label; redact + escape.
- FR-023/FR-024: suggestions advisory only.
- US-017, US-010.

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [x] Restated intent confirmed to match the user's request (Supervisor, brainstorm Q1 answer)
- [x] Domain terms align with `PROJECT_SPEC.md` glossary
- [x] Every Acceptance Criterion below traces to a line in the Requirement
- [x] All Requirement Refs exist in `PRD.md` and are fully covered by the Acceptance Criteria above

---

## Dependencies & Reachability

**Depends on**: T065 — `improvement_plan` in `ScoreResult` and the report section
**Entry point**: `write_report`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | `write_report` accepts an optional `improvements` list of `{dimension, metric_name, suggestion}` (via the same document/agent-input path the score already uses) | FR-057 |
| 2 | A named item present in the plan renders the agent text labelled `agent`, with the engine line still shown | FR-057 |
| 3 | A named item not in the plan → `ValidationError` before anything is written to disk | FR-057 |
| 4 | Non-string / empty / over-length suggestion, or duplicate `(dimension, metric_name)` → `ValidationError` | FR-057 |
| 5 | A secret-shaped token in a suggestion is redacted in the HTML (`_Ctx.agent_text()`), and HTML is escaped | FR-057, DDR-0001 |
| 6 | Items without an agent suggestion render the engine line labelled `engine` (T065 behaviour unchanged) | FR-057 |
| 7 | MCP tool schema / CLI `--agent-input` both accept `improvements`; parity holds | FR-022 |
| 8 | Real-repo: agent run on bryony writes a report with at least one `agent`-labelled fix | done-means-real-repo-verified |

---

## Evaluation & Acceptance

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | Valid override for a P1 item | report row shows agent text + `agent` label + engine line | automated test (rendered HTML) |
| 2 | Override for `security/no_such_metric` | `ValidationError`, `reports/` unchanged | automated test |
| 3 | Suggestion containing `FAKEfake…` secret-shaped value and `<script>` | redacted + escaped in HTML | automated test |
| 4 | Duplicate override for same item | `ValidationError` | automated test |
| 5 | bryony, MCP `write_report` with overrides | report shows agent-labelled fixes | `verify` skill, screenshot |

### Verification Command (exact, runnable)

```bash
.venv/bin/pytest tests/test_t066_improvement_overrides.py -q
.venv/bin/pytest -q && .venv/bin/ruff check src tests
```

### Evidence

> Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T066.md`.

---

## Demonstration

> See `tasks/TASK_REVIEW_T066.md`.

---

## UI / Design Acceptance Criteria

### 1. Visual Regression

| Screen / Component | Verification method | Expected result |
|-------------------|---------------------|-----------------|
| Improvement plan row with agent fix | Headless Chromium screenshot + LLM vision | agent text and `agent` label distinct from `engine` line |

### 2. Design-System Compliance

| Criterion | Verification method | Expected result |
|-----------|---------------------|-----------------|
| Colors match design tokens | CSS audit | reuse existing `.suggestion` styling |
| Typography matches spec | computed style | matches finding suggestions |
| Spacing / layout matches spec | visual | consistent with T065 section |

### 3. Layout / Responsiveness

| Viewport | Verification method | Expected result |
|----------|---------------------|-----------------|
| Mobile (320–480px) | headless Chromium `--window-size=400,900` | long agent text wraps, no page horizontal scroll |
| Tablet (768px) | headless Chromium | readable |
| Desktop (1024px+) | headless Chromium | readable |

---

## Approach

**Pattern reference**: `src/easy_verifier/core/findings.py:259` — optional `suggestion` validation shape; `src/easy_verifier/core/report.py:909` — `ctx.agent_text()` rendering of agent prose.

Validate `improvements` against the plan computed from the same score input (single source of truth),
fail closed before any disk write, render beside T065's engine line.

---

## Edge Case Checklist

- [ ] Unknown item → error, not silent drop
- [ ] Duplicate item → error
- [ ] Secret-shaped text → redacted; HTML → escaped
- [ ] Override for an abstained-dimension line (not an item) → error
- [ ] Replay with stored agent input reproduces the same report (byte-equal after DDR-0005)

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/core/report.py` | accept + validate + render overrides |
| `src/easy_verifier/core/improve.py` | lookup helper for plan item identity |
| adapters (`mcp_server.py`, `cli.py`) | only if the input schema is declared there |
| `tests/test_t066_improvement_overrides.py` | new |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| `src/easy_verifier/core/judge.py` | numbers never change here |
| plan computation in `improve.py` | T065 owns it |
| `src/easy_verifier/core/redact.py` | reuse, do not modify |

---

## Test Plan

Unit tests for each AC on a synthetic plan; rendered-HTML assertions; security-review on the new
agent-text egress; Stage 5 real-repo run on bryony through MCP.

---

## Completion Checklist

- [ ] Implementation done
- [ ] Self-review: `Skill({ skill: "code-review" })` run
- [ ] Security review: `Skill({ skill: "security-review" })` run (Medium risk, new agent-text egress)
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T066.md` (Hard-Stop Gate 5)
- [ ] `Skill({ skill: "verify" })` run on bryony — real repo
- [ ] `memory/MEMORY.md` updated (if new patterns learned)
- [ ] Supervisor notified: task ready for Stage 4 review
