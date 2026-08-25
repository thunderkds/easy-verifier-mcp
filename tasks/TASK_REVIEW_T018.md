# TASK_REVIEW — T018: README documenting the intended v1 surface

> Sibling of `tasks/TASK_GUIDE_T018.md`. Everything here is **filled by the reviewer at Stage
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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | ☑ pass | `tests/test_t018_readme.py` — 6 tests. AC #4/SC #1 `test_runnable_readme_commands_exit_zero`, AC #4/SC #2 `test_planned_command_blocks_are_never_executed`, AC #9 `test_readme_has_at_least_one_command_block`, AC #10/SC #3 `test_documented_dimensions_match_the_registry`, SC #4 `test_an_unmarked_unrunnable_block_fails_the_rule`, plus `test_readme_never_leaves_reports_behind` for the no-writes edge case |
| Verification command run | ☑ pass | `pytest tests/test_t018_readme.py -q` → `6 passed in 0.34s`. Full suite `339 passed in 2.78s`, `ruff check src tests` → `All checks passed!`, `ruff format --check` clean. Run with the main checkout's interpreter (agent worktrees have no `.venv`), exit code read directly |
| Negative cases hold | ☑ pass | The Stage 4 P1(b) rewrite was validated by **sabotage in both directions**: `_is_planned` hardwired to `True` → FAILED; hardwired to `False` → FAILED; clean → 6 passed. Before the fix, *both* sabotages passed. The implementer separately confirmed the drift test goes red when a dimension name is stripped from the README (`{'security'}` reported undocumented), and that the injected-unmarked-block rule goes red without the `OSError` handling in `_run` |
| verify | ☑ pass | `verify` skill run by the Supervisor at the real CLI — 9 steps, 5 of them probes — **pass**. Every runtime claim the README makes was driven against `python -m easy_verifier.adapters.cli`: the one runnable block exits 0 with parseable JSON on stdout and warnings on stderr; all four `--scope` values accepted; **both narrow scopes refuse without their selector** (the P1(a) correction, `files_read: 0`, `coverage: 0.0`, explicit warning); coverage never appears without its miss list (11 populated entries); the standalone limited-context warning fires on a non-kit repo; evaluating a repo wrote **nothing** into it and created no `reports/`; a `FAKEfake…` token was fingerprinted with the raw value absent and `had_redactions: true`; and all three planned subcommands are genuinely `invalid choice`, so the markers are truthful rather than hedging |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | ☑ pass | Reviewed: `README.md` (127 lines) and `tests/test_t018_readme.py` (182 lines as shipped, 223 after fixes). Read as consumed contracts, not reviewed: `dimensions/__init__.py` (`DIMENSIONS`, for the drift assertion) and `adapters/cli.py`'s argparse surface (to check the README's flag claims against reality). No source file was modified — the guide put `src/**` off-limits, and the one docs-vs-code disagreement found was reported rather than fixed |
| Full smoke suite still green (no regression) | ☑ pass | `339 passed in 2.78s`, up from 333 on `develop` (6 new). `ruff` clean. No source change, so no regression surface beyond the new test file |
| **UI: Visual regression (diff or verdict pasted)** | ☐ N/A | Documentation task — no UI component. The deliverable's only surface is the CLI, verified above |
| **UI: Design-system compliance (tokens/colors/typography verified)** | ☐ N/A | As above |
| **UI: Responsiveness at target viewports** | ☐ N/A | As above |

### Stage 4 findings

`code-review` run by the Supervisor: **P0 0 / P1 2 (both fixed, `acb6016`) / P2 3 / P3 0**.
`security-review` ☐ N/A (Low risk; no source change, and the new test spawns subprocesses only for
commands the README itself documents).

**P1(a) — the README stated something false about the tool.** The scopes table said `changes` takes
`--ref` *(optional)*. It does not: omitting it refuses outright — `files_read: 0`, `coverage: 0.0`
and an unresolved-scope warning, exactly as `task` without `--task-id` does. The table also
contradicted the sentence directly above it, which already stated the refusal principle for narrow
scopes generally. Corrected to **required**, with the refusal stated once for both selectors. Note
the doc-truth test **cannot** catch this class: only fenced commands are pinned, prose is not.

**P1(b) — `test_planned_command_blocks_are_never_executed` could not fail.** Its loop body was a
bare `continue`, so the monkeypatched `subprocess.run` was unreachable and the test asserted
nothing. Proved by sabotage: it passed with `_is_planned` hardwired to `True` **and** hardwired to
`False` — two contradictory premises, both green. **Fifth instance of this project's green-test-that-
cannot-fail class** (T005 tier prefix, T008 interchangeable cap fixtures and unasserted miss
reasons, T010 the untested cap path), and it was guarding precisely the half of the marker rule the
guide called binding. Rewritten to drive the shared `_run_unmarked` runner, record what was actually
invoked, and pin both sides — no planned command ran, and the unmarked set is non-empty and ran in
full. Now fails under both sabotages.

**Accepted residue, not fixed:**

(a) **The exit-0 half of the doc-truth test rests on a single command.** Only 1 of 6 blocks is
runnable; the other 5 are correctly marked planned. That is the honest consequence of the user's
"full v1 surface" decision, not a defect — but the CLI flags that *do* work today (`--scope
task`/`--task-id`, `--ref`, `--budget-bytes`) appear only in prose, so nothing pins them. Adding two
or three runnable examples would materially strengthen the test, and is the obvious follow-up when
T015 lands.

(b) **A mismarked block is undetectable.** Marking a genuinely-broken-today command as planned hides
it, since planned blocks are never executed. Inherent to the convention the guide accepted.

(c) **The drift test matches `` `name` `` anywhere in the file**, so a dimension could count as
documented by appearing only inside a planned example, satisfying AC #2 without a real description.

**Observed at Stage 5, recorded rather than fixed:**

(d) **The README's only runnable command produces an empty pack on a clean checkout** — `--scope
worktree` evaluates *uncommitted* changes, and a fresh clone has none, so the first command a
newcomer types returns 0 excerpts, coverage 0.0 and empty stderr. `--scope project` would
demonstrate the tool. Friction rather than a defect, but in the worst possible place.

(e) **The doc-truth test cannot validate any command using shell syntax.** It runs `shlex.split`
through `subprocess` with no shell, so `$(pwd)`, pipes and `&&` never expand — the docker block's
`"$(pwd)"` is doubly unverifiable. `docker` **is** installed on this machine, which makes the planned
marker load-bearing for safety and not only accuracy: an unmarked docker block would have reached the
daemon.

(f) **Docs-vs-code gap reported by the implementer, correctly not fixed**: FR-013a discovery, FR-025
combined-pack and FR-014/017/018 report rendering are all in `PRD.md` but absent from `src/`
(T011–T016 unbuilt). All documented under the planned marker.

---

## Demonstration

> Anchors what this task delivered to an observable before/after pair. BEFORE has no `N/A` path:
> if the task changes executable code, BEFORE is a pasted, timestamped terminal capture taken
> **before any implementation commit exists**; if it does not (docs, templates, skill-instruction
> text), BEFORE is the **verbatim prior content** of what changed — a quoted excerpt, not a command.

**BEFORE**: Verbatim prior content of `README.md` in full (a single line, no trailing newline):

```
# easy-verifier-mcp
```

**AFTER**: `README.md` is now a full operator-facing document (what the tool is/refuses to do, the
seven dimensions checked against `DIMENSIONS`, the four scopes and their selectors, both adapters
with runnable-vs-planned commands, safety posture, coverage/miss-list rule, standalone/kit-aware
modes) plus `tests/test_t018_readme.py`, a doc-truth test enforcing that every fenced command block
is either runnable today or carries a `planned` marker:

```
$ .venv/bin/python -m pytest tests/test_t018_readme.py -q
......                                                                   [100%]
6 passed in 0.29s
$ echo exit=$?
exit=0
```

**DELTA**: A newcomer can now read `README.md` alone to learn what runs today (the CLI) versus what
is planned (MCP, Docker, discovery/combined/write-report), and a future edit that drops the
`planned` marker or lets `DIMENSIONS` drift from the doc is caught by an automated test instead of
going unnoticed.

**WITNESS**: Supervisor, 2026-08-25 — Stage 4 `code-review` and Stage 5 `verify` both run against the
T018 worktree with the main checkout's interpreter, independently of the implementing agent
(`backend-developer`, sonnet, which wrote `dc39e4a`). The Stage 4 P1s were found by attacking the
implementation rather than reading the diff: P1(b) by hardwiring `_is_planned` in both directions and
observing the test stay green either way, and P1(a) by running `--scope changes` without `--ref` at
the CLI and comparing the result against what the README claimed. Post-fix suite `339 passed`, and
every runtime claim in the README was driven at the real CLI surface in the nine steps recorded in
the `verify` row above.
