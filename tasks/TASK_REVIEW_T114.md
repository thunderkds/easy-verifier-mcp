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
| `test_t072` area 5 row | `docs/AREA_COVERAGE.md` row lists the 2 new rules | doc must equal the rule table |

Docs also updated: `README.md` rating table, `docs/EVALUATION_GUIDE.md` scope bullet,
`docs/SCORING_RULES.md` blast-radius rows, `docs/AREA_COVERAGE.md` area 5.

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

**AFTER**: [same command, post-change] OR [verbatim excerpt of the new content]

**DELTA**: [one sentence — what a user can now do that they could not before]

**WITNESS**: [who ran it and when — derived from `memory/event-trace/Txxx.jsonl`, never the
implementing agent alone]
