# TASK_GUIDE — T073: Structure convention patterns — layers, routes, requirement items, issue references (registry, extendable)
**Date**: 2026-10-04
**Complexity Level**: C2
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
5. Apply the C2 process from `.claude/agents/general-agent-template.md`
6. Read `memory/codebase-map.md`, `BRAINSTORMING_LOG_code-derived-rules.md`, and
   `<repo>/docs/ddr/0011-code-derived-rules-and-flexible-conventions.md`
   (docs/ddr is gitignored — main checkout only), plus DDR-0007 (registry citations)

---

## Requirement (Pillar 1 — Adapt the requirement)

User decisions (2026-10-04, DDR-0011): read code structure through **cited registry tokens** (no new
dependency); every convention is a **declared, extendable pattern list** ("flexible, not stick on a
solution"). This task adds the data and the pure extraction functions only; no rating rule changes.

**Restated intent**:
> The engine can classify a source file into a layer, find route handlers, find requirement items in any
> recognised form, and find issue references in commit messages — all from declared, cited patterns that a
> repository can extend — without changing any score yet.

**Out of scope**: new rating rules, weights, floors (T074/T075); report changes.

**Requirement Refs**: FR-068 (pattern lists, citations, extension), FR-043/FR-049 (cited registry).

### Requirement Fidelity Gate

- [x] Restated intent confirmed (user: "yes, plan and run them automatically", 2026-10-04, after grilling G1–G5)
- [x] Domain terms align with the glossary
- [x] Every AC traces to the Requirement
- [x] All Requirement Refs exist in `PRD.md`

---

## Dependencies & Reachability

**Depends on**: None
**Entry point**: `layer_of`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to |
|---|---|---|
| 1 | Declared pattern data, each entry cited (DDR-0007): `layer_paths` (api / service / data path and name patterns), `route_tokens` per language (e.g. js-ts `@Get(` `@Post(` `app.get(` `router.get(`; python `@app.route(` `@router.get(` `path(`; java `@GetMapping(`; csharp `[HttpGet`; go `HandleFunc(`; …), `requirement_item_patterns` (AC-n, FR-n, US-n, REQ-…, Gherkin `Scenario:`, checklist items under spec docs, OpenAPI `operationId`), `issue_reference_patterns` (`#123`, `KEY-123`, `fixes/closes/refs #n`, issue URLs) | FR-068 |
| 2 | Language-agnostic patterns live in one shared curated place; language-specific route tokens live in each language's curated file; the registry loader/validator accepts them and `required_fields()` is updated consistently | FR-068 |
| 3 | A repository extends any of these lists through the existing local registry layer and through `.easy-verifier.toml`; extension entries are tagged like other local data (source tag, FR-048) | FR-068 |
| 4 | Pure functions (no I/O beyond what callers pass): `layer_of(path) -> 'api'|'service'|'data'|None`, route handler finder over source text (returns line, method, path literal if any, handler name), requirement-item finder over text, issue-reference finder over commit messages | FR-068 |
| 5 | Matching happens after comments/strings are blanked where the token is code (routes), on raw text where it is prose (requirement items, commit messages) — stated in each function's docstring | FR-068 |
| 6 | No score, payload key or report changes (parity snapshot unchanged) | scope |

---

## Evaluation & Acceptance

### Success Criteria

| # | Given | Expect | How |
|---|---|---|---|
| 1 | `src/users/users.controller.ts`, `app/models/user.py`, `lib/util.js` | api, data, None | automated |
| 2 | NestJS controller text with `@Get(':id')` on a method | one route with method GET, path `:id`, handler name | automated |
| 3 | Express `router.post('/orders', create)` | one route | automated |
| 4 | Text with `AC-3`, `Scenario: pay`, `- [ ] user can …` in a spec | three items | automated |
| 5 | Commit messages `fix: x (#12)`, `PROJ-9 add y`, `chore: z` | two references | automated |
| 6 | `.easy-verifier.toml` adds layer pattern `src/domain/**` → service | `layer_of('src/domain/a.ts') == 'service'` | automated |
| 7 | Full suite | unchanged except new tests | automated |

### Verification Command

```bash
cd <worktree> && PYTHONPATH=src <repo>/.venv/bin/python -m pytest tests/test_t073_structure_patterns.py -q
```

### Evidence

> Filled by the reviewer in `tasks/TASK_REVIEW_T073.md`.

---

## Demonstration

> BEFORE captured by the Supervisor: real-repo scores in scratchpad `t073/before.txt` (develop-equivalent, before any T073 code).

---

## UI / Design Acceptance Criteria

Pure backend/rules task — no UI change. Evidence rows: ☐ N/A.

---

## Approach

**Pattern reference**: `src/easy_verifier/registry/curated/js-ts.toml` (`[[import_syntax]]`, `[[security_sinks]]` entries with citations), `src/easy_verifier/core/tokens.py` (`import_statements`, `strip`), `src/easy_verifier/core/batches.py` (`PURPOSE_CLASSES` as declared path data), `core/registry.py` local layer.

Write a short design note in `tasks/TASK_REVIEW_T073.md` under `## Design` before code (where shared patterns live, field shapes, extension path). If DDR-0011 conflicts with the registry model, STOP and report.

Environment notes for the implementer: worktrees have no .venv — `PYTHONPATH=src <main>/.venv/bin/python -m pytest`; `</dev/null` on CLI calls; the 2 container tests fail on a stale Docker image (ignore); no network installs; never write into real repo trees. Budget ~60 tool calls (the step-limit hook stops at 90); the Supervisor runs real-repo before/after and screenshots at Stage 5.

---

## Edge Case Checklist

- [ ] Decorator split over lines (`@Get(\n ':id')`)
- [ ] Route tokens inside comments/strings never match
- [ ] Windows path separators normalised
- [ ] Test files never classified into a layer
- [ ] Unknown language → no route tokens → finder returns nothing (never raises)

---

## Files to Change (Predicted)

| File | Change |
|---|---|
| `src/easy_verifier/registry/curated/*.toml` (+ a shared file if needed) | new cited fields |
| `src/easy_verifier/core/registry.py`, `core/metric_tables.py` | load/validate fields |
| new `src/easy_verifier/core/structure.py` | pure finders |
| `tests/test_t073_structure_patterns.py` | new |

## Files Must NOT Touch

| File | Reason |
|---|---|
| `core/judge.py` rules/weights/floors | T074/T075 |
| `core/report.py` | no UI change |

---

## Completion Checklist

- [ ] Design note before code
- [ ] Implementation done; tests pass; ruff clean
- [ ] Supervisor notified
