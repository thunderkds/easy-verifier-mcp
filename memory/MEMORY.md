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

- ▶ **[Integration strategy](decisions.md): local merges, ONE PR at the end** (user, 2026-08-15). Task branches merge locally into `plan/stage2-task-breakdown`; nothing is pushed per-task; one PR into `develop` when the user chooses. Per-task scrutiny is Stage 4 + Stage 5, not the PR.
- ⚠️ **UNPUSHED: `plan/stage2-task-breakdown` has no upstream** — as of 2026-08-15 it carries 7 local-only commits (all of Phase 0 / Stage 0.5 / Stage 1 / Stage 2; `docs/phase0-stage1-foundation` is an ancestor). Based on `origin/develop`, should PR into `develop`. The guardrail hook blocks push from the Supervisor by design — **the user must run** `git push -u origin plan/stage2-task-breakdown`. Stage 3 branches stack on this unpushed base until then.
- ▶ **Stage 2 complete (2026-08-15).** `PROJECT_SPEC.md` + `PROJECT_KANBAN.md` + 17 TASK_GUIDEs exist; `PROJECT_KANBAN.md` is now the single source of in-flight state. `memory/NEXT-SESSION.md` deleted as designed. Stage 3 not started; no product code yet.
- [Codebase Map](codebase-map.md) — structural snapshot: directory tree, entry points, blast-radius hotspots. Refresh via /map-codebase.

- [Context-packer architecture](decisions.md) — engine performs no LLM inference; all reasoning comes from the calling agent (MCP main agent, or user's agent CLI).
- [Two adapters, one core](decisions.md) — `mcp_server.py` (FastMCP HTTP/SSE) + `cli.py` (repo path); thin adapters, identical output required.
- [Two-step report flow](decisions.md) — pack → caller reasons → `write_report` validates + renders HTML into target repo `reports/`.
- [Redact secrets at evidence layer](decisions.md) — secret values fingerprinted before leaving the engine; never reach agent, report, or log. → see DDR-0001
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
- [Truncation is rejection-triggered; `omitted_count` is a lower bound](decisions.md) — pull until one item doesn't fit, drop it, stop. Never drain to count: for a file-reading `collect` that means reading every file. Fixes a T001 guide contradiction; aligns T001 with T005.
- [T012 budget recommendation: per-dimension, not pooled](decisions.md) — a total budget split across dimensions makes each pack's contents depend on what else was requested, breaking reproducibility. Decision to be recorded when T012 is picked up.

### Gotchas (see [learnings.md](learnings.md))

- ⚠️ **Stage 3 worktrees are created off the root commit** — an agent's worktree may contain only `LICENSE`+`README.md`. Every spawn prompt must order the agent to verify `PROJECT_SPEC.md` + its own guide are present and rebase onto the planning branch if not.
- ✅ **Trace state file unwritable from an isolated worktree — RESOLVED, no hook change.** It *is* writable from the main checkout. Standing Stage 5 procedure: Supervisor writes `.claude/hooks/.state/active_task` then runs the guide's Verification Command itself before merging. Not a bypass — it is the independent re-run Stage 5 already requires. Details in [learnings.md](learnings.md).
- **Guardrail hook matches command *mentions*** — a commit message or memory file containing `git push` blocks the whole Bash call. Use Write/Edit or `git commit -F`.

### Learning Records

_None yet._
