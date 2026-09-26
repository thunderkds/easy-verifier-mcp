# TASK_REVIEW — T028: [Short Title]

> Sibling of `tasks/TASK_GUIDE_T028.md`. Everything here is **filled by the reviewer at Stage
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

**BEFORE**: backend-developer captured this at `ea08f39` (the worktree HEAD, before any T028
commit) by driving the real MCP server over stdio (`.venv/bin/python -m
easy_verifier.adapters.mcp_server`, `PYTHONPATH=<worktree>/src`). The target was a 4-file tmp fixture
(README, `src/app.py`, one test, `pyproject.toml`) with `scope=worktree`, and call 1 carried
`agent_input={"picks": {}}`. The script is in the session scratchpad as `demo.py`.
*Disclosure:* the capture ran at 16:18:33Z, before implementation. It was pasted here after
implementation commit `00499d2` because the first attempt to save this file failed on a tool
precondition and nobody noticed. The output below is the original, unedited.

```
$ date -u && git rev-parse --short HEAD && .venv/bin/python demo.py
Sat Sep 26 04:18:33 PM UTC 2026
ea08f39
call 1 (picks round done, no gate_evaluations): isError = False
  ratings: [('architecture', 'rating_abstention', None), ('blast-radius', 'rating', 50), ('code-quality', 'rating', 64), ('requirement-fidelity', 'rating_abstention', None), ('security', 'rating_abstention', None), ('solution-fit', 'rating_abstention', None), ('test-strategy', 'rating_abstention', None)]
  needs_input: null
call 2 (gate_evaluations for architecture): isError = True
   Error executing tool score: agent input: 1 error(s): gate_evaluations: not yet supported (arrives with T028)
```

**AFTER**: the same fixture shape and the same script at `00499d2`. The script now reads the offered
ref from call 1 and adds `"rationale": "PRIVATE"`. It prints the post-fix output below. The
`agent.weight` of an agent-rated entry was later changed to `null`; this run printed `"0.40"`.

```
Sat Sep 26 04:28:53 PM UTC 2026
00499d2
call 1 (picks round done, no gate_evaluations): isError = False
  ratings: [('architecture', 'rating_abstention', None), ('blast-radius', 'rating', 50), ('code-quality', 'rating', 64), ('requirement-fidelity', 'rating_abstention', None), ('security', 'rating_abstention', None), ('solution-fit', 'rating_abstention', None), ('test-strategy', 'rating_abstention', None)]
  needs_input: {"gate_evaluations": [{"dimension": "architecture", "reason": "abstained", "evidence_refs": ["README.md:1-3"], "omitted": 0}, {"dimension": "code-quality", "reason": "borderline: redaction_hits_observed, redacted_file_share, excerpts_observed", "evidence_refs": ["pyproject.toml:1-2"], "omitted": 0}, {"dimension": "requirement-fidelity", "reason": "abstained", "evidence_refs": ["pyproject.toml:1-2", "src/app.py:1-2", "tests/test_app.py:1-4"], "omitted": 0}, {"dimension": "solution-fit", "reason": "abstained", "evidence_refs": ["pyproject.toml:1-2", "src/app.py:1-2", "tests/test_app.py:1-4"], "o…
call 2 (gate_evaluations for architecture): isError = False
  ratings: [('architecture', 'agent_rated', 70, '70 = agent 70 (confidence 0.8; rules abstained: below_coverage_floor)'), ('blast-radius', 'rating', 50, None), ('code-quality', 'rating', 64, None), ('requirement-fidelity', 'rating_abstention', None, None), ('security', 'rating_abstention', None, None), ('solution-fit', 'rating_abstention', None, None), ('test-strategy', 'rating_abstention', None, None)]
  needs_input: null
  overall: 61 "3 of 7 dimensions contributed (2 rule-rated, 0 blended, 1 agent-rated); ratings average contributors only, so abstention can raise the overall; abstained: solution-fit (...), requirement-fidelity (...), security (...), test-strategy (...)"
  provenance[architecture]: [{'dimension': 'architecture', 'sources': 'rules', 'rating': 'agent-rated'}]
  'PRIVATE' in response: False
```

Gate payload size on a real repository: `score_repository(bryony, detect_gates=True)`, default
scope. The first call returns `needs_input.picks` at 2069 B. The picks round
(`agent_input={"picks": {}}`) returns `needs_input.gate_evaluations` at **2524 B** of compact JSON,
against a 222,975 B score payload. Five dimensions are gated: architecture, blast-radius and
code-quality as `borderline: redaction_hits_observed, redacted_file_share[, …]`, and
requirement-fidelity and solution-fit as `abstained`, each with 20 refs and 27 omitted.

**DELTA**: over MCP, an agent can now answer a hard gate with a cited score and confidence. That
answer turns an abstention into a labelled agent-rated number, or blends into a borderline rating
by `w = 0.5 × c`, with the parts always shown.

**WITNESS**: [who ran it and when — derived from `memory/event-trace/Txxx.jsonl`, never the
implementing agent alone]
