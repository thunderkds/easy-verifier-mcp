# TASK_REVIEW — T066: Improvement plan (agent)

> Sibling of `tasks/TASK_GUIDE_T066.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☐ pass / ☐ fail | [test file path(s) — required before Done] |
| Verification command run | ☑ pass | Supervisor re-run: full suite **1664 passed, 2 skipped, 2 failed** (2 = known stale-Docker container tests, fail on clean `develop` too); ruff All checks passed — pass |
| Negative cases hold | ☑ pass | Supervisor MCP stdio on bryony copy: `write_report` with `security/no_such_metric` → `isError: True`, "1 improvement error(s): improvements[0]: security/no_such_metric is not an item of the improvement plan; items: …"; report count 4 → 5 across both calls (bad call wrote nothing) — pass |
| verify | ☑ pass | `verify` run by Supervisor 2026-10-03 09:23 UTC: MCP `score` → `write_report` with 3 P1 overrides on a scratch copy of bryony (`bryony-T066`, real bryony untouched). Report: agent labels 3, engine labels 10, raw `FAKEfake9Qx7…` 0 (rendered `sess…****:3ee04d1a1ad9`), raw `<script>x` 0, escaped 1 — feature confirmed working — pass |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Reviewed `core/improve.py` (validate_improvements, item_keys, error types), `core/report.py` (write_report wiring, plan item render, CSS), `core/roles.py` (agent-input key list), `adapters/mcp_server.py` (tool description), new test file. code-review: P0 0, P1 0, P2 0, P3 1 (`score` accepts `improvements` and ignores them — harmless since the score payload renders no agent text; noted). Security (Medium, manual): new agent-text egress goes redact → escape via `ctx.agent_text`; error echoes redacted + capped; validation before any disk write — pass |
| Full smoke suite still green (no regression) | ☑ pass | 1664 passed (T065 base 1631 + 33 new), only the 2 pre-existing container failures — pass |
| **UI: Visual regression (diff or verdict pasted)** | ☑ pass | `/tmp/claude-1000/-home-hungnguyenhuu-workspace-pets-hungnguyen111-easy-verifier-mcp/4b78de6f-bc95-4225-acbd-da02da5664de/scratchpad/t066/agent_fix_1280.png` — LLM-vision verdict (Supervisor): P1 rows show agent text with amber AGENT pill above the engine line with purple ENGINE pill; P2 Evidence now a collapsed "Why not measured" block; secret shown redacted, script tag shown as text — pass |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☑ pass | CSS audit: reuses `.suggestion` styling; new `.fix-source-agent` amber #ffb800 is the report's existing amber accent; muted engine line #9a9ac0 — pass |
| **UI: Responsiveness at target viewports** | ☑ pass | 1280 and true 400px (iframe; headless Chrome's minimum window is 500px): `/tmp/claude-1000/-home-hungnguyenhuu-workspace-pets-hungnguyen111-easy-verifier-mcp/4b78de6f-bc95-4225-acbd-da02da5664de/scratchpad/t066/agent_fix_400.png`, `plan_400_unscrolled.png`; page width 385, no horizontal page scroll, table scrolls inside `.plan-table`; agent text wraps with `overflow-wrap: break-word` — pass |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE** (captured by backend-developer on `feat/T066-improvement-overrides` at `bf265f1`, before any implementation commit). Probe: `/tmp/claude-1000/-home-hungnguyenhuu-workspace-pets-hungnguyen111-easy-verifier-mcp/4b78de6f-bc95-4225-acbd-da02da5664de/scratchpad/t066/probe.sh` (run as `/tmp/claude-1000/-home-hungnguyenhuu-workspace-pets-hungnguyen111-easy-verifier-mcp/4b78de6f-bc95-4225-acbd-da02da5664de/scratchpad/t066/probe.sh > /tmp/claude-1000/-home-hungnguyenhuu-workspace-pets-hungnguyen111-easy-verifier-mcp/4b78de6f-bc95-4225-acbd-da02da5664de/scratchpad/t066/before.txt 2>&1`), target = scratchpad copy of bryony (`rsync -a --exclude=/reports /home/hungnguyenhuu/workspace/project/bryony/bryony/ /tmp/claude-1000/-home-hungnguyenhuu-workspace-pets-hungnguyen111-easy-verifier-mcp/4b78de6f-bc95-4225-acbd-da02da5664de/scratchpad/bryony-T066/`), findings `[]`, agent input `/tmp/claude-1000/-home-hungnguyenhuu-workspace-pets-hungnguyen111-easy-verifier-mcp/4b78de6f-bc95-4225-acbd-da02da5664de/scratchpad/t066/agent_input.json`:

```json
{"improvements": [{"dimension": "architecture", "metric_name": "decision_records_missing", "suggestion": "Start docs/adr/ in bryony with ADR-0001 recording why nodes/ and backend/ are separate deployables."}]}
```

Today the override is rejected as an unknown agent-input key, and the only way to get a report is without it, where every fix is labelled engine:

```
Sat Oct  3 09:10:13 AM UTC 2026
$ cd /home/hungnguyenhuu/workspace/pets/hungnguyen111/easy-verifier-mcp-T066 && PYTHONPATH=src /home/hungnguyenhuu/workspace/pets/hungnguyen111/easy-verifier-mcp/.venv/bin/python -m easy_verifier.adapters.cli write-report --repo /tmp/claude-1000/-home-hungnguyenhuu-workspace-pets-hungnguyen111-easy-verifier-mcp/4b78de6f-bc95-4225-acbd-da02da5664de/scratchpad/bryony-T066 --scope project --findings /tmp/claude-1000/-home-hungnguyenhuu-workspace-pets-hungnguyen111-easy-verifier-mcp/4b78de6f-bc95-4225-acbd-da02da5664de/scratchpad/t066/findings.json --agent-input /tmp/claude-1000/-home-hungnguyenhuu-workspace-pets-hungnguyen111-easy-verifier-mcp/4b78de6f-bc95-4225-acbd-da02da5664de/scratchpad/t066/agent_input.json </dev/null
validation error: agent input: 1 error(s): improvements: unknown key; only picks, gate_evaluations, registry_entries and reviews are accepted
exit=2
$ ls /tmp/claude-1000/-home-hungnguyenhuu-workspace-pets-hungnguyen111-easy-verifier-mcp/4b78de6f-bc95-4225-acbd-da02da5664de/scratchpad/bryony-T066/reports; grep -o fix-source\">[a-z]*< <latest report> | sort | uniq -c
ls: cannot access '/tmp/claude-1000/-home-hungnguyenhuu-workspace-pets-hungnguyen111-easy-verifier-mcp/4b78de6f-bc95-4225-acbd-da02da5664de/scratchpad/bryony-T066/reports': No such file or directory
Sat Oct  3 09:10:14 AM UTC 2026
--- same call without --agent-input (no way to attach a suggestion today): every fix is labelled engine
$ cd /home/hungnguyenhuu/workspace/pets/hungnguyen111/easy-verifier-mcp-T066 && PYTHONPATH=src /home/hungnguyenhuu/workspace/pets/hungnguyen111/easy-verifier-mcp/.venv/bin/python -m easy_verifier.adapters.cli write-report --repo /tmp/claude-1000/-home-hungnguyenhuu-workspace-pets-hungnguyen111-easy-verifier-mcp/4b78de6f-bc95-4225-acbd-da02da5664de/scratchpad/bryony-T066 --scope project --findings /tmp/claude-1000/-home-hungnguyenhuu-workspace-pets-hungnguyen111-easy-verifier-mcp/4b78de6f-bc95-4225-acbd-da02da5664de/scratchpad/t066/findings.json </dev/null
{
  "path": "reports/evidence-report-project-20261003T091023-101957Z.html",
  "advisory": "Sensitivity notice: this report is written inside the evaluated repository, so it can be committed to version control, attached to a ticket, or pasted into a pull request \u2014 and in MCP mode the same evidence also reaches the calling agent, which may be a hosted model outside your control. Secrets detected while gathering evidence are replaced by non-reversible fingerprints before they reach this document, but excerpts still quote real source code and file paths from this repository. Review before sharing it anywhere either destination can carry it."
}
exit=0
$ grep -o 'fix-source">[a-z]*<' /tmp/claude-1000/-home-hungnguyenhuu-workspace-pets-hungnguyen111-easy-verifier-mcp/4b78de6f-bc95-4225-acbd-da02da5664de/scratchpad/bryony-T066/reports/evidence-report-project-20261003T091023-101957Z.html | sort | uniq -c
     10 fix-source">engine<
Sat Oct  3 09:10:23 AM UTC 2026

[exited with code 0]
```

**AFTER** (Supervisor, MCP stdio, branch HEAD `577075d`, bryony scratch copy):

```
Sat Oct  3 09:23:35 AM UTC 2026
unknown item -> isError: True | Error executing tool write_report: 1 improvement error(s): improvements[0]: security/no_such_metric is not an item of the improvement plan; items: architecture/decision_records_missing, ...
write_report -> False reports/evidence-report-project-20261003T092406-323006Z.html
agent labels: 3  engine: 10  secret raw: 0  raw script: 0  escaped script: 1
```

**DELTA**: the calling LLM agent can now attach a repo-specific fix to any improvement-plan item through `write_report`; the report shows it labelled agent above the engine line, and an unknown/duplicate item is rejected before anything is written.

**WITNESS**: Supervisor (main session), 2026-10-03 09:23 UTC — independent MCP run on a bryony copy and full-suite re-run; not the implementing agent alone.
