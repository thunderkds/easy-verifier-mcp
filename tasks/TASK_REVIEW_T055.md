# TASK_REVIEW — T055: Area rule groups needing git evidence (#5, #27)

> Sibling of `tasks/TASK_GUIDE_T055.md`. Everything here is **filled by the reviewer at Stage
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

**BEFORE**: captured 2026-09-29T10:15:58Z by backend-developer at worktree HEAD `e0a6d83` (no T055
implementation commit exists). Fixture: a fresh git repo (5 commits) built by a scratch script —
`init` (src/shop/api.py with public `list_items`, `get_item` and private `_helper`;
`migrations/0001_init.sql`; README.md, PRD.md, docs/requirements.md, SPEC.md, ROADMAP.md,
pyproject.toml), three "code change" commits touching only `src/shop/api.py` (never docs), then
`HEAD` = "remove get_item; drop price column" (deletes `def get_item`, adds
`migrations/0002_drop_price.sql` = `ALTER TABLE items DROP COLUMN price;`).

```
$ PYTHONPATH=src .venv/bin/python -m easy_verifier.adapters.cli score --repo <fixture> --scope changes --ref HEAD </dev/null > before.json
exit=0
$ python show.py before.json   # ratings of the two dimensions T055 touches
blast-radius: kind=rating_abstention value=None reason=all_metrics_abstained
  unavailable max_fan_in_changed: no import statement was found in this pack's code-file excerpts, so there is no import graph to measure; ...
  unavailable changed_files_in_churn_hotspots_share: examined: only 5 local commit(s), fewer than the 20 a churn ranking needs, so no file is called a hotspot
requirement-fidelity: kind=rating value=0 reason=None
  input acceptance_criteria_traced_to_code_share = 0.0 (at_least 0.8, passed=False) area='Business-rule correctness'
  input acceptance_criteria_traced_to_test_share = 0.0 (at_least 0.8, passed=False) area='Business-rule correctness'
$ grep -c 'Documentation source-of-truth governance\|public_symbols_removed' before.json
0
```

No #5 rule sees the removed public function or the dropped column (blast-radius has only the fan-in
and churn rules, both abstaining), and no rule or metric carries the #27 area
`Documentation source-of-truth governance` — the two competing requirements docs (PRD.md,
docs/requirements.md) and the three code-only commits are invisible to the rating.

**AFTER**: [same command, post-change] OR [verbatim excerpt of the new content]

**DELTA**: [one sentence — what a user can now do that they could not before]

**WITNESS**: [who ran it and when — derived from `memory/event-trace/T055x.jsonl`, never the
implementing agent alone]
