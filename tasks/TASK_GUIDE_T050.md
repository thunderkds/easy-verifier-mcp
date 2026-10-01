# TASK_GUIDE — T050: Code-quality and architecture packs gather code evidence (source excerpts, import lines)
**Date**: 2026-09-28
**Complexity Level**: C2
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
8. Read `tasks/TASK_REVIEW_T033.md` (why CCN/cycle metrics abstain on code-quality/architecture packs) and `memory/learnings.md` 2026-09-28 entries

---

## Requirement (Pillar 1 — Adapt the requirement)

Found at T033 Stage 4 (2026-09-28): code-quality packs contain only config/docs and this repo's architecture pack held 0 code excerpts of 7, so T033's `functions_over_ccn_10_share`, `max_function_ccn` and `top_level_import_cycles` abstain in practice, and T035's approved code-quality CCN rules (40+20 weight) and architecture cycle rule (40) would always abstain. Supervisor ruling: add code evidence to those two packs before T035.

**Restated intent**:
> On a real repository, the code-quality pack carries bounded whole-function source excerpts and the architecture pack carries import-line excerpts, so T033's CCN and cycle metrics compute at the real `score` surface instead of abstaining.

**Out of scope**:
- Changing metric definitions or thresholds (T033/T035)
- Other dimensions
- Coverage floors

**Requirement Refs**:
- FR-043: code-quality CCN and architecture cycle rules need their metrics to compute
- FR-027 / FR-027a: metrics from the pack; truncation reported
- NFR-009: bounded packs (byte budget)

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [ ] Restated intent confirmed to match the user's request (by Supervisor / user — not the implementing agent)
- [ ] Domain terms align with `PROJECT_SPEC.md` glossary (`grill-with-docs` run if terminology was fuzzy)
- [ ] Every Acceptance Criterion below traces to a line in the Requirement
- [ ] All Requirement Refs exist in `PRD.md` and are fully covered by the Acceptance Criteria above

> An agent must NOT start implementing until this gate is checked. If anything here is unclear,
> STOP and ask the Supervisor (Karpathy: Think Before Coding).

---

## Dependencies & Reachability

**Depends on**: T033 — token metrics and registry syntax fields

**Entry point**: `collect`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | code-quality `collect` adds source-code excerpts for files in scope (source classified via `curated_metric_tables()`), ordered after existing config/doc evidence by relevance tier, bounded by the byte budget; truncation reported as today | code evidence, bounded |
| 2 | architecture `collect` adds import-line excerpts (lines matching the registry `import_syntax`, with minimal context) for source files in scope, bounded; excerpts cite path:line | import evidence |
| 3 | Real CLI `score --scope project` on this repo and on a scratch multi-file Python repo: code-quality `max_function_ccn` and `functions_over_ccn_10_share` have values (or abstain only for truncation, stated), architecture `top_level_import_cycles` has a value | real surface |
| 4 | Existing config/doc excerpts and their order unchanged; existing tests pass; pack size stays within budget (measure bytes before/after on this repo and one external repo if available) | no regression, NFR-009 |
| 5 | Secret-bearing files never read; excerpts pass through redaction (unchanged pipeline) | DDR-0001/0002 |

---

## Evaluation & Acceptance (How we know the agent worked correctly)

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | scratch Python repo with a CCN-12 function | code-quality `max_function_ccn` = 12 at CLI | automated + app run |
| 2 | scratch repo alpha↔beta imports | architecture `top_level_import_cycles` = 1 at CLI | automated + app run |

### Verification Command (exact, runnable)

```bash
python -m pytest -q
python -m ruff check src tests
```

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T050.md`.

---

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T050.md`.

---

## UI / Design Acceptance Criteria

> N/A — pure backend task (no UI component). All three UI Evidence rows are ☐ N/A.

---

## Approach

**Pattern reference**: `dimensions/test_strategy.py` (T031) — reads sources through `context.read_source` after primary evidence, capped, with an all-or-none warning; `dimensions/_doc_extract.py` for doc-shaped collection

Smallest change: extend the two dimensions' collection with a trailing, lowest-relevance tier of code excerpts. Code-quality: whole-function excerpts (use `tokens.approximate_ccn` spans to cut) for the largest/most complex functions first, so the budget keeps the informative ones. Architecture: import lines only. Keep whole-set metric semantics honest: if the byte budget drops code excerpts, the pack reports truncation and whole-set metrics abstain (existing FR-027a machinery).

---

## Edge Case Checklist

- [ ] Huge repos: excerpt selection must be deterministic (stable order) for adapter parity (DDR-0005)
- [ ] Generated/minified files: excluded by existing ignore rules and the 500-char line cap
- [ ] Repo with docs but no code: behaviour unchanged
- [ ] Changes scope: only files in the diff

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/dimensions/code_quality.py` | code excerpt tier |
| `src/easy_verifier/dimensions/architecture.py` | import-line tier |
| `src/easy_verifier/dimensions/_doc_extract.py` | only if the shared helper needs a hook |
| `tests/` | fixture repos + CLI-level tests |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| src/easy_verifier/core/judge.py | T035 |
| metric definitions in core/metrics.py | T033 owns them |

---

## Test Plan

Fixture repos driven through `score_repository`; pack byte-size assertions; parity (CLI vs MCP) unchanged; sabotage: disabling the new tier makes the CLI-level tests fail.

---

## Completion Checklist

- [ ] Implementation done
- [ ] Self-review: `Skill({ skill: "code-review" })` run
- [ ] Security review: `Skill({ skill: "security-review" })` run (Medium risk)
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T050.md`'s Evidence table (Hard-Stop Gate 5)
- [ ] `Skill({ skill: "verify" })` run — feature confirmed working at a real surface
- [ ] `memory/MEMORY.md` updated (if new patterns or feedback learned)
- [ ] Supervisor notified: task ready for Stage 4 review
