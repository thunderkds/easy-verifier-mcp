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
| Verification command run | ☐ pass / ☐ fail | [paste actual output] |
| Negative cases hold | ☐ pass / ☐ fail | |
| verify | ☐ pass / ☐ fail / ☐ N/A | [what was observed — must literally state "pass" or "fail" here too, e.g. "skill run, feature confirmed working — pass": the merge gate scans this Notes column for the word "pass", not just the Result column] |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☐ pass / ☐ fail | [what was reviewed vs. skipped, and why] |
| Full smoke suite still green (no regression) | ☐ pass / ☐ fail | |
| **UI: Visual regression (diff or verdict pasted)** | ☐ pass / ☐ fail / ☐ N/A | [screenshot path or LLM verdict — required for UI tasks, Hard-Stop Gate 6] |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☐ pass / ☐ fail / ☐ N/A | [method used + output] |
| **UI: Responsiveness at target viewports** | ☐ pass / ☐ fail / ☐ N/A | [viewports tested, any overflow findings] |

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

**AFTER**: [same command, post-change] OR [verbatim excerpt of the new content]

**DELTA**: [one sentence — what a user can now do that they could not before]

**WITNESS**: [who ran it and when — derived from `memory/event-trace/Txxx.jsonl`, never the
implementing agent alone]
