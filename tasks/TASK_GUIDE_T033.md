# TASK_GUIDE — T033: Registry-driven token metrics: approximate CCN per function, imports, fan-in, cycles
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

---

## Requirement (Pillar 1 — Adapt the requirement)

Decided B1 (2026-09-28): measure structure by registry-driven tokens — branch keywords, comment/string delimiters, function-start and import syntax per language; lizard-style approximate CCN; import-based fan-in and cycles; no new dependency.

**Restated intent**:
> The engine computes approximate cyclomatic complexity per observed function, import edges, fan-in of files, and top-level module cycles for all 9 curated languages, using only registry data.

**Out of scope**:
- Rules/thresholds (T035)
- Exact parsing (tree-sitter/lizard rejected)

**Requirement Refs**:
- FR-043 (metric half): code-quality CCN, architecture cycles, blast-radius fan-in
- FR-027 / FR-027a: metrics from the pack; per-function CCN is evidence-local, repo-wide shares are whole-set

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [ ] Restated intent confirmed to match the user's request (by Supervisor / user — not the implementing agent)
- [ ] Domain terms align with `PROJECT_SPEC.md` glossary (`grill-with-docs` run if terminology was fuzzy)
- [ ] Every Acceptance Criterion below traces to a line in the Requirement
- [ ] All Requirement Refs exist in `PRD.md` and are fully covered by the Acceptance Criteria above

> An agent must NOT start implementing until this gate is checked. If anything here is unclear,
> STOP and ask the Supervisor (Karpathy: Think Before Coding).

---

## Dependencies & Reachability

**Depends on**: T031 — metrics read registry

**Entry point**: `approximate_ccn`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | Registry fields `branch_keywords`, `comment_delimiters`, `string_delimiters`, `function_start`, `import_syntax` exist for all 9 languages, each cited | registry-driven |
| 2 | `approximate_ccn` = 1 + decision points per function after stripping comments/strings; matches hand-counted values on a per-language fixture (±0) | lizard-style CCN |
| 3 | New metrics `functions_over_ccn_10_share` (whole-set), `max_function_ccn` (evidence-local), `top_level_import_cycles` (whole-set), `max_fan_in_changed` (whole-set) with `computed_from` citations | metrics for rules |
| 4 | Keywords inside strings/comments are not counted (fixture per language) | known failure mode |
| 5 | Truncated pack → whole-set metrics abstain; `max_function_ccn` still computes | FR-027a |

---

## Evaluation & Acceptance (How we know the agent worked correctly)

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | Python function with `if/elif/for/and` | CCN = 5 | automated test |
| 2 | JS file with `if` inside a string literal | not counted | automated test |

### Verification Command (exact, runnable)

```bash
python -m pytest -q
python -m ruff check src tests
```

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T033.md`.

---

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T033.md`.

---

## UI / Design Acceptance Criteria

> N/A — pure backend task (no UI component). All three UI Evidence rows are ☐ N/A.

---

## Approach

**Pattern reference**: `dimensions/blast_radius.py` `_reference_pattern` — one compiled alternation, single lazy pass

One small tokenizer: strip comments/strings using registry delimiters, then count keyword/operator hits per function span (function starts from registry; end = next start at same or lower indent, or brace balance for brace languages). Label the metric citation 'approximate CCN (lizard-style), McCabe 1976'.

---

## Edge Case Checklist

- [ ] Ruby blocks / Kotlin lambdas / JS arrow functions — define what counts as a function per language and test it
- [ ] Nested functions
- [ ] Very long files: bounded by the pack budget
- [ ] Generated/minified code: skip lines above a length cap

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/core/metrics.py` | new metric definitions |
| `src/easy_verifier/core/tokens.py` | new: tokenizer (pure) |
| `src/easy_verifier/registry/curated/*.toml` | structure fields |
| `tests/` | per-language hand-counted fixtures |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| src/easy_verifier/core/judge.py | T035 |
| evidence gathering in dimensions/ | metrics consume packs only |

---

## Test Plan

Hand-counted CCN fixtures for all 9 languages; import graph fixture with a known cycle; truncation abstention test.

---

## Completion Checklist

- [ ] Implementation done
- [ ] Self-review: `Skill({ skill: "code-review" })` run
- [ ] Security review: `Skill({ skill: "security-review" })` run (Medium risk)
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T033.md`'s Evidence table (Hard-Stop Gate 5)
- [ ] `Skill({ skill: "verify" })` run — feature confirmed working at a real surface
- [ ] `memory/MEMORY.md` updated (if new patterns or feedback learned)
- [ ] Supervisor notified: task ready for Stage 4 review
