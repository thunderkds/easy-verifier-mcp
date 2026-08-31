# TASK_GUIDE — T022: `score` operation in both adapters and the report's score panel
**Date**: 2026-08-26
**Complexity Level**: C1
**Risk Level**: Low
**Priority**: P0
**Assigned agent**: Backend-Implementer
**Agent guide**: `.claude/agents/backend.md`

---

## Mandatory Startup (Do Not Skip)

1. Read `PROJECT_SPEC.md` — Critical Constraint 7 (adapters stay thin) and Glossary **Rating** / **Assessment** / **Divergence**
2. Read `memory/MEMORY.md`
3. Read this file completely
4. Read `.claude/agents/backend.md`
5. Read `docs/ddr/0003-...md` — an abstention must render **distinctly** from a low rating

---

## Requirement (Pillar 1 — Adapt the requirement)

This is the task that makes the user's request true end to end: *point it at a path, get numbers*.

**Restated intent**:
> A `score` operation is exposed in **both** adapters and rendered in the HTML report. Given only a
> repository path and a scope, it returns per-dimension ratings, the disclosed overall, and the
> metrics each rating cites — **with no findings submitted and no agent in the loop**. When findings
> are also supplied, assessments and divergences render beside the ratings.

**Out of scope**:
- Any metric, rule, weight or arithmetic — all of it lives in T019/T020/T021 (Constraint 7, FR-021).
- Changing the evidence-pack operations that already ship.

**Requirement Refs**:
- FR-030: a rating obtainable from a single invocation against a path, no agent required
- FR-029a: rating and assessment side by side with divergence
- FR-028a/b: abstention renders distinctly; the overall discloses who abstained
- FR-021: adapters contain no logic of their own; FR-022: both adapters agree
- FR-016a: a coverage figure is never rendered without its miss list — extended to ratings

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [ ] Restated intent confirmed to match the user's request (by Supervisor / user)
- [ ] Domain terms align with the glossary
- [ ] Every Acceptance Criterion below traces to a line in the Requirement
- [ ] All Requirement Refs exist in `PRD.md` and are fully covered by the Acceptance Criteria above

---

## Dependencies & Reachability

**Depends on**: T019, T020, T021 — metrics, rating, assessment; **T014** — the MCP adapter must
exist to expose a tool on it; **T015** — the CLI subcommand surface must be settled first, or this
task rebuilds it.

> **Sequencing is binding.** Do not start T022 before T014 and T015 have merged. Adding a `score`
> operation to an adapter that is mid-restructure means doing the adapter work twice.

**Entry point**: `score` (CLI subcommand and MCP tool of the same name)

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | `easy-verifier score --repo <path> [--scope ...]` returns ratings + overall + cited metrics with **no** findings input and no server | FR-030, FR-021b |
| 2 | The MCP adapter exposes the same `score` tool, and its output matches the CLI's for the same repo, scope and dimensions | FR-019, FR-022 |
| 3 | Optional `--findings <path>` (or stdin, matching T015's settled convention) adds assessments and divergences to the same output | FR-029a |
| 4 | An **abstaining** dimension renders visibly differently from a low-rated one — in JSON, in the terminal, and in the HTML report. A reader must not be able to confuse "could not see" with "is bad" | FR-028a, Constraint 1b |
| 5 | The overall renders **with** its disclosure (how many of seven contributed, who abstained, why) — never the number alone | FR-028b, FR-016a |
| 6 | The report gains a score panel: per-dimension rating, assessment where present, divergence where both exist, and the metrics each rating cites | FR-029a, FR-018a |
| 7 | The report stays **self-contained** — no external CSS/JS/font/image request added by the panel | FR-018 |
| 8 | Adapters contain no metric computation, no weighting, no rounding decisions and no rating arithmetic — asserted structurally, as T015's AC #5 does | FR-021 |
| 9 | Exit codes follow T015's settled convention; an all-abstained run is **not** an error exit — it is a successful run reporting that nothing could be rated | FR-028a |
| 10 | Container paths never leak into a rendered score panel (the `_Ctx.path` chokepoint already exists — use it, do not re-implement) | FR-021c |

---

## Evaluation & Acceptance

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | `score --repo .` on this repo, no findings | Per-dimension ratings + disclosed overall + cited metrics; exit 0 | automated test + real CLI run |
| 2 | Same, on a repo where `test-strategy` falls below its floor | That dimension renders as an abstention with the floor, achieved coverage and unreached sources; **no number** for it | automated test |
| 3 | Same inputs through the MCP adapter | Output matches the CLI's modulo T017 normalization | automated test |
| 4 | `score --repo . --findings f.json` | Assessments and divergences render beside ratings; neither is blended | automated test |
| 5 | A repo where every dimension abstains | Exit **0**, output states nothing could be rated and why per dimension | automated test |
| 6 | The rendered report opened with the network blackholed | Renders fully; zero external requests | manual + automated |

### Verification Command (exact, runnable)

```bash
cd <worktree> && PATH=.venv/bin:$PATH python -m pytest tests/test_score_operation.py -q
```

---

## Approach

**Pattern reference**: `src/easy_verifier/adapters/cli.py` — `_run_single` / `_run_combined` are the
exact shape to imitate: parse, call one core function, serialize, echo caveats to stderr so stdout
stays a clean JSON document. Add `_run_score` beside them and nothing else.

For the report panel, imitate `report.py:_render_coverage` / `_coverage_entry` — they already solve
"render a number that must never appear without its miss list", which is the same problem AC #4/#5
pose for ratings. Route every path through the existing `_Ctx.path`, and every caller-authored
string through `_Ctx.agent_text()` (redact → escape) — T013's security P1 was precisely a
caller-authored field bypassing redaction.

---

## Edge Case Checklist

- [ ] A dimension that raised — must render distinctly from *both* a low rating and a floor abstention (T013's Stage 4 P1 was exactly this conflation in this exact renderer)
- [ ] An abstention reason containing HTML — escaped through the existing chokepoint
- [ ] A score run against a repo with no `reports/` write access — fail cleanly, matching `ReportWriteError` handling
- [ ] `--findings` naming a dimension absent from the score run
- [ ] Terminal output must not require color to distinguish an abstention from a rating

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/adapters/cli.py` | `score` subcommand + `_run_score` |
| `src/easy_verifier/adapters/mcp_server.py` | `score` tool registration |
| `src/easy_verifier/core/report.py` | Score panel renderer |
| `tests/test_score_operation.py` | New |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| `src/easy_verifier/core/metrics.py`, `judge.py`, `assessment.py` | Their contracts are fixed; this task only surfaces them |

---

## Test Plan

Drive the **real CLI** for the abstention and all-abstained paths, not the functions in-process —
this project has twice had Stage 4 pass a defect that only appeared at the adapter boundary (T008's
widened scope, T012's exit-code divergence). Build a fixture repo designed to force an abstention
rather than one that happens to produce one.

---

## Completion Checklist

- [ ] Implementation done
- [ ] Self-review: `Skill({ skill: "code-review" })` run
- [ ] Security review: N/A (Low risk — no new primitive; state so explicitly)
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T022.md`'s Evidence table
- [ ] `Skill({ skill: "verify" })` run — **at the real CLI**
- [ ] `memory/MEMORY.md` updated
- [ ] Supervisor notified: task ready for Stage 4 review
