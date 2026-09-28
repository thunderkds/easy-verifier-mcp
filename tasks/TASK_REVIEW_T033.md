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

**AFTER**: same scratch repo, same command, on the T033 implementation (backend-developer).

```
$ date -u +%Y-%m-%dT%H:%M:%SZ
2026-09-28T06:10:21Z
$ PYTHONPATH=src ../easy-verifier-mcp/.venv/bin/python -m easy_verifier.adapters.cli score --repo $S/repo --scope worktree < /dev/null > $S/after.json
exit=0
functions_over_ccn_10_share present
max_function_ccn present
top_level_import_cycles present
max_fan_in_changed present
architecture functions_over_ccn_10_share 0.0 ['src/app/alpha.py:1-12', 'src/app/beta.py:1-8', 'src/app/gamma.py:1-5']
architecture max_function_ccn 5 ['src/app/alpha.py:1-12']
architecture top_level_import_cycles 1 ['src/app/alpha.py:1-12', 'src/app/beta.py:1-8']
architecture max_fan_in_changed ABSTAIN: only the blast-radius pack says which files changed: ...
blast-radius max_fan_in_changed 2 ['src/app/alpha.py', 'src/app/alpha.py:1-1', 'src/app/beta.py', 'src/app/beta.py:1-1', 'src/app/gamma.py:1-1', 'tests/test_alpha.py:1-1']
code-quality functions_over_ccn_10_share ABSTAIN: no source-file excerpt in this pack contains a function start ...
code-quality max_function_ccn ABSTAIN: no source-file excerpt in this pack contains a function start ...
$ python -c "...approximate_ccn(open('src/app/alpha.py').read(), curated_metric_tables().syntax['.py'])"
(FunctionCcn(line=4, end_line=11, ccn=5),)
existing metrics unchanged: True 77 105        # all 77 pre-T033 (dimension, metric) outcomes byte-equal
overall before/after: 62 62
```

Hand check: `classify` has if, and, elif, for = 4 decision points -> CCN 5; the `if while for` inside
the string and the comment are not counted. alpha<->beta is the one cycle. alpha (imported by beta,
test_alpha) and beta (imported by alpha, gamma) tie at fan-in 2.

Known gap at the real surface: code-quality packs carry no source excerpts, and on this repository's
own project scope the architecture pack carries 0 code excerpts of 7, so the CCN and cycle metrics
abstain there (honestly, with reasons). See the completion report for the proposed dimension change.

**DELTA**: `score` now reports approximate CCN per observed function (share over 10, max), top-level
import cycles and the max fan-in of changed files, each cited to the excerpts it was computed from,
for all 9 curated languages from registry data only.

**WITNESS**: [who ran it and when — derived from `memory/event-trace/T033.jsonl`, never the
implementing agent alone]
