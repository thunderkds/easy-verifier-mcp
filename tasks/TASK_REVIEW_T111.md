# TASK_REVIEW — T111: change-risk docs

> Sibling of `tasks/TASK_GUIDE_T111.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☐ pass / ☐ fail / ☐ N/A | |
| Verification command run | ☐ pass / ☐ fail / ☐ N/A | |
| Negative cases hold | ☐ pass / ☐ fail / ☐ N/A | |
| verify | ☐ pass / ☐ fail / ☐ N/A | |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☐ pass / ☐ fail / ☐ N/A | |
| Full smoke suite still green (no regression) | ☐ pass / ☐ fail / ☐ N/A | |
| **UI: Visual regression (diff or verdict pasted)** | ☐ N/A | No UI |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☐ N/A | No UI |
| **UI: Responsiveness at target viewports** | ☐ N/A | No UI |

---

## Demonstration

**BEFORE** (verbatim, README.md before T111):

> **Read a change score as partial (2026-10-05).** The `changes` scope narrows which files are read,
> but most rules are still repository-health rules:
> - test-strategy and security usually abstain (`below_coverage_floor`): their test config, CI and
>   lockfile are not in the diff. A bugfix without a regression test is **not penalised**; the gap
>   only shows in `sources_missing` as "no test discovered for N file(s)".
> - architecture rates the repository's documents, not the change.
> - blast-radius `max_fan_in_changed` abstains when the reference sweep stops at its file ceiling.
>
> Example: a one-file node-monorepo bugfix with no test scored 97 (architecture 90, code-quality 100,
> blast-radius 100; test-strategy, security and requirement-fidelity abstained). Read
> `overall.abstentions` and `warnings` before trusting the number.


**AFTER**: [verbatim new section excerpt]

**DELTA**: [one sentence]

**WITNESS**: [who ran it and when]

