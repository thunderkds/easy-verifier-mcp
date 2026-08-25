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
