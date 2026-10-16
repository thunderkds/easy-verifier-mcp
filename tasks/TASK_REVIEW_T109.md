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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t109_change_kind_gate.py` (44 tests; ImportError at collection before the code, exit 2). Supervisor re-run: `44 passed in 13.06s` — pass |
| Verification command run | ☑ pass | `ruff check src tests` → `All checks passed!`; T100 guard 16 passed (agent) — pass |
| Negative cases hold | ☑ pass | Supervisor real-repo run 2026-10-16 13:22 UTC, node-monorepo `--ref 09be767d0 --agent-input` with `{"value": "hotfix", "reason": "", "extra": 1}` → exit 0, kind stays `"bugfix"` / `"detected"`, rating 0, `rejected`: `change_kind.extra: unknown key; only value and reason are accepted`, `change_kind.value: must be one of bugfix, feature, refactor, chore`, `change_kind.reason: must be a non-empty string`. Secret-shaped reason redacted (t109 test) — pass |
| verify | ☑ pass | Agent AC6 through the real stdio MCP server + CLI (2026-10-16T13:19:56Z): MCP asks `needs_input.change_kind {proposal: bugfix, allowed: [bugfix, feature, refactor, chore]}`; answered → `source: confirmed`, question no longer asked; CLI `--agent-input` same; CLI == MCP True with and without the answer. AC5 override flips the rule both ways (t109 tests). Supervisor negative run above — pass |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Reviewed the 7-file src diff (+185/−8): `gate.parse_change_kind` (type-checked, bounded, unknown keys redacted, never raises), `change_kind_request`, score headline `reason`/`rejected`, synthesis → pipeline → change_risk pass-through, roles agent-input key, MCP adapter. Accepted 2 out-of-list test touches: T101 stub gains `change_kind_question = None` (pure presence); T069 test unchanged (message reworded to list `change_kind`). code-review: P0/P1/P2 none; P3: the report shows the confirmed source but not the agent's reason. Security (Medium): untrusted input validated before use, reason redacted, no model call (NFR-001) — pass |
| Full smoke suite still green (no regression) | ☑ pass | Agent: `3077 passed, 3 skipped in 452.06s`, exit 0 (a first run's 44 t013 errors were the agent's own log under `.local/`; re-run clean) — pass |
| **UI: Visual regression (diff or verdict pasted)** | ☑ N/A | No UI |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☑ N/A | No UI |
| **UI: Responsiveness at target viewports** | ☑ N/A | No UI |

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
