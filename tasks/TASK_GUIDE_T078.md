# TASK_GUIDE — T078: Use local-layer and `.easy-verifier.toml` conventions in scoring, embedded for byte-equal replay
**Date**: 2026-10-08
**Complexity Level**: C2
**Risk Level**: Medium
**Priority**: P1
**Assigned agent**: backend-developer
**Agent guide**: `.claude/agents/backend.md`

---

## Mandatory Startup (Do Not Skip)

Before writing any code:
1. Read `PROJECT_SPEC.md`
2. Read `memory/MEMORY.md`
3. Read this file completely
4. Read `.claude/agents/backend.md`
5. Apply the C2 process from the Complexity matrix in `.claude/agents/general-agent-template.md`
6. Read `memory/codebase-map.md`
7. Read `docs/ddr/0011-code-derived-rules-and-flexible-conventions.md` (line 62: this task) and `docs/ddr/0005-*.md` (adapter parity = byte equality after declared normalization)
8. Read `tasks/TASK_GUIDE_T075.md` AC 10 (where this task was split from)

---

## Requirement (Pillar 1 — Adapt the requirement)

DDR-0011 made every convention a declared, extendable pattern list: `layer_paths`, `requirement_item_patterns`, `issue_reference_patterns` (the `conventions` entry) and `route_tokens` (per language, plus repository-wide in `conventions`). A repository can already extend them through the **local registry layer** (`registry.layered_conventions()`, at `sot_root()`) and **`.easy-verifier.toml` `[conventions]`** (`roles.load_repo_conventions` → `registry.with_config_conventions`). Both are loaded and validated — but scoring ignores them: `structure._curated()`, `requirement_fidelity._curated_conventions()`, `api.py` and `metric_tables.py` (`layer_of`) all use the curated entry only, and `metrics.py:1431` discloses "only the curated layer_paths apply: local-layer and .easy-verifier.toml …". DDR-0011 deferred this to T078 because conventions that change a score must travel with the report for FR-048 replay.

**Restated intent**:
> When a repository declares extra conventions (local layer or `.easy-verifier.toml` `[conventions]`), every rule that reads conventions (layer paths, route tokens, requirement-item and issue-reference patterns) uses curated + those extras, add-only (curated always wins). Every non-curated convention value that was used is embedded in the score payload / report (as replayable agent-input `registry_entries` items with source tag `user-supplied` / local tags and source `.easy-verifier.toml` or the local layer), so `--agent-input` replay on another machine — without the local layer or the toml — reproduces the score byte-for-byte (FR-048, DDR-0005). The "only the curated … apply" disclosure is removed / updated.

**Amendment (user, AskUserQuestion 2026-10-08 — option B "per-call only"):** toml conventions are embedded as `registry_entries` items `{"language":"conventions","field":<convention field>,"value":[...],"citation_url":".easy-verifier.toml","source_tag":"user-supplied"}`. Validation accepts `citation_url == ".easy-verifier.toml"` **only** for `language == "conventions"` + `user-supplied`. On replay such items are added in memory to that call's resolved conventions and **never written to disk**. Local-layer convention values (https links, local tags) are embedded as `{"language":"conventions", ...}` items too and replay-saved like other entries. Convention fields become valid `field` values for the `conventions` name.

**Out of scope**:
- New convention fields or new pattern kinds.
- Changing how `.easy-verifier.toml` is validated (limits stay `roles.MAX_CONFIG_*`).
- Repo-declared route receivers for T079 (the user chose the router-module rule; extras via `route_tokens` work automatically once this lands).

**Requirement Refs**:
- FR-048 (embedded registry entries, replay reproduces the score)
- FR-068 (flexible conventions)
- FR-022 / DDR-0005 (adapter parity)

### Requirement Fidelity Gate (sign off BEFORE implementation)

- [x] Restated intent confirmed (Supervisor 2026-10-08 from T075 AC 10 + DDR-0011 line 62; user approved this lane 2026-10-08 "continue")
- [x] Domain terms align with `PROJECT_SPEC.md` glossary
- [x] Every Acceptance Criterion below traces to a line in the Requirement
- [x] All Requirement Refs exist in `PRD.md`

---

## Dependencies & Reachability

**Depends on**: T073, T075, T079 (all merged)

**Entry point**: `with_config_conventions`

---

## Acceptance Criteria

| # | Criterion (testable) | Traces to requirement |
|---|----------------------|-----------------------|
| 1 | `.easy-verifier.toml` `[conventions] layer_paths = ["api=**/endpoints/**"]` changes `layer_of` results and the architecture layer metrics for that repo | use in scoring |
| 2 | Same for `requirement_item_patterns`, `issue_reference_patterns` (requirement-fidelity) and `route_tokens` (api + requirement-fidelity routes↔tests) | use in scoring |
| 3 | Local-layer `conventions.toml` values are used the same way (curated wins on conflict; add-only) | local layer |
| 4 | Every non-curated value used appears in the payload's `registry_entries` with its source tag and source; with no extras the payload is **byte-identical** to today (sha256 on a real repo with no toml/local layer) | FR-048, no regression |
| 5 | Replay: score a temp repo with a toml → take its `registry_entries` → delete the toml → `score --agent-input <entries>` gives a byte-equal payload (after the DDR-0005 normalizations only) | FR-048 replay |
| 6 | CLI and MCP give the same payload for AC 1/5 (DDR-0005 parity) | FR-022 |
| 7 | The disclosure at `metrics.py:~1431` and the T074 derivation note are updated to say which sources applied | honesty |
| 8 | Agent-supplied `registry_entries` for conventions go through the existing validation (`registry` agent-input checks); an invalid one is refused with a reason, never silently used | safety |

---

## Evaluation & Acceptance (How we know the agent worked correctly)

### Success Criteria (observable, pass/fail)

| # | Given (input/state) | Expect (output/behavior) | How it's checked |
|---|---------------------|--------------------------|------------------|
| 1 | temp repo + toml `layer_paths` extra | architecture metric changes; entry embedded | automated test |
| 2 | same repo, toml removed, replay with entries | byte-equal payload | automated test |
| 3 | nest-api / fullstack-ts (no toml) | sha256 of payload unchanged vs BEFORE | real-repo run |

### Verification Command (exact, runnable)

```bash
python -m pytest -q
python -m ruff check src tests
```

### Evidence (filled by reviewer at Stage 4/5)

> **Moved.** Filled by the reviewer at Stage 4/5 in `tasks/TASK_REVIEW_T078.md`.

---

## Demonstration

> **Moved.** See `tasks/TASK_REVIEW_T078.md`.

BEFORE commands (before any code change; paste timestamped output):
1. A temp git repo with `.easy-verifier.toml` `[conventions] layer_paths = [...]` (and/or `route_tokens`) — `score --repo <r> --scope project </dev/null`: show the extras are ignored (metric/derivation unchanged vs without the toml; the "only the curated" disclosure present).
2. A real repo without toml (nest-api or fullstack-ts): `score ... </dev/null | sha256sum` — the no-regression baseline. Long runs in background.

---

## UI / Design Acceptance Criteria

> N/A — pure backend task. All three UI Evidence rows are ☐ N/A.

---

## Real repos

Absolute paths: `.local/real-repos.md` (local, git-ignored).

real repos: nest-api `<real-repos>/nest-api`, fullstack-ts `<real-repos>/fullstack-ts`, node-monorepo `<real-repos>/node-monorepo` (read-only, `--repo` only).

---

## Approach

**Pattern reference**: how T038/T047 embed `registry_entries` (`score.py:~393 registry.local_entries(...)`, `ScoreResult.registry_entries`) and how agent-input entries are validated (`registry.py:~1081–1130`).

Thread one resolved `conventions` entry (curated + local + toml, via `layered_conventions()` + `with_config_conventions()`) from `score` into the places that today call the curated entry (`structure._curated`, `requirement_fidelity._curated_conventions`, `api.py`, `metric_tables` `layer_of`). Keep the curated default for callers that pass nothing. Embed the non-curated values used. Smallest change that does that — no new abstraction layer.

---

## Edge Case Checklist

- [ ] toml value equal to a curated value → not embedded twice, no change
- [ ] Invalid toml convention → existing validation warning, value not used
- [ ] Replay entry for a convention that the receiving machine's curated set already has → no duplicate
- [ ] Caches (`lru_cache` on `_curated`, `_route_patterns`) must not leak one repo's extras into another repo's score in the same MCP server process
- [ ] Redaction: toml values are user text — pass through the existing redact path where they appear in derivations

---

## Files to Change (Predicted)

| File | Change |
|------|--------|
| `src/easy_verifier/core/score.py` | resolve conventions once, embed used extras |
| `src/easy_verifier/core/structure.py`, `core/metric_tables.py` | accept the resolved entry |
| `src/easy_verifier/dimensions/requirement_fidelity.py`, `dimensions/api.py`, `dimensions/architecture.py` (if it reads layers) | use the resolved entry |
| `src/easy_verifier/core/metrics.py` | disclosure text |
| `tests/test_t078_repo_conventions.py` | new |

## Files Must NOT Touch

| File | Reason |
|------|--------|
| `src/easy_verifier/dimensions/blast_radius.py`, `dimensions/data.py`, curated `*.toml` migration rows | T057 runs in parallel |
| `dimensions/api.py` `_breaking_metric` | T084 |
| `packs/*` | unrelated |

---

## Test Plan

Unit: resolved-entry merge (add-only, curated wins). Score-level: AC 1–5 on temp repos. Parity: CLI vs MCP on the AC 5 repo. Real repo: no-toml sha256 unchanged.

---

## Completion Checklist

- [ ] Implementation done
- [ ] Lint passes
- [ ] Tests written AND pass — output pasted into `tasks/TASK_REVIEW_T078.md` Evidence (Hard-Stop Gate 5)
- [ ] Real-repo no-regression sha256 + replay demo pasted in Demonstration
- [ ] Supervisor notified: task ready for Stage 4 review
