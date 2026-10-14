# TASK_REVIEW — T067: Evidence floor

> Sibling of `tasks/TASK_GUIDE_T067.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t067_evidence_floor.py` (33 tests: floor 45 abstains / 50 rated / floor 0.51 makes 50 abstain; measured_share + unmeasured rules round-trip; gates only no_static_rule + borderline; evidence-lack gate_evaluations rejected naming the dimension; GatedRating refuses evidence-lack; warnings payload; plan abstained line lists unmeasured; report warning block; overall with fewer contributors). Updated tests cite DDR-0010: test_t028_evaluate_gate, test_judge, test_t065, test_t066, test_score_operation. New tests fail on pre-change source (agent) — pass |
| Verification command run | ☑ pass | Supervisor 2026-10-03 15:10 UTC node-monorepo CLI: overall 67; code-quality `insufficient_measured_weight` 0.20; warnings: blast-radius (4 unmeasured), code-quality (5 unmeasured), requirement-fidelity (below_coverage_floor; requirements-doc/spec-doc/task-breakdown not found) — pass |
| Negative cases hold | ☑ pass | MCP gate round on node-monorepo (agent): only solution-fit asked; evaluation for code-quality rejected "never agent-rated … (DDR-0010)"; solution-fit accepted agent-rated 70; code-quality stays abstention — pass |
| verify | ☑ pass | Supervisor drove CLI on node-monorepo (above); agent drove MCP stdio gate round + fullstack-ts before/after (code-quality 67→abstain 0.45, test-strategy 100→abstain 0.30, overall 68→58, both explained: whole-set metrics abstained on byte-budget truncation). CLI/MCP byte-equal excluding needs_input/registry_notes — feature confirmed working — pass |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Reviewed judge.py (floor, reason, EVIDENCE_LACK_REASONS, measured_share derived from unavailable_metrics, validators), gate.py (gate only no_static_rule/borderline; refuse evidence-lack evaluations), score.py warnings, improve.py unmeasured lines, report.py warning block, tests. code-review: P0 0, P1 0, P2 1 (pre-existing 'Context warnings' banner overflows at 400px — not from this change, follow-up), P3 1 (MCP score tool description wording). Security (manual): no new egress of agent text; warnings render engine text via esc — pass |
| Full smoke suite still green (no regression) | ☑ pass | Supervisor re-run: 1697 passed, 2 skipped, 2 failed (the 2 known stale-Docker container tests, failing on develop too); ruff All checks passed — pass |
| **UI: Visual regression (diff or verdict pasted)** | ☑ pass | `<scratchpad>/t067_report_1280.png` — LLM-vision verdict (Supervisor): 'Evidence warnings — no number given' block above Quality score, red-edged banner, each dimension with reason and unmeasured rules — pass |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☑ pass | reuses `warning-banner` / `miss-list` classes, no new colours — pass |
| **UI: Responsiveness at target viewports** | ☑ pass | `<scratchpad>/t067_report_400.png` (true 400px iframe): new block fits 349/349px; page-level horizontal scroll 522/385 comes from the pre-existing 'Context warnings' banner and is identical on pre-change source — new block pass; pre-existing overflow logged as follow-up |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE**: captured by backend-developer on `fix/T067-evidence-floor` at HEAD `d98ac4d` (no implementation commit yet). Command: `PYTHONPATH=src .venv/bin/python -m easy_verifier.adapters.cli score --repo <real-repos>/node-monorepo --scope project </dev/null | python3 -c '...print dimension, value/reason_code, inputs (metric, weight), len(unavailable_metrics)...'`

```
Sat Oct  3 02:49:24 PM UTC 2026
d98ac4d
architecture 50 [('architecture_description_missing', 30), ('decision_records_missing', 30)] 1
blast-radius all_metrics_abstained [] 4
code-quality 100 [('lint_config_missing', 10), ('format_config_missing', 10)] 5
requirement-fidelity below_coverage_floor [] 0
security 50 [('redaction_hits_observed', 35), ('sink_hits_observed', 35), ('lockfile_missing', 15), ('cookie_flags_missing_observed', 15)] 0
solution-fit no_static_rule [] 0
test-strategy 100 [('assertion_density_per_test', 20), ('test_config_and_ci_missing', 20), ('tests_without_assertions_share', 15), ('skipped_test_share', 10), ('network_calls_in_unit_tests_observed', 10)] 1
```

code-quality is rated **100** from only 2 measured inputs (lint_config_missing 10 + format_config_missing 10 = 20 weight) while 5 rule metrics were unavailable.

**AFTER**: same command, captured by backend-developer on fix/T067-evidence-floor (implementation commits present):

```
Sat Oct  3 03:07:42 PM UTC 2026
287efc5
architecture 50 [('architecture_description_missing', 30), ('decision_records_missing', 30)] 1
blast-radius all_metrics_abstained [] 4
code-quality insufficient_measured_weight [] 5
requirement-fidelity below_coverage_floor [] 0
security 50 [('redaction_hits_observed', 35), ('sink_hits_observed', 35), ('lockfile_missing', 15), ('cookie_flags_missing_observed', 15)] 0
solution-fit no_static_rule [] 0
test-strategy 100 [('assertion_density_per_test', 20), ('test_config_and_ci_missing', 20), ('tests_without_assertions_share', 15), ('skipped_test_share', 10), ('network_calls_in_unit_tests_observed', 10)] 1
overall 67 | warnings: [('blast-radius', 'all_metrics_abstained', None), ('code-quality', 'insufficient_measured_weight', '0.20'), ('requirement-fidelity', 'below_coverage_floor', None)]
```

MCP `score` on node-monorepo, pre-change source (d98ac4d) vs. this branch (call 2 carries `agent_input.picks = {}`, so the gate round is asked):

```
before call1 needs_input keys: ['picks', 'reference']
before call2 gate_evaluations asked: [('blast-radius', 'abstained'), ('requirement-fidelity', 'abstained'), ('solution-fit', 'abstained')]
after call1 needs_input keys: ['picks', 'reference']
after call2 gate_evaluations asked: [('solution-fit', 'abstained')]
after CLI == MCP payload (needs_input/registry_notes excluded): True
after replay old evaluation for code-quality -> Error executing tool score: agent input: 1 error(s): gate_evaluations.code-quality: the rules abstained insufficient_measured_weight for missing evidence; that is reported as a warning and is never agent-rated, so no evaluation is accepted for it (DDR-0010)
after solution-fit evaluated -> agent_rated 70 = agent 70 (confidence 0.5; rules abstained: no_static_rule) | code-quality stays rating_abstention insufficient_measured_weight
after overall: 4 of 7 dimensions contributed (3 rule-rated, 0 blended, 1 agent-rated); ratings average contributors only, so abstention
```

**DELTA**: code-quality on node-monorepo is no longer a confident 100 built from 20% of its rule weight: it abstains `insufficient_measured_weight` (measured_share 0.20) and is shown as a warning listing the five unmeasured rules, and the MCP gate now asks the agent only about solution-fit instead of also inviting it to invent numbers for blast-radius and requirement-fidelity.

**WITNESS**: Supervisor (main session), 2026-10-03 15:10 UTC — independent node-monorepo CLI run and full-suite re-run; not the implementing agent alone.
