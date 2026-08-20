# TASK_REVIEW — T009: test-strategy dimension

> Sibling of `tasks/TASK_GUIDE_T009.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t009_test_strategy.py` — 17 tests, one per Success Criterion (1–4) plus AC #1/#5/#6/#7/#8/#9, the ranked-cap ordering guard, the declared-source probe guard, and the missing-vs-bogus selector pair. `PATH=<main>/.venv/bin:$PATH PYTHONPATH=src python -m pytest tests/test_t009_test_strategy.py -q` → `17 passed in 0.19s` (2026-08-20T11:34:02Z, exit 0). |
| Verification command run | ☑ pass | See the AFTER capture below: `pytest tests/test_t009_test_strategy.py -q` → `17 passed`, and `python -m easy_verifier.adapters.cli test-strategy --repo .` now prints a real pack (was `invalid choice: 'test-strategy'` in BEFORE). |
| Negative cases hold | ☑ pass | Empty repo → `coverage_score 0.0`, full miss list, no estimate. `--scope task` with the flag **omitted** → `resolved_scope=None`, zero files read, explicit "could not be resolved" warning (no widening); with it **empty** and with it **bogus** (`T999`) → empty task scope, zero files read. `--scope changes` without `--ref` → same refusal. Coverage artifacts (`coverage.xml`, `.coverage`, `htmlcov/`) named in a warning but never read and their figures never serialized. |
| verify | ☐ pass / ☐ fail / ☐ N/A | Not run by the implementer — `verify` is user-invocation-only. The CLI was driven manually with each selector present, omitted, empty and bogus (see Negative cases) as a stand-in; Stage 5 `verify` still owed. |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☐ pass / ☐ fail | Changed set: `src/easy_verifier/dimensions/test_strategy.py` (new), `src/easy_verifier/dimensions/__init__.py` (one registry row), `tests/test_t009_test_strategy.py` (new), `tests/test_t001_pipeline.py` (registry expectation only). `core/**`, `_doc_extract.py` and `.claude/hooks/**` untouched. |
| Full smoke suite still green (no regression) | ☑ pass | `PATH=<main>/.venv/bin:$PATH PYTHONPATH=src python -m pytest -q` → `311 passed in 1.31s`, exit 0 (baseline 294 + 17 new). `ruff check .` → `All checks passed!`. |
| **UI: Visual regression (diff or verdict pasted)** | ☐ pass / ☐ fail / ☐ N/A | [screenshot path or LLM verdict — required for UI tasks, Hard-Stop Gate 6] |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☐ pass / ☐ fail / ☐ N/A | [method used + output] |
| **UI: Responsiveness at target viewports** | ☐ pass / ☐ fail / ☐ N/A | [viewports tested, any overflow findings] |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE** (captured 2026-08-20T11:26:38Z on `feat/t009-test-strategy` at `8d96335`, before any
implementation commit — the guide's Verification Command, run in the worktree):

```
$ date -u
Thu Aug 20 11:26:38 AM UTC 2026
$ git log --oneline -1
8d96335 docs(T009): carry Supervisor gate sign-off onto the branch
$ PATH=<main>/.venv/bin:$PATH PYTHONPATH=src python -m pytest tests/test_t009_test_strategy.py -q
ERROR: file or directory not found: tests/test_t009_test_strategy.py

no tests ran in 0.00s
pytest exit=4
$ PYTHONPATH=src python -m easy_verifier.adapters.cli test-strategy --repo .
usage: easy-verifier [-h] [--repo REPO]
                     [--scope {changes,project,task,worktree}] [--ref REF]
                     [--task-id TASK_ID] [--budget-bytes BUDGET_BYTES]
                     {architecture,code-quality,requirement-fidelity,security,solution-fit}
easy-verifier: error: argument dimension: invalid choice: 'test-strategy' (choose from 'architecture', 'code-quality', 'requirement-fidelity', 'security', 'solution-fit')
```

Neither half of the Verification Command can run: the test file does not exist, and `test-strategy`
is not a dimension the CLI accepts.

**AFTER** (2026-08-20T11:34:02Z, same commands, same worktree):

```
$ PATH=<main>/.venv/bin:$PATH PYTHONPATH=src python -m pytest tests/test_t009_test_strategy.py -q
.................                                                        [100%]
17 passed in 0.19s
exit=0
$ PYTHONPATH=src python -m easy_verifier.adapters.cli test-strategy --repo . | head -30
{
  "dimension": "test-strategy",
  "mode": "kit-aware",
  "scope": "project",
  "files_read": [
    "pyproject.toml",
    "tests/conftest.py",
    "src/easy_verifier/dimensions/test_strategy.py",
    "tests/test_t001_pipeline.py",
    "tests/test_t002_context.py",
    "tests/test_t003_scope.py",
    "tests/test_t004_redact.py",
    "tests/test_t005_budget.py",
    "tests/test_t006_findings.py",
    "tests/test_t007_doc_dimensions.py",
    "tests/test_t008_security.py",
    "tests/test_t009_test_strategy.py"
  ],
  "excerpts": [
    {
      "path": "pyproject.toml",
      "start_line": 20,
      "end_line": 29,
      "text": "dev = [\"pytest>=7.4\", \"ruff>=0.6\"]\n\n[tool.setuptools.packages.find]\nwhere = [\"src\"]\n\n[tool.pytest.ini_options]\ntestpaths = [\"tests\"]\n..."
    },
```

The dimension is now a CLI choice, the pytest configuration is cited at its real
lines (`pyproject.toml:20-29`, the `[tool.pytest.ini_options]` block), and the
repo's own test tree is read as evidence.

**DELTA**: [one sentence — what a user can now do that they could not before]

**WITNESS**: [who ran it and when — derived from `memory/event-trace/Txxx.jsonl`, never the
implementing agent alone]
