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


**AFTER** (README.md, new section "Reading a change score (2026-10-16)", first lines):

> **Reading a change score (2026-10-16).** A `changes` or `worktree` score has two headlines:
> `overall`, the mean of the repository-health dimensions that could be rated, and `change_risk`, a
> separate rating of the change itself. `change_risk` is never averaged into `overall`. It is rated
> only at `changes` and `worktree` scope; at `project` and `task` scope it abstains with a stated
> reason. Read both numbers.
>
> Also covers: change-kind detection and MCP/CLI (`--agent-input <file>`) confirmation, the FR-082
> rule table, repository-wide context roles, and the node-monorepo example (overall 97 -> 85,
> `change_risk` 0). `docs/EVALUATION_GUIDE.md` gains "Reading the change-risk headline";
> `docs/DOCKER_MCP_GUIDE.md` section 5 now agrees. `tests/test_t081_change_check_guide.py` pins updated
> (they asserted the removed "not penalised" wording).

**DELTA**: the docs no longer say a bugfix without a test "is not penalised" or quote 97 as the change score; they explain the separate `change_risk` headline, kind detection and confirmation, the rule table, and the measured 97 -> 85 / `change_risk` 0 example.

**WITNESS**: backend-developer agent (T111), 2026-10-16; `grep` exit=1 and 166 pytest passed, 1 skipped (py3.12 venv).
