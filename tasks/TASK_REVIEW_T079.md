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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☐ pass / ☐ fail | [test file path(s) — required before Done] |
| Verification command run | ☐ pass / ☐ fail | [paste actual output] |
| Negative cases hold | ☐ pass / ☐ fail | |
| verify | ☐ pass / ☐ fail / ☐ N/A | [what was observed — must literally state "pass" or "fail" here too, e.g. "skill run, feature confirmed working — pass": the merge gate scans this Notes column for the word "pass", not just the Result column] |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☐ pass / ☐ fail | [what was reviewed vs. skipped, and why] |
| Full smoke suite still green (no regression) | ☐ pass / ☐ fail | |
| **UI: Visual regression (diff or verdict pasted)** | ☐ pass / ☐ fail / ☐ N/A | [screenshot path or LLM verdict — required for UI tasks, Hard-Stop Gate 6] |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☐ pass / ☐ fail / ☐ N/A | [method used + output] |
| **UI: Responsiveness at target viewports** | ☐ pass / ☐ fail / ☐ N/A | [viewports tested, any overflow findings] |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE** (2026-10-08T03:42:23Z to 03:43:14Z, pristine `git archive HEAD` of c50955f as `PYTHONPATH`, no implementation commit existed):
`easy_verifier.adapters.cli score --repo /home/hungnguyenhuu/workspace/project/bryony/bryony --scope project --all </dev/null` (the guide's `--batches all` is not a valid flag; `--all` is the form)
- overall 42 (10 of 13 dimensions); `api` 0, `requirement-fidelity` 0
- requirement-fidelity `routes_without_test_share` = 1.0: "3 of 3 route(s) have no test ... backend/scripts/companies/special-character/app/main.js:15 GET /, :21 GET /fetch, :37 GET /submit" (all literal `app.get(`; none of bryony's `webapp.*` routes)
- api `api_spec_missing`: "3 route handler(s) (backend/scripts/companies/special-character/app/main.js:15, :21, :37)"

**AFTER** (2026-10-08T03:43:14Z to 03:44:11Z, worktree src with the change): identical to BEFORE. overall 42, api 0, requirement-fidelity 0, still "3 of 3 route(s)". Unit-level: `webapp = express(); webapp.get('/api/x', handler)` -> `Route(GET, /api/x, handler)`; `$.get`/`axios.get`/`map.get` -> no route (tests/test_t079_express_receivers.py, 17 passed).

**DELTA**: a JS/TS file that binds a variable to `express()` / `express.Router()` / `Router()` (including `var a = self.a = express()`) now has `<var>.get('/…', …)` counted as a route; bryony's score is unchanged because its `webapp` is bound in another file (see KNOWN LIMIT).

**KNOWN LIMIT (AC 6 not met)**: bryony's 12+ `webapp.*` routes are not in `backend/server/dashboard/index.js` (which only does `var webapp = self.webapp = express(); webapp.use(...)`) but in `backend/server/dashboard/router.js`, `web/router.js` and `scraper/routers/master.js`. There `webapp` is `let webapp = app.webapp`, `var webapp = app.app`, or a parameter `function (app, webapp)`: cross-file bindings, which the guide puts out of scope. The same-file rule therefore finds 0 of them.

**WITNESS**: [who ran it and when — derived from `memory/event-trace/Txxx.jsonl`, never the
implementing agent alone]
