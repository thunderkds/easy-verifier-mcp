# TASK_REVIEW — T114: Project-scope blast-radius

> Sibling of `tasks/TASK_GUIDE_T114.md`. Everything here is **filled by the reviewer at Stage
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

### AC7 pre-registered expectations (written 2026-10-17 before the AFTER runs, commit `8cbd2f1`)

Rules: `high_reach_files_without_test_share` <= 0.20, `high_reach_churn_hotspot_share` <= 0.30,
weights 50/50 (one scope group; the four change rules are not evaluated at project scope).

| Repo | Expected blast-radius | Expected values | Expected overall direction |
|---|---|---|---|
| node-api | rates | test share high (>= 0.50, fails: few tests); churn share 0.2-0.6 | down (a low blast-radius joins the average; baseline 62) |
| node-monorepo | rates (or abstains: no fan-in >= 3 if most files share `index.js`/same-stem names) | test share high (fails); churn share any | down or unchanged (baseline 53) |
| fullstack-ts | rates | test share 0.3-0.8; churn share any | small move (baseline 58) |
| nest-api | rates | test share <= 0.5 (nest spec files by name); churn: abstains if < 20 commits | small move (baseline 81) |
| python-ml | rates or abstains (stated reason: no file imported by >= 3, or churn unavailable) | test share high (few tests) | down or unchanged (baseline 65) |

Pass criteria: every repo rates or abstains with a stated reason; each listed top-5 file's fan-in is
plausible on a manual grep of its importers; no narrow-scope payload change (AC6); project payload
growth <= 10 % vs develop on node-api and node-monorepo.

### Changed test expectations (step 2, Supervisor-accepted scope groups + 50/50)

First full suite on `8cbd2f1`: 27 failed, 3138 passed, 3 skipped, 3 errors, exit 1. Env-known: T014
`test_module_import_emits_nothing_to_stdout` + 3 T101 HTTP errors. The 26 regressions, by cause:

| Test | Change | Reason |
|---|---|---|
| `test_judge.py` (`_numeric_metrics`, `_rating_with_value`, threshold test x6, 5 overall/serialization tests) | fixtures build one scope group's metrics (`_held`: the group of the rule under test, else the change group) | a real blast-radius pack lists one group; each group sums to 100, so a single passing rule still earns exactly its weight (assertion unchanged) |
| `test_metrics.py` (`_CORE_METRICS`, whole-set truncation test; 4 tests) | subtract / exclude `SCOPE_METRICS` like `PACK_METRICS` | the high-reach metrics are listed only by the project blast-radius pack that computed them (that is what keeps narrow payloads byte-equal) |
| `test_t035_cited_rules.py` (approved table, weights, README table) | 2 approved rows added; weights checked per scope group; README rows added | new rules; each group is a rating's whole rule set |
| `test_t055` `test_signed_off_weights_thresholds_and_areas[blast-radius]` | 2 signed-off rows; per-group sum | same |
| `test_t052` project-scope churn share; `test_t055` project compat abstention | expect `NOT_THIS_SCOPE` at project scope (worktree case unchanged) | at project scope the change rules are not evaluated (mirrors T110 `NOT_THIS_KIND`) |
| `test_t055` `test_unused_facts_leave_the_pack_json_byte_identical` | project blast-radius pack adds `whole_file` (+ `code_index_files` when files are cited); narrow pack still has none | the project pack now carries its high-reach results |
| `test_t068` under-cap snapshot | regenerated; only the 6 blast-radius metrics differ, every rating and overall (61) unchanged | as above |
| `test_t069` blast-radius project summary line | new `_CHANGES_ONLY` text | the old text said blast-radius is measured only on a change, which is no longer true |
| `test_t071` backticked identifiers | the 6 blast-radius rule names declared in `DECLARED` | the guide's scope bullet now names both rule groups |
| `test_t072` area 5 row | `docs/AREA_COVERAGE.md` row lists the 2 new rules | doc must equal the rule table |

Docs also updated: `README.md` rating table, `docs/EVALUATION_GUIDE.md` scope bullet,
`docs/SCORING_RULES.md` blast-radius rows, `docs/AREA_COVERAGE.md` area 5.

### AC6 — narrow-scope payloads byte-equal to develop (this repo, 2026-10-17)

`ac6.sh`: develop tree (`eae4175`, `git archive`) vs branch, `blast-radius` pack and whole `score`
payload, against this worktree:

| Scope | blast-radius pack sha256 (dev = branch) | bytes | score payload sha256 (dev = branch) |
|---|---|---|---|
| changes `eae4175..8cbd2f1` | `0bb88e215f8d404820f8e11e8a6f52c209646e1e973a62a0080ef4bb785686f8` | 85,460 | `e227f54545bde74dff5dfe9223a00bb5922f0948aec9fc74d54bda45f0b5db2b` |
| worktree | `850602b3541e8da8cc09a104d5f3c23f487129de0b858e4e469edb6077ad757c` | 2,356 | `40c062df7bd0cfe3c5cd23ecac113364944b52a1365b790e4996c02720e8b389` |
| task T113 | `438a73183ceeb4f70f9c9d84e385ce2da21d5b296cd35d0026c94f8f6741512e` | 20,478 | `af89692a89e93720ca57af29b0a21a6adf8a234acdaef5d3518a53a0ec654075` |

All six pairs identical — pass.

Full suite on `bfa0a3a`+t071 fix: 1 failed, 3184 passed, 3 skipped, 3 errors, exit 1 — only the
4 known env failures (T014 stdout import, 3 T101 HTTP) — pass.

### AC7 — real repos (AFTER on `5ac6cfc`, 2026-10-17T09:35-09:37Z, `score --scope project`)

A first AFTER pass on `bfa0a3a` was spot-checked and failed the pre-registered "fan-in plausible"
criterion: the whole-word name matcher counted directory segments and hyphenated pieces as edges
(fullstack-ts `apps/web/src/routes/auth.ts` fan-in 65 from every `./auth/...` path; node-api
`src/payment/gateway/dtos/index.ts` 62 from every `../dtos/x.dto`; node-monorepo `utils/service.js`
65 counting `base-mongodb-service`), and a web file was "covered" by an API e2e spec through the
keyword `const`. Fixed in `5ac6cfc` (deviation, see below): a statement names a file only by the last
segment of a path specifier / dotted module name; a symbol-covering test must be in the source's
project (T112's `_project`); declaration keywords are never symbols.

| Repo | blast-radius | test share (<= 0.20) | churn share (<= 0.30) | overall | payload bytes |
|---|---|---|---|---|---|
| node-api | 50 | 0.26 fail (13 of 50) | 0.14 pass (7 of 50) | 62 -> 60 | 1,894,820 -> 1,899,449 (+0.24 %) |
| node-monorepo | 50 | 1.00 fail (26 of 26) | 0.00 pass | 53 -> 53 | 1,989,346 -> 1,991,718 (+0.12 %) |
| fullstack-ts | 50 | 0.50 fail (11 of 22) | 0.09 pass (2 of 22) | 58 -> 57 | 1,752,617 -> 1,755,928 |
| nest-api | 100 | 0.20 pass (2 of 10) | 0.00 pass | 81 -> 83 | 1,387,577 -> 1,385,217 |
| python-ml | 100 | 0.15 pass (2 of 13) | 0.23 pass (3 of 13) | 65 -> 69 | 1,388,972 -> 1,386,948 |

Top-5 high-reach files (path, fan-in, churn, coverage):
- node-api: `src/helpers/error.helper.ts` 53/0 name; `src/core/constants/app.constant.ts` 26/4 symbol;
  `src/auth/interfaces/validated-user-info.interface.ts` 25/0 symbol; `src/commons/enums/user.enum.ts`
  25/1 symbol; `src/helpers/string.helpers.ts` 21/3 name.
- node-monorepo: `backend/utils/configs.js` 61/0; `backend/utils/logger.js` 61/0;
  `backend/platform/db/base-mongodb-service.js` 54/0; `backend/utils/rest-controller-base.js` 42/0;
  `backend/platform/db/index.js` 18/4 — all no covering test.
- fullstack-ts: `apps/api/src/prisma/prisma.service.ts` 33/1 symbol; `apps/web/src/routes/auth.ts`
  33/4 hotspot, none; `apps/api/src/auth/guards/jwt-auth.guard.ts` 16/1 name;
  `apps/web/src/errorDialog/ErrorDialogProvider.tsx` 16/1 name; `apps/api/src/prisma/prisma.module.ts`
  15/1 none.
- nest-api: `src/common/constants/message.constant.ts` 17; `src/common/dto/pagination.dto.ts` 13;
  `src/common/enums/user.enum.ts` 12; `src/common/constants/error-code.constant.ts` 10;
  `src/modules/user/entities/user.entity.ts` 10 — all churn 0, all symbol-covered.
- python-ml: `src/core/config/settings.py` 22/16 hotspot, name; `src/core/llm/metrics.py` 10/5
  symbol; `src/core/llm/factory.py` 7/9 hotspot, symbol; `src/core/subgraphs/wrapper.py` 6/1 symbol;
  `src/core/llm/payload.py` 5/1 symbol.

Manual checks: fullstack-ts `routes/auth.ts`: `grep` finds 33 non-test files importing `.../auth`,
all under `apps/web`; that is exactly 33. node-monorepo `utils/configs.js`: 77 non-test files require
`.../configs`, 24+ of them under `backend/scripts/` (tooling purpose class, not counted), which fits
61. Against the pre-registered expectations: all 5 rate (none abstains). node-api's test share
(0.26) came in under the expected >= 0.50; nest-api's churn did not abstain (102 commits); the
python-ml test share is low (0.15) rather than high. Overall moves: -2, 0, -1, +2, +4. Payload growth
is <= 0.24 %, under the 10 % limit — pass.

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE**: captured on `feat/T114-project-blast-radius` at `eae4175` (develop with T113 merged, no
T114 code), by `score --scope project < /dev/null` (CLI, `PYTHONPATH=src`, py3.12):

```
$ date -u   # 2026-10-17T08:39:31Z
$ easy-verifier score --repo <real-repos>/node-api --scope project < /dev/null
blast-radius: {"kind": "rating_abstention", "reason_code": "all_metrics_abstained",
  "reason": "all declared rating metrics abstained", "achieved_coverage": 0.5,
  "unavailable_metrics": [["max_fan_in_changed", "no import statement was found in this pack's
  code-file excerpts, so there is no import graph to measure; ..."],
  ["changed_files_in_churn_hotspots_share", "... only the blast-radius pack at changes, worktree
  or task scope gathers them ..."], ["public_symbols_removed", "this pack is at 'project' scope,
  which carries no diff; ..."], ["destructive_migration_ops", "... 'project' scope ..."]]}
overall: 62   (payload 1,894,820 bytes)

$ date -u   # 2026-10-17T08:42:10Z
$ easy-verifier score --repo <scratchpad>/synth --scope project < /dev/null
  # synthetic repo, known import graph: src/core.ts and src/util.ts each imported by
  # alpha/beta/gamma/delta (fan-in 4), src/helper.ts by delta (fan-in 1), tests/core.test.ts
  # imports core; 26 commits, util.ts touched by 25 of them
blast-radius: rating_abstention all_metrics_abstained "all declared rating metrics abstained"
  unavailable: max_fan_in_changed, changed_files_in_churn_hotspots_share,
  public_symbols_removed, destructive_migration_ops
overall: 75 (1 contributor: test-strategy)
```

Baseline on the other AC7 repos (same commit, 2026-10-17T08:39-08:41Z), blast-radius
abstained (`all_metrics_abstained`) on each: payload bytes node-monorepo 1,989,346, fullstack-ts
1,752,617, nest-api 1,387,577, python-ml 1,388,972; overall node-monorepo 53, fullstack-ts 58,
nest-api 81, python-ml 65.

**AFTER**: same command on `5ac6cfc` (2026-10-17T09:35:21Z), node-api:

```
blast-radius: {"kind": "rating", "value": 50, "inputs": [
  high_reach_files_without_test_share 0.26 (13 of 50 high-reach files untested) -> fail (<= 0.20),
  high_reach_churn_hotspot_share 0.14 (7 of 50 in the top 10 % by churn) -> pass (<= 0.30)],
  "unavailable_metrics": []}
  table: src/helpers/error.helper.ts | fan-in 53 | churn 0 | tested by src/helpers/error.helper.spec.ts (name)
         src/core/constants/app.constant.ts | fan-in 26 | churn 4 | tested by src/auth/auth.service.spec.ts (symbol DEFAULT_REGULAR_USER_AMOUNT) ...
overall: 62 -> 60   (payload 1,894,820 -> 1,899,449 bytes)
```
Synthetic repo: blast-radius 0 (src/core.ts and src/util.ts fan-in 4; util untested and the churn
hotspot: both shares 0.5); overall 75 -> 38.

**DELTA**: at project scope blast-radius now rates the repository's most-imported files (untested share, churn-hotspot share) with the cited files' fan-in and churn, where before it always abstained.

**WITNESS**: [who ran it and when — derived from `memory/event-trace/Txxx.jsonl`, never the
implementing agent alone]
