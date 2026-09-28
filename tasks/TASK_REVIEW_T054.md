# TASK_REVIEW — T054: Bugfix: reference gate asks for colocated_test_name_patterns (T037 × T052 merge regression)

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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t037_reference_gate.py`: `test_optional_fields_are_never_required` extended; reality test gains the `colocated_test_name_patterns` case (fixture test file moved to `test/app.test.js` so directory evidence isolates the field's gating role); new guard `test_every_field_metric_is_curated_everywhere_or_declared_optional` (catches the next field of this kind). Supervisor re-run `1342 passed, 2 skipped in 59.46s` |
| Verification command run | ☑ pass | Supervisor 2026-09-28 13:44 UTC: pytest `1342 passed, 2 skipped` (exit 0; the two merge-regression failures `test_no_framework_and_curated_language_means_no_gate[pyproject.toml|Cargo.toml]` now pass); `ruff check src tests` → `All checks passed!` (exit 0) |
| Negative cases hold | ☑ pass | Express repo still asks exactly its 4 framework fields (gate not over-suppressed) |
| verify | ☑ pass | Supervisor MCP-path core call (`score_repository(detect_gates=True)`): this repo `reference` None (was a `python.colocated_test_name_patterns` request after the T037×T052 merge); express repo → express test_name_patterns/test_declarations/assertions/security_sinks — pass |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Reviewed `core/metric_tables.py` OPTIONAL_FIELDS (+1 member with reason) and test changes. Root cause: T052 added a consumed-but-optional field to FIELD_METRICS in parallel with T037's gate deriving required fields from FIELD_METRICS; each branch green alone. New guard test prevents recurrence. P0 0, P1 0. Security N/A beyond Med inline: data-only change |
| Full smoke suite still green (no regression) | ☑ pass | full suite 1342 passed, 2 skipped |
| **UI: Visual regression (diff or verdict pasted)** | ☑ N/A | Pure backend task, no UI |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☑ N/A | Pure backend task, no UI |
| **UI: Responsiveness at target viewports** | ☑ N/A | Pure backend task, no UI |

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

**DELTA**: Curated-language repos without frameworks again get no reference request, and any future optional registry field must be declared or the guard test fails.

**WITNESS**: Supervisor re-ran suite, ruff and MCP-path gate calls on this repo and an express repo on 2026-09-28 (13:44 UTC), independent of the implementing agent.