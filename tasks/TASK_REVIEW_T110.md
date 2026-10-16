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

**AC6 actual** (run after the expectations above, one at a time in the background, CLI `score --scope changes --ref <hash> < /dev/null`, repo path given as `<real-repos>/python-ml`; each block is the script output: start stamp + worktree commit, exit code, `change_risk` headline fields, the rated inputs, the unavailable list, and each measured derivation clipped at 400 chars):

E1:
```
E1 8969d63 start 2026-10-16T13:44:22Z at 3841954
exit 0
kind=rating value=100 change_kind=feature/detected
  input new_code_without_test_share 0.0 passed=True ['tests/test_goal_spec.py']
  unavailable []
  derivation new_code_without_test_share : 0 of 1 changed source file(s) have no matched test: none; matched: src/core/profile/goal_spec.py -> tests/test_goal_spec.py; a test file counts when it is added or changed in this change and its name is a conventional test name of the changed source file in the same project (test-strategy's correspondence); a deleted test never counts
```
E2:
```
E2 684ebb4 start 2026-10-16T13:44:30Z at 3841954
exit 0
kind=rating value=0 change_kind=feature/detected
  input new_code_without_test_share 1.0 passed=False ['src/ui/components/chat.py', 'src/ui/components/sidebar.py', 'src/ui/copy.py']
  unavailable []
  derivation new_code_without_test_share : 3 of 3 changed source file(s) have no matched test: src/ui/components/chat.py, src/ui/components/sidebar.py, src/ui/copy.py; matched: none; a test file counts when it is added or changed in this change and its name is a conventional test name of the changed source file in the same project (test-strategy's correspondence); a deleted test never counts
```
E3:
```
E3 299fe50 start 2026-10-16T13:44:37Z at 3841954
exit 0
kind=rating value=50 change_kind=refactor/detected
  input refactor_tests_deleted 0 passed=True ['src/core/subgraphs/planning/planning_agent.py', 'src/core/subgraphs/research/prompts.py']
  input refactor_uncovered_share 0.5 passed=False ['src/core/subgraphs/research/prompts.py']
  unavailable []
  derivation refactor_tests_deleted : 0 test file(s) deleted by the change: none (git diff --name-status -M: a rename git detects is not a deletion); cited are the changed files read
  derivation refactor_uncovered_share : 1 of 2 changed source file(s) have no covering test in the repository: src/core/subgraphs/research/prompts.py; covered: src/core/subgraphs/planning/planning_agent.py -> tests/test_planning_agent.py; a test covers when its name is a conventional test name of the source file in the same project, wherever it sits in the working tree and whether or not the change touched it; a deleted test never cover
```
E4:
```
E4 77dab9c start 2026-10-16T13:44:44Z at 3841954
exit 0
kind=rating_abstention value=None change_kind=chore/detected
  unavailable [['bugfix_without_regression_test', 'chore: no test expectation'], ['new_code_without_test_share', 'chore: no test expectation'], ['refactor_tests_deleted', 'chore: no test expectation'], ['refactor_uncovered_share', 'chore: no test expectation']]
```

Verdict: E1–E4 all match the pre-registered expectations (E1 100 pass; E2 0, share 1.0, 3 sources cited; E3 50, deleted 0 pass, uncovered 0.5 fail citing `research/prompts.py`; E4 chore abstains, every rule "chore: no test expectation").


**AFTER** (2026-10-16T13:44:30Z, same command on `3841954`; `change_risk` headline verbatim):

```
{"kind": "rating", "dimension": "change-risk", "value": 0, "inputs": [{"metric_name": "new_code_without_test_share", "metric_value": 1.0, "weight": 25, "threshold": 0.2, "comparison": "at_most", "passed": false, "earned_weight": 0, "computed_from": ["src/ui/components/chat.py", "src/ui/components/sidebar.py", "src/ui/copy.py"], "metric_citation": [{"label": "ISO/IEC/IEEE 29119-2:2021 (test processes, test environment)", "url": "https://www.iso.org/standard/79428.html"}], "threshold_citation": "project-default", "source_tag": "curated", "area": "Test strategy, coverage, false confidence, isolation"}], "unavailable_metrics": [], "method": "round once to the nearest integer using Python round (ties to even): 100 * sum(earned_weight) / sum(weight) over numeric available rule metrics; a met threshold earns its full declared weight and an unmet threshold earns zero", "change_kind": {"value": "feature", "source": "detected", "signals": [{"source": "commit subject", "value": "684ebb44 feat: show off-topic refusal message in Streamlit chat and sidebar", "kind": "feature"}], "signals_omitted": 0}}
```

**DELTA**: the same feature commit no longer abstains with "rules for feature arrive in T110"; it is rated 0 by `new_code_without_test_share` = 1.0 (3 of 3 changed sources without a matched test, each cited), and the bugfix/refactor rules are not evaluated.

**WITNESS**: [who ran it and when]
