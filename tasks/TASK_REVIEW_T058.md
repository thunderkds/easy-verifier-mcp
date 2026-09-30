# TASK_REVIEW — T[NNN]: [Short Title]

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

**BEFORE**: captured by backend-developer 2026-09-30T07:32:26Z-07:33:08Z, worktree HEAD `3a381b6` (no fix commit exists), `PYTHONPATH=src <main>/.venv/bin/python -c 'from easy_verifier.adapters.cli import main; main()' score --repo <repo> --scope project </dev/null`:

```
2026-09-30T07:32:26Z
== bryony exit=0 07:32:35Z          (/home/hungnguyenhuu/workspace/project/bryony/bryony)
architecture             50  (30/60)
blast-radius             None  (0/0)
code-quality             100  (20/20)
requirement-fidelity     None  (0/0)
security                 59  (50/85)
solution-fit             None  (0/0)
test-strategy            100  (75/75)
overall 77 (contributor_count 4)
COOKIE UNAVAILABLE: no authentication or session code (a registry auth_markers token) was found in 12 source-file excerpt(s) of registry languages with cookie tokens, so no cookie flag is ju...
== kitchd exit=0 07:32:38Z          (/home/hungnguyenhuu/workspace/pets/hungnguyen111/kitchd)
architecture             100  (60/60)
blast-radius             None  (0/0)
code-quality             67  (30/45)
requirement-fidelity     15  (15/100)
security                 59  (50/85)
solution-fit             None  (0/0)
test-strategy            100  (30/30)
overall 68 (contributor_count 5)
COOKIE UNAVAILABLE: no authentication or session code ... was found in 11 source-file excerpt(s) ...
== ai-training exit=0 07:32:40Z     (/home/hungnguyenhuu/workspace/training/hoang.hoan/ai-training)
architecture             70  (70/100)
blast-radius             None  (0/0)
code-quality             40  (10/25)
requirement-fidelity     0  (0/15)
security                 59  (50/85)
solution-fit             None  (0/0)
test-strategy            100  (30/30)
overall 54 (contributor_count 5)
COOKIE UNAVAILABLE: no authentication or session code ... was found in 5 source-file excerpt(s) ...

2026-09-30T07:33:08Z  security --repo <bryony> --scope project </dev/null
files_read 225 excerpts 40   truncated False omitted_count 0
index.js read? False quoted? False      (backend/server/dashboard/index.js)
```

**AFTER**: [same command, post-change] OR [verbatim excerpt of the new content]

**DELTA**: [one sentence — what a user can now do that they could not before]

**WITNESS**: [who ran it and when — derived from `memory/event-trace/T058.jsonl`, never the
implementing agent alone]
