# TASK_REVIEW — T110: change-risk slice 1

> Sibling of `tasks/TASK_GUIDE_T110.md`. Everything here is **filled by the reviewer at Stage
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

**BEFORE** (captured 2026-10-16T13:24:34Z on `feat/T110-change-kind-rules` at `1cec676`, before any implementation commit; python-ml `684ebb4` "feat: show off-topic refusal message in Streamlit chat and sidebar", 3 changed source files, no test; command `python -m easy_verifier.adapters.cli score --repo <real-repos>/python-ml --scope changes --ref 684ebb4 < /dev/null`, `EASY_VERIFIER_REPORTS_DIR` outside the worktree; `change_risk` headline verbatim):

```
{"kind": "rating_abstention", "dimension": "change-risk", "reason_code": "all_metrics_abstained", "reason": "all declared rating metrics abstained", "coverage_floor": 1.0, "achieved_coverage": 1.0, "sources_missing": [], "failure": null, "unavailable_metrics": [["bugfix_without_regression_test", "rules for feature arrive in T110"]], "abstentions": [], "change_kind": {"value": "feature", "source": "detected", "signals": [{"source": "commit subject", "value": "684ebb44 feat: show off-topic refusal message in Streamlit chat and sidebar", "kind": "feature"}], "signals_omitted": 0}}
```

**AC6 pre-registered expectations** (written 2026-10-16 before any AC6 run; all on python-ml, `--scope changes --ref <hash>`, no agent input, so the kind is the detected one):

| # | Case | Commit | Changed files (git show --name-status) | Expected `change_risk` |
|---|------|--------|------------------------------------------|------------------------|
| E1 | feature with tests | `8969d63` feat: add GoalSpec derivation, feasibility, and archetype resolution | A `src/core/profile/goal_spec.py`, A `tests/test_goal_spec.py` | kind feature; `rating` 100; `new_code_without_test_share` = 0.0 passed (≤ 0.20); bugfix/refactor rules not evaluated |
| E2 | feature without tests | `684ebb4` (the BEFORE commit) | M `src/ui/components/chat.py`, `src/ui/components/sidebar.py`, `src/ui/copy.py` | kind feature; `rating` 0; `new_code_without_test_share` = 1.0 failed, citing the 3 sources |
| E3 | refactor | `299fe50` refactor: use shared JSON_ONLY_INSTRUCTION in planning and research prompts | M `src/core/subgraphs/planning/planning_agent.py`, M `src/core/subgraphs/research/prompts.py` | kind refactor; `rating` 50; `refactor_tests_deleted` = 0 passed; `refactor_uncovered_share` = 0.5 failed (planning_agent.py covered by the repository's `tests/test_planning_agent.py`; `research/prompts.py` has no `test_prompts.py`), citing `src/core/subgraphs/research/prompts.py` |
| E4 | docs-only (chore) | `77dab9c` docs: add formal task contract for supervisor pipeline | A `src/docs/task-design.md` | kind chore; `rating_abstention` all_metrics_abstained, every rule "chore: no test expectation" |

**AFTER**: [same command, post-change]

**DELTA**: [one sentence]

**WITNESS**: [who ran it and when]
