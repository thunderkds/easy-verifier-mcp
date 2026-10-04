# TASK_REVIEW — T069: Report summary

> Sibling of `tasks/TASK_GUIDE_T069.md`. Everything here is **filled by the reviewer at Stage
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

**BEFORE** (captured by backend-developer on `feat/T069-report-summary` at `ae77a8b`, before any code
change; `S=/tmp/claude-1000/-home-hungnguyenhuu-workspace-pets-hungnguyen111-easy-verifier-mcp/4b78de6f-bc95-4225-acbd-da02da5664de/scratchpad`):

```
$ rsync -a --exclude node_modules --exclude reports \
    /home/hungnguyenhuu/workspace/training/tien.nguyen/nestjs-training/coffee-shop-api/ $S/coffee-shop-api/
$ echo '[]' > $S/findings-empty.json
$ cd <worktree> && date -u && PYTHONPATH=src <main>/.venv/bin/python -m easy_verifier.adapters.cli \
    write-report --repo $S/coffee-shop-api --scope project --findings $S/findings-empty.json </dev/null > $S/before-out.json
Sun Oct  4 04:01:53 AM UTC 2026
exit=0
  "path": "reports/evidence-report-project-20261004T040154-307470Z.html",

$ date -u; grep -o '<h[12][^>]*>[^<]*' $S/coffee-shop-api/reports/*.html | head -12
Sun Oct  4 04:01:58 AM UTC 2026
<h1>Evidence report
<h2>Before you share this report
<h2>Context warnings
<h2>Evidence warnings — no number given
<h2>Quality score
<h2>Improvement plan
<h2>Checklist coverage
<h2>Dimensions
```

The report opens straight into warnings, then the score panel and the plan: there is no summary
section (the only "summary" strings in the file are `<details><summary>` toggles). A copy of this
report is kept at `$S/before-report.html`.

**AFTER**: [same command, post-change] OR [verbatim excerpt of the new content]

**DELTA**: [one sentence — what a user can now do that they could not before]

**WITNESS**: [who ran it and when — derived from `memory/event-trace/Txxx.jsonl`, never the
implementing agent alone]
