# TASK_REVIEW — T113: One full code scan per run

> Sibling of `tasks/TASK_GUIDE_T113.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t113_code_index.py` (AC1–AC6, cycle-root regression, bounded citations, warning wording); 6 fail on develop. Supervisor re-run 2026-10-17: t113 + t068 + t112 + t100 → `117 passed in 105.13s`, exit 0 |
| Verification command run | ☑ pass | as above; `ruff check src tests` passed (agent) |
| Negative cases hold | ☑ pass | over-cap repo discloses `capped index/code` and replays byte-equal; secret files never indexed (T029/T100 green); root config file no longer hides an import cycle |
| verify | ☑ pass | Real CLI `score --scope project` on 5 real repos, develop → branch: node-api test-strategy abstain→75, architecture 10→10, overall 60→62; node-monorepo reliability 61→22 (Supervisor spot-checked `backend/scripts/companies/linkedin/queue/utils.js:330` `catch (e) {}` and `dashboard-user.js:506` `http.request` without timeout — real), overall 59→53; fullstack-ts test-strategy abstain→75, 56→58; python-ml abstain→75, 64→65; nest-api abstain→75, 81→81 (last 3 re-run by Supervisor on the final commit). All other dimensions unchanged; no index cap hit — pass |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Reviewed core/index.py, context `_load` index path, metrics/_code_extract index metrics + MAX_LISTED_PATHS, score `capped`, test_strategy wording. Index reads go through `peek_source` (containment, secret refusal, UTF-8) — no new walker. AC5: payload bytes shrank on every repo (this repo −1.7 %, node-monorepo −12.2 %, node-api −7.7 %, fullstack-ts −6.1 %, python-ml −5.5 %, nest-api −4.6 %). P2: node-monorepo run time 31.5 s → 62.3 s (≈2×, AC8 reported, not optimised). Accepted deviations: sink_hits stays evidence-local; guide alias fix |
| Full smoke suite still green (no regression) | ☑ pass | Agent at fb90ad8: 3162 passed, 3 skipped; only the known env failures (T014 stdout import + 3 T101 HTTP, `No module named 'mcp'`, also on develop) — pass |
| **UI: Visual regression (diff or verdict pasted)** | ☐ N/A | backend |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☐ N/A | backend |
| **UI: Responsiveness at target viewports** | ☐ N/A | backend |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE** (captured before the first implementation commit; `develop` = `3182202`):

1. node-api, `score --repo <real-repos>/node-api --scope project < /dev/null`, output file
   `<scratchpad>/<node-api alias>_score.json` (scratch file named after the repo), mtime `2026-10-17 11:31:23 +0700` (04:31:23Z). Verbatim lines:

   ```
   "no number given — only 30% of its rule weight was measured (a rating needs at least 50%); add what the unmeasured rules need"
   /capped [{"dimension": "test-strategy", "role": "test-file", "matched": 110, "read": 50}]
   "no number given — all declared rating metrics abstained"
   ```
   (the third is blast-radius's rating abstention; stderr of the same run:
   `warning [batches]: read batches 1 of 3 (200 of 450 in-scope source files, most important and most-changed first)`).
   Every test-strategy rated code metric in that file abstains with
   `whole-set-dependent: the byte budget truncated this pack, ... (at least 1 item(s) omitted -- a lower bound, never an exact count)`.

2. Synthetic repo (`<scratchpad>/t113/make_big.py big 40`: 40 Python modules under `src/app/`, 40
   test files of 70 tests each), `2026-10-17T04:55:00Z`, `score --repo big --scope project
   --budget-bytes 30000 < /dev/null` on `3182202`:

   ```
   test-strategy assertion_density_per_test -> whole-set-dependent: the byte budget truncated this pack, so any ratio, density or share computed here describes what survived the budget, not the repository (at least 1 item(s) omitted -- a lower bound, never an exact count)
   test-strategy source_files_without_covering_test_share -> whole-set-dependent: the byte budget truncated this pack, ...
   test-strategy tests_without_assertions_share -> whole-set-dependent: the byte budget truncated this pack, ...
   test-strategy skipped_test_share -> whole-set-dependent: the byte budget truncated this pack, ...
   test-strategy None less than the declared floor of this dimension's rule weight was measured, so no number is given
   ```

### AC7 pre-registered expectations (written 2026-10-17T04:56Z, before any new-code run)

| Repo | Expectation |
|---|---|
| node-api | test-strategy **rates** (no "30 % of rule weight" abstention); its index metrics carry no "byte budget truncated" reason; code-quality/architecture/reliability metrics computed over all 450 sources (no "sample" note); security may move (sinks now over every source) |
| fullstack-ts | code-quality and test-strategy: no rated metric abstains with "byte budget truncated" |
| node-monorepo | index capped only if > 5000 code files / 50 MB (disclosed as `dimension: index`); run time stated; ≤ 2× develop |
| python-ml | test-strategy / code-quality no byte-budget abstention; other dimensions unchanged |
| nest-api | as python-ml; security value may move (sinks over every source, T092 precedent) |
| all | dimensions with no index metric (api, data, operations, infrastructure, supply-chain, requirement-fidelity, solution-fit, blast-radius) unchanged |

**AFTER**: the same synthetic repo and command (`score --repo big --scope project --budget-bytes
30000 < /dev/null`), on `fb90ad8`, `2026-10-17T08:23:32Z`, exit 0:

```
test-strategy assertion_density_per_test -> 1.0  | ...); all 80 code files -- computed over the whole text of those files, not only the excerpts quoted in this pack
test-strategy source_files_without_covering_test_share -> 0.0  | ...; all 80 code files -- computed over the whole text of those files, ...
test-strategy tests_without_assertions_share -> 0.0  | ...; all 80 code files -- computed over the whole text of those files, ...
test-strategy skipped_test_share -> 0.0  | ...; all 80 code files -- computed over the whole text of those files, ...
code-quality 100
test-strategy 100
index caps []
```
(BEFORE: those four abstained with "the byte budget truncated this pack", and test-strategy gave
no number.) node-api project score: test-strategy went from "only 30% of its rule weight was
measured" to 75 (AC7 table, Evidence).

**DELTA**: a project score now measures test-strategy, code-quality, architecture and reliability code metrics over every code file of the repository (read once per run), so a pack the byte budget clips no longer makes them abstain or describe a sample.

**WITNESS**: [who ran it and when — derived from `memory/event-trace/Txxx.jsonl`, never the
implementing agent alone]
