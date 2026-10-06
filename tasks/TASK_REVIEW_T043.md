# TASK_REVIEW — T043: New dimension: reliability

> Sibling of `tasks/TASK_GUIDE_T043.md`. Everything here is **filled by the reviewer at Stage
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

**BEFORE**: captured by backend-developer in worktree `easy-verifier-mcp-T043` at `eb16069` (develop, no T043 commit yet).

```text
$ PYTHONPATH=src .venv/bin/python -m easy_verifier.adapters.cli list-dimensions < /dev/null   # 2026-10-06T04:04:09Z
dimension names: architecture, blast-radius, code-quality, requirement-fidelity, security, solution-fit, test-strategy  (7 dimensions; no 'reliability')
exit=0

$ ... cli score --repo /home/hungnguyenhuu/workspace/training/tien.nguyen/nestjs-training/coffee-shop-api --scope project < /dev/null   # 2026-10-06T04:04:25Z .. 2026-10-06T04:04:27Z, exit=0
overall 65 (4 of 7 dimensions)
ratings: architecture=80 blast-radius=all_metrics_abstained code-quality=71 requirement-fidelity=50 security=59 solution-fit=no_static_rule test-strategy=insufficient_measured_weight
'reliability' anywhere in the payload: False

$ ... cli score --repo /home/hungnguyenhuu/workspace/project/bryony/bryony --scope project < /dev/null   # 2026-10-06T04:04:39Z .. 2026-10-06T04:04:51Z, exit=0
overall 69 (4 of 7 dimensions)
ratings: architecture=83 blast-radius=all_metrics_abstained code-quality=67 requirement-fidelity=below_coverage_floor security=50 solution-fit=no_static_rule test-strategy=75
'reliability' anywhere in the payload: False

$ ... cli score --repo /home/hungnguyenhuu/workspace/pets/hungnguyen111/kitchd --scope project < /dev/null   # 2026-10-06T04:04:51Z .. 2026-10-06T04:04:56Z, exit=0
overall 72 (4 of 7 dimensions)
ratings: architecture=100 blast-radius=all_metrics_abstained code-quality=70 requirement-fidelity=60 security=59 solution-fit=no_static_rule test-strategy=insufficient_measured_weight
'reliability' anywhere in the payload: False
```

**AFTER**: [same command, post-change] OR [verbatim excerpt of the new content]

**DELTA**: [one sentence — what a user can now do that they could not before]

**WITNESS**: [who ran it and when — derived from `memory/event-trace/T043.jsonl`, never the
implementing agent alone]
