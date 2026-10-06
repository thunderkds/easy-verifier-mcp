# TASK_REVIEW — T048: Finance pack (#3 financial integrity & historical reconstruction)

> Sibling of `tasks/TASK_GUIDE_T048.md`. Everything here is **filled by the reviewer at Stage
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

**BEFORE** (captured by backend-developer before any T048 implementation commit, worktree HEAD = develop 1e7b3a5; demo repo = scratch git repo with `.easy-verifier.toml` `packs = ["finance"]` and `src/payments.py` declaring `amount: float`):

```text
$ date -u; git -C easy-verifier-mcp-T048 rev-parse --short HEAD
2026-10-06T08:43:49Z
1e7b3a5
$ python -m easy_verifier.adapters.cli score --repo demo < /dev/null   # demo: .easy-verifier.toml packs = ["finance"], src/payments.py 'amount: float'
exit=0
stderr:
warning [registry]: unknown pack 'finance' ignored; known packs: healthcare
ratings dimensions: ['architecture', 'blast-radius', 'code-quality', 'reliability', 'requirement-fidelity', 'security', 'solution-fit', 'test-strategy']
area #3 in areas_without_rule: True
finance in payload: False | float_money in payload: False
overall: 67 lared floor of this dimension's rule weight was measured, so no number is given)
```

The finance pack is unknown (noted and ignored), no finance slot/metric exists, and area #3 "Financial integrity & historical reconstruction" is listed in `areas_without_rule`.

**AFTER**: [same command, post-change] OR [verbatim excerpt of the new content]

**DELTA**: [one sentence — what a user can now do that they could not before]

**WITNESS**: [who ran it and when — derived from `memory/event-trace/T048.jsonl`, never the
implementing agent alone]
