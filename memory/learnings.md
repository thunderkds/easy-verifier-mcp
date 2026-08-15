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

**Interim handling**: expect untagged traces from worktree-isolated Stage 3 agents. Do not read a
missing attribution as evidence that a task skipped verification — check the Evidence table instead.
Must be resolved before the first merge gate actually fires. `.claude/hooks/**` is must-not-touch,
so the fix is a user decision.

### 2026-08-15 — The git guardrail hook matches command *mentions*, not just invocations

Writing a commit message or a memory file whose text contains `git push` or `git reset --hard`
blocks the whole Bash call, even though nothing dangerous is being run. Workaround: write the
content with the Write/Edit tool, or pass commit messages via `git commit -F <file>`. Known and
deliberately not fixed — `.claude/hooks/**` is must-not-touch.
