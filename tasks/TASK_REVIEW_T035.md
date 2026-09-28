# TASK_REVIEW — T035: Per-dimension cited rules for the existing 7 dimensions

> Sibling of `tasks/TASK_GUIDE_T035.md`. Everything here is **filled by the reviewer at Stage
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

**BEFORE**: captured before any T035 implementation commit (HEAD 685f07a), real CLI
`PYTHONPATH=src python -m easy_verifier.adapters.cli score --scope project --repo <repo> </dev/null`,
per-dimension rating/abstention + overall (old 11 shared rules applied to every dimension):

```text
### easy-verifier-mcp (/home/hungnguyenhuu/workspace/pets/hungnguyen111/easy-verifier-mcp-T035) -- 2026-09-28T07:17:16Z exit=0
  architecture           rating 65
  blast-radius           rating 64
  code-quality           rating 50
  requirement-fidelity   rating 50
  security               rating 50
  solution-fit           rating 82
  test-strategy          rating 60
  overall: {'kind': 'overall_rating', 'value': 60}
### kitchd (/home/hungnguyenhuu/workspace/pets/hungnguyen111/kitchd) -- 2026-09-28T07:17:17Z exit=0
  architecture           rating 45
  blast-radius           rating 64
  code-quality           rating 41
  requirement-fidelity   rating 50
  security               rating 50
  solution-fit           rating 45
  test-strategy          rating 60
  overall: {'kind': 'overall_rating', 'value': 51}
### bryony (/home/hungnguyenhuu/workspace/project/bryony/bryony) -- 2026-09-28T07:17:19Z exit=0
  architecture           rating 82
  blast-radius           rating 64
  code-quality           rating 82
  requirement-fidelity   abstain (achieved coverage is below the declared floor)
  security               rating 29
  solution-fit           abstain (achieved coverage is below the declared floor)
  test-strategy          rating 57
  overall: {'kind': 'overall_rating', 'value': 63}
### ai-training (/home/hungnguyenhuu/workspace/training/hoang.hoan/ai-training) -- 2026-09-28T07:17:26Z exit=0
  architecture           rating 65
  blast-radius           rating 50
  code-quality           rating 50
  requirement-fidelity   rating 82
  security               rating 60
  solution-fit           abstain (achieved coverage is below the declared floor)
  test-strategy          rating 60
  overall: {'kind': 'overall_rating', 'value': 61}
```

**AFTER**: [same command, post-change] OR [verbatim excerpt of the new content]

**DELTA**: [one sentence — what a user can now do that they could not before]

**WITNESS**: [who ran it and when — derived from `memory/event-trace/T035.jsonl`, never the
implementing agent alone]
