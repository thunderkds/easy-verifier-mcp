# TASK_REVIEW — T065: Improvement plan (engine)

> Sibling of `tasks/TASK_GUIDE_T065.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t065_improvement_plan.py` (18 tests: shape, P0/P1, threshold 0, at_most direction, rounding tie, P2 range with negative low, ordering, P2 by high end, gated rules basis, non-gated final basis, abstained dimension, agent-rated, all met, overall abstention, FIX_HINTS covers every RATING_RULES metric, score payload, report group order + ENGINE label, "No gaps"); `tests/integration/test_adapter_parity.py` (+improvement_plan byte-equal); `tests/test_score_operation.py` (key sets). Supervisor re-run: `PYTHONPATH=src …/.venv/bin/python -m pytest tests/test_t065_improvement_plan.py tests/test_judge.py tests/test_score_operation.py -q` → **108 passed in 1.98s** — pass |
| Verification command run | ☑ pass | Supervisor 2026-10-03 08:38 UTC: CLI + MCP stdio `score` on node-monorepo (`--scope project`), both exit 0, `plan byte-equal: True`, overall 75. P1: architecture decision_records_missing +50/+13; security redaction_hits_observed +35/+9; security cookie_flags_missing_observed +15/+4. P2: 7 items with ranges (e.g. top_level_import_cycles [-5,+5] overall). Abstained: blast-radius all_metrics_abstained, requirement-fidelity below_coverage_floor, solution-fit no_static_rule. Hand check (Supervisor): cookie fix → security 65 → (50+100+65+100)/4=78.75→79 = +4 ✓; agent's check: decision records 87.5→88 = +13 (a real-repo rounding tie) — pass |
| Negative cases hold | ☑ pass | threshold 0 never P0; abstained/agent-rated dimension → reason line, no items; overall abstention → no items; rule without hint fails test; agent sabotage runs (P0 always true/false, weight-share gain, reversed order, blended basis) each turned the suite red — pass |
| verify | ☑ pass | `verify` skill run by Supervisor: CLI and MCP adapters driven on real repo node-monorepo, plan present and byte-equal across adapters; HTML report section inspected (P0→P1→P2, ENGINE labels, collapsible cited files) — feature confirmed working — pass |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Reviewed `core/improve.py` (new), `core/judge.py` (rating_value/overall_value extraction only — no rule/weight/threshold/band change), `core/score.py` (property + to_dict), `core/report.py` (new section + CSS), the 3 test files, `docs/SCORING_FLOW.md`. Callers of rate/rate_overall covered by `tests/test_judge.py`. code-review: P0 0, P1 0, P2 1 (long P2 abstention reasons inline in the report — suggestion, not applied), P3 0. Security (Medium, manual — built-in needs origin/HEAD): no new egress; all engine text via `ctx.esc`, paths via existing `_render_ref`/`ctx.path` — pass |
| Full smoke suite still green (no regression) | ☑ pass | Supervisor re-run: **1631 passed, 2 skipped, 2 failed** (88s). Both failures (`test_container_parity_is_explicitly_verified`, `test_container_redaction_proof_is_not_silent_when_docker_is_missing`) are pre-existing: the container parity test fails identically on clean `develop` (stale local Docker image, unexpected `supply-chain` tool). ruff: All checks passed — pass |
| **UI: Visual regression (diff or verdict pasted)** | ☑ pass | Headless Chromium, network blocked: `<scratchpad>/plan_1280.png`. LLM-vision verdict (Supervisor): Improvement plan section after score panel; P0 'None.', P1 table 3 rows, P2 table; ENGINE pill on every fix; no break of existing panels — pass |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☑ pass | CSS audit of diff: only existing palette values (#1e1e42, #6b6b9a, #c084fc, rgba(168,85,247,.15) = existing .suggestion purple, #00ff88); headings/table typography match score panel — pass |
| **UI: Responsiveness at target viewports** | ☑ pass | 1280 / 768 / 400 px (`<scratchpad>/plan_{1280,768,400}.png`): at 400 the table scrolls inside `.plan-table`, page has no horizontal scroll — pass |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE** (captured by backend-developer on `feat/T065-improvement-plan` at `ebba8ff`, before any implementation commit; no `improvement_plan` key in the `score` payload):

```
Sat Oct  3 08:24:36 AM UTC 2026
$ cd <repo>-T065 && PYTHONPATH=src <repo>/.venv/bin/python -m easy_verifier.adapters.cli score --repo <real-repos>/node-monorepo --scope project </dev/null | python3 -c "import json,sys; p=json.load(sys.stdin); print(sorted(p), 'improvement_plan' in p)"
['detected_stack', 'metrics', 'overall', 'provenance', 'ratings'] False
exit=0
Sat Oct  3 08:24:46 AM UTC 2026
```

**AFTER** (Supervisor, same command, branch HEAD `76d441f`):

```
Sat Oct  3 08:39:12 AM UTC 2026
['detected_stack', 'improvement_plan', 'metrics', 'overall', 'provenance', 'ratings'] True
exit=0
Sat Oct  3 08:39:22 AM UTC 2026
```

**DELTA**: the owner of a scored repo now gets every unmet or unmeasured rule grouped P0/P1/P2 with its exactly recomputed gain and a fix line (e.g. node-monorepo: recording ADRs is worth +13 overall), in CLI/MCP JSON and the HTML report.

**WITNESS**: Supervisor (main session), 2026-10-03 08:38–08:39 UTC — independent CLI + MCP runs on node-monorepo and full-suite re-run; not the implementing agent alone.
