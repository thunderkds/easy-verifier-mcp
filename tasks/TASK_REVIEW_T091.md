# TASK_REVIEW — T091: Redaction masks ordinary paths whose name pieces mix letters then digits

> Sibling of `tasks/TASK_GUIDE_T091.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | pass | tests/test_t091_letter_digit_pieces.py |
| Verification command run | ☐ pass / ☐ fail | [paste actual output] |
| Negative cases hold | ☐ pass / ☐ fail | |
| verify | ☐ pass / ☐ fail / ☐ N/A | [what was observed — must literally state "pass" or "fail" here too, e.g. "skill run, feature confirmed working — pass": the merge gate scans this Notes column for the word "pass", not just the Result column] |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☐ pass / ☐ fail | [what was reviewed vs. skipped, and why] |
| Full smoke suite still green (no regression) | pass | Full suite after t046 fix: 2 failed (the 2 known container tests), 2648 passed, 2 skipped in 413.81s |
| **UI: Visual regression (diff or verdict pasted)** | ☐ pass / ☐ fail / ☐ N/A | [screenshot path or LLM verdict — required for UI tasks, Hard-Stop Gate 6] |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☐ pass / ☐ fail / ☐ N/A | [method used + output] |
| **UI: Responsiveness at target viewports** | ☐ pass / ☐ fail / ☐ N/A | [viewports tested, any overflow findings] |
| Repro loop | pass | `redact("tests/test_t087_third_party_exclusion.py")` -> `test…****:009fc5eee991.py` and t029 `test_every_tracked_path_of_this_repo_survives_redaction` failed on develop 94618c1 (2026-10-13T03:11Z); see Demonstration BEFORE |
| Regression test | pass | tests/test_t091_letter_digit_pieces.py (2 of 4 positives failed on develop; 5 negatives main-3f9a2b1c.js, xQzRtWvB.., 32-char mixed, interleaved a1b2.., base64url-ish still fingerprint); t029 now passes. Boundary tests added (abcdefg087 7-letter, Ab087 mixed-case). Sabotage: widened to `[A-Za-z]{1,30}[0-9]{1,8}` -> "2 failed, 9 passed" (both boundary tests failed); restored -> 11 passed. |
| Smoke suite | pass | t029/t046/t051/t053/t091: 160 passed. Real repos bryony redaction_hits_observed 11 -> 11, kitchd 62 -> 62; score JSON byte-identical before/after (cmp), so no hit disappeared |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE** (develop 94618c1, captured before any fix commit; trigger `redact('tests/test_t087_third_party_exclusion.py')` then `pytest -q tests/test_t029_redact_filenames.py`):

```
2026-10-13T03:11:00Z
test…****:009fc5eee991.py
E         
E         Left contains one more item: 'tests/test_t087_third_party_exclusion.py'
E         Use -v to get more diff

tests/test_t029_redact_filenames.py:66: AssertionError
=========================== short test summary info ============================
FAILED tests/test_t029_redact_filenames.py::test_every_tracked_path_of_this_repo_survives_redaction
1 failed, 17 passed in 0.47s
```

**AFTER**: `redact("tests/test_t087_third_party_exclusion.py")` returns the path unchanged; t029 file 18 passed. Real repos: bryony 11 -> 11, kitchd 62 -> 62 (byte-identical score JSON).

**DELTA**: Paths whose name pieces are a letter run then a digit run (`t087`, `v2`, `utf8`, `py3`) are no longer fingerprinted, so citations to them resolve and develop is green.

**WITNESS**: [who ran it and when — derived from `memory/event-trace/Txxx.jsonl`, never the
implementing agent alone]
