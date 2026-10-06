# TASK_REVIEW — T082: The score names the evaluation areas it does not measure

> Sibling of `tasks/TASK_GUIDE_T082.md`. Everything here is **filled by the reviewer at Stage
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

**BEFORE**: captured 2026-10-06T04:03:36Z–04:03:53Z on worktree HEAD `eb16069` (no implementation
commit exists), by backend-developer, target coffee-shop-api, `--scope project`:

```
$ PYTHONPATH=src .venv/bin/python -m easy_verifier.adapters.cli score \
    --repo .../nestjs-training/coffee-shop-api --scope project < /dev/null > before.json   # exit=0
$ python -c "d=json.load(open('before.json')); o=d['overall']; print(sorted(o)); print(o['disclosure'])"
['abstentions', 'contributor_count', 'contributor_values', 'contributors', 'disclosure', 'kind',
 'method', 'rated_by', 'total_dimension_count', 'value']
disclosure: 4 of 7 dimensions contributed (4 rule-rated, 0 blended, 0 agent-rated); ratings average
contributors only, so abstention can raise the overall; abstained: solution-fit (no_static_rule: ...),
test-strategy (insufficient_measured_weight: ...), blast-radius (all_metrics_abstained: ...)
$ "areas_measured" / "areas_without_rule" / "evaluation areas" anywhere in before.json -> False False False
overall value: 65

$ ... write-report --repo .../coffee-shop-api --scope project --findings empty.json < /dev/null
{"path": "reports/evidence-report-project-20261006T040354-734779Z.html", "advisory": null}  # exit=0
$ grep -c "evaluation area\|Areas no rule" <that report>  ->  0
```

The payload has no area count and no uncovered-area list; the disclosure names dimensions only; the
HTML score panel never mentions evaluation areas.

**AFTER**: [same command, post-change] OR [verbatim excerpt of the new content]

**DELTA**: [one sentence — what a user can now do that they could not before]

**WITNESS**: [who ran it and when — derived from `memory/event-trace/T082.jsonl`, never the
implementing agent alone]
