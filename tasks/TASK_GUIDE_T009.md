# TASK_GUIDE — T009: test-strategy dimension (bespoke)
**Date**: 2026-08-15
**Complexity Level**: C2
**Risk Level**: Low
**Priority**: P1
**Assigned agent**: Backend-Implementer
**Agent guide**: `.claude/agents/backend.md`

---

## Mandatory Startup (Do Not Skip)

1. Read `PROJECT_SPEC.md`
2. Read `memory/MEMORY.md`
3. Read this file completely
4. Read `.claude/agents/backend.md`
5. **C2** — apply the C2 process from the Complexity matrix in `.claude/agents/general-agent-template.md`
6. **C2** — read `memory/codebase-map.md`

---

## Requirement (Pillar 1 — Adapt the requirement)

Gather evidence about how a repository tests itself, so the calling agent can judge whether the
change under evaluation is actually covered.

**Restated intent**:
> The `test-strategy` dimension returns citable evidence about the target's test surface — where
> tests live, what framework and configuration they use, which tests correspond to the files in the
> active scope, and, in kit-aware mode, the acceptance criteria the tests are supposed to satisfy.
> It reports what it could not find rather than estimating coverage.

**Out of scope**:
- Running the target's test suite (NFR-007 forbids executing target-repo code) or reading a
  coverage tool's output as authority.
- Judging whether coverage is adequate (FR-013).
- Writing tests.

**Requirement Refs**:
- FR-010: `test-strategy`, 1 of 7
- FR-011: structured pack — files read, citable excerpts, miss list
- FR-013: evidence only, no verdict
- FR-007: kit-aware `task` scope contributes the task's acceptance criteria
- FR-016: declared `sources_sought`
- NFR-007: never execute code from the target repo

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [x] Restated intent confirmed to match the user's request (by Supervisor / user)
- [x] Domain terms align with `PROJECT_SPEC.md` glossary — `PROJECT_SPEC.md` Constraint 8 names
      `test-strategy` explicitly as one of the three bespoke dimensions that must **not** be forced
      through `_doc_extract`, which AC #1 restates
- [x] Every Acceptance Criterion below traces to a line in the Requirement
- [x] All Requirement Refs exist in `PRD.md` and are fully covered by the Acceptance Criteria above —
      verified 2026-08-20 by the Supervisor: FR-003, FR-004, FR-005, FR-007, FR-009, FR-010, FR-011,
      FR-013, FR-016, FR-016a, NFR-002, NFR-007 all present in `PRD.md`. Note FR-016a (cited by
      AC #3) is a distinct row from FR-016 — both exist

---

## Dependencies & Reachability

**Depends on**: T005 — `budget()` for lazy bounded output. (T003's `Scope` is used for source↔test correspondence; it lands in Wave 1 ahead of this.)

**Entry point**: `collect` (in `dimensions/test_strategy.py`)

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | Ships as a descriptor + `collect`, **bespoke** — does not import `_doc_extract` | FR-009, Constraint 8 |
| 2 | Discovers test locations and framework/config evidence (`pytest.ini`/`pyproject` sections, `jest.config`, `tox.ini`, CI workflow test steps) and cites them | FR-011 |
| 3 | For files in the active scope, surfaces the corresponding test files where a correspondence can be established, and **names the scope files with no discoverable test** in the miss list | FR-011, FR-016a |
| 4 | In kit-aware `task` scope, includes the task's acceptance criteria as evidence | FR-007 |
| 5 | Never executes the target's tests, test runner, or `conftest.py` — asserted structurally (no `subprocess`, no `import` of target code) | NFR-007 |
| 6 | Emits no coverage percentage, adequacy judgment, grade or verdict | FR-013 |
| 7 | A repo with no tests at all yields a valid pack, coverage 0.0 on the test sources, and an explicit miss list — never an inferred or estimated figure | FR-005, NFR-002 |
| 8 | `collect` returns a lazily-consumed `Iterable[Excerpt]` | Critical Constraint 3 |
| 9 | Works in standalone mode with the limited-context warning | FR-003, FR-004 |

---

## Evaluation & Acceptance

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | This repo (has `tests/`, pytest config) | Test dir and pytest config cited with real line numbers | automated test |
| 2 | Temp repo with `src/foo.py` and `tests/test_foo.py` | Correspondence established and cited | automated test |
| 3 | Temp repo with `src/foo.py` and no tests | `src/foo.py` named in the miss list; no estimated coverage anywhere in the pack | automated test |
| 4 | This repo, `task` scope `T009` | This guide's acceptance criteria present as evidence | automated test |

### Verification Command (exact, runnable)

```bash
pytest tests/test_t009_test_strategy.py -q && \
  python -m easy_verifier.adapters.cli test-strategy --repo . | head -30
```

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T009.md`.

---

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T009.md`.

---

## Approach

**Pattern reference**: `src/easy_verifier/dimensions/security.py` (T008) — the sibling bespoke dimension; match its structure.

Source↔test correspondence should be **conventional and honest**: `src/foo.py` ↔ `tests/test_foo.py`
and the handful of equivalent conventions per ecosystem. Where the convention does not match, say
"no test discovered for this file" rather than reaching for a cleverer heuristic. A wrong
correspondence is worse than an admitted gap — it tells the reviewing agent a file is covered when
it is not, which is exactly the class of confident-but-unfounded claim this whole project exists to
prevent.

Resist the pull toward computing a coverage number. The dimension's honest output is "here are the
tests, here is what they configure, here is what has none".

---

## Edge Case Checklist

- [ ] Tests co-located with source (`foo.py` + `foo_test.py`, or Go-style `_test.go`) rather than in a `tests/` tree
- [ ] Several test files for one source file, or one test file covering many sources
- [ ] Test framework config split across `pyproject.toml`, `pytest.ini` and `setup.cfg` simultaneously
- [ ] A repo with a `tests/` directory that is empty, or contains only `__init__.py`
- [ ] Monorepo with several independent test suites in subprojects
- [ ] `conftest.py` — cited as evidence, never imported or executed
- [ ] A committed coverage report (`.coverage`, `coverage.xml`, `htmlcov/`) → may be cited as an artifact that exists, but its numbers must not be presented as the engine's own finding
- [ ] Test fixtures containing large data files → bounded, do not consume the budget
- [ ] `changes` scope where only test files changed → valid, meaningful pack
- [ ] `changes` scope where a test file was deleted → visible, not silently absent
- [ ] Non-Python ecosystems in standalone mode (JS, Go, Rust) → recognised or honestly reported as unrecognised

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/dimensions/test_strategy.py` | New — bespoke descriptor + `collect` |
| `tests/test_t009_test_strategy.py` | New |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| `.claude/hooks/**` | Must-not-touch |
| `src/easy_verifier/dimensions/_doc_extract.py` | Owned by T007, capped at four callers |
| `src/easy_verifier/core/**` | The contract is fixed; raise needed changes with the Supervisor |
| `memory/**`, `PROJECT_KANBAN.md` | Supervisor-only |

---

## Test Plan

`tests/test_t009_test_strategy.py` — temp-repo fixtures for the correspondence cases (matched,
unmatched, co-located, multiple), plus this repo as the realistic kit-aware fixture. Include a
structural test asserting the module contains no `subprocess`, no `importlib`, and no dynamic import
of target-repo paths (AC #5), and a negative test asserting no field in the pack matches a
coverage-percentage or adequacy vocabulary (AC #6).

---

## Completion Checklist

- [ ] Implementation done
- [ ] Self-review: `Skill({ skill: "code-review" })` run
- [ ] Security review: N/A (Low risk)
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T009.md`'s Evidence table (Hard-Stop Gate 5)
- [ ] `Skill({ skill: "verify" })` run
- [ ] `memory/MEMORY.md` updated (if new patterns or feedback learned)
- [ ] Supervisor notified: task ready for Stage 4 review
