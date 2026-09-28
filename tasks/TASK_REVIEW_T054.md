# TASK_REVIEW — T054: [Short Title]

> Sibling of `tasks/TASK_GUIDE_T054.md`. Everything here is **filled by the reviewer at Stage
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

**BEFORE** (2026-09-28T13:37:03Z, `PYTHONPATH=src <main>/.venv/bin/python -m pytest -q tests/test_t037_reference_gate.py -k no_framework_and_curated_language`, run in the T054 worktree before any implementation commit):

```
=== timestamp: 2026-09-28T13:37:03Z ===
--- failing tests ---
.F..F.                                                                   [100%]
=================================== FAILURES ===================================
_____ test_no_framework_and_curated_language_means_no_gate[pyproject.toml] _____
...
>       assert score_repository(repo, detect_gates=True).reference is None
E       AssertionError: assert {'requests': [{'language': 'python', 'field': 'colocated_test_name_patterns', 'why': 'rules: requirement-fidelity.acce...t of further missing fields are scored with generic patterns only; omitted fields are listed once these are answered.'} is None
...
_______ test_no_framework_and_curated_language_means_no_gate[Cargo.toml] _______
...
>       assert score_repository(repo, detect_gates=True).reference is None
E       AssertionError: assert {'requests': [{'language': 'rust', 'field': 'colocated_test_name_patterns', 'why': 'rules: requirement-fidelity.accept...t of further missing fields are scored with generic patterns only; omitted fields are listed once these are answered.'} is None
...
2 failed, 4 passed, 26 deselected in 1.01s
```

And (2026-09-28T13:37:12Z, `EASY_VERIFIER_SOT=$(mktemp -d) PYTHONPATH=src <main>/.venv/bin/python -c "from easy_verifier.core.score import score_repository; print(score_repository('.', scope='worktree', detect_gates=True).reference)" </dev/null`, run against this repo itself):

```
=== timestamp: 2026-09-28T13:37:12Z ===
--- MCP-path python colocated request on this repo ---
{'requests': [{'language': 'python', 'field': 'colocated_test_name_patterns', 'why': 'rules: requirement-fidelity.acceptance_criteria_traced_to_code_share, requirement-fidelity.acceptance_criteria_traced_to_test_share, test-strategy.assertion_density_per_test, test-strategy.source_files_without_covering_test_share'}], 'omitted': 0, 'instructions': '...'}
```

**AFTER**: [pending fix commit — same two commands, re-run post-fix]

**DELTA**: [pending]

**WITNESS**: [pending — derived from `memory/event-trace/T054.jsonl`, never the implementing agent alone]
