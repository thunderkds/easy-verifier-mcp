# TASK_GUIDE — T085: frontend-a11y credits Next.js / Nuxt default browser targets as a browser-support declaration
**Date**: 2026-10-08
**Complexity Level**: C1
**Risk Level**: Low
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
7. Read `tasks/TASK_GUIDE_T049.md` and `tasks/TASK_REVIEW_T049.md` (the pack; P2 finding this comes from)

---

## Requirement (Pillar 1 — Adapt the requirement)

The frontend-a11y pack (`src/easy_verifier/packs/frontend_a11y.py`, `registry/packs/frontend-a11y.toml`) rates `browser_support_declaration_missing` = 1 when no `browser_support` file declares targets. Next.js and Nuxt ship a documented default browser target, the same way the pack already credits their default viewport through `viewport_default_entries` (`defaulted` count). On next-web (a Next/Nuxt app) the metric reports "missing" though the framework defines targets; a11y = 45.

**Restated intent** (user decision 2026-10-08, "Count framework default"):
> When no explicit browser-support declaration is found but the scope ships a Next.js or Nuxt config file (registry-listed globs, cited to each framework's supported-browsers documentation), `browser_support_declaration_missing` = 0, citing that config file, and the derivation says the targets are the **framework default** (naming the framework). An explicit declaration still wins and is reported as today.

The globs live in a new cited pack field (e.g. `browser_support_default_entries`, mirroring `viewport_default_entries`) — data, not Python names. Citation: Next.js https://nextjs.org/docs/architecture/supported-browsers ; for Nuxt find the official docs page stating its default build target — if none exists, STOP and report to the Supervisor (do not cite a non-authoritative source).

**Out of scope**: other frameworks; changing rating weights; parsing the default target list.

**Requirement Refs**: FR-049 (packs, T049), DDR-0007 (cited registry).

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [x] Restated intent confirmed (user decision 2026-10-08 via AskUserQuestion; user "yes, run the remaining tasks" 2026-10-08)
- [x] Domain terms align with `PROJECT_SPEC.md` glossary
- [x] Every Acceptance Criterion below traces to a line in the Requirement
- [x] All Requirement Refs exist in `PRD.md`

---

## Dependencies & Reachability

**Depends on**: T049 (merged)

**Entry point**: `browser_support_default_entries`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | Scope with markup + `next.config.js`, no browserslist → metric value 0, `computed_from` = the config, derivation contains "framework default" and "Next.js" | Next default |
| 2 | Same with `nuxt.config.ts` → value 0, "Nuxt" | Nuxt default |
| 3 | Explicit `.browserslistrc` plus `next.config.js` → derivation is today's "browser support declared at …" | explicit wins |
| 4 | Neither → value 1, today's derivation unchanged | no regression |
| 5 | Globs are a cited pack registry field validated by the registry (shape check, `PACK_FIELDS`); the local layer can add a glob (test) | DDR-0007 |
| 6 | Pack off → payload byte-identical to BEFORE on a real repo (sha256) | no regression |
| 7 | Real repo: next-web a11y browser metric 1 → 0, dimension rating BEFORE/AFTER pasted | real-repo verified |

---

## Evaluation & Acceptance (How we know the agent worked correctly)

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | fixtures AC 1–4 | as listed | automated test |
| 2 | next-web with the a11y pack | browser metric 0, "framework default" | real-repo run (background) |

### Verification Command (exact, runnable)

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check src tests
```

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T085.md`.

---

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T085.md`.

BEFORE commands (before any code change; paste timestamped output): next-web `score --scope project` with the frontend-a11y pack enabled (see `tasks/TASK_REVIEW_T049.md` for the exact command and pack flag) `</dev/null` — record the a11y rating and `browser_support_declaration_missing` derivation; plus the same run with the pack off piped to `sha256sum` (background).

---

## UI / Design Acceptance Criteria

> N/A — pure backend task. All three UI Evidence rows are ☐ N/A.

---

## Real repos

Absolute paths: `.local/real-repos.md` (local, git-ignored).

real repos (read-only, `--repo` only): nest-api `<real-repos>/nest-api`, fullstack-ts `<real-repos>/fullstack-ts`, node-monorepo `<real-repos>/node-monorepo`, next-web (path in `memory/learnings.md`, T049 entry). Run real-repo scores with `run_in_background` and `</dev/null`; worktree code via `PYTHONPATH=<worktree>/src`. CLI: `.venv/bin/python -m easy_verifier.adapters.cli score --repo R --scope project|changes [--ref A..B] [--all] </dev/null`.

---

## Approach

**Pattern reference**: `viewport_default_entries` in `frontend-a11y.toml` and its `is_default`/`defaulted` handling in `_scan`; BROWSER_METRIC block in `_metrics`. Add the field, a `default` hit in `_Scan`, one branch in the metric.

---

## Edge Case Checklist

- [ ] Config file found but outside `shipped` (test/excluded paths) → not credited
- [ ] Both Next and Nuxt configs → first by path order, deterministic
- [ ] `docs/` mention of the pack field updated if docs list pack fields

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/packs/frontend_a11y.py` | default-target branch |
| `src/easy_verifier/registry/packs/frontend-a11y.toml` | new cited field |
| `src/easy_verifier/core/registry.py` | `PACK_FIELDS` entry for the new field |
| `tests/test_t085_a11y_default_browsers.py` | new |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| `dimensions/api.py` | T084 in parallel |
| `dimensions/blast_radius.py`, `dimensions/data.py`, `registry/curated/conventions.toml` | T086 in parallel |

---

## Test Plan

Unit tests on the pack for AC 1–5; existing T049 tests stay green unedited (except an expectation that encoded the old Next/Nuxt "missing" result — call it out if so). Real-repo next-web + pack-off sha256.

## Completion Checklist

- [ ] Implementation done
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T085.md` Evidence (Hard-Stop Gate 5)
- [ ] Real-repo BEFORE/AFTER pasted in Demonstration
- [ ] Supervisor notified: task ready for Stage 4 review
