# TASK_REVIEW — T069: Report summary

> Sibling of `tasks/TASK_GUIDE_T069.md`. Everything here is **filled by the reviewer at Stage
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

**BEFORE** (captured by backend-developer on `feat/T069-report-summary` at `ae77a8b`, before any code
change; `S=/tmp/claude-1000/-home-hungnguyenhuu-workspace-pets-hungnguyen111-easy-verifier-mcp/4b78de6f-bc95-4225-acbd-da02da5664de/scratchpad`):

```
$ rsync -a --exclude node_modules --exclude reports \
    /home/hungnguyenhuu/workspace/training/tien.nguyen/nestjs-training/coffee-shop-api/ $S/coffee-shop-api/
$ echo '[]' > $S/findings-empty.json
$ cd <worktree> && date -u && PYTHONPATH=src <main>/.venv/bin/python -m easy_verifier.adapters.cli \
    write-report --repo $S/coffee-shop-api --scope project --findings $S/findings-empty.json </dev/null > $S/before-out.json
Sun Oct  4 04:01:53 AM UTC 2026
exit=0
  "path": "reports/evidence-report-project-20261004T040154-307470Z.html",

$ date -u; grep -o '<h[12][^>]*>[^<]*' $S/coffee-shop-api/reports/*.html | head -12
Sun Oct  4 04:01:58 AM UTC 2026
<h1>Evidence report
<h2>Before you share this report
<h2>Context warnings
<h2>Evidence warnings — no number given
<h2>Quality score
<h2>Improvement plan
<h2>Checklist coverage
<h2>Dimensions
```

The report opens straight into warnings, then the score panel and the plan: there is no summary
section (the only "summary" strings in the file are `<details><summary>` toggles). A copy of this
report is kept at `$S/before-report.html`.

**AFTER** (backend-developer, worktree at the T069 implementation; same copy, same command, plus a
second run with `--agent-input $S/agent-summary.json` carrying an example `summary`):

```
$ date -u; PYTHONPATH=src <main>/.venv/bin/python -m easy_verifier.adapters.cli write-report \
    --repo $S/coffee-shop-api --scope project --findings $S/findings-empty.json </dev/null
Sun Oct  4 04:09:20 AM UTC 2026
exit=0   "path": "reports/evidence-report-project-20261004T040922-176546Z.html"
$ ... --agent-input $S/agent-summary.json </dev/null
exit=0   "path": "reports/evidence-report-project-20261004T040923-295583Z.html"

$ date -u; grep -o '<h[12][^>]*>[^<]*' <second report> | head -5
Sun Oct  4 04:09:28 AM UTC 2026
<h1>Evidence report
<h2>Before you share this report
<h2>Summary
<h2>Context warnings
<h2>Evidence warnings — no number given

Summary section, tags stripped:
Overall 65/100 — 2 of 7 dimensions rated: code-quality 71, security 59.
Not rated: solution-fit — no measurable static rule is declared for this dimension, so it is rated only at the evaluate gate.
Focus on these first
  - security: secret-shaped values in the code (redaction_hits_observed) — now 41, rule at most 0; worth +21 overall (security +41). Standard: CWE-798 Use of Hard-coded Credentials, OWASP ASVS 5.0.0 V13.3.1 (secrets management)
  - code-quality: highest function complexity (max_function_ccn) — now 25, rule at most 15; worth +9 overall (code-quality +17). Standard: McCabe 1976, A Complexity Measure, NIST SP 500-235 (Watson & McCabe 1996); threshold: NIST SP 500-235 (15 with justification)
  - code-quality: type checker not in strict mode (strict_type_config_missing) — now 1, rule at most 0; worth +5 overall (code-quality +11). Standard: ISO/IEC 5055:2021 (...), mypy configuration file, strict option, TypeScript TSConfig reference, strict; threshold: project default
Could not evaluate — add what each needs
  - architecture: not found: architecture-doc, decision-record
  - blast-radius: not measured: most imports of one changed module (fan-in), share of changed files in churn hotspots, public symbols removed (+1 more); not found: referencing files (...), git co-change history (...), repository change hotspots (...)
  - requirement-fidelity: not found: requirements-doc, task-breakdown
  - test-strategy: not measured: share of source files no test covers, assertions per test, share of tests without assertions (+1 more); not found: ci-workflow, source-to-test correspondence for files in the active scope
Hey, I checked your code: 2 of the 7 areas could be rated. The weak points I would fix first are the ones listed above, each tied to the rule and standard it comes from. For the areas that could not be rated, add the missing pieces listed under Could not evaluate and run the check again. [AGENT]

AC6 against the real BEFORE (summary removed; only the generated-at timestamp and the first-write
marker normalized, since the AFTER report is the second one in that reports/):
$ python3 $S/detail_diff.py $S/before-report.html <first AFTER report>
detail sections byte-identical after removing summary: True (108622 bytes)
```

bryony copy (`$S/bryony`, `write-report --scope project`, 04:11:12→04:11:25 UTC, exit 0): `Overall
66/100 — 4 of 7 dimensions rated: architecture 70 (sample: 200 of 1,178 files), code-quality 67
(sample: …), security 50, test-strategy 75 (sample: …)`; focus = security redaction_hits_observed
(+8), architecture decision_records_missing (+7), test-strategy
source_files_without_covering_test_share (+6); could not evaluate = blast-radius,
requirement-fidelity.

Screenshots: `$S/shots/coffee-1280.png`, `$S/shots/coffee-400.png`, `$S/shots/bryony-1280.png`,
`$S/shots/bryony-400.png` (400 = a true 400px iframe). Measured in the 400px iframe: summary
`scrollWidth=349 clientWidth=349`, no summary element past 400px; the page's own scrollWidth
(402 coffee / 522 bryony) comes from the pre-existing Context-warnings banner (T067 learning), not
the summary.

**DELTA**: The report now opens with a short summary: the overall, which dimensions were rated, the
top three fixes with their rule, standard and worth, and what to add for the dimensions that could
not be rated, plus an optional paragraph from the calling agent labelled agent. Before, the report
opened straight into warnings and detail.

**WITNESS**: [who ran it and when — derived from `memory/event-trace/Txxx.jsonl`, never the
implementing agent alone]
