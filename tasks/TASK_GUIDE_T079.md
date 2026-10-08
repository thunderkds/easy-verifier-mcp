# TASK_GUIDE — T079: Express route handlers on any app/router variable name (`webapp.get('/…')`)
**Date**: 2026-10-08
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
6. Read `memory/codebase-map.md`
7. Read `docs/ddr/0011-code-derived-rules-and-flexible-conventions.md` (code-derived rules; conventions are extendable pattern lists — "flexible, not stick on a solution")

---

## Requirement (Pillar 1 — Adapt the requirement)

Express route tokens in `registry/curated/js-ts.toml` are literal receiver names (`app.get(`, `router.get(`). Real code names its Express app anything: bryony declares `var webapp = self.webapp = express();` (`backend/server/dashboard/index.js`) and registers 12 routes as `webapp.get('/api/…', …)`. None are found, so `requirement-fidelity` (routes↔tests) falls below its floor on bryony and the `api` dimension misses its routes (learnings 2026-10-07 T044: with T079-style tokens + `--batches all`, 15 routes are found).

**Restated intent**:
> A JS/TS call `<name>.<method>('/…', …)` counts as a route handler when `<name>` is bound **in the same file** to an Express application or router (`express()`, `express.Router()`, `Router()`, including chained assignments like `var webapp = self.webapp = express()`), in addition to today's literal `app.`/`router.` tokens. Receivers not bound that way are not routes.

**Why not a bare wildcard receiver** (Supervisor, measured 2026-10-08): bryony also has `$.get('/…')` (jQuery, 4 hits) — an HTTP *client* call. `axios.get('/api', cfg)`, `http.get(...)`, `map.get('/k')` have the same shape. A wildcard would count client calls as routes. Binding the receiver to `express()`/`Router()` keeps it to server routes without a deny-list.

**Amendment (user, AskUserQuestion 2026-10-08 — "Router-module rule"):** the same-file rule found 0 of bryony's routes — they live in `dashboard/router.js`, `web/router.js`, `scraper/routers/master.js`, where the receiver is a **parameter of an exported function** (`module.exports = function (app, webapp)`) or **assigned from a property** (`let webapp = app.webapp`, `var webapp = app.app`). These now also bind a receiver, when the name is called as `<name>.<method>('/path', handler)` (path literal starting `/`, ≥2 arguments). jQuery `$.get` and other unbound names still do not count.

**Out of scope**:
- Full cross-file data-flow tracking (resolving imports). The router-module rule above is a per-file approximation.
- Other frameworks (Koa/Fastify/Hapi) — separate rows if ever needed.
- Changing `find_routes` semantics for other languages.

**Requirement Refs**:
- FR-067…FR-071 (DDR-0011 code-derived rules; route evidence)

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [x] Restated intent confirmed to match the user's request (Supervisor 2026-10-08; Kanban row T079, user approved parallel run 2026-10-08)
- [x] Domain terms align with `PROJECT_SPEC.md` glossary
- [x] Every Acceptance Criterion below traces to a line in the Requirement
- [x] All Requirement Refs exist in `PRD.md`

---

## Dependencies & Reachability

**Depends on**: T073 (`core/structure.py:find_routes`, route_tokens), T075 (routes↔tests)

**Entry point**: `find_routes`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | `const webapp = express(); webapp.get('/api/x', handler)` → one route `GET /api/x`, handler `handler` | bound receiver |
| 2 | Chained binding `var webapp = self.webapp = express();` and `const r = express.Router()` / `const r = Router()` are recognised | bryony shape |
| 3 | `$.get('/api/x', cb)`, `axios.get('/api/x', cfg)`, `map.get('/k', v)` with no Express binding in the file → **no** route | no client calls |
| 4 | Existing `app.get(`/`router.get(` and NestJS decorator behaviour unchanged (existing T073/T075 tests green) | no regression |
| 5 | The receiver rule is data, not a hard-coded name list in Python: the binding constructors (`express()`, `express.Router()`, `Router()`) live in a cited registry/conventions field with `citation_url` (Express routing docs), consistent with DDR-0011 extendable lists | flexible conventions |
| 7 | Router-module rule (amendment): exported-function parameters and `= <param>.<prop>` assignments bind receivers; `$.get`, `axios.get`, `http.get` on unbound names still 0; a parameter only used as `x.get(name)` (one argument) still 0 | amendment |
| 6 | Real repo: bryony `requirement-fidelity` and `api` now find bryony's `webapp.*` routes (before/after counts pasted) | real-repo verified |

---

## Evaluation & Acceptance (How we know the agent worked correctly)

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | fixture file with `webapp = express()` + 2 routes | 2 routes | automated test |
| 2 | fixture with only `$.get('/x', cb)` | 0 routes | automated test |
| 3 | bryony `score --scope project --batches all </dev/null` | api / requirement-fidelity route counts rise vs BEFORE | real-repo run (background) |

### Verification Command (exact, runnable)

```bash
python -m pytest -q
python -m ruff check src tests
```

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T079.md`.

---

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T079.md`.

BEFORE command (run before any code change, paste timestamped output):
`easy-verifier score --repo /home/hungnguyenhuu/workspace/project/bryony/bryony --scope project --batches all </dev/null` → record `api` and `requirement-fidelity` ratings/abstentions and the route count from their derivations. Run it with `run_in_background` (project scope takes minutes).

---

## UI / Design Acceptance Criteria

> N/A — pure backend task (no UI component). All three UI Evidence rows are ☐ N/A.

---

## Approach

**Pattern reference**: `core/structure.py:find_routes` + `_route_patterns`; `registry/curated/js-ts.toml` `[[route_tokens]]` (Express row, line ~402).

Smallest change: per file, find identifiers bound to an Express constructor (registry-listed), and add `<METHOD>=<ident>.<method>(` tokens for them before matching — reusing the existing call-token path (handler = last positional identifier, one-argument guard). Keep the literal `app.`/`router.` rows.

---

## Edge Case Checklist

- [ ] Chained assignment `var a = self.a = express();`
- [ ] Binding inside a comment or string must not count (match on stripped code)
- [ ] `app.get('setting')` one-argument guard still applies to new receivers
- [ ] Receiver name containing `$` or `_`
- [ ] Same file has both `express()` app and jQuery `$` → only the app's calls count

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/core/structure.py` | receiver binding detection feeding route tokens |
| `src/easy_verifier/registry/curated/js-ts.toml` | cited constructor list (or conventions.toml if that's where it fits) |
| `tests/test_t073_*.py` or new `tests/test_t079_express_receivers.py` | tests |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| `src/easy_verifier/dimensions/api.py` `_breaking_metric` | T084 follow-up, separate |
| `.easy-verifier.toml` / repo-local conventions loading | T078 (runs after this task) |
| `src/easy_verifier/packs/*`, `registry/packs/*` | T049 runs in parallel |

---

## Test Plan

Unit tests on `find_routes` with JS/TS fixtures for AC 1–4; one score-level test that a repo with `webapp = express()` routes and matching tests gets routes↔tests evidence.

---

## Completion Checklist

- [ ] Implementation done
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T079.md`'s Evidence table (Hard-Stop Gate 5)
- [ ] Real-repo BEFORE/AFTER on bryony pasted in Demonstration
- [ ] Supervisor notified: task ready for Stage 4 review
