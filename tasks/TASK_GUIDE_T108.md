# TASK_GUIDE — T108: `change-risk` dimension tracer bullet — detected change kind + bugfix regression-test rule + `change_risk` headline
**Date**: 2026-10-16
**Complexity Level**: C2
**Risk Level**: Medium (new dimension and new payload key; project scope must stay byte-identical)
**Priority**: P1
**Assigned agent**: backend-developer
**Agent guide**: `.claude/agents/backend.md`

---

## Mandatory Startup (Do Not Skip)

Before writing any code:
1. Read `PROJECT_SPEC.md` (glossary: **Change kind**, **Change risk**, **Matched test**, **Measured file**)
2. Read `memory/MEMORY.md`
3. Read this file completely
4. Read `.claude/agents/backend.md`
5. Apply the C2 process from the Complexity matrix in `.claude/agents/general-agent-template.md`
6. Read `PRD.md` FR-079, FR-080, FR-082, US-022; `docs/ddr/0014-change-risk-dimension.md`; `BRAINSTORMING_LOG_change-risk.md`
7. Read `memory/codebase-map.md`; then `src/easy_verifier/dimensions/__init__.py`, one small dimension
   end to end (`code_quality.py`), `core/judge.py` (rule tables, `COVERAGE_FLOORS`, overall), `core/score.py`
   (`ScoreResult`), `dimensions/test_strategy.py` (`_correspondence`, `_project_boundary`,
   `_deleted_change_set_tests`), `core/structure.py:find_issue_references`

---

## Requirement (Pillar 1 — Adapt the requirement)

User, 2026-10-16: path B sliced, "Separate headline", S1 rule table approved.

**Restated intent**:
> Add a 14th dimension, **`change-risk`**, that rates a change (not the repository) at `changes` and
> `worktree` scope and abstains with a stated reason at `project` and `task` scope. In this tracer
> slice it **detects** the change kind and applies the **bugfix** rule only: a bugfix passes
> `bugfix_without_regression_test` when at least one test file added or changed in the scope is a
> **matched test** for changed code. Its rating is reported as a separate headline **`change_risk`**
> next to `overall` (CLI, MCP and HTML report) and is **not** averaged into `overall`. The payload
> carries `change_kind: {value, source: "detected", signals: [...]}`.

**Kind detection (FR-080)**, deterministic, in this order of evidence, all disclosed in `signals`:
branch name prefix (`fix/`, `bugfix/`, `hotfix/` → bugfix; `feat/`, `feature/` → feature; `refactor/` →
refactor; `chore/`, `docs/`, `ci/`, `deps/` → chore), Conventional-Commit subjects in the range
(`fix:`, `feat:`, `refactor:`, `chore:`/`docs:`/`ci:`/`build:`), issue references ("fixes #N", via
`find_issue_references`), and file kinds (only docs/config/lockfile changed → chore). Mixed signals →
the most demanding kind (bugfix > feature > refactor > chore). No signal → `feature`. At `worktree`
scope (no commits) only branch name and file kinds apply.

**In this slice, kinds other than bugfix** (feature, refactor, chore) are detected and shown, but the
dimension **abstains** with reason "rules for <kind> arrive in T110" — no invented rule.

**Out of scope**: the `change_kind` MCP gate / agent confirmation (T109); feature/refactor/chore rules
(T110); symbol-level matching (S2); any change to other dimensions' rules or to `overall`'s math.

**Requirement Refs**: FR-079, FR-080, FR-082 (bugfix row), US-022; preserves NFR-001, FR-022, FR-021.

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [x] Restated intent confirmed against the user's request (Supervisor, 2026-10-16)
- [x] Domain terms align with `PROJECT_SPEC.md`
- [x] Every Acceptance Criterion traces to the Requirement
- [x] Requirement Refs exist in `PRD.md`

---

## Dependencies & Reachability

**Depends on**: T107
**Entry point**: `score_repository` (`src/easy_verifier/core/score.py`) via CLI `score --scope changes` and MCP `score(scope="changes")`; the dimension is also callable alone as `change-risk` (FR-009)

---

## Acceptance Criteria

| # | Criterion (testable) |
|---|----------------------|
| 1 | `change-risk` is registered in `DIMENSIONS`, listed by `list_dimensions`, callable on its own (CLI + MCP tool), with a descriptor, roles and a coverage floor like the others |
| 2 | At `project` and `task` scope it abstains with a stated reason ("change risk is rated at changes/worktree scope only"); `score --scope project` payload on this repo + 3 real repos is **byte-identical** to before, **except** for the presence of the new dimension's abstention entry, if the payload lists every dimension — if it does, the reviewer accepts exactly that one added entry and nothing else; if the design can omit it at project scope instead, prefer omitting it (state which in the review) |
| 3 | Kind detection as specified above, deterministic, with `signals` listing each signal and its source (branch / commit subject / issue reference / file kinds); unit tests per signal, per conflict (most demanding wins) and for the no-signal default |
| 4 | `bugfix_without_regression_test` (weight, threshold `≥ 1`, citation = the matched test file(s) or the changed source files lacking one): matched = a test file **added or changed** in the scope that corresponds to a changed source file by the existing naming correspondence within one project (`_project_boundary`), with the counterpart searched repository-wide. A test **deleted** by the diff never matches. A rule with no standard behind it cites the project default, like other project-default thresholds |
| 5 | The score payload gains a top-level `change_risk` headline (rating or abstention, plus `change_kind`) next to `overall`; `overall`'s value and contributors are unchanged by this dimension. CLI and MCP payloads are identical (parity, FR-022 normalization) |
| 6 | HTML report: a "Change risk" block next to the overall summary showing rating/abstention, kind + source + signals, and the failing rule with its citation |
| 7 | **Real repos, pre-registered**: before running, write in the review file the expected result for (a) the node-monorepo bugfix `09be767d0` (no test) → `change_risk` fails the rule; (b) one bugfix-with-test commit found by `git log --grep` in a real repo (alias + short hash) → passes; (c) one feature commit → abstains "rules for feature arrive in T110". Then run (background, one at a time) and paste the `change_risk` headline of each |
| 8 | Tests in `tests/test_t108_change_risk.py` on synthetic git repos in `tmp_path`: bugfix with matched test passes; bugfix without passes→fails; deleted test never matches; test in another project of a monorepo does not match; worktree scope; project scope abstains |

---

## Evaluation & Acceptance

### Success Criteria (observable, pass/fail)
- The node-monorepo 97-case now shows `change_risk` failing `bugfix_without_regression_test`.
- AC2 byte-identity (with the single declared exception, if any) holds on 4 repos.
- New tests pass; full suite and ruff green.

### Verification Command (exact, runnable)

Py3.12 venv as in T107. Then:

```bash
<py312> -m pytest -q tests/test_t108_change_risk.py
<py312> -m pytest -q          # background
<py312> -m ruff check src tests
<py312> -m easy_verifier.adapters.cli score --repo <repo> --scope changes --ref <hash> < /dev/null
```

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T108.md`.

---

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T108.md`. BEFORE = `list_dimensions` without `change-risk` and the
> node-monorepo `09be767d0` payload with no `change_risk` key.

---

## UI / Design Acceptance Criteria

> The HTML report gains one block (AC6). Evidence rows: visual regression = a rendered report screenshot
> or HTML excerpt reviewed against the existing summary block; design-system compliance = reuses the
> existing report CSS classes only (no new colours/fonts); responsiveness = same container as the
> summary block, checked at 375 px and 1280 px.

---

## Approach

**Pattern reference**: an existing small dimension (`dimensions/code_quality.py`) for the
descriptor/collect shape; `test_strategy._correspondence` + `_project_boundary` for matching (import or
extract into a shared helper — do not copy); `judge.py` rule tables for the rule; `score.py` for the
payload key.

1. Capture BEFORE. 2. Kind detection, test-first. 3. Dimension + rule, test-first. 4. Payload headline +
report block. 5. AC2 and AC7 real-repo runs (background, one at a time).

---

## Edge Case Checklist

- [ ] Rename-only diff (`R100`) is not changed code
- [ ] Generated / vendored / third-party paths never count as changed code (T087)
- [ ] Root commit, empty diff, clipped diff (`MAX_DIFF_CHARS`) → disclosed abstention, not a rating
- [ ] Test-only bugfix diff (only a test changed) → kind detected from signals; the rule passes only if the test corresponds to changed code — a test-only diff has no changed code, so abstain "no changed source code"
- [ ] Branch name unavailable (detached HEAD, `--ref <hash>`) → commit subjects + file kinds only
- [ ] Commit subjects are read only from the scope's range, never from unrelated history
- [ ] Replay: same diff → byte-equal payload

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/dimensions/change_risk.py` | new |
| `src/easy_verifier/dimensions/__init__.py` | register |
| `src/easy_verifier/core/judge.py`, `core/metrics.py` | rule, metric, floor, citation |
| `src/easy_verifier/core/score.py` | `change_risk` headline |
| `src/easy_verifier/core/report.py` | Change risk block |
| `tests/test_t108_change_risk.py` | new |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| other dimensions' rule tables / weights | no repository-health change |
| `src/easy_verifier/core/scope.py` | scope semantics stay |
| `src/easy_verifier/core/gate.py` | the kind gate is T109 |

---

## Test Plan

Synthetic git repos in `tmp_path` per AC8 (branch names, commit subjects, issue refs, deleted test,
monorepo with two `package.json`). Real-repo runs are evidence, not tests.

---

## Completion Checklist

- [ ] Implementation committed on `feat/T108-change-risk`
- [ ] AC7 pre-registered expectations written **before** the runs; results pasted after
- [ ] No private name or path in any tracked file (T100 guard green)
- [ ] Supervisor notified: ready for Stage 4 review
