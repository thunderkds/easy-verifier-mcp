# TASK_REVIEW — T008: Security dimension

> Sibling of `tasks/TASK_GUIDE_T008.md`. Everything here is filled during Stage 4/5 review.

---

## Evidence

| Check | Result | Notes / output snippet |
|-------|--------|------------------------|
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☐ pass / ☐ fail | [test file path(s) — required before Done] |
| Verification command run | ☐ pass / ☐ fail | [paste actual output] |
| Negative cases hold | ☐ pass / ☐ fail | |
| verify | ☐ pass / ☐ fail / ☐ N/A | [what was observed — Notes must also state pass or fail] |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☐ pass / ☐ fail | [what was reviewed vs. skipped, and why] |
| Full smoke suite still green (no regression) | ☐ pass / ☐ fail | |
| **UI: Visual regression (diff or verdict pasted)** | ☒ N/A | Pure backend task; no UI exists in v1. |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☒ N/A | Pure backend task; no UI exists in v1. |
| **UI: Responsiveness at target viewports** | ☒ N/A | Pure backend task; no UI exists in v1. |

---

## Demonstration

**BEFORE**: 2026-08-19T03:09:11Z — `PYTHONPATH=src PATH=/home/hungnguyenhuu/workspace/pets/hungnguyen111/easy-verifier-mcp/.venv/bin:$PATH pytest tests/test_t008_security.py -q && python -m easy_verifier.adapters.cli security --repo . --scope project | head -30`

```text
ERROR: file or directory not found: tests/test_t008_security.py


no tests ran in 0.00s
```

Exit status: 4.

**AFTER**: [same command, post-change]

**DELTA**: [one sentence — what a user can now do that they could not before]

**WITNESS**: [who ran it and when — derived from `memory/event-trace/T008.jsonl`, never the implementing agent alone]
