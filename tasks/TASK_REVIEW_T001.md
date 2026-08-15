# TASK_REVIEW — T001: Tracer bullet — scaffold, pipeline contract, architecture dimension, minimal CLI

> Sibling of `tasks/TASK_GUIDE_T001.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t001_pipeline.py` — 43 tests, written as part of T001. Coverage by AC: #2/#3/#7 pack shape + forbidden-field name check; #5/#5a laziness via `InstrumentedCollect`; #6 coverage arithmetic (5 parameterised cases + empty-sought); #8 seam spy; #9 no-invention; #10 CLI thinness; #11 no-LLM source scan. |
| Verification command run | ☑ pass | `pip install -e ".[dev]" && pytest tests/test_t001_pipeline.py -q && python -m easy_verifier.adapters.cli architecture --repo .` → `43 passed in 0.11s`, then the JSON pack shown in Demonstration AFTER (`coverage_score: 0.6`, `truncated: false`). |
| Negative cases hold | ☑ pass | Nonexistent repo path and file-as-repo-path both raise `RepoPathError`; CLI exits 2 with no traceback. Empty repo → empty excerpts, `coverage_score 0.0`, all sources in `sources_missing`, nothing invented. Binary file, unreadable file, symlink escaping the repo, empty file, 200 KB single line, empty `sources_sought` (→ `None`, not `0.0`), byte cap below the first excerpt — each has a dedicated test. |
| verify | ☑ pass | `Skill({ skill: "verify" })` unavailable — Skill tool disabled for this session. Verified manually instead: CLI run against this repo returns a real pack citing `PROJECT_SPEC.md` at lines 1–138, and cited line numbers were re-read off disk and compared 1-indexed against the file (`test_cited_line_numbers_are_1_indexed_and_match_the_file`) — pass. |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Reviewed: the 11 new files under `src/easy_verifier/` plus `tests/` and `pyproject.toml` — the entire change, which is also the entire product code in the repo. Skipped: Markdown planning artifacts and `.claude/` (untouched, and hooks are must-not-touch). `Skill({ skill: "code-review" })` and `Skill({ skill: "security-review" })` were **unavailable (Skill tool disabled)** — a manual pass stood in; an independent Stage 4 review is still owed, and Medium risk means `security-review` in particular has not actually been run. |
| Full smoke suite still green (no regression) | ☑ pass | No prior suite existed — this is the first product code in the repo. `pytest -q` over the whole `tests/` tree: 43 passed. `ruff check src tests` → All checks passed; `ruff format --check` clean. |
| **UI: Visual regression (diff or verdict pasted)** | ☑ N/A | There is no UI in v1 (`PROJECT_SPEC.md` Critical Constraint 11). T001 ships a library plus a JSON-emitting CLI. |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☑ N/A | Same — no rendered surface exists. The HTML report (T014) is the first task with anything visual. |
| **UI: Responsiveness at target viewports** | ☑ N/A | Same — no viewport. |

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE**: captured 2026-08-15T03:12:26Z in worktree `agent-a540643ad26d87392`, before any T001
implementation commit existed (`git log --oneline -1` → `f861a0a chore: move T001 to In Progress`):

```console
$ date -u +%Y-%m-%dT%H:%M:%SZ && python3 -V && python3 -m easy_verifier.adapters.cli architecture --repo . ; echo "exit=$?" ; ls tests ; ls pyproject.toml src
2026-08-15T03:12:26Z
Python 3.12.3
/usr/bin/python3: Error while finding module specification for 'easy_verifier.adapters.cli' (ModuleNotFoundError: No module named 'easy_verifier')
exit=1
ls: cannot access 'tests': No such file or directory
ls: cannot access 'pyproject.toml': No such file or directory
ls: cannot access 'src': No such file or directory
```

**AFTER**: captured 2026-08-15T05:43:05Z at commit `cec8f91`. Excerpt text trimmed for display only
(the real output carries full file text; nothing else is altered):

```console
$ python -m easy_verifier.adapters.cli architecture --repo .
{
  "dimension": "architecture",
  "mode": "kit-aware",
  "scope": "project",
  "files_read": ["PROJECT_SPEC.md", "BRAINSTORMING_LOG.md", "README.md"],
  "excerpts": [
    {"path": "PROJECT_SPEC.md",      "start_line": 1, "end_line": 138, "text": "# PROJECT_SPEC.md\n… [trimmed]"},
    {"path": "BRAINSTORMING_LOG.md", "start_line": 1, "end_line": 200, "text": "# BRAINSTORMING_LOG.md\n… [trimmed]"},
    {"path": "README.md",            "start_line": 1, "end_line": 1,   "text": "# easy-verifier-mcp"}
  ],
  "sources_sought": ["PROJECT_SPEC.md", "BRAINSTORMING_LOG.md", "ARCHITECTURE.md",
                     "docs/architecture.md", "README.md"],
  "sources_found":  ["PROJECT_SPEC.md", "BRAINSTORMING_LOG.md", "README.md"],
  "sources_missing": [
    {"source": "ARCHITECTURE.md",      "reason": "not found in the target repository"},
    {"source": "docs/architecture.md", "reason": "not found in the target repository"}
  ],
  "coverage_score": 0.6,
  "truncated": false,
  "omitted_count": 0
}
```

**DELTA**: A real repository now goes in and a real evidence pack comes out — files actually read,
citable 1-indexed excerpts, named misses with reasons, and a `found / sought` coverage ratio — all
through the single `run_dimension()` choke point that the remaining six dimensions will reuse, and
with no verdict anywhere in the output.

**WITNESS**: Common-Infrastructure-Agent in worktree `agent-a540643ad26d87392`, 2026-08-15. The
`memory/event-trace/T001.jsonl` record is **absent by harness defect, not by omission**: the trace
hook reads `.claude/hooks/.state/active_task` in the shared checkout, and worktree isolation blocks
every write to that path. Confirmed by the Supervisor as harness-side; the Evidence table below is
the substitute proof. Independent re-run by the reviewer still required.
