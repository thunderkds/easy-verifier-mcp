# TASK_GUIDE — T054: Bugfix: reference gate asks for colocated_test_name_patterns (T037 × T052 merge regression)
**Date**: 2026-09-28
**Complexity Level**: C1
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
7. Read `tasks/TASK_REVIEW_T037.md` (OPTIONAL_FIELDS ruling R1) and `tasks/TASK_REVIEW_T052.md` (colocated_test_name_patterns, omitted on purpose for python/php/rust)

---

## Requirement (Pillar 1 — Adapt the requirement)

Merge of T037 + T053 + T052 into feat/llm-integration (2026-09-28): both branches were green alone; combined, `tests/test_t037_reference_gate.py::test_no_framework_and_curated_language_means_no_gate[pyproject.toml]` and `[Cargo.toml]` fail, and this repo's MCP score asks `python.colocated_test_name_patterns`. T052 added the field to FIELD_METRICS; T037's gate treats every consumed field as required unless in OPTIONAL_FIELDS. The field is optional by design (Python/PHP/Rust omit it; prefix names keep the directory-first rule).

**Restated intent**:
> The reference gate never asks for `colocated_test_name_patterns`; curated-language repos without frameworks get no reference request again.

**Out of scope**:
- Changing classification behaviour
- Adding colocated patterns for python/php/rust

**Requirement Refs**:
- FR-045: missing fields only (token discipline)
- T037 ruling R1: optional fields never gate

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [ ] Restated intent confirmed to match the user's request (by Supervisor / user — not the implementing agent)
- [ ] Domain terms align with `PROJECT_SPEC.md` glossary (`grill-with-docs` run if terminology was fuzzy)
- [ ] Every Acceptance Criterion below traces to a line in the Requirement
- [ ] All Requirement Refs exist in `PRD.md` and are fully covered by the Acceptance Criteria above

> An agent must NOT start implementing until this gate is checked. If anything here is unclear,
> STOP and ask the Supervisor (Karpathy: Think Before Coding).

---

## Dependencies & Reachability

**Depends on**: T052 — colocated_test_name_patterns field; T037 — OPTIONAL_FIELDS

**Entry point**: `OPTIONAL_FIELDS`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | `colocated_test_name_patterns` is in `metric_tables.OPTIONAL_FIELDS` with a one-line reason | fix |
| 2 | `test_optional_fields_really_are_optional_in_metric_code` covers the new member (removing it from every language leaves the fed metrics computing as often as with the full registry) | reality test |
| 3 | The two failing T037 tests pass; full suite green on feat/llm-integration's merged state | regression |
| 4 | MCP-path `score_repository(<this repo>, scope='worktree', detect_gates=True).reference` is None | real surface |

---

## Evaluation & Acceptance (How we know the agent worked correctly)

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | this repo, MCP path | `reference` None | app run |
| 2 | pyproject.toml / Cargo.toml fixtures | no gate | automated test |

### Verification Command (exact, runnable)

```bash
python -m pytest -q
python -m ruff check src tests
```

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T054.md`.

---

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T054.md`.

---

## UI / Design Acceptance Criteria

> N/A — pure backend task (no UI component). All three UI Evidence rows are ☐ N/A.

---

## Approach

**Pattern reference**: `core/metric_tables.py` OPTIONAL_FIELDS (T037) and its reality test

Reproduce with the two failing tests first (bug-fix flavour), add the member, extend the reality test.

---

## Edge Case Checklist

- [ ] A future registry field consumed by metrics but optional must be added to OPTIONAL_FIELDS — consider a test asserting every FIELD_METRICS field is either curated for all 9 languages or listed optional

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/core/metric_tables.py` | OPTIONAL_FIELDS member |
| `tests/test_t037_reference_gate.py` | reality test coverage (and the optional guard test above if cheap) |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| classification code | out of scope |

---

## Test Plan

The two failing tests + reality test; full suite.

---

## Completion Checklist

- [ ] Implementation done
- [ ] Self-review: `Skill({ skill: "code-review" })` run
- [ ] Security review: `Skill({ skill: "security-review" })` run (Medium risk)
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T054.md`'s Evidence table (Hard-Stop Gate 5)
- [ ] `Skill({ skill: "verify" })` run — feature confirmed working at a real surface
- [ ] `memory/MEMORY.md` updated (if new patterns or feedback learned)
- [ ] Supervisor notified: task ready for Stage 4 review
