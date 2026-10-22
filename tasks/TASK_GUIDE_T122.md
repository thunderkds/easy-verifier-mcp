# TASK_GUIDE — T122: MCP `score` reply is a summary by default; full metric detail on request
**Date**: 2026-10-21
**Complexity Level**: C1
**Risk Level**: Medium
**Priority**: P1
**Assigned agent**: backend-developer
**Agent guide**: `.claude/agents/backend.md`

---

## Mandatory Startup (Do Not Skip)

Before writing any code:
1. Read `PROJECT_SPEC.md`
2. Read the memory slice in your spawn prompt (`<!-- memory-slice -->`). Read `memory/MEMORY.md` in full only if your work reaches a file, hook, skill or decision the slice does not cover
3. Read this file completely
4. Read `.claude/agents/backend.md`
5. Note the **Complexity Level** above and apply the matching process from the Complexity matrix in your role guide

---

## Requirement (Pillar 1 — Adapt the requirement)

Field report (2026-10-21, consumer easy-personal-mcp, `score` of HUN-34 with `budget_bytes=120000`): the reply
was **780,505** characters. The caller expected at most 120,000. Claude Code could not read it inline and
spilled it to a file. Supervisor reproduction on develop `2004992`: the reply is **806,343** characters, and
the `metrics` key is **714,739** of them (953 metric rows: `derivation` 236k, `outcome` 215k,
`computed_from` 103k). Everything else is about 92k.

`budget_bytes` is documented as "byte ceiling for excerpt text" (`adapters/cli.py:151`). It never limited
the reply, and the caller misread it. The real problem is that every review pays for about 700k characters of
raw metric detail the agent seldom reads. The owner chose (2026-10-21) **summary by default**.

**Restated intent** (Supervisor's interpretation, in this project's domain language):
> The MCP `score` tool takes `detail: "summary" | "full"`, default `"summary"`. A summary reply omits the
> per-metric rows (`metrics.metrics`). Everything else is unchanged: ratings, overall, improvement plan,
> warnings, needs_input, change_risk, provenance. `"full"` returns today's payload byte-for-byte. The
> tool description says `budget_bytes` limits evidence excerpts, not the reply, and how to get full detail.

**Out of scope** (what this task explicitly does NOT do):
- CLI output (unchanged; the CLI writes JSON to stdout and has no context window)
- `combined` / per-dimension tools
- A hard reply-size cap or truncation
- Shrinking `ratings` / `improvement_plan` content

**Requirement Refs**:
- FR-089: "MCP `score` returns a summary by default without per-metric rows; `detail=\"full\"` returns the complete payload."

### Requirement Fidelity Gate (sign off BEFORE implementation) — signed 2026-10-21, owner said "start and merge to develop for all tasks"

- [x] Restated intent confirmed to match the user's request (owner chose summary-by-default 2026-10-21)
- [x] Domain terms align with `PROJECT_SPEC.md` glossary
- [x] Every Acceptance Criterion below traces to a line in the Requirement
- [x] New FR added to `PRD.md` and covered by the Acceptance Criteria

> An agent must NOT start implementing until this gate is checked.

---

## Dependencies & Reachability

**Depends on**: None (sequence with T121 if both edit the score payload path; no shared lines expected)

**Entry point**: `score` in `src/easy_verifier/adapters/mcp_server.py` (payload from `ScoreResult.to_dict`, `core/score.py:197`)

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | MCP `score` with no `detail` → no per-metric rows in the reply; every other top-level key present and equal to the `"full"` reply | summary default |
| 2 | `detail="full"` → reply equal to today's payload | full on request |
| 3 | Invalid `detail` value → clear validation error naming the allowed values | input contract |
| 4 | `needs_input.gate_evaluations` stays usable in summary mode: every `evidence_refs` it lists resolves without the metric rows (assert or document) | agent loop unbroken |
| 5 | Tool description states `budget_bytes` limits evidence excerpts, not the reply, and names `detail="full"` | misread parameter |
| 6 | CLI `score` output byte-identical to before | CLI out of scope |

---

## Evaluation & Acceptance (How we know the agent worked correctly)

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | Fixture repo, MCP `score()` | no metric rows; ratings/overall equal to full | automated test |
| 2 | Real run: `easy-personal-mcp` HUN-34 changes scope via MCP | reply length before (806,343) vs after (expected ≈ 92k) | `verify` skill, pasted in TASK_REVIEW |

### Verification Command (exact, runnable)

```bash
uv run pytest tests -k "score and (detail or summary)" -q
```

### Evidence (filled by reviewer at Stage 4/5)

> Filled in `tasks/TASK_REVIEW_T122.md`. No UI: the three UI Evidence rows are ☐ N/A.

---

## Demonstration

> See `tasks/TASK_REVIEW_T122.md`. BEFORE: 806,343 chars, `metrics` 714,739 (develop `2004992`).

---

## Approach

**Pattern reference**: how `score` in `mcp_server.py` already adds MCP-only keys (`needs_input`) on top of `result.to_dict()`. Do the summary as an MCP-adapter step, not in the shared core.

**Vital slice**: `detail` parameter + drop `metrics.metrics` in summary mode + description text.
**Cut list**: no size cap, no partial metric lists.

---

## Edge Case Checklist

- [ ] `metrics.dimensions_without_pack` (small) kept or moved, and the decision is written in the docstring
- [ ] `write_report` unaffected (it re-gathers; it does not read the score reply)
- [ ] Docs that show a `score` reply example (README, `docs/DOCKER_MCP_GUIDE.md`, `docs/EVALUATION_GUIDE.md`) updated where they show `metrics`
- [ ] Doc test pinning backticked identifiers still passes

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/adapters/mcp_server.py` | `detail` param, summary filter, description |
| `tests/...` | Tests above |
| `PRD.md` | New FR (after gate) |
| `README.md` / docs | One line on `detail` and `budget_bytes` meaning |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| `src/easy_verifier/core/metrics.py`, `dimensions/**` | Scoring unchanged |
| `src/easy_verifier/adapters/cli.py` | CLI out of scope |

---

## Test Plan

In-process calls to `mcp_server.score` on a fixture repo in both modes; key-set and value equality; error
on a bad `detail`; CLI golden unchanged.

---

## Completion Checklist

- [ ] Implementation done
- [ ] Self-review: `Skill({ skill: "code-review" })` run
- [ ] Security review: `Skill({ skill: "security-review" })` run (Medium risk)
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T122.md`
- [ ] `Skill({ skill: "verify" })` run
- [ ] Supervisor notified: task ready for Stage 4 review
