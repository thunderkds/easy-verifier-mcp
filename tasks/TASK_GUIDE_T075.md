# TASK_GUIDE — T075: requirement-fidelity from code + documents (20/80) — routes↔tests, commit issue refs, flexible requirement items, code-aware floor
**Date**: 2026-10-04
**Complexity Level**: C3
**Risk Level**: Medium
**Priority**: P1
**Assigned agent**: backend-developer
**Agent guide**: `.claude/agents/backend.md`

---

## Mandatory Startup (Do Not Skip)

1. Read `PROJECT_SPEC.md` (glossary: Convention pattern, Requirement item, Layer, Source role)
2. Read `memory/MEMORY.md`
3. Read this file completely
4. Read `.claude/agents/backend.md`
5. Apply the C3 process from `.claude/agents/general-agent-template.md`
6. Read `memory/codebase-map.md`, `BRAINSTORMING_LOG_code-derived-rules.md`, and
   `<repo>/docs/ddr/0011-code-derived-rules-and-flexible-conventions.md`
   (docs/ddr is gitignored — main checkout only), plus DDR-0007 (registry citations)

---

## Requirement (Pillar 1 — Adapt the requirement)

User decisions (2026-10-04, DDR-0011, grilling G1/G2/G4): requirement-fidelity = documents 20
(`requirements_docs_count` 10, `code_commits_with_docs_share` 10) + `routes_without_test_share` 40 +
`commits_with_issue_reference_share` 20 + `requirement_items_traced_share` 20 (replaces the two AC
tracing rules; any requirement-item form; "flexible, not stick on a solution"). Coverage floor counts
code evidence; `task-breakdown` no longer sought.

**Restated intent**:
> A repository with routes, tests and commit history but no PRD gets a requirement-fidelity number;
> requirement items in whatever form the repo uses are traced when present and never penalise when absent.

**Out of scope**: API validation/versioning (T044); solution-fit; architecture (T074).

**Requirement Refs**: FR-067, FR-070, FR-071 (requirement-fidelity part), FR-068.

### Requirement Fidelity Gate

- [x] Restated intent confirmed (user: "yes, plan and run them automatically", 2026-10-04, after grilling G1–G5)
- [x] Domain terms align with the glossary
- [x] Every AC traces to the Requirement
- [x] All Requirement Refs exist in `PRD.md`

---

## Dependencies & Reachability

**Depends on**: T073 — route, requirement-item and issue-reference finders
**Entry point**: `routes_without_test_share`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to |
|---|---|---|
| 1 | `RATING_RULES['requirement-fidelity']` = `requirements_docs_count` 10, `code_commits_with_docs_share` 10, `routes_without_test_share` 40 (at most 0.2), `commits_with_issue_reference_share` 20 (at least 0.5, abstains below a declared minimum of commits, e.g. 20), `requirement_items_traced_share` 20 (project-default threshold, disclosed); AC↔code / AC↔test rules removed; areas + citations set | FR-070 |
| 2 | `routes_without_test_share`: routes found by T073; a route counts as tested when a test file references its path literal segments or its handler name (matched-by reported); derivation lists route count, tested count, up to N untested examples; abstains when no route found | FR-070 |
| 3 | `commits_with_issue_reference_share` over the same recent non-merge commit window the engine already uses; abstains below the minimum | FR-070 |
| 4 | `requirement_items_traced_share`: items from requirement-doc/spec roles (and any repo-declared source) traced when their id/text appears in code or tests; abstains when no items | FR-070 |
| 5 | Coverage floor: role list gains code roles (route files, test files, git history); `task-breakdown` removed; a repo with routes + tests and no docs passes the floor | FR-071 |
| 6 | `requirements-doc` / `spec-doc` roles accept common conventions (`specs/**/plan.md`, `docs/requirements*`, OpenAPI files) — extendable | FR-068 |
| 7 | Documents missing = failed document rules, never abstention | FR-067 |
| 8 | `docs/SCORING_RULES.md`, `docs/AREA_COVERAGE.md` updated; T072 sync test passes | FR-066 |
| 9 | Carried from T073 review: issue-reference matching must not count `UTF-8`, `SHA-256`, `ISO-8601`-style tokens or hex colours (declared exclusion list, extendable); Express single-argument `app.get(name)` (settings read) is not a route; Ruby bare route tokens apply only in routes files (`config/routes.rb`, declared) | FR-068 |
| 10 | Carried from T073/T074 review: repository-local and `.easy-verifier.toml` conventions used in scoring are embedded with the report/agent input so replay stays byte-equal (FR-048); after this, layer paths and requirement-item/issue patterns from those sources are used in scoring (update the T074 derivation note that says they are not yet used) | FR-048, FR-068 |
| 11 | Routes and requirement items are computed over whole files below and above the cap (T076/T068 path), never from truncated excerpts | FR-072 |

---

## Evaluation & Acceptance

### Success Criteria

| # | Given | Expect | How |
|---|---|---|---|
| 1 | Fixture: 5 routes, tests reference 4 | share 0.2 → passes (at most 0.2) | automated (boundary) |
| 2 | Fixture: no routes (library) | route rule abstains; rated if ≥ 50% measured else warning | automated |
| 3 | 30 commits, 18 with refs | 0.6 → passes | automated |
| 4 | 10 commits | issue-ref rule abstains | automated |
| 5 | Spec with `Scenario:` × 4, 3 referenced in tests | 0.75 | automated |
| 6 | nest-api (routes in NestJS controllers, e2e tests, specs/ plans) | requirement-fidelity rated (Supervisor before/after) | verify |

### Verification Command

```bash
cd <worktree> && PYTHONPATH=src <repo>/.venv/bin/python -m pytest tests/test_t075_requirement_fidelity_code_rules.py -q
```

### Evidence

> Filled by the reviewer in `tasks/TASK_REVIEW_T075.md`.

---

## Demonstration

> BEFORE (Supervisor, scratchpad `t073/before.txt`): nest-api `below_coverage_floor`; node-monorepo `below_coverage_floor`; fullstack-ts 15.

---

## UI / Design Acceptance Criteria

Pure backend/rules task — no UI change. Evidence rows: ☐ N/A.

---

## Approach

**Pattern reference**: `dimensions/requirement_fidelity.py` (current traceability + git co-change metrics), `core/git.py` (`run_git_text`), T073 finders, `core/judge.py` RATING_RULES.

C3: write a `## Design` note in `tasks/TASK_REVIEW_T075.md` before code (route↔test matching rule, commit window, item sources). Update tests pinning the old rules, citing DDR-0011.

Environment notes for the implementer: worktrees have no .venv — `PYTHONPATH=src <main>/.venv/bin/python -m pytest`; `</dev/null` on CLI calls; the 2 container tests fail on a stale Docker image (ignore); no network installs; never write into real repo trees. Budget ~60 tool calls (the step-limit hook stops at 90); the Supervisor runs real-repo before/after and screenshots at Stage 5.

---

## Edge Case Checklist

- [ ] Paths built by helpers (nest-api `test/utils/api-path.util.ts`) — handler-name match as fallback, matched-by reported
- [ ] Parameterised paths (`/users/:id`) match `/users/` segments
- [ ] Squash-merged history → abstain below minimum
- [ ] Batches (T068): routes found in sampled files are labelled sample
- [ ] Miss-list: every abstention states what bounded it

---

## Files to Change (Predicted)

| File | Change |
|---|---|
| `core/judge.py` | requirement-fidelity rules/weights; floor sources |
| `core/metrics.py`, `dimensions/requirement_fidelity.py` | new metrics, roles |
| registry roles | doc conventions |
| `docs/SCORING_RULES.md`, `docs/AREA_COVERAGE.md` | update (`git add -f`) |
| `tests/test_t075_requirement_fidelity_code_rules.py` | new |

## Files Must NOT Touch

| File | Reason |
|---|---|
| architecture rules | T074 |
| rating arithmetic, gates, floor logic | DDR-0010 |

---

## Completion Checklist

- [ ] Design note before code
- [ ] Implementation done; tests pass; ruff clean
- [ ] Supervisor notified
