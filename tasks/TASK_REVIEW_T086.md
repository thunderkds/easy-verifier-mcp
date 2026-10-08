# TASK_REVIEW — T086: toml migration_dirs via resolved conventions

> Sibling of `tasks/TASK_GUIDE_T086.md`. Everything here is **filled by the reviewer at Stage
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

**BEFORE** (2026-10-08T07:28:23Z, code at base commit; temp repo with git-ignored toml `[conventions] migration_dirs = ["dbchanges"]`, commit 2 adds `dbchanges/002.sql` = `ALTER TABLE t DROP COLUMN id;`; `score --scope changes --ref HEAD~1..HEAD --all`):
- blast-radius `destructive_migration_ops`: derivation "0 destructive migration operation(s) in the diff of 1 changed file(s): none"
- data `destructive_migration_ops_observed`: abstained, "no migration file with an up section, SQL or changelog was found, so no destructive operation could be observed"
- payload `registry_entries` already embeds the toml item (`migration_dirs: ['dbchanges']`, user-supplied), yet neither dimension used it.
- real-repo sha256 baselines (coffee-shop-api, kitchd `--scope project --all`) captured in background to scratchpad/before.*.sha.

**AFTER** (2026-10-08T07:52:11Z, same temp repo and command): blast-radius `destructive_migration_ops` = 1 ("dbchanges/002.sql:1-1 DROP COLUMN ..."); data `destructive_migration_ops_observed` = 1; registry_entries still embeds the toml item. Replay without the toml is byte-equal (tests/test_t086_toml_migration_dirs.py). coffee-shop-api and kitchd `--scope project --all` sha256 identical before/after (2a12a8c9...74a, d1384151...56f). Full suite: 2 failed (known container tests), 2537 passed, 2 skipped; ruff clean. New tests fail pre-fix (5 of 8; the other 3 are negatives/replay guards).

**DELTA**: a repo's `.easy-verifier.toml` `migration_dirs` / `destructive_migration_ddl` now drive blast-radius #5 and data #4, and replay byte-equal.

**WITNESS**: [who ran it and when — derived from `memory/event-trace/Txxx.jsonl`, never the
implementing agent alone]
