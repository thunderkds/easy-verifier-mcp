# TASK_GUIDE — T107: Context roles are read repository-wide at narrow scopes
**Date**: 2026-10-16
**Complexity Level**: C2
**Risk Level**: Medium (changes every narrow-scope score; project scope must stay byte-identical)
**Priority**: P1
**Assigned agent**: backend-developer
**Agent guide**: `.claude/agents/backend.md`

---

## Mandatory Startup (Do Not Skip)

Before writing any code:
1. Read `PROJECT_SPEC.md` (glossary: **Context role**, **Measured file**)
2. Read `memory/MEMORY.md`
3. Read this file completely
4. Read `.claude/agents/backend.md`
5. Apply the C2 process from the Complexity matrix in `.claude/agents/general-agent-template.md`
6. Read `PRD.md` FR-078 and US-022, `BRAINSTORMING_LOG_change-risk.md`, and `docs/ddr/0014-change-risk-dimension.md`
7. Read `memory/codebase-map.md`, then the role probe in each dimension listed under Approach

---

## Requirement (Pillar 1 — Adapt the requirement)

User, 2026-10-16: "for the medium/small scope, like implement, and fix bugs, does this repos cover them
as good as" → path B approved; this is slice 1's shared fix.

**Restated intent**:
> At a narrow scope (`changes`, `worktree`, `task`), a dimension's **context roles** — test config, CI
> workflow, lockfile, lint/format config, package manifest, container config, API spec, project
> documents — are read from the **whole repository** and cited as context, while **measured files**
> (source and test code) stay the scope's file set. A context role that sits outside the diff is no
> longer recorded as `"not in the resolved … scope"`, so dimensions stop abstaining below their
> coverage floor for that reason. `project`-scope payloads do not change by a single byte.

**Out of scope**: the `change-risk` dimension (T108); any rule, weight or threshold change; widening
which *code* files are measured; `core/scope.py` resolution semantics (changes = diff files).

**Requirement Refs**: FR-078, US-022; preserves FR-006/FR-008 (scope semantics), FR-022 (replay).

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [x] Restated intent confirmed against the user's request (Supervisor, 2026-10-16)
- [x] Domain terms align with `PROJECT_SPEC.md` (context role, measured file, scope)
- [x] Every Acceptance Criterion traces to the Requirement
- [x] Requirement Refs exist in `PRD.md`

---

## Dependencies & Reachability

**Depends on**: None
**Entry point**: `score_repository` (`src/easy_verifier/core/score.py`) — reached by CLI `score --scope changes` and MCP `score(scope="changes")`

---

## Acceptance Criteria

| # | Criterion (testable) |
|---|----------------------|
| 1 | One shared definition of which roles are **context roles** (the list in FR-078, expressed as the existing role names) and one shared helper that, at a narrow scope, returns a context role's files from the repository-wide role resolution instead of filtering them to the scope's file set. Every dimension that today records `"not in the resolved … scope"` for a role uses it: `test_strategy`, `security`, `supply_chain`, `operations`, `infrastructure`, `api`, `data`, `reliability` (verify the list by grep; add any missed) |
| 2 | Code and test files are still measured only from the scope's file set: no metric that counts source/test files changes its denominator at a narrow scope because of this task |
| 3 | At a narrow scope, each context role read this way is visible in the pack (cited excerpt or `files_read`) and the pack says it was read as context (a note or warning naming the roles), so a reader can tell repository context from changed files |
| 4 | **Project scope byte-identical**: `score --scope project` JSON payload before vs after on this repo and on 3 real repos (`fullstack-ts`, `python-ml`, `node-monorepo`; paths in `.local/real-repos.md`) is byte-equal after the existing three-rule normalization (DDR-0005) |
| 5 | **Narrow-scope effect, real repo**: re-run the 2026-10-05 case `score --scope changes --ref 09be767d0` on `node-monorepo`. Before: test-strategy, security, requirement-fidelity abstain (`below_coverage_floor`, context roles "not in the resolved changes scope"). After: no abstention whose stated cause is a context role outside the diff. Paste both payload summaries (overall, per-dimension rating/abstention) |
| 6 | Unresolved narrow scope still refuses (does not silently become a project read): the existing "unresolved scope" path in each dimension is unchanged, and a test proves it |
| 7 | Tests: a synthetic repo in `tmp_path` with a test config, CI file and lockfile outside a one-file diff — each listed dimension reads them as context at `changes` scope and measures only the changed file; project-scope output for the same repo unchanged |

---

## Evaluation & Acceptance

### Success Criteria (observable, pass/fail)
- AC4 byte-equality holds on 4 repos.
- AC5 shows the abstentions caused by out-of-diff context roles are gone.
- New tests pass; full suite and ruff green.

### Verification Command (exact, runnable)

`.venv` is broken (system Python 3.14). Use a py3.12 venv with the project installed:
`uv venv -p /usr/bin/python3.12 <dir> && VIRTUAL_ENV=<dir> uv pip install -e '.[dev]'`.

```bash
<py312> -m pytest -q tests/test_t107_context_roles_repo_wide.py
<py312> -m pytest -q          # long: background
<py312> -m ruff check src tests
<py312> -m easy_verifier.adapters.cli score --repo <repo> --scope project < /dev/null   # before/after, background, one at a time
```

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T107.md`.

---

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T107.md`. BEFORE = the node-monorepo `--scope changes --ref 09be767d0`
> payload summary showing the three `below_coverage_floor` abstentions.

---

## UI / Design Acceptance Criteria

> N/A — no UI. All three UI Evidence rows are ☐ N/A.

---

## Approach

**Pattern reference**: `src/easy_verifier/dimensions/test_strategy.py:233-251` — the role probe
(`in_bounds = paths if whole_repo else [p for p in paths if p in scope_set]`) is the line that changes:
for a context role, `in_bounds` is the repository-wide `paths`.

1. Capture BEFORE (AC5) and the project payloads for AC4 **before** any code change (background, one at a time).
2. Test-first (AC7), then the shared context-role definition + helper, then each dimension's probe.
3. Re-run AC4 and AC5.

---

## Edge Case Checklist

- [ ] A context role that is *also* in the diff (e.g. the lockfile changed) is read once, not twice
- [ ] Secret-bearing files are never read as context (`_is_secret_bearing`, DDR-0002)
- [ ] Third-party roots (T087 exclusion) stay excluded for context roles too
- [ ] Byte budget: context excerpts compete with changed-file evidence — changed files must not be starved; context goes after tier-1 changed files in relevance order
- [ ] `task` scope without kit artifacts still refuses as today
- [ ] The T098 `capped` disclosure stays truthful for context roles read repo-wide

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| a shared module (e.g. `src/easy_verifier/core/roles.py` or `dimensions/_scope_roles.py`) | context-role set + helper |
| `src/easy_verifier/dimensions/{test_strategy,security,supply_chain,operations,infrastructure,api,data,reliability}.py` | use the helper in the role probe |
| `tests/test_t107_context_roles_repo_wide.py` | new |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| `src/easy_verifier/core/scope.py` | scope semantics stay (FR-006/008) |
| `src/easy_verifier/core/judge.py` rule tables/weights | no rule change in this task |
| `experiments/` | unrelated |

---

## Test Plan

Synthetic repo in `tmp_path` (git init, two commits) per AC7; existing scope/dimension tests must stay
green unchanged — a changed expectation in an old test is a stop-and-report, not a fix.

---

## Completion Checklist

- [ ] Implementation committed on `feat/T107-context-roles`
- [ ] AC4/AC5 outputs pasted into `tasks/TASK_REVIEW_T107.md`
- [ ] No private name or path in any tracked file (T100 guard green)
- [ ] Supervisor notified: ready for Stage 4 review
