# TASK_GUIDE — T076: Whole-file code metrics below the cap — no truncation abstention for structure metrics
**Date**: 2026-10-04
**Complexity Level**: C2
**Risk Level**: Medium
**Priority**: P0
**Assigned agent**: backend-developer
**Agent guide**: `.claude/agents/backend.md`

---

## Mandatory Startup (Do Not Skip)

1. Read `PROJECT_SPEC.md`, `memory/MEMORY.md`, this file, `.claude/agents/backend.md`
2. Apply the C2 process from `.claude/agents/general-agent-template.md`
3. Read `memory/codebase-map.md`, `tasks/TASK_REVIEW_T068.md` (Design: `compute_sampled_metrics`, `EvidencePack.sample`), `tasks/TASK_REVIEW_T074.md`

---

## Requirement (Pillar 1 — Adapt the requirement)

T068 follow-up #2 (logged 2026-10-04): repositories at or under the 200-file cap still compute code
structure metrics from byte-budgeted excerpts, so truncation makes them abstain. After DDR-0011 moved
architecture weight to code, kitchd's architecture went from a documents-only 100 to "no number".
The user asked for this wave to run automatically; this task is required for its goal.

**Restated intent**:
> Every repository — small or large — gets its code structure metrics computed over whole source files,
> so a truncated excerpt budget never hides them; large repositories keep batches, small ones are one
> full batch without a sample label.

**Out of scope**: test-strategy's test-file metrics (assertion density etc.); the byte budget value;
payload size (separate follow-up); requirement-fidelity (T075).

**Requirement Refs**: FR-072; FR-060 (shared mechanism); NFR-009.

### Requirement Fidelity Gate

- [x] Restated intent confirmed (Supervisor; user "plan and run them automatically", 2026-10-04)
- [x] Domain terms align (batch, sample, whole-set metric)
- [x] Every AC traces to the Requirement
- [x] All Requirement Refs exist in `PRD.md`

---

## Dependencies & Reachability

**Depends on**: None
**Entry point**: `compute_sampled_metrics`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to |
|---|---|---|
| 1 | At or under the cap, code-quality (CCN share, max CCN, type escapes, TODO share) and architecture (import cycles, layer direction) are computed from whole source files via the same path as above the cap | FR-072 |
| 2 | Their derivations say "all N source files" — no "sample" label, no `samples` entry, no `continue_batches` | FR-072 |
| 3 | Byte-budget truncation of excerpts is still reported (FR-027a) but no longer makes these metrics abstain | FR-072 |
| 4 | Excerpts and the byte budget unchanged; payload growth bounded (results only, like `SampleFacts`) | NFR-009 |
| 5 | Above-cap behaviour (T068) unchanged | FR-060 |
| 6 | Secret-bearing files still refused; redaction of stored facts unchanged | DDR-0002 |
| 7 | Snapshots that change are regenerated with the diff reviewed; parity holds | FR-022 |

## Evaluation & Acceptance

### Success Criteria

| # | Given | Expect | How |
|---|---|---|---|
| 1 | Fixture ≤ cap with a tiny budget that truncates | cycles / CCN metrics computed, not abstained | automated |
| 2 | Same fixture, metric values | equal to computing directly over all its files (oracle) | automated |
| 3 | kitchd | architecture rated (Supervisor) | verify |

### Verification Command

```bash
cd <worktree> && PYTHONPATH=src /home/hungnguyenhuu/workspace/pets/hungnguyen111/easy-verifier-mcp/.venv/bin/python -m pytest tests/test_t076_whole_file_metrics.py -q
```

### Evidence

> Filled by the reviewer in `tasks/TASK_REVIEW_T076.md`.

## Demonstration

> BEFORE (Supervisor): kitchd architecture `insufficient_measured_weight` — import cycles and layer direction abstain "whole-set-dependent: the byte budget truncated this pack" (scratchpad `t073/t074-kitchd.json`).

## UI / Design Acceptance Criteria

Pure backend — ☐ N/A.

## Approach

**Pattern reference**: `metrics.compute_sampled_metrics`, `EvidencePack.sample` / `SampleFacts`, `dimensions/_code_extract.py` batches (T068).

Treat ≤ cap as one full batch internally; only the disclosure differs. Budget ~50 tool calls; Supervisor does real-repo checks.

## Edge Case Checklist

- [ ] Zero source files → metrics abstain as today (no division by zero)
- [ ] Unknown language files excluded as today
- [ ] Repos ≤ cap without truncation: values identical to before

## Files to Change (Predicted)

| File | Change |
|---|---|
| `dimensions/_code_extract.py`, `dimensions/code_quality.py`, `dimensions/architecture.py`, `core/metrics.py`, `core/models.py` | full-batch path below the cap |
| `tests/test_t076_whole_file_metrics.py` | new |

## Files Must NOT Touch

| File | Reason |
|---|---|
| `core/judge.py` | no rule change |
| test-strategy test-file metrics | out of scope |

## Completion Checklist

- [ ] Implementation done; tests pass; ruff clean
- [ ] Supervisor notified
