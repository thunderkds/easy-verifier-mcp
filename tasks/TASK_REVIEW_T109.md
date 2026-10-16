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

**AFTER**: [same command, post-change]

**DELTA**: [one sentence]

**WITNESS**: [who ran it and when]
