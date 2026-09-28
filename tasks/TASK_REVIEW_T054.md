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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | pass | `tests/test_t037_reference_gate.py::test_optional_fields_are_never_required`, `::test_optional_fields_really_are_optional_in_metric_code[colocated_test_name_patterns-True]`, `::test_every_field_metric_is_curated_everywhere_or_declared_optional`, `::test_no_framework_and_curated_language_means_no_gate[pyproject.toml]`, `[Cargo.toml]` |
| Verification command run | pass | `python -m pytest -q` → `1342 passed, 2 skipped in 61.22s`; `python -m ruff check src tests` → `All checks passed!` |
| Negative cases hold | pass | `function_start` (a genuinely required, curated-everywhere field) still asserts `after < full` in `test_optional_fields_really_are_optional_in_metric_code`, unaffected by this change |
| verify | N/A | C1 bugfix with a real-surface AC (#4, MCP `score_repository(...).reference is None`) already exercised directly above and by the two regressed T037 tests; no separate `verify` skill run performed |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | pass | Reviewed only `src/easy_verifier/core/metric_tables.py` (`OPTIONAL_FIELDS`) and `tests/test_t037_reference_gate.py`; no classification code touched, per Files Must NOT Touch |
| Full smoke suite still green (no regression) | pass | `1342 passed, 2 skipped` (was `1341 passed, 2 skipped` before the new guard test was added; no prior failures introduced) |
| **UI: Visual regression (diff or verdict pasted)** | N/A | pure backend task, no UI component |
| **UI: Design-system compliance (tokens/colors/typography verified)** | N/A | pure backend task, no UI component |
| **UI: Responsiveness at target viewports** | N/A | pure backend task, no UI component |

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

**AFTER** (2026-09-28T13:42:27Z and 13:42:28Z, same two commands, run after the fix commit):

```
=== timestamp: 2026-09-28T13:42:27Z ===
--- previously failing tests ---
......                                                                   [100%]
6 passed, 28 deselected in 0.93s
=== timestamp: 2026-09-28T13:42:28Z ===
--- MCP-path python colocated request on this repo ---
None
```

**DELTA**: A curated-language repo (pyproject.toml/Cargo.toml, no framework) no longer fails the reference-gate no-op test, and this repo's own MCP `score` no longer asks the caller to research `python.colocated_test_name_patterns` — the reference gate goes quiet again for curated languages with no framework.

**WITNESS**: backend-developer (T054 implementing agent), 2026-09-28, run in worktree `easy-verifier-mcp-T054`; trace state file `.claude/hooks/.state/active_task` set to T054 before the run.
