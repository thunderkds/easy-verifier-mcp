# TASK_REVIEW — T079: Express routes on any app/router variable

> Sibling of `tasks/TASK_GUIDE_T079.md`. Everything here is **filled by the reviewer at Stage
> 4/5** — it is deliberately NOT in the guide, because the implementing agent re-reads the guide on
> every turn and never fills these two sections.
>
> Consumers resolve each section **guide first, this file second** (`.claude/hooks/lib/guide_sections.py`):
> a legacy guide that still carries these sections inline keeps working unchanged, and a stray
> review file can never override an inline section.

---

## Evidence

| Check | Result | Notes / output snippet |
|-------|--------|------------------------|
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t079_express_receivers.py` (red-first; same-file binding, chained binding, `express.Router()`/`Router()`/`new Router()`, router-module params, property-from-param, zero cases `$.get`/`axios.get`/`http.get`/`window.jQuery`/`Vue.http`/non-exported helper/one-argument). Supervisor re-run 2026-10-08 with T073: `80 passed, 2306 deselected in 2.30s` |
| Verification command run | ☑ pass | `ruff check src tests` → `All checks passed!`; full suite (implementer, after P1 fix): `2382 passed, 2 skipped, 2 failed` — the 2 known stale-Docker container tests |
| Negative cases hold | ☑ pass | Supervisor probe on d37a6f7: `var $ = window.jQuery; $.get('/api/x', function…)` → [], `const http = Vue.http; http.get('/api/users', (res)=>…)` → [], jQuery inside a router module → []; `module.exports = function (app) { var webapp = app.app; webapp.get('/api/c', function…) }` → [GET /api/c] |
| verify | ☑ pass | Supervisor 2026-10-08: `find_routes` over every tracked node-monorepo `.js` file → 18 routes, only in `dashboard/router.js` 5, `scraper/routers/master.js` 7, `web/router.js` 3, `special-character/app/main.js` 3 — no hit in jQuery client files; implementer `score --scope project --all </dev/null`: api 3→18 route handlers, requirement-fidelity routes_without_test_share 1.0 (0/3 tested) → 0.722 (5/18 tested), overall 42 unchanged (other rules still fail) — pass |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | reviewed `core/structure.py` (`find_routes`, `_bound_tokens`, `_weak_names`, `_router_call`), `core/registry.py` route_tokens validator, `registry/curated/js-ts.toml` 2 rows, test file. Findings: **P1** (fixed in 9edd3c6) RECEIVER_ASSIGN bound any `x = a.b`, so browser `$ = window.jQuery; $.get('/x', cb)` counted as a route; **P3** (fixed) stray blank-line deletion in `class Registry`, docstring missing RECEIVER_PARAM/ASSIGN. P2 noted: per-file token tuples vary, so `_route_patterns` lru_cache (64) recompiles per file — node-monorepo project run time unchanged (~50–58 s), not acted on. Security: no new input surface; tokens are curated registry data; route regexes built with `token_regex` (escaped) — clean |
| Full smoke suite still green (no regression) | ☑ pass | `2382 passed, 2 skipped, 2 failed` (container tests `test_container_parity_is_explicitly_verified`, `test_container_redaction_proof_is_not_silent_when_docker_is_missing`; stale image, pre-existing) — pass |
| **UI: Visual regression (diff or verdict pasted)** | ☐ N/A | backend-only |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☐ N/A | backend-only |
| **UI: Responsiveness at target viewports** | ☐ N/A | backend-only |
| Repro loop | ☐ N/A | feature task, not a bugfix |
| Regression test | ☑ pass | existing `app.get`/`router.get`/NestJS tests in T073 suite unchanged and green |
| Smoke suite | ☑ pass | node-monorepo real-repo run (verify row) |
---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE** (2026-10-08T03:42:23Z to 03:43:14Z, pristine `git archive HEAD` of c50955f as `PYTHONPATH`, no implementation commit existed):
`easy_verifier.adapters.cli score --repo <real-repos>/node-monorepo --scope project --all </dev/null` (the guide's `--batches all` is not a valid flag; `--all` is the form)
- overall 42 (10 of 13 dimensions); `api` 0, `requirement-fidelity` 0
- requirement-fidelity `routes_without_test_share` = 1.0: "3 of 3 route(s) have no test ... backend/scripts/companies/special-character/app/main.js:15 GET /, :21 GET /fetch, :37 GET /submit" (all literal `app.get(`; none of node-monorepo's `webapp.*` routes)
- api `api_spec_missing`: "3 route handler(s) (backend/scripts/companies/special-character/app/main.js:15, :21, :37)"

**AFTER** (router-module rule, 2026-10-08T03:52:03Z to 03:53:01Z, same command, worktree src): overall stays 42, but the route evidence rose:
- api `api_spec_missing`: "18 route handler(s) (backend/server/dashboard/router.js:83, :88, :107, :108, :112, and 13 more)" (BEFORE: 3)
- requirement-fidelity `routes_without_test_share` = 0.722: "13 of 18 route(s) have no test: 5 tested (matched by path literal 5, by handler name 0)" (BEFORE: 1.0, "3 of 3", 0 tested)
- find_routes per file: dashboard/router.js 5, web/router.js 3, scraper/routers/master.js 7 = 15 webapp routes + the 3 literal `app.get` ones.
- api and requirement-fidelity ratings remain 0 (other rules still fail); only the route facts changed.
- The first, same-file-only AFTER (03:43:14Z) was identical to BEFORE: node-monorepo's `webapp` is bound cross-file, which the amendment's router-module rule now covers.

**DELTA**: routes registered on a receiver bound by a same-file `express()`/`Router()`, by a parameter of the exported function, or by a property assignment are now counted (node-monorepo 3 -> 18 routes; routes<->tests 3 of 3 untested -> 13 of 18 untested). jQuery `$.get`, `axios.get`, `http.get` on unbound names stay 0.

**Stage 4 P1 fix**: a property assignment binds a receiver only when it reads from a parameter of the exported function or from a constructor-bound name (`var $ = window.jQuery; $.get('/x', function(){})` and `const http = Vue.http` are 0). Re-run at 2026-10-08T04:01:29Z to 04:02:19Z: still 18 routes, routes<->tests 13 of 18 untested (0.722), api_spec_missing counts 18.

**Looseness decision**: rule (2) alone would admit `const http = this.http; http.get('/x', cfg)`. Names bound by (1)/(2) ("weak") therefore count only for a call with a `/` path literal and either a function/arrow handler as last argument or 3+ arguments (middleware chain). An identifier handler with two arguments is not a route. Cost: `webapp.get('/x', handler)` in a router module with a bare identifier handler and no middleware is missed. Constructor-bound names keep the original rule.

**WITNESS**: Supervisor, 2026-10-08 — independently probed the false-route cases on d37a6f7 and scanned every node-monorepo `.js` file (18 routes); trace attributed via active_task (`memory/event-trace/T079.jsonl`).