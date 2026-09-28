# TASK_REVIEW — T050: Code-quality and architecture packs gather code evidence (source excerpts, import lines)

> Sibling of `tasks/TASK_GUIDE_T050.md`. Everything here is **filled by the reviewer at Stage
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

**BEFORE**: captured by backend-developer on the worktree at `13cef1c` (no T050 commit yet).
Scratch repo `$S/repo` (git, committed): `src/app/alpha.py` (`route`: if, elif, elif+and, if+or,
for, if, while, if, if = 11 decision points, CCN 12 by `approximate_ccn`; imports `beta`),
`src/app/beta.py` (imports `alpha`), `src/app/__init__.py`, `tests/test_alpha.py`,
`pyproject.toml` (with `[tool.ruff]`), `README.md`. `show.py` prints the three T050 metrics for
the code-quality and architecture packs from the score JSON; `packbytes.py` runs `run_dimension`
for both dimensions at project scope and sums excerpt bytes (NFR-009 baseline).

```
$ git -C easy-verifier-mcp-T050 rev-parse --short HEAD
13cef1c
$ date -u +%Y-%m-%dT%H:%M:%SZ
2026-09-28T06:16:03Z
$ PYTHONPATH=src python -m easy_verifier.adapters.cli score --repo $S/repo --scope project < /dev/null > $S/before_scratch.json
exit=0
$ python show.py before_scratch.json
architecture  functions_over_ccn_10_share  ABSTAIN: no source-file excerpt in this pack contains a function start the registry recognises, so no function was obse
architecture  max_function_ccn             ABSTAIN: no source-file excerpt in this pack contains a function start the registry recognises, so no function was obse
architecture  top_level_import_cycles      ABSTAIN: no import statement was found in this pack's source-file excerpts, so there is no import graph to measure; tha
code-quality  functions_over_ccn_10_share  ABSTAIN: no source-file excerpt in this pack contains a function start the registry recognises, so no function was obse
code-quality  max_function_ccn             ABSTAIN: no source-file excerpt in this pack contains a function start the registry recognises, so no function was obse
code-quality  top_level_import_cycles      ABSTAIN: no import statement was found in this pack's source-file excerpts, so there is no import graph to measure; tha
$ PYTHONPATH=src python -m easy_verifier.adapters.cli score --repo . --scope project < /dev/null > $S/before_self.json
exit=0
$ python show.py before_self.json
architecture  functions_over_ccn_10_share  ABSTAIN: no source-file excerpt in this pack contains a function start the registry recognises, so no function was obse
architecture  max_function_ccn             ABSTAIN: no source-file excerpt in this pack contains a function start the registry recognises, so no function was obse
architecture  top_level_import_cycles      ABSTAIN: no import statement was found in this pack's source-file excerpts, so there is no import graph to measure; tha
code-quality  functions_over_ccn_10_share  ABSTAIN: no source-file excerpt in this pack contains a function start the registry recognises, so no function was obse
code-quality  max_function_ccn             ABSTAIN: no source-file excerpt in this pack contains a function start the registry recognises, so no function was obse
code-quality  top_level_import_cycles      ABSTAIN: no import statement was found in this pack's source-file excerpts, so there is no import graph to measure; tha
$ PYTHONPATH=src python packbytes.py $S/repo   # NFR-009 baseline
code-quality  bytes=70 excerpts=1 truncated=False omitted=0
architecture  bytes=49 excerpts=1 truncated=False omitted=0
$ PYTHONPATH=src python packbytes.py .
code-quality  bytes=1711 excerpts=1 truncated=False omitted=0
architecture  bytes=84498 excerpts=7 truncated=False omitted=0
$ date -u +%Y-%m-%dT%H:%M:%SZ
2026-09-28T06:16:04Z
```

All three metrics abstain in both packs on both repos because neither pack quotes any source code
(code-quality: 1 config excerpt; architecture on this repo: 7 doc excerpts, 0 code).

**AFTER**: [same command, post-change] OR [verbatim excerpt of the new content]

**DELTA**: [one sentence — what a user can now do that they could not before]

**WITNESS**: [who ran it and when — derived from `memory/event-trace/T050.jsonl`, never the
implementing agent alone]
