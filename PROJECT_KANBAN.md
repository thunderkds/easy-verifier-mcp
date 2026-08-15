# PROJECT_KANBAN.md
**Last updated**: 2026-08-15

> Compact task board. Full context lives in `PROJECT_SPEC.md`. Update this file whenever a task status changes.

---

## Board

> Task line format: **Txxx** — [title] | [agent] | C[0–3] | Risk: Low/Med/High | P[0–2]
> Task-to-task preconditions live in the task's own `TASK_GUIDE_Txxx.md` (`Depends on:` field), not on this board — `pre_agent_validate_guide.py` checks it against this board's sections at spawn time. The `## Blocked` table below is for non-task blockers only (external people/APIs/decisions).

### Todo

**Wave 1 — Foundation (blocking; nothing in Wave 2+ starts until the pipeline contract is fixed)**
- [ ] **T002** — `context.py`: kit detection, kit-aware/standalone modes, limited-context warning | backend-developer | C2 | Risk: Med | P0
- [ ] **T003** — `scope.py`: task/changes/worktree/project scope resolution | backend-developer | C1 | Risk: Low | P0
- [ ] **T004** — `redact.py`: evidence-layer secret fingerprinting | backend-developer | C2 | Risk: High | P0
- [ ] **T005** — `budget.py`: relevance ordering, lazy consumption, explicit truncation | backend-developer | C2 | Risk: Med | P0
- [ ] **T006** — `findings.py`: finding schema + `write_report` validation | backend-developer | C1 | Risk: Med | P0

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

_None._

### Ready for Review

_None._

### Done

- [x] **T001** — Tracer bullet: scaffold + `run_dimension()` contract + `architecture` dimension + minimal CLI | C2 | Completed: 2026-08-15 | 49 tests · code-review P0 0/P1 1 (fixed)/P2 2 (both taken) · security-review 0 HIGH 0 MEDIUM · merged to `plan/stage2-task-breakdown`

---

## Blocked

| Task | Reason | Waiting on |
|------|--------|-----------|
| _(all tasks until T004)_ | **`redact()` is an identity passthrough** — evidence packs can contain live secrets, so the CLI must not be pointed at a repo holding real credentials by anyone who will share the output. Harmless while output reaches only the invoking user's terminal; **becomes material at T013**, when reports are written into a target repo. T013 must not merge before T004. | T004 |
| _(all Stage 3)_ | **Base branch unpushed.** `plan/stage2-task-breakdown` has no upstream; 7 local-only commits. Feature branches stack on an unpushed base, so nothing is reviewable off-machine and a later guide revision means a rebase for every stacked branch. Not blocking local work. Supervisor cannot push (guardrail hook by design) — user runs `git push -u origin plan/stage2-task-breakdown`. | thunderkds |
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
| 3 Execution | 🔄 In Progress (1/17 done) |
| 4 Review | 🔄 In Progress |
| 5 Integration & Verify | 🔄 In Progress |
