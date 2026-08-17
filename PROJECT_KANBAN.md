# PROJECT_KANBAN.md
**Last updated**: 2026-08-17

> Compact task board. Full context lives in `PROJECT_SPEC.md`. Update this file whenever a task status changes.

---

## Board

> Task line format: **Txxx** — [title] | [agent] | C[0–3] | Risk: Low/Med/High | P[0–2]
> Task-to-task preconditions live in the task's own `TASK_GUIDE_Txxx.md` (`Depends on:` field), not on this board — `pre_agent_validate_guide.py` checks it against this board's sections at spawn time. The `## Blocked` table below is for non-task blockers only (external people/APIs/decisions).

### Todo

_(Wave 1 complete — T001, T002, T003, T004, T005, T006 all merged to `develop`. Wave 2 is now the front.)_

**Wave 2 — Dimensions (parallelizable once Wave 1 is stable)**
- [ ] **T007** — Shared doc-extraction helper + solution-fit, requirement-fidelity, code-quality | backend-developer | C2 | Risk: Low | P0
- [ ] **T008** — `security` dimension (bespoke, every mode and scope) | backend-developer | C2 | Risk: Med | P0
- [ ] **T009** — `test-strategy` dimension (bespoke) | backend-developer | C2 | Risk: Low | P1
- [ ] **T010** — `blast-radius` dimension (bespoke) | backend-developer | C2 | Risk: Low | P1
- [ ] **T011** — Dimension discovery operation (FR-013a) | backend-developer | C0 | Risk: Low | P1

**Wave 3 — Output**
- [ ] **T012** — `synthesis.py`: combined multi-dimension pack + aggregate coverage | backend-developer | C1 | Risk: Low | P1
- [ ] **T013** — `report.py`: self-contained multi-dimension HTML into target `reports/` | backend-developer | C2 | Risk: Med | P0

**Wave 4 — Adapters**
- [ ] **T014** — `mcp_server.py`: FastMCP, stdio default, HTTP/SSE opt-in loopback-only | backend-developer | C1 | Risk: Med | P0
- [ ] **T015** — `cli.py`: full surface, `--findings <path>` or stdin JSON, no server | backend-developer | C1 | Risk: Low | P0
- [ ] **T016** — Dockerfile + compose: non-root, read-only mount except `reports/` | common-infrastructure | C1 | Risk: Med | P0

**Wave 5 — Verification (QA-owned)**
- [ ] **T017** — Verification suite: two-mode integration, FR-022 parity, NFR-010 redaction proof (**HITL gate: parity definition**) | qa-expert | C2 | Risk: High | P0

### In Progress

_(none)_

### Ready for Review

_(none)_

### Done

- [x] **T005** — `budget.py`: relevance ordering, lazy consumption, explicit truncation | C2 | Risk: Med | Completed: 2026-08-17 | 26 tests (224 suite total) · code-review P0 0/**P1 1 (fixed)**/P2 2 (1 fixed, 1 accepted)/P3 1 · security-review ☐ **skill could not run** — the built-in resolves the diff via `origin/HEAD` and this repo's remote is named `github`; diff surface reviewed directly by the Supervisor instead, with the relocated redaction probed live on three paths · `verify` run by Supervisor · merged to `develop`. **P1 was a design defect the task's own test masked**: single-pass arrival-order admission with a one-excerpt eviction patch is not tiering — with 6 tier-3 excerpts ahead of 3 changed-file ones, the pack contained **zero** changed files. Its AC #2 test passed only because that test's tier-3 prefix was exactly short enough for one eviction to cover. Fixed per user decision by implementing the guide's prescribed **tier passes** (`collect` is now a callable, invoked once per non-empty tier); regression pinned by `test_changed_files_are_admitted_first_even_after_a_long_tier_3_prefix`. **P2 fixed**: `resolve_scope()` wired into `run_dimension`, closing T003's waived reachability debt — `project`/`worktree` now tier for real. **Accepted, recorded in `TASK_REVIEW_T005.md`**: (a) tier 2 narrowed to `scope.task_ref.guide_path` only, dropping kit-artifact names — a fixed non-empty tier-2 set would force a `collect()` pass and usually a full drain on *every* call; cost is that `PROJECT_SPEC.md` now ranks tier 3 under `project`/`worktree` scope, and **T007 should re-open this rather than inherit it**; (b) `changes`/`task` scope kinds still tier as `None` inside `run_dimension`, which has no way to accept a `ref`/`task_id` without a signature change; (c) no per-excerpt byte-overhead constant — adding one would move every T001 threshold, and AC #8's "documented tolerance" is met by zero tolerance.
- [x] **T001** — Tracer bullet: scaffold + `run_dimension()` contract + `architecture` dimension + minimal CLI | C2 | Completed: 2026-08-15 | 49 tests · code-review P0 0/P1 1 (fixed)/P2 2 (both taken) · security-review 0 HIGH 0 MEDIUM · merged to `plan/stage2-task-breakdown`
- [x] **T004** — `redact.py`: evidence-layer secret fingerprinting | C2 | Risk: High | Completed: 2026-08-16 | 53 tests · code-review P0 0/P1 0/**P2 2 (accepted residue, not fixed — see below)**/P3 2 · security-review 0 HIGH 0 MEDIUM · blast-radius run · merged to `develop` (`1acfa5c`). **Accepted residue**: a credential assignment whose value is followed by trailing prose with no comment marker, and single-character-class tokens of 12–31 chars, both pass through unredacted — they sit below the detector floors on purpose, so the tool stays usable when it evaluates its own repo (this repo is its own fixture).
- [x] **T006** — `findings.py`: finding schema + `validate_findings` | C1 | Completed: 2026-08-16 | 29 tests · code-review **no findings** · security-review 0 HIGH 0 MEDIUM · `verify` run by Supervisor against a real `run_dimension()` pack · merged to `develop` (`4b466d6`)
- [x] **T003** — `scope.py`: task/changes/worktree/project scope resolution | C1 | Risk: Low | Completed: 2026-08-16 | 32 tests · code-review P0 0/**P1 1 (fixed)**/P2 2 (1 fixed, 1 waived)/P3 1 (not taken) · security-review ☐ N/A (Low risk; subprocess surface covered by code-review's security reviewer) · `verify` run by Supervisor end-to-end across all four scopes · merged to `develop`. **P1 was a REPEAT defect**: `_walk_files` followed symlinked directories out of the repo — the same escape T002 already fixed in `context.py:_walk`. `scope.py` reimplemented the walk from scratch and reintroduced it; fixed with a containment check on entry, pinned by 2 regression tests. **Waived**: the guide's predicted edits to `models.py`/`pipeline.py`/`cli.py` were skipped — all 9 ACs pass without them and `run_dimension()`'s contract stays fixed. Cost: `resolve_scope` is unreachable until T005 lands.
- [x] **T002** — `context.py`: kit detection, kit-aware/standalone modes | C2 | Completed: 2026-08-16 | 35 tests · code-review P2×1 fixed · security-review 0 findings · `verify` run by Supervisor on the real CLI in both modes · merged to `develop` (`89046c8`). **Integration defect caught and fixed at Stage 5**: T002 moved path validation into `detect_context`, silently dropping T004's redaction of the `RepoPathError` message. Neither branch's tests caught it — each passed alone; the defect existed only in the combination. Restored in `context.py:_resolve_repo_path`.

> Post-merge state on `develop`: **224 tests pass**, `ruff` clean. 6 of 17 tasks done.

---

## Blocked

| Task | Reason | Waiting on |
|------|--------|-----------|
| ~~_(all tasks until T004)_~~ | ~~**`redact()` is an identity passthrough**~~ — **CLOSED 2026-08-16.** T004 landed the real detector; the seam now fingerprints at the evidence layer. Verified BEFORE/AFTER in `tasks/TASK_REVIEW_T004.md`. Residue, recorded rather than hidden: two confirmed detector misses (a credential assignment whose value is followed by trailing prose with no comment marker; single-char-class tokens of 12–31 chars) — both P2, both accepted trade-offs that keep the tool usable when it evaluates its own repo. T013 is unblocked. | — |
| ~~_(all Stage 3)_~~ | ~~**Base branch unpushed.**~~ **CLOSED 2026-08-16.** `plan/stage2-task-breakdown` was pushed and merged into `develop` via PR #2 (`e185baa`). `develop` is now the integration branch for Stage 3 task merges. | — |
| ~~T004~~ | **CLOSED 2026-08-15.** Fingerprint is unsalted SHA-256, 12-hex prefix, 4-char mask — the user confirmed reports stay inside the evaluated repo, so correlation is worth more than dictionary resistance. Rationale and revisit condition in `memory/decisions.md`. **T004 is unblocked.** | — |
| T017 | **HITL gate (open item #15)**: FR-022 says adapters produce "identical" output; the KPI table says "byte-equal". Timestamps and host-vs-container absolute paths differ by construction, so byte-equality is unachievable as written. Needs a defined normalization or a weaker, precise word. | thunderkds |

> Both are gates at pickup time, not blockers on planning — the guides are written and the tasks are
> spawnable the moment the decision is recorded.

---

## Stage Tracker

| Stage | Status |
|-------|--------|
| 0.5 Brainstorming | ✅ Done |
| 1 Environment Setup | ✅ Done |
| 1.5 Sub-Agent Architecture | ✅ Done |
| 2 Planning (/plan) | ✅ Done |
| 3 Execution | 🔄 In Progress (5/17 done) |
| 4 Review | 🔄 In Progress |
| 5 Integration & Verify | 🔄 In Progress |
