# TASK_REVIEW — T099: Redaction keeps extensionless lower-case word paths

> Sibling of `tasks/TASK_GUIDE_T099.md`. Everything here is **filled by the reviewer at Stage
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

**BEFORE** (captured 2026-10-14T03:34:04Z on develop `2452bcf`, before any implementation commit; run by backend-developer):

```
$ PYTHONPATH=src .venv/bin/python -c "from easy_verifier.core.redact import redact; print(redact('bin/build-push-kibana-docker-image'))"
bin/…****:e169e83f548e
$ git -C scraping-devops ls-files | count paths where redact(p) != p
tracked 597 changed 1
  bin/build-push-kibana-docker-image -> bin/…****:e169e83f548e
```

**AFTER** (2026-10-14T03:37:09Z, worktree `fix/T099-extensionless-paths`):

```
bin/build-push-kibana-docker-image
tracked 597 changed 0
```

**DELTA**: a citation to `bin/build-push-kibana-docker-image` (and any extensionless lower-case word path) now resolves; scraping-devops goes from 1 tracked path changed by `redact()` to 0.

**WITNESS**: [who ran it and when — derived from `memory/event-trace/T099.jsonl`, never the
implementing agent alone]
