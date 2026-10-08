# TASK_REVIEW — T049: Frontend accessibility pack

> Sibling of `tasks/TASK_GUIDE_T049.md`. Everything here is **filled by the reviewer at Stage
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

**BEFORE** (captured by backend-developer before any T049 implementation commit, worktree HEAD = c50955f; real repo = `/home/hungnguyenhuu/workspace/project/beautifly/github/tapchat-web` (pnpm/turbo monorepo, Next.js + React, 832 JSX/TSX/HTML files), read-only):

```text
$ date -u; git rev-parse HEAD
2026-10-08T03:40:49Z
c50955f839d7e6d4dde26a16a698c5c87a3080fd
$ PYTHONPATH=<worktree>/src python -m easy_verifier.adapters.cli score --repo tapchat-web </dev/null > tapchat_before.json
exit=0   (finished 2026-10-08T03:41:07Z)
stderr:
warning [batches]: read batches 1 of 5 (200 of 891 in-scope source files, most important and most-changed first); continue with --batches 2, or --all
overall 65 contributors [['architecture', 67], ['code-quality', 70], ['security', 59]]
areas_measured 14
areas_without_rule ['Financial integrity & historical reconstruction', 'Transactions, concurrency, idempotency', 'PHI minimization, retention, test-data safety', 'Accessibility, responsive UX, browser compat', 'Vendor, BAA, data classification, residency']
detected_stack {'languages': ['js-ts'], 'frameworks': [{'name': 'next', 'language': 'js-ts'}, {'name': 'react', 'language': 'js-ts'}]}
sha256 d05f470941b57176fb20b422564490dd40acd005cb221fc34d7806852829b9f3

$ date -u    # same repo, pack requested via --agent-input {"packs": ["frontend-a11y"]}
2026-10-08T03:41:39Z
exit=0
stderr:
warning [registry]: unknown pack 'frontend-a11y' ignored; known packs: healthcare, finance
warning [batches]: read batches 1 of 5 (200 of 891 in-scope source files, most important and most-changed first); continue with --batches 2, or --all
overall 65
ratings ['api', 'architecture', 'blast-radius', 'code-quality', 'data', 'infrastructure', 'operations', 'reliability', 'requirement-fidelity', 'security', 'solution-fit', 'supply-chain', 'test-strategy']
#19 in areas_without_rule True
cmp tapchat_before.json tapchat_before_on.json -> IDENTICAL
```

The `frontend-a11y` pack is unknown (ignored with a warning), no accessibility metric exists, and area #19 "Accessibility, responsive UX, browser compat" is listed in `areas_without_rule`.

**AFTER**: [same command, post-change] OR [verbatim excerpt of the new content]

**DELTA**: [one sentence — what a user can now do that they could not before]

**WITNESS**: [who ran it and when — derived from `memory/event-trace/T049.jsonl`, never the
implementing agent alone]
