# TASK_REVIEW — T034: Security sink patterns per language (CWE-95/78/89)

> Sibling of `tasks/TASK_GUIDE_T034.md`. Everything here is **filled by the reviewer at Stage
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

**BEFORE**: captured 2026-09-28T06:22:07Z on `13cef1c` (no T034 implementation commit exists; working-tree edits were stashed for the run). A real CLI `score` over a scratch git repo whose `app/db.py` holds an f-string SQL `cursor.execute(...)` (CWE-89) and `subprocess.run(cmd, shell=True)` (CWE-78): no metric named `*sink*` exists, the security pack quotes only `pyproject.toml:1-2`, and neither sink line appears anywhere in the output.

```text
$ date -u; git -C /home/hungnguyenhuu/workspace/pets/hungnguyen111/easy-verifier-mcp-T034 rev-parse --short HEAD
2026-09-28T06:22:07Z
13cef1c
$ cat -n app/db.py (scratch repo)
     1	import sqlite3
     2	import subprocess
     3	
     4	
     5	def find_user(cursor, user):
     6	    cursor.execute(f"SELECT * FROM users WHERE name = '{user}'")
     7	    return cursor.fetchall()
     8	
     9	
    10	def run(cmd):
    11	    return subprocess.run(cmd, shell=True)
$ PYTHONPATH=src .venv/bin/python -c 'main(["score","--repo","<scratch>/sinkrepo","--scope","project"])' > out.json
exit=0
security metric names: ['test_to_source_ratio', 'source_files_without_covering_test', 'assertion_density_per_test', 'assertions_observed', 'redaction_hits_observed', 'redacted_file_share', 'excerpts_observed', 'declared_source_coverage', 'evidence_lines_observed', 'mean_excerpt_lines', 'source_file_share', 'functions_over_ccn_10_share', 'max_function_ccn', 'top_level_import_cycles', 'max_fan_in_changed']
any metric named *sink*: []
excerpts_observed: value=1 abstained=False computed_from=['pyproject.toml:1-2']
occurrences of 'execute(' / 'shell=True' in output: 0 0
```

**AFTER**: [same command, post-change] OR [verbatim excerpt of the new content]

**DELTA**: [one sentence — what a user can now do that they could not before]

**WITNESS**: [who ran it and when — derived from `memory/event-trace/T034.jsonl`, never the
implementing agent alone]
