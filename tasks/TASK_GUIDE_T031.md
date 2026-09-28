# TASK_GUIDE — T031: Metrics read test naming, declarations and assertions from the registry
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

---

## Requirement (Pillar 1 — Adapt the requirement)

Gaps found 2026-09-28 (`memory/decisions.md`): Kotlin/PHP counted as source but `_candidate_test_names` returns `()`; idiomatic Go (`t.Errorf`) counts 0 assertions; RSpec `it "x" do` and C# `[Fact]`/`[Test]` unmatched; C/C++/Swift/Scala/Elixir/Dart not source.

**Restated intent**:
> Test/source classification, test-name correspondence, test-declaration and assertion counting all come from the registry, so every curated language is measured correctly.

**Out of scope**:
- New metrics (T033, T034)
- Rule changes (T035)

**Requirement Refs**:
- FR-041: no second copy of language tables
- FR-027 / FR-027a unchanged (metrics from pack only; whole-set abstains on truncation)

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [ ] Restated intent confirmed to match the user's request (by Supervisor / user — not the implementing agent)
- [ ] Domain terms align with `PROJECT_SPEC.md` glossary (`grill-with-docs` run if terminology was fuzzy)
- [ ] Every Acceptance Criterion below traces to a line in the Requirement
- [ ] All Requirement Refs exist in `PRD.md` and are fully covered by the Acceptance Criteria above

> An agent must NOT start implementing until this gate is checked. If anything here is unclear,
> STOP and ask the Supervisor (Karpathy: Think Before Coding).

---

## Dependencies & Reachability

**Depends on**: T030 — registry loader and curated entries

**Entry point**: `_is_test_file`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | `_SOURCE_SUFFIXES`, `_TEST_NAME_PATTERNS`, candidate-name rules, `_ASSERTION_PATTERN`, `_TEST_DECLARATION_PATTERNS` in `core/metrics.py` are derived from the registry; no hard-coded language table remains | one source of truth |
| 2 | Kotlin `FooTest.kt` covers `Foo.kt`; PHP `FooTest.php` covers `Foo.php` | Kotlin/PHP gap |
| 3 | Go test using `t.Errorf`/`t.Fatalf` counts assertions; RSpec `it "x" do` and C# `[Fact]`, `[Test]`, `[TestMethod]` count as test declarations | Go/RSpec/C# gaps |
| 4 | Source extensions for languages outside the 9 come from Linguist data when present (T032) or the generic set; no crash when absent | C/C++/Swift/... not ignored |
| 5 | All existing metric tests for Python/JS/Java/Rust pass unchanged | no regression |

---

## Evaluation & Acceptance (How we know the agent worked correctly)

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | fixture Go repo: `calc.go` + `calc_test.go` using `t.Errorf` | `assertions_observed` > 0, calc.go covered | automated test |
| 2 | fixture Kotlin repo: `Foo.kt` + `src/test/kotlin/FooTest.kt` | `source_files_without_covering_test` = 0 | automated test |

### Verification Command (exact, runnable)

```bash
python -m pytest -q
python -m ruff check src tests
```

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T031.md`.

---

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T031.md`.

---

## UI / Design Acceptance Criteria

> N/A — pure backend task (no UI component). All three UI Evidence rows are ☐ N/A.

---

## Approach

**Pattern reference**: `core/metrics.py` existing classification (`_directory_evidence` deepest-wins) — keep the algorithm, replace only the tables

Keep `metrics.py` pure (no file reads, per its docstring): the registry is loaded once by the caller and passed in or read from a module-level immutable snapshot built at import. Add registry fields `test_name_patterns`, `test_candidates`, `test_declarations`, `assertions` with citations (Go testing pkg docs, RSpec docs, xUnit/NUnit/MSTest docs, PHPUnit, JUnit/Kotlin test).

---

## Edge Case Checklist

- [ ] `metrics.py` must still import nothing that reads the filesystem — pass data in
- [ ] Go same-package rule (`_parent` check) preserved
- [ ] Test fixture dirs (`tests/fixtures/src/x.py`) still classified by deepest segment

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/core/metrics.py` | tables → registry-derived |
| `src/easy_verifier/registry/curated/*.toml` | add test/assertion fields |
| `tests/` | per-language metric fixtures |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| src/easy_verifier/core/judge.py | T035 |
| metrics.py purity contract | structural guarantee (FR-027) |

---

## Test Plan

Per-language fixture tests (Go, Kotlin, PHP, Ruby, C#); unchanged existing suite.

---

## Completion Checklist

- [ ] Implementation done
- [ ] Self-review: `Skill({ skill: "code-review" })` run
- [ ] Security review: `Skill({ skill: "security-review" })` run (Medium risk)
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T031.md`'s Evidence table (Hard-Stop Gate 5)
- [ ] `Skill({ skill: "verify" })` run — feature confirmed working at a real surface
- [ ] `memory/MEMORY.md` updated (if new patterns or feedback learned)
- [ ] Supervisor notified: task ready for Stage 4 review
