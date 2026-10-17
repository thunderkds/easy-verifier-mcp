# TASK_REVIEW — T112: Agent-confirmed test ↔ changed-symbol pairs

> Sibling of `tasks/TASK_GUIDE_T112.md`. Everything here is **filled by the reviewer at Stage
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

**BEFORE** (captured 2026-10-17T03:17:04Z by backend-developer on `feat/T112-test-symbol-pairs` at
`c457c70` -- no implementation commit yet). Synthetic repo (built by a scratch script): root
`pyproject.toml`; `utils/dates.py` defines `def parse_date(text)`; `tests/test_api.py` imports and
calls `parse_date`. Commit 1 `chore: initial`; commit 2 `fix: parse_date added one day` edits the
body of `parse_date` and adds `test_parse_date_keeps_the_day` (calling `parse_date`) to
`tests/test_api.py`.

```
$ date -u +%Y-%m-%dT%H:%M:%SZ
2026-10-17T03:17:04Z
$ PYTHONPATH=src:<py312 site-packages> python3.12 -m easy_verifier.adapters.cli score \
    --repo <scratch>/demo --scope changes --ref HEAD < /dev/null > before.json   # exit=0
change_risk 0 | kind bugfix detected
  bugfix_without_regression_test = 0 passed=False
    cites: ['utils/dates.py']
    derivation (metrics): "0 matched test files: none of the test files added or changed
    (tests/test_api.py) matches the 1 changed source file(s) cited; a test file counts when it is
    added or changed in this change and its name is a conventional test name of a changed source
    file in the same project (test-strategy's correspondence; project boundaries read from
    manifests anywhere above the files); a deleted test never counts"
```

The changed test calls the changed function, but because its name does not correspond
(`test_api.py` vs `dates.py`) the bugfix scores 0 / fail.

**AFTER**: [same command, post-change] OR [verbatim excerpt of the new content]

**DELTA**: [one sentence — what a user can now do that they could not before]

**WITNESS**: [who ran it and when — derived from `memory/event-trace/Txxx.jsonl`, never the
implementing agent alone]
