# TASK_GUIDE — T002: context.py — kit detection, kit-aware/standalone modes
**Date**: 2026-08-15
**Complexity Level**: C2
**Risk Level**: Medium
**Priority**: P0
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

Decide, for any target repository, whether it was built with the kit — and load the right ground
truth either way, without ever inventing what is not there.

**Restated intent**:
> `detect_context(repo_path)` returns a `RepoContext` stating the mode (`kit-aware` or
> `standalone`), which artifacts were found, and which were sought and missing. In standalone mode
> the context carries a limited-context warning that every downstream tool response and report is
> obliged to surface. Every dimension receives this context; none re-implements detection.

**Out of scope**:
- Scope resolution (T003) and per-dimension source lists — this task supplies the *mode and the
  document inventory*, not the evidence.
- Rendering the warning into HTML (T013) — this task guarantees the warning is present in the
  structured data.

**Requirement Refs**:
- FR-001: probe for `PROJECT_SPEC.md`, `PRD.md`, `PROJECT_KANBAN.md`, `tasks/TASK_GUIDE_*.md`, `memory/`
- FR-002: kit-aware mode loads those artifacts as ground truth
- FR-003: standalone mode scans docs first (`README*`, `docs/`, ADRs, `CONTRIBUTING*`), code only where docs are silent
- FR-004: standalone mode emits an explicit limited-context warning in every tool response and report
- FR-005: never synthesize, infer, or substitute content for an artifact not found
- NFR-002: every emitted claim traceable to a file actually read
- NFR-005: works on arbitrary repos with no prior setup

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [ ] Restated intent confirmed to match the user's request (by Supervisor / user — not the implementing agent)
- [ ] Domain terms align with `PROJECT_SPEC.md` glossary
- [ ] Every Acceptance Criterion below traces to a line in the Requirement
- [ ] All Requirement Refs exist in `PRD.md` and are fully covered by the Acceptance Criteria above

---

## Dependencies & Reachability

**Depends on**: T001 — `run_dimension()` and the `EvidencePack`/`Excerpt` models must exist; this task adds `RepoContext` to the pipeline's inputs.

**Entry point**: `detect_context`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | `detect_context(repo_path)` returns `RepoContext` with `mode`, `artifacts_found`, `artifacts_missing`, `doc_sources`, `warnings` | FR-001 |
| 2 | A repo containing any kit artifact resolves to `kit-aware`; a repo containing none resolves to `standalone` | FR-001, FR-002 |
| 3 | **Partial kit repos are handled explicitly**: a repo with `PROJECT_SPEC.md` but no `tasks/` is `kit-aware` with `tasks/` listed in `artifacts_missing` — never downgraded silently to standalone, never treated as fully kit-aware | FR-001, FR-005 |
| 4 | In standalone mode, `warnings` contains a non-empty limited-context warning, and `RepoContext` exposes it such that a caller cannot construct a tool response without it | FR-004 |
| 5 | Standalone document discovery finds `README*`, `docs/**`, `CONTRIBUTING*`, and ADR-shaped files, in that precedence order, with code as a documented last resort | FR-003 |
| 6 | Not one field of `RepoContext` is populated from a file that does not exist on disk; missing artifacts appear only in `artifacts_missing` | FR-005, NFR-002 |
| 7 | `detect_context` performs no writes and executes nothing from the target repo | NFR-007 |
| 8 | Running against a repo with no config file, no kit install, and no network succeeds | NFR-005 |

---

## Evaluation & Acceptance

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | This repo (`easy-verifier-mcp`) — the free kit-aware fixture | `mode == "kit-aware"`, `PROJECT_SPEC.md`/`PRD.md`/`PROJECT_KANBAN.md`/`tasks/`/`memory/` all in `artifacts_found`, `warnings` empty | automated test |
| 2 | The site-packages directory of any installed pip package — the free standalone fixture | `mode == "standalone"`, limited-context warning present, docs discovered if any exist | automated test |
| 3 | A temp repo with `PROJECT_SPEC.md` only | `mode == "kit-aware"`, four artifacts in `artifacts_missing` | automated test |
| 4 | A completely empty temp dir | `mode == "standalone"`, `doc_sources` empty, warning present, no exception | automated test |

### Verification Command (exact, runnable)

```bash
pytest tests/test_t002_context.py -q
```

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T002.md`.

---

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T002.md`.

---

## Approach

**Pattern reference**: `src/easy_verifier/core/pipeline.py` (from T001) — match its dataclass style, its "return structured absence rather than raise" error handling, and its refusal to make judgments.

Keep detection dumb and total. A probe is a path existence check plus a readability check; the
result is data, never a decision about quality. The one design subtlety worth care is AC #3:
partial kit repos are the common real case (a repo mid-Stage-2, exactly like this one was
yesterday), and the tempting shortcuts — "all five or it's standalone", or "any one and assume the
rest" — are both wrong in a way that silently corrupts every downstream coverage score.

Model the warning as a first-class field, not a string a caller may forget to read. FR-004 says
*every* response and report; the cheapest way to make that true is to make the warning part of the
context object that every pack already carries.

---

## Edge Case Checklist

- [ ] Partial kit artifacts (AC #3) — the central case, not an exception
- [ ] `tasks/` exists but contains no `TASK_GUIDE_*.md` → directory found, guides missing, both recorded
- [ ] `memory/` exists but is empty
- [ ] A kit artifact exists as a **directory** where a file is expected (or vice versa) → treated as missing with a stated reason
- [ ] A kit artifact is a broken symlink → missing, not a crash
- [ ] Repo has `README.md`, `README.rst` and `README.txt` → all discovered, deterministic order
- [ ] `docs/` is enormous (thousands of files) → discovery is bounded and does not walk the whole tree eagerly
- [ ] `.git` and `node_modules`/`.venv`/`__pycache__` are excluded from doc discovery
- [ ] Repo is a bare git repo or a git worktree → detection still works off the filesystem
- [ ] Case-insensitive filesystems (macOS) vs. case-sensitive (Linux) → `readme.md` found on both
- [ ] Target path is a file, not a directory → clear error
- [ ] Deeply nested repo with a kit artifact only in a subdirectory → **not** kit-aware; detection is rooted at the given path and does not recurse for kit artifacts

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/core/context.py` | New — `RepoContext`, `detect_context()`, doc discovery |
| `src/easy_verifier/core/models.py` | Add `RepoContext`; add `mode`/`warnings` to `EvidencePack` |
| `src/easy_verifier/core/pipeline.py` | Thread `RepoContext` into `run_dimension()` and onto the pack |
| `src/easy_verifier/adapters/cli.py` | Surface mode + warning in output (serialization only) |
| `tests/test_t002_context.py` | New |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| `.claude/hooks/**` | Must-not-touch |
| `src/easy_verifier/core/redact.py` | Owned by T004 |
| `memory/**`, `PROJECT_KANBAN.md` | Supervisor-only |

---

## Test Plan

`tests/test_t002_context.py` — table-driven over temp-dir fixtures for the artifact combinations
(none / one / partial / all), plus two real-world fixtures: this repo for kit-aware and an
installed pip package for standalone (per `PROJECT_SPEC.md` — no synthetic fixtures needed). Add a
structural test asserting `EvidencePack` in standalone mode always carries a non-empty warning, so
FR-004 cannot regress via a code path that forgets to copy it.

---

## Completion Checklist

- [ ] Implementation done
- [ ] Self-review: `Skill({ skill: "code-review" })` run
- [ ] Security review: `Skill({ skill: "security-review" })` run (Medium risk — required)
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T002.md`'s Evidence table (Hard-Stop Gate 5)
- [ ] `Skill({ skill: "verify" })` run
- [ ] `memory/MEMORY.md` updated (if new patterns or feedback learned)
- [ ] Supervisor notified: task ready for Stage 4 review
