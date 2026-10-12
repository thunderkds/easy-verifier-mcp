# TASK_GUIDE — T079: Route tokens recognise the call shape, not the receiver name
**Date**: 2026-10-12 (task created 2026-10-04; guide generated with Wave 17)
**Complexity Level**: C1
**Risk Level**: Low
**Priority**: P1
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
6. Read `docs/ddr/0012-recognize-by-behaviour-and-content-not-names.md` (G3: call shape, never receiver name)

---

## Requirement (Pillar 1 — Adapt the requirement)

KANBAN (2026-10-04, after T075): *"Route tokens: generic Express-style `<any>.get('/…')` /
`.post("/…")` forms (bryony's `webapp.get('/api/...')` unmatched → requirement-fidelity below
floor)"*. DDR-0012 G3 (2026-10-12): entry detection keys on the **call shape**, never on receiver
names. T084 reuses these tokens as its api-layer signal.

Verified 2026-10-12: `registry/curated/js-ts.toml:402` lists only `app.` and `router.` receivers.
bryony registers routes as `webapp.get('/api/master/clients', function (req, res) {…})` in
`backend/server/scraper/routers/master.js` and `backend/server/dashboard/router.js`.

**Restated intent**:
> A JS/TS route registration is recognised by its shape (any receiver, an HTTP-verb method, and a
> first argument that is a string literal starting with `/`), whatever the variable is called.

**Out of scope**:
- Layer assignment (T084); request path (T085)
- Non-JS languages (their tokens are unchanged)
- Dynamically built paths (`app.get(prefix + '/x')`): not recognised, and not guessed

**Requirement Refs**:
- FR-070: routes ↔ tests (`routes_without_test_share`)
- FR-075: api layer = route registration by call shape

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [x] Restated intent confirmed (Supervisor, 2026-10-12)
- [x] Domain terms align with `PROJECT_SPEC.md` (convention pattern, route token)
- [x] Every Acceptance Criterion traces to the Requirement
- [x] FR-070 / FR-075 exist in `PRD.md`

---

## Dependencies & Reachability

**Depends on**: None

**Entry point**: `route_tokens` in `src/easy_verifier/registry/curated/js-ts.toml`, consumed by `routes_without_test_share`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | `<identifier>.get|post|put|patch|delete|all|head|options(` followed by a string or template literal starting with `/` is a route, for any identifier (`webapp`, `api`, `server`, `r`) | call shape |
| 2 | Negative: `map.get('/x')` **with no handler argument**, `cache.get('/key')`, `axios.get('/api')` and `fetch('/api')` are **not** routes. A route needs a second argument (a function, arrow, identifier, or middleware list) | precision |
| 3 | The existing NestJS decorator tokens and `app.`/`router.` forms keep matching (no regression) | no regression |
| 4 | If the token syntax (`core/registry.py`) cannot express AC 1–2, extend it minimally and document the extension in `conventions.toml` header comments. The citation stays the Express routing guide | registry stays the source of truth |
| 5 | **Real repo (paste)**: bryony's `routes_without_test_share` computes, citing `backend/server/scraper/routers/master.js:16` and similar, and requirement-fidelity is re-run. Report the before and after values. Clearing or not clearing the floor is reported honestly, not forced | real-repo verified |

---

## Evaluation & Acceptance (How we know the agent worked correctly)

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | `webapp.get('/api/x', function (req, res) {})` | route GET /api/x | automated test |
| 2 | `axios.get('/api/x')`, `cache.get('/k')` | no route | automated test |
| 3 | `@Get(':id')` in a Nest controller | still a route | automated test |
| 4 | bryony real run | routes counted, cited | pasted output |

### Verification Command (exact, runnable)

```bash
PYTHONPATH=src .venv/bin/python -m pytest -q
.venv/bin/python -m ruff check src tests
.venv/bin/easy-verifier score --repo /home/hungnguyenhuu/workspace/project/bryony/bryony --scope project > /tmp/bry.json   # run_in_background
```

### Evidence

> Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T079.md`.

---

## UI / Design Acceptance Criteria

> N/A: backend only. All three UI Evidence rows are ☐ N/A.

---

## Approach

**Pattern reference**: existing `[[route_tokens]]` entries in `registry/curated/js-ts.toml` and how
`routes_without_test_share` consumes them in `core/metrics.py`.

Prefer a data-only change (a token form for "any receiver + verb + `/` literal + second argument").
Change the token matcher only if the existing syntax cannot express it.

---

## Edge Case Checklist

- [ ] Template literal paths `` `/api/${id}` `` count; `prefix + '/x'` does not
- [ ] Multi-line calls (path on the next line)
- [ ] Commented-out routes are ignored (comment delimiters already in the registry)
- [ ] Test files' `request(app).get('/x')` (supertest) are not routes: no handler argument

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/registry/curated/js-ts.toml` | generic call-shape route token |
| `src/easy_verifier/core/registry.py` | only if the token syntax needs extending |
| `tests/test_t079_route_call_shape.py` | new |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| `RATING_RULES` in `core/judge.py` | no weight change |

---

## Test Plan

Unit tests for positive and negative call shapes (SC 1–3). Real bryony run in the background.

---

## Completion Checklist

- [ ] Implementation done
- [ ] Self-review: `Skill({ skill: "code-review" })` run
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T079.md`
- [ ] Real-repo run pasted (AC 5)
- [ ] Supervisor notified: task ready for Stage 4 review
