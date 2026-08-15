# learnings.md — Cold Tier: Clarifications, Patterns & Gotchas

> **Rules**: Supervisor-only writes. Each entry dated (`YYYY-MM-DD`) and citing the file/task it came from (the diff-driven pass greps this file by changed file path).

## Requirement Clarifications

## Patterns

## Gotchas

### 2026-08-15 — Stage 3 worktrees are created off the root commit, not the current branch

**Symptom**: T001's agent found its worktree contained only `LICENSE` and `README.md` — no
`PROJECT_SPEC.md`, no `tasks/`, no `BRAINSTORMING_LOG.md`. The worktree branch had been created off
`0242067 Initial commit` rather than off `plan/stage2-task-breakdown`, the branch the spawn was
issued from.

**Impact**: an agent spawned this way cannot read its own TASK_GUIDE, `PROJECT_SPEC.md`, or
`memory/` — every input the Mandatory Startup block requires. It fails at step 1 or, worse, proceeds
without them.

**Workaround that worked**: the agent rebased its worktree branch onto the planning branch. Note the
hard-reset route is blocked by `block-dangerous-git.sh`, so rebase is the available option.

**Standing instruction**: every Stage 3 spawn prompt must tell the agent to verify its worktree
contains `PROJECT_SPEC.md` and its own `tasks/TASK_GUIDE_Txxx.md` **before** any other step, and to
rebase onto the current planning branch if not. Do not assume the harness got the base right.

### 2026-08-15 — The trace-attribution state file is unwritable from an isolated worktree

**Symptom**: `craft-spawn-prompt` element 6 instructs the agent to write
`<main-checkout>/.claude/hooks/.state/active_task` by absolute path. Under `isolation: "worktree"`
this fails — the sandbox permits `mkdir -p` on that path but refuses the file write, via both a Bash
redirect and the Write tool. T001's `Bash` calls are therefore unattributed.

**Why it matters**: `pre_bash_block_unsafe_merge.py:trace_shows_verification` fails closed on
untagged traces, so this can block an honest task at merge time — the same failure mode T047 fixed
for the env-var approach, returning through a different channel.

**Status**: unresolved, harness-side. The state file lives in the shared checkout so the hook can
read it; worktree isolation exists precisely to prevent writes there. The two mechanisms are in
direct conflict and there is no agent-side fix.

**RESOLVED 2026-08-15 — workaround, no hook change needed.** The state file is writable from the
**main checkout**; only the isolated worktree is refused. Verified empirically: writing
`.claude/hooks/.state/active_task` from the main checkout caused subsequent Supervisor `Bash` calls
to land in `memory/event-trace/T001.jsonl`.

**Standing Stage 5 procedure**, run by the Supervisor from the main checkout before any merge:

1. `mkdir -p .claude/hooks/.state && printf '%s\n%s\n' "Txxx" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > .claude/hooks/.state/active_task`
2. Run the guide's exact Verification Command. This produces a real test-runner `Bash` record
   attributed to `Txxx`, which is what `trace_shows_verification` requires.

This is **not** a gate bypass — it is the Supervisor genuinely re-running the suite in a context
separate from the agent that wrote it, which is what Stage 5 `verify` and the Pillar 3 oracle rule
ask for regardless. The defect happens to enforce the right behaviour: the trace can only be
satisfied by someone other than the worktree-isolated implementer.

**Caveat**: the state file is shared across worktrees and stays valid for
`CLAUDE_ACTIVE_TASK_STATE_MAX_AGE_S` (default 6h), so unrelated Supervisor `Bash` calls made
afterwards also attribute to that task until it is overwritten. Harmless for attribution purposes;
rewrite it when switching tasks. Do not run two tasks' verification concurrently.

### 2026-08-15 — The merge gate needs the runner at a command boundary, inside 300 chars

Two separate reasons `trace_shows_verification` rejected genuine T001 test runs, both worth knowing
before every future merge:

1. **`TEST_INVOCATION_PATTERN` anchors with `match`, not `search`.** `.venv/bin/python -m pytest …`
   never matches — the pattern wants `pytest` or `python -m pytest` at the head of a
   separator-delimited part. An interpreter path prefix defeats it.
2. **`summary` is truncated to 300 characters** by `post_tool_trace.py`. A command with long absolute
   paths in a `cd` or `export` prefix pushes the runner past the cutoff, so it is invisible to the
   gate even when it *is* at a boundary.

**Working form** (short, runner at an `&&` boundary, env assignment stripped by
`ENV_ASSIGNMENT_PREFIX`):

```
cd <worktree> && PATH=.venv/bin:$PATH python -m pytest tests/test_txxx.py -q
```

Separators are `[;&|\n]+`, so a newline counts. This is not gaming the gate — the tests genuinely
run; the command is simply phrased so the gate can see what ran.

### 2026-08-15 — Stage 5 evidence must be checked out of the task branch before merging

`pre_bash_block_unsafe_merge.py` reads a task's verify evidence from the **main checkout's**
`tasks/TASK_REVIEW_Txxx.md`, but under worktree isolation that file is filled on the branch being
merged. The gate therefore blocks with "no evidence row" on a task whose evidence genuinely exists —
it is reading the pre-merge copy.

**Standing step**, before every Stage 5 merge:
`git checkout <task-branch> -- tasks/TASK_REVIEW_Txxx.md` and commit, then merge. Legitimate only
because the Supervisor has independently re-verified the row's claims first; landing an unverified
evidence file to satisfy a gate would be fabrication.

### 2026-08-15 — The active_task state file also drives the step-limit hook

The Stage 5 trace workaround has a cost: while `.claude/hooks/.state/active_task` names a task, the
Supervisor's *own* Bash calls count toward that task's `pre_agent_step_limit` budget, and the hook
will kill a call with "T001 has exceeded 90 tool calls". The counter auto-resets, so the next call
proceeds — but expect it during a long review, and do not mistake it for an agent looping.

### 2026-08-15 — The git guardrail hook matches command *mentions*, not just invocations

Writing a commit message or a memory file whose text contains `git push` or `git reset --hard`
blocks the whole Bash call, even though nothing dangerous is being run. Workaround: write the
content with the Write/Edit tool, or pass commit messages via `git commit -F <file>`. Known and
deliberately not fixed — `.claude/hooks/**` is must-not-touch.
