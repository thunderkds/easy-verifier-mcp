# TASK_REVIEW — T121: Secret hits in context files must not lower a narrow-scope security score

> Sibling of `tasks/TASK_GUIDE_T121.md`. Everything here is **filled by the reviewer at Stage
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

**BEFORE**: captured by backend-developer in the T121 worktree on branch `fix/T121-context-secret-hits` at `5a19bd2` (no implementation commit yet). Script: security pack via `combined_pack(["security"], repo, "changes", 120000, ref="3f4aceb^1...3f4aceb^2")`, hits grouped by (path, detector), then MCP `score(...)` security rating on `easy-personal-mcp` (not modified).

```
$ PYTHONPATH=src <main>/.venv/bin/python scratchpad/hun34.py < /dev/null
captured: 2026-10-21T10:58:07+00:00
easy-verifier HEAD: 5a19bd2
pack.redactions: 123
   116  .claude/harness-lock.json  high_entropy_hex
     3  tasks/TASK_REVIEW_HUN-34.md  key_material_segment
     2  tasks/TASK_REVIEW_HUN-34.md  high_entropy_string
     2  web/package-lock.json  high_entropy_string
security rating: 18
  redaction_hits_observed = 123 FAILED
  redaction_hits_observed derivation: 123 secret redaction(s) recorded while building this pack from the 18 file(s) listed here; a lower bound on the repository, since only these files were read
  redacted_file_share derivation: 3 file(s) with at least one redaction (.claude/harness-lock.json, tasks/TASK_REVIEW_HUN-34.md, web/package-lock.json) / 18 file(s) read
```

Only `tasks/TASK_REVIEW_HUN-34.md` is changed by HUN-34; `.claude/harness-lock.json` and `web/package-lock.json` are context-role (lockfile) files read repo-wide, yet they supply 118 of the 123 counted hits.

**AFTER**: [same command, post-change] OR [verbatim excerpt of the new content]

**DELTA**: [one sentence — what a user can now do that they could not before]

**WITNESS**: [who ran it and when — derived from `memory/event-trace/Txxx.jsonl`, never the
implementing agent alone]
