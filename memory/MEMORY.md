# MEMORY.md — Hot-Tier Memory Index

> **Rules**: Supervisor-only writes. Max 50,000 characters — a ratchet: `/compact-memory` may lower
> it, never raise it to fit growth. One-line summaries + links to cold files.
> Passed to every sub-agent as a path to read; the contents are not pasted into the spawn prompt.
> Updated by the Supervisor — prompted by the PostToolUse hook on `git push` / `git merge` (diff-driven pass), or via the `/compact-memory` skill.

---

## Memory Architecture

- [decisions.md](decisions.md) — code + infra architectural decisions (the "why")
- [glossary.md](glossary.md) — canonical biz domain terms and core domain models
- [learnings.md](learnings.md) — specs/requirement clarifications, patterns, gotchas

---

## Index

<!-- Format: - [Title](cold-file.md#section) — one-line summary.
     Target ≤150 chars/entry. Advisory: reported by the size test, never enforced.
     The enforced gate is the 50,000-character whole-file budget above. -->

### Decisions

- ▶ **[Integration strategy](decisions.md): local merges, one task at a time** (user, 2026-08-15; base updated 2026-08-16). **`develop` is now the Stage 3 integration branch** — `plan/stage2-task-breakdown` was pushed and merged via PR #2 (`e185baa`), closing the old "unpushed base" blocker. Per-task scrutiny is Stage 4 + Stage 5, not the PR.
- ▶ **Stage 2 complete (2026-08-15).** `PROJECT_SPEC.md` + `PROJECT_KANBAN.md` + 17 TASK_GUIDEs exist; `PROJECT_KANBAN.md` is now the single source of in-flight state. `memory/NEXT-SESSION.md` deleted as designed. Stage 3 not started; no product code yet.
- [Codebase Map](codebase-map.md) — structural snapshot: directory tree, entry points, blast-radius hotspots. Refresh via /map-codebase.

- [Context-packer architecture](decisions.md) — engine performs no LLM inference; all reasoning comes from the calling agent (MCP main agent, or user's agent CLI).
- [Two adapters, one core](decisions.md) — `mcp_server.py` (FastMCP HTTP/SSE) + `cli.py` (repo path); thin adapters, identical output required.
- [Two-step report flow](decisions.md) — pack → caller reasons → `write_report` validates + renders HTML into target repo `reports/`.
- [Redact secrets at evidence layer](decisions.md) — secret values fingerprinted before leaving the engine; never reach agent, report, or log. → see DDR-0001
- ▶ **[DDR-0002: never read secret-bearing files](decisions.md)** (user, 2026-08-16). `.env*`/`*.pem`/`*.key`/`id_rsa`/… excluded at `read_source()`; existence reported as `excluded: secret-bearing`, contents withheld. T008 gets a per-file HITL gate defaulting to refuse. **Complements, does not replace, DDR-0001** — a live-key-shaped token in a `README.md` proved exclusion alone is insufficient. Landed as Spec Constraint 4a + AC rows on T007/T008/T013 before pickup.
- ⚠️ **Never put a real vendor prefix in a test fixture** (`sk_live_`, `ghp_`, `xoxb-`). Scanners match on shape and cannot tell a fake from a real key — GitHub push protection rejected a push over T004's fixtures. Detectors match on `key=value` shape and character mix, never the prefix, so synthetic values test the same path. Convention: spell the fakeness in, as `FAKEfake…`.
- [Coverage score = auditable checklist ratio](decisions.md) — unweighted found/sought, never rendered without the miss list.
- [Docker in v1](decisions.md) — user override of supervisor's defer-to-v1.1 recommendation.
- [Evidence packs: 120 KB relevance-ordered budget](decisions.md) — byte-measured for determinism; explicit truncation field.
- [Dimension structure = pipeline fn + descriptors](decisions.md) — Option D; cross-cutting rules unbypassable; `collect` lazily iterable. See BRAINSTORMING_LOG.md.
- [Shared extraction helper for doc-shaped dimensions only](decisions.md) — 4 share a helper; security/test-strategy/blast-radius stay bespoke.
- [Local-only, stdio-first transport](decisions.md) — harness connects via local Docker, never the internet; HTTP/SSE opt-in and loopback-bound. Corrects inherited HTTP/SSE assumption.
- [Synthesis = engine aggregates, caller interprets](decisions.md) — recovers REQUIREMENT.md §4's missing synthesis layer without putting reasoning in the engine.
- [T001 is a tracer bullet, not a scaffold](decisions.md) — the pipeline contract lands as a working end-to-end path (repo in, real pack out) rather than an abstract signature; T004 fills the redaction seam it ships.
- [Extract the doc helper last, not first](decisions.md) — T007 builds three dimensions duplicatively, then factors out what the four actually share. Deliberate correction: Option A died from a premature shared abstraction.
- [Redaction fingerprint is unsalted](decisions.md) — SHA-256, 12-hex prefix, 4-char mask. Closes gap #14. Correlation beats dictionary resistance **because reports stay inside the evaluated repo**; revisit if that ever changes.
- [One HITL gate still open into Stage 3](decisions.md) — T017 FR-022 parity definition (gap #15): "identical" vs. "byte-equal". Recorded in PROJECT_KANBAN.md's Blocked table.
- ▶ **[T001 shipped — the `run_dimension()` contract is fixed](decisions.md)** (merged 2026-08-15). Signatures locked; 16 tasks written against it. File reading lives in `ctx.read_source()`, not the dimension. `sources_found` is clamped to `sources_sought` so the two partition it exactly; unprobed sources report `not examined`, never `not found`.
- ▶ **[T004 shipped — redaction is real](decisions.md)** (merged 2026-08-16, `1acfa5c`). Layered detectors: named patterns → entropy → per-segment key material, the last being what makes paths and URI passwords safe while keeping paths readable. **Two misses accepted, not fixed**: a credential assignment whose value is followed by trailing prose with no comment marker, and single-char-class tokens of 12–31 chars. Both anchors exist so the tool stays usable evaluating its own repo. T013 unblocked.
- ▶ **[T002, T006 and T003 merged](decisions.md)** (2026-08-16). `develop`: **198 tests**, ruff clean, **5/17 tasks done**. T003 = `resolve_scope()`, four scope kinds, read-only git only.
- ▶ **[A guide's "Files to Change" table is a prediction, not a contract](decisions.md)** — T003 skipped its predicted `models.py`/`pipeline.py`/`cli.py` edits, flagged it, and was waived: the **Acceptance Criteria** are the contract. Judge deviations against ACs, not the file table. Cost: `resolve_scope` unreachable until T005.
- ⚠️ **[A new module re-implementing a traversal re-inherits old bugs](learnings.md)** — T003's `scope.py` rewrote a file walk and reproduced the exact symlink-escape T002 had already fixed in `context.py:_walk`. Canonical containment test is `path.resolve().is_relative_to(repo.resolve())`, on entry **and** for symlinked files; it now lives in two places that must not drift. Check T007/T008 for the same.
- ⚠️ **[Agents may report "ready for review" with zero commits](learnings.md)** — T003 did. Always check `git log develop..HEAD` and `git status` in the worktree before trusting the report.
- ⚠️ **[Agent worktrees have no `.venv`](learnings.md)** — `PATH=.venv/bin:$PATH python` there silently falls back to system python and fails the T001 CLI tests. Use the main checkout's interpreter with `PYTHONPATH=src`, and check pytest's exit code directly (piping through `tail` masks it).
- ⚠️ **[A merge of two green branches can be a regression](learnings.md)** — T002 moved the path check that T004 had hardened with redaction; both suites passed alone, the leak existed only in the combination. **After every conflict resolution, re-probe any cross-cutting property (redaction/validation/auth/logging) that attached to a line the other branch relocated.**
- [Truncation is rejection-triggered; `omitted_count` is a lower bound](decisions.md) — pull until one item doesn't fit, drop it, stop. Never drain to count: for a file-reading `collect` that means reading every file. Fixes a T001 guide contradiction; aligns T001 with T005.
- [T012 budget recommendation: per-dimension, not pooled](decisions.md) — a total budget split across dimensions makes each pack's contents depend on what else was requested, breaking reproducibility. Decision to be recorded when T012 is picked up.

### Gotchas (see [learnings.md](learnings.md))

- ⚠️ **Stage 3 worktrees are created off the root commit** — an agent's worktree may contain only `LICENSE`+`README.md`. Every spawn prompt must order the agent to verify `PROJECT_SPEC.md` + its own guide are present and rebase onto the planning branch if not.
- ✅ **Trace state file unwritable from an isolated worktree — RESOLVED, no hook change.** It *is* writable from the main checkout. Standing Stage 5 procedure: Supervisor writes `.claude/hooks/.state/active_task` then runs the guide's Verification Command itself before merging. Not a bypass — it is the independent re-run Stage 5 already requires. Details in [learnings.md](learnings.md).
- **Guardrail hook matches command *mentions*** — a commit message or memory file containing `git push` blocks the whole Bash call. Use Write/Edit or `git commit -F`.
- ⚠️ **Merge gate: two traps, both hit on T001.** (a) Stage 5 evidence must be `git checkout <task-branch> -- tasks/TASK_REVIEW_Txxx.md` into the main checkout *before* merging — the gate reads the pre-merge copy. (b) The verification command must put the runner at a command boundary within 300 chars: `cd <worktree> && PATH=.venv/bin:$PATH python -m pytest tests/... -q`. An interpreter path prefix (`.venv/bin/python -m pytest`) never matches.
- **The `active_task` state file also feeds the step-limit hook** — Supervisor Bash calls count toward the named task's 90-call budget and will be killed once (auto-resets). Not an agent loop.
- ⚠️ **[`active_task` rejects a FUTURE timestamp as hard as a stale one](learnings.md)** — `age_s < 0` fails too. Always write it with `$(date -u '+%Y-%m-%dT%H:%M:%SZ')`, never a hand-guessed clock time, or the trace silently goes nowhere.
- ⚠️ **[The merge gate's own error hint is dead advice](learnings.md)** — it tells you to prefix `CLAUDE_ACTIVE_TASK=Txxx`, but that channel cannot work from inside a Bash call (hooks are siblings, not children). Use the state file.

### Learning Records

_None yet._
