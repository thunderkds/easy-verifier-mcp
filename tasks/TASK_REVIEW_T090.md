# TASK_REVIEW — T090: Report each route's request path (unweighted)

> Sibling of `tasks/TASK_GUIDE_T090.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | pass | tests/test_t090_request_paths.py (10 tests: SC1 Express path `GET /users: server/r.js:4 -> lib/svc.js:1 -> lib/store.js:4 (return User.find({});)`; SC2 none; direct; cycle plus two routes in one file; cap 20 disclosed; no-route abstains; wording; AC4 ratings, overall, improvement_plan, areas equal metric on vs off; AC3 report folded list; prefix-edge disclosure). `10 passed` |
| Verification command run | pass | Full suite: `2 failed, 2705 passed, 2 skipped in 404.11s`; the 2 failures are the known stale-image container tests (test_container_parity_is_explicitly_verified, test_container_redaction_proof_is_not_silent_when_docker_is_missing). `ruff check src tests`: All checks passed! |
| Negative cases hold | pass | no route -> abstention not 0; route reaching no data -> listed under none; import cycle terminates; 24 routes -> 20 listed with cap text; derivation holds no 'violation', 'bad' or 'should' |
| verify | ☐ pass / ☐ fail / ☐ N/A | [what was observed — must literally state "pass" or "fail" here too, e.g. "skill run, feature confirmed working — pass": the merge gate scans this Notes column for the word "pass", not just the Result column] |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☐ pass / ☐ fail | [what was reviewed vs. skipped, and why] |
| Full smoke suite still green (no regression) | ☐ pass / ☐ fail | |
| **UI: Visual regression (diff or verdict pasted)** | N/A | [screenshot path or LLM verdict — required for UI tasks, Hard-Stop Gate 6] |
| **UI: Design-system compliance (tokens/colors/typography verified)** | N/A | [method used + output] |
| **UI: Responsiveness at target viewports** | N/A | [viewports tested, any overflow findings] |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE** (captured from a `git archive HEAD` copy of the pre-change src, before any implementation commit; `score --repo <r> --scope project < /dev/null`, then `grep -c request_paths`):

```
bryony       2026-10-13T05:03:55Z -> 2026-10-13T05:04:23Z  json 2255526 bytes  grep -c request_paths -> 0
kitchd       2026-10-13T05:04:23Z -> 2026-10-13T05:04:34Z  json 1711923 bytes  grep -c request_paths -> 0
bryony --all 2026-10-13T05:04:34Z -> 2026-10-13T05:05:29Z  json 8159847 bytes  grep -c request_paths -> 0
```

**AFTER** (same commands on the T090 worktree, final commit; run 2026-10-13T05:32:26Z to 05:34:09Z): every dimension pack carries `request_paths` (13 each); the architecture one:

- kitchd: `57 route(s) found in 17 file(s): 43 reach a DB/ORM call in their own file, 13 through at least one other in-repo module, 1 reach none ... the first 20 of 57 routes are listed (cap)`
- bryony --all: `18 route(s) found in 4 file(s): 0 reach a DB/ORM call in their own file, 5 through at least one other in-repo module, 13 reach none ...; 2 dynamic import(s) with a literal directory prefix link every file directly in that directory, so a path through one names the first such file, not necessarily the one called`
- bryony default (batch 1 of 6): abstains, "no source file quoted here registers a route" (its routers are in later batches).

AC 5 hand-checked paths (each line opened in the repo):
- kitchd `POST login: apps/api/src/auth/auth.controller.ts:16 -> apps/api/src/auth/auth.service.ts:35 (const existing = await this.prisma.user.findUnique({)`: controller line 16 is `@Post('login')`, imports `./auth.service`; service line 35 is the `this.prisma.user.findUnique(` call.
- kitchd `GET (path is not a literal): apps/api/src/announcements/announcements.controller.ts:44 -> DB/ORM call at line 37`: line 44 is `@Get()`; line 37 in the same controller is `await this.prisma.user.findUnique(` (direct).
- kitchd `POST invite: users.controller.ts:26 -> auth/guards/roles.guard.ts:48`: line 26 `@Post('invite')`, `@UseGuards(JwtAuthGuard, RolesGuard)`, guard imported at line 14, `this.prisma.user.findUnique` at guard line 48. users.service.ts is also one hop away; the tie goes to the first path alphabetically (noted).
- bryony `GET /api/health-check: backend/server/dashboard/router.js:83 -> controller-manager.js:35 -> controllers/save-searches.js:14 -> server/job/report-searches.js:21 -> platform/db/services/dashboard-search.js:14 -> platform/db/base-mongodb-service.js:21 (mongooseConnectionManager.connect(...))`: router.js:83 is `webapp.get('/api/health-check'`; controller-manager.js:35 is `require('./controllers/' + name)` (dynamic prefix edge, so the next hop names the first file in the directory); save-searches.js:14 requires `../../job/report-searches`; report-searches.js:21 requires `dashboard-search`; dashboard-search.js:14 requires `../base-mongodb-service`; base-mongodb-service.js:21 is the connect call.
- bryony `GET /api/master/accounts/refresh: backend/server/scraper/routers/master.js:16 -> reaches no file that calls a DB/ORM API`: line 16 is the route; the file's only requires are async, url, underscore (no in-repo module).
- bryony `GET /api/companies: backend/server/web/router.js:18 -> reaches none`: line 18 is the route; requires are async, http, ../../utils/logger (no onward data call), underscore.

AC 4 on real repos (`cmp` of the extracted JSON sections, before vs after): ratings, overall, improvement_plan, areas_measured, areas_without_rule, warnings are byte-equal for bryony, kitchd and bryony --all (`cmp-ratings-<repo>-equal` for all three).

**DELTA**: for each recognised route the output now shows the in-repo file:line path from its handler to the first DB/ORM call (or that none is reached), counted and capped at 20, without moving any rating.

**WITNESS**: [who ran it and when — derived from `memory/event-trace/Txxx.jsonl`, never the
implementing agent alone]
