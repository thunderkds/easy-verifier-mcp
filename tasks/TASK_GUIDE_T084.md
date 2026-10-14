# TASK_GUIDE — T084: `breaking_api_changes_observed` counts only removals in files the api pack read
**Date**: 2026-10-08
**Complexity Level**: C1
**Risk Level**: Medium
**Priority**: P2
**Assigned agent**: backend-developer
**Agent guide**: `.claude/agents/backend.md`

---

## Mandatory Startup (Do Not Skip)

Before writing any code:
1. Read `PROJECT_SPEC.md`
2. Read `memory/MEMORY.md`
3. Read this file completely
4. Read `.claude/agents/backend.md`
5. Apply the C1 process from the Complexity matrix in `.claude/agents/general-agent-template.md`
6. Read `memory/codebase-map.md`
7. Read `tasks/TASK_GUIDE_T083.md` and `tasks/TASK_REVIEW_T083.md` (where this follow-up came from)

---

## Requirement (Pillar 1 — Adapt the requirement)

T083 made `src/easy_verifier/dimensions/api.py:_breaking_metric` abstain when no spec/route file in the diff was read. But when at least one diff file *was* read, the metric still counts removals (`gone`) from **every** spec/route file in the diff, including files the pack did not read (beyond `MAX_SPEC_FILES`, unreadable, outside the read set). Those removals are part of the value but not in `computed_from` — the value is partly uncited (FR-027).

**Restated intent** (user decision 2026-10-08, "Count read files only"):
> `breaking_api_changes_observed` counts only removals found in diff files the api pack actually read (and cites exactly those files). Diff files that have removals but were not read are **listed in the derivation as "not counted"** (redacted paths, capped like the examples), never added to the value. When no diff file was read, T083's abstention stays as is.

Also in scope (same function, left out of T078 because T084 owned it): `_breaking_metric` builds route tokens from `_curated_conventions()`; use the call's resolved conventions (`context_conventions(context)` as `_scan` does) so a repo's extra `route_tokens` find removed routes too. Pass what is needed from the caller; smallest change.

**Out of scope**: changing the spec-key / route parsing; changing T083 abstention text; other metrics.

**Requirement Refs**: FR-027 (cite what was read), FR-048 / FR-068 (conventions).

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [x] Restated intent confirmed (user decision 2026-10-08 via AskUserQuestion; user "yes, run the remaining tasks" 2026-10-08)
- [x] Domain terms align with `PROJECT_SPEC.md` glossary
- [x] Every Acceptance Criterion below traces to a line in the Requirement
- [x] All Requirement Refs exist in `PRD.md`

---

## Dependencies & Reachability

**Depends on**: T083, T078 (merged)

**Entry point**: `_breaking_metric`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | Diff with removals in read file A (2 removed) and unread file B (3 removed) → value 2, `computed_from` = (A,), derivation names B as "not counted" (with its count) | read files only |
| 2 | All removals in read files → value and derivation identical to today (no "not counted" text) | no regression |
| 3 | No read file → T083 abstention unchanged (existing T083 tests green, unedited) | T083 kept |
| 4 | Unread-file list is redacted and capped (`MAX_EXAMPLES` style, "and N more") | honesty / redaction |
| 5 | A repo `.easy-verifier.toml` `[conventions] route_tokens` extra makes a removed custom-route line count in `_breaking_metric` | resolved conventions |
| 6 | CLI and MCP agree on a changes-scope payload for AC 1 (DDR-0005) | parity |

---

## Evaluation & Acceptance (How we know the agent worked correctly)

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | AC 1 temp git repo, `--scope changes --ref HEAD~1..HEAD` | value counts read file only; unread listed | automated test + CLI run |
| 2 | nest-api `--scope project` (breaking abstains at project scope) | payload sha256 unchanged BEFORE vs AFTER | real-repo run |

### Verification Command (exact, runnable)

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check src tests
```

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T084.md`.

---

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T084.md`.

BEFORE commands (before any code change; paste timestamped output): (1) a temp git repo built so one spec file is read and another with removals is not (e.g. more spec files than `MAX_SPEC_FILES`, or the unread file outside the pack's read set) — `score --scope changes --ref HEAD~1..HEAD </dev/null`, show the api `breaking_api_changes_observed` value includes the unread file's removals while `computed_from` omits it; (2) nest-api `--scope project </dev/null | sha256sum` baseline (background).

---

## UI / Design Acceptance Criteria

> N/A — pure backend task. All three UI Evidence rows are ☐ N/A.

---

## Real repos

Absolute paths: `.local/real-repos.md` (local, git-ignored).

real repos (read-only, `--repo` only): nest-api `<real-repos>/nest-api`, fullstack-ts `<real-repos>/fullstack-ts`, node-monorepo `<real-repos>/node-monorepo`, next-web (path in `memory/learnings.md`, T049 entry). Run real-repo scores with `run_in_background` and `</dev/null`; worktree code via `PYTHONPATH=<worktree>/src`. CLI: `.venv/bin/python -m easy_verifier.adapters.cli score --repo R --scope project|changes [--ref A..B] [--all] </dev/null`.

---

## Approach

**Pattern reference**: T083 fix in `_breaking_metric`; `_scan` uses `context_conventions(context)`. Track removals per file; sum only `path in read`; collect the rest for the derivation.

---

## Edge Case Checklist

- [ ] Renamed spec file (old_path is spec) — the read check uses the path the pack read
- [ ] Unread file is secret-bearing → already skipped; never named beyond today's behaviour
- [ ] Unread file with zero removals → not listed

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/dimensions/api.py` | `_breaking_metric` + its caller |
| `tests/test_t084_breaking_read_only.py` | new |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| `src/easy_verifier/packs/*`, `registry/packs/*` | T085 in parallel |
| `dimensions/blast_radius.py`, `dimensions/data.py` | T086 in parallel |

---

## Test Plan

Unit tests on `_breaking_metric` with a fake diff (AC 1–4); a score-level temp-repo test for AC 5; CLI vs MCP payload compare for AC 6. Real-repo sha256.

## Completion Checklist

- [ ] Implementation done
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T084.md` Evidence (Hard-Stop Gate 5)
- [ ] Real-repo BEFORE/AFTER pasted in Demonstration
- [ ] Supervisor notified: task ready for Stage 4 review
