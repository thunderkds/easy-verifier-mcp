# TASK_REVIEW — T109: change-risk slice 1

> Sibling of `tasks/TASK_GUIDE_T109.md`. Everything here is **filled by the reviewer at Stage
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

**BEFORE** (captured 2026-10-16T13:00:08+00:00 on `feat/T109-change-kind-gate` at `20470ea`, before any implementation commit; synthetic git repo, one commit `add: swap operands` changing `src/calc.py` with no kind signal, so the detected kind is `feature`; MCP called in-process through `mcp_server.mcp.call_tool("score", ...)`, CLI through `python -m easy_verifier.adapters.cli`):

```
captured: 2026-10-16T13:00:08+00:00
MCP score(scope=changes): change_risk.kind = rating_abstention | change_kind = {"value": "feature", "source": "detected"}
MCP needs_input keys: ['gate_evaluations'] | needs_input.change_kind present: False
CLI score --agent-input {"change_kind": {"value": "bugfix", "reason": "swaps operands to fix a wrong sum"}} -> exit 2
CLI stderr: validation error: agent input: 1 error(s): change_kind: unknown key; only picks, packs, gate_evaluations, registry_entries, reviews, improvements, batches and summary are accepted
```

**AFTER** (captured 2026-10-16T13:20:50+00:00 at `6870c59`, same script and synthetic repo shape as BEFORE):

```
captured: 2026-10-16T13:20:50+00:00
MCP score(scope=changes): change_risk.kind = rating_abstention | change_kind = {"value": "feature", "source": "detected"}
MCP needs_input keys: ['change_kind', 'gate_evaluations'] | needs_input.change_kind present: True
CLI score --agent-input {"change_kind": {"value": "bugfix", "reason": "swaps operands to fix a wrong sum"}} -> exit 0
CLI change_kind: {"value": "bugfix", "source": "confirmed", "reason": "swaps operands to fix a wrong sum", "rejected": null} | change_risk.kind = rating | rule: [('bugfix_without_regression_test', False)]
```

AC6 real repo (node-monorepo, `--scope changes --ref 09be767d0`; CLI via `python -m easy_verifier.adapters.cli score ... --agent-input <file>`, MCP via the stdio server `python -m easy_verifier.adapters.mcp_server` driven by `mcp.client.stdio` per `.claude/skills/verify/SKILL.md`; `EASY_VERIFIER_REPORTS_DIR` under `.local/t109/`):

```
captured: 2026-10-16T13:19:56+00:00
[10.5s] CLI exit 0
CLI (no answer): change_risk.kind=rating value=0 | change_kind={"value": "bugfix", "source": "detected", "reason": null, "rejected": null} | rules=[["bugfix_without_regression_test", 0, false]]
CLI (no answer): signals=[{"source": "commit subject", "value": "09be767d Bugfix/ Update condition time range", "kind": "bugfix"}]
CLI needs_input present: False
[10.5s] CLI exit 0
CLI --agent-input bugfix: change_risk.kind=rating value=0 | change_kind={"value": "bugfix", "source": "confirmed", "reason": "the commit corrects existing behaviour in one source file", "rejected": null} | rules=[["bugfix_without_regression_test", 0, false]]
CLI --agent-input bugfix: signals=[{"source": "commit subject", "value": "09be767d Bugfix/ Update condition time range", "kind": "bugfix"}]
[12.5s] MCP stdio score (no answer)
MCP (no answer): change_risk.kind=rating value=0 | change_kind={"value": "bugfix", "source": "detected", "reason": null, "rejected": null} | rules=[["bugfix_without_regression_test", 0, false]]
MCP (no answer): signals=[{"source": "commit subject", "value": "09be767d Bugfix/ Update condition time range", "kind": "bugfix"}]
MCP needs_input.change_kind: {"proposal": "bugfix", "allowed": ["bugfix", "feature", "refactor", "chore"], "signals_omitted": 0} | instructions: The engine detected this change's kind from the signals listed (branch name, commit subjec...
[10.8s] MCP stdio score (agent_input.change_kind bugfix)
MCP agent_input bugfix: change_risk.kind=rating value=0 | change_kind={"value": "bugfix", "source": "confirmed", "reason": "the commit corrects existing behaviour in one source file", "rejected": null} | rules=[["bugfix_without_regression_test", 0, false]]
MCP agent_input bugfix: signals=[{"source": "commit subject", "value": "09be767d Bugfix/ Update condition time range", "kind": "bugfix"}]
MCP needs_input.change_kind after answer: False
CLI == MCP (with answer, byte-equal sorted JSON, needs_input/registry_notes excluded): True
CLI == MCP (no answer): True
```

**DELTA**: MCP `score` now asks `needs_input.change_kind` (proposal + signals + allowed + instructions), and the same `{value, reason}` answer through MCP or CLI `--agent-input` replaces the detected kind (`source: "confirmed"`, reason shown) and the rule follows it: detected `feature` abstained, confirmed `bugfix` applies `bugfix_without_regression_test` (fails); CLI and MCP payloads byte-equal on the real repo with and without the answer.

**WITNESS**: backend-developer agent (T109), 2026-10-16 13:00 UTC (BEFORE) and 13:19-13:21 UTC (AFTER + AC6), worktree `feat/T109-change-kind-gate`; Stage 4/5 reviewer to re-run.
