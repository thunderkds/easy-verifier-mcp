# TASK_REVIEW — T033: [Short Title]

> Sibling of `tasks/TASK_GUIDE_T033.md`. Everything here is **filled by the reviewer at Stage
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

**BEFORE**: captured by backend-developer on the worktree at `2b7ae8c` (no T033 commit yet).
Scratch repo: `src/app/{alpha,beta,gamma}.py` (alpha<->beta import each other, gamma imports beta,
`classify` has if/and/elif/for plus `if while for` inside a string and a comment), `tests/test_alpha.py`,
`pyproject.toml`; alpha.py and beta.py modified in the worktree.

```
$ date -u +%Y-%m-%dT%H:%M:%SZ
2026-09-28T05:51:33Z
$ PYTHONPATH=src ../easy-verifier-mcp/.venv/bin/python -m easy_verifier.adapters.cli score --repo $S/repo --scope worktree < /dev/null > $S/before.json
exit=0
$ python names.py before.json        # lists every metric name in the score payload
metric names: ['assertion_density_per_test', 'assertions_observed', 'declared_source_coverage', 'evidence_lines_observed', 'excerpts_observed', 'mean_excerpt_lines', 'redacted_file_share', 'redaction_hits_observed', 'source_file_share', 'source_files_without_covering_test', 'test_to_source_ratio']
approximate_ccn ABSENT
functions_over_ccn_10_share ABSENT
max_function_ccn ABSENT
top_level_import_cycles ABSENT
max_fan_in_changed ABSENT
$ date -u +%Y-%m-%dT%H:%M:%SZ
2026-09-28T05:51:42Z
$ PYTHONPATH=src python -c "from easy_verifier.core.tokens import approximate_ccn"
ModuleNotFoundError: No module named 'easy_verifier.core.tokens'
$ PYTHONPATH=src python -c "import easy_verifier.core.metrics as m; print(hasattr(m,'approximate_ccn'))"
False
```

**AFTER**: [same command, post-change] OR [verbatim excerpt of the new content]

**DELTA**: [one sentence — what a user can now do that they could not before]

**WITNESS**: [who ran it and when — derived from `memory/event-trace/T033.jsonl`, never the
implementing agent alone]
