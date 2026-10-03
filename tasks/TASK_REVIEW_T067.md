# TASK_REVIEW — T067: Evidence floor

> Sibling of `tasks/TASK_GUIDE_T067.md`. Everything here is **filled by the reviewer at Stage
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

**BEFORE**: captured by backend-developer on `fix/T067-evidence-floor` at HEAD `d98ac4d` (no implementation commit yet). Command: `PYTHONPATH=src .venv/bin/python -m easy_verifier.adapters.cli score --repo /home/hungnguyenhuu/workspace/project/bryony/bryony --scope project </dev/null | python3 -c '...print dimension, value/reason_code, inputs (metric, weight), len(unavailable_metrics)...'`

```
Sat Oct  3 02:49:24 PM UTC 2026
d98ac4d
architecture 50 [('architecture_description_missing', 30), ('decision_records_missing', 30)] 1
blast-radius all_metrics_abstained [] 4
code-quality 100 [('lint_config_missing', 10), ('format_config_missing', 10)] 5
requirement-fidelity below_coverage_floor [] 0
security 50 [('redaction_hits_observed', 35), ('sink_hits_observed', 35), ('lockfile_missing', 15), ('cookie_flags_missing_observed', 15)] 0
solution-fit no_static_rule [] 0
test-strategy 100 [('assertion_density_per_test', 20), ('test_config_and_ci_missing', 20), ('tests_without_assertions_share', 15), ('skipped_test_share', 10), ('network_calls_in_unit_tests_observed', 10)] 1
```

code-quality is rated **100** from only 2 measured inputs (lint_config_missing 10 + format_config_missing 10 = 20 weight) while 5 rule metrics were unavailable.

**AFTER**: [same command, post-change] OR [verbatim excerpt of the new content]

**DELTA**: [one sentence — what a user can now do that they could not before]

**WITNESS**: [who ran it and when — derived from `memory/event-trace/Txxx.jsonl`, never the
implementing agent alone]
