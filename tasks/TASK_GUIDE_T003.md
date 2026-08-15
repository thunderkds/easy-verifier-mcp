# TASK_GUIDE — T003: scope.py — task / changes / worktree / project
**Date**: 2026-08-15
**Complexity Level**: C1
**Risk Level**: Low
**Priority**: P0
**Assigned agent**: Backend-Implementer
**Agent guide**: `.claude/agents/backend.md`

---

## Mandatory Startup (Do Not Skip)

1. Read `PROJECT_SPEC.md`
2. Read `memory/MEMORY.md`
3. Read this file completely
4. Read `.claude/agents/backend.md`
5. **C1** — apply the C1 process from the Complexity matrix in `.claude/agents/general-agent-template.md`
6. C1 and multi-file — skim `memory/codebase-map.md` for layout only

---

## Requirement (Pillar 1 — Adapt the requirement)

Let the caller ask a narrower question than "the whole repo", and resolve that question into a
concrete file set the dimensions can work from.

**Restated intent**:
> `resolve_scope(kind, repo_path, context, **args)` returns a `Scope` naming the evaluated file set
> and, for `changes`, the diff — derived from local git with no network remote. `task` scope in
> kit-aware mode resolves a task ID to its `TASK_GUIDE_Txxx.md` and carries its acceptance criteria
> forward as evidence.

**Out of scope**:
- Relevance *ordering* of the resolved set (T005) — this task produces the set and the "changed
  first" signal; `budget.py` decides the order.
- Any dimension-specific filtering.

**Requirement Refs**:
- FR-006: four scopes — `task`, `changes`, `worktree`, `project`
- FR-007: `task` scope resolves to `tasks/TASK_GUIDE_Txxx.md` and includes its acceptance criteria
- FR-008: `changes` scope derives changed files and diff from git without a network remote
- NFR-007: never write to the target repo, never execute code from it
- NFR-012: no outbound network request

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [ ] Restated intent confirmed to match the user's request (by Supervisor / user)
- [ ] Domain terms align with `PROJECT_SPEC.md` glossary
- [ ] Every Acceptance Criterion below traces to a line in the Requirement
- [ ] All Requirement Refs exist in `PRD.md` and are fully covered by the Acceptance Criteria above

---

## Dependencies & Reachability

**Depends on**: T001 — pipeline contract; T002 — `RepoContext` (needed to know whether `task` scope is even resolvable).

**Entry point**: `resolve_scope`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | All four scope kinds are accepted and return a `Scope` with `kind`, `files`, `changed_files`, `diff`, `task_ref`, `notes` | FR-006 |
| 2 | `project` scope returns the repo's tracked/relevant file set with `.git`, vendored and build directories excluded | FR-006 |
| 3 | `worktree` scope returns uncommitted modifications (staged + unstaged + untracked), and is correct when the tree is clean (empty set, not an error) | FR-006 |
| 4 | `changes` scope accepts a commit range, a single commit, or a branch name and derives files + diff via local git only | FR-008 |
| 5 | No git invocation contacts a remote — a test asserts the command set contains no `fetch`, `pull`, `ls-remote`, or `clone` | FR-008, NFR-012 |
| 6 | `task` scope in kit-aware mode resolves `T007` → `tasks/TASK_GUIDE_T007.md` and populates `task_ref` with the guide path plus its parsed Acceptance Criteria rows | FR-007 |
| 7 | `task` scope in **standalone** mode returns a clear, structured refusal naming why (no kit artifacts), and does not fall back to `project` scope silently | FR-005, FR-007 |
| 8 | Every git call is read-only; no command mutates the target repo's index, worktree, or refs | NFR-007 |
| 9 | Target repo is not a git repository → `project` still works; `changes` and `worktree` return a structured "git required" result, not a traceback | FR-006 |

---

## Evaluation & Acceptance

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | This repo, `changes` scope over the last two commits | `changed_files` matches `git diff --name-only` for the same range | automated test |
| 2 | This repo, `task` scope, `T003` | `task_ref` points at this guide and its acceptance criteria are parsed | automated test |
| 3 | A temp dir with no `.git` | `project` succeeds; `worktree` returns the structured git-required result | automated test |
| 4 | Standalone repo, `task` scope | Structured refusal naming the missing kit context; no silent widening | automated test |

### Verification Command (exact, runnable)

```bash
pytest tests/test_t003_scope.py -q
```

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T003.md`.

---

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T003.md`.

---

## Approach

**Pattern reference**: `src/easy_verifier/core/context.py` (from T002) — same "return structured absence, never raise, never widen silently" discipline.

Shell out to `git` via `subprocess` with an explicit argument list (never `shell=True`), rather than
adding a git library dependency — the command set here is small and the dependency is not worth it.
Pass `-C <repo_path>` so nothing depends on the process working directory.

AC #7 is the one that matters most for the project's integrity: a `task` scope that quietly becomes
a `project` scope produces a coverage score that looks fine and answers a question nobody asked.
Refuse loudly instead.

---

## Edge Case Checklist

- [ ] Clean worktree → empty change set, not an error
- [ ] Untracked files in `worktree` scope → included (they are part of the uncommitted state)
- [ ] Renamed / deleted / binary files in a diff → represented, and deleted files are not opened for excerpts
- [ ] Commit range with zero commits, or an invalid ref → structured error naming the bad ref
- [ ] Detached HEAD, shallow clone, or a repo with a single commit (no parent to diff against)
- [ ] Submodules → not recursed into
- [ ] Task ID given in different forms (`T007`, `t007`, `TASK_GUIDE_T007.md`) → normalized
- [ ] Task ID that does not exist → structured miss listing the IDs that do exist
- [ ] Two guides matching one ID → deterministic error, not an arbitrary pick
- [ ] Paths with spaces or non-ASCII characters
- [ ] Very large diff → the diff is bounded here or clearly marked for `budget.py` to truncate downstream, never loaded unbounded into memory
- [ ] `git` binary absent from PATH (relevant inside the container) → structured error

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/core/scope.py` | New — `Scope`, `resolve_scope()`, read-only git helpers |
| `src/easy_verifier/core/models.py` | Add `Scope`; record scope on `EvidencePack` |
| `src/easy_verifier/core/pipeline.py` | Accept a resolved `Scope` |
| `src/easy_verifier/adapters/cli.py` | `--scope` / `--task` / `--range` flags (parsing only) |
| `tests/test_t003_scope.py` | New |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| `.claude/hooks/**` | Must-not-touch |
| `src/easy_verifier/core/redact.py` | Owned by T004 |
| `memory/**`, `PROJECT_KANBAN.md` | Supervisor-only |

---

## Test Plan

`tests/test_t003_scope.py` — use this repo as the git fixture (real history, real diffs) and temp
dirs for the degenerate cases. Include a static test over `scope.py` asserting no remote-contacting
git subcommand appears anywhere in the module (AC #5), since that is a security property that a
future well-meaning edit could quietly break.

---

## Completion Checklist

- [ ] Implementation done
- [ ] Self-review: `Skill({ skill: "code-review" })` run
- [ ] Security review: N/A (Low risk)
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T003.md`'s Evidence table (Hard-Stop Gate 5)
- [ ] `Skill({ skill: "verify" })` run
- [ ] `memory/MEMORY.md` updated (if new patterns or feedback learned)
- [ ] Supervisor notified: task ready for Stage 4 review
