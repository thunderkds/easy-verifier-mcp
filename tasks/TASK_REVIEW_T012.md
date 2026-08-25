# TASK_REVIEW — T012: synthesis.py — combined pack + aggregate coverage

> Sibling of `tasks/TASK_GUIDE_T[NNN].md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t012_synthesis.py` — 27 tests, all written as part of this task, one or more per AC. `PYTHONPATH=src python -m pytest tests/test_t012_synthesis.py -q` → `27 passed in 3.54s` |
| Verification command run | ☑ pass | Full suite in the worktree: `PYTHONPATH=src python -m pytest -q` → `366 passed in 6.17s`. Lint: `ruff check src tests` → `All checks passed!` |
| Negative cases hold | ☑ pass | Sabotage checks, each green on the real implementation and **red** when the property is inverted: AC #4 (a `narrative` field added → detection test fails), AC #6 (per-dimension try/except removed → 3 tests fail on the raw `RuntimeError`), AC #9 (budget pooled/divided instead of per-dimension → both equivalence tests fail), AC #10 (request order preserved instead of canonical → both order tests fail). Two Stage 4 regressions confirmed red on `b20d97a` and one on `5fbf548` before their fixes. |
| verify | ☑ pass | `/verify` run by the user at the real CLI on the merge-equivalent overlay — **pass**. Driven: 3-dimension and all-seven calls (exit 0, canonical order, `budget_model: per-dimension`); unknown name → exit 2 naming valid dimensions; missing `--dimensions` → exit 2; bad repo path → exit 2 on **both** the combined and single paths (the P1(b) fix, which pre-fix returned exit 0); duplicate + reversed names → deduped and canonically ordered; `--scope task`/`changes` with no selector → `security` reads 0 files with an explicit unresolved-scope warning, so T008's Stage 5 scope-widening defect does **not** reproduce through the new entry point. |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Reviewed: `core/synthesis.py`, `core/models.py` (the three DDR-0004 seam types), `dimensions/__init__.py` (`list_dimensions`), `adapters/cli.py` (`combined` subcommand), `tests/test_t012_synthesis.py`. Skipped: the seven dimension modules and `budget.py`/`pipeline.py` — this task calls `run_dimension` and changes nothing inside it, confirmed by the diff touching no file under `dimensions/` other than the package `__init__`. |
| Full smoke suite still green (no regression) | ☑ pass | 366 passed, up from the 339 baseline on `develop`; no pre-existing test modified. On the merge-equivalent overlay with T013 applied: 407 passed. |
| **UI: Visual regression (diff or verdict pasted)** | ☐ N/A | Pure backend/synthesis task — returns dataclasses, renders nothing. Section deleted per `PROJECT_SPEC.md` Critical Constraint 11. |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☐ N/A | As above — no component, no interaction, no design system in scope. |
| **UI: Responsiveness at target viewports** | ☐ N/A | As above — no rendered surface owned by this task. |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE**: Captured 2026-08-25T09:58:48Z, working tree stashed back to the pre-implementation state
(`git stash -u` on top of `5d61f46`, no `synthesis.py`/`combined` subcommand/`CombinedPack` model yet
existed):

```
$ date -u +%Y-%m-%dT%H:%M:%SZ
2026-08-25T09:58:48Z
$ PYTHONPATH=src python -c "from easy_verifier.core.synthesis import combined_pack"
Traceback (most recent call last):
  File "<string>", line 1, in <module>
ModuleNotFoundError: No module named 'easy_verifier.core.synthesis'
```

**AFTER**: Captured 2026-08-25T09:58:55Z, same worktree with the implementation applied:

```
$ date -u +%Y-%m-%dT%H:%M:%SZ
2026-08-25T09:58:55Z
$ PYTHONPATH=src python -m pytest tests/test_t012_synthesis.py -q
......................                                                   [100%]
22 passed in 3.39s
$ PYTHONPATH=src python -m easy_verifier.adapters.cli combined --repo . --dimensions architecture,security > /tmp/combined_out.json
$ echo exit=$?
exit=0
$ tail -3 /tmp/combined_out.json
    ]
  },
  "budget_model": "per-dimension"
}
```

**DELTA**: A caller can now request several named dimensions in one `combined_pack()` call (or the
CLI's `combined --dimensions a,b,...` subcommand) and get their packs back together with a single
aggregate `CoverageSummary` — per-dimension scores, a pooled combined figure, the union of miss
lists named per dimension, and the stated combining method — where before each dimension had to be
run and reconciled separately by the caller.

**WITNESS**: backend-developer (Sonnet 5), 2026-08-25, ran both captures directly in the
`easy-verifier-mcp-t012` worktree using the main checkout's `.venv/bin/python` interpreter
(`PYTHONPATH=src`); `memory/event-trace/T012.jsonl` does not exist in this worktree, so this is the
implementer's own run — an independent Stage 4/5 re-run by the Supervisor/reviewer is still required
per standing procedure.
