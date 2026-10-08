# TASK_GUIDE — T086: Migration patterns use the call's resolved conventions (`.easy-verifier.toml` `migration_dirs`)
**Date**: 2026-10-08
**Complexity Level**: C1
**Risk Level**: Low
**Priority**: P2
**Assigned agent**: backend-developer
**Agent guide**: `.claude/agents/backend.md`

---

## Mandatory Startup (Do Not Skip)

Before writing any code:
1. Read `PROJECT_SPEC.md`
2. Read `memory/MEMORY.md`
3. Read this file completely
4. Read `.claude/agents/backend.md`
5. Apply the C1 process from the Complexity matrix in `.claude/agents/general-agent-template.md`
6. Read `memory/codebase-map.md`
7. Read `tasks/TASK_GUIDE_T057.md` and `tasks/TASK_GUIDE_T078.md` (both merged; this joins them)

---

## Requirement (Pillar 1 — Adapt the requirement)

T057 moved migration knowledge into `conventions` fields (`migration_dirs`, `destructive_migration_ddl`, curated-only `destructive_migration_apis`). `blast_radius.migration_patterns()` reads `layered_conventions()` — curated + local layer only. T078 (merged) resolves conventions per call (curated + local + `.easy-verifier.toml` + replayed items) via `structure.context_conventions(context)` / `repo_conventions`, and embeds the non-curated values in `registry_entries` for replay (`registry.convention_entries`). `migration_patterns()` does not use that, so a repo's toml `migration_dirs` is ignored by blast-radius #5 and data #4.

**Restated intent**:
> `migration_patterns` takes the call's resolved conventions entry (callers in `blast_radius.py` and `data.py` pass `context_conventions(context)`), so `.easy-verifier.toml` `[conventions] migration_dirs` / `destructive_migration_ddl` extras apply to both dimensions and, being non-curated values of the resolved entry, are embedded for byte-equal replay like other T078 conventions. `destructive_migration_apis` stays curated-only — a toml value for it is refused with a warning (verify; add the refusal if T078's toml path lets it through).

**Out of scope**: new migration fields; changing T057 matching semantics; the `_DOWN_START`/comment/Flyway rules.

**Requirement Refs**: FR-048 (replay), FR-068 (flexible conventions), DDR-0007.

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [x] Restated intent confirmed (user decision 2026-10-08 via AskUserQuestion; user "yes, run the remaining tasks" 2026-10-08)
- [x] Domain terms align with `PROJECT_SPEC.md` glossary
- [x] Every Acceptance Criterion below traces to a line in the Requirement
- [x] All Requirement Refs exist in `PRD.md`

---

## Dependencies & Reachability

**Depends on**: T057, T078 (merged)

**Entry point**: `migration_patterns`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | Temp repo with toml `[conventions] migration_dirs = ["dbchanges"]` and a destructive DDL line added under `dbchanges/` in a commit → blast-radius #5 and data #4 count it (`--scope changes --ref HEAD~1..HEAD`) | toml applies |
| 2 | That value appears in the payload `registry_entries`; deleting the toml and replaying with `--agent-input` gives a byte-equal payload (DDR-0005 normalizations only) | FR-048 replay |
| 3 | toml `destructive_migration_apis` value is refused with a warning, never used | curated-only |
| 4 | No toml: coffee-shop-api and kitchd `--scope project` payload sha256 identical BEFORE vs AFTER | no regression |
| 5 | Existing T057/T055/T045 tests green, expectations unedited | no regression |
| 6 | Two repos scored in one process (MCP server) do not leak migration dirs into each other (no cache keyed only globally) | isolation |

---

## Evaluation & Acceptance (How we know the agent worked correctly)

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | AC 1 temp repo | destructive op counted; entry embedded | automated test + CLI run |
| 2 | AC 2 replay | byte-equal | automated test |
| 3 | coffee/kitchd | sha256 equal | real-repo run (background) |

### Verification Command (exact, runnable)

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m ruff check src tests
```

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T086.md`.

---

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T086.md`.

BEFORE commands (before any code change; paste timestamped output): (1) the AC 1 temp repo — `score --scope changes --ref HEAD~1..HEAD </dev/null`: show blast-radius #5 / data #4 do not count the `dbchanges/` operation; (2) coffee-shop-api and kitchd `--scope project </dev/null | sha256sum` baselines (background).

---

## UI / Design Acceptance Criteria

> N/A — pure backend task. All three UI Evidence rows are ☐ N/A.

---

## Real repos

real repos (read-only, `--repo` only): coffee-shop-api `/home/hungnguyenhuu/workspace/training/tien.nguyen/nestjs-training/coffee-shop-api`, kitchd `/home/hungnguyenhuu/workspace/pets/hungnguyen111/kitchd`, bryony `/home/hungnguyenhuu/workspace/project/bryony/bryony`, tapchat-web (path in `memory/learnings.md`, T049 entry). Run real-repo scores with `run_in_background` and `</dev/null`; worktree code via `PYTHONPATH=<worktree>/src`. CLI: `.venv/bin/python -m easy_verifier.adapters.cli score --repo R --scope project|changes [--ref A..B] [--all] </dev/null`.

---

## Approach

**Pattern reference**: T078 threading (`context_conventions(context)` in `api.py` `_scan`); T057 `migration_patterns`. Give `migration_patterns` an `entry` parameter (default: today's behaviour for any caller passing none); pass the resolved entry from the two dimensions. Smallest change.

---

## Edge Case Checklist

- [ ] Resolved entry missing a field still raises (packaging error) only for the curated layer
- [ ] toml dir name any case → matched lowercase like curated
- [ ] Secret-shaped toml value dropped (T078 rule) — still dropped

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/dimensions/blast_radius.py`, `dimensions/data.py` | pass resolved conventions |
| `src/easy_verifier/core/registry.py` / `core/roles.py` | only if AC 3 needs a toml refusal |
| `tests/test_t086_toml_migration_dirs.py` | new |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| `dimensions/api.py` | T084 in parallel |
| `packs/*`, `registry/packs/*` | T085 in parallel |

---

## Test Plan

Unit: `migration_patterns(entry)` with a toml-extended entry. Score-level temp-repo tests for AC 1–3 and AC 6. Real-repo sha256.

## Completion Checklist

- [ ] Implementation done
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T086.md` Evidence (Hard-Stop Gate 5)
- [ ] Real-repo BEFORE/AFTER pasted in Demonstration
- [ ] Supervisor notified: task ready for Stage 4 review
