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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t081_change_check_guide.py` now pins the new text ("Reading a change score", "`change_risk`", "never averaged into `overall`") instead of the removed wording — accepted by Supervisor (it pinned exactly the text this task removes). Doc pin tests t018/t035/t100/t081/t071/t080/t024/t103/t072: `166 passed, 1 skipped in 45.53s` (agent) — pass |
| Verification command run | ☑ pass | `grep -rn "not penalised\|change score as partial" README.md docs/DOCKER_MCP_GUIDE.md docs/EVALUATION_GUIDE.md` → no match, exit=1 (agent) — pass |
| Negative cases hold | ☑ pass | Docs only: `git diff develop...HEAD -- src` empty; no private names (T100 guard green) — pass |
| verify | ☑ pass | Supervisor ran the README's CLI example verbatim (2026-10-16) on a throwaway repo (`fix/sum` branch, one-line bugfix, no test): exit 0, `change_risk` rating 0, kind `bugfix` `confirmed`, reason "swaps operands to fix a wrong sum", `bugfix_without_regression_test` failed — matches the documented behaviour. README section reviewed against T107–T110 review files: numbers and rule table accurate — pass |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | README § Checking a feature or bugfix, DOCKER_MCP_GUIDE § 5, EVALUATION_GUIDE (payload row + "Reading the change-risk headline"), test_t081 pins. code-review: P0/P1/P2 none — pass |
| Full smoke suite still green (no regression) | ☑ pass | No code change; every doc-pinning test passes (166 passed, 1 skipped) — pass |
| **UI: Visual regression (diff or verdict pasted)** | ☑ N/A | No UI |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☑ N/A | No UI |
| **UI: Responsiveness at target viewports** | ☑ N/A | No UI |

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
