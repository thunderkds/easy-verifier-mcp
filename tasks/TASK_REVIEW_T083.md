# TASK_REVIEW — T[NNN]: changes-scope crash on non-code diff

> Sibling of `tasks/TASK_GUIDE_T[NNN].md`. Everything here is **filled by the reviewer at Stage
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
| Repro loop | ☐ pass / ☐ fail | [command/observation that reproduced the bug before the fix] |
| Regression test | ☐ pass / ☐ fail | [test file path(s) added to lock the fix in] |
| Smoke suite | ☐ pass / ☐ fail | [bug-specific smoke check beyond the full suite row above] |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE**: captured 2026-10-08T02:54:40Z on base 129de71 (pre-fix). Repro: temp git repo, commit 1 = `prod.tfvars` + README, commit 2 changes only `prod.tfvars`; `easy-verifier score --repo <r> --scope changes --ref HEAD~1..HEAD </dev/null` (via `python -c` calling `easy_verifier.adapters.cli.main`, same entry point):

```
2026-10-08T02:54:40Z
validation error: metric 'breaking_api_changes_observed' (api) reports a value but cites no evidence
exit=2
```

(Note: changes scope needs `--ref`; a bare working-tree diff resolves to "changes scope could not be resolved", so the repro uses a committed range.)

**AFTER**: 2026-10-08T02:55:41Z same repro, post-fix: score completes (exit 0), api metric:
`"name": "breaking_api_changes_observed", "outcome": {"abstained": true, "reason": "no API specification or route source file in this diff was read"}`. Real repo `project/bryony/bryony` `--ref HEAD~1..HEAD` (2026-10-08T02:57:59Z): exit=0, metric value 0, cited.

**DELTA**: `score --scope changes` on a diff with no API spec or route source file now completes, with the breaking-change metric abstaining honestly instead of crashing the whole score.

**WITNESS**: [who ran it and when — derived from `memory/event-trace/T083.jsonl`, never the
implementing agent alone]
