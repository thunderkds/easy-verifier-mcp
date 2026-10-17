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

**AFTER**: [same command, post-change] OR [verbatim excerpt of the new content]

**DELTA**: [one sentence — what a user can now do that they could not before]

**WITNESS**: [who ran it and when — derived from `memory/event-trace/Txxx.jsonl`, never the
implementing agent alone]
