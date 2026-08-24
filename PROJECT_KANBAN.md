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

- [x] **T009** — `test-strategy` dimension (bespoke) | C2 | Risk: Low | Completed: 2026-08-24 | 20 tests (314 suite total) · ruff clean · code-review P1 1 (cross-subproject false correspondence, fixed) · security-review ☐ N/A (Low risk) · `verify` run by the Supervisor at the real CLI — **FAILED first, passed after `591c0ce`** — merged to `develop`. **Stage 5 caught a P1 that Stage 4 closed over, including its own independent CLI re-verification**: the declared-source probe resolved bare `SOURCES_SOUGHT` names at repo root only, while the scope sweep read the same file from its real subdirectory — so a single default invocation against this repo produced a pack citing `tests/conftest.py` in both `files_read` and an excerpt while `sources_missing` simultaneously reported `conftest.py` as `not found in the target repository`, understating `coverage_score` to 0.111 (1/9). **Third instance of this project's recurring miss-list defect class** (T007 false secret-file reasons, T008 fabricated miss list) and the first in the opposite direction — the read happened and the miss list denied it. Fixed with `_resolve_declared_source()`, which falls back to a basename match inside the already-computed `scope_files` rather than writing a new walk; `pytest.ini`/`tox.ini`/`setup.cfg`/`pyproject.toml`/`package.json`/`jest.config.js` all shared the bug and are fixed uniformly, `.github/workflows/ci.yml` is correctly left root-anchored. Post-fix `coverage_score` 0.222 (2/9); genuine absences still report `not found`. Regression pinned by `test_nested_declared_source_is_never_both_cited_and_declared_missing`, confirmed red on `75b58ab` first. **Accepted residue, recorded in `TASK_REVIEW_T009.md`**: (a) the basename fallback inherits whatever `core/scope.py:_EXCLUDED_DIRS` misses — `node_modules` is excluded, `vendor/` is not, so in a repo with no config of its own a vendored dependency's `package.json` is credited as the project's declared source; **filed against `scope.py`, not charged to T009**, since the scope lock correctly kept the implementer out of the shared exclusion set; (b) `sources_found` names `conftest.py` for a file at `tests/conftest.py` — `files_read` disambiguates, but the checklist alone gives a path that does not exist.
- [x] **T008** — `security` dimension (bespoke, every mode and scope) | C2 | Risk: Med | Completed: 2026-08-20 | 15 tests (294 suite total) · ruff clean · code-review P0 0/**P1 2 fixed**/**P2 2 fixed**/P3 1 not taken · security-review ☐ **skill could not run** — the built-in resolves the diff via `origin/HEAD` and this repo's remote is named `github`; diff surface reviewed directly by the Supervisor, which confirmed no new filesystem, subprocess, or network primitive and no reimplemented path resolver · blast-radius run · `verify` run by the Supervisor at the real CLI surface — **FAILED first, passed after `4e4c07a`** · merged to `develop`. **Both Stage 4 P1s were green-suite defects the author's own fixtures could not see**: (a) candidates were `sorted(scope.files)[:200]`, a relevance-blind alphabetical cap — a 205-filler repo with a root `requirements.txt` and `zzz/Dockerfile` returned **zero excerpts**, and the bounded-reads test missed it because all 205 of its fixture files are identical; fixed with category ranking, the same lesson as T005's tier passes; (b) `collect` never probed `SOURCES_SOUGHT` at all, so `pipeline._missing_sources` fell back to its default and **fabricated the entire miss list** — `.env`, `Dockerfile`, `package.json` and `src/auth.py`, none of which exist here, were all reported as `not examined: the byte budget was reached`; same class as T007's false miss reasons. The suite had **no assertion on miss reasons at all**, which is why both shipped green. **Stage 5 then caught a third defect all three Stage 4 gates passed over**: omitting a narrow scope's required selector (`--scope task` with no `--task-id`) collapsed `ScopeError` into the whole-repo path, so the pack read repository-root files while labelling itself `scope: task` with empty warnings — contradicting `pipeline.py:60`'s own stated "never widen on failure" invariant. Only reachable by driving the CLI; a *bogus* selector was handled correctly all along, and only the *missing* one widened. **Accepted residue, recorded in `TASK_REVIEW_T008.md`**: (a) a fourth miss reason `not in the resolved <kind> scope`, beyond the three AC #11 names — the agent flagged it before building it; accepted because without the gate declared-source probing breaks Success Criterion 3, and AC #11 requires its three states be distinct, not that the vocabulary be capped; (b) `coverage_score` stays a weak signal (0.09 on this repo) because AC #7 requires a statically declared `SOURCES_SOUGHT` containing paths like `src/auth.py` that most repos lack — now truthful, but it does not track the 14 real excerpts produced; (c) `secret_approval` is never threaded through `run_dimension` or either adapter, so the HITL gate is structurally always-refuse in production — AC #12 is satisfied (`approval_requests` reaches the pack) but no operator can currently consent.
- [x] **T007** — Shared doc-extraction helper + solution-fit, requirement-fidelity, code-quality | C2 | Risk: Low | Completed: 2026-08-18 | 55 focused tests · 279 full suite · ruff clean · code-review P0 0/**P1 7 fixed**/**P2 2 accepted**/P3 0 · final independent re-review P0 0/P1 0 · Stage 5 verified in the assigned worktree and again after merge · merged to `develop` (`a948f11`). The resumed review caught six green-suite defects: missing standalone docs/code fallback, omitted task-guide ACs, hierarchy-blind sections, false secret-file miss reasons, safe-name symlink aliases to secret files, and non-Markdown comments suppressing config evidence. T005's tier-2 narrowing was re-opened: T007 reads declared kit sources and task-guide globs directly, while standalone mode uses discovered docs then bounded code fallback; no `budget.py` change was needed.
- [x] **T005** — `budget.py`: relevance ordering, lazy consumption, explicit truncation | C2 | Risk: Med | Completed: 2026-08-17 | 26 tests (224 suite total) · code-review P0 0/**P1 1 (fixed)**/P2 2 (1 fixed, 1 accepted)/P3 1 · security-review ☐ **skill could not run** — the built-in resolves the diff via `origin/HEAD` and this repo's remote is named `github`; diff surface reviewed directly by the Supervisor instead, with the relocated redaction probed live on three paths · `verify` run by Supervisor · merged to `develop`. **P1 was a design defect the task's own test masked**: single-pass arrival-order admission with a one-excerpt eviction patch is not tiering — with 6 tier-3 excerpts ahead of 3 changed-file ones, the pack contained **zero** changed files. Its AC #2 test passed only because that test's tier-3 prefix was exactly short enough for one eviction to cover. Fixed per user decision by implementing the guide's prescribed **tier passes** (`collect` is now a callable, invoked once per non-empty tier); regression pinned by `test_changed_files_are_admitted_first_even_after_a_long_tier_3_prefix`. **P2 fixed**: `resolve_scope()` wired into `run_dimension`, closing T003's waived reachability debt — `project`/`worktree` now tier for real. **Accepted, recorded in `TASK_REVIEW_T005.md`**: (a) tier 2 narrowed to `scope.task_ref.guide_path` only, dropping kit-artifact names — a fixed non-empty tier-2 set would force a `collect()` pass and usually a full drain on *every* call; cost is that `PROJECT_SPEC.md` now ranks tier 3 under `project`/`worktree` scope, and **T007 should re-open this rather than inherit it**; (b) `changes`/`task` scope kinds still tier as `None` inside `run_dimension`, which has no way to accept a `ref`/`task_id` without a signature change; (c) no per-excerpt byte-overhead constant — adding one would move every T001 threshold, and AC #8's "documented tolerance" is met by zero tolerance.
- [x] **T001** — Tracer bullet: scaffold + `run_dimension()` contract + `architecture` dimension + minimal CLI | C2 | Completed: 2026-08-15 | 49 tests · code-review P0 0/P1 1 (fixed)/P2 2 (both taken) · security-review 0 HIGH 0 MEDIUM · merged to `plan/stage2-task-breakdown`
- [x] **T004** — `redact.py`: evidence-layer secret fingerprinting | C2 | Risk: High | Completed: 2026-08-16 | 53 tests · code-review P0 0/P1 0/**P2 2 (accepted residue, not fixed — see below)**/P3 2 · security-review 0 HIGH 0 MEDIUM · blast-radius run · merged to `develop` (`1acfa5c`). **Accepted residue**: a credential assignment whose value is followed by trailing prose with no comment marker, and single-character-class tokens of 12–31 chars, both pass through unredacted — they sit below the detector floors on purpose, so the tool stays usable when it evaluates its own repo (this repo is its own fixture).
- [x] **T006** — `findings.py`: finding schema + `validate_findings` | C1 | Completed: 2026-08-16 | 29 tests · code-review **no findings** · security-review 0 HIGH 0 MEDIUM · `verify` run by Supervisor against a real `run_dimension()` pack · merged to `develop` (`4b466d6`)
- [x] **T003** — `scope.py`: task/changes/worktree/project scope resolution | C1 | Risk: Low | Completed: 2026-08-16 | 32 tests · code-review P0 0/**P1 1 (fixed)**/P2 2 (1 fixed, 1 waived)/P3 1 (not taken) · security-review ☐ N/A (Low risk; subprocess surface covered by code-review's security reviewer) · `verify` run by Supervisor end-to-end across all four scopes · merged to `develop`. **P1 was a REPEAT defect**: `_walk_files` followed symlinked directories out of the repo — the same escape T002 already fixed in `context.py:_walk`. `scope.py` reimplemented the walk from scratch and reintroduced it; fixed with a containment check on entry, pinned by 2 regression tests. **Waived**: the guide's predicted edits to `models.py`/`pipeline.py`/`cli.py` were skipped — all 9 ACs pass without them and `run_dimension()`'s contract stays fixed. Cost: `resolve_scope` is unreachable until T005 lands.
- [x] **T002** — `context.py`: kit detection, kit-aware/standalone modes | C2 | Completed: 2026-08-16 | 35 tests · code-review P2×1 fixed · security-review 0 findings · `verify` run by Supervisor on the real CLI in both modes · merged to `develop` (`89046c8`). **Integration defect caught and fixed at Stage 5**: T002 moved path validation into `detect_context`, silently dropping T004's redaction of the `RepoPathError` message. Neither branch's tests caught it — each passed alone; the defect existed only in the combination. Restored in `context.py:_resolve_repo_path`.

> Post-merge state on `develop`: **314 tests pass**, `ruff` clean. 9 of 17 tasks done.

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
| 3 Execution | 🔄 In Progress (9/17 done) |
| 4 Review | 🔄 In Progress |
| 5 Integration & Verify | 🔄 In Progress |
