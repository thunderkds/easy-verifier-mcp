# TASK_REVIEW — T075: requirement-fidelity code rules

> Sibling of `tasks/TASK_GUIDE_T075.md`. Everything here is **filled by the reviewer at Stage
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

**BEFORE** (Supervisor, before any T073–T075 code, branch plan/code-derived-rules; real repos, `score --scope project`):

```
Sun Oct  4 10:03:33 AM UTC 2026
0a02f85 plan: code-derived rules — brainstorm + grilling, DDR-0011, FR-067..071, US-021, glossary
coffee-shop-api overall 65 | architecture below_coverage_floor | requirement-fidelity below_coverage_floor | all {'architecture': 'below_coverage_floor', 'blast-radius': 'all_metrics_abstained', 'code-quality': 71, 'requirement-fidelity': 'below_coverage_floor', 'security': 59, 'solution-fit': 'no_static_rule', 'test-strategy': 'insufficient_measured_weight'}
bryony overall 66 | architecture 70 | requirement-fidelity below_coverage_floor | all {'architecture': 70, 'blast-radius': 'all_metrics_abstained', 'code-quality': 67, 'requirement-fidelity': 'below_coverage_floor', 'security': 50, 'solution-fit': 'no_static_rule', 'test-strategy': 75}
kitchd overall 58 | architecture 100 | requirement-fidelity 15 | all {'architecture': 100, 'blast-radius': 'all_metrics_abstained', 'code-quality': 'insufficient_measured_weight', 'requirement-fidelity': 15, 'security': 59, 'solution-fit': 'no_static_rule', 'test-strategy': 'insufficient_measured_weight'}
```

**AFTER**: [same command, post-change] OR [verbatim excerpt of the new content]

**DELTA**: [one sentence — what a user can now do that they could not before]

**WITNESS**: [who ran it and when — derived from `memory/event-trace/Txxx.jsonl`, never the
implementing agent alone]
