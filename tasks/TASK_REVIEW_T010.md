# TASK_REVIEW — T010: blast-radius dimension (bespoke)

> Sibling of `tasks/TASK_GUIDE_T010.md`. Everything here is **filled by the reviewer at Stage
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

**BEFORE**: captured `2026-08-24T10:32:41Z`, in the T010 worktree, before any implementation
commit existed (`git log develop..HEAD` was empty):

```console
$ date -u +%Y-%m-%dT%H:%M:%SZ
2026-08-24T10:32:41Z

$ PYTHONPATH=src .venv/bin/python -m pytest tests/test_t010_blast_radius.py -q
ERROR: file or directory not found: tests/test_t010_blast_radius.py

no tests ran in 0.00s
pytest exit=4

$ PYTHONPATH=src .venv/bin/python -m easy_verifier.adapters.cli blast-radius --repo . \
    --scope changes --ref HEAD~1..HEAD
usage: easy-verifier [-h] [--repo REPO]
                     [--scope {changes,project,task,worktree}] [--ref REF]
                     [--task-id TASK_ID] [--budget-bytes BUDGET_BYTES]
                     {architecture,code-quality,requirement-fidelity,security,solution-fit,test-strategy}
easy-verifier: error: argument dimension: invalid choice: 'blast-radius' (choose from 'architecture',
'code-quality', 'requirement-fidelity', 'security', 'solution-fit', 'test-strategy')
```

> Note: the guide's Verification Command reads `--range HEAD~1..HEAD`; the CLI's flag is `--ref`.
> The command above uses the corrected flag, and the guide text has been corrected in this task.

**AFTER**: same commands, `2026-08-24T10:42:04Z`, in the T010 worktree:

```console
$ date -u +%Y-%m-%dT%H:%M:%SZ
2026-08-24T10:42:04Z

$ PYTHONPATH=src .venv/bin/python -m pytest tests/test_t010_blast_radius.py -q
..................                                                       [100%]
18 passed in 1.01s
pytest exit=0

$ PYTHONPATH=src .venv/bin/python -m easy_verifier.adapters.cli blast-radius --repo . \
    --scope changes --ref HEAD~1..HEAD | head -30
warning [kit-aware]: Method: reference evidence in this pack comes from a textual search for
each scope file's path, dotted module path and file stem across the repository's code files. It
is not a resolved import graph — no target code was parsed, imported or run — so a same-named
symbol in an unrelated module is reported (over-reporting) and an aliased or dynamically formed
reference is not (under-reporting). Co-change evidence counts files appearing in the same local
git commits as a scope file: correlation in history, not a dependency.
warning [kit-aware]: Entry points were looked for in these packaging manifests: pyproject.toml,
setup.py, package.json, Cargo.toml, go.mod; by these declaration markers: [project.scripts],
[project.gui-scripts], [project.entry-points, console_scripts, entry_points, [[bin]], "bin",
"exports", "main", module ; and in entry-point-shaped files (__init__.py, __main__.py, main.*,
cli.*, app.*, server.*, routes.*, urls.py, index.*) surfaced by the reference search. Manifests
that are not in the repository are named in sources_missing.
warning [kit-aware]: Files that changed alongside the scope file(s) within the last 200 local
commits (number of commits they shared, not a dependency): PROJECT_KANBAN.md (2),
PROJECT_SPEC.md (1), memory/MEMORY.md (1), memory/NEXT-SESSION.md (1),
tasks/TASK_GUIDE_T001.md (1), … and 5 more. History is not followed across renames, so a file
renamed inside this window contributes only under its current name.
{
  "dimension": "blast-radius",
  "mode": "kit-aware",
  "scope": "changes",
  "files_read": [
    "pyproject.toml",
    ...
```

**DELTA**: a caller can now ask `easy-verifier blast-radius` for a repository's *code-dependency*
reach — which files textually reference the active scope, which files local git history shows
changing alongside them, and which packaging manifests declare downstream entry points — with the
discovery method stated in the pack itself and no risk rating anywhere.

**WITNESS**: [who ran it and when — derived from `memory/event-trace/T010.jsonl`, never the
implementing agent alone]
