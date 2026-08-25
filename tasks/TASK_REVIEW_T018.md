# TASK_REVIEW — T018: README documenting the intended v1 surface

> Sibling of `tasks/TASK_GUIDE_T018.md`. Everything here is **filled by the reviewer at Stage
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

**BEFORE**: Verbatim prior content of `README.md` in full (a single line, no trailing newline):

```
# easy-verifier-mcp
```

**AFTER**: `README.md` is now a full operator-facing document (what the tool is/refuses to do, the
seven dimensions checked against `DIMENSIONS`, the four scopes and their selectors, both adapters
with runnable-vs-planned commands, safety posture, coverage/miss-list rule, standalone/kit-aware
modes) plus `tests/test_t018_readme.py`, a doc-truth test enforcing that every fenced command block
is either runnable today or carries a `planned` marker:

```
$ .venv/bin/python -m pytest tests/test_t018_readme.py -q
......                                                                   [100%]
6 passed in 0.29s
$ echo exit=$?
exit=0
```

**DELTA**: A newcomer can now read `README.md` alone to learn what runs today (the CLI) versus what
is planned (MCP, Docker, discovery/combined/write-report), and a future edit that drops the
`planned` marker or lets `DIMENSIONS` drift from the doc is caught by an automated test instead of
going unnoticed.

**WITNESS**: [to be filled from `memory/event-trace/T018.jsonl` at Stage 4/5 review]
