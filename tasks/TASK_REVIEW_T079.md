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

**AFTER** (router-module rule, 2026-10-08T03:52:03Z to 03:53:01Z, same command, worktree src): overall stays 42, but the route evidence rose:
- api `api_spec_missing`: "18 route handler(s) (backend/server/dashboard/router.js:83, :88, :107, :108, :112, and 13 more)" (BEFORE: 3)
- requirement-fidelity `routes_without_test_share` = 0.722: "13 of 18 route(s) have no test: 5 tested (matched by path literal 5, by handler name 0)" (BEFORE: 1.0, "3 of 3", 0 tested)
- find_routes per file: dashboard/router.js 5, web/router.js 3, scraper/routers/master.js 7 = 15 webapp routes + the 3 literal `app.get` ones.
- api and requirement-fidelity ratings remain 0 (other rules still fail); only the route facts changed.
- The first, same-file-only AFTER (03:43:14Z) was identical to BEFORE: bryony's `webapp` is bound cross-file, which the amendment's router-module rule now covers.

**DELTA**: routes registered on a receiver bound by a same-file `express()`/`Router()`, by a parameter of the exported function, or by a property assignment are now counted (bryony 3 -> 18 routes; routes<->tests 3 of 3 untested -> 13 of 18 untested). jQuery `$.get`, `axios.get`, `http.get` on unbound names stay 0.

**Stage 4 P1 fix**: a property assignment binds a receiver only when it reads from a parameter of the exported function or from a constructor-bound name (`var $ = window.jQuery; $.get('/x', function(){})` and `const http = Vue.http` are 0). Re-run at 2026-10-08T04:01:29Z to 04:02:19Z: still 18 routes, routes<->tests 13 of 18 untested (0.722), api_spec_missing counts 18.

**Looseness decision**: rule (2) alone would admit `const http = this.http; http.get('/x', cfg)`. Names bound by (1)/(2) ("weak") therefore count only for a call with a `/` path literal and either a function/arrow handler as last argument or 3+ arguments (middleware chain). An identifier handler with two arguments is not a route. Cost: `webapp.get('/x', handler)` in a router module with a bare identifier handler and no middleware is missed. Constructor-bound names keep the original rule.

**WITNESS**: [who ran it and when — derived from `memory/event-trace/Txxx.jsonl`, never the
implementing agent alone]
