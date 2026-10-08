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
| **New test(s) cover Acceptance Criteria (file paths pasted)** | pass | tests/test_t086_toml_migration_dirs.py (8 tests, AC1-6; 5 fail on pre-fix src, 3 invariant ones pass both ways) |
| Verification command run | pass | full suite 2 failed (known stale-image container tests), 2537 passed, 2 skipped; ruff clean |
| Negative cases hold | pass | toml `destructive_migration_apis` refused (validation error 'curated-only field', same handling as other invalid toml values — stricter than guide's 'warning'); no-toml repo unchanged; cross-repo in-process no leak — pass |
| verify | pass | Supervisor 2026-10-08 independent temp repo (git-ignored toml migration_dirs=[dbchanges], commit adds DROP COLUMN): base src → blast-radius destructive_migration_ops 0, data abstains; T086 src → both 1 (`dbchanges/002.sql:1-1 DROP COLUMN`); registry_entries carries ['dbchanges'] — pass |
| Review scope bounded to the change's blast radius (affected set, not whole repo) | pass | Stage 4 code-review (Supervisor): migration_patterns(entry), _compat_evidence/_read_diff, data._facts, new tests. No P0/P1. Low risk; toml DDL extras pass through token_regex (escaped tokens, not raw regex); regex field stays curated-only — pass |
| Full smoke suite still green (no regression) | pass | coffee-shop-api 2a12a8c9… and kitchd d1384151… sha256 identical BEFORE/AFTER; T055/T057/T045 tests unedited and green — pass |
| **UI: Visual regression (diff or verdict pasted)** | N/A | pure backend task |
| **UI: Design-system compliance (tokens/colors/typography verified)** | N/A | pure backend task |
| **UI: Responsiveness at target viewports** | N/A | pure backend task |

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

**WITNESS**: Supervisor reran BEFORE/AFTER independently 2026-10-08 on a fresh temp repo (0/abstain → 1/1).
